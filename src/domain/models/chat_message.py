from dataclasses import dataclass
from typing import Optional, Tuple
from .tool_call import ToolCall
from .tool_result import ToolResult


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: Optional[str] = None
    tool_calls: Tuple[ToolCall, ...] = ()
    tool_result: Optional[ToolResult] = None
