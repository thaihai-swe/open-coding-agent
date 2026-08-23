"""Feature artifact headings and canonical REQ/AC/T-NNN traceability helpers."""
from __future__ import annotations

import re
from pathlib import Path

REQUIRED_HEADINGS = {
    "spec.md": ["## Metadata", "## Problem Statement", "## Acceptance Criteria"],
    "plan.md": ["## Metadata", "## Approach"],
    "tasks.md": ["## Metadata", "## Tasks"],
    "review.md": ["# ", "## Decision"],
    "status.md": [],
}
AC_RE = re.compile(r"\bAC[-_]?\d+\b", re.IGNORECASE)
TASK_RE = re.compile(r"\bT-\d{3}\b")
DONE_TASK_RE = re.compile(r"(?im)^\s*[-*]\s+\[[xX]\]\s+(T-\d{3})\b")
PHASE_FILES = {
    "Spec": ["status.md", "spec.md"],
    "Plan": ["status.md", "spec.md", "plan.md", "tasks.md"],
    "Implement": ["status.md", "spec.md", "plan.md", "tasks.md"],
    "Verify": ["status.md", "spec.md", "plan.md", "tasks.md"],
    "Done": ["status.md", "spec.md", "plan.md", "tasks.md", "review.md", "session-extracts.md"],
}


def _feature_artifact_name(artifact):
    if isinstance(artifact, str):
        return artifact
    if isinstance(artifact, dict) and artifact.get("kind") != "session":
        return artifact.get("name") or ""
    return ""


def files_for(root, *, skill="", phase=""):
    """Resolve the required file set for a skill route or coarse phase."""
    from core._lib.routing_metadata import skill_route

    skill_name = (skill or "").strip()
    phase_name = (phase or "").strip()
    if skill_name and phase_name:
        raise ValueError("--skill and --phase are mutually exclusive")
    if skill_name:
        route = skill_route(root, skill_name)
        if not route:
            raise ValueError(f"Skill not found in context routes: {skill_name}")
        prerequisites = [name for name in (route.get("prerequisites") or []) if isinstance(name, str) and name]
        structure = list(dict.fromkeys(prerequisites))
        heading_files = list(structure)
        for artifact in route.get("feature_artifacts") or []:
            name = _feature_artifact_name(artifact)
            if name and name not in heading_files:
                heading_files.append(name)
        return {
            "skill": skill_name,
            "phase": route.get("phase") or "",
            "prerequisites": structure,
            "structure": structure,
            "heading_files": heading_files,
            "headings": {
                name: REQUIRED_HEADINGS[name]
                for name in heading_files
                if name in REQUIRED_HEADINGS
            },
        }

    phase_name = phase_name or "Plan"
    structure = list(PHASE_FILES.get(phase_name, PHASE_FILES["Plan"]))
    prerequisites = []
    config_path = Path(root) / "corebase-specharness/project/harness-config.yaml"
    if config_path.is_file():
        from core.harness.config import HarnessConfig

        lifecycle = HarnessConfig(config_path).lifecycle or {}
        for item in lifecycle.get("phases", []):
            if item.get("name") != phase_name:
                continue
            for precondition in item.get("preconditions") or []:
                if not isinstance(precondition, dict):
                    continue
                if precondition.get("check", "exists") != "exists":
                    continue
                name = Path(str(precondition.get("artifact") or "")).name
                if name and name not in prerequisites:
                    prerequisites.append(name)
            break
    return {
        "skill": "",
        "phase": phase_name,
        "prerequisites": prerequisites,
        "structure": structure,
        "heading_files": list(structure),
        "headings": {
            name: REQUIRED_HEADINGS[name]
            for name in structure
            if name in REQUIRED_HEADINGS
        },
    }


def check_structure(fdir: Path, phase: str = "Plan", fileset=None, optional_files=None) -> tuple[list[str], list[str]]:
    errors, warns = [], []
    names = list(fileset) if fileset is not None else PHASE_FILES.get(phase, PHASE_FILES["Plan"])
    scope = phase or "check"
    for name in names:
        path = fdir / name
        if not path.exists():
            errors.append(f"missing required file for {scope}: {name}")
            continue
        warns.extend(check_required_headings(path))
    seen = set(names)
    for name in optional_files or []:
        if name in seen:
            continue
        path = fdir / name
        if path.exists():
            warns.extend(check_required_headings(path))
    return errors, warns


def check_required_headings(path: Path) -> list[str]:
    required = REQUIRED_HEADINGS.get(path.name, [])
    if not required or not path.is_file():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    return [f"{path.name} missing required heading: {heading.strip()}" for heading in required
            if heading not in text and heading.lower() not in text.lower()
            and not re.search(rf"^##\s+{re.escape(heading.lstrip('# ').lower())}\s*$", text, re.I | re.M)]


def _canonical(values):
    return {value.replace("_", "-").upper() for value in values}


def extract_ac_ids(text: str) -> set[str]:
    return _canonical(AC_RE.findall(text))


def extract_task_ids(text: str) -> set[str]:
    return set(TASK_RE.findall(text))


def traceability_summary(spec_text: str, tasks_text: str) -> dict:
    """Shared AC/task/proof facts used by readiness and final verification."""
    acs = extract_ac_ids(spec_text)
    task_ids = extract_task_ids(tasks_text)
    linked_acs = extract_ac_ids(tasks_text)
    done_without_evidence = []
    for match in DONE_TASK_RE.finditer(tasks_text):
        following = tasks_text[match.end():]
        next_task = re.search(r"(?im)^\s*[-*]\s+\[[ xX]\]\s+T-\d{3}\b", following)
        block = following[:next_task.start()] if next_task else following
        if not re.search(r"(?im)^\s*-?\s*(?:Validation evidence|Proof):\s*\S+", block):
            done_without_evidence.append(match.group(1))
    return {
        "acceptance_criteria": acs, "task_ids": task_ids, "linked_acceptance_criteria": linked_acs,
        "missing_task_links": sorted(acs - linked_acs),
        "orphan_task_links": sorted(linked_acs - acs),
        "done_without_evidence": sorted(done_without_evidence),
    }


def traceability_report(feature_dir: Path) -> tuple[list[str], list[str], list[str]]:
    texts = {}
    for name in ("spec.md", "plan.md", "tasks.md", "status.md"):
        path = feature_dir / name
        texts[name] = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    errors = []
    for failure in bidirectional_traceability(feature_dir):
        if failure.startswith("acceptance criteria without task linkage:"):
            errors.append("ACs without task linkage: " + failure.split(":", 1)[1].strip())
        elif failure.startswith("done tasks without validation evidence:"):
            errors.append("done tasks without validation evidence: " + failure.split(":", 1)[1].strip())
        elif failure.startswith("task-linked ACs not present in spec.md:"):
            errors.append("orphan ACs: " + failure.split(":", 1)[1].strip())
        else:
            errors.append(failure)
    reqs = set(re.findall(r"\bREQ-\d+\b", texts["spec.md"]))
    acs_spec = extract_ac_ids(texts["spec.md"])
    task_ids = extract_task_ids(texts["tasks.md"])
    acs_tasks = extract_ac_ids(texts["tasks.md"])
    lines = [
        "# Traceability Report", "", "| Kind | Count |", "| --- | --- |",
        f"| REQ | {len(reqs)} |", f"| AC (spec) | {len(acs_spec)} |",
        f"| AC (tasks) | {len(acs_tasks)} |", f"| TASK | {len(task_ids)} |", "",
    ]
    if errors:
        lines.append("**Issues Detected:**")
        lines.extend(f"- {error}" for error in errors)
    else:
        if not reqs and texts["spec.md"]:
            lines.append("**Note:** no REQ-* IDs found in spec.md")
        lines.append("**OK:** no orphan AC/TASK linkage issues detected.")
    lines.append("")
    return lines, errors, []


def bidirectional_traceability(feature_dir: Path) -> list[str]:
    spec, tasks, review = feature_dir / "spec.md", feature_dir / "tasks.md", feature_dir / "review.md"
    if not spec.is_file() or not tasks.is_file():
        return []
    summary = traceability_summary(spec.read_text(encoding="utf-8", errors="replace"),
                                   tasks.read_text(encoding="utf-8", errors="replace"))
    failures = []
    if not summary["acceptance_criteria"]:
        failures.append("spec.md contains no AC-* IDs")
    if not summary["task_ids"]:
        failures.append("tasks.md contains no T-NNN task IDs")
    if summary["missing_task_links"]:
        failures.append("acceptance criteria without task linkage: " + ", ".join(summary["missing_task_links"]))
    if summary["orphan_task_links"]:
        failures.append("task-linked ACs not present in spec.md: " + ", ".join(summary["orphan_task_links"]))
    if summary["done_without_evidence"]:
        failures.append("done tasks without validation evidence: " + ", ".join(summary["done_without_evidence"]))
    if review.is_file():
        review_text = review.read_text(encoding="utf-8", errors="replace").lower()
        if ("request_changes" in review_text or "changes requested" in review_text) and not extract_task_ids(review_text):
            failures.append("review findings require remediation task linkage")
    return failures
