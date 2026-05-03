"""
Google Sheets 更新模組
- 分頁 1：職缺清單
- 分頁 2：數據分析
"""

import json
import logging
from datetime import datetime
from collections import Counter

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

JOBS_SHEET = "職缺清單"
ANALYTICS_SHEET = "數據分析"

JOB_HEADERS = [
    "日期", "職稱", "公司", "地區", "工作型態", "工作簡介", "JD 連結", "來源"
]


def get_client(service_account_json: str) -> gspread.Client:
    info = json.loads(service_account_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


def get_existing_links(spreadsheet_id: str, service_account_json: str) -> set:
    """讀取現有職缺的連結，避免重複寫入"""
    try:
        client = get_client(service_account_json)
        ss = client.open_by_key(spreadsheet_id)
        ws = _get_or_create_worksheet(ss, JOBS_SHEET, JOB_HEADERS)
        records = ws.get_all_values()
        if len(records) <= 1:
            return set()
        # 第 7 欄（index 6）= JD 連結
        return {row[6] for row in records[1:] if len(row) > 6 and row[6]}
    except Exception as e:
        logger.error(f"❌ 讀取現有連結失敗: {e}")
        return set()


def write_jobs(
    spreadsheet_id: str,
    service_account_json: str,
    new_jobs: list[dict],
) -> int:
    """將新職缺插入 Google Sheet 第 2 列（最新在上）"""
    if not new_jobs:
        logger.info("✅ 無新職缺，跳過寫入")
        return 0

    client = get_client(service_account_json)
    ss = client.open_by_key(spreadsheet_id)
    ws = _get_or_create_worksheet(ss, JOBS_SHEET, JOB_HEADERS)

    rows = []
    for j in new_jobs:
        rows.append([
            j.get("date", ""),
            j.get("title", ""),
            j.get("company", ""),
            j.get("location", ""),
            j.get("work_type", ""),
            j.get("description", ""),
            j.get("link", ""),
            j.get("source", ""),
        ])

    # 在第 2 列插入（header 在第 1 列，最新資料在最上面）
    ws.insert_rows(rows, row=2)
    logger.info(f"✅ 寫入 {len(rows)} 筆職缺")
    return len(rows)


def update_analytics(spreadsheet_id: str, service_account_json: str) -> None:
    """重新計算並更新數據分析分頁"""
    client = get_client(service_account_json)
    ss = client.open_by_key(spreadsheet_id)

    # 讀取職缺清單
    jobs_ws = _get_or_create_worksheet(ss, JOBS_SHEET, JOB_HEADERS)
    all_rows = jobs_ws.get_all_values()
    jobs = all_rows[1:] if len(all_rows) > 1 else []

    analytics_ws = _get_or_create_worksheet(ss, ANALYTICS_SHEET, [])
    analytics_ws.clear()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = len(jobs)

    # 統計
    source_counter   = Counter()
    company_counter  = Counter()
    location_counter = Counter()
    worktype_counter = Counter()
    date_counter     = Counter()

    for row in jobs:
        if len(row) < 8:
            continue
        source_counter[row[7]]   += 1
        company_counter[row[2]]  += 1
        location_counter[row[3]] += 1
        worktype_counter[row[4]] += 1
        date_counter[row[0]]     += 1

    output = []

    # ── 標頭
    output.append(["📊 Job Tracker 數據分析", f"最後更新：{now}"])
    output.append([])
    output.append(["總職缺數", total])
    output.append([])

    # ── 來源分布
    output.append(["📌 來源分布", ""])
    output.append(["來源", "筆數"])
    for src, cnt in source_counter.most_common():
        output.append([src, cnt])
    output.append([])

    # ── 工作型態
    output.append(["🏢 工作型態", ""])
    output.append(["型態", "筆數"])
    for wt, cnt in worktype_counter.most_common():
        output.append([wt, cnt])
    output.append([])

    # ── 地區分布 Top 10
    output.append(["📍 地區分布 Top 10", ""])
    output.append(["地區", "筆數"])
    for loc, cnt in location_counter.most_common(10):
        if loc:
            output.append([loc, cnt])
    output.append([])

    # ── 公司出現次數 Top 20
    output.append(["🏆 公司排行 Top 20", ""])
    output.append(["公司", "筆數"])
    for company, cnt in company_counter.most_common(20):
        if company:
            output.append([company, cnt])
    output.append([])

    # ── 近 14 天每日新增
    output.append(["📅 近期每日新增", ""])
    output.append(["日期", "新增筆數"])
    for date, cnt in sorted(date_counter.items(), reverse=True)[:14]:
        output.append([date, cnt])

    analytics_ws.update("A1", output)
    _format_analytics(analytics_ws)
    logger.info("✅ 數據分析更新完成")


def _get_or_create_worksheet(ss: gspread.Spreadsheet, name: str, headers: list) -> gspread.Worksheet:
    try:
        ws = ss.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=name, rows=5000, cols=10)
        if headers:
            ws.append_row(headers)
            _format_header(ws)
    return ws


def _format_header(ws: gspread.Worksheet) -> None:
    """設定 header 列格式"""
    try:
        ws.format("A1:H1", {
            "backgroundColor": {"red": 0.18, "green": 0.18, "blue": 0.18},
            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            "horizontalAlignment": "CENTER",
        })
        ws.freeze(rows=1)
    except Exception:
        pass


def _format_analytics(ws: gspread.Worksheet) -> None:
    """分析頁簡單格式"""
    try:
        ws.format("A1:B1", {
            "textFormat": {"bold": True, "fontSize": 14},
        })
    except Exception:
        pass
