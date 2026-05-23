import time
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class AnalysisSession:
    thread_id: str
    messages: list[dict] = field(default_factory=list)
    dataframes: dict[str, pd.DataFrame] = field(default_factory=dict)
    charts: list[dict] = field(default_factory=list)
    db_alias: str | None = None
    last_active: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def touch(self):
        self.last_active = time.time()


class SessionManager:
    def __init__(self, ttl_seconds: int = 3600):
        self._sessions: dict[str, AnalysisSession] = {}
        self._ttl = ttl_seconds

    def get_or_create(self, thread_id: str) -> AnalysisSession:
        self._evict_expired()
        if thread_id not in self._sessions:
            self._sessions[thread_id] = AnalysisSession(thread_id=thread_id)
        session = self._sessions[thread_id]
        session.touch()
        return session

    def get(self, thread_id: str) -> AnalysisSession | None:
        return self._sessions.get(thread_id)

    def add_message(self, thread_id: str, role: str, content: str | list):
        session = self.get_or_create(thread_id)
        session.messages.append({"role": role, "content": content})

    def store_dataframe(self, thread_id: str, name: str, df: pd.DataFrame):
        session = self.get_or_create(thread_id)
        session.dataframes[name] = df

    def add_chart(self, thread_id: str, chart: dict):
        session = self.get_or_create(thread_id)
        session.charts.append(chart)

    def get_messages(self, thread_id: str) -> list[dict]:
        session = self.get(thread_id)
        return session.messages if session else []

    def get_dataframe_names(self, thread_id: str) -> list[str]:
        session = self.get(thread_id)
        return list(session.dataframes.keys()) if session else []

    def get_dataframe(self, thread_id: str, name: str) -> pd.DataFrame | None:
        session = self.get(thread_id)
        if session:
            return session.dataframes.get(name)
        return None

    def list_sessions(self) -> list[dict]:
        return [
            {
                "thread_id": s.thread_id,
                "message_count": len(s.messages),
                "dataframes": list(s.dataframes.keys()),
                "chart_count": len(s.charts),
                "last_active": s.last_active,
            }
            for s in self._sessions.values()
        ]

    def _evict_expired(self):
        now = time.time()
        expired = [tid for tid, s in self._sessions.items() if now - s.last_active > self._ttl]
        for tid in expired:
            del self._sessions[tid]

    def clear_all(self):
        self._sessions.clear()
