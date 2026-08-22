"""Single readiness evaluator for skill routes, phases, and status tokens."""

import re
from pathlib import Path

from core._lib.artifact_schema import files_for
from core._lib.artifacts import canonical_feature_dir, read_feature_status
from core._lib.routing_metadata import skill_route
from core.harness.config import HarnessConfig
from core.harness.lifecycle import Lifecycle


def _known_state(raw, states):
    value = (raw or "").strip().strip("`")
    if "|" in value:
        return ""
    return value if value in states else ""


def mechanical_checks(root, feature, phase, skill_name="", target_state=""):
    """Return deterministic readiness failures for a target phase or token."""
    feature_dir = canonical_feature_dir(root, feature)
    effective = (target_state or phase or "").strip()
    normalized = effective.lower()
    failures = []
    route_scoped = bool(skill_name)

    # Named-skill checks use route prerequisites instead of coarse phase extras.
    if route_scoped:
        if normalized == "done":
            sync_path = feature_dir / "session-extracts.md"
            if not sync_path.is_file():
                failures.append("session-extracts.md with post-ship sync evidence is required before Done")
            elif not re.search(r"(?im)^##\s+Post-Ship Sync\b", sync_path.read_text(encoding="utf-8", errors="replace")):
                failures.append("session-extracts.md has no Post-Ship Sync record before Done")
            if not (feature_dir / "review.md").is_file():
                failures.append("review.md is required before Done")
        return failures

    if normalized == "plan":
        from core.handlers.artifacts import check_requirements_readiness
        readiness = check_requirements_readiness(root, feature)
        if not readiness.get("ok"):
            failures.extend(readiness.get("errors", []) or ["requirements are not ready"])
    elif normalized == "implement":
        tasks_path = feature_dir / "tasks.md"
        if not tasks_path.is_file():
            failures.append("tasks.md is required before Implement")
        else:
            from core.task_graph import detect_cycle, parse_tasks
            tasks_text = tasks_path.read_text(encoding="utf-8", errors="replace")
            tasks = parse_tasks(tasks_text)
            if not tasks:
                failures.append("tasks.md must define at least one task before Implement")
            cycle = detect_cycle(tasks)
            if cycle:
                failures.append("task dependency cycle: " + " -> ".join(cycle))
            from core.handlers.artifacts import check_requirements_readiness
            readiness = check_requirements_readiness(root, feature)
            missing = readiness.get("metrics", {}).get("unmapped_criteria", [])
            if missing:
                failures.append("acceptance criteria missing task mapping: " + ", ".join(missing))
    elif normalized == "verify":
        tasks_path = feature_dir / "tasks.md"
        if not tasks_path.is_file():
            failures.append("tasks.md is required before Verify")
        else:
            from core.task_graph import parse_tasks
            tasks = parse_tasks(tasks_path.read_text(encoding="utf-8", errors="replace"))
            incomplete = [task["id"] for task in tasks if not task.get("done")]
            if incomplete:
                failures.append("unfinished tasks before Verify: " + ", ".join(incomplete))
            evidence_missing = [task["id"] for task in tasks if task.get("done") and not task.get("evidence")]
            if evidence_missing:
                failures.append("completed tasks missing validation evidence: " + ", ".join(evidence_missing))
    elif normalized == "done":
        sync_path = feature_dir / "session-extracts.md"
        if not sync_path.is_file():
            failures.append("session-extracts.md with post-ship sync evidence is required before Done")
        elif not re.search(r"(?im)^##\s+Post-Ship Sync\b", sync_path.read_text(encoding="utf-8", errors="replace")):
            failures.append("session-extracts.md has no Post-Ship Sync record before Done")
    return failures


def check_readiness(root, feature, *, skill="", phase="", target_state=""):
    """Return readiness facts. Raises only for unknown skills or missing targets."""
    root = Path(root)
    skill_name = (skill or "").strip()
    phase_name = (phase or "").strip()
    token = (target_state or "").strip()
    route = None
    if skill_name:
        route = skill_route(root, skill_name)
        if not route:
            raise ValueError(f"Skill not found in context routes: {skill_name}")
        if not phase_name:
            phase_name = route.get("phase", "") or ""
    if not phase_name:
        raise ValueError("--phase or --skill is required")

    config = HarnessConfig(root / "core-zero/project/harness-config.yaml")
    lifecycle = Lifecycle(config)
    feature_dir = canonical_feature_dir(root, feature)
    phases = [item for item in lifecycle.phases if item.name == phase_name]
    if not phases:
        raise ValueError(f"Phase not found: {phase_name}")

    if route is not None:
        file_set = files_for(root, skill=skill_name)
        failures = [
            f"Required artifact missing: {feature_dir / name}"
            for name in file_set["prerequisites"]
            if not (feature_dir / name).is_file()
        ]
    else:
        failures = phases[0].check_preconditions(str(feature_dir))

    failures.extend(mechanical_checks(root, feature, phase_name, skill_name, token))

    feature_state = read_feature_status(root, feature)
    current_raw = feature_state["phase"]
    current_state = _known_state(current_raw, lifecycle.states)
    skip_transition = (
        (current_state in {"Done", "Abandoned"} and skill_name in {"context-memory", "harness-maintain"})
        or (route is not None and not route.get("enter") and not route.get("exit"))
    )
    if skip_transition:
        transition_ok, transition_failures = True, []
    elif token:
        transition_ok, transition_failures = lifecycle.check_state_transition(
            current_state, token
        )
    else:
        transition_ok, transition_failures = lifecycle.check_transition(
            current_raw if current_raw != "Unknown" else "", phase_name
        )
    failures.extend(transition_failures)
    return {
        "failures": failures,
        "current_state": current_state or ("" if current_raw == "Unknown" else current_raw),
        "target_phase": phase_name,
        "target_state": token,
        "transition_ok": transition_ok,
        "skip_transition": skip_transition,
        "enforcement_mode": config.verification_mode(),
        "route": route,
        "lifecycle": lifecycle,
    }
