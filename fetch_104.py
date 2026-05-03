"""
104 職缺抓取模組
策略：RSS endpoint（HTTP 200 已驗證）+ regex 解析
篩選：薪資 > 4萬、台灣百大或外商
"""

import re
import logging
import requests
from datetime import datetime
from typing import Optional

from .company_filter import is_target_company

logger = logging.getLogger(__name__)

HEADERS = {
    "Referer": "https://www.104.com.tw/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SEARCH_KEYWORDS = [
    "software engineer",
    "AI engineer",
    "軟體工程師",
    "AI工程師",
]

RSS_URL = "https://www.104.com.tw/jobs/search/rss/"


def fetch_104_jobs(existing_links: set) -> list[dict]:
    all_jobs = []
    for keyword in SEARCH_KEYWORDS:
        logger.info(f"🔍 104 搜尋：{keyword}")
        jobs = _fetch_rss(keyword, existing_links)
        logger.info(f"  → {len(jobs)} 筆符合條件")
        all_jobs.extend(jobs)

    seen = set()
    unique = []
    for job in all_jobs:
        if job["link"] not in seen:
            seen.add(job["link"])
            unique.append(job)
    return unique


def _fetch_rss(keyword: str, existing_links: set) -> list[dict]:
    params = {"keyword": keyword, "jobsource": "2018indexpoc", "order": "11", "s9": "1"}
    try:
        resp = requests.get(RSS_URL, params=params, headers=HEADERS, timeout=20)
        logger.info(f"  HTTP {resp.status_code}")
        if resp.status_code != 200:
            logger.error(f"  ❌ HTTP {resp.status_code}")
            return []
        return _parse_rss_html(resp.text, existing_links)
    except Exception as e:
        logger.error(f"  ❌ 請求失敗：{e}")
        return []


def _parse_rss_html(raw: str, existing_links: set) -> list[dict]:
    item_blocks = re.findall(r"<item>([\s\S]*?)</item>", raw, re.IGNORECASE)
    if not item_blocks:
        logger.warning(f"  ⚠️ 找不到 <item>，回應前 400 字：{raw[:400]}")
        return []
    logger.info(f"  找到 {len(item_blocks)} 個 item")

    results = []
    for block in item_blocks:
        job = _parse_item(block)
        if not job or job["link"] in existing_links:
            continue
        if not _passes_filter(job):
            continue
        results.append(job)
        existing_links.add(job["link"])
    return results


def _parse_item(block: str) -> Optional[dict]:
    try:
        title    = (_cdata(block, "title") or _tag(block, "title") or "").strip()
        link     = (_tag(block, "link") or _tag(block, "guid") or "").strip()
        desc     = (_cdata(block, "description") or _tag(block, "description") or "")
        pub_date = _tag(block, "pubDate") or ""

        if not link:
            return None

        company  = _clean(_extract(desc, r"公司名稱[：:]\s*(.*?)(?:<br|<\/|$)"))
        location = _clean(_extract(desc, r"工作地點[：:]\s*(.*?)(?:<br|<\/|$)"))
        salary   = _clean(_extract(desc, r"薪資[：:]\s*(.*?)(?:<br|<\/|$)"))

        if not company:
            m = re.search(r"[－—-]\s*(.+)$", title)
            if m:
                company = m.group(1).strip()

        work_type = (
            "Remote" if re.search(r"遠端|remote", desc, re.I) else
            "Hybrid" if re.search(r"混合|hybrid", desc, re.I) else
            "On-site"
        )

        return {
            "date": _parse_date(pub_date),
            "title": title,
            "company": company,
            "location": location,
            "work_type": work_type,
            "salary_str": salary,
            "salary_min": _parse_salary_min(salary),
            "description": _clean(desc)[:300],
            "link": link,
            "source": "104",
        }
    except Exception as e:
        logger.debug(f"  parse_item 失敗: {e}")
        return None


def _passes_filter(job: dict) -> bool:
    sal = job.get("salary_min", 0)
    if sal > 0 and sal < 40000:
        return False
    return is_target_company(job["company"])


def _cdata(block, tag):
    m = re.search(rf"<{tag}><!\[CDATA\[([\s\S]*?)\]\]></{tag}>", block, re.I)
    return m.group(1) if m else None

def _tag(block, tag):
    m = re.search(rf"<{tag}[^>]*>([\s\S]*?)</{tag}>", block, re.I)
    return m.group(1) if m else None

def _extract(html, pattern):
    m = re.search(pattern, html, re.I)
    return m.group(1) if m else ""

def _clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"&amp;|&lt;|&gt;|&nbsp;", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def _parse_salary_min(s):
    if not s:
        return 0
    nums = re.findall(r"[\d,]+", s)
    try:
        return int(nums[0].replace(",", "")) if nums else 0
    except ValueError:
        return 0

def _parse_date(date_str):
    for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT"]:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            continue
    return datetime.now().strftime("%Y-%m-%d")
