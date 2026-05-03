"""
104 Job Board Scraper
Fetches Software Engineer & AI Engineer jobs with salary > 40,000 TWD
Filters for Top 100 Taiwan companies or foreign companies
"""

import requests
import time
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# 104 API endpoint
BASE_URL = "https://www.104.com.tw/jobs/search/api/jobs"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.104.com.tw/",
    "Accept": "application/json, text/plain, */*",
}

# Job category codes for Software/AI roles
JOB_CATEGORIES = {
    "軟體工程師": "2007001016",
    "韌體工程師": "2007001017",
    "AI工程師": "2007001019",
    "資料科學家": "2007001020",
    "機器學習工程師": "2007001012",
}

# Salary code: 40000+ monthly
SALARY_FILTER = "40000"  # 40k+

def build_params(keyword: str, page: int = 1) -> dict:
    return {
        "ro": "0",
        "keyword": keyword,
        "area": "6001001000",  # 全台灣
        "order": "15",         # 最新
        "asc": "0",
        "s9": "1",             # 經常性薪資
        "salary": "40000",     # salary min 40k
        "page": page,
        "mode": "s",
        "jobsource": "2018indexpoc",
    }

def fetch_jobs_104(keyword: str, max_pages: int = 5) -> list[dict]:
    """Fetch jobs from 104 for given keyword."""
    all_jobs = []

    for page in range(1, max_pages + 1):
        try:
            params = build_params(keyword, page)
            resp = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            jobs = data.get("data", {}).get("list", [])
            if not jobs:
                break

            for job in jobs:
                parsed = parse_104_job(job)
                if parsed:
                    all_jobs.append(parsed)

            logger.info(f"[104] {keyword} page {page}: {len(jobs)} jobs fetched")
            time.sleep(1.5)  # be polite

        except Exception as e:
            logger.error(f"[104] Error fetching page {page} for '{keyword}': {e}")
            break

    return all_jobs


def parse_104_job(job: dict) -> Optional[dict]:
    """Parse a 104 job listing into standard format."""
    try:
        job_id = job.get("jobNo", "")
        title = job.get("jobName", "")
        company = job.get("custName", "")
        location = job.get("jobAddrNoDesc", "")
        salary = job.get("salaryDesc", "面議")
        job_type = job.get("jobType", "")
        tags = job.get("tags", [])
        appear_date = job.get("appearDate", "")
        description = job.get("description", "")

        # Work type
        work_type_map = {"1": "全職", "2": "兼職", "3": "高階", "4": "派遣"}
        work_type = work_type_map.get(str(job.get("jobType", "")), "全職")

        # Remote work flag
        remote_tags = [t.get("name", "") for t in tags if "遠端" in t.get("name", "") or "remote" in t.get("name", "").lower()]
        if remote_tags:
            work_type += " / 遠端"

        link = f"https://www.104.com.tw/job/{job_id}"

        # Industry / company type hints
        industry = job.get("indDesc", "")
        is_foreign = any(kw in company for kw in ["Google", "Microsoft", "Amazon", "Meta", "Apple", "IBM",
                                                    "Oracle", "SAP", "Salesforce", "Nvidia", "NVIDIA",
                                                    "Intel", "Qualcomm", "MediaTek", "ASML", "NXP",
                                                    "Ericsson", "Nokia", "Siemens", "Bosch", "ABB",
                                                    "Accenture", "Deloitte", "PwC", "KPMG", "EY"])

        return {
            "id": f"104_{job_id}",
            "source": "104",
            "date": appear_date,
            "title": title,
            "company": company,
            "location": location,
            "work_type": work_type,
            "salary": salary,
            "description": description[:200] if description else "",
            "full_description": description,
            "industry": industry,
            "is_foreign_hint": is_foreign,
            "link": link,
            "fetched_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"[104] Parse error: {e}")
        return None


def scrape_104(keywords: list[str] = None) -> list[dict]:
    """Main entry point for 104 scraping."""
    if keywords is None:
        keywords = ["software engineer", "AI engineer", "軟體工程師", "AI工程師", "機器學習工程師", "資料科學家"]

    all_jobs = []
    seen_ids = set()

    for kw in keywords:
        jobs = fetch_jobs_104(kw, max_pages=5)
        for job in jobs:
            if job["id"] not in seen_ids:
                seen_ids.add(job["id"])
                all_jobs.append(job)
        time.sleep(2)

    logger.info(f"[104] Total unique jobs: {len(all_jobs)}")
    return all_jobs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    jobs = scrape_104()
    print(f"Fetched {len(jobs)} jobs from 104")
    for j in jobs[:3]:
        print(j)
