"""Structured context-route registry readers."""
from pathlib import Path
from core._lib.yaml_reader import load as load_yaml

WRITE_OBJECT_KEYS = {"path", "required"}


def load_routes(root):
    path = Path(root) / "references" / "context-routes.yaml"
    if not path.is_file():
        return {}
    data = load_yaml(str(path)) or {}
    return data if isinstance(data, dict) else {}


def normalize_write(item):
    """Normalize one route write to {path, required, kind}."""
    if isinstance(item, str):
        path = item.strip()
        if not path:
            raise ValueError("write path must be a non-empty string")
        kind = "file" if Path(path).suffix else "directory"
        return {"path": path, "required": kind == "file", "kind": kind}
    if isinstance(item, dict):
        extra = set(item) - WRITE_OBJECT_KEYS
        if extra:
            raise ValueError("unknown write keys: " + ", ".join(sorted(extra)))
        path = str(item.get("path") or "").strip()
        if not path:
            raise ValueError("write path must be a non-empty string")
        kind = "file" if Path(path).suffix else "directory"
        if "required" in item:
            if not isinstance(item["required"], bool):
                raise ValueError(f"write required must be a boolean: {path}")
            required = item["required"]
        else:
            required = kind == "file"
        return {"path": path, "required": required, "kind": kind}
    raise ValueError("write must be a string or {path, required}")


def normalize_writes(route_or_writes):
    """Normalize a route mapping or raw writes list."""
    if isinstance(route_or_writes, dict):
        writes = route_or_writes.get("writes") or []
    else:
        writes = route_or_writes or []
    return [normalize_write(item) for item in writes]


def clean_section_name(title):
    return (title or "").lstrip("# ").strip().strip("`")


def path_for_source(source):
    source = (source or "").strip().strip("`")
    aliases = {
        "core-policies.md": "corebase-specharness/memories/repo/core-policies.md",
        "project-knowledge-base.md": "corebase-specharness/memories/repo/project-knowledge-base.md",
        "learned-heuristics.md": "corebase-specharness/memories/repo/learned-heuristics.md",
        "adr-log.md": "corebase-specharness/memories/repo/adr-log.md",
    }
    if source in aliases:
        return aliases[source]
    if source.startswith("domain/"):
        return "corebase-specharness/memories/" + source
    return source or None


def route_rows(root, skill=""):
    selected = []
    row = skill_route(root, skill)
    for row in [row] if row else []:
        for source in row.get("sources", []):
            selected.append((source.get("path", ""), source.get("tier", "Should"), source.get("sections", [])))
    return selected


def skill_route(root, skill):
    target = (skill or "").lower()
    return next(
        (row for row in load_routes(root).get("skills", [])
         if row.get("skill", "").lower() == target),
        None,
    )


def feature_artifacts_for(root, skill):
    row = skill_route(root, skill)
    return row.get("feature_artifacts", []) if row else []
