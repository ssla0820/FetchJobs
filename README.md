# 🔍 Job Tracker — 104 + LinkedIn 職缺自動整合

每日自動抓取 104 與 LinkedIn 職缺，篩選後寫入 Google Sheet。

## 篩選條件
- 職稱：Software Engineer / AI Engineer（含中文）
- 薪資：月薪 ≥ 4 萬
- 公司：台灣百大企業 或 外商

---

## 📁 專案結構

```
job-tracker/
├── main.py                    # 主程式
├── requirements.txt
├── src/
│   ├── fetch_104.py           # 104 API 抓取
│   ├── fetch_linkedin.py      # LinkedIn RSS + Gmail
│   ├── company_filter.py      # 公司白名單篩選
│   └── sheets_writer.py       # Google Sheet 寫入
└── .github/
    └── workflows/
        └── daily.yml          # GitHub Actions（每天 09:00 台灣時間）
```

---

## 🚀 設定步驟

### Step 1：建立 Google Service Account

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 建立新專案（或選既有專案）
3. 啟用 API：
   - **Google Sheets API**
   - **Google Drive API**
4. 建立 Service Account：
   - IAM & Admin → Service Accounts → Create
   - 下載 JSON 金鑰
5. 把 JSON 金鑰內容複製備用（後面要貼到 GitHub Secrets）

### Step 2：共享 Google Sheet

1. 在 Google Sheet 分享設定中，加入 Service Account 的 email（格式：`xxx@xxx.iam.gserviceaccount.com`）
2. 權限設為**編輯者**
3. 複製 Sheet 的 ID（URL 中 `/d/` 後面那串）

### Step 3：設定 GitHub Secrets

在你的 GitHub Repo → Settings → Secrets and variables → Actions，新增：

| Secret 名稱 | 內容 |
|-------------|------|
| `SPREADSHEET_ID` | Google Sheet ID（URL 中的那串） |
| `SERVICE_ACCOUNT_JSON` | Service Account JSON 金鑰完整內容 |
| `GMAIL_SERVICE_ACCOUNT_JSON` | （可選）Gmail 授權 JSON，留空則跳過 Gmail 解析 |

### Step 4：Push 到 GitHub

```bash
git init
git add .
git commit -m "init job tracker"
git remote add origin https://github.com/你的帳號/job-tracker.git
git push -u origin main
```

GitHub Actions 會在每天台灣時間早上 9:00 自動執行。

---

## 🖱️ 手動執行

```bash
# 本地測試
export SPREADSHEET_ID="你的sheet id"
export SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
python main.py
```

或在 GitHub → Actions → Daily Job Tracker → Run workflow 手動觸發。

---

## 📊 Google Sheet 分頁說明

### 職缺清單
| 欄位 | 說明 |
|------|------|
| 日期 | 抓取日期 |
| 職稱 | 職位名稱 |
| 公司 | 公司名稱 |
| 地區 | 工作地點 |
| 工作型態 | Remote / Hybrid / On-site |
| 工作簡介 | JD 前 300 字 |
| JD 連結 | 原始連結 |
| 來源 | 104 / LinkedIn-RSS / LinkedIn-Gmail |

### 數據分析
自動統計：
- 總職缺數
- 來源分布
- 工作型態分布
- 地區 Top 10
- 公司排行 Top 20
- 近 14 天每日新增

---

## ⚠️ 注意事項

- LinkedIn RSS 職缺數量有限（每次約 10~25 筆），這是 LinkedIn 公開 RSS 的限制
- Gmail 解析需要 G Suite domain-wide delegation，個人 Gmail 帳號請跳過此功能，以 RSS 為主
- 104 API 每次最多掃 5 頁 × 4 個關鍵字 = 最多 600 筆，實際依薪資/公司篩選後會少很多
- 公司白名單在 `src/company_filter.py` 可自行新增
