#!/usr/bin/env python3
"""Save a prepared Markdown note into the user's Obsidian vault."""

from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import tempfile

from merge_notes import fsync_directory, project_folder, split_note


DEFAULT_VAULT = Path("/home/tang/note/note")
NOTE_FOLDER = "AI项目笔记"


def candidate_paths(folder: Path, project: str):
    stem = f"{datetime.now().astimezone():%Y-%m-%d_%H-%M-%S}_{project_folder(project)}"
    yield folder / f"{stem}.md"
    index = 2
    while True:
        yield folder / f"{stem}_{index}.md"
        index += 1


def atomic_create(folder: Path, project: str, content: str) -> Path:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=folder, prefix=".new-note.", delete=False
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)

        for destination in candidate_paths(folder, project):
            try:
                os.link(temporary, destination)
            except FileExistsError:
                continue
            fsync_directory(folder)
            return destination
        raise RuntimeError("unable to allocate note filename")
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="prepared UTF-8 Markdown file")
    parser.add_argument("--project", required=True, help="project name used in the filename")
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    args = parser.parse_args()

    if not args.source.is_file():
        parser.error(f"source file does not exist: {args.source}")
    if not (args.vault / ".obsidian").is_dir():
        parser.error(f"not an Obsidian vault: {args.vault}")

    content = args.source.read_text(encoding="utf-8")
    if not content.strip():
        parser.error("source note is empty")

    parsed = split_note(content)
    required = ("created", "project", "project_path", "status")
    if not parsed or any(not parsed[0].get(field, "").strip() for field in required):
        parser.error(f"source note requires frontmatter fields: {', '.join(required)}")
    if parsed[0]["project"].strip() != args.project.strip():
        parser.error("frontmatter project does not match --project")

    folder = args.vault / NOTE_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    destination = atomic_create(folder, args.project, content)
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
