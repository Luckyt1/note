# AI 笔记实验

这个项目用于探索 AI 参与笔记记录、整理和知识沉淀的可能性。

目前主要尝试：

- 让 AI 自动记录项目中的关键改动、验证结果与经验；
- 将分散的笔记整理成便于回顾的项目知识；
- 探索 AI、Obsidian 与 Git 协作的个人知识管理方式。

项目仍处于实验阶段，内容、结构和工作流程会随着实践持续更新。

## 在其他项目中部署 Skill

仓库中的 `skills/obsidian-project-note/` 是可直接审查和维护的 Skill 源码。运行下面的命令，可将它部署到另一个项目的 `.codex/skills/`：

```bash
python3 scripts/deploy_obsidian_skill.py /你的/目标项目
```

脚本默认把当前仓库作为 Obsidian 笔记库。目标项目已有同名 Skill 时不会覆盖；如需更新，使用 `--force`，旧版本会保留到目标项目的 `.codex/skill-backups/`。该脚本只部署项目级 Skill；在新设备安装自动整理定时器时，使用 `AI项目笔记系统迁移包/`。

## 导出 HTML

运行下面的命令，可将 `AI项目汇总/` 中的所有项目总结自动转换为独立 HTML 文件：

```bash
python3 scripts/export_summaries.py
```

生成结果保存在 `HTML汇总/`，不需要安装第三方依赖。推送到 `main` 后，GitHub Actions 会自动刷新并部署站点：

https://luckyt1.github.io/note/
