"""Explicit gate listing and configuration validation."""

import shutil

from core.harness.config import HarnessConfig
from core.handlers.common import _resolve_root, _result


def _config(root):
    return HarnessConfig(root / "corebase-specharness/project/harness-config.yaml")


def gate_list(args):
    root = _resolve_root(args)
    rows = []
    for gate in _config(root).get_gates():
        command = gate.command
        first = str(command[0]) if isinstance(command, (list, tuple)) and command else ""
        rows.append({
            "name": gate.name,
            "command": command,
            "on_fail": gate.on_fail,
            "category": gate.category,
            "required": gate.required,
            "available": True if gate.allow_shell else bool(first and shutil.which(first)),
        })
    return _result("gate-list", details={"gates": rows})


def gate_check(args):
    root = _resolve_root(args)
    errors, warnings = [], []
    from core.harness.gates import changed_files_from_git
    changed_files = changed_files_from_git(root) if getattr(args, "fast", False) else None
    skipped = []
    for gate in _config(root).get_gates():
        if changed_files is not None and not gate.matches_changed_files(changed_files):
            skipped.append(gate.name)
            continue
        if gate.allow_shell:
            continue
        if not shutil.which(str(gate.command[0])):
            (errors if gate.required else warnings).append(
                f"Gate '{gate.name}' command '{gate.command[0]}' is unavailable")
    return _result(
        "gate-check",
        "failed" if errors else ("deferred" if warnings else "ok"),
        warnings=warnings,
        errors=errors,
        details={"errors": errors, "warnings": warnings, "skipped": skipped, "fast": bool(getattr(args, "fast", False))},
    )
