"""
MCP Server: Database — exposes SQL database tools via the MCP protocol.
Run standalone: python -m backend.mcp_servers.database_server
"""
import asyncio
import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from backend.core.database_manager import DatabaseManager

app = Server("database-server")
db = DatabaseManager()


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="connect_database",
            description="Connect to a SQL database (SQLite, PostgreSQL, MySQL)",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Database URL, e.g. sqlite:///./data.db or postgresql://user:pass@host/db",
                    },
                    "alias": {"type": "string", "description": "Nickname for this connection", "default": "default"},
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="execute_sql",
            description="Execute a SQL query and return results as JSON",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL query to execute"},
                    "alias": {"type": "string", "description": "Database alias to query"},
                },
                "required": ["sql"],
            },
        ),
        Tool(
            name="get_db_schema",
            description="Get the full schema of the connected database (tables and columns)",
            inputSchema={
                "type": "object",
                "properties": {
                    "alias": {"type": "string", "description": "Database alias"},
                },
            },
        ),
        Tool(
            name="list_tables",
            description="List all tables in the connected database",
            inputSchema={
                "type": "object",
                "properties": {
                    "alias": {"type": "string"},
                },
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "connect_database":
            result = await db.connect(arguments["url"], arguments.get("alias", "default"))
        elif name == "execute_sql":
            result = await db.execute_query(arguments["sql"], arguments.get("alias"))
        elif name == "get_db_schema":
            result = await db.get_schema(arguments.get("alias"))
        elif name == "list_tables":
            result = await db.list_tables(arguments.get("alias"))
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
