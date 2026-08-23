"""Doctor support checks for the embedded lean-core payload."""

import ast
import fnmatch
from importlib import import_module
import json
from pathlib import Path
import re

REQUIRED_ROUTE_FIELDS = {
    "skill", "phase", "profile", "feature", "prerequisites",
    "feature_artifacts", "writes", "handoff", "sources",
}


def check_contracts(root):
    from core._lib.contracts import validate_manifest
    return validate_manifest(root)


def check_manifest_overlap(root):
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    groups = manifest.get("files", {})
    entries = [(group, item) for group in ("overwrite", "copyIfMissing") for item in groups.get(group, [])]
    files = [str(path.relative_to(root)).replace("\\", "/") for path in root.rglob("*") if path.is_file()]
    failures = []
    for index, (left_group, left) in enumerate(entries):
        left_matches = {path for path in files if fnmatch.fnmatch(path, left)}
        for right_group, right in entries[index + 1:]:
            if left_group == right_group:
                continue
            if left_matches & {path for path in files if fnmatch.fnmatch(path, right)}:
                failures.append(f"manifest ownership overlap: {left} / {right}")
    return failures


def check_context_routes(root):
    from core._lib.routing_metadata import (load_routes, normalize_write,
                                            path_for_source)
    from core._lib.yaml_reader import load as load_yaml

    root = Path(root)
    rows = load_routes(root).get("skills", [])
    state_machine = load_yaml(str(root / "corebase-specharness/project/state-machine.yaml")) or {}
    machine_phases = {
        phase.get("name") for phase in state_machine.get("phases", [])
        if isinstance(phase, dict) and phase.get("name")
    }
    machine_states = {
        state for state in state_machine.get("states", []) if isinstance(state, str)
    }
    failures = []
    if not rows:
        return ["context-routes.yaml has no skill routes"]
    names = [row.get("skill") for row in rows]
    known_names = {name for name in names if name}
    duplicates = sorted({name for name in names if name and names.count(name) > 1})
    failures.extend(f"duplicate context route: {name}" for name in duplicates)
    for row in rows:
        label = row.get("skill") or "unnamed"
        missing = REQUIRED_ROUTE_FIELDS - row.keys()
        if missing:
            failures.append(f"context route {label} missing fields: {', '.join(sorted(missing))}")
        if row.get("feature") not in {"required", "optional"}:
            failures.append(f"context route {label} feature must be required or optional")
        if not isinstance(row.get("phase"), str) or not row.get("phase"):
            failures.append(f"context route {label} phase must be a non-empty string")
            continue
        if row["phase"] not in machine_phases:
            failures.append(f"context route {label} phase {row['phase']} is not declared in state-machine.yaml")
        for field in ("enter", "exit"):
            value = row.get(field)
            if value in {None, ""}:
                continue
            if not isinstance(value, str) or value not in machine_states:
                failures.append(
                    f"context route {label} {field} {value} is not declared in state-machine.yaml"
                )
        if not isinstance(row.get("profile"), str) or not row.get("profile"):
            failures.append(f"context route {label} profile must be a non-empty string")
        for field in ("prerequisites", "feature_artifacts", "writes", "handoff"):
            if not isinstance(row.get(field), list):
                failures.append(f"context route {label} {field} must be a list")
        if "required_handoffs" in row:
            failures.append(f"context route {label} must not declare required_handoffs")
        for item in row.get("writes") or []:
            try:
                write = normalize_write(item)
            except ValueError as exc:
                failures.append(f"context route {label} has invalid write: {exc}")
                continue
            if write["kind"] == "directory" and write["required"]:
                failures.append(
                    f"context route {label} write {write['path']} is a directory and cannot be required"
                )
            if write["path"] == "status.md" and write["required"]:
                failures.append(
                    f"context route {label} write status.md is envelope-owned and cannot be required"
                )
        for target in row.get("handoff", []):
            if target not in known_names:
                failures.append(f"context route {label} references missing handoff skill {target}")
        if not isinstance(row.get("sources"), list):
            failures.append(f"context route {label} sources must be a list")
            continue
        for source in row["sources"]:
            if set(source) - {"path", "tier", "sections"} or "path" not in source:
                failures.append(f"context route {label} has invalid source fields")
                continue
            if source.get("tier", "Should") not in {"Must", "Should", "Skip"}:
                failures.append(f"context route {label} has invalid tier {source.get('tier')}")
            rel = path_for_source(source.get("path", ""))
            path = root / rel if rel else None
            if not path or not path.is_file():
                failures.append(f"context route {label} references missing file: {source.get('path', '')}")
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for section in source.get("sections", []):
                if not re.search(rf"^##\s+{re.escape(section)}\s*$", text, re.I | re.M):
                    failures.append(f"context route {label} references missing section {section} in {rel}")
    return failures


def check_command_registry(root):
    del root
    from core.cli import COMMANDS

    failures = []
    handlers = {}
    for command, entry in COMMANDS.items():
        if not isinstance(entry, tuple) or len(entry) != 3:
            failures.append(f"command {command} must define help, module, and handler")
            continue
        _, module_name, handler_name = entry
        key = (module_name, handler_name)
        if key in handlers:
            failures.append(f"duplicate command aliases: {handlers[key]} and {command}")
        handlers[key] = command
        try:
            handler = getattr(import_module(module_name), handler_name)
        except Exception as exc:
            failures.append(f"command {command} handler is unavailable: {exc}")
            continue
        if not callable(handler):
            failures.append(f"command {command} handler is not callable")
    return failures


def check_provider_contract(root):
    from core.handlers.diagnostics.providers import validate_provider_contract
    return validate_provider_contract(root)


def check_upgrade_contracts(root):
    """Keep kit-owned terminal escape transitions internally coherent.

    Budget honesty is enforced on the shipped seed by source-repo tests. Adopter
    `harness-config.yaml` is copy-if-missing and must not fail doctor after an
    upgrade that leaves an older ceiling in place.
    """
    from core._lib.yaml_reader import load as load_yaml

    machine = load_yaml(str(Path(root) / "corebase-specharness/project/state-machine.yaml")) or {}
    transitions = {
        (item.get("from"), item.get("to"))
        for item in machine.get("transitions", [])
        if isinstance(item, dict)
    }
    failures = []
    for state in ("ResearchComplete", "TaskPlanning", "PlanApproved", "Replanning"):
        if (state, "Blocked") not in transitions:
            failures.append(f"state-machine missing {state} -> Blocked transition")
    for state in (
        "ResearchComplete", "TaskPlanning", "PlanApproved", "Replanning",
        "NeedsClarification", "ChangesRequested", "Blocked",
    ):
        if (state, "Abandoned") not in transitions:
            failures.append(f"state-machine missing {state} -> Abandoned transition")
    return failures


def check_surface_integrity(root):
    root = Path(root)
    removed = [
        "corebase-specharness/scripts/core/harness/cli.py", "corebase-specharness/scripts/core/tool_providers.py",
        "corebase-specharness/scripts/core/dashboard_generator.py", "corebase-specharness/scripts/core/capability_recommender.py",
        "corebase-specharness/scripts/core/catalog_generator.py", "corebase-specharness/scripts/core/_lib/context_index.py",
        "corebase-specharness/scripts/core/_lib/budget.py",
        "corebase-specharness/scripts/core/_lib/telemetry_roi.py", "corebase-specharness/scripts/core/_lib/telemetry_store.py",
        "corebase-specharness/scripts/core/handlers/configuration.py", "corebase-specharness/scripts/core/handlers/handoff.py",
        "corebase-specharness/scripts/core/handlers/upgrades.py",
        "corebase-specharness/scripts/core/readiness.py",
        ".corebase-specharness/engine", ".corebase-specharness/scripts",
        "corebase-specharness/memories/repo/harness-config.md",
        "corebase-specharness/rules/architecture-principles.md",
        "corebase-specharness/rules/headroom.md",
        "corebase-specharness/generated",
        ".corebase-specharness/generated",
        ".corezero",
    ]
    leftovers = [f"removed leftover remains: {path}" for path in removed if (root / path).exists()]
    sessions = root / ".corebase-specharness" / "sessions"
    if sessions.is_dir():
        leftovers.extend(
            f"removed leftover remains: {path.relative_to(root)}"
            for path in sessions.rglob("last-pack.json")
            if path.is_file()
        )
        leftovers.extend(
            f"removed leftover remains: {path.relative_to(root)}"
            for path in sessions.rglob("*.lock")
            if path.is_file()
        )
    return leftovers


def _module_name(core_root, path):
    relative = path.relative_to(core_root.parent).with_suffix("")
    parts = relative.parts[:-1] if relative.name == "__init__" else relative.parts
    return ".".join(parts)


def _imported_modules(path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names if alias.name.startswith("core."))
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("core."):
            modules.add(node.module)
    return modules


def check_static_audit(root):
    """Audit source reachability and stale shipped references without importing extras."""
    from core.cli import COMMANDS

    root = Path(root)
    core_root = root / "corebase-specharness/scripts/core"
    paths = sorted(
        path for path in core_root.rglob("*.py")
        if "tests" not in path.parts
        and (
            path.name != "__init__.py"
            or path.parent.name == "diagnostics"
        )
    )
    modules = {_module_name(core_root, path): path for path in paths}
    roots = {"core.cli", "core.harness.doctor", "core.handlers.diagnostics"} | {
        entry[1] for entry in COMMANDS.values()
    }
    reachable = set(roots)
    unresolved_imports = set()
    changed = True
    while changed:
        changed = False
        for module in list(reachable):
            path = modules.get(module)
            if not path:
                continue
            for imported in _imported_modules(path):
                candidates = [name for name in modules if name == imported or name.startswith(imported + '.')]
                if not candidates:
                    unresolved_imports.add((module, imported))
                for candidate in candidates:
                    if candidate not in reachable:
                        reachable.add(candidate)
                        changed = True

    failures = [
        f"unreachable module shipped: {path.relative_to(root)}"
        for module, path in sorted(modules.items())
        if module not in reachable
    ]
    failures.extend(
        f"unresolvable internal import: {imported} imported by {module}"
        for module, imported in sorted(unresolved_imports)
    )

    seen = {}
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        key = str(path.relative_to(root)).lower()
        if key in seen:
            failures.append(f"duplicate case-insensitive path: {seen[key]} / {path.relative_to(root)}")
        seen[key] = path.relative_to(root)
    return failures


def check_project_setup(root):
    """Return advisory onboarding warnings without failing package health."""
    from core.harness.config import HarnessConfig
    config = HarnessConfig(Path(root) / "corebase-specharness/project/harness-config.yaml")
    warnings = []
    if config.project_setup_status() != "ready":
        warnings.append("project setup is not ready; run /starter-init or explicitly defer project tailoring")
    if not config.get_gates():
        warnings.append("no confirmed verification gates; advisory/no-gate verification cannot authorize Done without an explicit override")
    return warnings
