from dataclasses import dataclass
from typing import Optional
from .chat_message import ChatMessage


@dataclass(frozen=True)
class ProviderResponse:
    message: ChatMessage
    finish_reason: Optional[str] = None
