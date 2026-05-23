"""
MCP Server: Analytics — statistical analysis, charting, anomaly detection, predictions, reports.
Run standalone: python -m backend.mcp_servers.analytics_server
"""
import asyncio
import json

import pandas as pd
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from backend.core.chart_engine import ChartEngine
from backend.core.data_processor import DataProcessor

app = Server("analytics-server")
_datasets: dict[str, pd.DataFrame] = {}


def _get_df(name: str) -> pd.DataFrame:
    if name not in _datasets:
        raise ValueError(f"Dataset '{name}' not found. Load it first.")
    return _datasets[name]


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="statistical_summary",
            description="Compute descriptive statistics for all columns in a dataset",
            inputSchema={
                "type": "object",
                "properties": {"dataset": {"type": "string"}},
                "required": ["dataset"],
            },
        ),
        Tool(
            name="create_chart",
            description="Generate an interactive Plotly chart from a dataset",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset": {"type": "string"},
                    "chart_type": {
                        "type": "string",
                        "enum": ["bar", "line", "scatter", "histogram", "box", "pie", "area", "heatmap", "auto"],
                    },
                    "x": {"type": "string"},
                    "y": {"type": "string"},
                    "color": {"type": "string"},
                    "title": {"type": "string"},
                },
                "required": ["dataset", "chart_type"],
            },
        ),
        Tool(
            name="detect_anomalies",
            description="Detect outliers in numeric columns using IQR or Z-score method",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset": {"type": "string"},
                    "method": {"type": "string", "enum": ["iqr", "zscore"], "default": "iqr"},
                },
                "required": ["dataset"],
            },
        ),
        Tool(
            name="correlation_analysis",
            description="Compute correlation matrix and identify strongly correlated columns",
            inputSchema={
                "type": "object",
                "properties": {"dataset": {"type": "string"}},
                "required": ["dataset"],
            },
        ),
        Tool(
            name="time_series_analysis",
            description="Decompose a time series into trend, seasonal, and residual components",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset": {"type": "string"},
                    "date_column": {"type": "string"},
                    "value_column": {"type": "string"},
                },
                "required": ["dataset", "date_column", "value_column"],
            },
        ),
        Tool(
            name="run_prediction",
            description="Train a gradient boosting model for regression or classification",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset": {"type": "string"},
                    "target": {"type": "string"},
                    "features": {"type": "array", "items": {"type": "string"}},
                    "task": {"type": "string", "enum": ["regression", "classification"], "default": "regression"},
                },
                "required": ["dataset", "target", "features"],
            },
        ),
        Tool(
            name="data_quality_report",
            description="Audit a dataset for nulls, duplicates, type mismatches, and memory usage",
            inputSchema={
                "type": "object",
                "properties": {"dataset": {"type": "string"}},
                "required": ["dataset"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        df = _get_df(arguments.get("dataset", ""))

        if name == "statistical_summary":
            result = DataProcessor.statistical_summary(df)
        elif name == "create_chart":
            chart_type = arguments["chart_type"]
            x = arguments.get("x")
            y = arguments.get("y")
            title = arguments.get("title", "")
            color = arguments.get("color")

            if chart_type == "auto":
                result = ChartEngine.auto_chart(df, x, y, title)
            elif chart_type == "bar":
                result = ChartEngine.bar_chart(df, x, y, title, color)
            elif chart_type == "line":
                result = ChartEngine.line_chart(df, x, y, title, color)
            elif chart_type == "scatter":
                result = ChartEngine.scatter_chart(df, x, y, title, color)
            elif chart_type == "histogram":
                result = ChartEngine.histogram(df, x, title)
            elif chart_type == "box":
                result = ChartEngine.box_plot(df, y, x, title)
            elif chart_type == "pie":
                result = ChartEngine.pie_chart(df, x, y, title)
            elif chart_type == "area":
                result = ChartEngine.area_chart(df, x, y, title)
            elif chart_type == "heatmap":
                corr = DataProcessor.correlation_matrix(df)
                result = ChartEngine.heatmap(corr["matrix"], corr["columns"], title or "Correlation Heatmap")
            else:
                result = {"error": f"Unknown chart type: {chart_type}"}
        elif name == "detect_anomalies":
            result = DataProcessor.detect_anomalies(df, arguments.get("method", "iqr"))
        elif name == "correlation_analysis":
            corr = DataProcessor.correlation_matrix(df)
            corr["chart"] = ChartEngine.heatmap(corr["matrix"], corr["columns"])
            result = corr
        elif name == "time_series_analysis":
            ts = DataProcessor.time_series_analysis(df, arguments["date_column"], arguments["value_column"])
            if "trend" in ts:
                ts["chart"] = ChartEngine.time_series_decomposition_chart(ts)
            result = ts
        elif name == "run_prediction":
            pred = DataProcessor.run_prediction(
                df, arguments["target"], arguments["features"], arguments.get("task", "regression")
            )
            pred["chart"] = ChartEngine.feature_importance_chart(pred["feature_importances"])
            result = pred
        elif name == "data_quality_report":
            result = DataProcessor.data_quality_report(df)
        else:
            result = {"error": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, default=str))]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
