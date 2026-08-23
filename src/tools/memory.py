from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..domain.models import ChatMessage, ProviderResponse
from ..domain.provider import Provider

MEMORY_TYPES = ("user", "feedback", "project", "reference")
MEMORY_DIR_NAME = Path(".cda") / "memory"
MEMORY_INDEX_NAME = Path(".cda") / "memory" / "MEMORY.md"


@dataclass(frozen=True)
class Memory:
    name: str
    description: str
    type: str
    body: str
    filename: str


def sanitize_slug(name: str) -> str:
    """Convert a memory name into a safe filename slug within .cda/memory."""
    # Convert to lower case, replace spaces and slashes with hyphens
    slug = name.strip().lower().replace(" ", "-").replace("/", "-").replace("\\", "-")
    # Remove any directory traversal sequences
    slug = slug.replace("..", "")
    # Remove any non-alphanumeric chars except - and _
    slug = re.sub(r"[^a-z0-9_-]", "", slug)
    # Strip leading/trailing hyphens/underscores
    slug = slug.strip("-_")
    if not slug:
        slug = "memory"
    return f"{slug}.md"


def parse_memory_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse YAML-like frontmatter from markdown text."""
    if not text.startswith("---"):
        return {}, text.strip()
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text.strip()
    meta: dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, parts[2].strip()


def write_memory_file(
    name: str,
    mem_type: str,
    description: str,
    body: str,
    cwd: Path | str | None = None,
) -> Path:
    """Write a single memory file with YAML frontmatter and rebuild MEMORY.md."""
    root = Path.cwd() if cwd is None else Path(cwd)
    memory_dir = root / MEMORY_DIR_NAME
    memory_dir.mkdir(parents=True, exist_ok=True)

    filename = sanitize_slug(name)
    target = (memory_dir / filename).resolve()
    # Path traversal protection: target must be inside memory_dir
    if not target.is_relative_to(memory_dir.resolve()):
        target = memory_dir / "memory.md"

    valid_type = mem_type if mem_type in MEMORY_TYPES else "user"
    clean_name = name.strip() or target.stem
    clean_desc = description.strip() or body.split("\n")[0][:80]

    content = (
        f"---\n"
        f"name: {clean_name}\n"
        f"description: {clean_desc}\n"
        f"type: {valid_type}\n"
        f"---\n\n"
        f"{body.strip()}\n"
    )
    target.write_text(content, encoding="utf-8")
    rebuild_memory_index(root)
    return target


def read_memory_file(filename: str, cwd: Path | str | None = None) -> str | None:
    """Read full raw content of a single memory file."""
    root = Path.cwd() if cwd is None else Path(cwd)
    memory_dir = root / MEMORY_DIR_NAME
    target = (memory_dir / Path(filename).name).resolve()
    if not target.is_relative_to(memory_dir.resolve()) or not target.is_file():
        return None
    try:
        return target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def list_memory_files(cwd: Path | str | None = None) -> list[Memory]:
    """List all memory files with metadata, sorted by filename."""
    root = Path.cwd() if cwd is None else Path(cwd)
    memory_dir = root / MEMORY_DIR_NAME
    if not memory_dir.is_dir():
        return []

    result: list[Memory] = []
    for f in sorted(memory_dir.glob("*.md")):
        if f.name == "MEMORY.md":
            continue
        try:
            raw = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        meta, body = parse_memory_frontmatter(raw)
        name = meta.get("name", f.stem)
        desc = meta.get("description", body.split("\n")[0][:80] if body else "")
        mem_type = meta.get("type", "user")
        result.append(
            Memory(
                name=name,
                description=desc,
                type=mem_type if mem_type in MEMORY_TYPES else "user",
                body=body,
                filename=f.name,
            )
        )
    return result


def read_memory_index(cwd: Path | str | None = None) -> str:
    """Read MEMORY.md index content."""
    root = Path.cwd() if cwd is None else Path(cwd)
    target = root / MEMORY_INDEX_NAME
    try:
        if not target.is_file():
            return ""
        return target.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return ""


def rebuild_memory_index(cwd: Path | str | None = None) -> str:
    """Rebuild MEMORY.md index from all memory files in .cda/memory."""
    root = Path.cwd() if cwd is None else Path(cwd)
    memory_dir = root / MEMORY_DIR_NAME
    if not memory_dir.is_dir():
        return ""

    lines: list[str] = []
    for f in sorted(memory_dir.glob("*.md")):
        if f.name == "MEMORY.md":
            continue
        try:
            raw = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        meta, body = parse_memory_frontmatter(raw)
        name = meta.get("name", f.stem)
        desc = meta.get("description", body.split("\n")[0][:80] if body else "")
        lines.append(f"- [{name}]({f.name}) — {desc}")

    index_file = root / MEMORY_INDEX_NAME
    index_content = "\n".join(lines) + ("\n" if lines else "")
    try:
        index_file.write_text(index_content, encoding="utf-8")
    except OSError:
        pass
    return index_content.strip()


def _extract_response_text(response: Any) -> str:
    if isinstance(response, ProviderResponse):
        return response.message.content or ""
    collected = []
    for delta in response:
        if delta.content:
            collected.append(delta.content)
    return "".join(collected).strip()


def select_relevant_memories(
    provider: Provider,
    messages: list[ChatMessage],
    cwd: Path | str | None = None,
    max_items: int = 5,
) -> list[str]:
    """Select relevant memory filenames by matching recent conversation against catalog."""
    files = list_memory_files(cwd)
    if not files or max_items <= 0:
        return []

    # Collect recent user text (up to 3 user messages, max 2000 chars)
    recent_texts: list[str] = []
    for msg in reversed(messages):
        if msg.role == "user" and msg.content:
            recent_texts.append(msg.content)
            if len(recent_texts) >= 3:
                break
    recent = " ".join(reversed(recent_texts))[:2000].strip()
    if not recent:
        return []

    catalog_lines = [f"{i}: {f.name} — {f.description}" for i, f in enumerate(files)]
    catalog = "\n".join(catalog_lines)

    prompt = (
        "Given the recent conversation and the memory catalog below, "
        "select the indices of memories that are clearly relevant. "
        "Return ONLY a JSON array of integers, e.g. [0, 3]. "
        "If none are relevant, return [].\n\n"
        f"Recent conversation:\n{recent}\n\n"
        f"Memory catalog:\n{catalog}"
    )

    try:
        prompt_msg = ChatMessage("user", prompt)
        res = provider.complete([prompt_msg], tools=[], stream=False)
        text = _extract_response_text(res)
        match = re.search(r"\[.*?\]", text, re.DOTALL)
        if match:
            indices = json.loads(match.group())
            selected: list[str] = []
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(files):
                    selected.append(files[idx].filename)
                    if len(selected) >= max_items:
                        break
            return selected
    except Exception:
        pass

    # Fallback: keyword matching on name + description
    keywords = [w.lower() for w in re.findall(r"\w+", recent) if len(w) > 3]
    selected = []
    for f in files:
        combined = f"{f.name} {f.description}".lower()
        if any(kw in combined for kw in keywords):
            selected.append(f.filename)
            if len(selected) >= max_items:
                break
    return selected


def format_relevant_memories(filenames: list[str], cwd: Path | str | None = None) -> str:
    """Load full content of selected memory files and wrap in XML tags."""
    if not filenames:
        return ""
    parts = ["<relevant_memories>"]
    for filename in filenames:
        content = read_memory_file(filename, cwd)
        if content:
            parts.append(content.strip())
    if len(parts) == 1:
        return ""
    parts.append("</relevant_memories>")
    return "\n\n".join(parts)


def extract_memories(
    provider: Provider,
    messages: list[ChatMessage],
    cwd: Path | str | None = None,
) -> int:
    """Extract new memories from recent dialogue snapshot. Runs on turn completion."""
    dialogue_parts: list[str] = []
    for msg in messages[-10:]:
        role = msg.role
        content = msg.content or ""
        if content.strip():
            dialogue_parts.append(f"{role}: {content.strip()}")
    dialogue = "\n".join(dialogue_parts)[:4000].strip()
    if not dialogue:
        return 0

    existing = list_memory_files(cwd)
    existing_desc = (
        "\n".join(f"- {m.name}: {m.description}" for m in existing)
        if existing
        else "(none)"
    )

    prompt = (
        "Extract user preferences, constraints, or project facts from this dialogue.\n"
        "Return a JSON array. Each item: {name, type, description, body}.\n"
        "- name: short kebab-case identifier (e.g. 'user-preference-tabs')\n"
        "- type: one of 'user' (user preference), 'feedback' (guidance), 'project' (project fact), 'reference' (external pointer)\n"
        "- description: one-line summary for index lookup\n"
        "- body: full detail in markdown\n"
        "If nothing new or already covered by existing memories, return [].\n\n"
        f"Existing memories:\n{existing_desc}\n\n"
        f"Dialogue:\n{dialogue}"
    )

    try:
        prompt_msg = ChatMessage("user", prompt)
        res = provider.complete([prompt_msg], tools=[], stream=False)
        text = _extract_response_text(res)
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            return 0
        items = json.loads(match.group())
        if not isinstance(items, list):
            return 0
        count = 0
        for mem in items:
            if not isinstance(mem, dict):
                continue
            name = mem.get("name") or f"memory_{count + 1}"
            mem_type = mem.get("type", "user")
            desc = mem.get("description", "")
            body = mem.get("body", "")
            if desc and body:
                write_memory_file(name, mem_type, desc, body, cwd)
                count += 1
        return count
    except Exception:
        return 0


def consolidate_memories(
    provider: Provider,
    cwd: Path | str | None = None,
    threshold: int = 10,
) -> tuple[int, int]:
    """Merge duplicate/stale memories when file count reaches threshold."""
    files = list_memory_files(cwd)
    old_count = len(files)
    if old_count < threshold:
        return old_count, old_count

    catalog_parts = []
    for f in files:
        catalog_parts.append(
            f"## {f.filename}\nname: {f.name}\ntype: {f.type}\ndescription: {f.description}\n{f.body}"
        )
    catalog = "\n\n".join(catalog_parts)[:16000]

    prompt = (
        "Consolidate the following memory files. Rules:\n"
        "1. Merge duplicates into one\n"
        "2. Remove outdated/contradicted memories\n"
        "3. Keep the total under 30 memories\n"
        "4. Preserve important user preferences above all\n"
        "Return a JSON array. Each item: {name, type, description, body}.\n\n"
        f"{catalog}"
    )

    try:
        prompt_msg = ChatMessage("user", prompt)
        res = provider.complete([prompt_msg], tools=[], stream=False)
        text = _extract_response_text(res)
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            return old_count, old_count
        items = json.loads(match.group())
        if not isinstance(items, list) or not items:
            return old_count, old_count

        root = Path.cwd() if cwd is None else Path(cwd)
        memory_dir = root / MEMORY_DIR_NAME
        # Remove old memory files (keep MEMORY.md)
        for f in memory_dir.glob("*.md"):
            if f.name != "MEMORY.md":
                try:
                    f.unlink()
                except OSError:
                    pass

        new_count = 0
        for mem in items:
            if not isinstance(mem, dict):
                continue
            name = mem.get("name") or f"memory_{new_count + 1}"
            mem_type = mem.get("type", "user")
            desc = mem.get("description", "")
            body = mem.get("body", "")
            if desc and body:
                write_memory_file(name, mem_type, desc, body, cwd)
                new_count += 1
        return old_count, new_count
    except Exception:
        return old_count, old_count
