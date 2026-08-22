from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolResult:
    call_id: str
    content: Any
    is_error: bool = False
