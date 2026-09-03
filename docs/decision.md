<!-- Read the table of contents, then load the relevant decisions. Append new decisions; do not rewrite history. -->

# Decisions

初始化日期：2026-09-03。记录本次方案讨论和用户确认的选择。模型、性能或框架若仍属于候选，在条目中明确标注。后续按顺序追加新决策；变更既有选择时追加说明，不覆盖历史。

## Table of Contents

- [Decision 1 — Documentation Only](#decision-1--documentation-only)
- [Decision 2 — Manual Image Import MVP](#decision-2--manual-image-import-mvp)
- [Decision 3 — Python and Local Runtime](#decision-3--python-and-local-runtime)
- [Decision 4 — Model Evaluation Routes](#decision-4--model-evaluation-routes)
- [Decision 5 — Automatic Correction with Traceability](#decision-5--automatic-correction-with-traceability)
- [Decision 6 — Markdown and Tables](#decision-6--markdown-and-tables)
- [Decision 7 — Page-based Processing](#decision-7--page-based-processing)
- [Decision 8 — Sample Evidence and Evaluation](#decision-8--sample-evidence-and-evaluation)
- [Decision 9 — CLI Entry Point](#decision-9--cli-entry-point)
- [Decision 10 — Fast First Pass and Deeper Second Pass](#decision-10--fast-first-pass-and-deeper-second-pass)
- [Decision 11 — Unattended Batches and Deferred Review](#decision-11--unattended-batches-and-deferred-review)

### Decision 1 — Documentation Only

**Date:** 2026-09-03

**Context:** 新项目当前只有 sample-pic/，没有上下文文档或 Git 仓库。用户要求整理方案、使用 project-checkpoint 保存，并初始化各个文档文件。

**Decision:** 按 project-bootstrap 模板初始化 docs/current.md、design.md、plan.md、task.md 和 decision.md，再按 checkpoint 规则保存本次进度。当前仅写方案文档，后续 uv 初始化及实现不在本次执行范围。

**Rationale:** 建立可恢复的项目状态，保留已确认范围和下一步，并明确设计、目视评估和实际模型验证之间的区别。用户已明确授权文档初始化，无须再次询问是否创建模板文件。

**Alternatives Considered:**
- 只保留聊天记录：无法为后续会话提供稳定的任务与决策入口。
- 同时初始化 Python、安装模型或实现代码：超出本次仅记录文档的要求。

### Decision 2 — Manual Image Import MVP

**Date:** 2026-09-03

**Context:** 用户需要获取虚拟机中可见的文件内容，输入既有截图，也可能是扫描内容或屏幕照片。

**Decision:** MVP 手动批量导入并排序图片，主要处理英文文档，兼顾表格和少量代码。自动截图和翻页留到后续；几乎没有手写材料，暂不做专门优化。

**Rationale:** 先验证识别与校订质量，再接入自动采集。手动与自动来源可复用后续处理流程。

**Alternatives Considered:**
- MVP 直接自动控制虚拟机：用户明确选择后续实现。
- 通过文件共享或二维码传递原始数据：属于早期讨论的其他路线，本项目当前采用图片识别路线。

### Decision 3 — Python and Local Runtime

**Date:** 2026-09-03

**Context:** 用户指定 Python 3.12，后续使用 uv；可用两台 32GB 内存机器，其中一台核显，另一台为用户报告的 3080、16GB 显存。

**Decision:** 固定 Python 3.12 为技术基线，uv 为后续初始化和依赖管理工具。图片识别和文字校订在虚拟机外本地运行；保留 CPU 验证路径，建议以 3080 机器作为主要模型和批量验证环境。

**Rationale:** 符合用户本地模型方向，并允许先评估现有硬件能力。具体框架、驱动兼容性和核显加速方式待实际环境核对。

**Alternatives Considered:**
- 核显加速作为硬前提：缺少具体型号和后端验证，不能预先承诺。
- 依赖云端模型：不属于当前本地处理方案。

### Decision 4 — Model Evaluation Routes

**Date:** 2026-09-03

**Context:** 用户接受一个 OCR 模型加一个小型文字模型，也希望比较单个多模态模型完成两步的可能性。

**Decision:** 优先验证 PaddleOCR-VL + Qwen3-4B-Instruct-2507，并比较 Qwen3-VL-4B-Instruct 单模型方案；有明确需要时再比较 8B 或其他候选。当前不锁定最终模型、量化方式及推理后端。

**Rationale:** 双模型路线便于分别评估文档结构识别与文字校订；单模型路线可能简化主要模型部署，但实际质量和成本必须由同样本对比决定。

**Alternatives Considered:**
- 直接认定单模型更强：缺少本项目样本实测。
- 一开始部署多套 OCR、多个校订模型：增加复杂性，尚无证据证明必要。
- 把模型再次检查视为正确性证明：相同模型可能重复同一错误，仍需原图和参考答案。

### Decision 5 — Automatic Correction with Traceability

**Date:** 2026-09-03

**Context:** 用户希望自动修复类似 dup1icate 到 duplicate 的明显 OCR 错误，且不希望每处都手动确认。样图同时暴露技术名称、数字与代码被误改的风险。

**Decision:** 正文中上下文明确的 OCR 错误可自动修正，同时保存初稿、修改差异和来源。技术名称、专有词、数字、表格数据及代码采用相应保守规则；无法确认时标记并提供原图或局部复核。

**Rationale:** 自动校订应减少人工负担，同时能识别并撤销新增错误。恢复原文与润色、补写内容具有不同目标。

**Alternatives Considered:**
- 每次修改都要求人工批准：与用户希望自动修正常见错误的要求不符。
- 全文按普通英文拼写纠错：会破坏代码标识符、专业名称或数据。
- 覆盖识别初稿：无法区分 OCR 错误和校订新增错误。

### Decision 6 — Markdown and Tables

**Date:** 2026-09-03

**Context:** 用户选择 Markdown 输出并要求后续增加 PDF；材料可能包含普通表格与复杂表格。

**Decision:** MVP 导出 Markdown。普通表格使用 Markdown 表格；复杂表格采用内嵌 HTML 的设计，并保留对应图片以便核对。无法可靠恢复结构时明确保留图片和疑点。Markdown 转 PDF 属于后续任务。

**Rationale:** 保持文本易读、可编辑，并处理常见 Markdown 表格无法直接表示合并单元格的问题。实际预览器和未来 PDF 渲染兼容性需要验证。

**Alternatives Considered:**
- 所有表格都强制转成普通 Markdown：可能丢失层级和合并关系。
- 只输出图片：不满足文档内容可读取和编辑的主要目标。
- MVP 同时实现 PDF：用户明确指定后续增加。

### Decision 7 — Page-based Processing

**Date:** 2026-09-03

**Context:** 每次页数没有固定上限，可能达到几十页；本地模型资源有限，并且输入可能包含小字和复杂区域。

**Decision:** 采用逐页、逐区域处理和有限上下文，保存进度及中间结果，支持恢复和单页重试，最后合并 Markdown。跨页结构和重复内容依据来源与布局处理，不能只按相似文字推断。

**Rationale:** 使文档总页数与单次推理内存解耦，降低长任务失败后的重复工作，保留小字识别和局部复核的空间。

**Alternatives Considered:**
- 一次送入全部页面：可能造成缩图损失、上下文截断及资源超限。
- 把任何页数都可高质量处理作为承诺：缺少批量样本和目标硬件实测。

### Decision 8 — Sample Evidence and Evaluation

**Date:** 2026-09-03

**Context:** 用户提供四张样图；目前只完成目视查看，未安装或运行候选模型。complex-table.png 实际为无合并单元格的 5 列、6 行数据表格。

**Decision:** 将四张图作为首轮评估输入，后续建立人工参考答案并比较初稿和校订结果。明确记录模糊区域、摩尔纹、技术名称、前导零和代码符号风险。复杂表格与多页能力在补充样本后验证。

**Rationale:** 不能把目视可读、文件名称或官方模型基准当成本项目实测效果。模糊样本的正确处理包括暴露无法确认的内容。

**Alternatives Considered:**
- 现在宣布某模型满足需求：没有实际测试结果支持。
- 只评价输出是否通顺：无法发现漏行、数字错误或合理但错误的补写。
- 将现有表格视为覆盖全部复杂表格：未覆盖多层表头、合并单元格及跨页结构。

### Decision 9 — CLI Entry Point

**Date:** 2026-09-03

**Context:** 用户讨论未来自动滚动、外部截图和批量处理后，明确确认 CLI 作为入口。此前网页或桌面 UI 仍为未定选项。

**Decision:** MVP 正式采用 CLI，接收图片来源和页面顺序，提供任务启动、进度及批次反馈。处理核心独立于界面；完整网页、桌面窗口或内置交互编辑器不作为 MVP 依赖。

**Rationale:** CLI 适合批量运行和未来自动采集，能减少必须人工点击的环节。原图与修改记录可以保存为文件，后续再按需增加复核报告或交互能力。

**Alternatives Considered:**
- 将完整本地网页作为第一入口：增加交互开发和维护，当前需求更重视自动批处理。
- 将识别和校订逻辑绑定在界面事件中：不利于 CLI、自动采集和后续核对复用核心流程。

### Decision 10 — Fast First Pass and Deeper Second Pass

**Date:** 2026-09-03

**Context:** 用户明确第一轮要快，允许牺牲部分准确性，并澄清文字校订模型仍在 MVP 内；第一轮只处理简单词级错误，后续才做深入语法与语义检查。

**Decision:** 第一轮为快速 OCR、基本排版和轻量词级校订，自动修正 dup1icate 到 duplicate、becuase 到 because 等问题。It was make by me. 中 make 本身是合法单词，第一轮保留，后续二次校验再检查被动语态并提出 made 的修改。二次校验独立读取已保存结果，可先复用文字模型，不预先要求增加第三个模型。

**Rationale:** 将产出初稿的速度和深入内容检查分开，既保留简单自动纠错，又避免第一轮承担全面语法语义理解。原图、识别初稿和修改记录为后续核对提供依据。

**Scope Update:** 本条细化并调整 Decision 4、5、8 的当前实现与验收范围。候选模型仍待实测，第一轮优先评估总耗时和词级校订增量成本；深入语法语义校验不再是 MVP 必需项，初稿允许残余内容错误。

**Alternatives Considered:**
- 把文字模型整体移出 MVP：用户明确否定，MVP 仍需要轻量文字校订。
- 第一轮就修复句子语法、语义并反复视觉检查：不符合速度优先和分阶段处理的要求。
- 把语法通顺视为内容准确：日期、数字或否定词的误识别仍可能产生语法正确的错误内容，必要时仍需对照原图。

### Decision 11 — Unattended Batches and Deferred Review

**Date:** 2026-09-03

**Context:** 用户希望自动化流程避免频繁人工介入，并接受先处理一遍、后续再检测和人工核对。

**Decision:** 第一轮尽量无人值守；保留进度、修改差异、原图对应关系、失败页和已发现问题，批次结束集中反馈。单页技术失败可有限重试并允许其他页继续，持续性任务故障则保存进度并明确停止或暂停。第一轮不要求检测出所有内容错误，深入疑点检测、局部重识别和人工调整移到后续二次校验。

**Rationale:** 防止困难照片拖住整个批次，同时避免失败页面被静默当成已完成。分开记录初稿生成、存在失败页和后续已校验等状态，便于恢复与复核。

**Scope Update:** 调整 Decision 5、7、8 对 MVP 交互和质量检查的解释：保留来源和已有错误信息是第一轮要求，完整可视化复核、逐项人工确认及全面疑点覆盖不是第一轮验收门槛。

**Alternatives Considered:**
- 每遇到疑点就停下来询问用户：造成频繁介入，不符合批处理目标。
- 对每页运行多模型或多轮检查直到一致：增加首轮成本，仍不能保证内容正确。
- 无论失败与否都报告整批内容已校验：混淆处理状态与内容质量，不利于后续定位和恢复。
