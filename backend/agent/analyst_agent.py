import json
import os
import uuid
from typing import AsyncGenerator

import anthropic

from backend.agent.prompts import SYSTEM_PROMPT
from backend.agent.tools import TOOL_DEFINITIONS, ToolExecutor
from backend.api.agui_protocol import AGUIEvent, AGUIEventType
from backend.core.database_manager import DatabaseManager
from backend.core.session_manager import SessionManager

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8096


async def run_agent_stream(
    client: anthropic.AsyncAnthropic,
    system: str,
    messages: list[dict],
    executor: ToolExecutor,
    thread_id: str,
    run_id: str,
    session_mgr: SessionManager,
) -> AsyncGenerator[str, None]:
    """
    Streaming agent loop with multi-turn tool use.
    Yields AG-UI SSE event strings.
    """
    working_messages = [m for m in messages if m["role"] in ("user", "assistant")]

    yield AGUIEvent.sse(AGUIEventType.RUN_STARTED, {"threadId": thread_id, "runId": run_id})

    try:
        while True:
            msg_id = str(uuid.uuid4())[:8]
            text_started = False
            full_text = ""
            tool_calls_by_index: dict[int, dict] = {}

            yield AGUIEvent.sse(AGUIEventType.STEP_STARTED, {"stepName": "llm_call"})

            async with client.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=[
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=working_messages,
                tools=TOOL_DEFINITIONS,
            ) as stream:
                async for event in stream:
                    etype = event.type

                    if etype == "content_block_start":
                        block = event.content_block
                        idx = event.index
                        if block.type == "text":
                            text_started = True
                            yield AGUIEvent.sse(
                                AGUIEventType.TEXT_MESSAGE_START,
                                {"messageId": msg_id, "role": "assistant"},
                            )
                        elif block.type == "tool_use":
                            tool_calls_by_index[idx] = {
                                "id": block.id,
                                "name": block.name,
                                "args_str": "",
                            }
                            yield AGUIEvent.sse(
                                AGUIEventType.TOOL_CALL_START,
                                {
                                    "toolCallId": block.id,
                                    "toolCallName": block.name,
                                    "parentMessageId": msg_id,
                                },
                            )

                    elif etype == "content_block_delta":
                        delta = event.delta
                        idx = event.index
                        if delta.type == "text_delta":
                            full_text += delta.text
                            yield AGUIEvent.sse(
                                AGUIEventType.TEXT_MESSAGE_CONTENT,
                                {"messageId": msg_id, "delta": delta.text},
                            )
                        elif delta.type == "input_json_delta":
                            tc = tool_calls_by_index.get(idx)
                            if tc:
                                tc["args_str"] += delta.partial_json
                                yield AGUIEvent.sse(
                                    AGUIEventType.TOOL_CALL_ARGS,
                                    {"toolCallId": tc["id"], "delta": delta.partial_json},
                                )

                    elif etype == "content_block_stop":
                        idx = event.index
                        if text_started and idx not in tool_calls_by_index:
                            yield AGUIEvent.sse(
                                AGUIEventType.TEXT_MESSAGE_END, {"messageId": msg_id}
                            )
                            text_started = False

                final_msg = await stream.get_final_message()

            yield AGUIEvent.sse(AGUIEventType.STEP_FINISHED, {"stepName": "llm_call"})

            # Append assistant turn to working messages
            working_messages.append({"role": "assistant", "content": final_msg.content})

            # Save text to session
            if full_text:
                session_mgr.add_message(thread_id, "assistant", full_text)

            # Done if no tool use
            if final_msg.stop_reason != "tool_use":
                break

            # Execute tools
            tool_results = []
            for block in final_msg.content:
                if block.type != "tool_use":
                    continue

                yield AGUIEvent.sse(AGUIEventType.STEP_STARTED, {"stepName": f"tool:{block.name}"})

                result = await executor.execute(block.name, block.input)

                # Emit custom events for charts / reports
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

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, default=str),
                })

                yield AGUIEvent.sse(AGUIEventType.TOOL_CALL_END, {"toolCallId": block.id})
                yield AGUIEvent.sse(AGUIEventType.STEP_FINISHED, {"stepName": f"tool:{block.name}"})

            working_messages.append({"role": "user", "content": tool_results})

            # Emit state snapshot
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
