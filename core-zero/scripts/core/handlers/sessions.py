"""Session CLI command handlers with distinct lifecycle operations."""

from core._lib.routing_metadata import skill_route
from core.context_engine import build_context_pack
from core.context_state import (
    close_session,
    create_session,
    default_session_path,
    load_session,
    reopen_session,
    update_session_sections,
)
from core.handlers.common import _append_candidates, _require_feature, _resolve_root, _result, format_handoff


def _metadata(feature, skill, pack, route):
    return {
        "feature": feature,
        "phase": route.get("phase"),
        "skill": skill,
        "created_by": "corezero",
        "selected": [item["path"] for item in pack.get("selected", [])],
        "omitted": [item["path"] for item in pack.get("omitted", [])],
    }


def start_session(root, feature, skill, intent="", budget=0, objective=""):
    """Create or resume a session without appending checkpoint events."""
    _require_feature(root, feature)
    route = skill_route(root, skill)
    if not route:
        raise ValueError(f"Unknown skill route: {skill}")
    pack = build_context_pack(
        root,
        skill=skill,
        intent=intent,
        feature=feature,
        budget=budget,
        profile=route.get("profile", ""),
    )
    path = default_session_path(root, feature)
    metadata = _metadata(feature, skill, pack, route)
    existing = load_session(path)
    if existing and existing["metadata"].get("closed"):
        session = reopen_session(path, metadata)
    else:
        session = create_session(path, metadata, objective)
    return _result(
        "session-start",
        feature=feature,
        artifacts=[str(path)],
        warnings=pack.get("warnings", []),
        details={
            "session": str(path),
            "resumed": int(session["metadata"].get("updates", 0)) > 0,
            "selected": pack.get("selected", []),
            "omitted": pack.get("omitted", []),
            "estimated_tokens": pack.get("estimated_tokens", 0),
        },
    )


def session_start(args):
    """Create or resume a session without appending checkpoint events."""
    return start_session(
        _resolve_root(args),
        args.feature,
        args.skill,
        intent=getattr(args, "intent", "") or "",
        budget=getattr(args, "budget", 0) or 0,
        objective=getattr(args, "objective", "") or "",
    )


def checkpoint_session(
    root,
    feature,
    progress="",
    next_action="",
    blockers=None,
    decisions=None,
    handoff_file="",
    dry_run=False,
    objective="",
):
    """Append progress or handoff information to an existing session."""
    path = default_session_path(root, feature)
    progress_text = progress or None
    handoff = format_handoff(
        objective=objective,
        next_action=next_action,
        blockers=blockers,
        decisions=decisions,
        handoff_file=handoff_file,
    )
    if not progress_text and not handoff:
        raise ValueError("session-checkpoint requires --progress, --next-action, --blocker, --decision, or --handoff-file")
    if not load_session(path):
        raise ValueError(f"session does not exist: {path}")
    if not dry_run:
        session = update_session_sections(
            path,
            progress=progress_text,
            handoff=handoff,
            decisions=decisions,
        )
        updates = session["metadata"].get("updates", 0)
    else:
        updates = load_session(path)["metadata"].get("updates", 0)
    return _result(
        "session-checkpoint",
        feature=feature,
        artifacts=[str(path)],
        details={"session": str(path), "updates": updates, "dry_run": dry_run},
    )


def session_checkpoint(args):
    """Append progress or handoff information to an existing session."""
    return checkpoint_session(
        _resolve_root(args),
        args.feature,
        progress=getattr(args, "progress", "") or "",
        next_action=getattr(args, "next_action", "") or "",
        blockers=getattr(args, "blocker", []) or [],
        decisions=getattr(args, "decision", None),
        handoff_file=getattr(args, "handoff_file", "") or "",
        dry_run=bool(args.dry_run),
        objective=getattr(args, "objective", "") or "",
    )


def session_end(args):
    """Persist a final handoff and optional memory candidates."""
    root = _resolve_root(args)
    path = default_session_path(root, args.feature)
    handoff = format_handoff(
        objective=getattr(args, "objective", "") or "",
        next_action=getattr(args, "next_action", "") or "",
        blockers=getattr(args, "blocker", []) or [],
        decisions=getattr(args, "decision", []) or [],
        handoff_file=getattr(args, "handoff_file", "") or "",
    )
    if not handoff:
        raise ValueError("session-end requires --next-action, --blocker, --decision, or --handoff-file")
    extracts = None
    if not load_session(path):
        raise ValueError(f"session does not exist: {path}")
    if not args.dry_run:
        extracts = _append_candidates(root, args.feature, args.candidate, args.extract_file)
        session = close_session(path, handoff=handoff)
        updates = session["metadata"].get("updates", 0)
    else:
        updates = load_session(path)["metadata"].get("updates", 0)
    artifacts = [str(path)] + ([extracts] if extracts else [])
    return _result(
        "session-end",
        feature=args.feature,
        artifacts=artifacts,
        next_action="/context-memory" if extracts else "",
        details={"session": str(path), "updates": updates, "dry_run": args.dry_run},
    )
