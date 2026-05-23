# Data Analyst Agent

An advanced AI-powered data analyst with an interactive UI — powered by **Claude claude-sonnet-4-6**, **AG-UI streaming protocol**, **MCP servers**, and **React + Plotly**.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     React Frontend                        │
│  Sidebar  │  AG-UI Chat (SSE streaming)  │  Charts/Table │
│  (Files,  │  useAgentStream hook         │  Plotly.js    │
│   DB,     │  CopilotKit-compatible       │  TanStack     │
│  Reports) │  AG-UI protocol              │  Table        │
└─────────────────────┬────────────────────────────────────┘
                      │ SSE / POST /api/chat
┌─────────────────────▼────────────────────────────────────┐
│                  FastAPI Backend                          │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │            Data Analyst Agent (Claude)              │ │
│  │  claude-sonnet-4-6 + tool_use + streaming + caching │ │
│  └──────────────┬──────────────────────────────────────┘ │
│                 │ Tool calls                              │
│  ┌──────────────▼──────────────────────────────────────┐ │
│  │              MCP Tool Servers                        │ │
│  │  database_server │ file_server │ analytics_server   │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                          │
│  Core Engine: chart_engine · data_processor ·           │
│               database_manager · session_manager ·      │
│               report_generator                          │
└──────────────────────────────────────────────────────────┘
```

## Features

| Feature | Details |
|---|---|
| Natural Language SQL | Write and run SQL from plain English |
| File Analysis | CSV, Excel, JSON, Parquet support |
| Auto Chart Selection | Agent picks optimal chart type automatically |
| 8 Chart Types | Bar, Line, Scatter, Histogram, Box, Pie, Area, Heatmap |
| Anomaly Detection | IQR & Z-score outlier detection |
| Correlation Analysis | Pearson matrix with heatmap |
| Time Series Decomposition | Trend + Seasonal + Residual |
| Predictive Analytics | Gradient Boosting regression & classification |
| Data Quality Audit | Nulls, duplicates, types, memory |
| PDF Reports | Full report with charts + narrative |
| Excel Export | All datasets as separate sheets |
| Session Memory | Persistent conversation context per thread |
| Streaming | Real-time AG-UI SSE streaming with tool progress |
| Prompt Caching | Anthropic ephemeral cache for fast follow-ups |

## Quick Start

### 1. Backend

```bash
# Create .env from example
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Start the backend
uvicorn backend.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

### 3. Usage

1. **Upload a file** — drag CSV/Excel/JSON into the sidebar
2. **Or connect a database** — paste your DB URL in the Database panel
3. **Ask questions** — type in the chat, e.g.:
   - _"Show me the top 10 rows"_
   - _"Create a bar chart of sales by region"_
   - _"Are there any anomalies in the revenue column?"_
   - _"Run a regression to predict sales from ad_spend and employees"_
   - _"Generate a PDF report"_

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | **Required** — from https://console.anthropic.com |
| `BACKEND_PORT` | `8000` | FastAPI port |
| `FRONTEND_URL` | `http://localhost:5173` | CORS origin |
| `UPLOAD_DIR` | `./uploads` | File upload directory |
| `REPORTS_DIR` | `./reports` | Report output directory |
| `MAX_UPLOAD_MB` | `50` | Max upload size |
| `DEFAULT_DB_URL` | `sqlite:///./data.db` | Default DB (optional) |

## MCP Servers

The three MCP servers can also run as standalone processes and be connected from external clients:

```bash
# Database server
python -m backend.mcp_servers.database_server

# File server
python -m backend.mcp_servers.file_server

# Analytics server
python -m backend.mcp_servers.analytics_server
```

## Available Agent Tools

| Tool | Description |
|---|---|
| `connect_database` | Connect to PostgreSQL / MySQL / SQLite |
| `execute_sql` | Run SQL queries |
| `get_db_schema` | Inspect database structure |
| `load_file` | Load CSV/Excel/JSON/Parquet |
| `list_uploaded_files` | Browse uploaded files |
| `preview_dataset` | Show first N rows |
| `statistical_summary` | Descriptive stats for all columns |
| `create_chart` | Generate interactive Plotly chart |
| `detect_anomalies` | Find outliers (IQR / Z-score) |
| `correlation_analysis` | Pearson correlation matrix |
| `time_series_analysis` | Trend/seasonal decomposition |
| `run_prediction` | ML regression or classification |
| `data_quality_report` | Nulls, duplicates, types audit |
| `generate_report` | PDF or Excel report |

## Tech Stack

- **Agent**: Anthropic Claude claude-sonnet-4-6, Python SDK with streaming + prompt caching
- **Protocol**: AG-UI (Agent User Interaction) — SSE-based streaming
- **MCP**: `mcp` Python library — modular tool servers
- **Backend**: FastAPI, Uvicorn, SQLAlchemy (async)
- **Data**: Pandas, NumPy, SciPy, statsmodels, scikit-learn
- **Charts**: Plotly
- **Reports**: ReportLab (PDF), openpyxl (Excel)
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS
- **UI**: Plotly.js, TanStack Table, react-dropzone, Lucide icons
