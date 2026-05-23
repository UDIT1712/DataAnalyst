"""
MCP Server: File — loads CSV, Excel, and JSON files into analysis sessions.
Run standalone: python -m backend.mcp_servers.file_server
"""
import asyncio
import json
import os
from pathlib import Path

import pandas as pd
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
app = Server("file-server")

_loaded: dict[str, pd.DataFrame] = {}


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="load_file",
            description="Load a CSV, Excel (.xlsx/.xls), or JSON file into the analysis session",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Filename in the uploads directory",
                    },
                    "name": {
                        "type": "string",
                        "description": "Alias to reference this dataset by (default: filename without extension)",
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Excel sheet name (default: first sheet)",
                    },
                },
                "required": ["filename"],
            },
        ),
        Tool(
            name="list_uploaded_files",
            description="List all files available in the uploads directory",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="preview_file",
            description="Return the first N rows of a loaded dataset as JSON",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Dataset alias"},
                    "rows": {"type": "integer", "description": "Number of rows to preview", "default": 10},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="get_file_info",
            description="Get metadata (shape, dtypes, nulls) for a loaded dataset",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                },
                "required": ["name"],
            },
        ),
    ]


def _load_df(filename: str, sheet_name: str | None = None) -> pd.DataFrame:
    path = UPLOAD_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"{filename} not found in uploads/")
    ext = path.suffix.lower()
    if ext == ".csv":
        return pd.read_csv(path)
    elif ext in (".xlsx", ".xls"):
        return pd.read_excel(path, sheet_name=sheet_name or 0)
    elif ext == ".json":
        return pd.read_json(path)
    elif ext == ".parquet":
        return pd.read_parquet(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "load_file":
            filename = arguments["filename"]
            alias = arguments.get("name") or Path(filename).stem
            df = _load_df(filename, arguments.get("sheet_name"))
            _loaded[alias] = df
            result = {
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
            result = {"files": files}
        elif name == "preview_file":
            alias = arguments["name"]
            rows = arguments.get("rows", 10)
            df = _loaded.get(alias)
            if df is None:
                result = {"error": f"Dataset '{alias}' not loaded. Use load_file first."}
            else:
                result = {
                    "columns": df.columns.tolist(),
                    "rows": df.head(rows).to_dict(orient="records"),
                }
        elif name == "get_file_info":
            alias = arguments["name"]
            df = _loaded.get(alias)
            if df is None:
                result = {"error": f"Dataset '{alias}' not loaded."}
            else:
                result = {
                    "alias": alias,
                    "shape": list(df.shape),
                    "columns": df.columns.tolist(),
                    "dtypes": df.dtypes.astype(str).to_dict(),
                    "null_counts": df.isna().sum().to_dict(),
                    "memory_kb": round(df.memory_usage(deep=True).sum() / 1024, 2),
                }
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
