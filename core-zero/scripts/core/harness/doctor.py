"""Local package-health checks for an embedded CoreZero installation."""
from core._lib import doctor_checks
from core._lib.root import resolve_root
from core.harness.config import HarnessConfig


def run_doctor(root_path):
    root = resolve_root(root_path)
    if not root:
        return {"ok": False, "checks": [], "failed": 1, "error": "Could not resolve repository root"}
    checks = []
    for name, callback in (
        ("manifest", lambda: doctor_checks.check_contracts(root)),
        ("ownership", lambda: doctor_checks.check_manifest_overlap(root)),
        ("surfaces", lambda: doctor_checks.check_surface_integrity(root)),
        ("context_routes", lambda: doctor_checks.check_context_routes(root)),
        ("skills", lambda: doctor_checks.check_skill_contracts(root)),
        ("commands", lambda: doctor_checks.check_command_registry(root)),
        ("providers", lambda: doctor_checks.check_provider_contract(root)),
        ("upgrade_contracts", lambda: doctor_checks.check_upgrade_contracts(root)),
        ("static_audit", lambda: doctor_checks.check_static_audit(root)),
    ):
        try:
            failures = callback()
        except Exception as exc:
            failures = [str(exc)]
        checks.append({"name": name, "status": "pass" if not failures else "fail",
                       "message": "ok" if not failures else "; ".join(failures)})
    try:
        HarnessConfig(f"{root}/core-zero/project/harness-config.yaml")
        checks.append({"name": "configuration", "status": "pass", "message": "ok"})
    except Exception as exc:
        checks.append({"name": "configuration", "status": "fail", "message": str(exc)})
    try:
        warnings = doctor_checks.check_project_setup(root)
    except Exception as exc:
        warnings = [f"project setup could not be evaluated: {exc}"]
    checks.append({"name": "project_setup", "status": "warn" if warnings else "pass", "message": "ok" if not warnings else "; ".join(warnings)})
    failed = sum(check["status"] == "fail" for check in checks)
    return {"ok": failed == 0, "checks": checks, "failed": failed}


def doctor(args):
    outcome = run_doctor(args.root)
    errors = [
        f"{check['name']}: {check['message']}"
        for check in outcome.get("checks", [])
        if check.get("status") == "fail"
    ]
    warnings = [
        f"{check['name']}: {check['message']}"
        for check in outcome.get("checks", [])
        if check.get("status") == "warn"
    ]
    return {
        "status": "ok" if outcome.get("ok") else "failed",
        "errors": errors,
        "warnings": warnings,
        "details": outcome,
    }
