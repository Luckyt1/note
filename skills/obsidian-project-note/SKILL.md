---
name: obsidian-project-note
description: Save one concise Obsidian project note after AI coding or project-writing tasks that make substantive project changes, summarizing the outcome, key changes, and verification. Use when Codex implements, fixes, refactors, tests, configures, or documents a project; skip read-only work and migration-only copying, syncing, deployment, backup, restore, import, or export operations that do not change behavior.
---

# Obsidian Project Note

After finishing and verifying a project task, save exactly one concise Chinese Markdown note before the final response. The user's Obsidian 1.12.7 vault is `/home/tang/note/note`; notes belong in its `AI项目笔记/` folder.

## When to write

- Write a note when the task created, edited, moved, or deleted project code, configuration, tests, scripts, or project documentation.
- Write once per completed user task, after the last meaningful verification step.
- If changes were made but the task ends partial or blocked, still write the note and set the status accurately.
- Do not write for read-only explanations, repository inspection, planning, or review with no file changes.
- Do not write when the task only copies, syncs, deploys, backs up, restores, imports, exports, or relocates existing code or artifacts between directories, repositories, devices, or machines, even if files change at the destination.
- If migration work also implements, fixes, or refactors behavior, write only about that substantive engineering change; do not record the transport operation itself.
- Respect an explicit user request not to create a note.

## Note content

Use this compact structure and omit no required section:

```markdown
---
created: <ISO-8601 local time>
project: <project name>
project_path: <absolute project path>
status: completed | partial | blocked
tags:
  - ai-project
  - learning
---

# <short task title>

## 本次完成
<What outcome was achieved and why it matters.>

## 关键改动
- `<relative file>`：<important behavior change>

## 验证结果
- `<command or check>`：<result>
```

Keep it factual and useful to the future reader. Do not paste large diffs or logs. Never record secrets, credentials, tokens, private keys, or sensitive environment values.

## Save and verify

1. Draft the complete Markdown in a temporary file under `/tmp` using the normal file-editing tool.
2. Run:

   ```bash
   /home/tang/.codex/skills/obsidian-project-note/scripts/save_note.py <temporary-markdown-file> --project <project-name>
   ```

3. Read the printed destination path and verify that the note exists and contains the expected headings.
4. Remove the temporary file when permitted; otherwise leave it in `/tmp`.
5. Mention the saved note path briefly in the final response.

The helper writes directly into the Markdown vault, so Obsidian discovers the note without needing the GUI to be running. If sandbox permissions block the helper, request narrowly scoped permission for this exact write; do not silently skip the note or claim it was saved.

## Automatic organization

The user-level `obsidian-project-note-merge.timer` runs hourly. It calls `scripts/merge_notes.py` to:

- group inbox notes by the exact `project` frontmatter value;
- append each note to `AI项目汇总/<project>/项目汇总.md`;
- preserve a source marker so interrupted retries cannot duplicate content;
- delete an inbox note only after its merged file is durably written;
- leave malformed notes without a `project` value untouched for manual repair.

Do not manually move or delete inbox notes as part of normal Skill use; the timer owns that lifecycle.
