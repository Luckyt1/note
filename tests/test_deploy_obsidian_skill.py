import importlib.util
import tempfile
import unittest
from pathlib import Path

from scripts.deploy_obsidian_skill import deploy_skill


MERGE_SCRIPT = (
    Path(__file__).parents[1]
    / "skills"
    / "obsidian-project-note"
    / "scripts"
    / "merge_notes.py"
)
SPEC = importlib.util.spec_from_file_location("obsidian_merge_notes", MERGE_SCRIPT)
assert SPEC and SPEC.loader
MERGE_NOTES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MERGE_NOTES)


class DeployObsidianSkillTest(unittest.TestCase):
    def test_removes_deprecated_note_sections_before_merge(self) -> None:
        body = """# 标题

## 本次完成
保留。

## 值得学习
删除学习内容。

## 决策与取舍
删除决策内容。

## 后续事项
删除后续内容。
"""

        result = MERGE_NOTES.without_deprecated_sections(body)

        self.assertIn("## 本次完成\n保留。", result)
        self.assertNotIn("值得学习", result)
        self.assertNotIn("删除学习内容", result)
        self.assertNotIn("决策与取舍", result)
        self.assertNotIn("后续事项", result)

    def test_deploys_and_preserves_existing_install_on_force(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "project"
            vault = root / "vault"
            target.mkdir()
            (vault / ".obsidian").mkdir(parents=True)

            destination, backup = deploy_skill(target, vault)
            self.assertIsNone(backup)
            skill_text = (destination / "SKILL.md").read_text(encoding="utf-8")
            save_script = (destination / "scripts" / "save_note.py").read_text(
                encoding="utf-8"
            )
            self.assertIn(str(destination), skill_text)
            self.assertIn(str(vault), skill_text)
            self.assertIn(str(vault), save_script)

            (destination / "local-change.txt").write_text("keep", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                deploy_skill(target, vault)

            current, backup = deploy_skill(target, vault, force=True)
            self.assertEqual(destination, current)
            self.assertIsNotNone(backup)
            self.assertEqual(target / ".codex" / "skill-backups", backup.parent)
            self.assertEqual(
                "keep", (backup / "local-change.txt").read_text(encoding="utf-8")
            )


if __name__ == "__main__":
    unittest.main()
