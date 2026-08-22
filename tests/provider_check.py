import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.domain.errors import ProviderError
from src.domain.models import ChatMessage, ToolCall
from src.infrastructure.providers import OpenAIProvider


class TestProvider(unittest.TestCase):
    @patch.dict(os.environ, {"OPENAI_API_BASE": "https://api.openai.com/v1", "OPENAI_API_KEY": "secret-key", "OPENAI_MODEL": "gpt-4o"})
    @patch("urllib.request.urlopen")
    def test_complete_non_streaming(self, mock_urlopen: unittest.mock.MagicMock) -> None:
        payload = {"choices": [{"message": {"content": "Hello", "tool_calls": [{"id": "call-1", "function": {"name": "read_file", "arguments": '{"file_path": "a.txt"}'}}]}, "finish_reason": "tool_calls"}]}
        mock_urlopen.return_value = io.BytesIO(json.dumps(payload).encode("utf-8"))
        provider = OpenAIProvider()
        response = provider.complete([ChatMessage("user", "read file")], tools=[])
        self.assertEqual(response.message.content, "Hello")
        self.assertEqual(response.message.tool_calls, (ToolCall("call-1", "read_file", {"file_path": "a.txt"}),))
        self.assertNotIn("secret-key", str(response))

    @patch.dict(os.environ, {"OPENAI_API_BASE": "https://api.openai.com/v1", "OPENAI_API_KEY": "secret-key", "OPENAI_MODEL": "gpt-4o"})
    @patch("urllib.request.urlopen")
    def test_complete_streaming(self, mock_urlopen: unittest.mock.MagicMock) -> None:
        sse_lines = [
            b'data: {"choices": [{"delta": {"content": "Hel"}}]}\n',
            b'data: {"choices": [{"delta": {"content": "lo"}}]}\n',
            b'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call-1", "function": {"name": "read_file", "arguments": "{\\"file_path\\""}}]}}]}\n',
            b'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": ": \\"a.txt\\"}"}}]}}]}\n',
            b'data: [DONE]\n',
        ]
        mock_urlopen.return_value = sse_lines
        provider = OpenAIProvider()
        deltas = list(provider.complete([ChatMessage("user", "read file")], tools=[], stream=True))
        text = "".join(delta.content for delta in deltas)
        self.assertEqual(text, "Hello")
        final = deltas[-1]
        self.assertTrue(final.done)
        self.assertEqual(final.tool_calls, (ToolCall("call-1", "read_file", {"file_path": "a.txt"}),))

    def test_json_configuration(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps({"openai_api_base": "http://local", "openai_api_key": "json-key", "openai_model": "json-model"}), encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                provider = OpenAIProvider(config_path=path)
            self.assertEqual((provider.api_base, provider.api_key, provider.model), ("http://local", "json-key", "json-model"))

    def test_environment_overrides_json(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps({"openai_api_base": "http://local", "openai_api_key": "json-key", "openai_model": "json-model"}), encoding="utf-8")
            with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}, clear=True):
                provider = OpenAIProvider(config_path=path)
            self.assertEqual(provider.api_key, "env-key")

    def test_invalid_json_configuration(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text("not json", encoding="utf-8")
            with self.assertRaises(ProviderError):
                OpenAIProvider(config_path=path)

    def test_empty_choices_raises_actionable_provider_error(self) -> None:
        import urllib.error

        with patch.dict(os.environ, {"OPENAI_API_BASE": "https://api.openai.com/v1", "OPENAI_API_KEY": "secret-key", "OPENAI_MODEL": "gpt-4o"}):
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_urlopen.return_value = io.BytesIO(b'{"choices": []}')
                provider = OpenAIProvider()
                with self.assertRaises(ProviderError) as ctx:
                    provider.complete([ChatMessage("user", "hi")], tools=[])
                self.assertIn("contains no choices", str(ctx.exception))

    def test_http_error_response_raises_actionable_provider_error(self) -> None:
        import urllib.error

        with patch.dict(os.environ, {"OPENAI_API_BASE": "https://api.openai.com/v1", "OPENAI_API_KEY": "secret-key", "OPENAI_MODEL": "gpt-4o"}):
            with patch("urllib.request.urlopen") as mock_urlopen:
                fp = io.BytesIO(b'{"error": {"message": "Invalid API key provided"}}')
                mock_urlopen.side_effect = urllib.error.HTTPError("http://api", 401, "Unauthorized", {}, fp)
                provider = OpenAIProvider()
                with self.assertRaises(ProviderError) as ctx:
                    provider.complete([ChatMessage("user", "hi")], tools=[])
                self.assertIn("HTTP 401", str(ctx.exception))
                self.assertIn("Invalid API key provided", str(ctx.exception))
                self.assertNotIn("secret-key", str(ctx.exception))

    def test_missing_environment(self) -> None:
        with patch.dict(os.environ, {"CONFIG_FILE": "/tmp/nonexistent-openai-config.json"}, clear=True):
            with self.assertRaises(ProviderError):
                OpenAIProvider()


if __name__ == "__main__":
    unittest.main()
