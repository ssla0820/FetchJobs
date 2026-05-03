"""
HTML Report Generator
Generates a beautiful two-tab HTML report:
  Tab 1: 數據分析 (Analytics Dashboard)
  Tab 2: 職缺清單 (Job Listings)
"""

import json
import logging
from datetime import datetime
from collections import Counter, defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)


def generate_analytics_data(jobs: list[dict]) -> dict:
    """Compute analytics from job list."""
    total = len(jobs)
    by_source = Counter(j.get("source", "Unknown") for j in jobs)
    by_company_type = Counter(j.get("company_type", "其他") for j in jobs)
    by_location = Counter(j.get("location", "不明") for j in jobs)

    # Simplify locations
    location_simplified = Counter()
    for job in jobs:
        loc = job.get("location", "不明")
        if "台北" in loc or "Taipei" in loc:
            location_simplified["台北"] += 1
        elif "新北" in loc:
            location_simplified["新北"] += 1
        elif "桃園" in loc:
            location_simplified["桃園"] += 1
        elif "新竹" in loc or "Hsinchu" in loc:
            location_simplified["新竹"] += 1
        elif "台中" in loc:
            location_simplified["台中"] += 1
        elif "台南" in loc:
            location_simplified["台南"] += 1
        elif "高雄" in loc:
            location_simplified["高雄"] += 1
        else:
            location_simplified["其他"] += 1

    # Top companies
    by_company = Counter(j.get("company", "") for j in jobs)
    top_companies = by_company.most_common(10)

    # Title keyword analysis
    title_keywords = Counter()
    kw_map = {
        "Software Engineer": ["software engineer", "軟體工程師"],
        "AI / ML Engineer": ["ai engineer", "machine learning", "ml engineer", "ai工程師", "機器學習"],
        "Data Scientist": ["data scientist", "資料科學家", "data engineer"],
        "Backend Engineer": ["backend", "後端"],
        "Frontend Engineer": ["frontend", "前端"],
        "Full Stack": ["full stack", "fullstack", "全端"],
        "DevOps / SRE": ["devops", "sre", "platform engineer", "雲端"],
    }
    for job in jobs:
        title_lower = job.get("title", "").lower()
        matched = False
        for label, keywords in kw_map.items():
            if any(kw in title_lower for kw in keywords):
                title_keywords[label] += 1
                matched = True
                break
        if not matched:
            title_keywords["其他工程師"] += 1

    # Salary distribution
    salary_buckets = {"40k~60k": 0, "60k~80k": 0, "80k~100k": 0, "100k+": 0, "面議": 0}
    for job in jobs:
        sal = job.get("salary_min_parsed", 0)
        if sal == 0:
            salary_buckets["面議"] += 1
        elif sal < 60000:
            salary_buckets["40k~60k"] += 1
        elif sal < 80000:
            salary_buckets["60k~80k"] += 1
        elif sal < 100000:
            salary_buckets["80k~100k"] += 1
        else:
            salary_buckets["100k+"] += 1

    # Jobs by date (last 7 days)
    date_counts = defaultdict(int)
    for job in jobs:
        date = job.get("date", "")[:10]  # YYYY-MM-DD
        if date:
            date_counts[date] += 1
    date_trend = sorted(date_counts.items())[-7:]

    return {
        "total": total,
        "by_source": dict(by_source),
        "by_company_type": dict(by_company_type),
        "by_location": dict(location_simplified),
        "top_companies": top_companies,
        "by_title_type": dict(title_keywords),
        "salary_buckets": salary_buckets,
        "date_trend": date_trend,
    }


def generate_html_report(jobs: list[dict], output_path: str = "output/index.html") -> str:
    """Generate the full HTML report."""
    analytics = generate_analytics_data(jobs)
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Sort jobs by date desc
    sorted_jobs = sorted(jobs, key=lambda x: x.get("date", ""), reverse=True)

    jobs_html = _render_job_rows(sorted_jobs)
    analytics_js_data = json.dumps(analytics, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🧑‍💻 Tech Job Tracker · Taiwan</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #0a0e1a;
    --surface: #111827;
    --surface2: #1a2235;
    --border: #1e2d45;
    --accent: #3b82f6;
    --accent2: #06b6d4;
    --accent3: #8b5cf6;
    --green: #10b981;
    --yellow: #f59e0b;
    --red: #ef4444;
    --text: #e2e8f0;
    --text-muted: #64748b;
    --text-dim: #94a3b8;
    --radius: 12px;
    --radius-sm: 8px;
    --shadow: 0 4px 24px rgba(0,0,0,0.4);
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: 'Space Grotesk', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    background-image: radial-gradient(ellipse at 20% 0%, rgba(59,130,246,0.08) 0%, transparent 50%),
                      radial-gradient(ellipse at 80% 0%, rgba(139,92,246,0.06) 0%, transparent 50%);
  }}

  /* ── Header ── */
  .header {{
    padding: 32px 40px 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid var(--border);
    padding-bottom: 0;
  }}
  .logo {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .logo-icon {{
    width: 40px; height: 40px;
    background: linear-gradient(135deg, var(--accent), var(--accent3));
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
  }}
  .logo h1 {{
    font-size: 20px; font-weight: 700;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
  }}
  .logo p {{
    font-size: 12px; color: var(--text-muted); font-family: 'JetBrains Mono', monospace;
  }}
  .update-badge {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px; color: var(--text-muted);
    background: var(--surface2);
    padding: 6px 14px; border-radius: 20px;
    border: 1px solid var(--border);
  }}

  /* ── Tabs ── */
  .tabs {{
    display: flex; gap: 0;
    padding: 0 40px;
    border-bottom: 1px solid var(--border);
    margin-top: 0;
  }}
  .tab {{
    padding: 16px 28px;
    cursor: pointer;
    font-weight: 500; font-size: 14px;
    color: var(--text-muted);
    border-bottom: 2px solid transparent;
    transition: all 0.2s;
    display: flex; align-items: center; gap: 8px;
    position: relative; top: 1px;
  }}
  .tab:hover {{ color: var(--text); }}
  .tab.active {{
    color: var(--accent);
    border-bottom-color: var(--accent);
  }}
  .tab-count {{
    background: var(--accent);
    color: white; font-size: 11px;
    padding: 2px 8px; border-radius: 10px;
    font-weight: 600;
  }}

  /* ── Main Content ── */
  .content {{ padding: 32px 40px; }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}

  /* ── Analytics ── */
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px; margin-bottom: 32px;
  }}
  .stat-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 24px;
    position: relative; overflow: hidden;
    transition: border-color 0.2s, transform 0.2s;
  }}
  .stat-card:hover {{ border-color: var(--accent); transform: translateY(-2px); }}
  .stat-card::before {{
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  }}
  .stat-card.blue::before {{ background: linear-gradient(90deg, var(--accent), var(--accent2)); }}
  .stat-card.purple::before {{ background: linear-gradient(90deg, var(--accent3), var(--accent)); }}
  .stat-card.green::before {{ background: linear-gradient(90deg, var(--green), var(--accent2)); }}
  .stat-card.yellow::before {{ background: linear-gradient(90deg, var(--yellow), var(--green)); }}
  .stat-label {{
    font-size: 12px; color: var(--text-muted); text-transform: uppercase;
    letter-spacing: 0.08em; margin-bottom: 12px; font-weight: 600;
  }}
  .stat-value {{
    font-size: 36px; font-weight: 700; line-height: 1;
    font-family: 'JetBrains Mono', monospace;
    background: linear-gradient(135deg, var(--text), var(--text-dim));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
  }}
  .stat-sub {{ font-size: 12px; color: var(--text-muted); margin-top: 8px; }}

  .charts-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px; margin-bottom: 20px;
  }}
  .charts-grid-3 {{
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 20px;
  }}
  .chart-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 24px;
  }}
  .chart-title {{
    font-size: 14px; font-weight: 600;
    color: var(--text-dim); margin-bottom: 20px;
    display: flex; align-items: center; gap: 8px;
  }}
  .chart-title span {{ font-size: 16px; }}
  .chart-wrap {{ position: relative; height: 220px; }}

  /* ── Job Table ── */
  .toolbar {{
    display: flex; gap: 12px; align-items: center; margin-bottom: 20px;
  }}
  .search-input {{
    flex: 1; max-width: 360px;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 10px 16px;
    color: var(--text); font-family: inherit; font-size: 14px;
    outline: none; transition: border-color 0.2s;
  }}
  .search-input:focus {{ border-color: var(--accent); }}
  .search-input::placeholder {{ color: var(--text-muted); }}
  .filter-select {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 10px 14px;
    color: var(--text); font-family: inherit; font-size: 14px;
    outline: none; cursor: pointer;
  }}
  .result-count {{
    margin-left: auto;
    font-size: 13px; color: var(--text-muted);
    font-family: 'JetBrains Mono', monospace;
  }}

  .job-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }}
  .job-table th {{
    text-align: left; padding: 12px 16px;
    font-size: 11px; font-weight: 600;
    color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }}
  .job-table td {{
    padding: 14px 16px;
    border-bottom: 1px solid rgba(30,45,69,0.6);
    vertical-align: top;
  }}
  .job-table tr:hover td {{ background: rgba(59,130,246,0.04); }}

  .job-title a {{
    color: var(--text); text-decoration: none; font-weight: 600;
    transition: color 0.2s;
  }}
  .job-title a:hover {{ color: var(--accent); }}

  .badge {{
    display: inline-flex; align-items: center;
    padding: 3px 10px; border-radius: 20px;
    font-size: 11px; font-weight: 600;
    white-space: nowrap;
  }}
  .badge-104 {{ background: rgba(239,68,68,0.15); color: #fca5a5; border: 1px solid rgba(239,68,68,0.3); }}
  .badge-linkedin {{ background: rgba(59,130,246,0.15); color: #93c5fd; border: 1px solid rgba(59,130,246,0.3); }}
  .badge-foreign {{ background: rgba(139,92,246,0.15); color: #c4b5fd; border: 1px solid rgba(139,92,246,0.3); }}
  .badge-top100 {{ background: rgba(16,185,129,0.15); color: #6ee7b7; border: 1px solid rgba(16,185,129,0.3); }}
  .badge-remote {{ background: rgba(245,158,11,0.15); color: #fcd34d; border: 1px solid rgba(245,158,11,0.3); }}

  .description-cell {{
    max-width: 320px; color: var(--text-dim); font-size: 12px; line-height: 1.5;
  }}
  .description-text {{
    overflow: hidden; display: -webkit-box;
    -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  }}
  .expand-btn {{
    color: var(--accent); cursor: pointer; font-size: 11px;
    background: none; border: none; padding: 0; margin-top: 4px;
    font-family: inherit;
  }}

  .link-btn {{
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(59,130,246,0.1); color: var(--accent);
    border: 1px solid rgba(59,130,246,0.3);
    padding: 6px 12px; border-radius: var(--radius-sm);
    text-decoration: none; font-size: 12px; font-weight: 500;
    transition: all 0.2s; white-space: nowrap;
  }}
  .link-btn:hover {{ background: rgba(59,130,246,0.2); }}

  .no-results {{
    text-align: center; padding: 60px;
    color: var(--text-muted); font-size: 14px;
  }}

  /* ── Responsive ── */
  @media (max-width: 1024px) {{
    .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .charts-grid, .charts-grid-3 {{ grid-template-columns: 1fr; }}
    .header, .tabs, .content {{ padding-left: 20px; padding-right: 20px; }}
  }}
</style>
</head>
<body>

<div class="header">
  <div class="logo">
    <div class="logo-icon">🧑‍💻</div>
    <div>
      <h1>Tech Job Tracker</h1>
      <p>104 + LinkedIn · Software & AI Engineering · Taiwan</p>
    </div>
  </div>
  <div class="update-badge">⟳ Updated {updated_at}</div>
</div>

<div class="tabs">
  <div class="tab active" onclick="switchTab('analytics')">
    <span>📊</span> 數據分析
  </div>
  <div class="tab" onclick="switchTab('jobs')">
    <span>📋</span> 職缺清單
    <span class="tab-count">{len(jobs)}</span>
  </div>
</div>

<!-- ═══ TAB 1: Analytics ═══ -->
<div class="content">
<div id="tab-analytics" class="tab-panel active">

  <div class="stats-grid">
    <div class="stat-card blue">
      <div class="stat-label">總職缺數</div>
      <div class="stat-value">{analytics['total']}</div>
      <div class="stat-sub">Software + AI Engineering</div>
    </div>
    <div class="stat-card purple">
      <div class="stat-label">外商職缺</div>
      <div class="stat-value">{analytics['by_company_type'].get('外商', 0) + analytics['by_company_type'].get('外商 / 台灣百大', 0)}</div>
      <div class="stat-sub">跨國企業</div>
    </div>
    <div class="stat-card green">
      <div class="stat-label">台灣百大</div>
      <div class="stat-value">{analytics['by_company_type'].get('台灣百大', 0)}</div>
      <div class="stat-sub">台灣前百大企業</div>
    </div>
    <div class="stat-card yellow">
      <div class="stat-label">薪資 60k+</div>
      <div class="stat-value">{analytics['salary_buckets'].get('60k~80k', 0) + analytics['salary_buckets'].get('80k~100k', 0) + analytics['salary_buckets'].get('100k+', 0)}</div>
      <div class="stat-sub">月薪 60,000 TWD 以上</div>
    </div>
  </div>

  <div class="charts-grid">
    <div class="chart-card">
      <div class="chart-title"><span>📍</span> 地區分布</div>
      <div class="chart-wrap"><canvas id="chartLocation"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title"><span>💰</span> 薪資區間分布</div>
      <div class="chart-wrap"><canvas id="chartSalary"></canvas></div>
    </div>
  </div>

  <div class="charts-grid-3">
    <div class="chart-card">
      <div class="chart-title"><span>🏷️</span> 職稱類型</div>
      <div class="chart-wrap"><canvas id="chartTitle"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title"><span>🏢</span> 公司類型</div>
      <div class="chart-wrap"><canvas id="chartCompany"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title"><span>📅</span> 近 7 日職缺趨勢</div>
      <div class="chart-wrap"><canvas id="chartTrend"></canvas></div>
    </div>
  </div>

</div>

<!-- ═══ TAB 2: Job List ═══ -->
<div id="tab-jobs" class="tab-panel">

  <div class="toolbar">
    <input class="search-input" type="text" placeholder="🔍 搜尋職稱、公司..." oninput="filterJobs()">
    <select class="filter-select" onchange="filterJobs()" id="sourceFilter">
      <option value="">全部來源</option>
      <option value="104">104</option>
      <option value="LinkedIn">LinkedIn</option>
    </select>
    <select class="filter-select" onchange="filterJobs()" id="typeFilter">
      <option value="">全部類型</option>
      <option value="外商">外商</option>
      <option value="台灣百大">台灣百大</option>
    </select>
    <div class="result-count" id="resultCount">{len(jobs)} 筆</div>
  </div>

  <table class="job-table" id="jobTable">
    <thead>
      <tr>
        <th>日期</th>
        <th>來源</th>
        <th>職稱</th>
        <th>公司</th>
        <th>類型</th>
        <th>地區</th>
        <th>工作型態</th>
        <th>薪資</th>
        <th>工作簡介</th>
        <th>連結</th>
      </tr>
    </thead>
    <tbody id="jobBody">
{jobs_html}
    </tbody>
  </table>
  <div class="no-results" id="noResults" style="display:none">
    😕 沒有符合條件的職缺
  </div>

</div>
</div>

<script>
const analyticsData = {analytics_js_data};

// ── Tab switching ──
function switchTab(tab) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  event.currentTarget.classList.add('active');
  document.getElementById('tab-' + tab).classList.add('active');
  if (tab === 'analytics') initCharts();
}}

// ── Job filtering ──
function filterJobs() {{
  const search = document.querySelector('.search-input').value.toLowerCase();
  const source = document.getElementById('sourceFilter').value;
  const type = document.getElementById('typeFilter').value;
  const rows = document.querySelectorAll('#jobBody tr');
  let visible = 0;

  rows.forEach(row => {{
    const text = row.textContent.toLowerCase();
    const rowSource = row.dataset.source || '';
    const rowType = row.dataset.type || '';
    const matchSearch = !search || text.includes(search);
    const matchSource = !source || rowSource.includes(source);
    const matchType = !type || rowType.includes(type);

    if (matchSearch && matchSource && matchType) {{
      row.style.display = '';
      visible++;
    }} else {{
      row.style.display = 'none';
    }}
  }});

  document.getElementById('resultCount').textContent = visible + ' 筆';
  document.getElementById('noResults').style.display = visible === 0 ? 'block' : 'none';
}}

// ── Description expand ──
function toggleDesc(btn) {{
  const el = btn.previousElementSibling;
  if (el.style.webkitLineClamp === 'unset') {{
    el.style.webkitLineClamp = '2';
    btn.textContent = '展開';
  }} else {{
    el.style.webkitLineClamp = 'unset';
    btn.textContent = '收起';
  }}
}}

// ── Charts ──
let chartsInit = false;
function initCharts() {{
  if (chartsInit) return;
  chartsInit = true;

  const dark = {{
    color: '#94a3b8',
    grid: 'rgba(30,45,69,0.8)',
  }};

  Chart.defaults.color = dark.color;
  Chart.defaults.borderColor = dark.grid;

  const palette = ['#3b82f6','#8b5cf6','#06b6d4','#10b981','#f59e0b','#ef4444','#ec4899','#14b8a6'];

  // Location donut
  const locData = analyticsData.by_location;
  new Chart(document.getElementById('chartLocation'), {{
    type: 'doughnut',
    data: {{
      labels: Object.keys(locData),
      datasets: [{{ data: Object.values(locData), backgroundColor: palette,
        borderColor: '#111827', borderWidth: 2 }}]
    }},
    options: {{ plugins: {{ legend: {{ position: 'right', labels: {{ boxWidth: 12 }} }} }}, cutout: '60%' }}
  }});

  // Salary bar
  const salData = analyticsData.salary_buckets;
  new Chart(document.getElementById('chartSalary'), {{
    type: 'bar',
    data: {{
      labels: Object.keys(salData),
      datasets: [{{ data: Object.values(salData), backgroundColor: palette,
        borderRadius: 6, borderSkipped: false }}]
    }},
    options: {{
      plugins: {{ legend: {{ display: false }} }},
      scales: {{ x: {{ grid: {{ display: false }} }}, y: {{ grid: {{ color: dark.grid }} }} }}
    }}
  }});

  // Title type bar (horizontal)
  const titleData = analyticsData.by_title_type;
  new Chart(document.getElementById('chartTitle'), {{
    type: 'bar',
    data: {{
      labels: Object.keys(titleData),
      datasets: [{{ data: Object.values(titleData), backgroundColor: palette,
        borderRadius: 4, borderSkipped: false }}]
    }},
    options: {{
      indexAxis: 'y',
      plugins: {{ legend: {{ display: false }} }},
      scales: {{ x: {{ grid: {{ color: dark.grid }} }}, y: {{ grid: {{ display: false }} }} }}
    }}
  }});

  // Company type donut
  const compData = analyticsData.by_company_type;
  new Chart(document.getElementById('chartCompany'), {{
    type: 'doughnut',
    data: {{
      labels: Object.keys(compData),
      datasets: [{{ data: Object.values(compData), backgroundColor: palette,
        borderColor: '#111827', borderWidth: 2 }}]
    }},
    options: {{ plugins: {{ legend: {{ position: 'right', labels: {{ boxWidth: 12 }} }} }}, cutout: '60%' }}
  }});

  // Trend line
  const trendData = analyticsData.date_trend;
  new Chart(document.getElementById('chartTrend'), {{
    type: 'line',
    data: {{
      labels: trendData.map(d => d[0]),
      datasets: [{{
        data: trendData.map(d => d[1]),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59,130,246,0.1)',
        fill: true, tension: 0.4,
        pointBackgroundColor: '#3b82f6',
        pointRadius: 4,
      }}]
    }},
    options: {{
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ grid: {{ display: false }} }},
        y: {{ grid: {{ color: dark.grid }}, beginAtZero: true }}
      }}
    }}
  }});
}}

// Init charts on page load (analytics is default tab)
window.addEventListener('load', initCharts);
</script>
</body>
</html>"""

    # Write to file
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    logger.info(f"Report written to {output_path}")
    return str(output)


def _render_job_rows(jobs: list[dict]) -> str:
    """Render job table rows as HTML."""
    rows = []
    for job in jobs:
        source = job.get("source", "")
        title = job.get("title", "")
        company = job.get("company", "")
        location = job.get("location", "")
        work_type = job.get("work_type", "")
        salary = job.get("salary", "")
        description = job.get("description", "")[:200]
        link = job.get("link", "")
        date = job.get("date", "")[:10]
        company_type = job.get("company_type", "")

        source_badge = (
            '<span class="badge badge-104">104</span>' if source == "104"
            else '<span class="badge badge-linkedin">LinkedIn</span>'
        )

        type_badges = ""
        if "外商" in company_type:
            type_badges += '<span class="badge badge-foreign">外商</span> '
        if "台灣百大" in company_type:
            type_badges += '<span class="badge badge-top100">百大</span>'
        if "遠端" in work_type:
            type_badges += ' <span class="badge badge-remote">遠端</span>'

        link_html = (
            f'<a href="{link}" target="_blank" class="link-btn">查看 →</a>'
            if link else "—"
        )

        desc_html = (
            f'<div class="description-text">{description}</div>'
            f'<button class="expand-btn" onclick="toggleDesc(this)">展開</button>'
            if description else "—"
        )

        rows.append(f"""      <tr data-source="{source}" data-type="{company_type}">
        <td style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text-muted);white-space:nowrap">{date}</td>
        <td>{source_badge}</td>
        <td class="job-title"><a href="{link}" target="_blank">{title}</a></td>
        <td style="font-weight:500;white-space:nowrap">{company}</td>
        <td>{type_badges}</td>
        <td style="white-space:nowrap;color:var(--text-dim)">{location}</td>
        <td style="white-space:nowrap;color:var(--text-dim)">{work_type}</td>
        <td style="white-space:nowrap;font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--green)">{salary}</td>
        <td class="description-cell">{desc_html}</td>
        <td>{link_html}</td>
      </tr>""")

    return "\n".join(rows)


if __name__ == "__main__":
    # Demo with fake data
    demo_jobs = [
        {
            "source": "104", "date": "2025-01-15", "title": "Senior Software Engineer",
            "company": "台積電", "location": "新竹", "work_type": "全職",
            "salary": "月薪 80,000 ~ 120,000", "description": "負責開發製程控制系統",
            "link": "https://www.104.com.tw/job/test1",
            "company_type": "台灣百大", "is_foreign": False, "is_top100_tw": True,
            "salary_min_parsed": 80000,
        },
        {
            "source": "LinkedIn", "date": "2025-01-14", "title": "AI Engineer",
            "company": "Google Taiwan", "location": "台北", "work_type": "全職 / 遠端",
            "salary": "依職缺內容", "description": "Work on ML infrastructure and AI products.",
            "link": "https://linkedin.com/jobs/test2",
            "company_type": "外商", "is_foreign": True, "is_top100_tw": False,
            "salary_min_parsed": 0,
        },
    ]
    generate_html_report(demo_jobs, "output/index.html")
    print("Demo report generated at output/index.html")
