from dataclasses import dataclass
from typing import Tuple
from .tool_call import ToolCall


@dataclass(frozen=True)
class StreamDelta:
    content: str = ""
    tool_calls: Tuple[ToolCall, ...] = ()
    done: bool = False
