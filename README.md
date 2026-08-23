# AI 笔记实验

这个项目用于探索 AI 参与笔记记录、整理和知识沉淀的可能性。

目前主要尝试：

- 让 AI 自动记录项目中的关键改动、验证结果与经验；
- 将分散的笔记整理成便于回顾的项目知识；
- 探索 AI、Obsidian 与 Git 协作的个人知识管理方式。

项目仍处于实验阶段，内容、结构和工作流程会随着实践持续更新。

## 导出 HTML

运行下面的命令，可将 `AI项目汇总/` 中的所有项目总结自动转换为独立 HTML 文件：

```bash
python3 scripts/export_summaries.py
```

生成结果保存在 `HTML汇总/`，不需要安装第三方依赖。推送到 `main` 后，GitHub Actions 会自动刷新并部署站点：

https://luckyt1.github.io/note/
