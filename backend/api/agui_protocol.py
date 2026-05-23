"""
AG-UI (Agent User Interaction) Protocol implementation.
Spec: https://docs.copilotkit.ai/ag-ui
"""
import json
import time
from enum import StrEnum


class AGUIEventType(StrEnum):
    RUN_STARTED = "RUN_STARTED"
    RUN_FINISHED = "RUN_FINISHED"
    RUN_ERROR = "RUN_ERROR"
    STEP_STARTED = "STEP_STARTED"
    STEP_FINISHED = "STEP_FINISHED"
    TEXT_MESSAGE_START = "TEXT_MESSAGE_START"
    TEXT_MESSAGE_CONTENT = "TEXT_MESSAGE_CONTENT"
    TEXT_MESSAGE_END = "TEXT_MESSAGE_END"
    TOOL_CALL_START = "TOOL_CALL_START"
    TOOL_CALL_ARGS = "TOOL_CALL_ARGS"
    TOOL_CALL_END = "TOOL_CALL_END"
    STATE_SNAPSHOT = "STATE_SNAPSHOT"
    STATE_DELTA = "STATE_DELTA"
    MESSAGES_SNAPSHOT = "MESSAGES_SNAPSHOT"
    CUSTOM = "CUSTOM"


class AGUIEvent:
    @staticmethod
    def build(event_type: AGUIEventType, payload: dict) -> dict:
        return {
            "type": event_type,
            "timestamp": int(time.time() * 1000),
            **payload,
        }

    @staticmethod
    def sse(event_type: AGUIEventType, payload: dict) -> str:
        """Format as SSE data line."""
        data = AGUIEvent.build(event_type, payload)
        return f"data: {json.dumps(data)}\n\n"
