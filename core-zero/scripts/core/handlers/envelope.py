"""Skill envelope: status-set, skill-enter, skill-exit."""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from core._lib.artifacts import canonical_feature_dir, read_feature_status
from core._lib.locking import locked
from core._lib.routing_metadata import load_routes, normalize_writes, skill_route
from core.context_state import atomic_write, default_session_path, load_session
from core.handlers.common import _resolve_root, _result
from core.handlers.context import context_load
from core.handlers.sessions import checkpoint_session, start_session
from core.harness.readiness import _known_state, check_readiness

STATUS_TEMPLATE = Path("skills/_shared/status-template.md")


def _lifecycle(root):
    from core.harness.config import HarnessConfig
    from core.harness.lifecycle import Lifecycle
    return Lifecycle(HarnessConfig(root / "core-zero/project/harness-config.yaml"))


def _ensure_status_document(root, feature, dry_run=False):
    path = canonical_feature_dir(root, feature) / "status.md"
    if path.is_file():
        return path, False
    template = root / STATUS_TEMPLATE
    if not template.is_file():
        raise ValueError(f"status template is missing: {template}")
    text = template.read_text(encoding="utf-8")
    text = text.replace("`<slug>`", feature).replace("<slug>", feature)
    text = _replace_field(text, "Delivery profile", "Moderate")
    text = _replace_field(text, "Status", "Active")
    text = _replace_field(text, "Active task", "None")
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(path, text)
    return path, True


def _replace_field(text, label, value):
    updated, count = re.subn(
        rf"^- {label}:.*$",
        f"- {label}: {value}",
        text,
        count=1,
        flags=re.M,
    )
    if count:
        return updated
    return text.rstrip() + f"\n- {label}: {value}\n"


def _write_phase(path, phase, next_step="", dry_run=False):
    with locked(path):
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if not text:
            raise ValueError(f"status.md is missing: {path}")
        text = _replace_field(text, "Phase", phase)
        if next_step:
            text = _replace_field(text, "Next step", next_step)
        if not dry_run:
            atomic_write(path, text)
    return path


def _current_state(root, feature, states):
    raw = read_feature_status(root, feature).get("phase", "")
    return _known_state(raw, states)


def _missing_writes(root, feature, writes):
    missing = []
    feature_dir = canonical_feature_dir(root, feature) if feature else None
    for item in normalize_writes(writes):
        relative = item["path"]
        if not item["required"] or item["kind"] != "file" or relative == "status.md":
            continue
        if feature_dir is not None and "/" not in relative:
            path = feature_dir / relative
        else:
            path = root / relative
        if not path.exists():
            missing.append(relative)
    return missing


def _done_authorization(root, feature, override=False, override_reason=""):
    """Return recorded verification or deliberate override authorizing Done."""
    if override:
        if not override_reason.strip():
            return None, "--verification-override requires --override-reason"
        record = {"schema_version": 1, "recorded_at": datetime.now(timezone.utc).isoformat(), "feature": feature, "authorization": "explicit_override", "reason": override_reason.strip()}
        path = root / "core-zero/generated/closeout-overrides.json"
        prior = []
        if path.is_file():
            try:
                prior = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(prior, list): prior = []
            except (OSError, ValueError):
                prior = []
        prior.append(record)
        atomic_write(path, json.dumps(prior[-50:], indent=2) + "\n")
        return record, None
    path = root / "core-zero/generated/verification-runs.json"
    if not path.is_file():
        return None, "Done requires a successful non-dry-run verification record; run verify --skill harness-verify or provide an explicit override"
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, "Done requires a readable verification-runs.json record"
    if not isinstance(records, list):
        return None, "Done requires verification-runs.json to be a JSON array"
    fingerprint = hashlib.sha256((root / "core-zero/project/harness-config.yaml").read_bytes()).hexdigest()
    for record in reversed(records):
        if not isinstance(record, dict) or record.get("feature") != feature: continue
        if record.get("verified") is not True or record.get("config_sha256") != fingerprint: continue
        if (record.get("scope") or {}).get("skill") != "harness-verify": continue
        return record, None
    return None, "Done requires a successful current-config verify --skill harness-verify record or an explicit override"


def apply_status(root, feature, target, next_step="", dry_run=False, verification_override=False, override_reason="", source_skill=""):
    """Validate and write a status.md lifecycle token."""
    lifecycle = _lifecycle(root)
    target = (target or "").strip()
    path, created = _ensure_status_document(root, feature, dry_run=True)
    current = "" if created or not path.is_file() else _current_state(root, feature, lifecycle.states)
    ok, failures = lifecycle.check_state_transition(current, target)
    if not ok:
        return _result(
            "status-set",
            "failed",
            feature,
            [str(path)] if path.is_file() else [],
            errors=failures,
            details={"from": current or None, "to": target, "changed": False},
        )
    authorization = None
    if target == "Done" and current != "Done":
        if dry_run and verification_override:
            return _result("status-set", "failed", feature, [str(path)] if path.is_file() else [], errors=["--verification-override cannot be used with --dry-run"], details={"from": current or None, "to": target, "changed": False})
        if source_skill and source_skill != "harness-verify" and not verification_override:
            return _result("status-set", "failed", feature, [str(path)] if path.is_file() else [], errors=["Only harness-verify may transition a feature to Done without an explicit override"], details={"from": current or None, "to": target, "changed": False})
        if not source_skill and not verification_override:
            return _result("status-set", "failed", feature, [str(path)] if path.is_file() else [], errors=["Direct status-set to Done requires --verification-override; use skill-exit --skill harness-verify for normal closeout"], details={"from": current or None, "to": target, "changed": False})
        authorization, authorization_error = _done_authorization(root, feature, override=verification_override, override_reason=override_reason)
        if authorization_error:
            return _result("status-set", "failed", feature, [str(path)] if path.is_file() else [], errors=[authorization_error], details={"from": current or None, "to": target, "changed": False})
    if not dry_run:
        if created or not path.is_file():
            path, _ = _ensure_status_document(root, feature)
        _write_phase(path, target, next_step or "", dry_run=False)
    return _result(
        "status-set",
        "ok",
        feature,
        [str(canonical_feature_dir(root, feature) / "status.md")],
        next_action=next_step or "",
        details={
            "from": current or None,
            "to": target,
            "changed": current != target,
            "created": created,
            "dry_run": bool(dry_run),
            "done_authorization": authorization,
        },
    )


def status_set(args):
    """Validate and write a status.md lifecycle token."""
    return apply_status(
        _resolve_root(args),
        args.feature,
        args.phase,
        next_step=getattr(args, "next_step", "") or "",
        dry_run=bool(args.dry_run),
        verification_override=bool(getattr(args, "verification_override", False)),
        override_reason=getattr(args, "override_reason", "") or "",
    )


def _apply_enter_phase(root, args, route, lifecycle):
    enter = (route.get("enter") or "").strip()
    if not args.feature:
        return None
    path, created = _ensure_status_document(root, args.feature, dry_run=args.dry_run)
    if not enter:
        return {
            "phase": _current_state(root, args.feature, lifecycle.states) or None,
            "changed": False,
            "created": created,
        }
    current = "" if created else _current_state(root, args.feature, lifecycle.states)
    if current == enter or (
        current
        and current in lifecycle.phase_mapping
        and lifecycle.phase_mapping.get(current) == route.get("phase")
        and current != enter
        and not lifecycle.check_state_transition(current, enter)[0]
    ):
        return {"phase": current or enter, "changed": False, "created": created}
    result = apply_status(
        root,
        args.feature,
        enter,
        next_step=getattr(args, "next_step", "") or "",
        dry_run=args.dry_run,
    )
    if result["status"] != "ok":
        raise ValueError("; ".join(result.get("errors") or ["status-set failed"]))
    return {
        "phase": enter,
        "changed": result["details"].get("changed", False),
        "created": created or result["details"].get("created", False),
    }


def skill_enter(args):
    """Load a skill route, open the session, and set the enter state."""
    root = _resolve_root(args)
    route = skill_route(root, args.skill)
    if not route:
        raise ValueError(f"Unknown skill route: {args.skill}")
    if route.get("feature") == "required" and not args.feature:
        raise ValueError(f"--feature is required for skill {args.skill}")
    lifecycle = _lifecycle(root)
    status_details = _apply_enter_phase(root, args, route, lifecycle)
    session_details = None
    if args.feature and not args.dry_run:
        started = start_session(
            root,
            args.feature,
            args.skill,
            intent=getattr(args, "intent", "") or "",
            budget=getattr(args, "budget", 0) or 0,
            objective=getattr(args, "objective", "") or getattr(args, "intent", ""),
        ).get("details", {})
        session_details = {
            "session": started.get("session"),
            "resumed": started.get("resumed", False),
        }
    pack = context_load(args)
    next_action = ""
    if args.feature:
        next_action = f"python3 core-zero/scripts/core/cli.py skill-exit --skill {args.skill} --feature {args.feature}"
    pack_details = dict(pack.get("details") or {})
    return _result(
        "skill-enter",
        pack.get("status", "ok"),
        args.feature,
        pack.get("artifacts", []),
        warnings=pack.get("warnings", []),
        next_action=next_action,
        details={
            "skill": args.skill,
            "route_phase": route.get("phase"),
            "enter": route.get("enter") or "",
            "status": status_details,
            "session": session_details,
            "pack": pack_details,
            "selected": pack_details.get("selected", []),
            "skill_payload": pack_details.get("skill_payload", ""),
            "dry_run": bool(args.dry_run),
        },
    )


def skill_exit(args):
    """Record handoff, check writes, and set the exit state."""
    root = _resolve_root(args)
    route = skill_route(root, args.skill)
    if not route:
        raise ValueError(f"Unknown skill route: {args.skill}")
    if route.get("feature") == "required" and not args.feature:
        raise ValueError(f"--feature is required for skill {args.skill}")
    handoff = (getattr(args, "handoff", "") or "").strip()
    allowed = list(route.get("handoff") or [])
    shipped = {
        row.get("skill")
        for row in load_routes(root).get("skills", [])
        if row.get("skill")
    }
    if handoff and allowed and handoff not in allowed:
        raise ValueError(f"handoff {handoff} is not declared for {args.skill}")
    if handoff and not allowed and handoff not in shipped:
        raise ValueError(f"handoff {handoff} is not a shipped CoreZero skill")
    missing = _missing_writes(root, args.feature, route.get("writes") or []) if args.feature else []
    target = (getattr(args, "phase", "") or route.get("exit") or "").strip()
    status_details = None
    errors = list(f"missing write: {item}" for item in missing)
    if args.feature and target:
        readiness = check_readiness(
            root,
            args.feature,
            skill=args.skill,
            target_state=target,
        )
        errors.extend(readiness["failures"])
    if args.feature and target and not errors:
        result = apply_status(
            root,
            args.feature,
            target,
            next_step=getattr(args, "next_action", "") or (f"/{handoff}" if handoff else (f"/{allowed[0]}" if allowed else "")),
            dry_run=args.dry_run,
            verification_override=bool(getattr(args, "verification_override", False)),
            override_reason=getattr(args, "override_reason", "") or "",
            source_skill=args.skill,
        )
        status_details = result.get("details", {})
        if result["status"] != "ok":
            errors.extend(result.get("errors") or [])
    session_details = None
    path = default_session_path(root, args.feature) if args.feature else None
    if path and load_session(path) and not args.dry_run and not errors:
        next_action = getattr(args, "next_action", "") or (f"/{handoff}" if handoff else (f"/{allowed[0]}" if allowed else args.skill))
        session_details = checkpoint_session(
            root,
            args.feature,
            progress=getattr(args, "progress", "") or f"exited {args.skill}",
            next_action=next_action,
            blockers=getattr(args, "blocker", []) or [],
            decisions=getattr(args, "decision", []) or [],
            handoff_file=getattr(args, "handoff_file", "") or "",
            dry_run=False,
        ).get("details", {})
    next_action = getattr(args, "next_action", "") or (f"/{handoff}" if handoff else (f"/{allowed[0]}" if allowed else ""))
    artifacts = []
    if args.feature:
        status_path = canonical_feature_dir(root, args.feature) / "status.md"
        if status_path.is_file():
            artifacts.append(str(status_path))
    return _result(
        "skill-exit",
        "failed" if errors else "ok",
        args.feature,
        artifacts,
        warnings=[],
        errors=errors,
        next_action=next_action,
        details={
            "skill": args.skill,
            "exit": target,
            "handoff": handoff or (allowed[0] if allowed else ""),
            "missing_writes": missing,
            "status": status_details,
            "session": session_details,
            "dry_run": bool(args.dry_run),
        },
    )
