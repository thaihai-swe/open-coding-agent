"""ADR generation helpers."""

import re
from pathlib import Path

from core.context_state import atomic_write, default_session_path, load_session
from core.handlers.common import _resolve_root, _result, _slugify




def get_next_adr_number(root):
    adr_dir = Path(root) / "core-zero/project/adr"
    max_num = 0
    if adr_dir.exists():
        for item in adr_dir.iterdir():
            if item.is_file() and item.suffix == ".md":
                m = re.match(r'^(\d+)', item.name)
                if m:
                    max_num = max(max_num, int(m.group(1)))
    return max_num + 1


def adr_generate(args):
    """Auto-generate an architecture decision record draft from session decisions."""
    root = _resolve_root(args)
    if not root:
        raise ValueError("Unable to locate an initialized CoreZero repository")
    feature = getattr(args, "feature", "") or ""

    decisions = list(args.decision) if args.decision else []
    if not decisions and feature:
        session_path = default_session_path(root, feature)
        if session_path and session_path.exists():
            session = load_session(session_path)
            if session:
                metadata = session.get("metadata", {})
                decisions = list(metadata.get("decisions") or [])

    if not decisions and not args.title:
        raise ValueError("No decisions found in session, and no --decision or --title provided.")

    title = args.title
    if not title:
        first_dec = decisions[0] if decisions else "architecture-decision"
        title = first_dec[:60] + "..." if len(first_dec) > 60 else first_dec

    title_slug = _slugify(title)
    next_num = get_next_adr_number(root)
    num_str = f"{next_num:04d}"

    adr_dir = Path(root) / "core-zero/project/adr"
    template_path = Path(root) / "skills/spec-adr/references/adr-template.md"
    if not template_path.exists():
        template_content = (
            "# ADR-[number]: [Title]\n\n"
            "Status: Proposed\n"
            "Date: [Date]\n"
            "Feature slug: [slug]\n"
            "Related spec: [link to spec.md]\n"
            "Related plan: [link to plan.md]\n"
            "Reversibility: Moderate\n\n"
            "## Context\n"
            "[Context summary]\n\n"
            "## Decision\n"
            "[Decision choice]\n"
        )
    else:
        template_content = template_path.read_text(encoding="utf-8")

    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = feature or "repo"
    spec_link = f"../../../artifacts/features/{feature}/spec.md" if feature else "[none]"
    plan_link = f"../../../artifacts/features/{feature}/plan.md" if feature else "[none]"

    content = template_content
    content = content.replace("[number]", num_str)
    content = content.replace("[Title]", title)
    content = content.replace("[Date]", date_str)
    content = content.replace("[slug]", slug)
    content = content.replace("[link to spec.md]", spec_link)
    content = content.replace("[link to plan.md]", plan_link)
    reversibility = getattr(args, "reversibility", None) or "Moderate"
    if reversibility not in {"Easy", "Moderate", "Hard"}:
        raise ValueError("reversibility must be Easy, Moderate, or Hard")
    content = content.replace("`Easy | Moderate | Hard`", reversibility)
    content = content.replace("Reversibility: Moderate", f"Reversibility: {reversibility}")

    if decisions:
        content += "\n\n## Session Decisions Reference\n"
        for dec in decisions:
            content += f"- {dec}\n"

    new_adr_path = adr_dir / f"{num_str}-{title_slug}.md"
    relative_adr_path = f"core-zero/project/adr/{num_str}-{title_slug}.md"

    log_entry = (
        f"### ADR-{num_str} — {title}\n\n"
        f"- Date: {date_str}\n"
        f"- Feature slug: {slug}\n"
        f"- Artifact: {relative_adr_path}\n"
        f"- Status: Proposed\n"
        f"- Reversibility: {reversibility}\n"
        f"- Superseded by: none\n"
        f"- One-line summary: {decisions[0] if decisions else 'Proposed architecture decision.'}\n"
    )

    index_row = (
        f"| [ADR-{num_str}]({num_str}-{title_slug}.md) | {title} | Proposed | "
        f"{date_str} | {slug} | {reversibility} |"
    )

    payload = {
        "command": "adr-generate",
        "feature": feature,
        "number": next_num,
        "title": title,
        "path": str(new_adr_path),
        "relative_path": relative_adr_path,
        "log_entry": log_entry,
        "index_row": index_row,
        "dry_run": getattr(args, "dry_run", False)
    }

    if not getattr(args, "dry_run", False):
        new_adr_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(new_adr_path, content)

        adr_log_path = Path(root) / "core-zero/memories/repo/adr-log.md"
        if adr_log_path.exists():
            log_content = adr_log_path.read_text(encoding="utf-8")
            markers = (
                "<!-- Append new entries below in sequential ADR-NNN order. -->",
                "<!-- Append new entries below in ADR-003, ADR-004, ... order. -->",
                "<!-- Append new entries below. Most recent first. -->",
            )
            updated_log = None
            for marker in markers:
                if marker in log_content:
                    parts = log_content.split(marker, 1)
                    updated_log = parts[0] + marker + "\n\n" + log_entry.strip() + "\n" + parts[1]
                    break
            if updated_log is None:
                updated_log = log_content.rstrip() + "\n\n" + log_entry
            atomic_write(adr_log_path, updated_log)

        adr_index_path = Path(root) / "core-zero/project/adr/index.md"
        if adr_index_path.exists():
            index_content = adr_index_path.read_text(encoding="utf-8")
            marker = "<!-- Append new entries below. Most recent first. -->"
            if marker in index_content:
                parts = index_content.split(marker, 1)
                updated_index = parts[0] + marker + "\n" + index_row + "\n" + parts[1]
            else:
                updated_index = index_content.rstrip() + "\n" + index_row + "\n"
            atomic_write(adr_index_path, updated_index)

    if not getattr(args, "json", False):
        action_word = "DRAFTED (Dry-Run)" if getattr(args, "dry_run", False) else "GENERATED"
        print(f"ADR {action_word}: {relative_adr_path}")
        print(f"Title: {title}")
        print("\nSuggested log entry to append:")
        print(log_entry.strip())
        print("\nSuggested index row to append:")
        print(index_row)

    return _result("adr-generate", feature=feature,
                   artifacts=[] if getattr(args, "dry_run", False) else [relative_adr_path],
                   details=payload)
