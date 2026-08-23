import tempfile
import unittest
from pathlib import Path

from scripts.export_summaries import export_summaries


class ExportSummariesTest(unittest.TestCase):
    def test_exports_safe_standalone_html(self) -> None:
        markdown = """---
project: demo
---
# 示例汇总
<!-- internal marker -->

## 本次完成
支持 `代码`、**强调**和列表。

- 第一项
- 第二项

<script>alert('x')</script>
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source" / "示例" / "项目汇总.md"
            output = root / "output"
            source.parent.mkdir(parents=True)
            source.write_text(markdown, encoding="utf-8")

            [destination] = export_summaries(source.parents[1], output)
            first_result = destination.read_text(encoding="utf-8")
            export_summaries(source.parents[1], output)

            self.assertEqual(first_result, destination.read_text(encoding="utf-8"))
            self.assertIn('<html lang="zh-CN">', first_result)
            self.assertIn("<h1>示例汇总</h1>", first_result)
            self.assertIn("<code>代码</code>", first_result)
            self.assertIn("<strong>强调</strong>", first_result)
            self.assertIn("<ul>\n<li>第一项</li>", first_result)
            self.assertIn("&lt;script&gt;alert", first_result)
            self.assertNotIn("internal marker", first_result)
            self.assertNotIn("project: demo", first_result)


if __name__ == "__main__":
    unittest.main()
