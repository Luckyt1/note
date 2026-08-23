import tempfile
import unittest
from pathlib import Path

from scripts.deploy_obsidian_skill import deploy_skill


class DeployObsidianSkillTest(unittest.TestCase):
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
