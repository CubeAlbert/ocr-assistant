# Current State

**Current Phase:** Phase 2 — 本地模型可行性验证（🔄 in_progress；2.1 已完成，下一步为 2.2）

**Current Task:** 2.2 — 建立参考答案与首轮基线（⬜ pending；尚未开始）

**Current SubTask:** 2.2.1 — 为四张样图建立人工核对的参考转写，标明不确定区域和结构。

**Current Blocker:** None。第二台机器核对按用户安排暂缓；本机 Radeon 880M 加速未验证，属于结论范围限制，不作为 CPU 验证路径的阻塞。

**Next Step:** 等待用户授权后进入 2.2.1，先为四张样图建立人工参考转写；本次不执行 2.2。第二台机器可按 docs/environment.md 中的命令另行核对。

**Important Decisions:**
1. Git、uv/Python 3.12.13 项目配置、虚拟环境、参数化验证脚本和锁文件已建立，三个候选组件已有本机 CPU 最小推理输出；产品 CLI 仍属于 Phase 3。
2. MVP 通过 CLI 手动批量导入截图和照片，以英文文档为主，兼顾表格及少量代码；自动截图翻页属于后续范围。
3. 技术基线为 Python 3.12.13，项目使用 uv 管理依赖；文件内容在虚拟机外本地处理。
4. 优先验证 PaddleOCR-VL + 小型文字模型；同时比较 Qwen3-VL 单模型承担识别和校订的方案，最终模型尚未选定。
5. 第一轮自动整理基本排版并修正常见拼写、OCR 字符混淆、明显空格及断词错误；保存识别初稿和修改记录，保护技术名称及代码标识符。
6. MVP 导出 Markdown；普通表格使用 Markdown 表格，复杂表格计划采用内嵌 HTML 并保留图片；Markdown 转 PDF 留到后续。
7. 多页内容按页、按区域处理并保存进度，最后合并；任务总页数与单次模型上下文分开设计。
8. 已完成四张样图的目视评估及本机 CPU 最小推理，记录了本次运行耗时；人工参考答案、完整准确率/性能基线和资源占用比较尚未完成。
9. CLI 已正式确认为 MVP 入口；核心处理独立于界面，网页或桌面交互界面不作为 MVP 依赖。
10. 第一轮速度优先，允许一定识别误差，文字校订模型仍在 MVP 内。句子级语法和语义属于后续二次校验，例如 It was make by me. 在第一轮保留，第二轮再检查 make 到 made 的修改。
11. 批处理尽量无人值守；记录已发现的问题并集中反馈，不为每个疑点暂停任务。深入检测、可视化核对和必要的人工调整留到后续。
12. 第二台用户报告的 3080 机器核对暂缓，不再阻塞当前 2.1；命令文件已准备好，由用户自行测试核对并反馈。暂缓不代表已验证或取消，见 Decision 12。
13. 当前 Task 2.1 在参数化脚本、当前机器 CPU 验证和复现交接完成的范围内关闭；第二台机器验证按要求暂缓，不阻塞下一步 2.2，见 Decision 13。
14. PaddleOCR-VL 追溯性修正已完成：Paddle 路线显式记录 VL recognition 与 PP-DocLayoutV3 两个模型组件的文件 manifest；actual_device 取自完成推理的子进程，未传 max_new_tokens 时记录为 null。

## Active Context

- Design: [docs/design.md](design.md)
- Plan: [docs/plan.md](plan.md)
- Tasks: [docs/task.md](task.md)
- Decisions: [docs/decision.md](decision.md)
- 当前采用默认文档集合；2026-09-03 实查分支为 master，最新提交为 6ad0fc4（docs: add project agent guidelines），其前为 be07a2b（docs: add project documentation）。本轮编辑前工作区干净；新 session 必须重新检查。
- task.md 是任务状态来源；下方细化步骤与 task.md 的 2.1.1–2.1.8 一一对应。完成拆解不代表完成环境验证。
- plan.md 中“没有 Git 仓库”以及旧文档中的“本次仅文档”描述属于先前快照；Git 以实时检查为准，新 session 的执行范围以届时用户指令为准，不应重复初始化 Git。

## Task 2.1 — 新 session 执行交接

**目标与边界：** 为 2.2 准备可复现的本地模型验证环境，并证明选定的 CPU 或 NVIDIA 路径能完成最小推理。2.1 包括必要的验证脚本与配置；人工参考答案、四张图的完整基线、模型质量/性能排名及最终选型属于 2.2；产品 CLI、批次管理和 Markdown 导出属于 Phase 3。

**执行原则：** 实时状态以 task.md 的标记和本文件最新 checkpoint 为准。第二台机器核对已由用户明确暂缓，当前 2.1 按本机环境和复现交接验收；其后由用户在命令文件可用时自行核对第二台机器。不得将暂缓写成已验证，也不为等待另一台机器中断本机收尾。遇到实际权限限制或必须改变 Python/本地推理等既定边界时，记录证据并说明所需用户操作。

### 2.1.1 恢复仓库与设备核对（✅ 本机完成；第二台暂缓）

- 读取 AGENTS.md、本文件及 task.md 的 2.1；按需读取 design.md 的硬件、候选模型章节和 decision.md 的相关决定。
- 核对分支、未提交修改、已有项目文件及 sample-pic/；保留其他工作和原图，不重复初始化 Git。
- 识别当前可访问的目标机：A 为用户报告的核显/32GB 内存，B 为用户报告的 3080/16GB 显存/32GB 内存；这些均不是硬件实测结论。
- 分机记录系统版本、架构、CPU、实际内存、GPU 精确型号、独立显存与共享内存、驱动版本及是否处于虚拟机。NVIDIA 信息可用 nvidia-smi 核对；无该命令时记录原因，不直接判为没有 GPU。
- **产物/完成条件：** 当前执行机信息和来源已记录；按用户新安排，第二台机器核对单独暂缓，不计入当前 2.1 的关闭条件。命令文件已准备好，由用户自行核对第二台机器的系统、硬件、驱动、框架设备识别及运行结果，反馈后再更新验证范围。

### 2.1.2 检查工具、存储和获取条件（✅ done）

- 检查 uv 和 Python 的现有版本、可执行文件路径、Python 3.12 是否可用；确认 Git 可正常读取仓库。
- 检查工作区、依赖缓存及模型缓存目录的可写性、可用磁盘空间，以及官方包源和模型来源的可达性。
- 根据候选模型实际下载信息估计空间需求；记录缓存位置、已有可复用文件与必要环境变量，不保存凭据。
- **产物/完成条件：** 明确可复用项、缺少项及准备方式，具备后续初始化与下载的条件；问题定位到工具、权限、网络或存储，避免混作模型不兼容。

### 2.1.3 核对候选路线与后端兼容组合（✅ done）

- 查阅执行时的官方安装文档和模型说明，记录来源与日期；核对实际系统、Python 3.12、CPU/NVIDIA、驱动及框架版本的支持关系。
- 首轮范围沿用 design.md：PaddleOCR-VL + Qwen3-4B-Instruct-2507，以及 Qwen3-VL-4B-Instruct；PaddleOCR-VL 的具体版本仍需核对，不将文档候选直接当成可安装版本。
- 列明每条路线的模型标识、后端、包版本、设备、精度/量化及额外组件。优先使用可用路径；核显加速不是前提，CPU 支持也需具体后端证据。
- 检查依赖能否共存；确有冲突时为验证路线保留独立、可复现的环境和命令，说明理由。允许分阶段加载模型，不要求两个模型同时驻留显存。
- **产物/完成条件：** 有依据明确的候选安装组合及实际验证路径；这里只确定验证配置，最终模型选择留到 2.2。兼容性障碍须记录具体版本和错误，不静默更换 Python 基线或改用云端识别。

### 2.1.4 使用 uv 初始化 Python 3.12 项目（✅ done）

- 在现有仓库中建立最小验证项目，固定 Python 3.12，生成 pyproject.toml 和 .python-version，并创建对应虚拟环境。
- 若文件已由其他 session 创建，先检查并沿用；不覆盖现有配置，不为验证阶段引入完整应用骨架或无关框架。
- 确认通过 uv 运行的解释器确为预期版本与路径。
- **产物/完成条件：** 项目配置存在，uv 可运行 Python 3.12；记录实际执行的初始化和运行命令。

### 2.1.5 安装并锁定验证依赖（✅ done）

- 按 2.1.3 的组合安装必要依赖、生成 uv.lock，记录实际解析出的框架版本与软件包来源；独立环境同样记录可复现的依赖配置。
- 检查关键库导入及设备枚举；NVIDIA 路径须由框架实际识别 GPU，不能仅用 nvidia-smi 成功代替框架验证。
- 检查同步与锁文件一致；确保 .venv、缓存、模型权重及运行输出不被纳入 Git，保留 uv.lock 和 .python-version 可纳入版本控制。
- **产物/完成条件：** 必要库可导入、所选设备可访问、依赖可按锁定配置恢复；安装成功不等于模型推理成功。

### 2.1.6 准备候选模型及加载配置（✅ done）

- 从官方来源获取首轮比较所需模型及必要配套组件；逐条记录模型标识、固定 revision 或其他版本标识、文件位置、下载完成情况。
- 记录设备、精度/量化、输入分辨率、上下文或输出上限等实际加载配置；根据可用资源顺序加载和释放模型。
- 输入图片与识别文本在本地处理，原图保持不变；使用独立目录存放测试输出。
- **产物/完成条件：** 为后续比较准备的模型可从记录路径加载，配置完整；下载缺失、加载失败或尚未准备的路线逐项注明，不列为已就绪。

### 2.1.7 执行最小本地推理验证（✅ done）

- 为已准备的路线提供最小可重复命令或验证脚本；优先用 sample-pic/text.png 作为视觉模型单图输入，小型文字模型使用短文本输入。
- 对 PaddleOCR-VL、文字模型和 Qwen3-VL 分别检查：模型成功加载、完成推理、生成非空可读结果、结果保存在独立位置，并记录实际运行设备。
- 保存运行命令、配置、输入路径、输出路径、退出状态及必要错误日志；失败时记录具体原因和后续动作。缺少样图时明确缺口，不能把无法运行写成通过。
- **产物/完成条件：** 在当前执行机上完成所选 CPU 或 NVIDIA 路径的端到端最小推理；各候选组件分别有通过或失败证据。尚未跑通的组件保持未完成，不用 import 成功替代推理验证。
- 本步骤只证明环境能运行；即使输出包含正确词句，也不代表已验证词级校订边界、准确率、速度或复杂表格能力。

### 2.1.8 整理复现说明并保存交接（✅ done）

- 将实测环境、安装与锁定方式、模型版本、缓存/输出位置、必要环境变量、运行命令和结果集中记录到 docs/environment.md（已生成）；不记录密钥或无关机器标识。
- 按锁定配置检查环境同步，在新进程中重新执行必要的最小验证命令，证明说明可复用；无需为此重复下载模型或删除已有环境。
- 逐项核对本机候选准备/推理状态；第二台设备核对单独记录为用户安排的暂缓项，明确恢复条件及负责人，结论限定于已验证机器和后端。
- 收尾已完成：已补齐完整参数化脚本、输入/提示词/加载/生成/输出参数、模型文件 SHA-256 manifest 和新进程推理复现记录；三条路线均有非空输出。
- 同步 task.md 与 current.md，实际发生重要选型变化时追加 decision.md；当前范围的子任务有完成证据后才能将 2.1 标为 done，用户明确暂缓的第二台核对保留独立记录，不伪装为完成。
- **产物/完成条件：** 新 session 可按环境说明复现已通过的路径；任务状态与证据一致。2.1 完成后，下一步为 2.2 的人工参考转写与首轮基线，未经后续指令不继续推进。

**新 session 可直接使用的指令：**

> 使用 project-bootstrap 恢复 OCR Assistant 上下文，读取最新 current.md、task.md 和 environment.md；Task 2.1 已完成，下一步等待授权后进入 2.2，第二台机器可按 environment.md 命令自行核对。

## Checkpoint — 2026-09-03

- 完成：需求和 MVP 边界确认、Python 版本选择、候选架构整理、四张样图目视评估、五份上下文文档初始化；本轮正式确认 CLI，并同步第一轮轻量纠错与后续深入校验的边界。
- 该条记录属于执行前 planning checkpoint；当时 2.1 子任务为 pending，后续 scripted validation checkpoint 已记录实际环境检查、安装、下载和推理。
- 本轮已核对：Git 分支与提交、干净的编辑前工作区、项目仍只有文档与忽略规则；四张样图存在且被 Git 忽略。已修正本文件中的过时 Git 快照。
- 样图：[text.png](../sample-pic/text.png)、[fuzzy-photo.png](../sample-pic/fuzzy-photo.png)、[complex-table.png](../sample-pic/complex-table.png)、[code.png](../sample-pic/code.png)。
- 首要风险：屏幕照片摩尔纹和小字、技术名称被文字模型误改、数字或代码符号错误、多页内容遗漏。
- 样本缺口：真正的复杂表格、多页连续文档及可核对的人工参考答案。
- 当前未知：两台机器的精确型号与系统版本、核显后端兼容性、具体推理后端、CLI 命令契约及最终模型版本。入口形态已确定；剩余事项在后续环境和样本验证中处理。

## Checkpoint — 2026-09-03 (Task 2.1 execution)

- 当前机器环境已建立：Python 3.12.13、uv 项目配置、.venv、pyproject.toml、uv.lock；关键依赖可导入，最终新进程同步通过。
- 已完成本机 CPU 最小验证：PaddleOCR-VL-1.6 约 431.96 秒；Qwen3-4B-Instruct-2507 约 6.682 秒；Qwen3-VL-4B-Instruct 约 103.972 秒。三条路线均有非空输出和独立验证产物。
- 产物说明见 [docs/environment.md](environment.md)，输出位于 validation-output/；原始样图未修改。当前 CPU 证据不代表 GPU 加速、准确率、速度目标、复杂表格效果或最终模型选择。
- 已知未完成：第二台 RTX 3080 机器不可访问；本机 Radeon 880M 的 ROCm/其他加速未确认。2.2 未开始。

## Checkpoint — 2026-09-03 (Second machine deferred)

- 该条记录属于命令文件准备前的历史 checkpoint；第二台机器仍暂缓，现已具备用于用户自行核对的命令，按 Decision 13 不阻塞当前 2.1。
- 状态调整：2.1.1 当前本机范围完成；2.1.8 的复现交接已完成，2.1 已在当前授权范围内关闭；下一步为 2.2，第二台设备仍按安排暂缓。
- 该条记录属于执行前历史 checkpoint；后续 scripted validation checkpoint 已记录实际脚本、依赖、模型推理和验证结果。

## Checkpoint — 2026-09-03 (scripted validation)

- 已新增 scripts/check_environment.py 和 scripts/validate_model.py。前者输出系统、CPU、内存、GPU、Python、依赖和框架设备 JSON；后者按 route 单条运行 PaddleOCR-VL、Qwen3-4B 或 Qwen3-VL，并记录参数、模型文件 SHA-256 manifest、耗时、输出和失败 traceback。
- 三条路线均在当前机器 CPU 上通过脚本验证并产生非空输出；负向模型路径测试返回 exit code 1 并写入失败记录。结果和 run.json 位于 validation-output/，原图未修改。
- 2.1 已完成当前授权范围。第二台用户报告的 RTX 3080 机器按要求暂缓，不阻塞本次收尾；本机 AMD Radeon 880M 加速仍未验证。下一步指向 2.2，2.2 尚未执行。
## Checkpoint — 2026-09-03 (scripted validation and 2.1 completion)

- 已新增 scripts/check_environment.py 和 scripts/validate_model.py；脚本不包含当前用户缓存路径，模型、图片、设备和输出目录均由参数指定。
- 三条路线在当前机器 CPU 上通过脚本运行并产生非空输出；每次运行写 run.json，包含参数、模型文件 SHA-256 manifest、实际设备、耗时、输出和失败信息。不存在模型路径的负向测试返回 exit code 1。
- Task 2.1 已完成当前授权范围，下一步为 2.2；第二台 RTX 3080 机器按用户要求暂缓，由用户使用 docs/environment.md 中的命令自行核对。AMD Radeon 880M 加速仍未验证。

## Checkpoint — 2026-09-03 (Paddle traceability correction)

- 修正 Paddle 路线的默认参数记录：未传 max_new_tokens 时，run.json 的 parameters.max_new_tokens 为 null，命令中也不添加该参数。
- 新增 scripts/paddleocr_child.py；PaddleOCRVL 实际在该子进程中初始化并推理，子进程写入 paddleocr-child.json，父脚本将 actual_device_after_predict 作为 actual_device。
- Paddle 路线现在要求显式提供 PP-DocLayoutV3 目录，并在 run.json 的 model_components.layout_detection 中记录完整 SHA-256 文件清单和 manifest_sha256。
- 修正后的验证通过：CPU 子进程设备为 cpu，子进程返回 0，Markdown 输出非空；记录位于 validation-output/script-paddleocr-vl-corrected/run.json。2.2 仍未执行。
