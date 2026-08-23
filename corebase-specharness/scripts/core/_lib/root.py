"""Locate an embedded, project-local CoreBase SpecHarness installation."""
from pathlib import Path


def _is_embedded_root(path):
    return (
        (path / "manifest.json").is_file()
        and (path / "corebase-specharness" / "scripts" / "core" / "cli.py").is_file()
    )


def resolve_root(hint=None):
    """Resolve ``hint`` or the current directory upward to an embedded project root."""
    start = Path(hint).resolve() if hint else Path.cwd().resolve()
    if start.is_file():
        start = start.parent
    for candidate in (start, *start.parents):
        if _is_embedded_root(candidate):
            return str(candidate)
    return None
