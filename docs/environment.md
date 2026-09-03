# 本地模型验证环境

> 记录日期：2026-09-03
> 当前范围：Phase 2 / Task 2.1。本文只记录实际环境、安装、模型准备和最小推理证据；不代表已完成模型质量基线或最终选型。

## 1. 当前执行机

本次 session 能访问到一台 Windows 主机，硬件实际信息如下。其“核显、约 32GB 内存”的特征与设计中的机器 A 相符，但机器编号仍以用户后续确认或更完整资产信息为准。

| 项目 | 实测值 | 来源/说明 |
| --- | --- | --- |
| 系统 | Windows 10 专业版，10.0.19045，x64 | `Win32_OperatingSystem`、Python platform |
| 主机 | ASUS Adol 14 M5451GADOL | `Win32_ComputerSystem` |
| CPU | AMD Ryzen AI 9 H 465，10 cores / 20 threads | `Win32_Processor` |
| 内存 | 31.15 GB | `Win32_ComputerSystem.TotalPhysicalMemory` |
| GPU | AMD Radeon(TM) 880M Graphics，驱动 32.0.31007.5012 | `Win32_VideoController` |
| GPU 类型 | 集成显卡；CIM `AdapterRAM` 为 512 MiB，不将其当作独立显存结论 | 硬件枚举 |
| NVIDIA | 未找到 `nvidia-smi` | 命令查找结果；不能据此否定另一台机器有 NVIDIA |
| CUDA/框架 GPU | PyTorch `cuda_available=False`、device_count=0；Paddle `compiled_with_cuda=False`、place=`cpu` | 实际导入和设备枚举 |
| 虚拟机 | `HypervisorPresent=False`；主机型号为 ASUS 实体机型 | `Win32_ComputerSystem`；本记录按虚拟机外本地运行处理 |
| D 盘 | 可用约 619.49 GB | `Get-PSDrive D` |

第二台用户报告的机器（3080、16GB 显存、32GB 内存）未核对；用户已明确暂缓，命令文件已准备好，由用户自行测试核对并反馈。该项不再作为当前 2.1 的关闭前提，仍不能写成已验证。

样图已确认存在且未修改：`sample-pic/text.png`、`fuzzy-photo.png`、`complex-table.png`、`code.png`。本地运行输出位于被 Git 忽略的 `validation-output/`。

## 2. 工具与 Python

| 项目 | 实测值 |
| --- | --- |
| uv | `0.11.21`，WinGet 安装路径下的 `uv.exe` |
| 系统 Python | `3.14.5`，`C:\Python314\python.exe`；不作为本项目解释器 |
| Python 3.12 | uv 安装 `3.12.13` |
| 项目解释器 | `D:\Projects\ocr-assistant\.venv\Scripts\python.exe`，Python `3.12.13`，AMD64 |
| Git | `2.54.0.windows.1` |

已执行的初始化命令：

```powershell
uv python install 3.12
uv init --bare --python 3.12
uv python pin 3.12
uv venv --python 3.12
uv run python -c "import sys,platform; print(sys.executable); print(sys.version); print(platform.platform()); print(platform.machine())"
```

项目配置为 Python `>=3.12`，实际 pinned 文件为 `.python-version` 中的 `3.12`。

## 3. 已安装依赖

当前 `pyproject.toml` 顶层依赖与锁定版本：

- `paddlepaddle==3.2.1`
- `paddleocr[doc-parser]>=3.7.0`，解析到 `3.7.0`
- `torch>=2.14.0`，解析到 `2.14.0+cpu`
- `torchvision>=0.29.0`，解析到 `0.29.0`
- `transformers>=4.57.0`，解析到 `5.16.1`
- `accelerate>=1.14.0`，解析到 `1.14.0`
- `qwen-vl-utils==0.0.14`
- `python-docx==1.2.0`

`python-docx` 是 PaddleOCR CLI 保存 `docx` 结果时发现缺失后补充的依赖。`qwen-vl-utils` 初次导入还发现缺少 `torchvision`，补齐后 `transformers`、`accelerate` 和 `qwen_vl_utils` 均可导入。

为同时使用 PyPI 和 Paddle 官方 CPU index，项目保留了以下配置；`paddlepaddle` 明确绑定到 `paddle-cpu`，其他包从默认 PyPI 解析，`index-strategy` 固定为当前实际可复现的 `unsafe-best-match`：

```toml
[tool.uv]
index-strategy = "unsafe-best-match"

[[tool.uv.index]]
name = "paddle-cpu"
url = "https://www.paddlepaddle.org.cn/packages/stable/cpu/"

[tool.uv.sources]
paddlepaddle = { index = "paddle-cpu" }
```

验证命令及结果：

```powershell
uv tree --depth 1
uv lock --check
uv run python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.device_count())"
uv run python -c "import paddle; print(paddle.__version__, paddle.is_compiled_with_cuda(), paddle.get_device())"
uv run python -c "import paddleocr; print(getattr(paddleocr, '__version__', 'unknown'))"
uv run python -c "import transformers, accelerate, qwen_vl_utils; print(transformers.__version__, accelerate.__version__)"
```

实际结果：锁文件一致；Paddle `3.2.1 / False / cpu`，PaddleOCR `3.7.0`，PyTorch `2.14.0+cpu / False / 0`，Transformers `5.16.1`，Accelerate `1.14.0`，Qwen 工具导入成功。

## 4. 缓存与输出

- uv 缓存环境变量：`UV_CACHE_DIR=D:\Files\Repo\Python\uv-cache`。
- Hugging Face 缓存：`C:\Users\Albert\.cache\huggingface\hub`。
- PaddleX 官方模型缓存：`C:\Users\Albert\.paddlex\official_models`。
- ModelScope 下载缓存目标：`D:\Files\Repo\Python\modelscope-cache`。
- D 盘有约 619.49 GB 可用；工作区和缓存目录具备当前用户可访问权限。
- `validation-output/` 已加入 `.gitignore`；原图仍在 `sample-pic/`，没有被覆盖。

## 5. 官方资料与验证组合

本次以 2026-09-03 访问到的官方资料为准：

- PaddleOCR-VL 使用、硬件矩阵和手动安装：[PaddleOCR-VL Usage Tutorial](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PaddleOCR-VL.html)。x64 CPU 的 PaddlePaddle 本地路径受支持，手动安装文档验证 Python 3.9–3.13，使用 PaddlePaddle 3.2.1+；vLLM/SGLang/FastDeploy 不原生运行于 Windows。
- AMD 结论：[PaddleOCR-VL AMD GPU Usage Tutorial](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PaddleOCR-VL-AMD-GPU.html)。官方说明 AMD 路线已在 MI300X 验证，其他 AMD GPU 兼容性尚未确认；因此本机 Radeon 880M 不按已验证 GPU 路径记录，先走 CPU。
- Qwen3-VL 代码和安装：[QwenLM/Qwen3-VL](https://github.com/QwenLM/Qwen3-VL)。要求 `transformers>=4.57.0`，并建议中国大陆用户用 ModelScope 获取 checkpoint。
- 文字校订模型：[Qwen3-4B-Instruct-2507 model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)。本次按官方 Transformers 直接加载示例使用 `Qwen/Qwen3-4B-Instruct-2507`。
- Python 管理：[uv Installing and managing Python](https://docs.astral.sh/uv/guides/install-python/)。`uv python install 3.12` 是官方记录的指定版本安装方式。

当前验证组合：

| 路线 | 模型/引擎 | 设备与配置 | 状态 |
| --- | --- | --- | --- |
| 文档解析 | PaddleOCR-VL-1.6（完整 pipeline，含 PP-DocLayoutV3）/ PaddlePaddle | `cpu`，`fp32` 默认，单图 | 已完成最小推理 |
| 词级校订 | Qwen3-4B-Instruct-2507 / Transformers | CPU，短文本，`max_new_tokens=32` | 已完成最小推理 |
| 单模型视觉对比 | Qwen3-VL-4B-Instruct / Transformers | CPU，PIL RGB `text.png`，`max_new_tokens=64` | 已完成最小推理 |

## 6. PaddleOCR-VL CPU 最小验证

执行命令：

```powershell
uv run paddleocr doc_parser -i "D:\Projects\ocr-assistant\sample-pic\text.png" --device cpu --save_path "D:\Projects\ocr-assistant\validation-output\paddleocr-text"
```

第一次运行下载了官方缓存模型 `PP-DocLayoutV3` 和 `PaddleOCR-VL-1.6`，并在保存阶段因缺少 `docx` 退出；错误为 `ModuleNotFoundError: No module named 'docx'`。补充 `python-docx==1.2.0` 后使用相同命令重跑，模型命中缓存，退出码为 0。

第二次完整结果：

- 输入：`text.png`，1105×1581。
- 实际处理时间：`431959.553 ms`，约 431.96 秒。
- 输出：20 个布局/解析块，非空；模型输出含标题和正文块。
- 保存文件：
  - `validation-output/paddleocr-text/text.md`
  - `validation-output/paddleocr-text/text_res.json`
  - `validation-output/paddleocr-text/text_layout_det_res.png`
  - `validation-output/paddleocr-text/text.docx`
- 该结果证明当前 Windows + Python 3.12 + PaddlePaddle CPU 路径能完成模型加载、单图推理和本地保存；不证明识别准确率、速度目标、复杂表格效果或最终模型选型。

## 7. Qwen 当前进度

第一次直接从 Hugging Face 加载文字模型时，元数据下载后长时间没有权重进展，已中止；未把它记录为模型兼容失败。按 Qwen 官方仓库建议，随后执行：

```powershell
uv run python -c "from modelscope import snapshot_download; print(snapshot_download('Qwen/Qwen3-4B-Instruct-2507', cache_dir='D:/Files/Repo/Python/modelscope-cache'))"
```

ModelScope 已完成下载同一官方模型的 14 个文件，revision 记录为 `master`，并已用返回的本地目录完成短文本校订；加载/总耗时、设备、非空结果及退出码均已记录。

Qwen3-VL-4B-Instruct 已单独下载并完成视觉输入验证，使用同一张 `text.png`，未用文字模型结果替代。

## 8. 未完成项

- 第二台 3080 机器的系统、驱动、显存、框架设备识别和推理：暂缓；命令文件已准备好，由用户自行测试核对（Decision 13）。
- 本机 AMD Radeon 880M 的 GPU/ROCm 加速尚未确认；当前仅有 CPU 证据。
- 当前 2.1.8 已完成：scripts/check_environment.py、scripts/validate_model.py、SHA-256 manifest、三条脚本化推理和新进程复现命令均已记录。
- 四张样图人工参考答案、质量/性能排名和最终选型属于 2.2，本轮不提前执行。

## 9. Qwen 验证收尾

- 文字模型：Qwen/Qwen3-4B-Instruct-2507，ModelScope revision `master`，本地路径为 D:/Files/Repo/Python/modelscope-cache/models/Qwen--Qwen3-4B-Instruct-2507/snapshots/master；Transformers CPU 加载，dtype=auto，max_new_tokens=32。加载约 2.525 秒，总耗时约 6.682 秒，退出码 0，结果为 This is a duplicate record.，保存于 validation-output/qwen3-text/result.txt。
- 视觉模型：Qwen/Qwen3-VL-4B-Instruct，ModelScope revision `master`，本地路径为 D:/Files/Repo/Python/modelscope-cache/models/Qwen--Qwen3-VL-4B-Instruct/snapshots/master；Qwen3VLForConditionalGeneration + AutoProcessor，CPU 加载，dtype=auto，max_new_tokens=64。加载约 1.246 秒，总耗时约 103.972 秒，退出码 0，结果非空，保存于 validation-output/qwen3-vl-text/result.txt。
- 初次使用 file URI 传入 RGBA PNG 时，Transformers/torchvision 自动解码报 Unsupported image file；PIL 已确认原图有效，改为 PIL RGB 对象后验证通过。原图未修改。
- 最终新进程复核：uv lock --check 通过；uv sync --locked --index-strategy unsafe-best-match 通过；Python 3.12.13、Torch 2.14.0+cpu、PaddlePaddle 3.2.1、PaddleOCR 3.7.0、Transformers 5.16.1、Accelerate 1.14.0、qwen-vl-utils 和 python-docx 均可导入；Torch 未识别 CUDA 设备，Paddle 当前为 cpu。
- 实际推理命令均以 `uv run python -c` 执行：文字模型调用 `AutoTokenizer.from_pretrained(local_path, local_files_only=True)`、`AutoModelForCausalLM.from_pretrained(local_path, dtype=auto, device_map=cpu, local_files_only=True)`、`apply_chat_template` 和 `generate`；视觉模型调用 `AutoProcessor.from_pretrained(local_path, local_files_only=True)`、`Qwen3VLForConditionalGeneration.from_pretrained(local_path, dtype=auto, device_map=cpu, local_files_only=True)`、`apply_chat_template` 和 `generate`，两者均将结果写入上述 validation-output 路径。
## 9.1 Paddle 追溯性修正

针对初次脚本记录的审查已完成修正：

- Paddle 路线未传入 max_new_tokens 时，run.json 的 parameters.max_new_tokens 记录为 null；只有显式传参时才会进入子进程命令。
- PaddleOCR-VL 现在在独立的 paddleocr_child.py 子进程中执行。子进程在 pipeline 初始化后和推理完成后写入 actual_device_after_predict，父脚本只接受该字段作为 actual_device，不再用父进程的 Paddle 状态代替。
- Paddle 路线要求显式传入 PP-DocLayoutV3 目录；run.json 的 model_components.layout_detection 保存该目录的完整文件 SHA-256 清单和 manifest_sha256。
- 修正后的成功记录位于 validation-output/script-paddleocr-vl-corrected/run.json，CPU 子进程设备为 cpu，输出非空。

## 10. 参数化脚本与直接复现

### 前置条件

- 在项目根目录执行；Python 3.12 环境已经由 uv 创建。
- 依赖已锁定在 pyproject.toml 和 uv.lock；首次使用先执行 uv sync --locked --index-strategy unsafe-best-match。
- 模型必须先准备到本机目录。脚本不包含任何用户缓存路径；model-path、image、device 和 output-dir 全部由命令行传入。
- 输出目录应使用被 Git 忽略的 validation-output/；脚本不会修改输入图片。

### 环境检查

~~~powershell
uv run python scripts/check_environment.py --output-dir validation-output/environment-script
~~~

脚本同时向终端输出 JSON，并在指定目录写 environment.json。报告包含系统、CPU、物理内存、Windows GPU 枚举、Python 解释器、顶层依赖版本、PyTorch CUDA 识别结果和 Paddle 当前设备。缺少必要依赖或框架设备检查失败时返回非零退出码。

### 三条路线的单条运行命令

下面命令不包含任何固定绝对路径；粘贴后按提示填写项目根目录、输入图片、PaddleOCR-VL 的两个模型目录、两个 Qwen 模型目录和输出目录，因此可以在另一台机器或不同盘符下直接使用。

~~~powershell
$ProjectRoot = Read-Host '项目根目录'
Set-Location -LiteralPath $ProjectRoot

$Image = (Resolve-Path -LiteralPath (Read-Host '输入图片路径')).Path
$PaddleModel = (Resolve-Path -LiteralPath (Read-Host 'PaddleOCR-VL 模型目录')).Path
$PaddleLayoutModel = (Resolve-Path -LiteralPath (Read-Host 'PP-DocLayoutV3 模型目录')).Path
$QwenTextModel = (Resolve-Path -LiteralPath (Read-Host 'Qwen3-4B-Instruct-2507 模型目录')).Path
$QwenVLModel = (Resolve-Path -LiteralPath (Read-Host 'Qwen3-VL-4B-Instruct 模型目录')).Path

$OutputRootInput = Read-Host '输出目录（留空则使用项目根目录下的 validation-output）'
if ([string]::IsNullOrWhiteSpace($OutputRootInput)) {
    $OutputRoot = Join-Path (Get-Location) 'validation-output'
} elseif ([IO.Path]::IsPathRooted($OutputRootInput)) {
    $OutputRoot = $OutputRootInput
} else {
    $OutputRoot = Join-Path (Get-Location) $OutputRootInput
}

$EnvironmentOutput = Join-Path $OutputRoot 'environment-script'
$PaddleOutput = Join-Path $OutputRoot 'script-paddleocr-vl'
$QwenTextOutput = Join-Path $OutputRoot 'script-qwen3-text'
$QwenVLOutput = Join-Path $OutputRoot 'script-qwen3-vl'

uv sync --locked --index-strategy unsafe-best-match

uv run python scripts/check_environment.py --output-dir $EnvironmentOutput

uv run python scripts/validate_model.py --route paddleocr-vl --model-path $PaddleModel --layout-model-path $PaddleLayoutModel --model-revision master --image $Image --device cpu --output-dir $PaddleOutput

uv run python scripts/validate_model.py --route qwen3-text --model-path $QwenTextModel --model-revision master --input-text 'Correct only the obvious OCR spelling error in this sentence. Return only the corrected sentence: This is a dup1icate record.' --device cpu --max-new-tokens 32 --output-dir $QwenTextOutput

uv run python scripts/validate_model.py --route qwen3-vl --model-path $QwenVLModel --model-revision master --image $Image --device cpu --max-new-tokens 64 --output-dir $QwenVLOutput
~~~

参数说明：

| 参数 | 作用 |
| --- | --- |
| --route | 选择一条路线：paddleocr-vl、qwen3-text 或 qwen3-vl |
| --model-path | 当前路线的本地模型目录；PaddleOCR 路线传 VL recognition model 目录 |
| --image | PaddleOCR-VL/Qwen3-VL 的输入图片 |
| --input-text | Qwen3-4B 的文字输入；不传则使用脚本默认短句 |
| --device | cpu、auto、cuda/cuda:N 或 Paddle 的 gpu/gpu:N |
| --output-dir | 独立运行目录；其中保存结果、run.json 和必要日志 |
| --model-revision | VL 模型的可选来源 revision；master 等可变标签不会替代 SHA-256 manifest |
| --layout-model-path | PaddleOCR-VL 使用的 PP-DocLayoutV3 目录；Paddle 路线必填并纳入哈希 |
| --layout-model-revision | 版面模型的可选来源 revision；无法取得时使用其文件 manifest 作为本地身份 |
| --max-new-tokens | Qwen 路线生成上限；文字路线默认 32，视觉路线默认 64；Paddle 路线未设置时记录为 null |

每次运行都会计算主模型目录及显式传入的流水线组件目录中所有文件的 SHA-256，并在 run.json 保存每个文件的大小/哈希以及 manifest_sha256。无法取得不可变 revision 时，manifest 是该次本地模型身份；不要只记录 master。失败会写 status=failed、failure.traceback 和 exit_code=1，且命令返回非零退出码。

### 本机脚本化结果

| 路线 | 实际设备 | 总耗时 | 非空结果 | VL 模型 manifest_sha256 | 版面模型 manifest_sha256 | 运行记录 |
| --- | --- | ---: | --- | --- | --- | --- |
| PaddleOCR-VL-1.6 | cpu（子进程实测） | 466.20 s | 是，Markdown 约 3775 字符 | b3e4363e872b0b34613ddd83727ad9a3a8488924444d9b26780a96a1d7bbf557 | 04c761627e098bb197910c11e5329d4833a60a55069b8dcbcd0cfa7f8f858130 | validation-output/script-paddleocr-vl-corrected/run.json |
| Qwen3-4B-Instruct-2507 | cpu | 16.52 s | 是，27 字符 | 6d753b50aa12923bcd0cf95886d2dd4c4f43fc5408b6b4acf8d315655a300ed5 | — | validation-output/script-qwen3-text/run.json |
| Qwen3-VL-4B-Instruct | cpu | 83.01 s | 是，307 字符 | a6ebe76390fc375d92ff31345c351a8d187b4cd1ea830b7ee45b152c21f17919 | — | validation-output/script-qwen3-vl/run.json |

另做了负向验证：不存在的模型目录产生 validation-output/script-failure-test/run.json，记录 status=failed、FileNotFoundError，并返回退出码 1。Paddle 修复后的运行还额外保存了 paddleocr-child.json，其中的 actual_device_after_predict 由实际推理子进程写入。

本机已验证的是 CPU 路径。AMD Radeon 880M 的加速后端、任何 CUDA/NVIDIA 路径和第二台 3080 机器均未在本次运行中宣称通过。Paddle 路线现在要求显式传入 PP-DocLayoutV3 目录；该目录通过 PaddleOCRVL 子进程使用，并在 model_components.layout_detection 中单独记录文件 manifest。

## 11. fuzzy-photo 单图验证结论（2026-09-03）

- 当前机器 CPU 上，PaddleOCR-VL 用时约 187 秒，识别出主要目录条目，但遗漏多数页码，且存在编号和专业名称错误。
- Qwen3-VL 用时约 510 秒，从第一个条目开始大量重复点线，耗尽本次设置的 1536-token 输出预算，未完成目录识别；该预算是测试参数，不是模型固有上限。
- 两条路线均正常退出，但当前配置下都没有得到可靠的完整目录；运行成功和非空输出不等于内容质量通过。
- 本次未做图片预处理或文字校订，仅为单图探索测试，不能据此得出正式准确率或最终选型结论；第二台机器仍暂缓。
- 既往本地测试产物已按用户要求清理，前文旧输出路径仅作为历史记录；本次仅将结论纳入版本控制。
