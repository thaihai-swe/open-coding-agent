#!/usr/bin/env bash
# Deterministic embedded CoreZero installer: copy, seed, then validate locally.
set -euo pipefail

err() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
log() { printf '%s\n' "$*"; }
target=""
dry_run=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) dry_run=true; shift ;;
    --non-interactive) shift ;;
    -h|--help) printf 'Usage: install.sh <target_dir> [--dry-run]\n'; exit 0 ;;
    *) [[ -z "$target" ]] || err "unexpected argument: $1"; target="$1"; shift ;;
  esac
done
[[ -n "$target" ]] || err "Usage: install.sh <target_dir> [--dry-run]"
source_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
manifest="$source_dir/manifest.json"
[[ -f "$manifest" ]] || err "manifest.json not found"
command -v python3 >/dev/null || err "python3 is required"
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' || err "python3.10 or newer is required"

# Preflight: validate manifest shape and path safety before any target mutation.
python3 - "$manifest" "$source_dir" <<'PY' || err "manifest preflight failed"
import glob, json, sys
from pathlib import Path

manifest_path, source = sys.argv[1:]
try:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    print(f"manifest is not valid JSON: {exc}", file=sys.stderr)
    raise SystemExit(1)
errors = []
for key in ("name", "version", "requires_python", "files"):
    if key not in manifest:
        errors.append(f"manifest missing required key: {key}")
files = manifest.get("files", {})
if not isinstance(files, dict):
    errors.append("manifest files must be an object")
    files = {}
unknown = set(files) - {"overwrite", "copyIfMissing"}
if unknown:
    errors.append("manifest files has unsupported keys: " + ", ".join(sorted(unknown)))
for group in ("overwrite", "copyIfMissing"):
    for item in files.get(group, []):
        if not isinstance(item, str) or not item:
            errors.append(f"manifest {group} entries must be non-empty strings")
            continue
        path = Path(item)
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"manifest {group} path is unsafe: {item}")
            continue
        if any(token in item for token in "*?["):
            if not glob.glob(str(Path(source) / item), recursive=True):
                errors.append(f"manifest {group} pattern matches nothing: {item}")
        elif not (Path(source) / item).is_file():
            errors.append(f"manifest {group} source missing: {item}")
if errors:
    print("manifest validation failed:", file=sys.stderr)
    print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
    raise SystemExit(1)
PY

if $dry_run; then
  target="$(python3 - "$target" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve())
PY
)"
else
  mkdir -p "$target"
  target="$(cd "$target" && pwd)"
fi
if $dry_run; then
  backup="$target/.corezero-backup-dry-run"
else
  backup="$(mktemp -d "$target/.corezero-backup-XXXXXXXX")" || err "failed to allocate backup directory"
fi

copy_group() {
  local group="$1" mode="$2"
  python3 - "$manifest" "$group" "$source_dir" <<'PY' | while IFS= read -r rel; do
import glob, json, sys
from pathlib import Path
manifest, group, source = sys.argv[1:]
for item in json.loads(Path(manifest).read_text())['files'][group]:
    for raw in glob.glob(str(Path(source) / item), recursive=True):
        path = Path(raw)
        if path.is_file() and path.name != '.gitkeep' and '__pycache__' not in path.parts and not path.name.endswith(('.pyc', '.pyo')) and not path.name.startswith('test_'):
            print(path.relative_to(source).as_posix())
PY
    [[ -n "$rel" ]] || continue
    local src="$source_dir/$rel" dst="$target/$rel"
    if [[ "$mode" == seed && ( -e "$dst" || -L "$dst" ) ]]; then log "  preserve seed: $rel"; continue; fi
    if [[ -L "$dst" && "$mode" == overwrite ]]; then
      if $dry_run; then
        log "  [dry-run] backup overwrite link: $rel"
        log "  [dry-run] remove overwrite link: $rel"
      else
        mkdir -p "$(dirname "$backup/$rel")"
        cp -P "$dst" "$backup/$rel"
        rm -- "$dst"
      fi
    elif [[ -f "$dst" && "$mode" == overwrite ]]; then
      if $dry_run; then log "  [dry-run] backup: $rel"; else mkdir -p "$(dirname "$backup/$rel")"; cp "$dst" "$backup/$rel"; fi
    fi
    if $dry_run; then log "  [dry-run] copy: $rel"; else mkdir -p "$(dirname "$dst")"; cp "$src" "$dst"; fi
  done
}

manifest_version="$(python3 - "$manifest" <<'PY'
import json, sys
print(json.loads(open(sys.argv[1], encoding="utf-8").read())["version"])
PY
)"
overwrite_count="$(python3 - "$manifest" "$source_dir" <<'PY'
import glob, json, sys
from pathlib import Path
manifest, source = sys.argv[1:]
items = json.loads(Path(manifest).read_text())["files"]["overwrite"]
print(sum(1 for item in items for raw in glob.glob(str(Path(source) / item), recursive=True)
          if Path(raw).is_file() and Path(raw).name != ".gitkeep" and "__pycache__" not in Path(raw).parts
          and not Path(raw).name.endswith((".pyc", ".pyo")) and not Path(raw).name.startswith("test_")))
PY
)"
preserved_count="$(python3 - "$manifest" "$source_dir" "$target" <<'PY'
import glob, json, sys
from pathlib import Path
manifest, source, target = sys.argv[1:]
items = json.loads(Path(manifest).read_text())["files"]["copyIfMissing"]
print(sum(1 for item in items for raw in glob.glob(str(Path(source) / item), recursive=True)
          if Path(raw).is_file() and Path(raw).name != ".gitkeep" and "__pycache__" not in Path(raw).parts
          and not Path(raw).name.endswith((".pyc", ".pyo")) and not Path(raw).name.startswith("test_")
          and ((Path(target) / Path(raw).relative_to(source)).exists() or (Path(target) / Path(raw).relative_to(source)).is_symlink())))
PY
)"

log "Installing CoreZero v$manifest_version (overwrite files: $overwrite_count)"
copy_group overwrite overwrite
copy_group copyIfMissing seed
if ! $dry_run; then
  mkdir -p "$target/core-zero/generated"
  touch "$target/core-zero/generated/.gitkeep"
  chmod +x "$target/core-zero/scripts/install.sh" "$target/core-zero/scripts/validate-skill-consistency.py" "$target/core-zero/scripts/validate-static-audit.py"
  python3 "$target/core-zero/scripts/core/cli.py" doctor --root "$target" --json >/dev/null
fi
log "Installed embedded runtime: python3 core-zero/scripts/core/cli.py"
log "Upgrade report: refreshed $overwrite_count kit-owned files; preserved $preserved_count adopter-owned seeds."
log "harness-config.yaml, memories, feature artifacts, sessions, and generated state are not replaced."
log "Next (new/untailored repo): run /starter-init before delivery skills."
log "Next (tailored upgrade): invoke the appropriate named delivery skill directly."
