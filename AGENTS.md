# OCR Assistant

通过 CLI 在虚拟机外本地处理清晰截图和扫描图，快速生成经过轻量词级校订、可追溯到原图的 Markdown 初稿。相机拍摄的屏幕或文档照片已移出 MVP。

## 1. 快速开始

### 恢复项目上下文

1. 先读 [docs/current.md](docs/current.md)，确认当前阶段、任务和下一步。
2. 按 current.md 指定的路径加载相关设计、计划、任务和决策；未指定时使用 docs/ 下的默认五份文件。只按需读取相关章节。
3. 检查实际文件、当前分支和工作区状态。Git 已由用户初始化并完成初始提交；旧文档中“尚未初始化 Git”的快照已过时，以实时状态为准。
4. 根据用户当前请求确定工作范围。既定需求和已授权的常规操作直接执行，避免重复确认；记录在计划中的任务不等于已实现或已验证。

### 环境要求

- **已选定技术基线**：Python 3.12.13，项目已使用 uv 初始化并管理依赖。
- **当前阶段**：Phase 2 / Task 2.2 进行中；2.2.1–2.2.3 已完成，下一步 2.2.4 待用户另行指令。正式基线使用 text、complex-table、code，fuzzy-photo 已延期。
- **目标设备**：两台 32GB 内存机器，一台核显，另一台为用户报告的 3080、16GB 显存。具体硬件、系统和后端兼容性需要实测。
- **运行方式**：在虚拟机外本地推理；当前机器已验证 CPU 路径，AMD Radeon 880M 加速、CUDA/NVIDIA 路径和第二台 3080 机器仍未验证；最终模型、后端和量化配置尚未选定。

### 环境配置

项目使用 uv 管理 Python 3.12.13、虚拟环境和锁定依赖。依赖、模型目录、输入图片、设备和输出目录均通过命令行或环境变量传入，不把用户缓存路径写入脚本。详细复现命令见 docs/environment.md。

### 构建与运行

当前尚无产品 CLI。Task 2.1 的环境与模型验证入口是 scripts/check_environment.py 和 scripts/validate_model.py；Task 2.2 的单样本编排与离线评分入口是 scripts/run_baseline.py 和 scripts/evaluate_baseline.py。

~~~powershell
uv sync --locked --index-strategy unsafe-best-match
uv run python scripts/check_environment.py --output-dir validation-output/environment-script
uv run python scripts/validate_model.py --help
~~~

模型验证一次只运行一条路线，并将 run.json、结果和必要日志写入被 Git 忽略的 validation-output/。

### 测试

当前使用标准库 unittest 和脚本化 smoke 验证。Task 2.2.1–2.2.3 已有 10 个单元测试；脚本编译、环境检查、三条候选路线的当前机器 CPU 推理和故意失败路径也已验证。失败路径必须返回非零退出码，非空输出不能单独作为质量通过结论。

## 2. 项目结构

~~~text
ocr-assistant/
├── AGENTS.md          — 项目级协作指引
├── .gitignore         — Python/uv 本地产物、样图与验证输出忽略规则
├── .python-version    — uv 固定的 Python 主版本
├── pyproject.toml     — 项目依赖和 uv 配置
├── uv.lock            — 依赖锁定文件
├── scripts/           — 环境检查和三路线模型验证脚本
├── docs/
│   ├── current.md     — 当前状态、活动文档路由和下一步
│   ├── design.md      — 当前设计、MVP 边界和样图评估
│   ├── plan.md        — 阶段目标、依赖和验收条件
│   ├── task.md        — Phase → Task → SubTask 状态
│   ├── decision.md    — 顺序编号、追加维护的决策历史
│   └── environment.md — 实测环境和复现命令
├── sample-pic/        — 本地样图，已被 Git 忽略，不随仓库分发
└── validation-output/ — 本地验证结果，已被 Git 忽略
~~~

### 文档维护

- current.md 是上下文入口；task.md 是任务状态来源；design.md 描述当前方案，decision.md 保留历史选择。
- 变更决策时追加 decision.md 条目，不覆盖旧决策；当前设计和快照需要反映已经确认的新结论。
- 设计完成、代码实现、自动验证和用户机器实测分别记录，不能相互替代。
- 文档使用中文说明，保留英文术语、模型名及原文示例。

### 源码树结构

当前验证脚本位于 scripts/；PaddleOCR 路线由 scripts/paddleocr_child.py 在实际推理子进程中执行并写设备证据。产品 CLI 和批处理核心仍属于 Phase 3，不能把验证脚本当成产品入口。

### 依赖与代码生成

pyproject.toml、uv.lock 和 .python-version 已生成；依赖同步及可复现命令以 docs/environment.md 为准。

### 本地文件与版本控制

- sample-pic/ 仅用于本地验证，缺少该目录时不能假设新检出的仓库自带样图；不强制加入 Git。
- 保留原始图片，校正图和识别结果使用独立产物，不覆盖来源。
- uv.lock、.python-version 和 pyproject.toml 应纳入版本控制；虚拟环境、模型缓存、sample-pic/ 和 validation-output/ 继续按 .gitignore 排除。

## 3. 架构与编码规范

### 已确认的产品边界

- **MVP 入口为 CLI**；处理核心独立于界面，网页或桌面应用不是 MVP 依赖。
- **MVP 输入范围为清晰截图和扫描图**；相机照片识别属于后续能力，fuzzy-photo 不参与当前 CER、模型选型或 MVP 验收。
- **第一轮速度优先**：手动批量导入 → 快速 OCR 和基本排版 → 轻量文字校订 → Markdown 初稿。允许一定识别误差。
- **文字校订模型仍在 MVP 内**：仅修正常见拼写、OCR 字符混淆、明显空格与断词，例如 dup1icate 到 duplicate。
- **深入校验留到后续**：It was make by me. 的 make 是合法单词，第一轮保留；被动语态改为 made、句子语法与上下文语义检查属于二次校验。
- 保护专业名称、代码标识符、数字和前导零；不把不常见词一律改成常用词，也不凭常识补出图片未显示的内容。
- 多页材料按页或区域处理，保存页序、进度、原图对应关系、识别初稿、修改记录及失败页；批次反馈集中提供，避免频繁人工介入。
- 普通表格输出 Markdown；复杂表格可保留识别器产生的 HTML 和对应图片，不为完善单个表格阻塞整个批次。
- 自动截图翻页、深入语法语义复核、按需人工核对和 Markdown 转 PDF 属于后续能力。
- 模型候选与具体比较范围见 design.md；候选名称不代表已经部署或测试，不能把目视评估或官方基准写成本项目实测结果。

### 代码风格与质量

- **核心原则**: 与已有代码风格保持一致。当某个文件的写法与你准备采用的写法不同时，在偏离之前先弄清楚*为什么* — 这通常是有意为之的工程决策，而非风格偏好。
- 当前已有环境/模型验证脚本，尚未建立产品 CLI 或格式化工具；后续沿用实际项目配置，避免为文档维护安装无关依赖。
- 功能验证优先覆盖影响用户结果的行为：词级校订边界、页序与恢复、数字及代码保留、修改可追溯性。
- 性能评估分别记录 OCR、轻量校订和总耗时；速度、准确性、资源占用均用实际样本测量。

### Lint 与格式化

当前尚未配置独立的格式化或 lint 工具；脚本先保持标准库优先、可直接由 Python 3.12 执行的风格。

### 测试规范

当前使用 Python 标准库 unittest，不额外引入测试框架。可执行验证包括：
- uv run python -m unittest discover -s tests -v
- scripts/check_environment.py 的 JSON 环境报告
- scripts/validate_model.py 的三条单路线 smoke 推理
- 不存在模型路径的负向测试，要求 run.json 标记 failed 且退出码为 1

### 错误处理与日志

validate_model.py 无论成功或失败都写 run.json；PaddleOCR 子进程额外写 stdout/stderr 和 paddleocr-child.json。模型及其流水线组件的 SHA-256 manifest、实际设备、参数、输入、输出、耗时和 traceback 保存在记录中；空输出、缺少子进程设备证据和子进程失败均返回非零。

### 资源生命周期与所有权

大模型按路线单独加载和退出，不要求同时驻留。原图只读，模型缓存和 validation-output/ 为本地忽略产物，不能覆盖来源图片。

### 跨平台合规

Windows x64 CPU 路径已在当前机器实测。CUDA/NVIDIA、AMD Radeon 880M 加速和第二台机器仍须由实际设备验证；脚本不把当前用户缓存路径写死。

## 4. 评审与合入流程

### 提交前

1. 检查 Git 状态与差异，仅暂存当前任务涉及的文件，保持 sample-pic/ 不受版本控制。
2. 文档变更检查本地链接、阶段范围、任务状态、决策编号及空白错误；无需为纯文档变更新建测试框架。
3. 实现代码后运行与变更有关且已配置的验证，说明实际执行结果和未验证部分。
4. 用户要求提交或推送时执行相应操作；创建本指引不自动产生提交或推送。

### 分支与提交

- 当前可观察到 master 分支和 docs: add project documentation 初始提交；尚不足以推断强制分支、PR 或提交命名规则。
- 不为例行文档编辑擅自重建 Git、切换分支或修改全局 Git 配置。

<!--
### 分支与 PR 命名约定
尚未约定强制格式；形成约定后补充。

### Code Review 工作流
尚无项目专用评审工具或脚本；实际采用后补充。
-->

<!--
## 5. 持续集成 (CI)

当前没有 CI 配置、面板或本地模拟命令。
建立 CI 后填写真实配置路径、验证步骤和排错方式。
-->

## 6. 核心原则

1. **不要提交未经测试的代码。** 如果你没有运行过测试，那它就是不能用的。
2. **实事求是。** 诚实告知完成了什么、哪些确实能工作。如实记录局限性。
3. **先读再写。** 在改变已有代码之前，先理解它为什么要这样写。
4. **治本而非治标。** 不要对 Bug 报告中或 AI 建议的快速修复方案照单全收 — 确认它确实解决了正确的架构层级问题。
