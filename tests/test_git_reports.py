import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.git_reports import run


def command(root: Path, *args: str) -> None:
    subprocess.run(args, cwd=root, check=True, stdout=subprocess.DEVNULL)


class GitReportsTest(unittest.TestCase):
    def test_daily_then_weekly_removes_only_covered_daily_reports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            command(repo, "git", "init", "-q")
            command(repo, "git", "config", "user.name", "Tester")
            command(repo, "git", "config", "user.email", "tester@example.com")
            (repo / "work.txt").write_text("done\n", encoding="utf-8")
            command(repo, "git", "add", "work.txt")
            command(repo, "git", "commit", "-q", "-m", "完成日报功能")

            monday = date(2026, 8, 24)
            daily, weekly, committed = run(repo, monday, sync=False, force_weekly=False)
            self.assertTrue(daily.is_file())
            self.assertIsNone(weekly)
            self.assertFalse(committed)

            thursday = date(2026, 8, 27)
            _, weekly, committed = run(repo, thursday, sync=False, force_weekly=False)
            self.assertIsNotNone(weekly)
            self.assertFalse(committed)
            self.assertTrue(weekly.is_file())
            self.assertIn("Git 周报", weekly.read_text(encoding="utf-8"))
            self.assertFalse(daily.exists())
            self.assertFalse((repo / "Git日报" / "2026-08-27.md").exists())

    def test_sync_commits_only_reports_and_pushes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            remote = root / "remote.git"
            repo = root / "repo"
            command(root, "git", "init", "-q", "--bare", str(remote))
            command(root, "git", "init", "-q", "-b", "main", str(repo))
            command(repo, "git", "config", "user.name", "Tester")
            command(repo, "git", "config", "user.email", "tester@example.com")
            (repo / "work.txt").write_text("done\n", encoding="utf-8")
            command(repo, "git", "add", "work.txt")
            command(repo, "git", "commit", "-q", "-m", "initial")
            command(repo, "git", "remote", "add", "origin", str(remote))
            command(repo, "git", "push", "-q", "-u", "origin", "main")
            (repo / "unrelated.txt").write_text("do not commit\n", encoding="utf-8")

            daily, weekly, committed = run(
                repo, date.today(), sync=True, force_weekly=False
            )

            self.assertTrue(daily.exists())
            self.assertIsNone(weekly)
            self.assertTrue(committed)
            self.assertEqual("", subprocess.check_output(
                ["git", "-C", str(repo), "status", "--short", "--", "Git日报"],
                text=True,
            ))
            status = subprocess.check_output(
                ["git", "-C", str(repo), "status", "--short"], text=True
            )
            self.assertIn("?? unrelated.txt", status)
            remote_subject = subprocess.check_output(
                [
                    "git",
                    f"--git-dir={remote}",
                    "log",
                    "-1",
                    "--format=%s",
                    "refs/heads/main",
                ],
                text=True,
            ).strip()
            self.assertIn("Git 报告", remote_subject)


if __name__ == "__main__":
    unittest.main()
