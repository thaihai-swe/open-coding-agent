from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .registry import Tool, registry
from .skills import format_catalog
from .task_board import SYSTEM_MESSAGE as PLANNING_SYSTEM_MESSAGE

INSTRUCTION_FILENAMES = ("AGENTS.md", "CLAUDE.md", "CLAUDE.local.md")
MAX_FILE_CHARS = 4000
MAX_TOTAL_INSTRUCTION_CHARS = 12000
PROMPT_SECTIONS = ("identity", "planning", "security")
OVERRIDE_PROMPTS_DIR = Path(".cda") / "prompts"
DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
FALLBACK_SECTIONS: dict[str, str] = {
    "identity": "You are a coding agent. Act, don't explain.",
    "planning": PLANNING_SYSTEM_MESSAGE,
    "security": (
        "Security & Permission Policies:\n"
        "- File and search tools are restricted to the working directory. Paths outside the workspace are refused.\n"
        "- Dangerous shell commands and disk operations matching the deny list are blocked.\n"
        "- Operations targeting protected paths and sensitive configuration keys are blocked.\n"
        "- High-risk and medium-risk tool operations require explicit user authorization."
    ),
}


def _read_markdown(path: Path) -> str | None:
    try:
        if not path.is_file():
            return None
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return text.rstrip("\n")


def load_prompt_section(name: str, cwd: Path | None = None) -> str:
    """Load a named prompt section from project override, then bundled default.

    Resolution order:
    1. `{cwd}/.cda/prompts/{name}.md` (user override)
    2. `src/prompts/{name}.md` (bundled default)
    3. `FALLBACK_SECTIONS[name]` (inline safety fallback)
    """
    root = Path.cwd() if cwd is None else cwd
    override = _read_markdown(root / OVERRIDE_PROMPTS_DIR / f"{name}.md")
    if override:
        return override
    bundled = _read_markdown(DEFAULT_PROMPTS_DIR / f"{name}.md")
    if bundled:
        return bundled
    return FALLBACK_SECTIONS.get(name, "")


def discover_instructions(cwd: Path | None = None) -> list[tuple[str, str]]:
    root = Path.cwd() if cwd is None else cwd
    instructions: list[tuple[str, str]] = []
    seen_hashes: set[str] = set()
    total_chars = 0

    for filename in INSTRUCTION_FILENAMES:
        file_path = root / filename
        if not file_path.is_file():
            continue
        try:
            raw = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        content_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        if content_hash in seen_hashes:
            continue
        seen_hashes.add(content_hash)

        remaining_budget = MAX_TOTAL_INSTRUCTION_CHARS - total_chars
        if remaining_budget <= 0:
            break

        allowed_chars = min(len(raw), MAX_FILE_CHARS, remaining_budget)
        is_truncated = (allowed_chars < len(raw))

        body_slice = raw[:allowed_chars]
        if is_truncated:
            body_slice = f"{body_slice}\n[... TRUNCATED ...]"

        instructions.append((filename, body_slice))
        total_chars += allowed_chars

    return instructions


def format_security_section(cwd: Path | None = None) -> str:
    return load_prompt_section("security", cwd)


def format_tools_section(tools: list[Tool] | None = None) -> str:
    tool_list = list(registry.tools.values()) if tools is None else tools
    lines = ["Available tools:"]
    for t in sorted(tool_list, key=lambda x: x.name):
        lines.append(f"- {t.name}: {t.description}")
    return "\n".join(lines)


def assemble_system_prompt(
    cwd: Path | None = None,
    tools: list[Tool] | None = None,
    skills: dict[str, dict[str, Any]] | None = None,
) -> str:
    root = Path.cwd() if cwd is None else cwd
    resolved_cwd = str(root.resolve())

    sections: list[str] = [
        load_prompt_section("identity", root),
        f"Working directory: {resolved_cwd}",
        load_prompt_section("planning", root),
        format_security_section(root),
        format_tools_section(tools),
        format_catalog(skills),
    ]

    instructions = discover_instructions(root)
    if instructions:
        instruction_lines = ["Instructions:"]
        for name, content in instructions:
            instruction_lines.append(f"### {name}\n{content}")
        sections.append("\n\n".join(instruction_lines))

    return "\n\n".join(sections)
