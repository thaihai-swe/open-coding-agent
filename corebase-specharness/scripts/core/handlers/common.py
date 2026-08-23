"""Shared CLI handler helpers."""

import os
import re
from pathlib import Path

from core._lib.root import resolve_root
from core._lib.artifacts import canonical_feature_dir
from core._lib.locking import locked
from core.context_state import atomic_write

def _resolve_root(args, allow_uninitialized=False):
    root = resolve_root(args.root)
    if root:
        return Path(root)
    if allow_uninitialized:
        candidate = Path(args.root or os.getcwd()).resolve()
        if candidate.is_dir():
            return candidate
    raise ValueError("Unable to locate an initialized CoreBase SpecHarness repository")



def _result(command, status="ok", feature="", artifacts=None, warnings=None,
            next_action="", details=None, findings=None, errors=None):
    """Return the stable command envelope used by every handler."""
    return {
        "command": command,
        "status": status,
        "feature": feature,
        "artifacts": artifacts or [],
        "findings": findings or [],
        "warnings": warnings or [],
        "errors": errors or [],
        "next_action": next_action,
        "details": details or {},
    }



def _require_feature(root, feature):
    status = canonical_feature_dir(root, feature) / "status.md"
    if not status.is_file():
        raise ValueError(
            f"Feature '{feature}' is not initialized: required artifact is missing: {status}"
        )



def _read_file(path, label):
    if not path:
        return ""
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ValueError(f"Cannot read {label} {path}: {exc}") from exc



def format_handoff(objective="", next_action="", blockers=None, decisions=None, handoff_file=""):
    file_text = _read_file(handoff_file, "handoff file") if handoff_file else ""
    if file_text:
        return file_text
    lines = []
    if objective:
        lines.append(f"- Objective: {objective}")
    if next_action:
        lines.append(f"- Next step: {next_action}")
    lines.extend(f"- Blocker: {item}" for item in (blockers or []))
    lines.extend(f"- Decision: {item}" for item in (decisions or []))
    return "\n".join(lines)




def _append_candidates(root, feature, candidates, extract_file):
    content = list(candidates)
    file_text = _read_file(extract_file, "extract file")
    if file_text:
        content.append(file_text)
    appendix = "\n\n".join(item.rstrip() for item in content if item.strip())
    if not appendix:
        return None
    feature_path = canonical_feature_dir(root, feature) / "session-extracts.md"
    header = f"# Session Extracts: {feature}\n<!-- triaged: false -->\n\n## Pending Candidates\n\n"
    with locked(feature_path):
        existing = feature_path.read_text(encoding="utf-8") if feature_path.exists() else header
        triaged = existing.find("\n## Triaged")
        if triaged >= 0:
            updated = existing[:triaged].rstrip() + "\n\n" + appendix + "\n" + existing[triaged:]
        else:
            updated = existing.rstrip() + "\n\n" + appendix + "\n"
        feature_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(feature_path, updated)
    return str(feature_path)


def _slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text.strip('-')


