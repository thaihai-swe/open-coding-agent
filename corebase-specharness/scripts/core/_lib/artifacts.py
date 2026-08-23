"""Feature-artifact path helpers with strict containment."""
import re
from pathlib import Path

CANONICAL_FEATURES_RELATIVE_PATH = Path("artifacts/features")
SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,62}")


def validate_feature_slug(slug):
    value = (slug or "").strip()
    if not SLUG_RE.fullmatch(value):
        raise ValueError("--feature must be a lowercase hyphenated slug (1-63 characters)")
    return value


def canonical_features_dir(root):
    return Path(root).resolve() / CANONICAL_FEATURES_RELATIVE_PATH


def _contained(root, candidate):
    root, candidate = Path(root).resolve(), Path(candidate).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes managed root: {candidate}") from exc
    return candidate


def canonical_feature_dir(root, slug):
    base = canonical_features_dir(root)
    return _contained(base, base / validate_feature_slug(slug))



def read_feature_status(root, slug):
    slug = validate_feature_slug(slug)
    status_path = canonical_feature_dir(root, slug) / "status.md"
    text = status_path.read_text(encoding="utf-8", errors="replace") if status_path.is_file() else ""
    fields = {line[2:].split(":", 1)[0].strip().lower(): line.split(":", 1)[1].strip() for line in text.splitlines() if line.startswith("- ") and ":" in line}
    return {"slug": slug, "phase": fields.get("phase", "Unknown"), "delivery_profile": fields.get("delivery profile", "Baseline"), "status": fields.get("status", "Unknown"), "next_step": fields.get("next step", ""), "blockers": fields.get("blockers", ""), "has_blocker": "blocked" in fields.get("status", "").lower() or bool(fields.get("blockers", "").strip())}


def list_features(root):
    base = canonical_features_dir(root)
    return [read_feature_status(root, item.name) for item in sorted(base.iterdir()) if item.is_dir() and SLUG_RE.fullmatch(item.name)] if base.is_dir() else []



def resolve_artifact_path(feature_dir, artifact_template, feature_slug=None):
    slug = validate_feature_slug(feature_slug or Path(feature_dir).name)
    value = str(artifact_template).replace("<slug>", slug).replace("{feature}", slug)
    if Path(value).is_absolute() or ".." in Path(value).parts:
        raise ValueError(f"invalid artifact path: {artifact_template}")
    feature_dir = Path(feature_dir).resolve()
    if value.startswith("features/"):
        return str(_contained(feature_dir.parent.parent, feature_dir.parent.parent / value))
    return str(_contained(feature_dir, feature_dir / value))
