"""POSIX advisory file locks for serialized read-modify-write operations."""
from contextlib import contextmanager
import fcntl
from pathlib import Path


@contextmanager
def locked(path):
    """Hold an exclusive sidecar lock for the lifetime of the context."""
    lock_path = Path(str(path) + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
