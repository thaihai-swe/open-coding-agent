from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from .models import ChatMessage, ProviderResponse, StreamDelta


class Provider(Protocol):
    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]],
        stream: bool = False,
    ) -> ProviderResponse | Iterable[StreamDelta]:
        ...
