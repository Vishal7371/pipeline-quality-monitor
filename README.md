# 📊 Pipeline Quality Monitor

A powerful, browser-based data quality dashboard. Drop a CSV file and instantly get a complete health report — schema analysis, null detection, anomalies, SQL queries, and more.

**Zero backend. Zero setup. Just open and go.**

---

## ✨ Features

### Core Analysis
- **Quality Score** — 0-100 health gauge with pass/warn/fail checks
- **AI Data Summary** — auto-generated plain English description of your dataset
- **Smart Profiling** — auto-detect emails, phone numbers, URLs, ZIP codes, currencies
- **Column Recommendations** — primary key candidates, cleaning suggestions

### Visualization
- **Interactive Scatter Plot** — pick X/Y axes with color coding
- **Correlation Heatmap** — Pearson correlation for numeric columns
- **Null Rate & Distinct Value Charts**
- **Score Breakdown** — per-check contribution

### Deep Dive
- **SQL Query Engine** — real SQL powered by AlaSQL
- **Data Preview** — searchable, sortable table
- **Column Deep Dive** — histogram, top values, stats
- **Anomaly & Trend Detection**

### Transform & Export
- **Data Transformation** — rename, filter, download clean CSV
- **Custom Rules** — min/max/null thresholds per column
- **Export PDF / Excel / Shareable HTML**

### Workflow
- **Multi-File Dashboard** — switch between datasets
- **Compare Two Files** — schema diff
- **Run History & Data Lineage**
- **Dark/Light Mode & Keyboard Shortcuts**

---

## 🚀 Quick Start

```bash
git clone https://github.com/Vishal7371/pipeline-quality-monitor.git
open dashboard.html
```

No npm install, no build step, no server needed.

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| HTML/CSS/JS | Single-file dashboard |
| Chart.js | Visualizations |
| PapaParse | CSV parsing |
| AlaSQL | SQL engine |
| SheetJS | Excel export |
| html2canvas + jsPDF | PDF export |
| Python | Backend CLI checks |

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| ⌘O | Open file |
| ⌘E | Export Excel |
| ⌘P | Export PDF |
| ⌘T | Toggle theme |
| ⌘K | Jump to SQL |
| Esc | Close modal |

---

## 📄 License

MIT License

**Built with ❤️ by [Vishal](https://github.com/Vishal7371)**
