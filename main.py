"""
Job Tracker 主程式
Daily 執行流程：
1. 從 Google Sheet 讀取現有連結（避免重複）
2. 抓 104 職缺
3. 抓 LinkedIn RSS + Gmail 職缺
4. 寫入 Google Sheet 職缺清單
5. 更新數據分析分頁
"""

import os
import logging
import sys

from src.fetch_104 import fetch_104_jobs
from src.fetch_linkedin import fetch_linkedin_rss, fetch_linkedin_gmail
from src.sheets_writer import get_existing_links, write_jobs, update_analytics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    # ── 讀取環境變數
    spreadsheet_id       = os.environ.get("SPREADSHEET_ID", "")
    service_account_json = os.environ.get("SERVICE_ACCOUNT_JSON", "")
    gmail_creds_json     = os.environ.get("GMAIL_SERVICE_ACCOUNT_JSON", "")  # 可選

    if not spreadsheet_id or not service_account_json:
        logger.error("❌ 缺少必要環境變數：SPREADSHEET_ID 或 SERVICE_ACCOUNT_JSON")
        sys.exit(1)

    logger.info("🚀 Job Tracker 開始執行")

    # ── Step 1：取得現有連結
    logger.info("📋 讀取現有職缺連結...")
    existing_links = get_existing_links(spreadsheet_id, service_account_json)
    logger.info(f"  → 已有 {len(existing_links)} 筆")

    all_new_jobs = []

    # ── Step 2：104
    logger.info("=" * 50)
    logger.info("🟡 開始抓取 104 職缺")
    jobs_104 = fetch_104_jobs(existing_links)
    logger.info(f"  → 104 新增：{len(jobs_104)} 筆")
    all_new_jobs.extend(jobs_104)

    # ── Step 3：LinkedIn RSS
    logger.info("=" * 50)
    logger.info("🔵 開始抓取 LinkedIn RSS")
    jobs_li_rss = fetch_linkedin_rss(existing_links)
    logger.info(f"  → LinkedIn RSS 新增：{len(jobs_li_rss)} 筆")
    all_new_jobs.extend(jobs_li_rss)

    # ── Step 4：LinkedIn Gmail（可選）
    logger.info("=" * 50)
    logger.info("📧 開始抓取 LinkedIn Gmail")
    jobs_li_gmail = fetch_linkedin_gmail(existing_links, gmail_creds_json)
    logger.info(f"  → LinkedIn Gmail 新增：{len(jobs_li_gmail)} 筆")
    all_new_jobs.extend(jobs_li_gmail)

    # ── Step 5：寫入 Google Sheet
    logger.info("=" * 50)
    logger.info(f"📝 總共新增 {len(all_new_jobs)} 筆，寫入 Google Sheet...")
    written = write_jobs(spreadsheet_id, service_account_json, all_new_jobs)

    # ── Step 6：更新分析
    logger.info("📊 更新數據分析...")
    update_analytics(spreadsheet_id, service_account_json)

    logger.info("=" * 50)
    logger.info(f"✅ 完成！本次新增 {written} 筆職缺")


if __name__ == "__main__":
    main()
