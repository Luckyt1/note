# Obsidian AI 项目笔记系统：云端迁移入口

这个目录和笔记数据放在同一个 Obsidian 仓库中，上传整个仓库到云端时会一起保存。

## 目录内容

- `README.md`：当前迁移入口说明。
- `obsidian-project-note-portable.tar.gz`：Skill、保存/合并脚本、systemd 定时器、安装脚本和完整安装文档。
- `SHA256SUMS`：压缩包完整性校验值。

## 笔记数据目录

- `../AI项目笔记/`：等待每小时整理的临时笔记。
- `../AI项目汇总/`：按项目保存的长期笔记。

压缩包不重复包含笔记数据。迁移时应同步整个 Obsidian 仓库，而不是只上传压缩包。

## 迁移前的重要操作

同一个云同步仓库只能让一台设备运行自动整理 timer。迁移前在旧设备执行：

```bash
systemctl --user disable --now obsidian-project-note-merge.timer
```

等待云端同步完成后，再在新设备继续。

## 新设备快速安装

此安装器面向 Linux/systemd，推荐 Ubuntu 22.04 或更新版本，并需要 Python 3.10+、Obsidian 1.12.7+ 和 Codex。

```bash
cd "/你的/Obsidian仓库/AI项目笔记系统迁移包"
sha256sum -c SHA256SUMS
tar -xzf obsidian-project-note-portable.tar.gz
cd obsidian-project-note-portable
sha256sum -c MANIFEST.sha256
./install.sh --vault "/你的/Obsidian仓库"
```

安装器默认使用 OpenAI 官方个人 Skill 目录 `$HOME/.agents/skills`。如果新设备的 Codex 仍使用 `$HOME/.codex/skills`：

```bash
./install.sh --vault "/你的/Obsidian仓库" --skill-root "$HOME/.codex/skills"
```

完整说明、验证方法和数据安全设计请查看解压目录中的 `README.md`。

OpenAI 官方文档：[Build skills](https://developers.openai.com/codex/skills)
