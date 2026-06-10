"""
Core Data Analyst Agent — OpenAI GPT-4o with function calling.
Streams responses via AG-UI SSE protocol.
"""
import json
import os
import uuid
from typing import AsyncGenerator

import openai

from backend.agent.tools import TOOL_DEFINITIONS, ToolExecutor
from backend.api.agui_protocol import AGUIEvent, AGUIEventType
from backend.core.session_manager import SessionManager

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
MAX_TOKENS = 4096


async def run_agent_stream(
    client: openai.AsyncOpenAI,
    system: str,
    messages: list[dict],
    executor: ToolExecutor,
    thread_id: str,
    run_id: str,
    session_mgr: SessionManager,
) -> AsyncGenerator[str, None]:
    """
    Streaming agent loop with multi-turn OpenAI function calling.
    Yields AG-UI SSE event strings.
    """
    # Build OpenAI message list: system first, then conversation history
    working_messages: list[dict] = [{"role": "system", "content": system}]
    for m in messages:
        if m["role"] in ("user", "assistant") and isinstance(m["content"], str):
            working_messages.append({"role": m["role"], "content": m["content"]})

    yield AGUIEvent.sse(AGUIEventType.RUN_STARTED, {"threadId": thread_id, "runId": run_id})

    try:
        while True:
            msg_id = str(uuid.uuid4())[:8]
            full_text = ""
            text_started = False
            # index → {id, name, args}
            accumulated_tool_calls: dict[int, dict] = {}
            finish_reason: str | None = None

            yield AGUIEvent.sse(AGUIEventType.STEP_STARTED, {"stepName": "llm_call"})

            stream = await client.chat.completions.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=working_messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                stream=True,
            )

            async for chunk in stream:
                choice = chunk.choices[0]
                delta = choice.delta

                # ── Text content ──────────────────────────────────────────
                if delta.content:
                    if not text_started:
                        text_started = True
                        yield AGUIEvent.sse(
                            AGUIEventType.TEXT_MESSAGE_START,
                            {"messageId": msg_id, "role": "assistant"},
                        )
                    full_text += delta.content
                    yield AGUIEvent.sse(
                        AGUIEventType.TEXT_MESSAGE_CONTENT,
                        {"messageId": msg_id, "delta": delta.content},
                    )

                # ── Tool call deltas ──────────────────────────────────────
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in accumulated_tool_calls:
                            accumulated_tool_calls[idx] = {
                                "id": tc_delta.id or "",
                                "name": (tc_delta.function.name or "") if tc_delta.function else "",
                                "args": "",
                            }
                            yield AGUIEvent.sse(
                                AGUIEventType.TOOL_CALL_START,
                                {
                                    "toolCallId": accumulated_tool_calls[idx]["id"],
                                    "toolCallName": accumulated_tool_calls[idx]["name"],
                                    "parentMessageId": msg_id,
                                },
                            )

                        tc = accumulated_tool_calls[idx]
                        # Accumulate id/name in case they arrive in later chunks
                        if tc_delta.id:
                            tc["id"] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name:
                                tc["name"] = tc_delta.function.name
                            if tc_delta.function.arguments:
                                tc["args"] += tc_delta.function.arguments
                                yield AGUIEvent.sse(
                                    AGUIEventType.TOOL_CALL_ARGS,
                                    {"toolCallId": tc["id"], "delta": tc_delta.function.arguments},
                                )

                if choice.finish_reason:
                    finish_reason = choice.finish_reason

            # Close text message if open
            if text_started:
                yield AGUIEvent.sse(AGUIEventType.TEXT_MESSAGE_END, {"messageId": msg_id})

            yield AGUIEvent.sse(AGUIEventType.STEP_FINISHED, {"stepName": "llm_call"})

            # Save text to session
            if full_text:
                session_mgr.add_message(thread_id, "assistant", full_text)

            # Build assistant message for working history
            assistant_msg: dict = {"role": "assistant", "content": full_text or None}
            if accumulated_tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["args"]},
                    }
                    for tc in accumulated_tool_calls.values()
                ]
            working_messages.append(assistant_msg)

            # Done if no tool calls
            if finish_reason != "tool_calls" or not accumulated_tool_calls:
                break

            # ── Execute tool calls ────────────────────────────────────────
            for tc in accumulated_tool_calls.values():
                yield AGUIEvent.sse(AGUIEventType.STEP_STARTED, {"stepName": f"tool:{tc['name']}"})

                try:
                    args = json.loads(tc["args"]) if tc["args"] else {}
                except json.JSONDecodeError:
                    args = {}

                result = await executor.execute(tc["name"], args)

                # Emit chart / report custom events
                if isinstance(result, dict):
                    if "chart" in result:
                        yield AGUIEvent.sse(
                            AGUIEventType.CUSTOM,
                            {"name": "chart_generated", "value": result["chart"]},
                        )
                    if result.get("download_url"):
                        yield AGUIEvent.sse(
                            AGUIEventType.CUSTOM,
                            {"name": "report_ready", "value": result},
                        )

                # OpenAI tool result format: role="tool"
                working_messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result, default=str),
                })

                yield AGUIEvent.sse(AGUIEventType.TOOL_CALL_END, {"toolCallId": tc["id"]})
                yield AGUIEvent.sse(AGUIEventType.STEP_FINISHED, {"stepName": f"tool:{tc['name']}"})

            # State snapshot after tool round
            session = session_mgr.get(thread_id)
            yield AGUIEvent.sse(
                AGUIEventType.STATE_SNAPSHOT,
                {
                    "snapshot": {
                        "datasets": session_mgr.get_dataframe_names(thread_id),
                        "chart_count": len(session.charts) if session else 0,
                    }
                },
            )

    except Exception as e:
        yield AGUIEvent.sse(AGUIEventType.RUN_ERROR, {"message": str(e), "code": "AGENT_ERROR"})
        return

    yield AGUIEvent.sse(AGUIEventType.RUN_FINISHED, {"threadId": thread_id, "runId": run_id})
