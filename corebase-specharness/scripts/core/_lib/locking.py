"""POSIX advisory file locks for serialized read-modify-write operations."""
from contextlib import contextmanager
import fcntl
from pathlib import Path


@contextmanager
def locked(path):
    """Hold an exclusive lock without leaving a leftover sidecar next to the target."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        lock_path = target
        created = False
    else:
        lock_path = target.parent / f".{target.name}.lock"
        created = True
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            if created:
                try:
                    lock_path.unlink()
                except OSError:
                    pass


