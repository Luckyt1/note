import tempfile
import unittest
from pathlib import Path

from scripts.export_summaries import export_summaries, render_document


class ExportSummariesTest(unittest.TestCase):
    def test_exports_safe_standalone_html(self) -> None:
        markdown = """---
project: demo
---
# 示例汇总
<!-- internal marker -->

## 本次完成
- 创建时间：`2026-08-24T09:30:00+08:00`

支持 `代码`、**强调**和列表。

- 第一项
- 第二项

<script>alert('x')</script>

## 同日记录
- 创建时间：`2026-08-24T16:00:00+08:00`

当天的第二篇记录。

## 次日记录
- 创建时间：`2026-08-25T10:00:00+08:00`

继续记录。
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
            self.assertIn('<main class="document-page">', first_result)
            self.assertIn("prefers-color-scheme: dark", first_result)
            self.assertIn("prefers-reduced-motion: reduce", first_result)
            self.assertIn("<h1>示例汇总</h1>", first_result)
            self.assertIn("<code>代码</code>", first_result)
            self.assertIn("<strong>强调</strong>", first_result)
            self.assertIn("<ul>\n<li>第一项</li>", first_result)
            self.assertIn('aria-label="按日期查找笔记"', first_result)
            self.assertEqual(first_result.count('href="#date-2026-08-24"'), 1)
            self.assertEqual(first_result.count('id="date-2026-08-24"'), 1)
            self.assertIn('href="#date-2026-08-25"', first_result)
            self.assertIn('id="date-2026-08-25"', first_result)
            self.assertIn("&lt;script&gt;alert", first_result)
            self.assertNotIn("internal marker", first_result)
            self.assertNotIn("project: demo", first_result)

            index = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn("AI 项目汇总", index)
            self.assertIn('<header class="hero">', index)
            self.assertIn('<ul class="project-grid">', index)
            self.assertIn(
                'href="%E7%A4%BA%E4%BE%8B/%E9%A1%B9%E7%9B%AE%E6%B1%87%E6%80%BB.html"',
                index,
            )

    def test_omits_date_navigation_without_dated_notes(self) -> None:
        document = render_document("# 无日期汇总\n\n仅有说明。", "demo.md")

        self.assertNotIn('aria-label="按日期查找笔记"', document)


if __name__ == "__main__":
    unittest.main()
