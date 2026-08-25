#!/usr/bin/env python3
"""将 AI 项目汇总 Markdown 批量导出为独立 HTML 文件。"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from urllib.parse import quote, urlsplit


REPO_ROOT = Path(__file__).resolve().parents[1]
STYLE = """
:root {
  color-scheme: light;
  --page: #f3f1ec;
  --surface: #fffdf9;
  --surface-soft: #f7f5f0;
  --text: #272938;
  --muted: #686b78;
  --accent: #5856c7;
  --accent-strong: #3f3da1;
  --accent-soft: #eeedff;
  --border: #dedbe3;
  --code: #efedf5;
  --shadow: 0 18px 50px #25213a14;
}
@media (prefers-color-scheme: dark) {
  :root {
    color-scheme: dark;
    --page: #17171c;
    --surface: #202027;
    --surface-soft: #282830;
    --text: #ecebf2;
    --muted: #aaa8b4;
    --accent: #aaa7ff;
    --accent-strong: #c3c1ff;
    --accent-soft: #343250;
    --border: #3a3944;
    --code: #302f3a;
    --shadow: 0 18px 50px #0005;
  }
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  min-height: 100vh;
  padding: 2rem 1rem 4rem;
  background: var(--page);
  color: var(--text);
  font: 16px/1.75 -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  text-rendering: optimizeLegibility;
}
body::before { content: ""; position: fixed; inset: 0 0 auto; height: 4px; background: var(--accent); }
main {
  width: min(100%, 960px);
  margin: 0 auto;
  padding: clamp(1.5rem, 4vw, 4rem);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 24px;
  box-shadow: var(--shadow);
}
h1, h2, h3 { line-height: 1.3; text-wrap: balance; }
h1 { margin: .25rem 0 1rem; font-size: clamp(2rem, 6vw, 3.8rem); letter-spacing: -.04em; }
h2 { margin: 3.5rem 0 1.25rem; padding-left: .85rem; border-left: 4px solid var(--accent); font-size: clamp(1.35rem, 3vw, 1.75rem); scroll-margin-top: 6rem; }
h3 { margin: 2rem 0 .75rem; font-size: 1.05rem; color: var(--accent-strong); }
p { margin: .75rem 0 1.25rem; }
ul, ol { padding-left: 1.4rem; }
li { margin: .35rem 0; padding-left: .2rem; }
li::marker { color: var(--accent); }
a { color: var(--accent-strong); text-decoration-thickness: .08em; text-underline-offset: .2em; }
a:hover { color: var(--accent); }
a:focus-visible { outline: 3px solid var(--accent); outline-offset: 4px; border-radius: 4px; }
code { overflow-wrap: anywhere; background: var(--code); border-radius: 6px; padding: .18em .42em; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: .92em; }
pre { overflow-x: auto; background: var(--code); border: 1px solid var(--border); border-radius: 12px; padding: 1rem 1.2rem; line-height: 1.6; }
pre code { overflow-wrap: normal; background: none; padding: 0; }
.date-nav {
  position: sticky;
  top: .75rem;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: .5rem;
  overflow-x: auto;
  margin: -.5rem 0 2rem;
  padding: .65rem;
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: 14px;
  box-shadow: 0 8px 24px #25213a12;
  scrollbar-width: thin;
}
.date-nav strong { padding: 0 .35rem; color: var(--muted); font-size: .9rem; white-space: nowrap; }
.date-nav a { flex: none; display: inline-flex; align-items: center; min-height: 40px; padding: .35rem .75rem; background: var(--surface); border: 1px solid var(--border); border-radius: 999px; font-weight: 650; text-decoration: none; }
.date-nav a:hover { background: var(--accent-soft); border-color: var(--accent); }
blockquote { margin: 1.5rem 0; padding: .9rem 1.1rem; background: var(--surface-soft); border-left: 4px solid var(--accent); border-radius: 0 10px 10px 0; color: var(--muted); }
blockquote p { margin: 0; }
hr { border: 0; border-top: 1px solid var(--border); margin: 3rem 0; }
.hero { max-width: 680px; margin-bottom: 2.5rem; }
.eyebrow { margin: 0 0 .5rem; color: var(--accent-strong); font-size: .78rem; font-weight: 750; letter-spacing: .14em; text-transform: uppercase; }
.lead { color: var(--muted); font-size: clamp(1rem, 2.5vw, 1.18rem); }
.project-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: .9rem; margin: 0; padding: 0; list-style: none; }
.project-grid li { margin: 0; padding: 0; }
.project-grid a { display: flex; align-items: center; justify-content: space-between; min-height: 88px; padding: 1rem 1.15rem; background: var(--surface-soft); border: 1px solid var(--border); border-radius: 14px; font-weight: 700; text-decoration: none; transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease; }
.project-grid a::after { content: "→"; margin-left: 1rem; color: var(--accent); font-size: 1.25rem; }
.project-grid a:hover { transform: translateY(-2px); border-color: var(--accent); box-shadow: 0 10px 24px #25213a12; }
footer { width: min(100%, 960px); margin: 1.25rem auto 0; color: var(--muted); font-size: .85rem; text-align: center; }
@media (max-width: 640px) {
  body { padding: .75rem .65rem 2.5rem; }
  body::before { height: 3px; }
  main { padding: 1.4rem 1.1rem 2rem; border-radius: 18px; }
  h1 { font-size: clamp(1.9rem, 11vw, 2.8rem); }
  h2 { margin-top: 2.8rem; scroll-margin-top: 5.5rem; }
  .date-nav { top: .4rem; margin-inline: -.35rem; }
  .project-grid { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  .project-grid a { transition: none; }
}
@media print {
  body { padding: 0; background: #fff; color: #000; }
  body::before, .date-nav { display: none; }
  main { width: 100%; padding: 0; border: 0; box-shadow: none; }
  footer { width: 100%; }
}
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


def markdown_body(markdown: str) -> tuple[str, str, list[str]]:
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
    entry_dates: dict[int, str] = {}
    pending_heading: int | None = None
    for line_number, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r"^##\s+", stripped):
            pending_heading = line_number
        elif pending_heading is not None and (
            match := re.match(r"^-\s+创建时间：`(\d{4}-\d{2}-\d{2})", stripped)
        ):
            entry_dates[pending_heading] = match.group(1)
            pending_heading = None
    dates = list(dict.fromkeys(entry_dates.values()))
    anchored_dates: set[str] = set()

    def flush_paragraph() -> None:
        if paragraph:
            output.append(f"<p>{inline_markup(' '.join(paragraph))}</p>")
            paragraph.clear()

    def close_list() -> None:
        nonlocal list_tag
        if list_tag:
            output.append(f"</{list_tag}>")
            list_tag = None

    for line_number, line in enumerate(lines):
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
            date = entry_dates.get(line_number)
            anchor = ""
            if date and date not in anchored_dates:
                anchor = f' id="date-{date}"'
                anchored_dates.add(date)
            output.append(
                f"<h{level}{anchor}>{inline_markup(heading.group(2))}</h{level}>"
            )
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
    return title, "\n".join(output), dates


def render_date_navigation(dates: list[str]) -> str:
    if not dates:
        return ""
    links = "\n".join(
        f'<a href="#date-{date}"><time datetime="{date}">{date}</time></a>'
        for date in dates
    )
    return (
        '<nav class="date-nav" aria-label="按日期查找笔记">'
        f"<strong>按日期：</strong>\n{links}\n</nav>"
    )


def render_document(markdown: str, source_label: str) -> str:
    title, body, dates = markdown_body(markdown)
    navigation = render_date_navigation(dates)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{STYLE}</style>
</head>
<body>
<main class="document-page">
{navigation}
{body}
</main>
<footer>由 {html.escape(source_label)} 自动生成</footer>
</body>
</html>
"""


def render_index(exported: list[Path], output_root: Path) -> str:
    links = "\n".join(
        f'<li><a href="{quote(path.relative_to(output_root).as_posix())}">'
        f"{html.escape(path.parent.name)}</a></li>"
        for path in exported
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI 项目汇总</title>
  <style>{STYLE}</style>
</head>
<body>
<main class="index-page">
  <header class="hero">
    <p class="eyebrow">Personal knowledge base</p>
    <h1>AI 项目汇总</h1>
    <p class="lead">这里汇集了 AI 参与项目记录、整理和知识沉淀的实验结果。</p>
  </header>
  <ul class="project-grid">
{links}
  </ul>
</main>
<footer>由 scripts/export_summaries.py 自动生成</footer>
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
    (output_root / "index.html").write_text(
        render_index(exported, output_root), encoding="utf-8", newline="\n"
    )
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
