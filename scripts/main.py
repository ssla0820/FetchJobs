"""
Main Job Tracker Orchestrator
Runs daily via GitHub Actions to:
1. Scrape 104 & LinkedIn
2. Filter by salary, role, and company
3. Merge with existing data (dedup)
4. Generate HTML report
5. Save JSON data file
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from scraper_104 import scrape_104
from scraper_linkedin import scrape_linkedin
from job_filter import filter_jobs
from report_generator import generate_html_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("main")

DATA_FILE = Path("output/jobs_data.json")
REPORT_FILE = Path("output/index.html")
MAX_JOBS_KEPT = 500   # Keep most recent N jobs in history


def load_existing_jobs() -> list[dict]:
    """Load previously saved jobs."""
    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            logger.info(f"Loaded {len(data)} existing jobs")
            return data
        except Exception as e:
            logger.warning(f"Could not load existing jobs: {e}")
    return []


def save_jobs(jobs: list[dict]) -> None:
    """Save jobs to JSON file."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps(jobs, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    logger.info(f"Saved {len(jobs)} jobs to {DATA_FILE}")


def merge_jobs(existing: list[dict], new_jobs: list[dict]) -> list[dict]:
    """Merge new jobs with existing, deduplicate by ID."""
    seen_ids = {j["id"] for j in existing}
    added = 0

    for job in new_jobs:
        if job["id"] not in seen_ids:
            existing.append(job)
            seen_ids.add(job["id"])
            added += 1

    logger.info(f"Merged: +{added} new jobs → {len(existing)} total")

    # Sort by date desc, keep most recent
    existing.sort(key=lambda x: x.get("date", ""), reverse=True)
    if len(existing) > MAX_JOBS_KEPT:
        existing = existing[:MAX_JOBS_KEPT]
        logger.info(f"Trimmed to {MAX_JOBS_KEPT} most recent jobs")

    return existing


def generate_summary(jobs: list[dict]) -> str:
    """Generate a text summary for GitHub Actions log."""
    total = len(jobs)
    foreign = sum(1 for j in jobs if j.get("is_foreign"))
    top100 = sum(1 for j in jobs if j.get("is_top100_tw"))
    sources = {}
    for j in jobs:
        src = j.get("source", "Unknown")
        sources[src] = sources.get(src, 0) + 1

    lines = [
        "=" * 50,
        f"📊 Job Tracker Summary — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 50,
        f"✅ Total jobs in report: {total}",
        f"🌐 Foreign companies: {foreign}",
        f"🏆 Taiwan Top 100: {top100}",
        "📰 By source:",
        *[f"   • {src}: {count}" for src, count in sorted(sources.items())],
        "=" * 50,
    ]
    return "\n".join(lines)


def main():
    logger.info("🚀 Job Tracker starting...")

    # ── 1. Scrape ──
    logger.info("Scraping 104...")
    jobs_104 = []
    try:
        jobs_104 = scrape_104()
        logger.info(f"104: {len(jobs_104)} raw jobs")
    except Exception as e:
        logger.error(f"104 scraper failed: {e}")

    logger.info("Scraping LinkedIn...")
    jobs_linkedin = []
    try:
        jobs_linkedin = scrape_linkedin()
        logger.info(f"LinkedIn: {len(jobs_linkedin)} raw jobs")
    except Exception as e:
        logger.error(f"LinkedIn scraper failed: {e}")

    all_raw = jobs_104 + jobs_linkedin
    logger.info(f"Total raw: {len(all_raw)} jobs")

    # ── 2. Filter ──
    logger.info("Applying filters (salary ≥ 40k, top company)...")
    filtered = filter_jobs(all_raw, salary_threshold=40000)
    logger.info(f"After filter: {len(filtered)} jobs")

    # ── 3. Merge with history ──
    existing = load_existing_jobs()
    merged = merge_jobs(existing, filtered)

    # ── 4. Save data ──
    save_jobs(merged)

    # ── 5. Generate report ──
    logger.info("Generating HTML report...")
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    generate_html_report(merged, str(REPORT_FILE))
    logger.info(f"Report written to {REPORT_FILE}")

    # ── 6. Summary ──
    print(generate_summary(merged))

    # Write run metadata
    meta = {
        "last_run": datetime.now().isoformat(),
        "total_jobs": len(merged),
        "new_today": len(filtered),
    }
    Path("output/meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    logger.info("✅ Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
