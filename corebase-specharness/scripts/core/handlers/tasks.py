"""Task graph CLI command handlers."""

from core.context_state import atomic_write
from core._lib.ansi import status_icon, tree
from core.handlers.common import _read_file, _resolve_root, _result
from core.task_graph import (
    ALLOWED_TRANSITIONS,
    detect_cycle,
    feature_tasks_path,
    load_tasks,
    next_tasks,
    normalize_status,
    parse_tasks,
    sync_task_sidecar,
    update_task_text,
    validate_task_consistency,
)


def _task_data(root, feature):
    path = feature_tasks_path(root, feature)
    tasks = load_tasks(root, feature)
    if not path.is_file() and not tasks:
        raise ValueError(f"Tasks file not found: {path}")
    cycle = detect_cycle(tasks)
    errors = ["cycle: " + " -> ".join(cycle)] if cycle else []
    errors.extend(validate_task_consistency(tasks))
    known = {item["id"] for item in tasks}
    seen = set()
    for item in tasks:
        if item["id"] in seen:
            errors.append(f"duplicate task ID: {item['id']}")
        seen.add(item["id"])
    for item in tasks:
        for dependency in item["depends"]:
            if dependency not in known:
                errors.append(f"{item['id']} depends on missing {dependency}")
    return path, tasks, errors


def task_check(args):
    """Validate the task dependency graph and list next unblocked tasks."""
    root = _resolve_root(args)
    path, tasks, errors = _task_data(root, args.feature)
    ready = next_tasks(tasks) if not errors else []

    # Pretty ANSI tree when not JSON mode
    if not getattr(args, "json", False) and tasks:
        print()
        # Build tree nodes for display
        task_map = {t["id"]: t for t in tasks}
        roots = [t for t in tasks if not t.get("depends")]
        def build_node(task):
            node = {"label": f"{status_icon(task.get('status'))} {task['id']} - {task.get('header', '')}"}
            children = [build_node(task_map[d]) for d in task.get("depends", []) if d in task_map]
            if children:
                node["children"] = children
            return node
        tree_nodes = [build_node(t) for t in roots]
        if tree_nodes:
            print(tree(tree_nodes))
        print()
    return _result(
        args.command,
        "failed" if errors else "ok",
        args.feature,
        [str(path)],
        errors,
        details={"tasks": ready, "task_count": len(tasks)},
    )


def task_start(args):
    """Start an unblocked task."""
    return _task_update(args, "In Progress")


def task_done(args):
    """Mark a task done with proof evidence."""
    return _task_update(args, "Done")


def task_block(args):
    """Mark a task blocked with a reason."""
    return _task_update(args, "Blocked")


def _task_update(args, target):
    root = _resolve_root(args)
    path = feature_tasks_path(root, args.feature)
    evidence = list(getattr(args, "evidence", []))
    evidence_file = getattr(args, "evidence_file", "")
    if evidence_file:
        evidence.append(_read_file(evidence_file, "evidence file"))
    if target == "Done" and not any(item.strip() for item in evidence):
        raise ValueError("task completion requires explicit validation evidence")
    if target == "Blocked" and not args.note.strip():
        raise ValueError("task blocking requires --note with the blocker reason")
    path, tasks, errors = _task_data(root, args.feature)
    if errors:
        return _result(args.command, "failed", args.feature, [str(path)], errors)
    if not path.is_file():
        raise ValueError(f"Tasks file not found: {path}; tasks.json is read-only fallback")
    if not args.task:
        raise ValueError("--task is required")
    task = next((item for item in tasks if item["id"] == args.task), None)
    if not task:
        raise ValueError(f"task not found: {args.task}")
    current_status = normalize_status(task["status"])
    if target not in ALLOWED_TRANSITIONS.get(current_status, set()):
        raise ValueError(f"invalid task transition: {current_status} -> {target}")
    if target == "In Progress":
        by_id = {item["id"]: item for item in tasks}
        missing = [dep for dep in task["depends"] if dep not in by_id]
        blocked = [dep for dep in task["depends"] if dep in by_id and not by_id[dep]["done"]]
        if missing or blocked:
            raise ValueError(f"task has unfinished dependencies: {', '.join(missing or blocked)}")
    updated, change = update_task_text(path, args.task, target, evidence=evidence, note=args.note)
    next_ready = next_tasks(parse_tasks(updated))
    if not args.dry_run:
        atomic_write(path, updated)
        sync_task_sidecar(root, args.feature, parse_tasks(updated), updated)
    handoff_skill = "spec-tasks" if target == "Blocked" else "spec-implement"
    return _result(
        args.command,
        "ok",
        args.feature,
        [str(path)],
        next_action="python3 corebase-specharness/scripts/core/cli.py task-check --feature " + args.feature,
        details={
            "task": change,
            "next_task": next_ready[0] if next_ready else None,
            "dry_run": args.dry_run,
            "next_action": {
                "skill": handoff_skill,
                "intent": args.note or "Continue the next unblocked task",
                "task": next_ready[0]["id"] if next_ready else None,
            },
        },
    )
