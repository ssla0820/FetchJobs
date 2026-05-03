"""
公司篩選模組
條件：台灣百大企業 OR 外商公司
"""

import re

# ============================================================
# 台灣百大企業（CommonWealth / Forbes 台灣版）
# ============================================================
TW_TOP100 = {
    # 科技 / 半導體
    "台積電", "tsmc", "taiwan semiconductor",
    "聯發科", "mediatek",
    "鴻海", "foxconn", "hon hai",
    "廣達", "quanta",
    "仁寶", "compal",
    "緯創", "wistron",
    "英業達", "inventec",
    "和碩", "pegatron",
    "瑞昱", "realtek",
    "聯詠", "novatek",
    "日月光", "ase",
    "南亞科", "nanya",
    "力積電", "psmc",
    "世界先進", "vanguard",
    "聯電", "umc",
    "微星", "msi",
    "技嘉", "gigabyte",
    "華碩", "asus",
    "宏碁", "acer",
    "威盛", "via",
    "義隆", "elan",
    "瑞鼎", "raydium",
    "矽統", "sis",
    "智原", "faraday",
    "創意", "global unichip",
    "金麗科", "kinly",
    "神達", "mitac",
    "明基", "benq",
    "友達", "au optronics", "auo",
    "群創", "innolux",
    "元太", "e ink",
    "台達電", "delta electronics",
    "研華", "advantech",
    "光寶", "lite-on",
    "正威", "cheng uei",
    "台灣大哥大", "taiwan mobile",
    "中華電信", "chunghwa telecom",
    "遠傳", "far eastone",
    "富邦", "fubon",
    "國泰", "cathay",
    "玉山銀行", "e.sun",
    "台新銀行", "taishin",
    "中信銀行", "ctbc",
    "兆豐", "mega financial",
    "第一銀行", "first bank",
    "合庫", "taiwan cooperative",
    "統一", "uni-president",
    "全聯",
    "潤泰", "ruentex",
    "遠東", "far eastern",
    "台塑", "formosa plastics",
    "南亞", "nan ya",
    "台化", "formosa chemicals",
    "麗寶",
    "欣興", "unimicron",
    "華通", "tripod",
    "臻鼎", "zhen ding",
    "健鼎", "tripod technology",
    "大立光", "largan",
    "玉晶光", "genius electronic optical",
    "台揚", "taiyen",
    "雷科",
    "振鋒",
    "旺宏", "macronix",
    "華邦", "winbond",
    "群聯", "phison",
    "威剛", "adata",
    "創見", "transcend",
    "正崴", "foxlink",
    "台表科",
    "可成", "catcher",
    "嘉澤", "lotes",
    "中磊", "sercomm",
    "智邦", "accton",
    "友訊", "d-link",
    "合勤", "zyxel",
    "網路家庭", "pchome",
    "momo",
    "91app",
    "104",
    "1111",
    "趨勢科技", "trend micro",
    "訊連", "cyberlink",
    "鈊象", "igt",
    "雷亞", "rayark",
    "傑思", "jas",
    "天奕達", "tian yi da",
    "緯德", "wistron ics",
}

# ============================================================
# 外商關鍵字（有台灣據點的跨國企業）
# ============================================================
FOREIGN_COMPANIES = {
    # 美國科技
    "google", "alphabet",
    "microsoft", "微軟",
    "apple", "蘋果",
    "amazon", "aws",
    "meta", "facebook",
    "netflix",
    "nvidia", "輝達",
    "intel", "英特爾",
    "amd",
    "qualcomm", "高通",
    "broadcom", "博通",
    "arm",
    "ibm",
    "oracle",
    "salesforce",
    "servicenow",
    "workday",
    "cisco", "思科",
    "hp", "hewlett",
    "dell",
    "vmware",
    "sap",
    "siemens",
    "bosch",
    "abb",
    "emerson",
    "honeywell",
    # 金融
    "jpmorgan", "j.p. morgan",
    "goldman sachs",
    "morgan stanley",
    "citibank", "花旗",
    "hsbc", "匯豐",
    "standard chartered", "渣打",
    "ubs",
    "blackrock",
    "jane street",
    "citadel",
    # 半導體 / 設備
    "asml",
    "applied materials", "amat",
    "lam research",
    "kla",
    "synopsys",
    "cadence",
    "mentor",
    "ansys",
    # 台灣常見外商
    "infosys",
    "cognizant",
    "accenture", "埃森哲",
    "deloitte", "勤業眾信",
    "pwc", "資誠",
    "kpmg", "安侯建業",
    "ey", "ernst",
    "mckinsey",
    "bain",
    "boston consulting", "bcg",
    "garmin",
    "moxa",
    "abb",
    "schneider electric",
    "ericsson", "愛立信",
    "nokia",
    "samsung", "三星",
    "lg",
    "sk hynix",
    "micron", "美光",
    "western digital", "wd",
    "seagate",
    "hitachi",
    "toshiba",
    "renesas",
    "nxp",
    "infineon",
    "st microelectronics", "stmicro",
    "texas instruments", "ti",
    "analog devices", "adi",
    "maxim",
    "marvell",
    "xilinx",
    "altera",
    "lattice",
    "microchip",
    "on semiconductor",
    "vishay",
    # 電商 / 新創
    "shopify",
    "grab",
    "gojek",
    "bytedance", "tiktok", "字節跳動",
    "line",
    "rakuten", "樂天",
    "shopee", "蝦皮",
    "lazada",
    "agoda",
    "booking.com",
    "airbnb",
    "uber",
    "lyft",
    "stripe",
    "paypal",
    "square",
    "twilio",
    "zendesk",
    "atlassian",
    "github",
    "gitlab",
    "docker",
    "datadog",
    "splunk",
    "crowdstrike",
    "palo alto",
    "fortinet",
}

ALL_TARGET = TW_TOP100 | FOREIGN_COMPANIES


def is_target_company(company_name: str) -> bool:
    """
    判斷是否為目標公司（台灣百大 or 外商）。
    模糊比對：只要公司名稱包含關鍵字即符合。
    """
    if not company_name:
        return False

    name_lower = company_name.lower().strip()

    for keyword in ALL_TARGET:
        if keyword.lower() in name_lower:
            return True

    return False


def get_company_type(company_name: str) -> str:
    """回傳公司類型標籤"""
    if not company_name:
        return "其他"
    name_lower = company_name.lower()
    for kw in FOREIGN_COMPANIES:
        if kw.lower() in name_lower:
            return "外商"
    for kw in TW_TOP100:
        if kw.lower() in name_lower:
            return "台灣百大"
    return "其他"
