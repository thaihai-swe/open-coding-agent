"""Phase-readiness checks derived from shared artifact traceability facts."""
from pathlib import Path
from typing import Any

from core._lib.artifacts import canonical_feature_dir
from core._lib.artifact_schema import traceability_summary


def check_requirements_readiness(root: Path, feature: str) -> dict[str, Any]:
    feature_dir = canonical_feature_dir(root, feature)
    spec, tasks = feature_dir / "spec.md", feature_dir / "tasks.md"
    warnings, errors = [], []
    spec_text = spec.read_text(encoding="utf-8", errors="replace") if spec.is_file() else ""
    tasks_text = tasks.read_text(encoding="utf-8", errors="replace") if tasks.is_file() else ""
    if not spec.is_file():
        warnings.append("spec.md not found")
    if not tasks.is_file():
        warnings.append("tasks.md not found")
    summary = traceability_summary(spec_text, tasks_text)
    if spec.is_file() and not summary["acceptance_criteria"]:
        errors.append("spec.md contains no AC-* IDs")
    if tasks.is_file() and not summary["task_ids"]:
        errors.append("tasks.md contains no T-NNN task IDs")
    if tasks.is_file() and summary["missing_task_links"]:
        errors.append("ACs without task linkage: " + ", ".join(summary["missing_task_links"]))
    if tasks.is_file() and summary["orphan_task_links"]:
        errors.append("orphan ACs: " + ", ".join(summary["orphan_task_links"]))
    return {
        "feature": feature, "ok": not errors, "errors": errors, "warnings": warnings,
        "metrics": {
            "acceptance_criteria_count": len(summary["acceptance_criteria"]),
            "ac_mapped_to_tasks": len(summary["linked_acceptance_criteria"] & summary["acceptance_criteria"]),
            "unmapped_criteria": summary["missing_task_links"],
            "traceability_complete": not summary["missing_task_links"] and not summary["orphan_task_links"],
        },
        "readiness_score": 100 if not errors else 50 if summary["acceptance_criteria"] else 0,
    }
