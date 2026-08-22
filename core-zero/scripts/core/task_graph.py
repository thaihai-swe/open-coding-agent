"""Parse the Markdown task graph and enforce canonical task transitions."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from core._lib.artifacts import canonical_feature_dir
from core.context_state import atomic_write

# Canonical task identifiers are T-001. Older TASK-* forms are not parsed so stale task files fail loudly.
TASK_ID_RE = re.compile(r"\bT-(\d{3})\b")
# Checkbox task header: - [ ] T-001 or - [x] T-001-title
TASK_HEADER_RE = re.compile(
    r"^(\s*)[-*]\s+\[([ xX])\]\s+(T-\d{3})\b(.*)$",
    re.MULTILINE,
)
# Depends-on / Depends on: T-001, T-002, or - Depends on:
DEPENDS_RE = re.compile(
    r"(?im)^\s*(?:[-*]\s+)?Depends[- ]on:\s*(.*)$",
)
STATUS_RE = re.compile(r"(?im)^\s*(?:[-*]\s+)?Status:\s*(.+)$")
EVIDENCE_RE = re.compile(r"(?im)^\s*(?:[-*]\s+)?(?:Validation evidence|Proof):\s*(\S.*)$")
AC_RE = re.compile(r"\bAC[-_]?\d+\b")
STATUS_LINE_RE = re.compile(r"(?im)^(\s*(?:[-*]\s+)?Status:\s*).*$", re.MULTILINE)
CHECKBOX_RE = re.compile(r"^(\s*[-*]\s+)\[[ xX]\]")
DONE_STATUSES = {"done", "deferred"}
TASK_STATUSES = {"Not Started", "In Progress", "Blocked", "Done", "Deferred"}
ALLOWED_TRANSITIONS = {
    "Not Started": {"Not Started", "In Progress", "Blocked", "Deferred"},
    "In Progress": {"Not Started", "In Progress", "Blocked", "Done", "Deferred"},
    "Blocked": {"Not Started", "In Progress", "Blocked", "Deferred"},
    "Done": {"Done", "In Progress"},
    "Deferred": {"Deferred", "Not Started", "In Progress"},
}


def normalize_status(status: str) -> str:
    """Normalize legacy casing without changing the Markdown until a write."""
    for canonical in TASK_STATUSES:
        if canonical.lower() == (status or "").strip().lower():
            return canonical
    return (status or "Not Started").strip()


def _normalize_id(token: str) -> str | None:
    m = TASK_ID_RE.search(token or "")
    if not m:
        return None
    return f"T-{m.group(1)}"


def parse_tasks(text: str) -> list[dict]:
    """Return list of {id, done, depends, status, header} in file order."""
    if not text:
        return []
    headers = list(TASK_HEADER_RE.finditer(text))
    tasks = []
    for i, m in enumerate(headers):
        start = m.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        block = text[start:end]
        tid = m.group(3)
        checked = m.group(2).lower() == "x"
        status_m = STATUS_RE.search(block)
        status = (status_m.group(1).strip() if status_m else "").strip()
        done = checked or status.lower() in DONE_STATUSES
        deps = []
        for dm in DEPENDS_RE.finditer(block):
            raw = dm.group(1).strip()
            if not raw or raw in ("—", "-", "n/a", "N/A", "none", "None"):
                continue
            for part in re.split(r"[,;\s]+", raw):
                dep = _normalize_id(part)
                if dep and dep != tid:
                    deps.append(dep)
        # de-dupe preserve order
        seen = set()
        uniq = []
        for d in deps:
            if d not in seen:
                seen.add(d)
                uniq.append(d)
        evidence_m = EVIDENCE_RE.findall(block)
        ac_m = AC_RE.findall(block)
        tasks.append(
            {
                "id": tid,
                "done": done,
                "depends": uniq,
                "status": status or ("Done" if done else "Not Started"),
                "header": m.group(0).strip(),
                "checked": checked,
                "has_explicit_status": bool(status_m),
                "evidence": [e.strip() for e in evidence_m],
                "acceptance_criteria": list(set(ac_m)),
            }
        )
    return tasks


def detect_cycle(tasks: list[dict]) -> list[str] | None:
    """Return a cycle path, if any, without recursion-depth limits."""
    graph = {task["id"]: list(task["depends"]) for task in tasks}
    task_ids = set(graph)
    for task_id, dependencies in graph.items():
        graph[task_id] = [dependency for dependency in dependencies if dependency in task_ids]

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {task_id: WHITE for task_id in graph}
    parent = {}
    for start in graph:
        if color[start] != WHITE:
            continue
        color[start] = GRAY
        stack = [(start, iter(graph[start]))]
        while stack:
            task_id, dependencies = stack[-1]
            try:
                dependency = next(dependencies)
            except StopIteration:
                color[task_id] = BLACK
                stack.pop()
                continue
            if color[dependency] == GRAY:
                cycle = [dependency]
                cursor = task_id
                while cursor != dependency:
                    cycle.append(cursor)
                    cursor = parent[cursor]
                cycle.append(dependency)
                cycle.reverse()
                return cycle
            if color[dependency] == WHITE:
                parent[dependency] = task_id
                color[dependency] = GRAY
                stack.append((dependency, iter(graph[dependency])))
    return None


def validate_task_consistency(tasks: list[dict]) -> list[str]:
    """Validate explicit task statuses and checkbox/status agreement."""
    errors = []
    for task in tasks:
        status = normalize_status(task.get("status", ""))
        if status not in TASK_STATUSES:
            errors.append(f"{task['id']} has unknown status: {task.get('status', '')}")
            continue
        if task.get("has_explicit_status"):
            checked = bool(task.get("checked"))
            status_done = status.lower() in DONE_STATUSES
            if checked != status_done:
                expected_checkbox = "[x]" if status_done else "[ ]"
                errors.append(
                    f"{task['id']} checkbox/status disagreement: "
                    f"checkbox is {'[x]' if checked else '[ ]'} but Status is {status}; "
                    f"set the checkbox to {expected_checkbox} or change Status to "
                    f"{'Done' if checked else 'Not Started'} before using task commands"
                )
    return errors


def next_tasks(tasks: list[dict]) -> list[dict]:
    """Incomplete tasks whose Depends-on are all done (or empty).

    If no task has Depends-on filled, fall back to first incomplete in file order.
    """
    by_id = {t["id"]: t for t in tasks}
    any_deps = any(t["depends"] for t in tasks)
    incomplete = [t for t in tasks if not t["done"]]
    if not incomplete:
        return []
    if not any_deps:
        return [incomplete[0]]

    ready = []
    for task in incomplete:
        dependencies = task["depends"]
        if not dependencies:
            ready.append(task)
            continue
        # Missing dependencies are invalid and therefore never ready; known
        # dependencies must all be complete before this task can start.
        if all(by_id.get(dependency, {}).get("done", False) for dependency in dependencies):
            ready.append(task)
    return ready


def feature_tasks_path(root: Path, slug: str) -> Path:
    return canonical_feature_dir(root, slug) / "tasks.md"


def feature_tasks_sidecar_path(root: Path, slug: str) -> Path:
    return canonical_feature_dir(root, slug) / "tasks.json"


def sidecar_to_tasks(sidecar: dict) -> list[dict]:
    tasks = []
    for item in sidecar.get("tasks", []):
        tasks.append(
            {
                "id": item.get("id", ""),
                "done": item.get("status") in {"Done", "Deferred"} or bool(item.get("done")),
                "depends": list(item.get("depends", [])),
                "status": item.get("status", "Not Started"),
                "header": item.get("header", ""),
                "evidence": list(item.get("evidence", [])),
                "acceptance_criteria": list(item.get("acceptance_criteria", [])),
            }
        )
    return tasks


def load_tasks(root: Path, slug: str) -> list[dict]:
    """Load tasks from tasks.md when present; fall back to the tasks.json sidecar."""
    path = feature_tasks_path(root, slug)
    if path.is_file():
        return parse_tasks(path.read_text(encoding="utf-8", errors="replace"))
    sidecar = feature_tasks_sidecar_path(root, slug)
    if sidecar.is_file():
        try:
            data = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        if data.get("schema_version") != 1:
            return []
        return sidecar_to_tasks(data)
    return []


def _duplicate_ids(tasks: list[dict]) -> list[str]:
    seen = set()
    duplicates = []
    for item in tasks:
        if item["id"] in seen:
            duplicates.append(item["id"])
        seen.add(item["id"])
    return duplicates


def sync_task_sidecar(root: Path, slug: str, tasks: list[dict], updated_text: str):
    """Regenerate the tasks.json sidecar after a tasks.md mutation, if tasks.md exists."""
    path = feature_tasks_path(root, slug)
    if not path.is_file():
        return None
    duplicates = _duplicate_ids(tasks)
    rows = []
    for item in tasks:
        rows.append(
            {
                "id": item["id"],
                "header": item.get("header", ""),
                "status": item.get("status", "Not Started"),
                "done": item.get("done", False),
                "depends": list(item.get("depends", [])),
                "evidence": list(item.get("evidence", [])),
                "acceptance_criteria": list(item.get("acceptance_criteria", [])),
            }
        )
    sidecar = {
        "schema_version": 1,
        "source": "tasks.md",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "errors": ["duplicate task id: " + item for item in duplicates],
        "task_count": len(rows),
        "tasks": rows,
        "markdown_hash": hashlib.sha256(updated_text.encode("utf-8")).hexdigest(),
    }
    atomic_write(feature_tasks_sidecar_path(root, slug), json.dumps(sidecar, indent=2) + "\n")
    return feature_tasks_sidecar_path(root, slug)


def update_task_text(path: Path, task_id: str, status: str, evidence=None, note=None):
    """Update one task's state while preserving the rest of tasks.md."""
    if status not in TASK_STATUSES:
        raise ValueError(f"invalid task status: {status}")
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    matches = list(TASK_HEADER_RE.finditer(text))
    target = [match for match in matches if match.group(3) == task_id]
    if not target:
        raise ValueError(f"task not found: {task_id}")
    if len(target) > 1:
        raise ValueError(f"duplicate task ID: {task_id}")

    match = target[0]
    end = next((item.start() for item in matches if item.start() > match.start()), len(text))
    block = text[match.start():end]
    current = parse_tasks(block)
    current_status = normalize_status(current[0]["status"] if current else "Not Started")
    if status not in ALLOWED_TRANSITIONS.get(current_status, set()):
        raise ValueError(f"invalid task transition: {current_status} -> {status}")

    full_tasks = parse_tasks(text)
    by_id = {item["id"]: item for item in full_tasks}
    halt_files = (path.parent / "spec.md", path.parent / "plan.md", path)
    if status != current_status:
        halted = [str(item.name) for item in halt_files if item.exists() and "[:HALT" in item.read_text(encoding="utf-8", errors="replace")]
        if halted:
            raise ValueError(f"active [:HALT marker] blocks transition ({', '.join(halted)})")
    if status == "In Progress":
        blocked = [dep for dep in current[0].get("depends", []) if dep not in by_id or not by_id[dep]["done"]]
        if blocked:
            raise ValueError(f"task has unfinished dependencies: {', '.join(blocked)}")
    if status == "Done" and not EVIDENCE_RE.search(block):
        if not any(str(item).strip() for item in (evidence or [])):
            raise ValueError("task completion requires explicit validation evidence")

    checked = "x" if status.lower() in DONE_STATUSES else " "
    header = match.group(0)
    header = CHECKBOX_RE.sub(rf"\g<1>[{checked}]", header)
    block = header + block[match.end() - match.start():]
    if STATUS_LINE_RE.search(block):
        block = STATUS_LINE_RE.sub(rf"\g<1>{status}", block, count=1)
    else:
        newline = "\r\n" if "\r\n" in block else "\n"
        block = header + newline + f"  Status: {status}" + block[len(header):]

    additions = []
    additions.extend(f"  Validation evidence: {item.strip()}" for item in (evidence or []) if item.strip())
    if note and note.strip():
        additions.append(f"  Session note: {note.strip()}")
    if additions:
        block = block.rstrip() + "\n" + "\n".join(additions) + "\n\n"
    updated = text[:match.start()] + block + text[end:]
    return updated, {"id": task_id, "from": current_status, "to": status}
