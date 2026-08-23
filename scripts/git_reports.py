#!/usr/bin/env python3
"""Pull a Git repository and create deterministic daily and Thursday reports."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timedelta
import os
from pathlib import Path
import subprocess
import tempfile


REPO_ROOT = Path(__file__).resolve().parents[1]
DAILY_FOLDER = "Git日报"
WEEKLY_FOLDER = "Git周报"


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as handle:
            handle.write(content.rstrip() + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def commits_on(repo: Path, report_date: date) -> list[dict[str, object]]:
    start = report_date.isoformat()
    end = (report_date + timedelta(days=1)).isoformat()
    raw = git(
        repo,
        "log",
        f"--since={start} 00:00:00",
        f"--until={end} 00:00:00",
        "--date=iso-local",
        "--format=%H%x1f%h%x1f%an%x1f%ad%x1f%s",
    )
    commits: list[dict[str, object]] = []
    for line in raw.splitlines():
        fields = line.split("\x1f", 4)
        if len(fields) != 5:
            continue
        full_hash, short_hash, author, committed_at, subject = fields
        files: Counter[str] = Counter()
        insertions = deletions = 0
        for stat in git(repo, "show", "--numstat", "--format=", full_hash).splitlines():
            parts = stat.split("\t", 2)
            if len(parts) != 3:
                continue
            added, removed, filename = parts
            files[filename] += 1
            if added.isdigit():
                insertions += int(added)
            if removed.isdigit():
                deletions += int(removed)
        commits.append(
            {
                "hash": short_hash,
                "author": author,
                "time": committed_at,
                "subject": subject,
                "files": sorted(files),
                "insertions": insertions,
                "deletions": deletions,
            }
        )
    return commits


def daily_markdown(repo: Path, report_date: date, commits: list[dict[str, object]]) -> str:
    lines = [
        "---",
        f"date: {report_date.isoformat()}",
        'type: "git-daily-report"',
        f'repository: "{repo.name}"',
        "---",
        "",
        f"# {report_date.isoformat()} Git 日报",
        "",
        "## 概览",
        "",
        f"- 仓库：`{repo}`",
        f"- 提交数：{len(commits)}",
        f"- 代码变化：+{sum(int(c['insertions']) for c in commits)} / -{sum(int(c['deletions']) for c in commits)}",
        "",
        "## 提交记录",
        "",
    ]
    if not commits:
        lines.append("- 当天没有 Git 提交。")
    for commit in commits:
        lines.extend(
            [
                f"### `{commit['hash']}` {commit['subject']}",
                "",
                f"- 作者：{commit['author']}",
                f"- 时间：{commit['time']}",
                f"- 变更：+{commit['insertions']} / -{commit['deletions']}",
            ]
        )
        files = commit["files"]
        if files:
            lines.append(f"- 文件：{', '.join(f'`{name}`' for name in files)}")
        lines.append("")
    return "\n".join(lines)


def weekly_period(thursday: date) -> tuple[date, date]:
    return thursday - timedelta(days=6), thursday


def weekly_markdown(repo: Path, start: date, end: date, reports: list[Path]) -> str:
    sections = []
    for report in reports:
        body = report.read_text(encoding="utf-8")
        body = body.split("---", 2)[-1].strip() if body.startswith("---\n") else body.strip()
        sections.append(body)
    return "\n".join(
        [
            "---",
            f"start: {start.isoformat()}",
            f"end: {end.isoformat()}",
            'type: "git-weekly-report"',
            f'repository: "{repo.name}"',
            "---",
            "",
            f"# {start.isoformat()} 至 {end.isoformat()} Git 周报",
            "",
            "## 周报概览",
            "",
            f"- 汇总日报：{len(reports)} 份",
            f"- 生成时间：{datetime.now().astimezone().isoformat(timespec='seconds')}",
            "",
            "## 每日明细",
            "",
            *sections,
            "",
        ]
    )


def report_paths(folder: Path, start: date, end: date) -> list[Path]:
    paths = []
    current = start
    while current <= end:
        candidate = folder / f"{current.isoformat()}.md"
        if candidate.is_file():
            paths.append(candidate)
        current += timedelta(days=1)
    return paths


def sync_reports(repo: Path, report_date: date) -> bool:
    """Commit only report folders, rebase onto the remote, and push."""
    pathspecs = [DAILY_FOLDER]
    if (repo / WEEKLY_FOLDER).exists() or git(repo, "ls-files", "--", WEEKLY_FOLDER).strip():
        pathspecs.append(WEEKLY_FOLDER)
    git(repo, "add", "-A", "--", *pathspecs)
    staged = subprocess.run(
        ["git", "-C", str(repo), "diff", "--cached", "--quiet", "--exit-code"],
        check=False,
    )
    if staged.returncode not in (0, 1):
        raise RuntimeError("failed to inspect staged report changes")
    committed = staged.returncode == 1
    if committed:
        git(repo, "commit", "-m", f"生成 {report_date.isoformat()} Git 报告")
    git(repo, "pull", "--rebase", "--autostash")
    git(repo, "push")
    return committed


def run(
    repo: Path, report_date: date, *, sync: bool, force_weekly: bool
) -> tuple[Path, Path | None, bool]:
    repo = repo.resolve()
    git(repo, "rev-parse", "--is-inside-work-tree")
    if sync:
        git(repo, "pull", "--ff-only")

    daily_root = repo / DAILY_FOLDER
    daily = daily_root / f"{report_date.isoformat()}.md"
    atomic_write(daily, daily_markdown(repo, report_date, commits_on(repo, report_date)))

    weekly: Path | None = None
    if report_date.weekday() == 3 or force_weekly:
        end = report_date
        start, _ = weekly_period(end)
        sources = report_paths(daily_root, start, end)
        if not sources:
            raise RuntimeError("no daily reports found for weekly report")
        weekly = repo / WEEKLY_FOLDER / f"{start.isoformat()}_{end.isoformat()}.md"
        atomic_write(weekly, weekly_markdown(repo, start, end, sources))
        for source in sources:
            source.unlink()
    committed = sync_reports(repo, report_date) if sync else False
    return daily, weekly, committed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--no-pull", action="store_true", help="测试或离线时跳过 git pull")
    parser.add_argument("--force-weekly", action="store_true", help="非周四也生成周报")
    args = parser.parse_args()
    try:
        daily, weekly, committed = run(
            args.repo, args.date, sync=not args.no_pull, force_weekly=args.force_weekly
        )
    except (OSError, RuntimeError, UnicodeError) as error:
        parser.error(str(error))
    print(f"Daily report: {daily}")
    if weekly:
        print(f"Weekly report: {weekly}")
        print("Merged daily reports were removed after the weekly report was saved.")
    if not args.no_pull:
        print(f"Cloud sync complete; report commit created: {'yes' if committed else 'no'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
