import os
import uuid
from pathlib import Path
from typing import Annotated

import aiofiles
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.agent.analyst_agent import run_agent_stream
from backend.agent.tools import ToolExecutor
from backend.api.agui_protocol import AGUIEvent, AGUIEventType
from backend.core.database_manager import DatabaseManager

router = APIRouter()

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
REPORTS_DIR = Path(os.getenv("REPORTS_DIR", "./reports"))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "50")) * 1024 * 1024

_db_pool: dict[str, DatabaseManager] = {}


def _get_db(thread_id: str) -> DatabaseManager:
    if thread_id not in _db_pool:
        _db_pool[thread_id] = DatabaseManager()
    return _db_pool[thread_id]


# ─── AG-UI chat endpoint ──────────────────────────────────────────────────────

class AGUIRequest(BaseModel):
    thread_id: str = ""
    run_id: str = ""
    messages: list[dict] = []
    state: dict = {}
    forwarded_props: dict = {}


@router.post("/chat")
async def chat(req: AGUIRequest, request: Request):
    """AG-UI compatible SSE streaming endpoint."""
    import anthropic

    session_mgr = request.app.state.session_manager
    thread_id = req.thread_id or str(uuid.uuid4())
    run_id = req.run_id or str(uuid.uuid4())

    # Sync incoming messages into session (only user messages not yet stored)
    existing = session_mgr.get_messages(thread_id)
    for msg in req.messages:
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(c.get("text", "") for c in content if c.get("type") == "text")
            # Only add if it's a new message
            if not any(
                m["role"] == "user" and m["content"] == content for m in existing
            ):
                session_mgr.add_message(thread_id, "user", content)

    # Get the last user message
    all_messages = session_mgr.get_messages(thread_id)
    user_msgs = [m for m in all_messages if m["role"] == "user"]
    if not user_msgs:
        raise HTTPException(400, "No user message provided")

    last_user_msg = user_msgs[-1]["content"]

    db = _get_db(thread_id)
    executor = ToolExecutor(db, session_mgr, thread_id)
    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    from backend.agent.prompts import SYSTEM_PROMPT
    datasets = session_mgr.get_dataframe_names(thread_id)
    system = SYSTEM_PROMPT
    if datasets:
        system += f"\n\n## Currently loaded datasets: {', '.join(datasets)}"

    messages = session_mgr.get_messages(thread_id)

    async def event_generator():
        try:
            async for chunk in run_agent_stream(
                client, system, messages, executor, thread_id, run_id, session_mgr
            ):
                yield chunk
        except Exception as e:
            yield AGUIEvent.sse(AGUIEventType.RUN_ERROR, {"message": str(e), "code": "STREAM_ERROR"})

    return EventSourceResponse(event_generator(), media_type="text/event-stream")


# ─── File upload ─────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    allowed = {".csv", ".xlsx", ".xls", ".json", ".parquet"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported file type: {ext}. Allowed: {', '.join(allowed)}")

    UPLOAD_DIR.mkdir(exist_ok=True)
    safe_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    dest = UPLOAD_DIR / safe_name

    size = 0
    async with aiofiles.open(dest, "wb") as out:
        while chunk := await file.read(1024 * 64):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"File exceeds {os.getenv('MAX_UPLOAD_MB', 50)} MB limit")
            await out.write(chunk)

    return {"filename": safe_name, "original_name": file.filename, "size_kb": round(size / 1024, 1)}


# ─── Sessions ────────────────────────────────────────────────────────────────

@router.get("/sessions")
async def list_sessions(request: Request):
    session_mgr = request.app.state.session_manager
    return {"sessions": session_mgr.list_sessions()}


@router.delete("/sessions/{thread_id}")
async def delete_session(thread_id: str, request: Request):
    session_mgr = request.app.state.session_manager
    if session_mgr.get(thread_id):
        session_mgr._sessions.pop(thread_id, None)
    return {"status": "deleted"}


# ─── Reports ────────────────────────────────────────────────────────────────

@router.get("/reports/{filename}")
async def download_report(filename: str):
    path = REPORTS_DIR / filename
    if not path.exists():
        raise HTTPException(404, "Report not found")
    media = "application/pdf" if filename.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return FileResponse(str(path), media_type=media, filename=filename)


# ─── Uploaded files list ────────────────────────────────────────────────────

@router.get("/files")
async def list_files():
    files = []
    if UPLOAD_DIR.exists():
        for f in UPLOAD_DIR.iterdir():
            if f.is_file() and f.suffix.lower() in (".csv", ".xlsx", ".xls", ".json", ".parquet"):
                files.append({"name": f.name, "size_kb": round(f.stat().st_size / 1024, 1)})
    return {"files": sorted(files, key=lambda x: x["name"])}
