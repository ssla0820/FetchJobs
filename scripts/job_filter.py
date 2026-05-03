"""
Job Filter & Company Classifier
Filters jobs by salary threshold and company type (Top 100 TW or foreign)
"""

import re
import logging

logger = logging.getLogger(__name__)

# ── Foreign / MNC companies operating in Taiwan ──────────────────────────────
FOREIGN_COMPANIES = {
    # US Tech
    "Google", "Microsoft", "Amazon", "Meta", "Apple", "Netflix", "Uber",
    "Salesforce", "Oracle", "SAP", "IBM", "Cisco", "Dell", "HP", "HPE",
    "Intel", "Qualcomm", "NVIDIA", "Nvidia", "AMD", "Broadcom", "Marvell",
    "Arm", "ARM", "Synopsys", "Cadence", "Ansys", "Mentor",
    # US Finance / Consulting
    "Goldman Sachs", "JPMorgan", "Morgan Stanley", "Citi", "HSBC",
    "Accenture", "Deloitte", "McKinsey", "BCG", "Bain", "PwC", "EY", "KPMG",
    # European Tech
    "ASML", "NXP", "Philips", "Siemens", "Bosch", "Ericsson", "Nokia",
    "ABB", "Schneider", "Infineon",
    # Japan / Korea
    "Sony", "Panasonic", "Hitachi", "Fujitsu", "NEC", "Toshiba",
    "Samsung", "LG", "SK Hynix",
    # Other notable
    "Shopee", "Grab", "Sea", "Garena", "ByteDance", "Tiktok", "TikTok",
    "Rakuten", "LINE", "LINE Taiwan", "Mercari",
    # Semiconductor
    "TSMC", "台積電", "ASE", "日月光", "MediaTek", "聯發科",
    # Cloud / SaaS
    "Workday", "ServiceNow", "Snowflake", "Databricks", "Stripe",
}

# ── Taiwan Top 100 companies (revenue/market cap leaders) ────────────────────
TAIWAN_TOP100 = {
    # Semiconductor
    "台積電", "TSMC", "聯發科", "MediaTek", "日月光", "ASE", "聯電", "UMC",
    "瑞昱", "Realtek", "矽力杰", "創意電子", "世界先進", "力積電",
    # Electronics / EMS
    "鴻海", "Foxconn", "廣達", "Quanta", "仁寶", "Compal", "英業達", "Inventec",
    "緯創", "Wistron", "和碩", "Pegatron", "技嘉", "Gigabyte", "華碩", "ASUS",
    "宏碁", "Acer", "微星", "MSI",
    # Networking / Storage
    "友訊", "D-Link", "瑞昱", "威剛", "ADATA", "群聯", "Phison",
    # Displays
    "友達", "AUO", "群創", "Innolux",
    # Telecom
    "中華電信", "Chunghwa Telecom", "台灣大哥大", "Taiwan Mobile", "遠傳", "FarEasTone",
    # Finance
    "國泰金", "富邦金", "中信金", "兆豐金", "合庫金", "第一金", "玉山金",
    # IT Services
    "緯軟", "資拓宏宇", "勤業眾信", "叡揚", "精誠", "Systex", "遠傳FET",
    # E-commerce / Internet
    "PCHome", "momo", "91APP", "91app", "KKBOX", "17LIVE",
    # Others
    "台塑", "台化", "南亞", "奇美", "正新", "台達電", "Delta",
    "研華", "Advantech", "光寶", "Liteon", "士林電機",
}

FOREIGN_KEYWORDS = [
    "外商", "跨國", "international", "global", "worldwide",
    "Japan", "US", "USA", "Europe", "Korea", "Singapore",
    "美商", "日商", "韓商", "歐商", "星商",
]


def classify_company(company: str, industry: str = "", is_foreign_hint: bool = False) -> dict:
    """
    Returns dict with:
      - is_top100_tw: bool
      - is_foreign: bool
      - passes_filter: bool (either top100 or foreign)
      - company_type_label: str
    """
    c = company.strip()
    c_lower = c.lower()

    is_top100_tw = any(name.lower() in c_lower or c_lower in name.lower()
                       for name in TAIWAN_TOP100)

    is_foreign = (
        is_foreign_hint
        or any(name.lower() in c_lower or c_lower in name.lower() for name in FOREIGN_COMPANIES)
        or any(kw.lower() in c_lower for kw in FOREIGN_KEYWORDS)
        or any(kw.lower() in industry.lower() for kw in FOREIGN_KEYWORDS)
        # Heuristic: English-only company name → likely foreign
        or (bool(re.match(r'^[A-Za-z\s\.\,\-&]+$', c)) and len(c) > 3)
    )

    passes = is_top100_tw or is_foreign

    if is_foreign and is_top100_tw:
        label = "外商 / 台灣百大"
    elif is_foreign:
        label = "外商"
    elif is_top100_tw:
        label = "台灣百大"
    else:
        label = "其他"

    return {
        "is_top100_tw": is_top100_tw,
        "is_foreign": is_foreign,
        "passes_filter": passes,
        "company_type_label": label,
    }


def parse_salary_min(salary_str: str) -> int:
    """
    Try to parse the minimum monthly salary from a salary string.
    Returns 0 if cannot determine.
    """
    if not salary_str or salary_str in ("面議", "依職缺內容", "依面議"):
        return 0

    # Remove commas
    s = salary_str.replace(",", "").replace("，", "")

    # Pattern: "月薪 40,000 ~ 80,000" or "40000-80000"
    nums = re.findall(r'\d+', s)
    if not nums:
        return 0

    # Convert to int
    values = [int(n) for n in nums]

    # If yearly (> 500000), convert to monthly
    min_val = min(values)
    if min_val > 200000:
        min_val = min_val // 12

    return min_val


def filter_jobs(jobs: list[dict], salary_threshold: int = 40000) -> list[dict]:
    """
    Apply all filters:
    1. Salary ≥ threshold (skip if 面議, keep with warning)
    2. Company is Top 100 TW or foreign
    3. Role is software/AI engineering related
    """
    ROLE_KEYWORDS = [
        "software", "engineer", "developer", "programmer",
        "ai ", " ai", "artificial intelligence",
        "machine learning", " ml", "ml ",
        "data scientist", "data engineer",
        "backend", "frontend", "full stack", "fullstack",
        "devops", "sre", "platform",
        "工程師", "開發", "資料科學", "機器學習", "人工智慧",
        "後端", "前端", "全端", "雲端",
    ]

    filtered = []
    stats = {"total": len(jobs), "passed": 0, "blocked_salary": 0,
             "blocked_company": 0, "blocked_role": 0}

    for job in jobs:
        title_lower = job.get("title", "").lower()
        salary_str = job.get("salary", "")
        company = job.get("company", "")
        industry = job.get("industry", "")
        is_foreign_hint = job.get("is_foreign_hint", False)

        # ── Role filter ──
        if not any(kw in title_lower for kw in ROLE_KEYWORDS):
            stats["blocked_role"] += 1
            continue

        # ── Salary filter ──
        min_salary = parse_salary_min(salary_str)
        salary_ok = (min_salary == 0) or (min_salary >= salary_threshold)
        # For 面議, we keep but flag
        if not salary_ok:
            stats["blocked_salary"] += 1
            continue

        # ── Company filter ──
        company_info = classify_company(company, industry, is_foreign_hint)
        if not company_info["passes_filter"]:
            stats["blocked_company"] += 1
            continue

        # Attach classification info
        job["company_type"] = company_info["company_type_label"]
        job["is_foreign"] = company_info["is_foreign"]
        job["is_top100_tw"] = company_info["is_top100_tw"]
        job["salary_min_parsed"] = min_salary

        filtered.append(job)
        stats["passed"] += 1

    logger.info(f"Filter stats: {stats}")
    return filtered


if __name__ == "__main__":
    # Quick test
    test_jobs = [
        {"title": "Software Engineer", "salary": "月薪 50,000 ~ 80,000", "company": "Google",
         "industry": "", "is_foreign_hint": True},
        {"title": "軟體工程師", "salary": "月薪 35,000", "company": "某小公司",
         "industry": "", "is_foreign_hint": False},
        {"title": "AI Engineer", "salary": "面議", "company": "台積電",
         "industry": "", "is_foreign_hint": False},
    ]
    results = filter_jobs(test_jobs)
    print(f"Passed: {len(results)}/{len(test_jobs)}")
    for r in results:
        print(f"  {r['title']} @ {r['company']} → {r['company_type']}")
