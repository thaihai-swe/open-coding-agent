from __future__ import annotations

import json
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib import error as urllib_error, request

from ...domain.errors import ProviderError
from ...domain.models import ChatMessage, ProviderResponse, StreamDelta, ToolCall


class OpenAIProvider:
    def __init__(self, api_base: str | None = None, api_key: str | None = None, model: str | None = None, config_path: str | Path | None = None) -> None:
        cfg = _load_config(config_path)
        self.api_base = api_base if api_base is not None else os.environ.get("OPENAI_API_BASE", cfg.get("openai_api_base", ""))
        self.api_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", cfg.get("openai_api_key", ""))
        self.model = model if model is not None else os.environ.get("OPENAI_MODEL", cfg.get("openai_model", ""))
        if not self.api_base or not self.api_key or not self.model:
            raise ProviderError("Set OPENAI_API_BASE, OPENAI_API_KEY, and OPENAI_MODEL or configure .cda/.secrets/config.json.")

    def complete(self, messages: list[ChatMessage], tools: list[dict[str, Any]], stream: bool = False) -> ProviderResponse | Iterable[StreamDelta]:
        url = self.api_base.rstrip("/") + "/chat/completions"
        payload = {"model": self.model, "messages": [_message_payload(message) for message in messages], "tools": tools, "stream": stream}
        req = request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, method="POST")
        try:
            response = request.urlopen(req)
        except urllib_error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            message = _extract_error_message(body) or error.reason
            raise ProviderError(f"Provider HTTP {error.code} at {url}: {message}") from error
        except Exception as error:
            raise ProviderError(f"Provider request failed at {url}: {error}") from error

        if stream:
            return self._stream(response, url)

        try:
            raw_body = response.read().decode("utf-8")
            data = json.loads(raw_body)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ProviderError(f"Invalid JSON response from {url}: {error}") from error

        return _response_from_payload(data, url)

    def _stream(self, response: Any, url: str) -> Iterable[StreamDelta]:
        calls: dict[int, dict[str, str]] = {}
        try:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    yield StreamDelta(tool_calls=_assembled_calls(calls), done=True)
                    return
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError as error:
                    raise ProviderError(f"Invalid SSE JSON payload from {url}: {error}") from error
                if "error" in data and isinstance(data["error"], dict):
                    err_msg = data["error"].get("message") or str(data["error"])
                    raise ProviderError(f"Provider stream error from {url}: {err_msg}")
                choices = data.get("choices")
                if not isinstance(choices, list) or not choices:
                    continue
                choice = choices[0]
                if not isinstance(choice, dict):
                    continue
                delta = choice.get("delta", {})
                if not isinstance(delta, dict):
                    continue
                for call in delta.get("tool_calls", []) or []:
                    if not isinstance(call, dict):
                        continue
                    item = calls.setdefault(call.get("index", 0), {"id": "", "name": "", "arguments": ""})
                    item["id"] += call.get("id", "") or ""
                    function = call.get("function", {}) or {}
                    if isinstance(function, dict):
                        item["name"] += function.get("name", "") or ""
                        item["arguments"] += function.get("arguments", "") or ""
                if delta.get("content"):
                    yield StreamDelta(content=delta["content"])
        except ProviderError:
            raise
        except Exception as error:
            raise ProviderError(f"Invalid provider stream from {url}: {error}") from error
        yield StreamDelta(tool_calls=_assembled_calls(calls), done=True)


def _load_config(config_path: str | Path | None) -> dict[str, str]:
    path = Path(config_path or os.environ.get("CONFIG_FILE", ".cda/.secrets/config.json"))
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProviderError(f"Invalid configuration file {path}: {error}") from error
    if not isinstance(payload, dict) or not all(isinstance(value, str) for value in payload.values()):
        raise ProviderError(f"Configuration file {path} must contain a JSON object with string values.")
    return payload


def _message_payload(message: ChatMessage) -> dict[str, Any]:
    payload: dict[str, Any] = {"role": message.role, "content": message.content}
    if message.tool_calls:
        payload["tool_calls"] = [{"id": call.id, "type": "function", "function": {"name": call.name, "arguments": json.dumps(call.arguments)}} for call in message.tool_calls]
    if message.tool_result:
        payload.update({"role": "tool", "tool_call_id": message.tool_result.call_id, "content": json.dumps(message.tool_result.content)})
    return payload


def _calls(raw_calls: list[dict[str, Any]]) -> tuple[ToolCall, ...]:
    return tuple(ToolCall(call["id"], call["function"]["name"], json.loads(call["function"].get("arguments") or "{}")) for call in raw_calls)


def _assembled_calls(calls: dict[int, dict[str, str]]) -> tuple[ToolCall, ...]:
    return tuple(ToolCall(call["id"], call["name"], json.loads(call["arguments"] or "{}")) for _, call in sorted(calls.items()))


def _extract_error_message(body: str) -> str:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body[:500]
    error_payload = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error_payload, dict):
        return str(error_payload.get("message") or error_payload)
    return ""


def _response_from_payload(payload: dict[str, Any], url: str) -> ProviderResponse:
    if not isinstance(payload, dict):
        raise ProviderError(f"Provider response from {url} must be a JSON object.")
    if "error" in payload:
        raise ProviderError(f"Provider error from {url}: {_extract_error_message(json.dumps(payload))}")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ProviderError(f"Provider response from {url} contains no choices: {json.dumps(payload)[:500]}")
    choice = choices[0]
    if not isinstance(choice, dict) or not isinstance(choice.get("message"), dict):
        raise ProviderError(f"Provider response from {url} has no valid message: {json.dumps(payload)[:500]}")
    message = choice["message"]
    return ProviderResponse(ChatMessage("assistant", message.get("content"), _calls(message.get("tool_calls", []))), choice.get("finish_reason"))
