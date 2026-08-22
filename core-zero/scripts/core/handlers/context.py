"""CLI-facing bounded-context operations."""
from pathlib import Path

from core._lib.artifacts import canonical_feature_dir
from core._lib.ansi import bar, table
from core._lib.routing_metadata import skill_route
from core.context_engine import build_context_pack, extract_section, redact_secrets
from core.context_state import last_pack_path, record_context_pack
from core.handlers.common import _resolve_root, _result


def _manifest_selected(items):
    """Return selected rows without file bodies for inspectable pack/explain output."""
    stripped = []
    for item in items or []:
        row = dict(item)
        row.pop("content", None)
        stripped.append(row)
    return stripped


def _pack(args):
    root = _resolve_root(args)
    route = skill_route(root, args.skill)
    if not route:
        raise ValueError(f"Unknown skill route: {args.skill}")
    if route.get("feature") == "required" and not args.feature:
        raise ValueError(f"--feature is required for skill {args.skill}")
    delta_from = getattr(args, "delta_from", "") or None
    force_full = bool(getattr(args, "full", False))
    if not force_full and not delta_from and args.feature:
        cached = last_pack_path(root, args.feature)
        if cached and cached.is_file():
            delta_from = str(cached)
    pack = build_context_pack(
        root=root, skill=args.skill, intent=args.intent,
        feature=args.feature, task=getattr(args, "task", ""), budget=args.budget,
        profile=route.get("profile", ""), add_sources=getattr(args, "add_source", []),
        delta_from=delta_from,
    )
    if args.feature and not getattr(args, "dry_run", False):
        record_context_pack(root, args.feature, pack)
    return root, pack


def context_pack(args):
    """Plan a bounded context pack without returning file content."""
    _root, pack = _pack(args)
    if not getattr(args, "json", False) and pack.get("selected"):
        budget, used = pack.get("budget") or 0, pack.get("estimated_tokens") or 0
        print()
        label = f"{used}/{budget or 'auto'} tokens"
        print(f"Context budget: {bar(used, budget or max(used, 1), width=22, label=label)}")
        rows = [[item.get("tier", ""), str(item.get("score", "")), item.get("path", "")]
                for item in pack["selected"][:8]]
        if rows:
            print(table(["Tier", "Score", "Path"], rows))
    return _result(
        "context-pack",
        "ok",
        args.feature,
        [item["path"] for item in pack["selected"]],
        pack["warnings"] + [f"{item['path']}: {item['reason']}" for item in pack["omitted"]],
        "python3 core-zero/scripts/core/cli.py status",
        {
            "selected": _manifest_selected(pack["selected"]),
            "omitted": pack["omitted"],
            "estimated_tokens": pack["estimated_tokens"],
            "budget": pack["budget"],
            "manifest": {
                "skill": pack.get("skill"),
                "feature": pack.get("feature"),
                "task": pack.get("task"),
                "intent": pack.get("intent"),
                "budget": pack.get("budget"),
                "estimated_tokens": pack.get("estimated_tokens"),
                "reserve_tokens": pack.get("reserve_tokens"),
                "profile": pack.get("profile"),
                "budget_categories": pack.get("budget_categories", {}),
                "tokenizer": pack.get("tokenizer"),
            },
            "dry_run": getattr(args, "dry_run", False),
        },
    )


def context_load(args):
    """Return selected context content for an agent-selected skill procedure."""
    root, pack = _pack(args)
    loaded = []
    for item in pack["selected"]:
        path = (root / item.get("content_path", item["path"])).resolve()
        if Path(root).resolve() not in path.parents and path != Path(root).resolve():
            continue
        text = item.get("content")
        if text is None:
            text = item.get("runtime_summary")
        if text is None:
            text = path.read_text(encoding="utf-8", errors="replace")
            if item.get("sections"):
                text = "\n\n".join(section for section in
                                    (extract_section(text, name) for name in item["sections"]) if section)
        loaded.append({**item, "content": redact_secrets(text or "")})
    details = {
        "selected": loaded,
        "omitted": pack["omitted"], "estimated_tokens": pack["estimated_tokens"],
        "budget": pack["budget"], "phase": pack.get("phase", ""),
        "skill_payload": _render_skill_payload(root, args) if args.skill else "",
        "manifest": {
            "skill": pack.get("skill"),
            "feature": pack.get("feature"),
            "task": pack.get("task"),
            "intent": pack.get("intent"),
            "budget": pack.get("budget"),
            "estimated_tokens": pack.get("estimated_tokens"),
            "reserve_tokens": pack.get("reserve_tokens"),
            "profile": pack.get("profile"),
            "budget_categories": pack.get("budget_categories", {}),
            "tokenizer": pack.get("tokenizer"),
        },
        "dry_run": getattr(args, "dry_run", False),
    }
    return _result(
        "context-load",
        "ok",
        args.feature,
        [item["path"] for item in loaded],
        pack["warnings"] + [f"{item['path']}: {item['reason']}" for item in pack["omitted"]],
        "python3 core-zero/scripts/core/cli.py status",
        details,
    )

def context_explain(args):
    """Explain context source selection, omissions, and applied budgets."""
    _root, pack = _pack(args)
    findings = []
    findings.extend(
        {
            "path": item["path"],
            "decision": "selected",
            "reason": item["reason"],
            "provenance": item["provenance"],
            "tokens": item["tokens"],
            "trust": item["trust"],
        }
        for item in pack["selected"]
    )
    findings.extend(
        {
            "path": item["path"],
            "decision": "omitted",
            "reason": item["reason"],
            "provenance": item.get("provenance", ""),
            "tokens": item.get("tokens", 0),
        }
        for item in pack["omitted"]
    )
    return _result(
        "context-explain",
        "ok",
        args.feature,
        [item["path"] for item in pack["selected"]],
        pack["warnings"],
        findings=findings,
        details={
            "manifest": {
                "skill": pack.get("skill"),
                "feature": pack.get("feature"),
                "task": pack.get("task"),
                "intent": pack.get("intent"),
                "budget": pack.get("budget"),
                "estimated_tokens": pack.get("estimated_tokens"),
                "budget_categories": pack.get("budget_categories", {}),
                "tokenizer": pack.get("tokenizer"),
            },
            "selected": _manifest_selected(pack["selected"]),
            "omitted": pack["omitted"],
        },
    )


def _render_skill_payload(root, args):
    """Render the operational skill summary without duplicating full procedure prose."""
    skill_path = Path(root) / "skills" / args.skill / "SKILL.md"
    if not skill_path.is_file():
        return ""
    content = skill_path.read_text(encoding="utf-8")
    sections = [
        extract_section(content, "At a Glance"),
        extract_section(content, "Step-by-Step Execution Workflow"),
    ]
    selected = "\n\n".join(section for section in sections if section)
    if not selected:
        selected = content
    unresolved_acs = ""
    feature_dir = canonical_feature_dir(root, args.feature) if args.feature else None
    if feature_dir and feature_dir.is_dir():
        from core._lib.artifact_schema import traceability_report
        _report, errors, _warnings = traceability_report(feature_dir)
        unresolved_acs = "; ".join(error for error in errors if "AC" in error)
    route = skill_route(root, args.skill) or {}
    values = {"current_phase": route.get("phase", ""), "feature_slug": args.feature,
              "session_objective": args.intent, "unresolved_acs": unresolved_acs}
    for key, value in values.items():
        selected = selected.replace(f"{{{{{key}}}}}", value)
    return (
        "# Operational Skill Payload\n\n"
        f"Full procedure: skills/{args.skill}/SKILL.md\n\n"
        + selected
    )
