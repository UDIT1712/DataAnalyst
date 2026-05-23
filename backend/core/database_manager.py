import json
from typing import Any

import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


class DatabaseManager:
    def __init__(self):
        self._engines: dict[str, AsyncEngine] = {}
        self._active: str | None = None

    async def connect(self, url: str, alias: str = "default") -> dict:
        # Normalize URL to async driver
        if url.startswith("sqlite:///"):
            url = url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("mysql://"):
            url = url.replace("mysql://", "mysql+aiomysql://", 1)

        engine = create_async_engine(url, echo=False)
        # Test connection
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        self._engines[alias] = engine
        self._active = alias
        return {"status": "connected", "alias": alias, "url": url.split("@")[-1]}

    async def execute_query(self, sql: str, alias: str | None = None) -> dict:
        alias = alias or self._active
        if not alias or alias not in self._engines:
            raise ValueError("No active database connection. Use connect_database first.")

        engine = self._engines[alias]
        async with engine.connect() as conn:
            result = await conn.execute(text(sql))
            if result.returns_rows:
                rows = result.fetchall()
                columns = list(result.keys())
                data = [dict(zip(columns, row)) for row in rows]
                return {"columns": columns, "rows": data, "row_count": len(data)}
            else:
                await conn.commit()
                return {"affected_rows": result.rowcount, "row_count": 0}

    async def get_schema(self, alias: str | None = None) -> dict:
        alias = alias or self._active
        if not alias or alias not in self._engines:
            raise ValueError("No active database connection.")

        engine = self._engines[alias]
        schema: dict[str, Any] = {}
        async with engine.connect() as conn:
            inspector = await conn.run_sync(lambda sync_conn: inspect(sync_conn))
            tables = inspector.get_table_names()
            for table in tables:
                columns = inspector.get_columns(table)
                schema[table] = [
                    {"name": col["name"], "type": str(col["type"])} for col in columns
                ]
        return schema

    async def list_tables(self, alias: str | None = None) -> list[str]:
        alias = alias or self._active
        if not alias or alias not in self._engines:
            raise ValueError("No active database connection.")

        engine = self._engines[alias]
        async with engine.connect() as conn:
            inspector = await conn.run_sync(lambda sync_conn: inspect(sync_conn))
            return inspector.get_table_names()

    def query_to_dataframe(self, query_result: dict) -> pd.DataFrame:
        if not query_result.get("rows"):
            return pd.DataFrame(columns=query_result.get("columns", []))
        return pd.DataFrame(query_result["rows"])

    @property
    def active_alias(self) -> str | None:
        return self._active

    async def close_all(self):
        for engine in self._engines.values():
            await engine.dispose()
        self._engines.clear()
        self._active = None
