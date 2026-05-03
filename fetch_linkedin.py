"""
LinkedIn 職缺抓取模組
來源 1：Gmail Job Alert 解析
來源 2：LinkedIn Jobs RSS
"""

import re
import logging
import feedparser
import base64
from datetime import datetime, timedelta
from typing import Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .company_filter import is_target_company

logger = logging.getLogger(__name__)

LINKEDIN_RSS_QUERIES = [
    "software engineer Taiwan",
    "AI engineer Taiwan",
]

SALARY_KEYWORDS_PASS = [
    r"4[0-9],[0-9]{3}",   # 40,000+
    r"[5-9][0-9],[0-9]{3}",
    r"[1-9][0-9]{2},[0-9]{3}",
    r"TWD\s*\d{5,}",
    r"NTD\s*\d{5,}",
]


# ============================================================
# 來源 1：LinkedIn RSS
# ============================================================
def fetch_linkedin_rss(existing_links: set) -> list[dict]:
    results = []

    for query in LINKEDIN_RSS_QUERIES:
        encoded = query.replace(" ", "%20")
        url = (
            f"https://www.linkedin.com/jobs/search/?keywords={encoded}"
            f"&location=Taiwan&f_TPR=r86400&f_JT=F"  # 近24小時、全職
        )
        rss_url = (
            f"https://www.linkedin.com/jobs/search.rss?keywords={encoded}"
            f"&location=Taiwan&f_TPR=r86400&f_JT=F&f_SalaryRange=90000-999999999"
        )

        logger.info(f"🔍 LinkedIn RSS：{query}")
        try:
            feed = feedparser.parse(rss_url)
            entries = feed.get("entries", [])
            logger.info(f"  → 取得 {len(entries)} 筆")

            for entry in entries:
                job = _parse_rss_entry(entry)
                if job and job["link"] not in existing_links:
                    if is_target_company(job["company"]):
                        results.append(job)
                        existing_links.add(job["link"])

        except Exception as e:
            logger.error(f"  ❌ LinkedIn RSS 失敗 ({query}): {e}")

    return results


def _parse_rss_entry(entry: dict) -> Optional[dict]:
    try:
        link = entry.get("link", "").split("?")[0]
        if not link:
            return None

        title = entry.get("title", "").strip()
        summary = entry.get("summary", "") or entry.get("description", "")
        published = entry.get("published", "")

        # 解析公司與地點（LinkedIn RSS summary 格式：公司 - 地點）
        company, location = _parse_company_location(title, summary)

        work_type = (
            "Remote" if re.search(r"remote", summary, re.I) else
            "Hybrid" if re.search(r"hybrid", summary, re.I) else
            "On-site"
        )

        date_str = _parse_date(published)

        return {
            "date": date_str,
            "title": title,
            "company": company,
            "location": location,
            "work_type": work_type,
            "salary_str": "",
            "description": _clean_html(summary)[:300],
            "link": link,
            "source": "LinkedIn-RSS",
        }
    except Exception as e:
        logger.warning(f"  LinkedIn entry parse 失敗: {e}")
        return None


def _parse_company_location(title: str, summary: str) -> tuple[str, str]:
    """從 RSS title/summary 解析公司與地點"""
    company = ""
    location = ""

    # LinkedIn RSS title 格式通常是 "職稱 at 公司名"
    at_match = re.search(r"\bat\b (.+)", title, re.I)
    if at_match:
        company = at_match.group(1).strip()

    # summary 可能有更多資訊
    loc_match = re.search(r"(Taipei|Hsinchu|Taichung|Tainan|Kaohsiung|Taiwan[^,]*)", summary, re.I)
    if loc_match:
        location = loc_match.group(1).strip()

    return company, location


# ============================================================
# 來源 2：Gmail Job Alert 解析
# ============================================================
def fetch_linkedin_gmail(existing_links: set, gmail_creds_json: str) -> list[dict]:
    """
    用 Gmail API 讀取 LinkedIn Job Alert 信件並解析職缺。
    gmail_creds_json: Service Account JSON 字串（需有 Gmail domain-wide delegation）
    或傳入 None 時略過。
    """
    if not gmail_creds_json:
        logger.info("⏭️  Gmail 未設定，略過 LinkedIn Gmail 來源")
        return []

    results = []
    try:
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_info(
            __import__("json").loads(gmail_creds_json),
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )
        # 需要 delegated credentials（G Suite domain）
        # creds = creds.with_subject("your-email@yourdomain.com")

        service = build("gmail", "v1", credentials=creds)
        cutoff = (datetime.now() - timedelta(days=2)).strftime("%Y/%m/%d")
        query = f"from:jobalerts-noreply@linkedin.com after:{cutoff}"

        messages = _gmail_search(service, query)
        logger.info(f"📧 LinkedIn Gmail：找到 {len(messages)} 封信")

        for msg_meta in messages:
            msg = service.users().messages().get(
                userId="me", id=msg_meta["id"], format="full"
            ).execute()
            html_body = _extract_gmail_body(msg)
            jobs = _parse_email_jobs(html_body)

            for job in jobs:
                if job["link"] not in existing_links:
                    if is_target_company(job["company"]):
                        results.append(job)
                        existing_links.add(job["link"])

    except Exception as e:
        logger.error(f"❌ Gmail 抓取失敗: {e}")

    return results


def _gmail_search(service, query: str) -> list:
    try:
        result = service.users().messages().list(userId="me", q=query, maxResults=50).execute()
        return result.get("messages", [])
    except Exception:
        return []


def _extract_gmail_body(msg: dict) -> str:
    """從 Gmail API message 物件中解出 HTML body"""
    try:
        parts = msg.get("payload", {}).get("parts", [])
        for part in parts:
            if part.get("mimeType") == "text/html":
                data = part.get("body", {}).get("data", "")
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        # 沒有 parts，直接在 body
        data = msg.get("payload", {}).get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    except Exception:
        pass
    return ""


def _parse_email_jobs(html_body: str) -> list[dict]:
    """解析 LinkedIn Job Alert 信件 HTML"""
    jobs = []
    found_ids = set()

    card_regex = re.compile(r"jobcard_body_\d+_jobid_(\d+)")

    for m in card_regex.finditer(html_body):
        job_id = m.group(1)
        if job_id in found_ids:
            continue
        found_ids.add(job_id)

        pos = m.start()
        a_start = html_body.rfind("<a ", 0, pos)
        if a_start == -1:
            continue
        a_end = html_body.find("</a>", a_start)
        if a_end == -1:
            continue

        link_tag = html_body[a_start:a_end + 4]

        href_match = re.search(
            r'href="(https://www\.linkedin\.com/comm/jobs/view/\d+/[^"]*)"',
            link_tag
        )
        if not href_match:
            continue
        link = href_match.group(1).split("?")[0]

        title_match = re.search(r">([^<]{3,})</a>", link_tag)
        if not title_match:
            continue
        title = title_match.group(1).strip()

        plain = re.sub(r"<[^>]+>", " ", html_body[a_end + 4:a_end + 800])
        plain = re.sub(r"\s+", " ", plain)
        parts = plain.split("·")

        company = parts[0].strip() if len(parts) > 0 else ""
        location = parts[1].strip() if len(parts) > 1 else ""
        work_type = (
            "Remote" if re.search(r"remote", location, re.I) else
            "Hybrid" if re.search(r"hybrid", location, re.I) else
            "On-site"
        )

        jobs.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "title": title,
            "company": company,
            "location": location,
            "work_type": work_type,
            "salary_str": "",
            "description": "",
            "link": link,
            "source": "LinkedIn-Gmail",
        })

    return jobs


# ============================================================
# 工具
# ============================================================
def _clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_date(date_str: str) -> str:
    formats = ["%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return datetime.now().strftime("%Y-%m-%d")
