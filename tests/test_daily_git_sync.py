import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.daily_git_sync import install_timer, synchronize


def run(directory: Path, *args: str) -> None:
    subprocess.run(args, cwd=directory, check=True, stdout=subprocess.PIPE)


class DailyGitSyncTest(unittest.TestCase):
    def test_commits_rebases_and_pushes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            remote = root / "remote.git"
            first = root / "first"
            second = root / "second"
            run(root, "git", "init", "--bare", str(remote))
            run(root, "git", "clone", str(remote), str(first))
            run(first, "git", "config", "user.name", "Test")
            run(first, "git", "config", "user.email", "test@example.com")
            run(first, "git", "switch", "-c", "main")
            (first / "README.md").write_text("start\n", encoding="utf-8")
            run(first, "git", "add", "README.md")
            run(first, "git", "commit", "-m", "initial")
            run(first, "git", "push", "-u", "origin", "main")

            run(root, "git", "clone", "--branch", "main", str(remote), str(second))
            run(second, "git", "config", "user.name", "Test")
            run(second, "git", "config", "user.email", "test@example.com")
            (second / "remote.md").write_text("remote\n", encoding="utf-8")
            run(second, "git", "add", "remote.md")
            run(second, "git", "commit", "-m", "remote")
            run(second, "git", "push")

            (first / "local.md").write_text("local\n", encoding="utf-8")
            synchronize(first)
            run(second, "git", "pull", "--ff-only")
            self.assertTrue((second / "local.md").is_file())

            secret = first / "secret.txt"
            secret.write_text("github_pat_abcdefghijklmnopqrstuvwxyz123456", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                synchronize(first)
            status = subprocess.run(
                ["git", "status", "--short"],
                cwd=first,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout
            self.assertEqual("?? secret.txt\n", status)

    def test_installs_persistent_20_clock_timer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo project 笔记"
            units = root / "units"
            repo.mkdir()
            run(repo, "git", "init", "-b", "main")
            run(repo, "git", "remote", "add", "origin", "example.invalid:test.git")
            run(repo, "git", "config", "user.name", "Test")
            run(repo, "git", "config", "user.email", "test@example.com")
            (repo / "x").write_text("x", encoding="utf-8")
            run(repo, "git", "add", "x")
            run(repo, "git", "commit", "-m", "initial")
            run(repo, "git", "update-ref", "refs/remotes/origin/main", "HEAD")
            run(repo, "git", "branch", "--set-upstream-to=origin/main", "main")

            service, timer = install_timer(repo, units, enable=False)
            service_content = service.read_text(encoding="utf-8")
            content = timer.read_text(encoding="utf-8")
            self.assertIn("WorkingDirectory=", service_content)
            self.assertIn("\\x20", service_content)
            self.assertNotIn('WorkingDirectory="', service_content)
            self.assertIn("OnCalendar=*-*-* 20:00:00", content)
            self.assertIn("Persistent=true", content)


if __name__ == "__main__":
    unittest.main()
