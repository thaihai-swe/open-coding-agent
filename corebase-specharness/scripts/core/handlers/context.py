"""CLI-facing bounded-context operations."""
from pathlib import Path

from core._lib.ansi import bar, table
from core._lib.routing_metadata import skill_route
from core.context_engine import build_context_pack, extract_section, redact_secrets
from core.context_state import last_pack_manifest, record_context_pack, session_budget_report
from core.handlers.common import _resolve_root, _result
from core.harness.config import HarnessConfig


def _session_budget(root, feature):
    """Return session token usage and warn/hard status for a feature."""
    if not feature:
        return {}
    config_path = Path(root) / "corebase-specharness/project/harness-config.yaml"
    warn, hard = 40000, 80000
    if config_path.is_file():
        try:
            config = HarnessConfig(config_path)
            warn = config.session_warn_tokens()
            hard = config.session_hard_tokens()
        except Exception:
            pass
    return session_budget_report(root, feature, warn_tokens=warn, hard_tokens=hard)


def _session_budget_warning(report):
    if not report:
        return []
    usage = report.get("session_tokens_accumulated") or 0
    hard = report.get("session_hard_tokens") or 0
    status = report.get("session_budget_status") or "normal"
    if status == "breached":
        return [
            f"Session token usage ({usage}/{hard}) exceeded the hard budget. "
            "Run session-end and start a fresh session."
        ]
    if status == "warning":
        return [
            f"Session token usage ({usage}/{hard}) approaching saturation. "
            "Run session-end and start a fresh session."
        ]
    return []


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
        cached = last_pack_manifest(root, args.feature)
        if cached:
            delta_from = cached
    pack = build_context_pack(
        root=root, skill=args.skill, intent=args.intent,
        feature=args.feature, task=getattr(args, "task", ""), budget=args.budget,
        profile=route.get("profile", ""), add_sources=getattr(args, "add_source", []),
        delta_from=delta_from,
    )
    if args.feature and not getattr(args, "dry_run", False):
        record_context_pack(root, args.feature, pack)
    return root, pack, _session_budget(root, args.feature)


def context_pack(args):
    """Plan a bounded context pack without returning file content."""
    _root, pack, session_budget = _pack(args)
    if not getattr(args, "json", False) and pack.get("selected"):
        budget, used = pack.get("budget") or 0, pack.get("estimated_tokens") or 0
        print()
        label = f"{used}/{budget or 'auto'} tokens"
        print(f"Context budget: {bar(used, budget or max(used, 1), width=22, label=label)}")
        rows = [[item.get("tier", ""), str(item.get("score", "")), item.get("path", "")]
                for item in pack["selected"][:8]]
        if rows:
            print(table(["Tier", "Score", "Path"], rows))
    warnings = pack["warnings"] + [f"{item['path']}: {item['reason']}" for item in pack["omitted"]]
    warnings.extend(_session_budget_warning(session_budget))
    return _result(
        "context-pack",
        "ok",
        args.feature,
        [item["path"] for item in pack["selected"]],
        warnings,
        "python3 corebase-specharness/scripts/core/cli.py status",
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
                **session_budget,
            },
            "dry_run": getattr(args, "dry_run", False),
        },
    )


def context_load(args):
    """Return selected context content for an agent-selected skill procedure."""
    root, pack, session_budget = _pack(args)
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
    warnings = pack["warnings"] + [f"{item['path']}: {item['reason']}" for item in pack["omitted"]]
    warnings.extend(_session_budget_warning(session_budget))
    details = {
        "selected": loaded,
        "omitted": pack["omitted"], "estimated_tokens": pack["estimated_tokens"],
        "budget": pack["budget"], "phase": pack.get("phase", ""),
        "skill_payload": "",
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
            **session_budget,
        },
        "dry_run": getattr(args, "dry_run", False),
    }
    return _result(
        "context-load",
        "ok",
        args.feature,
        [item["path"] for item in loaded],
        warnings,
        "python3 corebase-specharness/scripts/core/cli.py status",
        details,
    )

def context_explain(args):
    """Explain context source selection, omissions, and applied budgets."""
    _root, pack, session_budget = _pack(args)
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
    warnings = list(pack["warnings"]) + _session_budget_warning(session_budget)
    return _result(
        "context-explain",
        "ok",
        args.feature,
        [item["path"] for item in pack["selected"]],
        warnings,
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
                **session_budget,
            },
            "selected": _manifest_selected(pack["selected"]),
            "omitted": pack["omitted"],
        },
    )

