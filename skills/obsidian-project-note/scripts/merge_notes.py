#!/usr/bin/env python3
"""Merge Obsidian AI project notes by project, then remove merged sources."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile


DEFAULT_VAULT = Path("/home/tang/note/note")
INBOX_FOLDER = "AI项目笔记"
SUMMARY_FOLDER = "AI项目汇总"
SOURCE_MARKER = "obsidian-project-note-source"


def yaml_value(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def parse_scalar(value: str) -> str:
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        try:
            return str(json.loads(value))
        except json.JSONDecodeError:
            pass
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def split_note(content: str) -> tuple[dict[str, str], str] | None:
    match = re.match(r"\A---\r?\n(?P<meta>.*?)\r?\n---(?:\r?\n|\Z)", content, re.DOTALL)
    if not match:
        return None

    metadata: dict[str, str] = {}
    for line in match.group("meta").splitlines():
        field = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*$", line)
        if field:
            metadata[field.group(1)] = parse_scalar(field.group(2))
    return metadata, content[match.end() :].strip()


def project_folder(project: str) -> str:
    clean = re.sub(r'[\\/:*?"<>|\r\n]+', "-", project).strip(" .-") or "project"
    if clean != project or len(clean.encode("utf-8")) > 180:
        digest = hashlib.sha256(project.encode("utf-8")).hexdigest()[:8]
        prefix = clean.encode("utf-8")[:160].decode("utf-8", errors="ignore").rstrip(" .-")
        clean = f"{prefix or 'project'}-{digest}"
    return clean


def extract_title(body: str, fallback: str) -> tuple[str, str]:
    title = re.search(r"(?m)^#\s+(.+?)\s*$", body)
    if not title:
        return fallback, body
    remaining = f"{body[: title.start()]}{body[title.end() :]}".strip()
    remaining = re.sub(r"(?m)^(#{2,5})(?=\s)", r"#\1", remaining)
    return title.group(1).strip(), remaining


def source_marker(source: Path) -> str:
    return f"<!-- {SOURCE_MARKER}: {source.name} -->"


def new_summary(project: str, project_path: str, updated: str) -> str:
    return (
        "---\n"
        f"project: {yaml_value(project)}\n"
        f"project_path: {yaml_value(project_path)}\n"
        f"updated: {yaml_value(updated)}\n"
        "tags:\n"
        "  - ai-project-summary\n"
        "  - learning\n"
        "---\n\n"
        f"# {project} 项目汇总\n"
    )


def entry(source: Path, metadata: dict[str, str], body: str) -> str:
    title, content = extract_title(body, source.stem)
    created = metadata.get("created", "时间未知")
    parts = [
        f"## {title}",
        source_marker(source),
        "",
        f"- 创建时间：`{created}`",
        f"- 原始笔记：`{source.name}`",
    ]
    if content:
        parts.extend(["", content])
    return "\n".join(parts)


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write(path: Path, content: str) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as handle:
            handle.write(content)
            if not content.endswith("\n"):
                handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def update_timestamp(content: str, updated: str) -> str:
    return re.sub(
        r"(?m)^updated:\s*.*$", f"updated: {yaml_value(updated)}", content, count=1
    )


def merge_group(
    archive: Path,
    inbox: Path,
    project: str,
    notes: list[tuple[Path, dict[str, str], str]],
) -> int:
    project_dir = archive / project_folder(project)
    project_dir.mkdir(parents=True, exist_ok=True)
    target = project_dir / "项目汇总.md"
    updated = notes[-1][1].get("created", "时间未知")

    if target.exists():
        merged = target.read_text(encoding="utf-8")
        parsed = split_note(merged)
        if not parsed or parsed[0].get("project") != project:
            raise RuntimeError(f"summary project mismatch: {target}")
    else:
        project_path = next((meta.get("project_path", "") for _, meta, _ in notes), "")
        merged = new_summary(project, project_path, updated)

    appended = 0
    for source, metadata, body in notes:
        marker = source_marker(source)
        if marker not in merged:
            merged = f"{merged.rstrip()}\n\n---\n\n{entry(source, metadata, body)}\n"
            appended += 1

    if appended:
        atomic_write(target, update_timestamp(merged, updated))

    for source, _, _ in notes:
        source.unlink()
    fsync_directory(inbox)
    return appended


def merge_notes(vault: Path) -> tuple[int, int, int]:
    if not (vault / ".obsidian").is_dir():
        raise ValueError(f"not an Obsidian vault: {vault}")

    inbox = vault / INBOX_FOLDER
    if not inbox.is_dir():
        return 0, 0, 0

    archive = vault / SUMMARY_FOLDER
    archive.mkdir(parents=True, exist_ok=True)
    groups: dict[str, list[tuple[Path, dict[str, str], str]]] = {}
    skipped = 0

    with (archive / ".merge.lock").open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for source in sorted(inbox.glob("*.md")):
            parsed = split_note(source.read_text(encoding="utf-8"))
            if not parsed or not parsed[0].get("project", "").strip():
                print(f"Skipped note without project: {source}", file=sys.stderr)
                skipped += 1
                continue
            metadata, body = parsed
            project = metadata["project"].strip()
            groups.setdefault(project, []).append((source, metadata, body))

        merged = 0
        for project in sorted(groups):
            merged += merge_group(archive, inbox, project, groups[project])

    return merged, len(groups), skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    args = parser.parse_args()

    try:
        merged, projects, skipped = merge_notes(args.vault)
    except (OSError, UnicodeError, ValueError, RuntimeError) as error:
        print(f"Merge failed: {error}", file=sys.stderr)
        return 1

    print(f"Merged {merged} note(s) into {projects} project summary file(s); skipped {skipped}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
