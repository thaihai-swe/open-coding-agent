"""Validation for the embedded CoreBase SpecHarness payload."""
import json
from pathlib import Path
import re

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


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
    generated = root / ".corebase-specharness/generated"
    if generated.exists():
        shipped = [item.name for item in generated.iterdir() if item.is_file() and item.name != ".gitkeep"]
        if shipped:
            failures.append("generated runtime state must not ship: " + ", ".join(sorted(shipped)))
    return failures
