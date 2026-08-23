#!/usr/bin/env python3
"""Compile bounded, inspectable context packs for one explicit named skill."""

from __future__ import annotations

import hashlib
import json
import re
from fnmatch import fnmatch
from pathlib import Path

from core._lib.artifacts import canonical_feature_dir
from core._lib.routing_metadata import (
    clean_section_name,
    feature_artifacts_for,
    path_for_source,
    route_rows,
    skill_route,
)
from core._lib.token_counter import estimate_tokens, tokenizer_mode
from core._lib.yaml_reader import load as load_yaml
from core.context_state import default_session_dir

DEFAULT_TIER_BOOST = {"Must": 40, "Should": 20, "Skip": 0}
DEFAULT_RETRIEVAL_EXCLUDES = {
    ".git", ".corebase-specharness", ".venv", "node_modules", "vendor", "dist", "build",
    "coverage", "__pycache__", "corebase-specharness", "skills", "references", "artifacts",
}
SENSITIVE_FILENAMES = {".env", ".env.local", ".env.production", "id_rsa", "id_ed25519"}
DEFAULT_SUFFIX_PRIORITY = {
    ".md": 50, ".rst": 45, ".txt": 40, ".py": 35, ".ts": 35, ".tsx": 35,
    ".js": 35, ".jsx": 35, ".go": 35, ".rs": 35, ".java": 35, ".kt": 35,
    ".c": 35, ".h": 35, ".cpp": 35, ".hpp": 35, ".rb": 35, ".sh": 35,
    ".yaml": 30, ".yml": 30, ".json": 30, ".toml": 30, ".ini": 25, ".cfg": 25,
}
SECRET_PATTERNS = (
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password|passwd|client[_-]?secret)\b(\s*[:=]\s*)[\"']?[^\s\"']{8,}"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"\bgh[opusr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
)


H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)

class Scorer:
    """Small keyword scorer used only inside the current repository."""

    def __init__(self, intent=""):
        self.words = frozenset(re.findall(r"[a-z0-9_-]+", (intent or "").lower()))
        self._word_pattern = (
            re.compile(
                r"\b(?:" + "|".join(
                    re.escape(word) for word in sorted(self.words, key=lambda item: (-len(item), item))
                ) + r")\b"
            )
            if self.words else None
        )

    def score_text(self, text, base_score=0):
        if self._word_pattern is None:
            return base_score
        matches = len(set(self._word_pattern.findall(text.lower())))
        return min(base_score + matches * 10, 100)


def extract_section(text, title):
    """Return one H2 section, including its child content."""
    target = (clean_section_name(title) or "").lower()
    lines = text.splitlines()
    result = []
    capturing = False
    for line in lines:
        if line.startswith("## "):
            current = line[3:].strip()
            if capturing:
                break
            if current.lower() == target:
                capturing = True
                result.append(line)
            continue
        if capturing:
            result.append(line)
    return "\n".join(result) if result else None


def select_relevant_sections(text, intent, limit=2):
    """Select matching H2 sections without searching outside the declared file."""
    scorer = Scorer(intent)
    if not scorer.words:
        return []
    candidates = []
    for heading in H2_RE.findall(text):
        section = extract_section(text, heading) or ""
        score = scorer.score_text(section)
        if score:
            candidates.append((score, len(section), heading))
    candidates.sort(key=lambda item: (-item[0], item[1], item[2].lower()))
    return [heading for _score, _size, heading in candidates[:limit]]


def _content_fingerprint(root, item):
    if item.get("runtime_summary") is not None:
        return hashlib.sha256(item["runtime_summary"].encode("utf-8")).hexdigest()
    path = Path(root) / item.get("content_path", item.get("path", ""))
    if not path.is_file():
        return ""
    raw = path.read_bytes()
    sections = item.get("sections") or []
    if sections:
        text = raw.decode("utf-8", errors="replace")
        raw = "\n\n".join(extract_section(text, name) or "" for name in sections).encode()
    return hashlib.sha256(raw).hexdigest()


def _slice_fingerprints(root, item):
    """Return {section_or_empty: hash} for one selected source."""
    sections = item.get("sections") or []
    fingerprint = item.get("fingerprint") or _content_fingerprint(root, item)
    if not sections:
        return {"": fingerprint}
    return {
        name: _content_fingerprint(root, {**item, "sections": [name]})
        for name in sections
    }


def _index_previous_pack(previous):
    """Build path fingerprint and per-section slice maps from a prior pack or session cache."""
    fingerprints = {}
    slices = {}
    if not isinstance(previous, dict):
        return fingerprints, slices
    for item in previous.get("selected") or []:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if not path:
            continue
        if item.get("fingerprint"):
            fingerprints[path] = item["fingerprint"]
        item_slices = item.get("slices")
        if isinstance(item_slices, dict) and item_slices:
            slices[path] = dict(item_slices)
    raw_fp = previous.get("fingerprints")
    if isinstance(raw_fp, dict):
        for path, fingerprint in raw_fp.items():
            if path and isinstance(fingerprint, str):
                fingerprints.setdefault(path, fingerprint)
    raw_slices = previous.get("slices")
    if isinstance(raw_slices, dict):
        for path, smap in raw_slices.items():
            if path and isinstance(smap, dict):
                slices[path] = {**slices.get(path, {}), **smap}
    return fingerprints, slices


def _full_file_fingerprint(root, item):
    if item.get("runtime_summary") is not None:
        return item.get("fingerprint") or _content_fingerprint(root, item)
    return _content_fingerprint(root, {**item, "sections": None})


def _delta_selected_item(root, item, previous_fingerprints, previous_slices):
    """Return a possibly section-trimmed item, or None when already loaded unchanged."""
    path = item["path"]
    old_fingerprint = previous_fingerprints.get(path)
    old_slices = previous_slices.get(path) or {}
    if old_fingerprint and old_fingerprint == item.get("fingerprint"):
        return None
    sections = list(item.get("sections") or [])
    if not sections:
        if old_slices.get("") == item.get("fingerprint"):
            return None
        updated = dict(item)
        updated["delta_reason"] = "new" if not old_fingerprint and not old_slices else "changed"
        return updated
    if "" in old_slices and old_slices.get("") == _full_file_fingerprint(root, item):
        return None
    current_slices = _slice_fingerprints(root, item)
    kept = [name for name in sections if old_slices.get(name) != current_slices.get(name)]
    if not kept:
        return None
    updated = dict(item)
    if kept != sections:
        updated["sections"] = kept
        if updated.get("runtime_summary") is None:
            source = Path(root) / updated.get("content_path", path)
            text = source.read_text(encoding="utf-8", errors="replace") if source.is_file() else ""
            updated["content"] = "\n\n".join(
                extract_section(text, name) or "" for name in kept
            )
        updated["tokens"] = estimate_tokens(updated.get("content") or "")
        updated["fingerprint"] = _content_fingerprint(root, updated)
        updated["delta_reason"] = "changed"
        return updated
    updated["delta_reason"] = "new" if not old_fingerprint and not old_slices else "changed"
    return updated


def _load_delta_baseline(delta_from):
    """Return (fingerprints, slices, label) for a session cache or --delta-from JSON."""
    if not delta_from:
        return {}, {}, None
    if isinstance(delta_from, dict):
        previous = delta_from
        label = "session"
    else:
        previous = json.loads(Path(delta_from).read_text(encoding="utf-8"))
        label = str(delta_from)
    fingerprints, slices = _index_previous_pack(previous)
    if not fingerprints and not slices:
        return {}, {}, None
    return fingerprints, slices, label


def _merge_context_entry(entries, path, tier, sections, reason, channel="project", **extra):
    key = str(Path(path).resolve())
    current = entries.get(key)
    if current:
        current["tier"] = "Must" if "Must" in (current["tier"], tier) else tier
        if current.get("sections") is None or sections is None:
            current["sections"] = None
        else:
            current["sections"] = list(dict.fromkeys(current["sections"] + sections)) or None
        current["reason"] = f"{current['reason']}; {reason}"
        current["channels"] = list(dict.fromkeys(current["channels"] + [channel]))
        current.update({key: value for key, value in extra.items() if value is not None})
        return
    entries[key] = {
        "path": Path(path),
        "tier": tier,
        "sections": sections or None,
        "reason": reason,
        "channels": [channel],
        **{key: value for key, value in extra.items() if value is not None},
    }


def _context_settings(root):
    config = load_yaml(str(Path(root) / "corebase-specharness/project/harness-config.yaml")) or {}
    return config.get("context") or {}


def _context_budget(root, profile, budget):
    context = _context_settings(root)
    profiles = context.get("profiles") or {}
    profile_config = profiles.get(profile) or {}
    configured = profile_config.get("payload") or context.get("payload_budget", 2500)
    ceiling = int(context.get("max_injected_tokens", configured))
    reserve = int(context.get("reserve_tokens", 0) or 0)
    if reserve:
        ceiling = max(ceiling - reserve, 1)
    selected = budget or configured
    return min(int(selected), ceiling)


def _channel_limits(root):
    context = _context_settings(root)
    feature_limit = int(context.get("max_feature_tokens", 1600))
    project_limit = int(context.get("max_project_tokens", 1200))
    return {
        "bootstrap": int(context.get("max_bootstrap_tokens", 800)),
        "project": project_limit,
        "feature": feature_limit,
        "task": feature_limit,
        "retrieved": int(context.get("max_retrieved_tokens", 1000)),
        "durable_memory": project_limit,
        "explicit": project_limit,
    }


def _feature_path(root, feature, kind, name):
    if kind == "session":
        return default_session_dir(root, feature) / name
    return canonical_feature_dir(root, feature) / name


def _last_h2_section(text, titles):
    """Return the last H2 section whose title matches one of titles."""
    wanted = {str(title).strip().lower() for title in titles if str(title).strip()}
    if not text or not wanted:
        return None
    lines = text.splitlines()
    headings = [
        (index, line[3:].strip())
        for index, line in enumerate(lines)
        if line.startswith("## ")
    ]
    last = None
    for index, (start, title) in enumerate(headings):
        if title.lower() in wanted:
            end = headings[index + 1][0] if index + 1 < len(headings) else len(lines)
            last = "\n".join(lines[start:end]).strip()
    return last or None


def _session_context_payload(path):
    """Return Objective plus the latest progress, handoff, and recent decisions."""
    if not path or not Path(path).is_file():
        return None
    from core.context_state import load_session
    session = load_session(path)
    if not session:
        return None
    body = session.get("body") or ""
    metadata = session.get("metadata") or {}
    parts = []
    objective = extract_section(body, "Objective")
    if objective and objective.strip():
        parts.append(objective.strip())
    progress = _last_h2_section(body, ("Progress Update", "Progress"))
    if progress:
        parts.append(progress)
    handoff = _last_h2_section(body, ("Handoff Update", "Handoff"))
    if handoff:
        parts.append(handoff)
    decisions = [item for item in (metadata.get("decisions") or []) if str(item).strip()]
    if decisions:
        recent = [str(item).strip() for item in decisions[-5:]]
        parts.append("## Decisions\n\n" + "\n".join(f"- {item}" for item in recent))
    return "\n\n".join(parts).strip() or "# Session\n"


def _task_context_payload(path, task_id):
    """Return a compact task-context payload containing active task, direct dependencies, and progress summary."""
    if not task_id or not path.is_file():
        return None
    from core.task_graph import parse_tasks
    text = path.read_text(encoding="utf-8", errors="replace")
    tasks = parse_tasks(text)
    by_id = {t["id"]: t for t in tasks}
    active = by_id.get(task_id)
    if not active:
        return _task_excerpt(path, task_id)
    done_count = sum(1 for t in tasks if t["done"])
    total_count = len(tasks)
    lines = [
        f"# Task Scope: {task_id}",
        f"Overall Progress: {done_count}/{total_count} tasks completed",
        "",
        "## Active Task",
        active["header"],
    ]
    if active.get("status"):
        lines.append(f"  - Status: {active['status']}")
    if active.get("depends"):
        lines.append(f"  - Depends on: {', '.join(active['depends'])}")
    if active.get("acceptance_criteria"):
        lines.append(f"  - Covers: {', '.join(active['acceptance_criteria'])}")
    if active.get("evidence"):
        lines.append(f"  - Proof: {'; '.join(active['evidence'])}")

    if active.get("depends"):
        lines.extend(["", "## Direct Dependencies"])
        for dep_id in active["depends"]:
            dep = by_id.get(dep_id)
            if dep:
                status_label = dep.get("status", "Done" if dep["done"] else "Not Started")
                lines.append(f"- {dep_id}: {dep['header']} (Status: {status_label})")
    return "\n".join(lines).strip()


def _task_excerpt(path, task_id):
    if not task_id or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = list(re.finditer(
        rf"(?m)^\s*[-*]\s+\[[ xX]\]\s+{re.escape(task_id)}\b.*$",
        text,
    ))
    if not matches:
        return None
    start = matches[0].start()
    next_match = re.search(r"(?m)^\s*[-*]\s+\[[ xX]\]\s+T-\d{3}\b", text[matches[0].end():])
    end = matches[0].end() + next_match.start() if next_match else len(text)
    return text[start:end].strip()


def _validate_added_source(root, raw_path, excluded, pinnable_sources=()):
    candidate = Path(raw_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"--add-source must be a repository-relative path: {raw_path}")
    path = (Path(root) / candidate).resolve()
    root_path = Path(root).resolve()
    if root_path not in path.parents and path != root_path:
        raise ValueError(f"--add-source is outside the repository: {raw_path}")
    relative = path.relative_to(root_path).as_posix()
    if any(part in excluded for part in Path(relative).parts) or path.name in SENSITIVE_FILENAMES:
        raise ValueError(f"--add-source is excluded by context policy: {raw_path}")
    if pinnable_sources and not any(fnmatch(relative, pattern) for pattern in pinnable_sources):
        raise ValueError(f"--add-source is not permitted by retrieval.pinnable_sources: {raw_path}")
    if not path.is_file():
        raise ValueError(f"--add-source does not name a readable file: {raw_path}")
    return path


def _glossary_triggers(glossary):
    try:
        text = glossary.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    frontmatter = text.split("---", 2)[1] if text.startswith("---") and text.count("---") >= 2 else ""
    match = re.search(r"(?m)^triggers:\s*\[([^]]*)\]", frontmatter)
    return {
        value.strip().strip("\"'").lower()
        for value in (match.group(1).split(",") if match else [])
        if value.strip()
    }


def _domain_packs(root, intent, settings):
    base = root / "corebase-specharness/memories/domain"
    words = Scorer(intent).words
    if not base.is_dir() or not words:
        return []
    packs = []
    for directory in sorted(base.iterdir()):
        if not directory.is_dir() or directory.is_symlink():
            continue
        try:
            directory.resolve().relative_to(base.resolve())
        except ValueError:
            continue
        glossary = directory / "glossary.md"
        if not glossary.is_file() or glossary.is_symlink():
            continue
        score = len(words & _glossary_triggers(glossary))
        if score:
            packs.append((score, directory.name, directory))
    flat_glossary = base / "glossary.md"
    if (not packs) and flat_glossary.is_file() and not flat_glossary.is_symlink():
        score = len(words & _glossary_triggers(flat_glossary))
        if score:
            packs.append((score, "domain", base))
    packs.sort(key=lambda item: (-item[0], item[1].lower()))
    return packs[:settings["max_domain_packs"]]


def _pinnable_paths(root, settings):
    root_path = Path(root).resolve()
    pinned = set()
    for pattern in settings.get("pinnable_sources", []):
        for path in root_path.glob(pattern):
            if not path.is_file() or path.is_symlink():
                continue
            try:
                resolved = path.resolve()
                resolved.relative_to(root_path)
            except (OSError, ValueError):
                continue
            pinned.add(resolved)
    return pinned


def _retrieval_settings(root, profile=""):
    context = _context_settings(root)
    retrieval = context.get("retrieval") or {}
    roots = retrieval.get("roots") or ["."]
    excluded = set(DEFAULT_RETRIEVAL_EXCLUDES)
    excluded.update(str(value) for value in (retrieval.get("exclude") or []))
    gitignore = root / ".gitignore"
    patterns = []
    if gitignore.is_file():
        patterns = [
            line.strip().lstrip("/")
            for line in gitignore.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.strip() and not line.lstrip().startswith("#") and not line.lstrip().startswith("!")
        ]
    profile_config = (context.get("profiles") or {}).get(profile) or {}
    if "retrieval_files" in profile_config:
        max_files = int(profile_config.get("retrieval_files") or 0)
    else:
        max_files = int(context.get("max_retrieval_files", 4))
    return {
        "roots": [str(value) for value in roots],
        "excluded": excluded,
        "max_files": max_files,
        "max_excerpt_tokens": min(
            int(context.get("max_source_excerpt_tokens", 400)),
            int(context.get("max_tool_output_tokens", context.get("max_source_excerpt_tokens", 400))),
        ),
        "max_total_tokens": int(context.get("max_retrieved_tokens", 1000)),
        "gitignore_patterns": patterns,
        "suffix_allowlist": {str(value).lower() for value in (retrieval.get("suffix_allowlist") or [])},
        "suffix_priority": retrieval.get("suffix_priority") or {},
        "pinnable_sources": [str(value) for value in (retrieval.get("pinnable_sources") or [])],
        "max_domain_packs": int(retrieval.get("max_domain_packs", 3)),
        "max_domain_files": int(retrieval.get("max_domain_files", 5)),
    }


def _is_ignored(relative, patterns):
    value = relative.as_posix()
    for raw in patterns:
        pattern = raw.rstrip("/")
        if not pattern:
            continue
        if raw.endswith("/") and (value == pattern or value.startswith(pattern + "/")):
            return True
        if fnmatch(value, pattern) or fnmatch(relative.name, pattern):
            return True
    return False


def _is_retrievable_file(root, path, excluded, gitignore_patterns, pinned=(), suffix_allowlist=()):
    try:
        relative = path.relative_to(root)
        resolved_path = path.resolve()
        resolved_path.relative_to(Path(root).resolve())
    except (OSError, ValueError):
        return False
    if resolved_path in pinned:
        return _is_plain_text_file(path, resolved_path)
    if (
        any(part in excluded for part in relative.parts)
        or path.name in SENSITIVE_FILENAMES
        or path.name.startswith(".env")
        or _is_ignored(relative, gitignore_patterns)
    ):
        return False
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".lock"}:
        return False
    if suffix_allowlist and str(path.suffix).lower() not in suffix_allowlist:
        return False
    return _is_plain_text_file(path, resolved_path)


def _is_plain_text_file(path, resolved_path):
    try:
        if resolved_path.stat().st_size > 256 * 1024:
            return False
        return b"\0" not in resolved_path.read_bytes()[:4096]
    except OSError:
        return False


def redact_secrets(text):
    """Redact detected secrets from arbitrary context text."""
    result = SECRET_PATTERNS[0].sub(r"\1\2[REDACTED]", text)
    for pattern in SECRET_PATTERNS[1:]:
        result = pattern.sub("[REDACTED]", result)
    return result


def _suffix_priority(path, configured):
    if not configured:
        return DEFAULT_SUFFIX_PRIORITY.get(str(Path(path).suffix).lower(), 0)
    priority = dict(DEFAULT_SUFFIX_PRIORITY)
    for suffix, boost in configured.items():
        priority[str(suffix).lower()] = int(boost)
    return priority.get(str(Path(path).suffix).lower(), 0)


def _excerpt_for_matches(text, scorer, max_tokens):
    lines = text.splitlines()
    matching = [
        index for index, line in enumerate(lines)
        if scorer._word_pattern.search(line.lower())
    ]
    if not matching:
        return ""
    collected, covered = [], set()
    for index in matching[:3]:
        for line_index in range(max(0, index - 2), min(len(lines), index + 5)):
            if line_index not in covered:
                covered.add(line_index)
                collected.append(lines[line_index])
        excerpt = "\n".join(collected).strip()
        if estimate_tokens(excerpt) >= max_tokens:
            break
    excerpt = "\n".join(collected).strip()
    while excerpt and estimate_tokens(excerpt) > max_tokens:
        excerpt = "\n".join(excerpt.splitlines()[:-1]).strip()
    return excerpt


def _retrieve_local_evidence(root, intent, feature, task, entries, settings):
    if int(settings.get("max_files") or 0) <= 0 or int(settings.get("max_total_tokens") or 0) <= 0:
        return []
    root = Path(root).resolve()
    query = " ".join(part for part in (intent, feature, task) if part)
    scorer = Scorer(query)
    if not scorer.words:
        return []
    known = {str(item["path"].resolve()) for item in entries.values()}
    pinned = _pinnable_paths(root, settings)
    candidates = []
    scanned = set()
    for raw_root in settings["roots"]:
        candidate_root = (root / raw_root).resolve()
        if root not in candidate_root.parents and candidate_root != root:
            continue
        if not candidate_root.is_dir():
            continue
        for path in candidate_root.rglob("*"):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if str(resolved) in known or resolved in scanned:
                continue
            scanned.add(resolved)
            if not _is_retrievable_file(
                root, path, settings["excluded"], settings["gitignore_patterns"],
                pinned, settings["suffix_allowlist"],
            ):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            base_score = scorer.score_text(text)
            if not base_score:
                continue
            excerpt = redact_secrets(
                _excerpt_for_matches(text, scorer, settings["max_excerpt_tokens"])
            )
            if excerpt:
                ranked_score = base_score + _suffix_priority(path, settings["suffix_priority"])
                candidates.append((ranked_score, base_score, estimate_tokens(excerpt), path, excerpt))
    candidates.sort(key=lambda value: (-value[0], value[2], str(value[3]).lower()))
    selected, total = [], 0
    for ranked_score, base_score, tokens, path, excerpt in candidates:
        if len(selected) >= settings["max_files"] or total + tokens > settings["max_total_tokens"]:
            continue
        selected.append({
            "path": str(path.relative_to(root)),
            "content_path": str(path.relative_to(root)),
            "tier": "Should",
            "reason": "automatic local retrieval matched active intent",
            "channels": ["retrieved"],
            "tokens": tokens,
            "partial": True,
            "provenance": "automatic_local_retrieval",
            "trust": "repository_evidence",
            "confidence": round(base_score / 100, 3),
            "runtime_summary": excerpt,
            "suffix": str(path.suffix).lower() or None,
        })
        total += tokens
    return selected


def _channel_for_path(path, root):
    relative = str(Path(path).resolve().relative_to(Path(root).resolve()))
    if relative.startswith("artifacts/") or relative.startswith(".corebase-specharness/"):
        return "feature"
    if relative.startswith("corebase-specharness/memories/"):
        return "durable_memory"
    if relative.startswith("corebase-specharness/rules/"):
        return "bootstrap"
    return "project"


def build_context_pack(
    root,
    intent="",
    feature="",
    task="",
    budget=0,
    skill="",
    profile="",
    delta_from=None,
    payload_budget=None,
    add_sources=None,
):
    """Build an inspectable bounded pack for the requested named skill route."""
    root = Path(root).resolve()
    skill_name = (skill or "").strip().lower()
    if not skill_name:
        raise ValueError("--skill is required for context loading")
    route = skill_route(root, skill_name)
    if not route:
        raise ValueError(f"Unknown skill route: {skill_name}")
    if route.get("feature") == "required" and not feature:
        raise ValueError(f"--feature is required for skill {skill_name}")
    if feature:
        feature_root = canonical_feature_dir(root, feature)
        missing = [
            name for name in route.get("prerequisites", [])
            if not (feature_root / name).is_file()
        ]
        if missing:
            raise ValueError(
                f"skill {skill_name} prerequisites are missing: {', '.join(missing)}"
            )

    profile_name = (profile or route.get("profile") or "").strip().lower()
    configured_payload = _context_budget(root, profile_name, budget)
    payload_budget = min(
        int(payload_budget if payload_budget is not None else configured_payload),
        configured_payload,
    )
    retrieval = _retrieval_settings(root, profile_name)
    channel_limits = _channel_limits(root)

    entries = {}
    policy_sections = ["Purpose", "Normative Rules"]
    if skill_name in {"spec-implement", "harness-verify"}:
        policy_sections = ["Purpose", "Normative Rules", "Security Policy"]
    elif skill_name == "context-memory":
        policy_sections = ["Purpose", "Normative Rules", "Memory Promotion Thresholds", "Security Policy"]
    always = [
        ("corebase-specharness/rules/caveman.md", "Must", None, "communication rule"),
        ("corebase-specharness/memories/repo/core-policies.md", "Must", policy_sections, "runtime policy"),
    ]
    for relative, tier, sections, reason in always:
        _merge_context_entry(entries, root / relative, tier, sections, reason, "bootstrap")

    for path, tier, sections in route_rows(root, skill=skill_name):
        relative = path_for_source(path)
        if not relative:
            continue
        target = root / relative
        if "*" in relative:
            for match in sorted(root.glob(relative)):
                _merge_context_entry(
                    entries, match, tier, sections, f"{skill_name} skill route",
                    _channel_for_path(match, root),
                )
        else:
            _merge_context_entry(
                entries, target, tier, sections, f"{skill_name} skill route",
                _channel_for_path(target, root),
            )

    if feature:
        feature_root = canonical_feature_dir(root, feature)
        for artifact in feature_artifacts_for(root, skill_name):
            if isinstance(artifact, str):
                kind, name = "artifacts", artifact
            elif isinstance(artifact, dict):
                kind, name = artifact.get("kind", "artifacts"), artifact.get("name", "")
            else:
                raise ValueError(f"invalid feature artifact route for {skill_name}")
            if kind == "session" or name:
                if task and name == "tasks.md":
                    continue
                target = _feature_path(root, feature, kind, name)
                if kind == "session" and name == "session.md":
                    summary = _session_context_payload(target)
                    if summary:
                        _merge_context_entry(
                            entries, target, "Must", None, f"{skill_name} session summary",
                            "feature", runtime_summary=summary,
                        )
                        continue
                    if not target.exists():
                        _merge_context_entry(
                            entries, target, "Should", None, f"{skill_name} feature artifact",
                            "feature",
                        )
                        continue
                if target.exists():
                    _merge_context_entry(
                        entries, target, "Must", None, f"{skill_name} feature artifact",
                        "feature",
                    )
                else:
                    _merge_context_entry(
                        entries, target, "Should", None, f"{skill_name} feature artifact",
                        "feature",
                    )
        if skill_name != "starter-init":
            _merge_context_entry(
                entries, feature_root / "status.md", "Must", None, "active feature status", "feature",
            )
        if task:
            task_payload = _task_context_payload(feature_root / "tasks.md", task)
            if task_payload:
                _merge_context_entry(
                    entries, feature_root / "tasks.md", "Must", None, f"active task {task}",
                    "task", runtime_summary=task_payload,
                )

    for raw_path in add_sources or []:
        target = _validate_added_source(
            root, raw_path, retrieval["excluded"], retrieval["pinnable_sources"],
        )
        _merge_context_entry(
            entries, target, "Must", None, "explicit source expansion", "explicit",
        )

    for _score, name, directory in _domain_packs(root, intent, retrieval):
        for filename in ("glossary.md", "patterns.md", "anti-patterns.md", "boundaries.md", "spec.md")[:retrieval["max_domain_files"]]:
            target = directory / filename
            if target.is_file() and not target.is_symlink():
                _merge_context_entry(
                    entries, target, "Should", None,
                    f"intent matched domain pack {name}", "durable_memory",
                    provenance="intent_domain_pack", trust="adopter_memory",
                )

    scorer = Scorer(intent)
    candidates = []
    always_paths = {str((root / relative).resolve()) for relative, *_ in always}
    for item in entries.values():
        path = item["path"]
        if not path.is_file():
            candidates.append({
                "item": item,
                "tokens": 0,
                "score": DEFAULT_TIER_BOOST.get(item["tier"], 0),
                "sections": item["sections"] or [],
                "partial": False,
                "content": "",
            })
            continue
        text = item.get("runtime_summary") or path.read_text(encoding="utf-8", errors="replace")
        sections = list(item["sections"] or [])
        is_always = str(path.resolve()) in always_paths
        if not is_always and intent and not sections and not item.get("runtime_summary"):
            sections = select_relevant_sections(text, intent)
        selected_text = (
            "\n\n".join(extract_section(text, section) or "" for section in sections)
            if sections else text
        )
        candidates.append({
            "item": item,
            "tokens": estimate_tokens(selected_text),
            "score": scorer.score_text(selected_text, DEFAULT_TIER_BOOST.get(item["tier"], 0)),
            "sections": sections,
            "partial": bool(intent and sections and not item["sections"]),
            "content": selected_text,
        })

    for retrieved in _retrieve_local_evidence(root, intent, feature, task, entries, retrieval):
        candidates.append({
            "item": {
                "path": root / retrieved["path"],
                "tier": retrieved["tier"],
                "sections": None,
                "reason": retrieved["reason"],
                "channels": retrieved["channels"],
                "runtime_summary": retrieved["runtime_summary"],
                "provenance": retrieved["provenance"],
                "trust": retrieved["trust"],
                "confidence": retrieved["confidence"],
                "suffix": retrieved.get("suffix"),
            },
            "tokens": retrieved["tokens"],
            "score": int(retrieved["confidence"] * 100),
            "sections": [],
            "partial": True,
            "content": retrieved["runtime_summary"],
        })

    tier_priority = {"Must": 2, "Should": 1, "Skip": 0}
    candidates.sort(key=lambda value: (
        str(value["item"]["path"].resolve()) not in always_paths,
        -tier_priority.get(value["item"]["tier"], 0),
        -value["score"],
        value["tokens"],
        str(value["item"]["path"]).lower(),
    ))
    warnings = []
    previous_fingerprints, previous_slices, delta_label = {}, {}, None
    if delta_from:
        try:
            previous_fingerprints, previous_slices, delta_label = _load_delta_baseline(delta_from)
        except (OSError, ValueError, TypeError) as exc:
            warnings.append(f"delta ignored: {exc}")
    delta_active = bool(delta_label)

    selected, omitted, covered, delta_omitted, total, channel_totals = [], [], [], [], 0, {}
    for candidate in candidates:
        item = candidate["item"]
        path = item["path"]
        relative = str(path.relative_to(root))
        if not path.is_file():
            if item["tier"] == "Must":
                raise ValueError(f"required context source is missing: {relative}")
            omitted.append({
                "path": relative,
                "reason": item.get("reason", "missing"),
                "provenance": item.get("provenance", "route"),
            })
            continue
        selected_item = {
            "path": relative,
            "content_path": relative,
            "sections": candidate["sections"] or None,
            "tier": item["tier"],
            "reason": item["reason"],
            "channels": item["channels"],
            "tokens": candidate["tokens"],
            "partial": candidate["partial"],
            "provenance": item.get("provenance", "declared_route"),
            "trust": item.get("trust", "trusted_kit" if relative.startswith("corebase-specharness/") else "repository_evidence"),
            "confidence": item.get("confidence", round(candidate["score"] / 100, 3)),
        }
        if item.get("suffix") is not None:
            selected_item["suffix"] = item["suffix"]
        if item.get("runtime_summary") is not None:
            selected_item["runtime_summary"] = item["runtime_summary"]
        selected_item["content"] = candidate.get("content") or ""
        selected_item["fingerprint"] = _content_fingerprint(root, selected_item)
        injected = selected_item
        if delta_active:
            updated = _delta_selected_item(
                root, selected_item, previous_fingerprints, previous_slices,
            )
            if updated is None:
                delta_omitted.append({
                    "path": relative,
                    "reason": "unchanged since prior session load",
                    "tokens": selected_item.get("tokens", 0),
                    "provenance": "session_delta",
                })
                covered.append(selected_item)
                continue
            injected = updated
        tokens = injected["tokens"]
        if item["tier"] != "Must" and payload_budget and total + tokens > payload_budget:
            omitted.append({
                "path": relative, "reason": "budget exceeded", "tokens": tokens,
                "provenance": item.get("provenance", "capacity_limit"),
            })
            continue
        exceeded_channels = [
            channel for channel in item["channels"]
            if channel in channel_limits
            and channel_totals.get(channel, 0) + tokens > channel_limits[channel]
        ]
        if item["tier"] != "Must" and exceeded_channels:
            omitted.append({
                "path": relative,
                "reason": "channel budget exceeded: " + ", ".join(exceeded_channels),
                "tokens": tokens,
                "provenance": item.get("provenance", "capacity_limit"),
            })
            continue
        selected.append(injected)
        covered.append(selected_item)
        total += tokens
        for channel in item["channels"]:
            channel_totals[channel] = channel_totals.get(channel, 0) + tokens

    if payload_budget and total > payload_budget:
        warnings.append(
            f"mandatory context exceeds payload budget by {total - payload_budget} tokens; "
            "all Must sources were retained"
        )
    for channel, limit in channel_limits.items():
        if channel_totals.get(channel, 0) > limit:
            warnings.append(
                f"mandatory {channel} context exceeds its budget by "
                f"{channel_totals[channel] - limit} tokens; all Must sources were retained"
            )
    return {
        "selected": selected,
        "omitted": omitted,
        "estimated_tokens": total,
        "budget": payload_budget or None,
        "reserve_tokens": int(_context_settings(root).get("reserve_tokens", 0)),
        "profile": profile_name or None,
        "phase": route.get("phase", ""),
        "skill": skill_name,
        "feature": feature or None,
        "task": task or None,
        "intent": intent or None,
        "tokenizer": tokenizer_mode(),
        "budget_categories": {
            "mandatory_tokens": sum(item["tokens"] for item in selected if item["tier"] == "Must"),
            "optional_tokens": sum(item["tokens"] for item in selected if item["tier"] != "Must"),
            "omitted_tokens": sum(item.get("tokens", 0) for item in omitted),
            "channels": channel_totals,
            "channel_limits": channel_limits,
        },
        "warnings": warnings,
        "delta": delta_active,
        "delta_from": delta_label,
        "fingerprints": {item["path"]: item["fingerprint"] for item in covered},
        "slices": {item["path"]: _slice_fingerprints(root, item) for item in covered},
        "delta_omitted": delta_omitted,
        "unchanged_selected": len(delta_omitted),
        "baseline_selected": len(set(previous_fingerprints) | set(previous_slices)),
    }
