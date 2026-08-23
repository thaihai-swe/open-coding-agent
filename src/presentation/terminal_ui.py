from __future__ import annotations

import json
import re
import select
import sys
from collections.abc import Callable
from typing import Any

from ..tools.permissions import AuthorizeDecision, AuthorizeOption

_ENTER = "enter"
_NEWLINE = "newline"
_BACKSPACE = "backspace"
_EOF = "eof"
_IGNORE = "ignore"


def _has_shift(modifier: int) -> bool:
    return bool((max(modifier, 1) - 1) & 1)


def _key_from_csi(params: str, final: str) -> str:
    parts: list[int] = []
    if params:
        for item in params.split(";"):
            parts.append(int(item) if item.isdigit() else 0)
    if final == "~" and len(parts) >= 3 and parts[0] == 27 and parts[2] == 13:
        return _NEWLINE if _has_shift(parts[1]) else _ENTER
    if final == "u" and parts and parts[0] == 13:
        modifier = parts[1] if len(parts) > 1 else 1
        return _NEWLINE if _has_shift(modifier) else _ENTER
    return _IGNORE


def _read_key(read_char: Callable[[], str], timed_read: Callable[[], str] | None = None) -> str:
    timed = timed_read or read_char
    char = read_char()
    if char == "":
        return _EOF
    if char == "\r":
        return _ENTER
    if char == "\n":
        return _NEWLINE
    if char in {"\x7f", "\b"}:
        return _BACKSPACE
    if char == "\x04":
        return _EOF
    if char == "\x03":
        raise KeyboardInterrupt
    if char != "\x1b":
        return char
    nxt = timed()
    if nxt == "":
        return _IGNORE
    if nxt in {"\r", "\n"}:
        return _NEWLINE
    if nxt == "O":
        return _ENTER if timed() == "M" else _IGNORE
    if nxt != "[":
        return _IGNORE
    params = ""
    while True:
        item = timed()
        if item == "":
            return _IGNORE
        if "@" <= item <= "~":
            return _key_from_csi(params, item)
        params += item


def _edit_prompt(read_char: Callable[[], str], write: Callable[[str], None], timed_read: Callable[[], str] | None = None) -> str:
    write("> ")
    lines = [""]
    while True:
        key = _read_key(read_char, timed_read)
        if key in {_ENTER, _EOF}:
            write("\n")
            return "\n".join(lines)
        if key == _NEWLINE:
            lines.append("")
            write("\n> ")
            continue
        if key == _BACKSPACE:
            if lines[-1]:
                lines[-1] = lines[-1][:-1]
                write("\b \b")
            elif len(lines) > 1:
                lines.pop()
                write(f"\r\033[K\033[A\r> {lines[-1]}")
            continue
        if key == _IGNORE or len(key) != 1 or key < " ":
            continue
        lines[-1] += key
        write(key)


def _read_stdin_char(timeout: float | None) -> str:
    if timeout is not None and not select.select([sys.stdin], [], [], timeout)[0]:
        return ""
    first = sys.stdin.buffer.read(1)
    if not first:
        return ""
    lead = first[0]
    if lead < 0x80:
        return first.decode("ascii")
    if 0xC0 <= lead < 0xE0:
        need = 1
    elif 0xE0 <= lead < 0xF0:
        need = 2
    elif 0xF0 <= lead < 0xF8:
        need = 3
    else:
        return "\ufffd"
    extra = sys.stdin.buffer.read(need)
    return (first + extra).decode("utf-8", "replace")


class TerminalUI:
    def __init__(self, input_fn: Callable[[str], str] = input, output=None, json_mode: bool = False, show_tool_results: bool = True) -> None:
        self.input_fn = input_fn
        self.output = output or sys.stdout
        self.json_mode = json_mode
        self.show_tool_results = show_tool_results

    def prompt(self) -> str:
        if self.input_fn is input:
            try:
                interactive = sys.stdin.isatty()
            except Exception:
                interactive = False
            if interactive:
                try:
                    return self._prompt_tty()
                except ImportError:
                    pass
        return self._prompt_line()

    def _prompt_line(self) -> str:
        try:
            return self.input_fn("> ")
        except (EOFError, StopIteration):
            return ""

    def _prompt_tty(self) -> str:
        import termios
        import tty

        fd = sys.stdin.fileno()
        saved = termios.tcgetattr(fd)
        stream = sys.stderr if self.json_mode else self.output
        try:
            mode = termios.tcgetattr(fd)
            mode[tty.IFLAG] &= ~(termios.ICRNL | termios.IXON | termios.ISTRIP)
            mode[tty.LFLAG] &= ~(termios.ECHO | termios.ICANON | termios.IEXTEN)
            mode[tty.CC][termios.VMIN] = 1
            mode[tty.CC][termios.VTIME] = 0
            termios.tcsetattr(fd, termios.TCSADRAIN, mode)
            stream.write("\033[>4;2m")
            stream.flush()

            def write(text: str) -> None:
                stream.write(text)
                stream.flush()

            return _edit_prompt(_read_stdin_char_blocking, write, _read_stdin_char_timed)
        finally:
            stream.write("\033[>4;0m")
            stream.flush()
            termios.tcsetattr(fd, termios.TCSADRAIN, saved)

    def authorize(self, name: str, arguments: dict[str, Any]) -> AuthorizeDecision:
        prompt = (
            f"Approve {name} {json.dumps(arguments, sort_keys=True)}?\n"
            f"[{AuthorizeOption.ALLOW_ONCE}] Yes "
            f"[{AuthorizeOption.ALLOW_ALWAYS}] Yes, don't ask again "
            f"[{AuthorizeOption.DENY_ONCE}] No "
            f"[{AuthorizeOption.DENY_ALWAYS}] No, don't ask again: "
        )
        return AuthorizeDecision.from_response(self.input_fn(prompt).strip())

    def event(self, event: dict[str, Any]) -> None:
        if self.json_mode:
            self._write(json.dumps(event, default=str))
            return
        if event["type"] == "text":
            self.output.write(self._render_markdown(event["content"]))
            self.output.flush()
        elif event["type"] in {"tool", "tool_denied"}:
            self._write(f"[{event['type']}] {event['name']} {json.dumps(event['arguments'], sort_keys=True)}")
        elif event["type"] == "tool_result":
            if not self.show_tool_results:
                return
            self._write(f"[tool_result] {event.get('name', '')} {event.get('content', '')}")
        elif event["type"] == "status":
            self._write(f"[status] {event.get('message', '')}")
        elif event["type"] == "error":
            self._write(f"Error: {event['message']}")

    def _write(self, message: str) -> None:
        self.output.write(message + "\n")
        self.output.flush()

    def _render_markdown(self, text: str) -> str:
        # ponytail: ATX headings + **bold** only; AC-021 does not require CommonMark
        rendered: list[str] = []
        for line in text.splitlines(keepends=True):
            newline = "\n" if line.endswith("\n") else ""
            body = line[:-1] if newline else line
            hashes = 0
            while hashes < len(body) and body[hashes] == "#":
                hashes += 1
            if hashes and hashes < len(body) and body[hashes] == " ":
                body = body[hashes + 1 :]
            rendered.append(re.sub(r"\*\*(.+?)\*\*", r"\1", body) + newline)
        return "".join(rendered)


def _read_stdin_char_blocking() -> str:
    return _read_stdin_char(None)


def _read_stdin_char_timed() -> str:
    return _read_stdin_char(0.05)
