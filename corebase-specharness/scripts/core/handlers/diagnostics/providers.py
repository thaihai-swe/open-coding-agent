"""Optional local tool-provider configuration and execution."""

import json
import shutil
from pathlib import Path

from core._lib.yaml_reader import loads as load_yaml_text
from core.harness.gates import Gate
from core.handlers.common import _resolve_root, _result

VALID_CATEGORIES = {"review", "code-intelligence"}
VALID_MODES = {"optional", "required"}


def _registry(root):
    path = Path(root) / "references/tool-providers-registry.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid provider registry: {exc}") from exc
    providers = data.get("providers")
    if not isinstance(providers, list):
        raise ValueError("Provider registry must contain a providers list")
    return providers


def _provider_config(root):
    path = Path(root) / "corebase-specharness/project/tool-providers.md"
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Provider configuration frontmatter is incomplete")
    data = load_yaml_text(parts[1]) or {}
    if not isinstance(data, dict):
        raise ValueError("Provider configuration frontmatter must be a mapping")
    return data.get("providers") or {}


def _selection(root, category):
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Unknown provider category: {category}")
    selected = _provider_config(root).get(category) or {}
    if not isinstance(selected, dict):
        raise ValueError(f"Provider category '{category}' must be a mapping")
    active = selected.get("active", "none")
    mode = selected.get("mode", "optional")
    if not isinstance(active, str):
        raise ValueError(f"Provider category '{category}' active value must be a string")
    if mode not in VALID_MODES:
        raise ValueError(f"Provider category '{category}' mode must be optional or required")
    return {"active": active, "mode": mode}


def _selected_provider(root, category):
    selection = _selection(root, category)
    if selection["active"] == "none":
        return selection, None
    provider = next(
        (item for item in _registry(root)
         if item.get("id") == selection["active"] and item.get("category") == category),
        None,
    )
    if provider is None:
        raise ValueError(
            f"Configured {category} provider '{selection['active']}' is not in the registry"
        )
    return selection, provider


def _availability(provider):
    executable = str(provider.get("executable", ""))
    return bool(executable and shutil.which(executable))


def _details(root, category):
    selection, provider = _selected_provider(root, category)
    if provider is None:
        return {
            "category": category,
            "active": "none",
            "mode": selection["mode"],
            "available": False,
            "guide": "",
            "actions": [],
        }
    return {
        "category": category,
        "active": provider["id"],
        "mode": selection["mode"],
        "available": _availability(provider),
        "guide": provider.get("guide", ""),
        "actions": sorted((provider.get("actions") or {}).keys()),
    }


def validate_provider_contract(root):
    errors = []
    try:
        providers = _registry(root)
    except ValueError as exc:
        return [str(exc)]
    seen = set()
    for provider in providers:
        provider_id = provider.get("id")
        category = provider.get("category")
        if not isinstance(provider_id, str) or not provider_id:
            errors.append("Provider registry entry missing id")
            continue
        if provider_id in seen:
            errors.append(f"Duplicate provider registry id: {provider_id}")
        seen.add(provider_id)
        if category not in VALID_CATEGORIES:
            errors.append(f"Provider '{provider_id}' has invalid category")
        if not isinstance(provider.get("executable"), str) or not provider["executable"]:
            errors.append(f"Provider '{provider_id}' missing executable")
        if not isinstance(provider.get("guide"), str) or not (Path(root) / provider["guide"]).is_file():
            errors.append(f"Provider '{provider_id}' guide is missing")
        for action, command in (provider.get("actions") or {}).items():
            if not isinstance(action, str) or not isinstance(command, list) or not command:
                errors.append(f"Provider '{provider_id}' action '{action}' must be a non-empty argv list")
    for category in VALID_CATEGORIES:
        try:
            _selected_provider(root, category)
        except ValueError as exc:
            errors.append(str(exc))
    return errors


def provider_list(args):
    root = _resolve_root(args)
    return _result("provider-list", details={
        "providers": _registry(root),
        "configured": [_details(root, category) for category in sorted(VALID_CATEGORIES)],
    })


def provider_check(args):
    root = _resolve_root(args)
    categories = [args.category] if getattr(args, "category", "") else sorted(VALID_CATEGORIES)
    details = [_details(root, category) for category in categories]
    warnings = [
        f"Optional provider '{item['active']}' is unavailable"
        for item in details
        if item["active"] != "none" and item["mode"] == "optional" and not item["available"]
    ]
    errors = [
        f"Required provider '{item['active']}' is unavailable"
        for item in details
        if item["active"] != "none" and item["mode"] == "required" and not item["available"]
    ]
    return _result(
        "provider-check",
        "failed" if errors else ("deferred" if warnings else "ok"),
        warnings=warnings,
        errors=errors,
        details={"providers": details},
    )


def run_provider(root, category, action="", feature="", dry_run=False):
    selection, provider = _selected_provider(root, category)
    if provider is None:
        details = _details(root, category)
        details.update({"executed": False, "required": selection["mode"] == "required"})
        return _result(
            "provider-run",
            "deferred",
            feature=feature,
            warnings=[f"No {category} provider is enabled"],
            details=details,
        )
    if not _availability(provider):
        message = f"Provider '{provider['id']}' is unavailable"
        details = _details(root, category)
        details.update({"executed": False, "required": selection["mode"] == "required"})
        return _result(
            "provider-run",
            "failed" if selection["mode"] == "required" else "deferred",
            feature=feature,
            warnings=[] if selection["mode"] == "required" else [message],
            errors=[message] if selection["mode"] == "required" else [],
            details=details,
        )

    action = action or ("run" if category == "review" else "check")
    if action == "check":
        details = _details(root, category)
        details.update({"executed": False, "required": selection["mode"] == "required"})
        return _result(
            "provider-run",
            feature=feature,
            details=details,
            next_action=f"Use {provider.get('guide', '')} for provider-specific agent or MCP actions.",
        )
    command = (provider.get("actions") or {}).get(action)
    if not isinstance(command, list) or not command:
        raise ValueError(f"Provider '{provider['id']}' does not support action '{action}'")
    gate = Gate(
        name=f"{provider['id']}:{action}",
        command=command,
        on_fail="block",
        config={"thresholds": {"timeout_seconds": 300}},
    )
    result = gate.run(root, dry_run=dry_run).to_dict()
    details = _details(root, category)
    details.update({"executed": True, "required": selection["mode"] == "required", "action": action, "result": result})
    return _result(
        "provider-run",
        "ok" if result["passed"] is True else ("deferred" if result["passed"] is None else "failed"),
        feature=feature,
        errors=[] if result["passed"] else [result["error"] or "Provider command failed"],
        details=details,
    )


def provider_run(args):
    return run_provider(
        _resolve_root(args),
        args.category,
        action=getattr(args, "action", "") or "",
        feature=getattr(args, "feature", "") or "",
        dry_run=getattr(args, "dry_run", False),
    )
