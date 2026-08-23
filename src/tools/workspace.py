import pathlib


def bound_path(path: str, *, cwd: pathlib.Path | None = None) -> pathlib.Path:
    root = (cwd or pathlib.Path.cwd()).resolve()
    resolved = pathlib.Path(path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"Path is outside workspace: {path}")
    return resolved
