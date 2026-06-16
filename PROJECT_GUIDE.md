# SDTrack 项目使用与交接说明

本文档用于说明本项目的结构、环境、数据放置、命令行入口、报告修改与现场 demo 运行方式。所有命令默认在项目根目录执行。

## 1. 项目结构

### 顶层目录

- `.venv/`  
  当前机器上的 Python 虚拟环境。复制项目到其他电脑时不建议直接复用，应重新创建虚拟环境并安装依赖。

- `Assignment_Insturctions/`  
  课程作业要求与评分说明。

- `data/`  
  数据、权重、官方结果和资源清单目录。部分目录可能是指向外部数据盘的链接。完整实验依赖这里的数据组织。

- `demo_assets/`  
  项目内自带的轻量 demo 数据子集。默认 demo 会优先使用该目录，因此把项目文件夹交给别人后，默认现场 demo 不依赖外部数据盘。

- `external/SDTrack/`  
  官方 SDTrack 开源代码仓库。现场 demo 和官方推理会调用其中的 `SDTrack-Event/tracking/test.py`。

- `outputs/`  
  所有生成结果目录，包括最终 PDF/PPTX、实验指标、图表、demo dashboard、prediction、日志、可视化视频等。

- `report/`  
  LaTeX 报告源码目录。手动修改报告正文、附录、公式、图表引用时主要修改这里。

- `scripts/`  
  辅助脚本目录。

- `slides/`  
  PPT 生成工程源码。PPT 的页面脚本位于这里，生成后的 PPTX 在 `outputs/`。

- `src/`  
  自写 Python 代码目录，包含评估器、绘图、ATR-GTP 改进、demo 调度、可视化等核心代码。

### 顶层文件

- `README.md`  
  简要交付说明。

- `PROJECT_GUIDE.md`  
  当前这份完整使用说明。

- `Plan.md` / `Plan.pdf`  
  原始实施计划和计划 PDF。

- `SDTrack.pdf`  
  选定论文原文。

- `requirements-sdtrack-cu121.txt`  
  SDTrack 复现、demo、评估、绘图所需 Python 依赖。

- `requirements-report.txt`  
  报告相关的少量 Python 依赖。

- `run_all.ps1`  
  一键入口：实验、图表、报告、PPT 串联执行。

- `run_data_setup.ps1`  
  数据校验、解压和数据链接建立入口。

- `run_experiments.ps1`  
  实验入口：环境记录、官方推理、官方结果复算、ATR-GTP tracker 消融等。

- `run_figures.ps1`  
  图表和可视化重生成入口。

- `run_report.ps1`  
  报告编译入口，会重画图表并用 `latexmk -xelatex` 编译 PDF。

- `run_report_fast.ps1`  
  快速报告编译入口，只编译 LaTeX，不重画图表，适合只修改文字、公式、引用和图片尺寸后的快速检查。

- `run_slides.ps1`  
  PPTX 生成入口。

- `run_demo.ps1`  
  现场 demo 入口，支持实机推理、回放、指定序列、多序列、列出序列等参数。

### `src/` 重要代码

- `src/demo_live.py`  
  现场 demo 总调度：预检查、调用官方模型、生成 ATR-GTP 输入、评估指标、生成 HTML dashboard、视频和图表。

- `src/atr_gtp_tracker_eval.py`  
  ATR-GTP 完整 tracker 推理消融代码，负责生成输入变体并调用官方 tracker。

- `src/ablate_gtp.py`  
  ATR-GTP 输入级变体生成和协议图生成。

- `src/analyze_atr_gtp.py`  
  ATR-GTP 输入级统计分析和图表生成。

- `src/eval_sdtrack.py`  
  自写 evaluator，计算 AUC、PR20、归一化精度、mean IoU、中心误差等指标。

- `src/eval_official_bundle.py`  
  对官方 tracking results 做批量复算。

- `src/make_figures.py`  
  论文报告中的主要实验图表生成代码。

- `src/visualize_cases.py`  
  成功/失败案例截图和数据集样例图生成。

- `src/visualize_sequences.py`  
  完整输入帧流、输出叠框视频、ATR-GTP 输入对比视频和 contact sheet 生成。

- `src/data_setup.py`  
  根据资源清单进行数据解压、整理和链接。

- `src/environment_report.py`  
  记录环境、GPU、CUDA、PyTorch 等信息。

- `src/metrics.py`  
  IoU、中心误差、AUC、PR20 等基础指标实现。

### 报告和最终文件位置

- LaTeX 主文件：`report/main.tex`
- BibTeX 参考文献：`report/refs.bib`
- 报告静态图片：`report/figures/`
- 自动生成图表：`outputs/figures/`
- 案例可视化图片：`outputs/cases/`
- 报告临时编译结果：`outputs/pdf/main.pdf`
- 最终报告 PDF：`outputs/序号+SDTrack+姓名1+姓名2+姓名3+姓名4.pdf`
- 最终 PPTX：`outputs/序号+SDTrack+姓名1+姓名2+姓名3+姓名4.pptx`

## 2. 环境依赖与安装

### Clone 后先拉取 Git LFS 资源

本仓库使用 Git LFS 保存 checkpoint、demo 输入帧、最终 PDF/PPTX 和主要二进制图片资源。首次 clone 后必须执行：

```powershell
git lfs install
git lfs pull
```

如果跳过该步骤，部分 `.png`、`.pdf`、`.pptx` 或 `.pth.tar` 文件会只是很小的 LFS pointer 文本，默认 demo 会因为缺少真实 checkpoint 或输入帧而失败。

### 推荐环境

- Windows + PowerShell
- Python 3.10
- NVIDIA GPU
- CUDA 可用
- TeX Live，并确保命令行可用 `latexmk`
- 可选：`ffmpeg`，用于把 demo 视频转为浏览器兼容的 H.264 MP4

### 创建 Python 环境

复制项目到新电脑后，建议重新创建虚拟环境：

```powershell
git lfs install
git lfs pull
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-sdtrack-cu121.txt
```

如果只编译报告，也可以安装报告依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-report.txt
```

### 环境检查

```powershell
.\.venv\Scripts\python.exe -c "import torch; print(torch.__version__, torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no cuda')"
latexmk -version
ffmpeg -version
```

如果 `torch.cuda.is_available()` 为 `False`，现场实机推理会失败，但可以使用 demo 回放模式：

```powershell
.\run_demo.ps1 -ReplayOnly
```

## 3. 数据和数据集放置

### 项目内 demo 数据

默认现场 demo 优先读取：

```text
demo_assets/FE108/test
demo_assets/FE108/annos/gt_rect
```

当前项目内自带 demo 序列：

```text
bike_low
box_hdr
star_motion
star_mul222
```

因此，把整个项目文件夹复制到别的电脑后，默认 `.\run_demo.ps1` 可以使用这些项目内序列进行实机推理，不需要外部完整 FE108 数据。

### 完整实验数据

完整复现实验建议按下面结构放置：

```text
data/FE108/test/<sequence>/inter1_stack_3008/*.png
data/FE108/test/<sequence>/groundtruth_rect.txt
data/VisEvent/test/<sequence>/...
data/official_results_E/FE108_eval/FE108/annos/gt_rect/*.txt
data/official_results_E/FE108_eval/FE108/annos/absent/*.txt
data/weights/
outputs/checkpoints/train/SDTrack/SDTrack-tiny-fe108/SDTrack_ep0100.pth.tar
```

当前 `data/FE108`、`data/VisEvent`、`data/official_results_E` 可能是目录链接。换电脑后如果链接失效，需要重新放置数据或重新建立链接。

### 资源清单

下载链接和资源说明位于：

```text
data/resource_manifest.json
```

数据准备脚本：

```powershell
.\run_data_setup.ps1 -SourceRoot external_data\raw -WorkRoot external_data\work -ExtractDatasets fe108
```

参数说明：

- `-SourceRoot`：原始压缩包和权重所在目录。
- `-WorkRoot`：解压后的工作数据目录。
- `-ExtractDatasets none|fe108|visevent|all`：选择解压的数据集。
- `-SkipOfficialExtract`：跳过官方结果包解压。

如果只做默认现场 demo，不需要完整数据集，只需要 `demo_assets` 和 checkpoint。

## 4. 命令行入口

### 一键全流程

```powershell
.\run_all.ps1
```

作用：运行实验汇总、生成图表、编译报告、生成 PPT。

可选参数：

```powershell
.\run_all.ps1 -PrepareData -ExtractDatasets fe108
.\run_all.ps1 -RunOfficial
.\run_all.ps1 -RunOfficialVisEvent
```

### 数据准备

```powershell
.\run_data_setup.ps1 -SourceRoot external_data\raw -WorkRoot external_data\work -ExtractDatasets all
```

作用：从原始资源目录解压 FE108/VisEvent、官方评估包、官方结果，并建立项目内数据入口。

### 实验

```powershell
.\run_experiments.ps1
```

默认作用：

- 记录环境信息。
- 生成 ATR-GTP 协议。
- 对已有 prediction 做评估。

常用参数：

```powershell
.\run_experiments.ps1 -RunOfficial
.\run_experiments.ps1 -RunOfficialVisEvent
.\run_experiments.ps1 -RunAtrTracker
.\run_experiments.ps1 -PrepareData -ExtractDatasets fe108
```

### 图表

```powershell
.\run_figures.ps1
```

作用：

- 重画实验图表到 `outputs/figures/`。
- 生成案例图到 `outputs/cases/`。
- 生成完整帧流可视化到 `outputs/sequence_viz/`。
- 更新报告使用的表格到 `outputs/tables/`。

### 报告

```powershell
.\run_report.ps1
```

作用：

- 先运行 `run_figures.ps1`。
- 编译 `report/main.tex`。
- 输出 `outputs/pdf/main.pdf`。
- 复制最终报告到 `outputs/序号+SDTrack+姓名1+姓名2+姓名3+姓名4.pdf`。

如果只修改文字、公式、参考文献或图片尺寸，不需要重画图表，使用快速编译：

```powershell
.\run_report_fast.ps1
```

该命令只执行 LaTeX 编译和最终 PDF 复制，不调用 `run_figures.ps1`，速度更快。

也可以直接执行底层 LaTeX 命令：

```powershell
latexmk -xelatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir=outputs\pdf report\main.tex
```

### PPT

```powershell
.\run_slides.ps1
```

作用：根据 `slides/` 和 `outputs/figures/` 生成最终 PPTX。该脚本依赖当前机器上的 Codex/Presentations 运行时，如果换电脑可能需要调整 Node/插件运行时路径。

### Demo

```powershell
.\run_demo.ps1
```

作用：现场运行原始 SDTrack-Tiny 推理和 ATR-GTP adaptive_smooth 改进推理，生成 HTML dashboard、视频、指标、prediction 和日志。

详细参数见第 6 节。

## 5. 如何修改报告

### 修改位置

- 报告正文、附录、公式、图表排版：`report/main.tex`
- 参考文献：`report/refs.bib`
- 静态机制图：`report/figures/`
- 自动生成图表的数据和绘图逻辑：`src/make_figures.py`、`src/visualize_cases.py`、`src/visualize_sequences.py`
- 自动生成表格：`outputs/tables/`

### 常见修改

#### 修改文字

直接编辑：

```text
report/main.tex
```

然后编译：

```powershell
.\run_report.ps1
```

如果只改了文字且不需要重画图表，推荐使用：

```powershell
.\run_report_fast.ps1
```

#### 修改参考文献

编辑：

```text
report/refs.bib
```

正文中用 `\citep{key}` 或 `\citet{key}` 引用，然后运行：

```powershell
.\run_report.ps1
```

只改 BibTeX 或引用位置时，也可以用快速编译：

```powershell
.\run_report_fast.ps1
```

#### 修改图片尺寸

在 `report/main.tex` 中找到：

```latex
\includegraphics[width=0.80\linewidth]{xxx.png}
```

调整 `width=...` 即可。例如：

```latex
\includegraphics[width=0.70\linewidth]{xxx.png}
```

修改图片尺寸后通常不需要重画图表，直接快速编译：

```powershell
.\run_report_fast.ps1
```

#### 替换图片

保持文件名不变时，直接覆盖对应图片即可：

```text
report/figures/
outputs/figures/
outputs/cases/
outputs/paper_figures/
```

如果新增文件名，需要在 `report/main.tex` 中同步修改 `\includegraphics{...}`。

### 报告输出位置

编译后会生成：

```text
outputs/pdf/main.pdf
outputs/序号+SDTrack+姓名1+姓名2+姓名3+姓名4.pdf
```

提交前需要替换报告封面和文件名中的序号、姓名、学号占位。

## 6. 如何跑现场 Demo

### 默认实机 demo

```powershell
.\run_demo.ps1
```

默认行为：

- 序列：`bike_low`
- 原始模型：SDTrack-Tiny checkpoint + 原始 GTP 输入
- 改进后跟踪器：同一 checkpoint + ATR-GTP adaptive_smooth 输入
- 输出目录：`outputs/demo/<timestamp>/`
- 自动打开 HTML dashboard

### 不自动打开浏览器

```powershell
.\run_demo.ps1 -NoBrowser
```

适合只想生成结果，然后手动打开：

```text
outputs/demo/<timestamp>/index.html
```

### 查看可选序列

```powershell
.\run_demo.ps1 -ListSequences
```

输出会分为：

- 项目内自带 demo 序列。
- 完整 FE108 数据存在时可选的额外序列。

### 指定单条序列

```powershell
.\run_demo.ps1 -Sequence box_hdr
.\run_demo.ps1 -Sequence star_motion
.\run_demo.ps1 -Sequence star_mul222
```

### 指定多条序列

```powershell
.\run_demo.ps1 -Sequence bike_low,box_hdr
```

或者：

```powershell
.\run_demo.ps1 -Sequence bike_low -Sequence box_hdr
```

### 长 demo

```powershell
.\run_demo.ps1 -LongDemo
```

会在当前序列基础上加入 `star_motion`。耗时更长。

### 回放模式

```powershell
.\run_demo.ps1 -ReplayOnly
```

作用：不重新调用模型，只使用已有 prediction 和视频重新生成 dashboard。适合作为现场应急方案。HTML 中会标注这是回放已有结果。

### 指定输出目录

```powershell
.\run_demo.ps1 -OutDir outputs\demo\my_demo
```

### Demo 运行过程

实机 demo 的阶段包括：

1. 预检查 CUDA、checkpoint、数据、官方 test 入口。
2. 调用官方 `tracking/test.py` 跑原始 SDTrack-Tiny。
3. 生成 ATR-GTP adaptive_smooth 输入。
4. 再次调用官方 `tracking/test.py` 跑改进后跟踪器。
5. 计算 AUC、PR20、NP@0.2、mean IoU、中心误差。
6. 生成输入帧流、输出叠框视频、ATR-GTP 输入对比视频、指标图和 HTML dashboard。

### Demo 结果在哪里看

每次 demo 的结果在：

```text
outputs/demo/<timestamp>/
```

重要文件：

- `index.html`  
  现场 dashboard。打开它即可看环境、日志、视频、指标和 prediction 样例。

- `state.json`  
  本次 demo 状态、环境、序列、输出文件和指标汇总。

- `logs/demo.log`  
  现场运行总日志。

- `logs/baseline_<sequence>_test.log`  
  原始模型官方 test 日志。

- `logs/adaptive_smooth_<sequence>_test.log`  
  改进后跟踪器官方 test 日志。

- `results/baseline/SDTrack/SDTrack-tiny-fe108/<sequence>.txt`  
  原始模型 prediction。

- `results/adaptive_smooth/SDTrack/SDTrack-tiny-fe108/<sequence>.txt`  
  改进后跟踪器 prediction。

- `metrics/summary_by_variant.csv`  
  两组方法的 AUC、PR20、NP@0.2、mean IoU、中心误差。

- `metrics/per_sequence_metrics.csv`  
  每条序列的详细指标。

- `metrics/iou_curves.csv`  
  逐帧 IoU 曲线数据。

- `videos/`  
  三类视频：
  - `<sequence>_input_full_browser.mp4`：完整输入事件帧流。
  - `<sequence>_output_overlay_full_browser.mp4`：GT、原始模型、改进后跟踪器叠框输出。
  - `<sequence>_atr_input_compare_full_browser.mp4`：原始 GTP 与 ATR-GTP 输入对比。

- `figures/metrics_bar.png`  
  AUC/PR20 柱状图。

- `figures/iou_curve.png`  
  逐帧 IoU 曲线。

### Demo 中三种颜色含义

在输出框视频中：

- 红框：GT 真值框。
- 蓝框：原始模型 SDTrack-Tiny。
- 绿框：改进后跟踪器 ATR-GTP adaptive_smooth。

### 换电脑运行 demo 的注意事项

1. 不建议复制 `.venv`，应重新创建环境并安装依赖。
2. 默认 demo 使用 `demo_assets`，无需完整 FE108 数据。
3. 实机推理需要 CUDA 可用；CUDA 不可用时用 `-ReplayOnly`。
4. 若浏览器打不开原始 MP4，dashboard 默认使用 H.264 的 `_browser.mp4` 和 GIF 预览。
5. 若要跑完整 FE108 或额外序列，需要重新放置完整数据到 `data/FE108/test`。
