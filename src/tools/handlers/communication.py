from typing import Any, Dict, List, Optional
from ..registry import Tool, registry
from ..types import MessageStatus


def send_user_message(message: str, attachments: Optional[List[Any]] = None, status: str = MessageStatus.NORMAL) -> Dict[str, Any]:
    if status not in {MessageStatus.NORMAL, MessageStatus.PROACTIVE}:
        raise ValueError("status must be normal or proactive")
    return {"message": message, "status": status}


TOOLS = [Tool("send_user_message", "Communication", "LOW", "Sends user message", {"required": ["message"], "properties": {"message": {"type": "string"}}}, send_user_message)]

for tool in TOOLS:
    registry.register(tool)
