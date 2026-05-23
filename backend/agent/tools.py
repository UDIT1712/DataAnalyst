"""
Anthropic tool definitions + in-process implementations for the Data Analyst Agent.
Each tool maps to one of the three MCP server capabilities.
"""
import json
import os
from pathlib import Path

import pandas as pd

from backend.core.chart_engine import ChartEngine
from backend.core.data_processor import DataProcessor
from backend.core.database_manager import DatabaseManager
from backend.core.report_generator import ReportGenerator
from backend.core.session_manager import SessionManager

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))

# ─── Anthropic tool schemas ──────────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "connect_database",
        "description": "Connect to a SQL database (SQLite, PostgreSQL, MySQL). Call this before executing any SQL queries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Database URL. Examples: sqlite:///./data.db | postgresql://user:pass@host/db | mysql://user:pass@host/db",
                },
                "alias": {"type": "string", "description": "Short name for this connection (default: 'default')"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "execute_sql",
        "description": "Execute a SQL query against the connected database. Always LIMIT to 1000 rows unless user asks for more.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "SQL query to run"},
                "alias": {"type": "string", "description": "Database alias (defaults to active connection)"},
            },
            "required": ["sql"],
        },
    },
    {
        "name": "get_db_schema",
        "description": "Get the full schema (tables and column types) of the connected database.",
        "input_schema": {
            "type": "object",
            "properties": {
                "alias": {"type": "string"},
            },
        },
    },
    {
        "name": "load_file",
        "description": "Load a CSV, Excel, or JSON file from the uploads directory into the analysis session.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Filename in the uploads/ directory"},
                "name": {"type": "string", "description": "Alias to use for this dataset"},
                "sheet_name": {"type": "string", "description": "Excel sheet name (optional)"},
            },
            "required": ["filename"],
        },
    },
    {
        "name": "list_uploaded_files",
        "description": "List all files available in the uploads directory.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "preview_dataset",
        "description": "Show the first N rows of a loaded dataset to understand its structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Dataset alias"},
                "rows": {"type": "integer", "description": "Number of rows (default: 10)"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "statistical_summary",
        "description": "Compute descriptive statistics (mean, median, std, quartiles, skew) for all columns in a dataset.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Dataset alias"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "create_chart",
        "description": "Generate an interactive Plotly chart from a loaded dataset. Returns chart JSON for the frontend to render.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Dataset alias"},
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "scatter", "histogram", "box", "pie", "area", "heatmap", "auto"],
                    "description": "Chart type. Use 'auto' to let the system pick the best type.",
                },
                "x": {"type": "string", "description": "Column for x-axis"},
                "y": {"type": "string", "description": "Column for y-axis"},
                "color": {"type": "string", "description": "Column to use for color grouping"},
                "title": {"type": "string", "description": "Chart title"},
            },
            "required": ["name", "chart_type"],
        },
    },
    {
        "name": "detect_anomalies",
        "description": "Find outliers in all numeric columns of a dataset using IQR or Z-score method.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "method": {"type": "string", "enum": ["iqr", "zscore"], "description": "Detection method (default: iqr)"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "correlation_analysis",
        "description": "Compute a Pearson correlation matrix and identify strongly correlated column pairs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "time_series_analysis",
        "description": "Decompose a time series column into trend, seasonal, and residual components.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Dataset alias"},
                "date_column": {"type": "string", "description": "Column containing dates"},
                "value_column": {"type": "string", "description": "Numeric column to decompose"},
            },
            "required": ["name", "date_column", "value_column"],
        },
    },
    {
        "name": "run_prediction",
        "description": "Train a Gradient Boosting model for regression or classification and return metrics + feature importances.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Dataset alias"},
                "target": {"type": "string", "description": "Column to predict"},
                "features": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of feature column names",
                },
                "task": {"type": "string", "enum": ["regression", "classification"]},
            },
            "required": ["name", "target", "features"],
        },
    },
    {
        "name": "data_quality_report",
        "description": "Audit a dataset for nulls, duplicates, type mismatches, and memory usage.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "generate_report",
        "description": "Generate a downloadable PDF or Excel report from the current analysis session.",
        "input_schema": {
            "type": "object",
            "properties": {
                "format": {"type": "string", "enum": ["pdf", "excel"], "description": "Output format"},
                "title": {"type": "string", "description": "Report title"},
                "narrative": {"type": "string", "description": "Text narrative/summary to include in the report"},
            },
            "required": ["format", "title"],
        },
    },
]


# ─── Tool executor ────────────────────────────────────────────────────────────

class ToolExecutor:
    def __init__(self, db: DatabaseManager, session_mgr: SessionManager, thread_id: str):
        self.db = db
        self.session_mgr = session_mgr
        self.thread_id = thread_id

    def _get_df(self, name: str) -> pd.DataFrame:
        df = self.session_mgr.get_dataframe(self.thread_id, name)
        if df is None:
            raise ValueError(f"Dataset '{name}' not found. Load it first with load_file or execute_sql.")
        return df

    def _store_df(self, name: str, df: pd.DataFrame):
        self.session_mgr.store_dataframe(self.thread_id, name, df)

    async def execute(self, tool_name: str, tool_input: dict) -> dict:
        try:
            return await self._dispatch(tool_name, tool_input)
        except Exception as e:
            return {"error": str(e)}

    async def _dispatch(self, name: str, inp: dict) -> dict:
        if name == "connect_database":
            return await self.db.connect(inp["url"], inp.get("alias", "default"))

        elif name == "execute_sql":
            result = await self.db.execute_query(inp["sql"], inp.get("alias"))
            if result.get("rows"):
                df = self.db.query_to_dataframe(result)
                ds_name = f"query_{len(self.session_mgr.get_dataframe_names(self.thread_id))}"
                self._store_df(ds_name, df)
                result["dataset_name"] = ds_name
            return result

        elif name == "get_db_schema":
            return await self.db.get_schema(inp.get("alias"))

        elif name == "load_file":
            filename = inp["filename"]
            alias = inp.get("name") or Path(filename).stem
            path = UPLOAD_DIR / filename
            ext = path.suffix.lower()
            if ext == ".csv":
                df = pd.read_csv(path)
            elif ext in (".xlsx", ".xls"):
                df = pd.read_excel(path, sheet_name=inp.get("sheet_name", 0))
            elif ext == ".json":
                df = pd.read_json(path)
            elif ext == ".parquet":
                df = pd.read_parquet(path)
            else:
                raise ValueError(f"Unsupported file type: {ext}")
            self._store_df(alias, df)
            return {
                "status": "loaded",
                "alias": alias,
                "shape": list(df.shape),
                "columns": df.columns.tolist(),
                "dtypes": df.dtypes.astype(str).to_dict(),
            }

        elif name == "list_uploaded_files":
            files = []
            if UPLOAD_DIR.exists():
                for f in UPLOAD_DIR.iterdir():
                    if f.is_file() and f.suffix.lower() in (".csv", ".xlsx", ".xls", ".json", ".parquet"):
                        files.append({"name": f.name, "size_kb": round(f.stat().st_size / 1024, 1)})
            return {"files": files}

        elif name == "preview_dataset":
            df = self._get_df(inp["name"])
            rows = inp.get("rows", 10)
            return {
                "columns": df.columns.tolist(),
                "rows": df.head(rows).to_dict(orient="records"),
                "shape": list(df.shape),
            }

        elif name == "statistical_summary":
            df = self._get_df(inp["name"])
            return DataProcessor.statistical_summary(df)

        elif name == "create_chart":
            df = self._get_df(inp["name"])
            chart_type = inp["chart_type"]
            x, y = inp.get("x"), inp.get("y")
            title = inp.get("title", "")
            color = inp.get("color")

            dispatch = {
                "auto": lambda: ChartEngine.auto_chart(df, x, y, title),
                "bar": lambda: ChartEngine.bar_chart(df, x, y, title, color),
                "line": lambda: ChartEngine.line_chart(df, x, y, title, color),
                "scatter": lambda: ChartEngine.scatter_chart(df, x, y, title, color),
                "histogram": lambda: ChartEngine.histogram(df, x, title),
                "box": lambda: ChartEngine.box_plot(df, y, x, title),
                "pie": lambda: ChartEngine.pie_chart(df, x, y, title),
                "area": lambda: ChartEngine.area_chart(df, x, y, title),
                "heatmap": lambda: ChartEngine.heatmap(
                    DataProcessor.correlation_matrix(df)["matrix"],
                    DataProcessor.correlation_matrix(df)["columns"],
                    title or "Correlation Heatmap",
                ),
            }
            chart_json = dispatch[chart_type]()
            self.session_mgr.add_chart(self.thread_id, chart_json)
            return {"chart": chart_json, "type": chart_type}

        elif name == "detect_anomalies":
            df = self._get_df(inp["name"])
            return DataProcessor.detect_anomalies(df, inp.get("method", "iqr"))

        elif name == "correlation_analysis":
            df = self._get_df(inp["name"])
            corr = DataProcessor.correlation_matrix(df)
            corr["chart"] = ChartEngine.heatmap(corr["matrix"], corr["columns"])
            self.session_mgr.add_chart(self.thread_id, corr["chart"])
            return corr

        elif name == "time_series_analysis":
            df = self._get_df(inp["name"])
            ts = DataProcessor.time_series_analysis(df, inp["date_column"], inp["value_column"])
            if "trend" in ts:
                ts["chart"] = ChartEngine.time_series_decomposition_chart(ts)
                self.session_mgr.add_chart(self.thread_id, ts["chart"])
            return ts

        elif name == "run_prediction":
            df = self._get_df(inp["name"])
            pred = DataProcessor.run_prediction(
                df, inp["target"], inp["features"], inp.get("task", "regression")
            )
            pred["chart"] = ChartEngine.feature_importance_chart(pred["feature_importances"])
            self.session_mgr.add_chart(self.thread_id, pred["chart"])
            return pred

        elif name == "data_quality_report":
            df = self._get_df(inp["name"])
            return DataProcessor.data_quality_report(df)

        elif name == "generate_report":
            session = self.session_mgr.get(self.thread_id)
            dfs = session.dataframes if session else {}
            charts = session.charts if session else []
            fmt = inp["format"]
            if fmt == "pdf":
                filename = ReportGenerator.generate_pdf(
                    inp["title"],
                    inp.get("narrative", ""),
                    dfs,
                    charts,
                    self.thread_id,
                )
            else:
                filename = ReportGenerator.generate_excel(dfs, charts, self.thread_id)
            return {"status": "generated", "filename": filename, "download_url": f"/reports/{filename}"}

        else:
            return {"error": f"Unknown tool: {name}"}
