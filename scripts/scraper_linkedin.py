"""
LinkedIn Job Scraper (via Google Search + BeautifulSoup)
Searches LinkedIn jobs through Google to avoid direct scraping blocks.
"""

import requests
import time
import re
import logging
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus, urlparse, parse_qs
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

LINKEDIN_SEARCH_QUERIES = [
    'site:linkedin.com/jobs "software engineer" "Taiwan" "外商" OR "跨國" OR "international"',
    'site:linkedin.com/jobs "AI engineer" "Taiwan" "外商" OR "跨國" OR "international"',
    'site:linkedin.com/jobs "machine learning engineer" Taiwan',
    'site:linkedin.com/jobs "software engineer" Taiwan "全球百大" OR "Fortune 500" OR "外商"',
    'site:linkedin.com/jobs "AI engineer" OR "data scientist" Taiwan',
]

# LinkedIn direct job search API (public, no auth required for basic listing)
LINKEDIN_JOBS_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"


def search_linkedin_via_google(query: str, num_results: int = 10) -> list[str]:
    """Use Google search to find LinkedIn job URLs."""
    urls = []
    try:
        search_url = f"https://www.google.com/search?q={quote_plus(query)}&num={num_results}"
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        for link in soup.select("a[href]"):
            href = link.get("href", "")
            # Extract actual URLs from Google redirect
            if "/url?q=" in href:
                actual_url = href.split("/url?q=")[1].split("&")[0]
                if "linkedin.com/jobs" in actual_url:
                    urls.append(actual_url)
            elif "linkedin.com/jobs" in href:
                urls.append(href)

        logger.info(f"[LinkedIn/Google] Query '{query[:50]}': {len(urls)} URLs found")
        time.sleep(3)  # Respect rate limits
    except Exception as e:
        logger.error(f"[LinkedIn/Google] Search error: {e}")

    return list(set(urls))


def fetch_linkedin_jobs_direct(keywords: list[str], location: str = "Taiwan") -> list[dict]:
    """Fetch LinkedIn job listings using their public guest API."""
    all_jobs = []

    for keyword in keywords:
        try:
            params = {
                "keywords": keyword,
                "location": location,
                "f_SB2": "1",   # Has salary info
                "f_JT": "F",    # Full time
                "start": 0,
                "count": 25,
                "sortBy": "DD",  # Most recent
            }

            resp = requests.get(
                LINKEDIN_JOBS_URL,
                headers=HEADERS,
                params=params,
                timeout=15
            )

            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                job_cards = soup.select("li")

                for card in job_cards:
                    parsed = parse_linkedin_card(card, keyword)
                    if parsed:
                        all_jobs.append(parsed)

                logger.info(f"[LinkedIn] '{keyword}': {len(job_cards)} cards found")
            else:
                logger.warning(f"[LinkedIn] Status {resp.status_code} for '{keyword}'")

            time.sleep(2.5)

        except Exception as e:
            logger.error(f"[LinkedIn] Error for '{keyword}': {e}")

    return all_jobs


def parse_linkedin_card(card, keyword: str) -> Optional[dict]:
    """Parse a LinkedIn job card HTML element."""
    try:
        # Job title
        title_el = card.select_one(".base-search-card__title") or card.select_one("h3")
        if not title_el:
            return None
        title = title_el.get_text(strip=True)

        # Company
        company_el = card.select_one(".base-search-card__subtitle") or card.select_one("h4")
        company = company_el.get_text(strip=True) if company_el else "Unknown"

        # Location
        loc_el = card.select_one(".job-search-card__location")
        location = loc_el.get_text(strip=True) if loc_el else "Taiwan"

        # Date
        date_el = card.select_one("time")
        date_str = date_el.get("datetime", "") if date_el else datetime.now().strftime("%Y-%m-%d")

        # Link
        link_el = card.select_one("a[href*='linkedin.com/jobs']") or card.select_one("a")
        link = link_el.get("href", "") if link_el else ""
        if link and not link.startswith("http"):
            link = "https://www.linkedin.com" + link

        # Job ID from URL
        job_id = re.search(r'/(\d+)/?', link)
        job_id_str = job_id.group(1) if job_id else hash(link)

        # Filter relevance: must match SW/AI engineering roles
        title_lower = title.lower()
        relevant_keywords = ["software", "engineer", "ai ", "machine learning", "ml ", "data",
                              "backend", "frontend", "fullstack", "full stack", "developer",
                              "工程師", "開發", "資料科學"]
        if not any(kw in title_lower for kw in relevant_keywords):
            return None

        return {
            "id": f"linkedin_{job_id_str}",
            "source": "LinkedIn",
            "date": date_str,
            "title": title,
            "company": company,
            "location": location,
            "work_type": "全職",
            "salary": "依職缺內容",
            "description": f"LinkedIn 職缺：{title} @ {company}",
            "full_description": "",
            "industry": "",
            "is_foreign_hint": True,  # LinkedIn Taiwan jobs tend to be foreign/top companies
            "link": link,
            "fetched_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.debug(f"[LinkedIn] Card parse error: {e}")
        return None


def scrape_linkedin(keywords: list[str] = None) -> list[dict]:
    """Main entry point for LinkedIn scraping."""
    if keywords is None:
        keywords = [
            "software engineer",
            "AI engineer",
            "machine learning engineer",
            "data scientist",
            "backend engineer",
        ]

    all_jobs = []
    seen_ids = set()

    # Method 1: LinkedIn guest API
    jobs_direct = fetch_linkedin_jobs_direct(keywords)
    for job in jobs_direct:
        if job["id"] not in seen_ids:
            seen_ids.add(job["id"])
            all_jobs.append(job)

    logger.info(f"[LinkedIn] Total unique jobs: {len(all_jobs)}")
    return all_jobs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    jobs = scrape_linkedin()
    print(f"Fetched {len(jobs)} jobs from LinkedIn")
    for j in jobs[:3]:
        print(j)
