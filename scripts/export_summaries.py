#!/usr/bin/env python3
"""将 AI 项目汇总 Markdown 批量导出为独立 HTML 文件。"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from urllib.parse import urlsplit


REPO_ROOT = Path(__file__).resolve().parents[1]
STYLE = """
:root { color-scheme: light dark; }
body { max-width: 900px; margin: 0 auto; padding: 2rem 1rem 4rem; font: 16px/1.75 system-ui, sans-serif; }
h1, h2, h3 { line-height: 1.3; margin-top: 1.8em; }
h1 { border-bottom: 2px solid #8885; padding-bottom: .35em; }
h2 { border-bottom: 1px solid #8885; padding-bottom: .25em; }
code { background: #8882; border-radius: 4px; padding: .15em .35em; }
pre { overflow-x: auto; background: #8882; border-radius: 8px; padding: 1rem; }
pre code { background: none; padding: 0; }
a { color: #3977d4; }
blockquote { border-left: 4px solid #8886; margin-left: 0; padding-left: 1rem; color: #777; }
hr { border: 0; border-top: 1px solid #8885; margin: 2rem 0; }
footer { color: #777; font-size: .9rem; margin-top: 3rem; }
""".strip()


def inline_markup(text: str) -> str:
    """转换汇总中使用的少量行内 Markdown，并始终转义原始 HTML。"""
    tokens: list[str] = []

    def stash(value: str) -> str:
        tokens.append(value)
        return f"\ufff0{len(tokens) - 1}\ufff1"

    text = re.sub(
        r"`([^`]+)`",
        lambda match: stash(f"<code>{html.escape(match.group(1))}</code>"),
        text,
    )

    def replace_link(match: re.Match[str]) -> str:
        label, href = match.group(1), match.group(2).strip()
        scheme = urlsplit(href).scheme.lower()
        if scheme not in {"", "http", "https", "mailto"}:
            return stash(html.escape(label))
        return stash(
            f'<a href="{html.escape(href, quote=True)}">{html.escape(label)}</a>'
        )

    text = re.sub(r"\[([^]]+)]\(([^)]+)\)", replace_link, text)
    rendered = html.escape(text)
    rendered = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", rendered)
    rendered = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", rendered)
    for index, token in enumerate(tokens):
        rendered = rendered.replace(f"\ufff0{index}\ufff1", token)
    return rendered


def without_front_matter(lines: list[str]) -> list[str]:
    if not lines or lines[0].strip() != "---":
        return lines
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[index + 1 :]
    return lines


def markdown_body(markdown: str) -> tuple[str, str]:
    lines = without_front_matter(markdown.splitlines())
    title = next(
        (match.group(1) for line in lines if (match := re.match(r"^#\s+(.+)$", line))),
        "项目汇总",
    )
    output: list[str] = []
    paragraph: list[str] = []
    list_tag: str | None = None
    code_lines: list[str] = []
    in_code = False
    in_comment = False

    def flush_paragraph() -> None:
        if paragraph:
            output.append(f"<p>{inline_markup(' '.join(paragraph))}</p>")
            paragraph.clear()

    def close_list() -> None:
        nonlocal list_tag
        if list_tag:
            output.append(f"</{list_tag}>")
            list_tag = None

    for line in lines:
        stripped = line.strip()
        if in_comment:
            if "-->" in stripped:
                in_comment = False
            continue
        if stripped.startswith("<!--"):
            in_comment = "-->" not in stripped
            continue
        if in_code:
            if stripped.startswith("```"):
                output.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
                code_lines.clear()
                in_code = False
            else:
                code_lines.append(line)
            continue
        if stripped.startswith("```"):
            flush_paragraph()
            close_list()
            in_code = True
            continue
        if not stripped:
            flush_paragraph()
            close_list()
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        unordered = re.match(r"^[-*+]\s+(.+)$", stripped)
        ordered = re.match(r"^\d+\.\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            close_list()
            level = len(heading.group(1))
            output.append(f"<h{level}>{inline_markup(heading.group(2))}</h{level}>")
        elif stripped == "---":
            flush_paragraph()
            close_list()
            output.append("<hr>")
        elif unordered or ordered:
            flush_paragraph()
            wanted_tag = "ul" if unordered else "ol"
            if list_tag != wanted_tag:
                close_list()
                output.append(f"<{wanted_tag}>")
                list_tag = wanted_tag
            item = (unordered or ordered).group(1)  # type: ignore[union-attr]
            output.append(f"<li>{inline_markup(item)}</li>")
        elif stripped.startswith("> "):
            flush_paragraph()
            close_list()
            output.append(f"<blockquote><p>{inline_markup(stripped[2:])}</p></blockquote>")
        else:
            close_list()
            paragraph.append(stripped)

    if in_code:
        output.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
    flush_paragraph()
    close_list()
    return title, "\n".join(output)


def render_document(markdown: str, source_label: str) -> str:
    title, body = markdown_body(markdown)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{STYLE}</style>
</head>
<body>
<main>
{body}
</main>
<footer>由 {html.escape(source_label)} 自动生成</footer>
</body>
</html>
"""


def export_summaries(source_root: Path, output_root: Path) -> list[Path]:
    sources = sorted(source_root.rglob("项目汇总.md"))
    if not sources:
        raise FileNotFoundError(f"在 {source_root} 中没有找到项目汇总.md")

    exported: list[Path] = []
    for source in sources:
        relative = source.relative_to(source_root)
        destination = output_root / relative.with_suffix(".html")
        destination.parent.mkdir(parents=True, exist_ok=True)
        document = render_document(source.read_text(encoding="utf-8"), str(relative))
        destination.write_text(document, encoding="utf-8", newline="\n")
        exported.append(destination)
    return exported


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=REPO_ROOT / "AI项目汇总")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "HTML汇总")
    args = parser.parse_args()

    try:
        exported = export_summaries(args.source.resolve(), args.output.resolve())
    except (FileNotFoundError, OSError) as error:
        parser.error(str(error))
    for path in exported:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
