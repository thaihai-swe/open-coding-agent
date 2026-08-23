"""Lifecycle CLI command handlers: init, status, phase-check, verify."""

import hashlib
import json
from datetime import datetime, timezone

from core._lib.ansi import status_icon, table
from core._lib.artifacts import canonical_feature_dir, list_features, read_feature_status
from core._lib.routing_metadata import load_routes
from core.harness.lifecycle import Lifecycle
from core.context_state import atomic_write, session_budget_report
from core.handlers.common import _resolve_root, _result
from core.harness.config import HarnessConfig
from core.harness.readiness import _known_state, check_readiness


def _append_generated_record(path, record, limit=50):
    """Append a bounded JSON audit record, recovering safely from malformed history."""
    prior = []
    if path.is_file():
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(parsed, list):
                prior = parsed
        except (OSError, ValueError):
            pass
    prior.append(record)
    atomic_write(path, json.dumps(prior[-limit:], indent=2) + "\n")




def init(args):
    """Initialize deterministic CoreBase SpecHarness repository scaffolding."""
    root = _resolve_root(args, allow_uninitialized=True)
    directories = [
        "corebase-specharness/memories/repo", "corebase-specharness/memories/domain", "corebase-specharness/project",
        ".corebase-specharness/generated", "artifacts/features",
    ]
    seeds = [
        "corebase-specharness/memories/repo/core-policies.md",
        "corebase-specharness/memories/repo/learned-heuristics.md",
        "corebase-specharness/memories/repo/project-knowledge-base.md",
        "corebase-specharness/memories/repo/adr-log.md",
        "corebase-specharness/project/architecture.md",
        "corebase-specharness/project/product-sense.md",
        "corebase-specharness/project/project-constraints.md",
        "corebase-specharness/project/glossary.md",
    ]
    writes = []
    if not args.dry_run:
        for relative in directories:
            (root / relative).mkdir(parents=True, exist_ok=True)
        for relative in seeds:
            path = root / relative
            if not path.exists():
                atomic_write(path, f"# {path.stem.replace('-', ' ').title()}\n\n[USER REVIEW NEEDED]\n")
                writes.append(relative)
        gitignore = root / ".gitignore"
        existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
        additions = [".corebase-specharness/generated/*"]
        missing = [line for line in additions if line not in existing.splitlines()]
        if missing:
            atomic_write(gitignore, existing.rstrip() + "\n" + "\n".join(missing) + "\n")
            writes.append(".gitignore")
    initialized = (root / "corebase-specharness/memories/repo/core-policies.md").exists()
    stack_markers = {
        "node": ["package.json"],
        "python": ["pyproject.toml", "requirements.txt", "setup.py"],
        "go": ["go.mod"],
        "rust": ["Cargo.toml"],
        "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
    }
    detected_stacks = [
        name for name, markers in stack_markers.items()
        if any((root / marker).is_file() for marker in markers)
    ]
    native_instructions = [
        name for name in ("CLAUDE.md", ".cursorrules", ".windsurfrules", ".github/copilot-instructions.md")
        if (root / name).is_file()
    ]
    config_path = root / "corebase-specharness/project/harness-config.yaml"
    try:
        gates = [gate.name for gate in HarnessConfig(config_path).get_gates()] if config_path.is_file() else []
    except Exception:
        gates = []
    unknowns = []
    if not detected_stacks:
        unknowns.append("repository stack")
    if not gates:
        unknowns.append("confirmed verification gates")
    suggested_gates = []
    stack_templates = {
        "python": {"name": "test", "command": ["python3", "-m", "pytest"], "on_fail": "block", "category": "test", "paths": ["**/*.py", "tests/**"]},
        "node": {"name": "test", "command": ["npm", "test"], "on_fail": "block", "category": "test", "paths": ["**/*.{js,ts,jsx,tsx}", "package.json"]},
        "go": {"name": "test", "command": ["go", "test", "./..."], "on_fail": "block", "category": "test", "paths": ["**/*.go", "go.mod"]},
        "rust": {"name": "test", "command": ["cargo", "test"], "on_fail": "block", "category": "test", "paths": ["**/*.rs", "Cargo.toml"]},
        "java": {"name": "test", "command": ["./gradlew", "test"], "on_fail": "block", "category": "test", "paths": ["**/*.java", "build.gradle", "pom.xml"]},
    }
    for stack in detected_stacks:
        if stack in stack_templates:
            suggested_gates.append(stack_templates[stack])
    return _result("init", artifacts=writes, next_action="/starter-init", details={
        "root": str(root), "initialized": initialized, "dry_run": args.dry_run,
        "onboarding_readiness": {
            "detected_stacks": detected_stacks,
            "portable_router": "AGENTS.md" if (root / "AGENTS.md").is_file() else "",
            "preserved_native_instruction_files": native_instructions,
            "confirmed_gates": gates,
            "unknowns": unknowns,
            "recommended_next_skill": "/starter-init",
            "suggested_gates_template": suggested_gates,
        },
    })


def _valid_handoffs(root, feature):
    machine = Lifecycle(HarnessConfig(root / "corebase-specharness/project/harness-config.yaml"))
    current = _known_state(read_feature_status(root, feature).get("phase", ""), machine.states)
    routes = [row for row in load_routes(root).get("skills", []) if isinstance(row, dict)]
    current_route = next(
        (row for row in routes if row.get("exit") == current or row.get("enter") == current),
        None,
    )
    legal_enter = []
    for row in routes:
        enter = (row.get("enter") or "").strip()
        if not enter:
            continue
        ok, _ = machine.check_state_transition(current, enter)
        if ok and row.get("skill"):
            legal_enter.append(row["skill"])
    return {
        "current_state": current or None,
        "declared_handoffs": list((current_route or {}).get("handoff") or []),
        "legal_enter_skills": legal_enter,
        "note": "These are valid next skills, not a chosen next skill.",
    }


def status(args):
    """Report feature state without generating operational artifacts."""
    root = _resolve_root(args)
    features = list_features(root)
    if args.feature:
        features = [item for item in features if item.get("slug") == args.feature]
    blockers = [item.get("slug", "") for item in features if item.get("has_blocker")]
    next_action = features[0].get("next_step", "") if len(features) == 1 else "python3 corebase-specharness/scripts/core/cli.py status"
    warnings = [f"Blocker: {slug}" for slug in blockers]
    details = {"features": features, "dry_run": args.dry_run}
    if args.feature:
        config_path = root / "corebase-specharness/project/harness-config.yaml"
        warn, hard = 40000, 80000
        if config_path.is_file():
            try:
                config = HarnessConfig(config_path)
                warn = config.session_warn_tokens()
                hard = config.session_hard_tokens()
            except Exception:
                pass
        report = session_budget_report(root, args.feature, warn_tokens=warn, hard_tokens=hard)
        details["session_budget"] = report
        usage = report.get("session_tokens_accumulated") or 0
        if report.get("session_budget_status") == "breached":
            warnings.append(
                f"Session token usage ({usage}/{hard}) exceeded the hard budget. "
                "Run session-end and start a fresh session."
            )
        elif report.get("session_budget_status") == "warning":
            warnings.append(
                f"Session token usage ({usage}/{hard}) approaching saturation. "
                "Run session-end and start a fresh session."
            )
    if getattr(args, "next", False):
        if not args.feature:
            raise ValueError("status --next requires --feature")
        details["next"] = _valid_handoffs(root, args.feature)
        next_action = "Inspect details.next.declared_handoffs; do not treat this as a chosen skill"
    return _result("status", feature=args.feature, warnings=warnings,
                   next_action=next_action, details=details)

def evaluate_phase_check(root, feature, skill="", phase=""):
    """Evaluate phase or skill-route readiness and return the CLI envelope."""
    readiness = check_readiness(root, feature, skill=skill or "", phase=phase or "")
    failures = readiness["failures"]
    meets_preconditions = not failures
    enforcement_mode = readiness["enforcement_mode"]
    allowed = meets_preconditions or enforcement_mode == "advisory"
    current_state = readiness["current_state"] or None
    phase_name = readiness["target_phase"]
    lifecycle = readiness["lifecycle"]
    payload = {
        "allowed": allowed,
        "meets_preconditions": meets_preconditions,
        "enforcement_mode": enforcement_mode,
        "reason": "preconditions met" if meets_preconditions else "; ".join(failures),
        "mechanical_failures": failures,
        "transition": "ok" if readiness["transition_ok"] else "illegal",
        "current_state": current_state,
        "target_phase": phase_name,
        "target_state": (
            lifecycle.states_for_phase(phase_name)[0]
            if readiness["transition_ok"] and len(lifecycle.states_for_phase(phase_name)) == 1
            else None
        ),
    }
    advisory_findings = [] if meets_preconditions or enforcement_mode == "blocking" else failures
    return _result(
        "phase-check",
        "ok" if meets_preconditions else ("deferred" if enforcement_mode == "advisory" else "failed"),
        feature,
        [str(root / "corebase-specharness/project/harness-config.yaml")],
        warnings=advisory_findings,
        findings=advisory_findings,
        errors=[] if meets_preconditions or enforcement_mode == "advisory" else failures,
        details=payload,
    )


def phase_check(args):
    """Check phase or skill-route preconditions without mutating status."""
    return evaluate_phase_check(
        _resolve_root(args),
        args.feature,
        skill=getattr(args, "skill", "") or "",
        phase=getattr(args, "phase", "") or "",
    )


def verify(args):
    """Run deterministic verification checks and mechanical gates."""
    root = _resolve_root(args)
    skill = (getattr(args, "skill", "") or "").strip()
    phase_name = (getattr(args, "phase", "") or "").strip()
    if skill and phase_name:
        raise ValueError("--skill and --phase are mutually exclusive")
    compatibility_warning = ""
    if not skill:
        phase_name = phase_name or "Verify"
        compatibility_warning = (
            "verify without --skill uses coarse --phase compatibility; "
            "pass --skill for route-scoped readiness and structure"
        )
    phase = evaluate_phase_check(root, args.feature, skill=skill, phase=phase_name)
    artifact = evaluate_artifact_check(
        root, args.feature, skill=skill, phase=phase_name, trace=True
    )
    config = HarnessConfig(root / "corebase-specharness/project/harness-config.yaml")
    enforcement_mode = config.verification_mode()
    gates = config.get_gates()
    from core.harness.gates import changed_files_from_git
    changed_files = changed_files_from_git(root) if getattr(args, "fast", False) else None
    gate_results = [gate.run(str(root), dry_run=args.dry_run, changed_files=changed_files).to_dict() for gate in gates]
    from core.handlers.diagnostics.providers import run_provider
    provider = run_provider(root, "review", action="run", feature=args.feature, dry_run=args.dry_run)
    provider_details = provider.get("details", {})
    if not args.dry_run:
        _append_generated_record(
            root / ".corebase-specharness/generated/gate-runs.json",
            {"feature": args.feature, "gates": gate_results},
        )
        _append_generated_record(
            root / ".corebase-specharness/generated/provider-runs.json",
            {
                "feature": args.feature,
                "category": "review",
                "provider": {
                    "status": provider["status"],
                    "active": provider_details.get("active"),
                    "mode": provider_details.get("mode"),
                    "executed": provider_details.get("executed"),
                    "required": provider_details.get("required"),
                    "errors": provider.get("errors", []),
                },
            },
        )
    gates_passed = all(
        res.get("passed") is True or gate.on_fail != "block"
        for gate, res in zip(gates, gate_results)
    )
    traceability_errors = artifact.get("details", {}).get("traceability_errors", [])

    provider_required = bool(provider_details.get("required", False))
    provider_executed = bool(provider_details.get("executed", False))
    provider_passed = provider["status"] == "ok" or (
        not provider_required and provider["status"] in {"deferred", "unavailable"}
    )
    phase_passed = phase.get("details", {}).get("meets_preconditions", phase["status"] == "ok")
    artifact_passed = not artifact.get("details", {}).get("validation_errors", artifact["status"] != "failed")
    static_checks_passed = phase_passed and artifact_passed and not traceability_errors
    verified = (
        not args.dry_run and bool(gates) and static_checks_passed and gates_passed and provider_passed
    )
    findings = (
        phase.get("details", {}).get("mechanical_failures", [])
        + artifact.get("details", {}).get("validation_errors", [])
        + traceability_errors
        + [f"gate failed: {res['name']}" for res in gate_results if res.get("passed") is False]
        + provider.get("errors", [])
    )
    dry_run_warning = "dry-run: gates were not executed; no verification verdict issued"
    details = {
        "skill": skill or None,
        "phase": phase,
        "scope": {"skill": skill or None, "phase": phase_name or None},
        "artifacts": artifact,
        "gate_results": gate_results,
        "provider": provider,
        "enforcement_mode": enforcement_mode,
        "verification_mode": enforcement_mode,
        "dry_run": bool(args.dry_run),
        "would_pass_static_checks": bool(args.dry_run) and static_checks_passed,
        "verified": verified,
        "passed": verified,
        "summary": (
            "Dry-run: static checks were evaluated but gates were not executed; "
            "no verification verdict was issued."
            if args.dry_run
            else (
                "Feature is verified with all required evidence and configured gates passing."
                if verified
                else (
                    "Advisory mode: work is NOT verified. Incomplete evidence was reported as "
                    "findings and the process exits 0 without a verification verdict."
                    if enforcement_mode == "advisory"
                    else "Blocking mode: required evidence is missing and verification failed."
                )
            )
        ),
    }
    if not gates:
        findings.append("no confirmed verification gates are configured")
        details["summary"] = (
            "NOT VERIFIED — no confirmed verification gates are configured. "
            "Run /starter-init or use an explicit reasoned closeout override."
        )
    details["verdict"] = "VERIFIED" if verified else ("DRY RUN — NO VERDICT" if args.dry_run else "NOT VERIFIED")
    if not args.dry_run:
        config_path = root / "corebase-specharness/project/harness-config.yaml"
        record = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "feature": args.feature,
            "scope": {"skill": skill or None, "phase": phase_name or None},
            "verified": verified,
            "verification_mode": enforcement_mode,
            "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
            "static_checks_passed": static_checks_passed,
            "gates_configured": len(gates),
            "gates_passed": gates_passed,
            "provider_passed": provider_passed,
            "findings": findings,
        }
        _append_generated_record(root / ".corebase-specharness/generated/verification-runs.json", record)
        details["evidence_record"] = record
    if args.dry_run:
        details["warnings"] = [dry_run_warning]
    if not getattr(args, "json", False):
        provider_label = (
            "pass" if provider_passed and provider_executed
            else "skipped (not configured)" if provider["status"] in {"deferred", "unavailable"} and not provider_executed
            else "fail"
        )
        rows = [
            ["phase-check", status_icon("pass" if phase_passed else "fail"), "pass" if phase_passed else "incomplete"],
            ["artifact-check", status_icon("pass" if artifact_passed else "fail"), "pass" if artifact_passed else "incomplete"],
            ["traceability", status_icon("pass" if not traceability_errors else "fail"), "ok" if not traceability_errors else f"{len(traceability_errors)} error(s)"],
            ["gate-runner", status_icon("pass" if gates_passed else "fail"), "dry-run" if args.dry_run else ("pass" if gates_passed else "fail")],
            ["review-provider", status_icon("pass" if provider_label == "pass" else "fail"), provider_label],
        ]
        print()
        print(table(["Check", "", "Result"], rows))
        for res in gate_results:
            if res.get("executed"):
                print(f"[{'PASS' if res['passed'] else 'FAIL'}] {res['name']} ({res['duration_ms']}ms)")
    warnings = phase.get("warnings", []) + artifact.get("warnings", [])
    if compatibility_warning:
        warnings.append(compatibility_warning)
    if args.dry_run:
        warnings.append(dry_run_warning)
    warnings.extend(findings if enforcement_mode == "advisory" else [])
    result = _result(
        "verify",
        "ok" if verified else ("deferred" if enforcement_mode == "advisory" else "failed"),
        args.feature,
        artifact.get("artifacts", []),
        warnings,
        next_action=(
            "/harness-verify"
            if verified
            else "Feature is not verified; inspect details.verified and findings before closeout"
        ),
        details=details,
        findings=findings,
        errors=[] if enforcement_mode == "advisory" else findings,
    )
    result["traceability_errors"] = traceability_errors
    return result



def evaluate_artifact_check(root, feature, skill="", phase="", trace=False):
    """Validate feature artifact structure and optional traceability."""
    feature_dir = canonical_feature_dir(root, feature)
    if not feature_dir.is_dir():
        raise ValueError(f"Feature directory not found: {feature_dir}")
    from core._lib.artifact_schema import check_structure, files_for, traceability_report
    file_set = files_for(root, skill=skill or "", phase=phase or "")
    scope = file_set["skill"] or file_set["phase"] or "Plan"
    errors, warnings = check_structure(
        feature_dir,
        scope,
        fileset=file_set["structure"],
        optional_files=file_set.get("heading_files") or [],
    )
    details = {
        "skill": file_set["skill"] or None,
        "phase": file_set["phase"] or None,
        "structure": file_set["structure"],
    }
    if trace:
        report, trace_errors, _twarns = traceability_report(feature_dir)
        details["traceability"] = report
        details["traceability_errors"] = trace_errors
        errors.extend(trace_errors)
    enforcement_mode = HarnessConfig(root / "corebase-specharness/project/harness-config.yaml").verification_mode()
    return _result(
        "artifact-check",
        "ok" if not errors else ("deferred" if enforcement_mode == "advisory" else "failed"),
        feature,
        [str(feature_dir)],
        warnings=warnings + (errors if enforcement_mode == "advisory" else []),
        findings=errors,
        details={**details, "validation_errors": errors, "enforcement_mode": enforcement_mode},
        errors=[] if enforcement_mode == "advisory" else errors,
    )


def artifact_check(args):
    """Validate feature artifact structure and traceability."""
    skill = (getattr(args, "skill", "") or "").strip()
    phase = (getattr(args, "phase", "") or "").strip()
    if skill and phase:
        raise ValueError("--skill and --phase are mutually exclusive")
    if not skill and not phase:
        raise ValueError("artifact-check requires --skill or --phase")
    return evaluate_artifact_check(
        _resolve_root(args),
        args.feature,
        skill=skill,
        phase=phase,
        trace=bool(getattr(args, "trace", False)),
    )
