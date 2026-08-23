#!/usr/bin/env python3
"""将仓库内的 obsidian-project-note Skill 部署到另一个项目。"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import os
import shutil
import tempfile


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_SKILL = REPO_ROOT / "skills" / "obsidian-project-note"
ORIGINAL_VAULT = "/home/tang/note/note"
ORIGINAL_SKILL_DIR = "/home/tang/.codex/skills/obsidian-project-note"


def replace_paths(skill_dir: Path, installed_dir: Path, vault: Path) -> None:
    replacements = {
        ORIGINAL_VAULT: str(vault),
        ORIGINAL_SKILL_DIR: str(installed_dir),
        str(SOURCE_SKILL): str(installed_dir),
    }
    for path in skill_dir.rglob("*"):
        if not path.is_file() or path.suffix not in {".md", ".py", ".yaml", ".yml"}:
            continue
        content = path.read_text(encoding="utf-8")
        for old, new in replacements.items():
            content = content.replace(old, new)
        path.write_text(content, encoding="utf-8", newline="\n")


def validate_skill(skill_dir: Path) -> None:
    if not (skill_dir / "SKILL.md").is_file():
        raise FileNotFoundError(f"Skill source is incomplete: {skill_dir}")
    for script in (skill_dir / "scripts").glob("*.py"):
        compile(script.read_text(encoding="utf-8"), str(script), "exec")


def backup_path(destination: Path, backup_root: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = backup_root / f"{destination.name}-{stamp}"
    index = 2
    while candidate.exists():
        candidate = backup_root / f"{destination.name}-{stamp}-{index}"
        index += 1
    return candidate


def deploy_skill(
    target_project: Path,
    vault: Path,
    *,
    force: bool = False,
    source_skill: Path = SOURCE_SKILL,
) -> tuple[Path, Path | None]:
    target_project = target_project.resolve()
    vault = vault.resolve()
    source_skill = source_skill.resolve()
    if not target_project.is_dir():
        raise FileNotFoundError(f"Target project does not exist: {target_project}")
    if not (vault / ".obsidian").is_dir():
        raise FileNotFoundError(f"Not an Obsidian vault: {vault}")
    validate_skill(source_skill)

    skill_root = target_project / ".codex" / "skills"
    destination = skill_root / "obsidian-project-note"
    skill_root.mkdir(parents=True, exist_ok=True)
    staging_root = Path(tempfile.mkdtemp(prefix=".skill-deploy-", dir=skill_root))
    staged_skill = staging_root / destination.name
    backup: Path | None = None
    try:
        shutil.copytree(source_skill, staged_skill)
        replace_paths(staged_skill, destination, vault)
        validate_skill(staged_skill)

        if destination.exists() or destination.is_symlink():
            if not force:
                raise FileExistsError(
                    f"Skill already exists: {destination}; use --force to keep a backup and replace it"
                )
            backup_root = target_project / ".codex" / "skill-backups"
            backup_root.mkdir(parents=True, exist_ok=True)
            backup = backup_path(destination, backup_root)
            os.replace(destination, backup)

        try:
            os.replace(staged_skill, destination)
        except Exception:
            if backup and backup.exists() and not destination.exists():
                os.replace(backup, destination)
            raise

        for script in (destination / "scripts").glob("*.py"):
            script.chmod(0o755)
        return destination, backup
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target_project", type=Path, help="需要启用 Skill 的项目目录")
    parser.add_argument(
        "--vault",
        type=Path,
        default=REPO_ROOT,
        help="Obsidian 仓库路径，默认是当前 note 仓库",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="替换已有 Skill，并在 .codex/skill-backups 中保留备份",
    )
    args = parser.parse_args()

    try:
        destination, backup = deploy_skill(
            args.target_project, args.vault, force=args.force
        )
    except (FileExistsError, FileNotFoundError, OSError, UnicodeError) as error:
        parser.error(str(error))
    print(f"Installed Skill: {destination}")
    if backup:
        print(f"Previous Skill backup: {backup}")
    print("Restart Codex in the target project if the Skill is not detected immediately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
