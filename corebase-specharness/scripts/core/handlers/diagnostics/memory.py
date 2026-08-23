"""Read-only memory size diagnostics."""

from pathlib import Path
from typing import Any

from core._lib.token_counter import estimate_tokens
from core._lib.yaml_reader import load as load_yaml
from core.handlers.common import _resolve_root, _result


MEMORY_FILES = (
    "corebase-specharness/memories/repo/core-policies.md",
    "corebase-specharness/memories/repo/learned-heuristics.md",
    "corebase-specharness/memories/repo/project-knowledge-base.md",
    "corebase-specharness/memories/repo/adr-log.md",
)


def _thresholds(root: Path) -> dict[str, int]:
    config = load_yaml(str(root / "corebase-specharness/project/harness-config.yaml")) or {}
    values = config.get("thresholds") or {}
    return {
        "memory_warn_lines": int(values.get("memory_warn_lines", 100)),
        "memory_hard_lines": int(values.get("memory_hard_lines", 3200)),
    }


def _memory_files(root: Path, thresholds: dict[str, int]) -> list[dict[str, Any]]:
    files = []
    relatives = list(MEMORY_FILES)
    domain_base = root / "corebase-specharness/memories/domain"
    if domain_base.is_dir():
        relatives.extend(
            str(path.relative_to(root)).replace("\\", "/")
            for path in sorted(domain_base.rglob("*.md"))
            if path.is_file()
        )
    seen = set()
    for relative in relatives:
        if relative in seen:
            continue
        seen.add(relative)
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = len(text.splitlines())
        level = (
            "hard-cap" if lines >= thresholds["memory_hard_lines"]
            else "warning-level" if lines >= thresholds["memory_warn_lines"]
            else ""
        )
        files.append({
            "path": relative,
            "lines": lines,
            "tokens": estimate_tokens(text),
            "warnings": [level] if level else [],
        })
    return files


def memory_gate(args):
    """Check durable-memory files against configured line thresholds."""
    root = _resolve_root(args)
    details = check_memory_gate(root, mode=args.mode)
    status = "ok" if details["exit_code"] == 0 else "failed"
    return _result(
        "memory-gate",
        status,
        warnings=[item["file"] for item in details["warnings"]],
        errors=[item["file"] for item in details["breaches"]],
        next_action=details["recommendation"],
        details=details,
    )


def check_memory_gate(root: Path, mode: str = "advisory") -> dict[str, Any]:
    """Check durable-memory files against configured line thresholds."""
    thresholds = _thresholds(root)
    files = _memory_files(root, thresholds)
    warnings = [
        {"file": item["path"], "lines": item["lines"], "limit": thresholds["memory_warn_lines"]}
        for item in files if item["warnings"] == ["warning-level"]
    ]
    breaches = [
        {"file": item["path"], "lines": item["lines"], "limit": thresholds["memory_hard_lines"]}
        for item in files if item["warnings"] == ["hard-cap"]
    ]
    exit_code = 1 if (
        (mode == "warn" and (warnings or breaches))
        or (mode == "block" and breaches)
    ) else 0
    return {
        "mode": mode,
        "thresholds": {"warn": thresholds["memory_warn_lines"], "hard": thresholds["memory_hard_lines"]},
        "breaches": breaches,
        "warnings": warnings,
        "exit_code": exit_code,
        "recommendation": "/context-memory" if warnings or breaches else "",
    }


def _visible_heading_lines(text: str) -> list[str]:
    """Return markdown heading lines outside HTML comments and fenced code blocks."""
    visible = []
    in_comment = False
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        if stripped.startswith("<!--"):
            if "-->" not in line:
                in_comment = True
            continue
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        visible.append(line)
    return visible


def _semantic_memory_summary(root: Path) -> dict[str, Any]:
    """Parse structure of heuristics, policies, and ADRs for proactive memory health."""
    lh_path = root / "corebase-specharness/memories/repo/learned-heuristics.md"
    adr_path = root / "corebase-specharness/memories/repo/adr-log.md"
    active_heuristics, archived_heuristics = 0, 0
    if lh_path.is_file():
        text = lh_path.read_text(encoding="utf-8", errors="replace")
        for line in _visible_heading_lines(text):
            if line.startswith("### LH-"):
                if "ARCHIVED" in line or "[ARCHIVED" in line:
                    archived_heuristics += 1
                else:
                    active_heuristics += 1
    adr_count = 0
    if adr_path.is_file():
        text = adr_path.read_text(encoding="utf-8", errors="replace")
        adr_count = len(
            [line for line in _visible_heading_lines(text) if line.startswith("### ADR-")]
        )
    return {
        "active_heuristics_count": active_heuristics,
        "archived_heuristics_count": archived_heuristics,
        "adr_count": adr_count,
        "recommended_action": "/context-memory" if active_heuristics >= 10 else "",
    }


def memory_audit(args):
    """Report durable-memory file size, token estimates, and semantic breakdown."""
    root = _resolve_root(args)
    thresholds = _thresholds(root)
    files = _memory_files(root, thresholds)
    warnings = [f"{item['path']}: {warning}" for item in files for warning in item["warnings"]]
    hard_cap = any(item["warnings"] == ["hard-cap"] for item in files)
    semantic = _semantic_memory_summary(root)
    if semantic["recommended_action"] and semantic["recommended_action"] not in warnings:
        warnings.append(f"high active heuristics count ({semantic['active_heuristics_count']}); consider triage")
    return _result(
        "memory-audit",
        "failed" if hard_cap else "ok",
        getattr(args, "feature", ""),
        [item["path"] for item in files],
        warnings,
        next_action="/context-memory" if warnings else "",
        details={
            "files": files,
            "total_tokens": sum(item["tokens"] for item in files),
            "total_lines": sum(item["lines"] for item in files),
            "thresholds": thresholds,
            "hard_cap_blocked": hard_cap,
            "semantic_summary": semantic,
            "dry_run": getattr(args, "dry_run", False),
        },
    )
