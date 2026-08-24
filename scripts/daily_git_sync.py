#!/usr/bin/env python3
"""每天安全提交并推送一个 Git 仓库；也可安装 20:00 用户级定时器。"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime
import fcntl
import getpass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


REPO_ROOT = Path(__file__).resolve().parents[1]
UNIT_NAME = "note-git-sync"
MAX_FILE_SIZE = 90 * 1024 * 1024
SECRET_PATTERNS = (
    re.compile(rb"ghp_[A-Za-z0-9]{20,}"),
    re.compile(rb"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(rb"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(rb"AKIA[0-9A-Z]{16}"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def ensure_repository(repo: Path) -> None:
    if not repo.is_dir():
        raise RuntimeError(f"Repository does not exist: {repo}")
    result = git(repo, "rev-parse", "--show-toplevel", check=False)
    if result.returncode or Path(result.stdout.strip()).resolve() != repo:
        raise RuntimeError(f"Not the root of a Git repository: {repo}")
    if git(repo, "rev-parse", "--abbrev-ref", "@{upstream}", check=False).returncode:
        raise RuntimeError("Current branch has no upstream; push with -u once first")
    for marker in ("MERGE_HEAD", "REBASE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD"):
        marker_path = Path(git(repo, "rev-parse", "--git-path", marker).stdout.strip())
        if not marker_path.is_absolute():
            marker_path = repo / marker_path
        if marker_path.exists():
            raise RuntimeError(f"Git operation is still in progress: {marker}")


@contextmanager
def repository_lock(repo: Path):
    lock_path = repo / "AI项目汇总" / ".merge.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def staged_paths(repo: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return [repo / os.fsdecode(name) for name in result.stdout.split(b"\0") if name]


def validate_staged_files(repo: Path) -> None:
    problems: list[str] = []
    for path in staged_paths(repo):
        if not path.is_file():
            continue
        size = path.stat().st_size
        relative = path.relative_to(repo)
        if size > MAX_FILE_SIZE:
            problems.append(f"file exceeds 90 MiB: {relative}")
            continue
        data = path.read_bytes()
        if b"\0" in data:
            continue
        if any(pattern.search(data) for pattern in SECRET_PATTERNS):
            problems.append(f"possible credential: {relative}")
    if problems:
        raise RuntimeError("Refusing public sync:\n- " + "\n- ".join(problems))


@contextmanager
def preserve_index_on_error(repo: Path):
    index_path = Path(git(repo, "rev-parse", "--git-path", "index").stdout.strip())
    if not index_path.is_absolute():
        index_path = repo / index_path
    original = index_path.read_bytes() if index_path.exists() else None
    try:
        yield
    except Exception:
        if original is None:
            index_path.unlink(missing_ok=True)
        else:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=".index-restore-", dir=index_path.parent
            )
            temporary = Path(temporary_name)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(original)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, index_path)
            finally:
                temporary.unlink(missing_ok=True)
        raise


def synchronize(repo: Path) -> str:
    repo = repo.resolve()
    ensure_repository(repo)
    with repository_lock(repo):
        with preserve_index_on_error(repo):
            git(repo, "add", "-A")
            validate_staged_files(repo)
            if git(repo, "diff", "--cached", "--quiet", check=False).returncode:
                day = datetime.now().astimezone().date().isoformat()
                message = (
                    f"保留 {day} 的笔记进展\n\n"
                    "Constraint: 每日 20:00 自动同步到远程仓库\n"
                    "Confidence: high\n"
                    "Scope-risk: narrow\n"
                    "Directive: 冲突或凭据检查失败时停止自动推送\n"
                    "Tested: git diff --cached --check\n"
                    "Not-tested: 笔记内容的人工复核"
                )
                whitespace = git(repo, "diff", "--cached", "--check", check=False)
                if whitespace.returncode:
                    raise RuntimeError(whitespace.stdout + whitespace.stderr)
                git(repo, "commit", "-m", message)

        upstream = git(repo, "rev-parse", "--abbrev-ref", "@{upstream}").stdout.strip()
        remote = upstream.split("/", 1)[0]
        git(repo, "fetch", remote)
        counts = git(repo, "rev-list", "--left-right", "--count", f"HEAD...{upstream}").stdout.split()
        _, behind = map(int, counts)
        if behind:
            git(repo, "rebase", upstream)
        git(repo, "push")
        return git(repo, "rev-parse", "--short", "HEAD").stdout.strip()


def unit_argument(value: Path | str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def unit_path(value: Path) -> str:
    encoded = str(value).encode("utf-8")
    safe = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789/._-"
    return "".join(chr(byte) if byte in safe else f"\\x{byte:02x}" for byte in encoded)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def install_timer(repo: Path, unit_dir: Path, *, enable: bool = True) -> tuple[Path, Path]:
    repo = repo.resolve()
    ensure_repository(repo)
    script = Path(__file__).resolve()
    service = unit_dir / f"{UNIT_NAME}.service"
    timer = unit_dir / f"{UNIT_NAME}.timer"
    atomic_write(
        service,
        "[Unit]\n"
        "Description=Daily Git sync for AI notes\n"
        "After=network-online.target\n"
        "Wants=network-online.target\n\n"
        "[Service]\n"
        "Type=oneshot\n"
        f"WorkingDirectory={unit_path(repo)}\n"
        f"ExecStart={unit_argument(sys.executable)} {unit_argument(script)} --repo {unit_argument(repo)}\n"
        "Environment=GIT_TERMINAL_PROMPT=0\n",
    )
    atomic_write(
        timer,
        "[Unit]\n"
        "Description=Sync AI notes to GitHub every day at 20:00\n\n"
        "[Timer]\n"
        "OnCalendar=*-*-* 20:00:00\n"
        "Persistent=true\n"
        "Unit=note-git-sync.service\n\n"
        "[Install]\n"
        "WantedBy=timers.target\n",
    )
    if enable:
        if not shutil.which("systemctl"):
            raise RuntimeError("systemctl is required to enable the timer")
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
        subprocess.run(
            ["systemctl", "--user", "enable", "--now", timer.name], check=True
        )
        if shutil.which("loginctl"):
            subprocess.run(
                ["loginctl", "enable-linger", getpass.getuser()], check=False
            )
    return service, timer


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO_ROOT, help="需要同步的 Git 仓库")
    parser.add_argument("--install", action="store_true", help="安装并启用每天 20:00 定时器")
    parser.add_argument(
        "--unit-dir",
        type=Path,
        default=Path.home() / ".config" / "systemd" / "user",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--no-enable", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if args.install:
            service, timer = install_timer(
                args.repo, args.unit_dir, enable=not args.no_enable
            )
            print(f"Installed service: {service}")
            print(f"Installed timer: {timer}")
        else:
            commit = synchronize(args.repo)
            print(f"Git sync complete: {commit}")
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Git sync failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
