#!/usr/bin/env python3
"""Durable, append-only session state."""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from core._lib.artifacts import validate_feature_slug
from core._lib.locking import locked


def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def default_session_dir(root, feature):
    if not feature:
        return None
    return Path(root).resolve() / ".corezero" / "sessions" / validate_feature_slug(feature)


def default_session_path(root, feature):
    directory = default_session_dir(root, feature)
    return directory / "session.md" if directory else None


def _front_matter(text):
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("invalid session front matter")
    try:
        return json.loads(text[4:end]), text[end + 5:]
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid session metadata: {exc}") from exc


def load_session(path):
    path = Path(path)
    if not path.is_file():
        return None
    metadata, body = _front_matter(path.read_text(encoding="utf-8"))
    return {"metadata": metadata, "body": body}


def create_session(path, metadata, objective=""):
    if Path(path).exists():
        return load_session(path)
    body = "# Session\n\n## Objective\n\n" + (objective.strip() or "[not set]") + "\n\n## Progress\n\n[not started]\n\n## Handoff\n\n[not prepared]\n"
    with locked(path):
        if Path(path).exists():
            return load_session(path)
        metadata = dict(metadata)
        metadata.setdefault("started_at", datetime.now().isoformat(timespec="seconds"))
        atomic_write(path, "---\n" + json.dumps(metadata, indent=2) + "\n---\n" + body)
    return load_session(path)


def _append_event(text, title, value):
    if value is None or not value.strip():
        return text
    return text.rstrip() + f"\n\n## {title}\n\n{value.strip()}\n"


def update_session_sections(path, progress=None, handoff=None, decisions=None):
    with locked(path):
        session = load_session(path)
        if not session:
            raise ValueError(f"session does not exist: {path}")
        body = _append_event(session["body"], "Progress Update", progress)
        body = _append_event(body, "Handoff Update", handoff)
        metadata = dict(session["metadata"])
        metadata["updates"] = int(metadata.get("updates", 0)) + 1
        extra = [item.strip() for item in (decisions or []) if str(item).strip()]
        if extra:
            recorded = list(metadata.get("decisions") or [])
            recorded.extend(extra)
            metadata["decisions"] = recorded
        atomic_write(path, "---\n" + json.dumps(metadata, indent=2) + "\n---\n" + body)
    return load_session(path)


def close_session(path, handoff=None):
    with locked(path):
        session = load_session(path)
        if not session:
            raise ValueError(f"session does not exist: {path}")
        body = _append_event(session["body"], "Handoff Update", handoff)
        metadata = dict(session["metadata"])
        metadata["updates"] = int(metadata.get("updates", 0)) + 1
        metadata["closed"] = True
        metadata["ended_at"] = datetime.now().isoformat(timespec="seconds")
        atomic_write(path, "---\n" + json.dumps(metadata, indent=2) + "\n---\n" + body)
    return load_session(path)


def reopen_session(path, metadata):
    with locked(path):
        session = load_session(path)
        if not session:
            raise ValueError(f"session does not exist: {path}")
        refreshed = dict(session["metadata"])
        refreshed.update(metadata)
        refreshed["updates"] = int(refreshed.get("updates", 0)) + 1
        refreshed["closed"] = False
        refreshed["started_at"] = datetime.now().isoformat(timespec="seconds")
        refreshed.pop("ended_at", None)
        body = session["body"].rstrip()
        body += "\n\n## Session Reopened\n\nResumed for skill {0} with phase {1}.\n".format(metadata.get("skill", "?"), metadata.get("phase", "?"))
        atomic_write(path, "---\n" + json.dumps(refreshed, indent=2) + "\n---\n" + body)
    return load_session(path)


def session_budget_report(root, feature, warn_tokens=40000, hard_tokens=80000):
    """Return accumulated session tokens and warn/hard budget status."""
    usage = 0
    path = default_session_path(root, feature)
    if path:
        session = load_session(path)
        if session:
            usage = int((session["metadata"] or {}).get("token_usage_estimate") or 0)
    warn = int(warn_tokens or 40000)
    hard = int(hard_tokens or 80000)
    if usage >= hard:
        status = "breached"
    elif usage >= warn:
        status = "warning"
    else:
        status = "normal"
    return {
        "session_tokens_accumulated": usage,
        "session_budget_status": status,
        "session_warn_tokens": warn,
        "session_hard_tokens": hard,
    }


def last_pack_manifest(root, feature):
    """Return the last context-pack baseline stored in session.md, if any."""
    session_path = default_session_path(root, feature)
    if not session_path:
        return None
    session = load_session(session_path)
    if not session:
        return None
    metadata = session["metadata"]
    fingerprints = metadata.get("last_context_fingerprint") or {}
    if not isinstance(fingerprints, dict) or not fingerprints:
        return None
    selected = [
        {"path": path, "fingerprint": fingerprint}
        for path, fingerprint in fingerprints.items()
        if path
    ]
    if not selected:
        return None
    return {
        "skill": metadata.get("skill"),
        "feature": feature,
        "estimated_tokens": metadata.get("last_context_tokens", 0),
        "selected": selected,
        "fingerprints": fingerprints,
    }


def record_context_pack(root, feature, pack):
    """Persist the last context-pack manifest in session.md for auto-delta."""
    session_path = default_session_path(root, feature)
    if not session_path or not session_path.is_file():
        return None
    fingerprints = pack.get("fingerprints") or {}
    if not fingerprints:
        fingerprints = {
            item.get("path"): item.get("fingerprint")
            for item in pack.get("selected") or []
            if isinstance(item, dict) and item.get("path")
        }
    with locked(session_path):
        session = load_session(session_path)
        if not session:
            return None
        metadata = dict(session["metadata"])
        metadata["last_context_fingerprint"] = fingerprints
        prior = int(metadata.get("token_usage_estimate", 0) or 0)
        metadata["token_usage_estimate"] = prior + int(pack.get("estimated_tokens") or 0)
        metadata["last_context_tokens"] = int(pack.get("estimated_tokens") or 0)
        atomic_write(
            session_path,
            "---\n" + json.dumps(metadata, indent=2) + "\n---\n" + session["body"],
        )
    return session_path

