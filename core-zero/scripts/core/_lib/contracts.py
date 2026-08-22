"""Validation for the embedded CoreZero payload."""
import json
from pathlib import Path
import re

from core._lib.yaml_reader import loads as load_yaml_text

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$")

SCHEMA_VERSION = 1
SUPPORTED = "supported schema_version is 1"
_MIGRATE_FORMAT = (
    "schema_version {current} is unsupported (supported schema_version is 1); "
    "migrate by re-running bash core-zero/scripts/install.sh on the target checkouts "
    "or applying the shipped kit template {template}"
)
_MISSING_FORMAT = (
    "must declare schema_version: 1 ({supported}); migrate by re-running "
    "bash core-zero/scripts/install.sh or applying the shipped kit template {template}"
)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _schema_mapping(path):
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) < 3:
            return {}
        text = parts[1]
    data = load_yaml_text(text) or {}
    return data if isinstance(data, dict) else {}

def check_schema_version(path, name, template_label, supported=SCHEMA_VERSION):
    document = _schema_mapping(path) or {}
    if document.get("schema_version") != supported:
        if document.get("schema_version") is None:
            details = _MISSING_FORMAT.format(
                supported=SUPPORTED, template=template_label
            )
        else:
            details = _MIGRATE_FORMAT.format(
                current=document.get("schema_version"),
                template=template_label,
            )
        return [f"{name} {details}"]
    return []


def check_tool_providers_version(root):
    return check_schema_version(
        Path(root) / "core-zero/project/tool-providers.md", "tool-providers.md",
        "core-zero/project/tool-providers.md",
    )


def check_status_template_version(root):
    return check_schema_version(
        Path(root) / "skills/_shared/status-template.md", "status-template.md",
        "skills/_shared/status-template.md",
    )


def validate_manifest(root):
    root, path = Path(root), Path(root) / "manifest.json"
    if not path.is_file():
        return ["manifest.json missing"]
    try:
        manifest = load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"manifest.json is invalid JSON: {exc}"]
    failures = []
    for key in ("name", "version", "requires_python", "files"):
        if key not in manifest:
            failures.append(f"manifest.json missing required key: {key}")
    if not isinstance(manifest.get("version"), str) or not SEMVER_RE.fullmatch(manifest["version"]):
        failures.append("manifest.json version must be a valid SemVer string")
    files = manifest.get("files", {})
    if not isinstance(files, dict):
        return ["manifest.json files must be an object"]
    unknown = set(files) - {"overwrite", "copyIfMissing"}
    if unknown:
        failures.append("manifest files has unsupported keys: " + ", ".join(sorted(unknown)))
    owners = {group: set(files.get(group, [])) for group in ("overwrite", "copyIfMissing")}
    if owners["overwrite"] & owners["copyIfMissing"]:
        failures.append("manifest ownership overlaps between overwrite and copyIfMissing")
    for group in ("overwrite", "copyIfMissing"):
        for entry in files.get(group, []):
            if not any(token in entry for token in "*?[") and not (root / entry).is_file():
                failures.append(f"manifest {group} source missing: {entry}")
    generated = root / "core-zero/generated"
    if generated.exists():
        shipped = [item.name for item in generated.iterdir() if item.is_file() and item.name != ".gitkeep"]
        if shipped:
            failures.append("generated runtime state must not ship: " + ", ".join(sorted(shipped)))
    return failures
