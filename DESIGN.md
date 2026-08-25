# Design

## Source of truth
- Status: Active
- Last refreshed: 2026-08-25
- Primary product surfaces: 项目索引页、项目汇总页、页内日期导航。
- Evidence reviewed: `README.md`、`scripts/export_summaries.py`、`HTML汇总/index.html`；仓库内没有现成品牌资产、截图或独立样式表。

## Brand
- Personality: 安静、清晰、可信，像一本整理良好的个人工程手册。
- Trust signals: 明确的项目名称、日期、内容层级和生成来源。
- Avoid: 仪表盘感、强烈渐变、密集装饰、依赖图片才能成立的布局。

## Product goals
- Goals: 快速进入项目、按日期定位笔记、长文阅读舒适、手机和电脑均可用。
- Non-goals: 社交互动、复杂搜索、动态后台和完整知识库管理。
- Success signals: 首屏能识别站点用途；两次点击内到达目标日期；长文层级易扫读。

## Personas and jobs
- Primary personas: 笔记库维护者，以及通过 GitHub Pages 查阅项目记录的读者。
- User jobs: 选择项目、定位日期、阅读改动与验证记录、复制命令或代码。
- Key contexts of use: 桌面端回顾长文、手机端快速查找、系统深色模式下阅读。

## Information architecture
- Primary navigation: 项目索引 → 项目汇总 → 日期锚点。
- Core routes/screens: `HTML汇总/index.html` 与各项目的 `项目汇总.html`。
- Content hierarchy: 站点/项目标题 → 日期入口 → 单篇记录标题 → 固定记录章节。

## Design principles
- Principle 1: 内容优先；装饰只用于强化层级和可点击性。
- Principle 2: 原生优先；用语义 HTML、CSS 和锚点完成交互。
- Tradeoffs: 保持单文件、零依赖，接受不提供复杂主题切换和客户端搜索。

## Visual language
- Color: 温和的纸张底色、深墨正文、蓝紫强调色；深色模式使用低眩光墨黑底色。
- Typography: 系统中文无衬线字体，代码使用系统等宽字体；正文保持舒适行高和有限行宽。
- Spacing/layout rhythm: 以 8px 为基础节奏，正文最大宽度约 960px，章节之间留出明显呼吸感。
- Shape/radius/elevation: 12–20px 圆角、细边框、轻阴影，不使用高光玻璃拟态作为主体。
- Motion: 仅链接和卡片的短过渡；遵守减少动态效果偏好。
- Imagery/iconography: 当前不使用图片或图标字体，避免增加资源和加载成本。

## Components
- Existing components to reuse: 项目列表、日期导航、Markdown 标题/列表/代码块、页脚。
- New/changed components: 首页介绍区、项目卡片列表、胶囊日期链接、长文内容容器。
- Variants and states: 浅色/深色、hover、focus-visible、移动端堆叠、打印模式。
- Token/component ownership: 颜色、间距和圆角由 `scripts/export_summaries.py` 中的共享 `STYLE` 管理。

## Accessibility
- Target standard: WCAG 2.2 AA 的基础可读性与键盘可操作性。
- Keyboard/focus behavior: 所有链接保留语义，使用清晰的 `:focus-visible` 外框。
- Contrast/readability: 正文、弱化文字和强调色在两种主题下保持足够对比；正文不超过舒适阅读宽度。
- Screen-reader semantics: 使用 `main`、`nav`、标题层级、`time` 与描述性 `aria-label`。
- Reduced motion and sensory considerations: `prefers-reduced-motion` 下关闭滚动和过渡动画。

## Responsive behavior
- Supported breakpoints/devices: 360px 起的手机、平板和桌面浏览器。
- Layout adaptations: 手机缩小页边距和标题字号；项目卡片单列；日期导航横向滚动。
- Touch/hover differences: 链接保持至少约 44px 的触摸高度；hover 仅作为增强，不承载必要信息。

## Interaction states
- Loading: 静态页面，无应用级加载状态。
- Empty: 无日期时隐藏日期导航；无项目时导出命令明确报错。
- Error: 静态生成失败由命令行错误返回。
- Success: 链接和日期跳转立即生效。
- Disabled: 当前没有禁用态控件。
- Offline/slow network, if applicable: 页面内联 CSS、无远程资源，可离线完整阅读。

## Content voice
- Tone: 简洁、客观、工程化。
- Terminology: 使用“项目汇总”“按日期”“创建时间”等现有术语。
- Microcopy rules: 按动作或信息命名，避免营销化描述和不必要感叹号。

## Implementation constraints
- Framework/styling system: Python 标准库生成语义 HTML，CSS 内联到每个独立页面。
- Design-token constraints: 使用 CSS 自定义属性集中主题色，不新增构建步骤或依赖。
- Performance constraints: 不加载远程字体、图片、JavaScript 或第三方 CSS。
- Compatibility constraints: 现代桌面与移动浏览器；保留系统浅色/深色偏好。
- Test/screenshot expectations: 导出测试验证关键结构与安全转义；生成后运行全量单元测试和 HTML 静态检查。

## Open questions
- [ ] 未来是否需要跨项目全文搜索；只有项目和日期数量显著增长后再评估。
