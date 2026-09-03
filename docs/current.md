# Current State

**Current Phase:** Phase 2 — 本地模型可行性验证（⬜ pending；后续工作，本次不启动）

**Current Task:** 2.1 — 初始化验证环境

**Current SubTask:** 在后续实施开始时核对两台目标机器的系统、CPU、GPU、显存及 Python 3.12 兼容性

**Current Blocker:** None。当前没有已确认的技术阻塞；运行速度、识别效果及核显加速能力尚未实测。

**Next Step:** 本次文档更新完成后停止。收到后续开始实施的指令时，先核对目标环境，再使用 uv 初始化 Python 3.12 项目；按 CLI 批处理、速度优先和轻量词级校订的目标建立样图基线并比较候选模型。

**Important Decisions:**
1. 当前只初始化和记录方案文档；尚未初始化 Git、uv、Python 运行环境，也未下载或运行本地候选模型。
2. MVP 通过 CLI 手动批量导入截图和照片，以英文文档为主，兼顾表格及少量代码；自动截图翻页属于后续范围。
3. 技术基线为 Python 3.12，后续使用 uv 管理项目和依赖；文件内容在虚拟机外本地处理。
4. 优先验证 PaddleOCR-VL + 小型文字模型；同时比较 Qwen3-VL 单模型承担识别和校订的方案，最终模型尚未选定。
5. 第一轮自动整理基本排版并修正常见拼写、OCR 字符混淆、明显空格及断词错误；保存识别初稿和修改记录，保护技术名称及代码标识符。
6. MVP 导出 Markdown；普通表格使用 Markdown 表格，复杂表格计划采用内嵌 HTML 并保留图片；Markdown 转 PDF 留到后续。
7. 多页内容按页、按区域处理并保存进度，最后合并；任务总页数与单次模型上下文分开设计。
8. 已完成四张样图的目视评估，尚无本地模型准确率、耗时或资源占用的测试结果。
9. CLI 已正式确认为 MVP 入口；核心处理独立于界面，网页或桌面交互界面不作为 MVP 依赖。
10. 第一轮速度优先，允许一定识别误差，文字校订模型仍在 MVP 内。句子级语法和语义属于后续二次校验，例如 It was make by me. 在第一轮保留，第二轮再检查 make 到 made 的修改。
11. 批处理尽量无人值守；记录已发现的问题并集中反馈，不为每个疑点暂停任务。深入检测、可视化核对和必要的人工调整留到后续。

## Active Context

- Design: [docs/design.md](design.md)
- Plan: [docs/plan.md](plan.md)
- Tasks: [docs/task.md](task.md)
- Decisions: [docs/decision.md](decision.md)
- 当前采用默认文档集合；项目目录尚不是 Git 仓库，没有分支或提交历史可用于路由。

## Checkpoint — 2026-09-03

- 完成：需求和 MVP 边界确认、Python 版本选择、候选架构整理、四张样图目视评估、五份上下文文档初始化；本轮正式确认 CLI，并同步第一轮轻量纠错与后续深入校验的边界。
- 本次操作范围：docs/ 下的 Markdown 文档。
- 样图：[text.png](../sample-pic/text.png)、[fuzzy-photo.png](../sample-pic/fuzzy-photo.png)、[complex-table.png](../sample-pic/complex-table.png)、[code.png](../sample-pic/code.png)。
- 首要风险：屏幕照片摩尔纹和小字、技术名称被文字模型误改、数字或代码符号错误、多页内容遗漏。
- 样本缺口：真正的复杂表格、多页连续文档及可核对的人工参考答案。
- 当前未知：两台机器的精确型号与系统版本、核显后端兼容性、具体推理后端、CLI 命令契约及最终模型版本。入口形态已确定；剩余事项在后续环境和样本验证中处理。
