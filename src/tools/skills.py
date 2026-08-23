from __future__ import annotations

from pathlib import Path
from typing import Any

from .task_board import SYSTEM_MESSAGE as PLANNING_SYSTEM_MESSAGE
# PLANNING_SYSTEM_MESSAGE kept for callers that import it via this module.


def parse_frontmatter(text: str, default_name: str) -> tuple[dict[str, str], str]:
    meta: dict[str, str] = {}
    body = text

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            body = parts[2].lstrip("\r\n")
            for line in fm_text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip()
                    val = val.strip()
                    # Strip single/double quotes if present
                    if len(val) >= 2 and ((val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'")):
                        val = val[1:-1].strip()
                    if key in {"name", "description", "when_to_use", "tags"}:
                        meta[key] = val

    name = meta.get("name") or default_name
    meta["name"] = name

    desc = meta.get("description")
    if not desc:
        # Fallback to first markdown heading or first non-empty line of body
        found_desc = ""
        for line in body.splitlines():
            s = line.strip()
            if not s:
                continue
            if s.startswith("#"):
                found_desc = s.lstrip("#").strip()
                break
            if not found_desc:
                found_desc = s
                break
        desc = found_desc or name
        meta["description"] = desc

    return meta, body


def scan_skills(
    project_root: Path | None = None,
    global_root: Path | None = None,
) -> dict[str, dict[str, Any]]:
    p_root = Path.cwd() / ".agents" / "skills" if project_root is None else project_root
    g_root = Path.home() / ".agents" / "skills" if global_root is None else global_root

    skills: dict[str, dict[str, Any]] = {}

    # Scan global root first
    if g_root.exists() and g_root.is_dir():
        try:
            for item in sorted(g_root.iterdir()):
                if item.is_dir():
                    manifest = item / "SKILL.md"
                    if manifest.is_file():
                        try:
                            raw = manifest.read_text(encoding="utf-8")
                            meta, _ = parse_frontmatter(raw, item.name)
                            skills[meta["name"]] = {
                                "name": meta["name"],
                                "description": meta.get("description", ""),
                                "when_to_use": meta.get("when_to_use"),
                                "content": raw,
                                "path": str(manifest),
                            }
                        except (OSError, UnicodeDecodeError):
                            continue
        except OSError:
            pass

    # Scan project root second (project overrides global on name collision)
    if p_root.exists() and p_root.is_dir():
        try:
            for item in sorted(p_root.iterdir()):
                if item.is_dir():
                    manifest = item / "SKILL.md"
                    if manifest.is_file():
                        try:
                            raw = manifest.read_text(encoding="utf-8")
                            meta, _ = parse_frontmatter(raw, item.name)
                            skills[meta["name"]] = {
                                "name": meta["name"],
                                "description": meta.get("description", ""),
                                "when_to_use": meta.get("when_to_use"),
                                "content": raw,
                                "path": str(manifest),
                            }
                        except (OSError, UnicodeDecodeError):
                            continue
        except OSError:
            pass

    return skills


def format_catalog(skills: dict[str, dict[str, Any]] | None = None) -> str:
    if skills is None:
        skills = scan_skills()

    if not skills:
        return "Skills available:\n(no skills found)"

    lines = ["Skills available:"]
    for name in sorted(skills.keys()):
        s = skills[name]
        desc = s.get("description", "")
        wtu = s.get("when_to_use")
        if wtu:
            lines.append(f"- **{name}**: {desc} (when to use: {wtu})")
        else:
            lines.append(f"- **{name}**: {desc}")
    lines.append("Use load_skill to get full details when needed.")
    return "\n".join(lines)


def load_skill_content(name: str, skills: dict[str, dict[str, Any]] | None = None) -> str:
    if skills is None:
        skills = scan_skills()
    if name in skills:
        return str(skills[name]["content"])
    raise ValueError(f"Skill not found: {name}")


def build_system_message(skills: dict[str, dict[str, Any]] | None = None) -> str:
    from .prompt import assemble_system_prompt

    return assemble_system_prompt(skills=skills)


def expand_slash_prompt(
    prompt: str,
    skills: dict[str, dict[str, Any]] | None = None,
) -> tuple[str | None, str | None]:
    if not prompt.startswith("/"):
        return prompt, None

    rest = prompt[1:]
    parts = rest.split(None, 1)
    if not parts:
        return None, "Unknown skill: /"

    cmd = parts[0]
    args = parts[1] if len(parts) > 1 else None

    if skills is None:
        skills = scan_skills()

    if cmd in skills:
        content = skills[cmd]["content"]
        wrapper = f'<skill name="{cmd}">\n{content}\n</skill>'
        expanded = f"{wrapper}\n{args}" if args else wrapper
        return expanded, None

    return None, f"Unknown skill: /{cmd}"
