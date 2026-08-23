"""Zero-dependency ANSI terminal rendering helpers."""

from __future__ import annotations

import os
import re
import sys
from typing import Callable, Iterable, List, Optional, Sequence


_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def supports_color(stream=None) -> bool:
    stream = stream or sys.stdout
    if not hasattr(stream, "isatty") or not stream.isatty():
        return False
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("CI", "").lower() in {"1", "true", "yes"}:
        return False
    if os.environ.get("TERM", "") in {"", "dumb"}:
        return False
    return True


COLOR = supports_color()


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", str(text))


def _wrap(code: str, text: str) -> str:
    if not COLOR:
        return str(text)
    return f"\033[{code}m{text}\033[0m"


def dim(text: str) -> str:
    return _wrap("2", text)


def bold(text: str) -> str:
    return _wrap("1", text)


def fg_red(text: str) -> str:
    return _wrap("31", text)


def fg_green(text: str) -> str:
    return _wrap("32", text)


def fg_yellow(text: str) -> str:
    return _wrap("33", text)


def fg_blue(text: str) -> str:
    return _wrap("34", text)



def bar(
    used: float,
    total: float,
    width: int = 30,
    color_fn: Optional[Callable[[str], str]] = None,
    label: str = "",
) -> str:
    """Render a Unicode block progress bar with plain fallback."""
    if total <= 0:
        pct = 0.0
    else:
        pct = max(0.0, min(1.0, float(used) / float(total)))
    filled = int(round(width * pct))
    empty = max(0, width - filled)
    if COLOR:
        painter = color_fn or fg_green
        blocks = painter("█" * filled) + dim("░" * empty)
        core = f"{blocks} {int(pct * 100)}%"
    else:
        core = f"[{'#' * filled}{'-' * empty}] {int(pct * 100)}%"
    if label:
        return f"{core} {label}"
    return core


def table(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    """Render an auto-sizing text table."""
    materialised = [list(row) for row in rows]
    if not materialised:
        return ""
    widths = [len(strip_ansi(h)) for h in headers]
    for row in materialised:
        for idx, cell in enumerate(row):
            if idx >= len(widths):
                continue
            widths[idx] = max(widths[idx], len(strip_ansi(cell)))

    def _pad(cell: object, width: int) -> str:
        text = str(cell)
        pad = width - len(strip_ansi(text))
        return text + (" " * max(0, pad))

    lines = [
        " | ".join(bold(_pad(header, widths[idx])) for idx, header in enumerate(headers)),
        "-+-".join("-" * width for width in widths),
    ]
    for row in materialised:
        lines.append(
            " | ".join(_pad(row[idx] if idx < len(row) else "", widths[idx]) for idx in range(len(headers)))
        )
    return "\n".join(lines)


def tree(nodes: Sequence[dict], prefix: str = "") -> str:
    """Render a simple dependency/status tree.

    Each node is ``{"label": str, "children": [node, ...]}``.
    """
    lines: List[str] = []
    total = len(nodes)
    for index, node in enumerate(nodes):
        is_last = index == total - 1
        branch = "└─ " if is_last else "├─ "
        lines.append(f"{prefix}{branch}{node.get('label', '')}")
        children = node.get("children") or []
        if children:
            child_prefix = prefix + ("   " if is_last else "│  ")
            child_text = tree(children, child_prefix)
            if child_text:
                lines.append(child_text)
    return "\n".join(lines)


def status_icon(status: str) -> str:
    key = (status or "").strip().lower()
    if key in {"done", "pass", "passed", "ok", "closed"}:
        return fg_green("✔")
    if key in {"fail", "failed", "error", "blocked"}:
        return fg_red("✖")
    if key in {"warn", "warning", "open"}:
        return fg_yellow("!")
    if key in {"in progress", "running", "active"}:
        return fg_blue("•")
    return dim("·")
