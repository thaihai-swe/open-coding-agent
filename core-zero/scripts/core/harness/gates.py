import os
import shlex
import shutil
import signal
import subprocess
import time

MAX_OUTPUT_BYTES = 64 * 1024


def changed_files_from_git(root_dir):
    """Return repository-relative changed paths, or None when git is unavailable."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(root_dir),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    files = []
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path:
            files.append(path)
    return files


class GateResult:
    def __init__(self, name, passed, output, error=None, duration_ms=0, executed=True):
        self.name, self.passed, self.output = name, passed, output
        self.error, self.duration_ms, self.executed = error, duration_ms, executed

    def to_dict(self):
        return {
            "name": self.name,
            "passed": self.passed,
            "executed": self.executed,
            "output_tail": self.output[-2000:],
            "truncated": len(self.output.encode("utf-8", errors="replace")) >= MAX_OUTPUT_BYTES,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


class Gate:
    def __init__(self, name, command, on_fail, config, category="", required=True, timeout_seconds=None, allow_shell=False, paths=None):
        self.name, self.command, self.on_fail, self.config = name, command, on_fail or "block", config
        self.category, self.required = category or "", bool(required)
        self.timeout_seconds, self.allow_shell = timeout_seconds, bool(allow_shell)
        self.paths = [str(item) for item in (paths or []) if str(item).strip()]

    def matches_changed_files(self, changed_files):
        """Return True when this gate should run for the given changed-file list."""
        if not self.paths:
            return True
        if changed_files is None:
            return True
        from fnmatch import fnmatch
        for relative in changed_files:
            value = str(relative).lstrip("./")
            for pattern in self.paths:
                if fnmatch(value, pattern) or fnmatch(value, pattern.rstrip("/") + "/**"):
                    return True
        return False

    def run(self, root_dir, dry_run=False, changed_files=None):
        argv = [str(part) for part in self.command] if isinstance(self.command, (list, tuple)) else []
        display = self.command if self.allow_shell else " ".join(shlex.quote(part) for part in argv)
        if changed_files is not None and not self.matches_changed_files(changed_files):
            return GateResult(
                self.name, True, f"[fast] skipped: no matching changed files for {self.name}", executed=False
            )
        if dry_run:
            return GateResult(
                self.name, None, f"[dry-run] would run: {display}", executed=False
            )
        if not self.allow_shell and not shutil.which(argv[0]):
            return GateResult(self.name, False, "", f"UNAVAILABLE: tool '{argv[0]}' not found")
        started = time.monotonic()
        process = None
        try:
            process = subprocess.Popen(self.command if self.allow_shell else argv, shell=self.allow_shell, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=False, cwd=str(root_dir), start_new_session=True)
            output, _ = process.communicate(timeout=self.timeout_seconds or self.config.get("thresholds", {}).get("timeout_seconds", 300))
            text = output[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
            return GateResult(self.name, process.returncode == 0, text, None if process.returncode == 0 else text[-2000:], int((time.monotonic() - started) * 1000))
        except subprocess.TimeoutExpired:
            if process:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    output, _ = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    output, _ = process.communicate()
            else:
                output = b""
            return GateResult(self.name, False, output[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace"), "TIMEOUT", int((time.monotonic() - started) * 1000))
        except Exception as exc:
            return GateResult(self.name, False, "", str(exc), int((time.monotonic() - started) * 1000))
