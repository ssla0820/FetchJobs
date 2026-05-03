# 🧑‍💻 Tech Job Tracker — Taiwan

每日自動抓取 **104** 與 **LinkedIn** 的 Software Engineer / AI Engineer 職缺，  
篩選條件：薪資 > 40,000 / 公司為台灣百大或外商，並產生 GitHub Pages 報表。

---

## 📊 Live Report

> **`https://<your-username>.github.io/<repo-name>/`**

---

## 🗂️ 專案結構

```
job-tracker/
├── scripts/
│   ├── main.py              # 主程式（爬蟲 → 過濾 → 產生報表）
│   ├── scraper_104.py       # 104 人力銀行爬蟲
│   ├── scraper_linkedin.py  # LinkedIn 職缺爬蟲
│   ├── job_filter.py        # 薪資 & 公司過濾邏輯
│   └── report_generator.py  # HTML 報表產生器
├── output/
│   ├── index.html           # 靜態報表（GitHub Pages 呈現）
│   └── jobs_data.json       # 職缺資料（歷史累積）
├── .github/
│   └── workflows/
│       └── daily_job_tracker.yml  # GitHub Actions 排程
├── requirements.txt
└── README.md
```

---

## ⚙️ 設定步驟

### 1. Fork / Clone 這個 Repo

```bash
git clone https://github.com/<your-username>/job-tracker.git
cd job-tracker
```

### 2. 啟用 GitHub Pages

到 `Settings → Pages → Source`，選擇 **Deploy from a branch** → Branch: `gh-pages`

### 3. 啟用 GitHub Actions

到 `Actions` tab → 點選 **Enable GitHub Actions**  
第一次可以手動觸發：`Actions → Daily Job Tracker → Run workflow`

### 4. 自動排程

GitHub Actions 設定為每天 **08:00 台灣時間 (00:00 UTC)** 自動執行

---

## 🔍 篩選邏輯

| 條件 | 設定 |
|------|------|
| 職位類型 | Software Engineer、AI Engineer、ML Engineer、資料科學家... |
| 薪資門檻 | 月薪 ≥ 40,000 TWD（面議職缺保留但標記） |
| 公司類型 | 台灣前百大企業 **或** 外商/跨國企業 |
| 來源 | 104 人力銀行 + LinkedIn |

---

## 📋 報表功能

### Tab 1: 數據分析
- 職缺總數、外商比例、薪資分布
- 地區分布圓餅圖
- 職稱類型長條圖
- 近 7 日職缺趨勢折線圖

### Tab 2: 職缺清單
- 欄位：日期 / 來源 / 職稱 / 公司 / 類型 / 地區 / 工作型態 / 薪資 / 工作簡介 / 連結
- 即時搜尋（職稱 / 公司）
- 篩選：來源、公司類型

---

## 🛠️ 本地執行

```bash
pip install -r requirements.txt
cd scripts
python main.py
# → 報表輸出至 output/index.html
```

---

## 📌 注意事項

- 爬蟲有加入適當的 delay 避免被封鎖
- LinkedIn 使用 public guest API，無需登入
- 職缺歷史最多保留 500 筆最新資料
- 如遇到爬蟲失敗，GitHub Actions log 會顯示錯誤訊息

---

## 📜 License

MIT
