# SDTrack-Course-Demo

本仓库是围绕 CVPR 2026 论文 **SDTrack: A Baseline for Event-based Tracking via Spiking Neural Networks** 的课程项目交付，包含中文 LaTeX 报告、可编辑 PPTX、官方 SDTrack 代码、FE108 demo 数据子集、SDTrack-Tiny checkpoint、SNN 初始化权重、ATR-GTP 输入级改进、独立评估器、图表生成脚本和现场 demo dashboard。

仓库目标是让他人 clone 后，在安装环境依赖并拉取 Git LFS 大文件后，可以：

- 修改和重新编译中文论文报告。
- 运行默认现场 demo，展示原始 SDTrack-Tiny 与 ATR-GTP adaptive_smooth 改进后跟踪器。
- 查看实验图表、指标、prediction、输入帧流、输出叠框视频和 IoU 曲线。

## Quick Start

### 1. Clone and Pull LFS Assets

```powershell
git clone https://github.com/JustinZHAO-05/SDTrack-Course-Demo.git
cd SDTrack-Course-Demo
git lfs install
git lfs pull
```

Git LFS 资源包括 demo 输入帧、checkpoint、SNN 初始化权重、最终 PDF/PPTX 和二进制图片资源。若未执行 `git lfs pull`，demo 可能因为缺少权重或 PNG 帧而失败。

### 2. Create Python Environment

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-sdtrack-cu121.txt
```

检查 CUDA：

```powershell
.\.venv\Scripts\python.exe -c "import torch; print(torch.__version__, torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no cuda')"
```

### 3. Run Live Demo

```powershell
.\run_demo.ps1
```

默认 demo 使用项目内 `demo_assets/FE108/test/bike_low`，并完整运行：

1. 原始模型：SDTrack-Tiny checkpoint + 原始 GTP 输入。
2. 改进后跟踪器：同一 checkpoint + ATR-GTP adaptive_smooth 输入。
3. 指标评估：AUC、PR20、NP@0.2、mean IoU、中心误差。
4. 可视化：输入事件帧流、输出叠框视频、ATR-GTP 输入对比、IoU 曲线、prediction 样例。

结果位于：

```text
outputs/demo/<timestamp>/index.html
```

常用 demo 命令：

```powershell
.\run_demo.ps1 -ListSequences
.\run_demo.ps1 -Sequence box_hdr
.\run_demo.ps1 -Sequence bike_low,box_hdr
.\run_demo.ps1 -NoBrowser
.\run_demo.ps1 -ReplayOnly
```

## Modify and Compile the Report

LaTeX 主文件：

```text
report/main.tex
```

参考文献：

```text
report/refs.bib
```

只修改文字、公式、引用或图片尺寸时，使用快速编译：

```powershell
.\run_report_fast.ps1
```

该命令不会重画图表，输出：

```text
outputs/pdf/main.pdf
outputs/序号+SDTrack+姓名1+姓名2+姓名3+姓名4.pdf
```

如果修改了绘图脚本、指标 CSV 或案例可视化，使用完整报告构建：

```powershell
.\run_report.ps1
```

## Main Commands

```powershell
.\run_demo.ps1              # 现场 demo
.\run_report_fast.ps1       # 快速编译报告，不重画图表
.\run_report.ps1            # 重画图表并编译报告
.\run_figures.ps1           # 只重画图表和案例图
.\run_experiments.ps1       # 实验/评估入口
.\run_all.ps1               # 实验、图表、报告、PPT 全流程
.\run_slides.ps1            # 生成 PPTX
```

## Repository Layout

```text
src/                    自写评估、绘图、ATR-GTP、demo 调度代码
report/                 中文 LaTeX 报告源码和 BibTeX
slides/                 PPT 生成工程
external/SDTrack/       官方 SDTrack 代码，vendored third-party
demo_assets/            可随仓库 clone 的 FE108 demo 子集
data/weights/           demo 所需 SNN 初始化权重
outputs/checkpoints/    demo 所需 SDTrack-Tiny checkpoint
outputs/figures/        报告使用的实验图表
outputs/cases/          报告使用的案例图和帧流截图
outputs/tables/         报告使用的 LaTeX/CSV 表格
outputs/*.pdf           最终报告 PDF
outputs/*.pptx          最终 PPTX
```

更完整的交接说明见：

```text
PROJECT_GUIDE.md
```

## Data Notes

默认 demo 不需要完整 FE108 数据，只需要仓库内 `demo_assets`、`data/weights` 中的初始化权重和 `outputs/checkpoints` 中的 checkpoint。

完整 FE108/VisEvent 大规模复现实验需要额外下载数据。资源清单位于：

```text
data/resource_manifest.json
```

推荐完整数据目录结构见 `PROJECT_GUIDE.md`。本仓库不提交完整 FE108/VisEvent 数据集，只提交可运行默认 demo 的最小子集。

## Third-Party Code and Citation

Official SDTrack code is vendored under `external/SDTrack` from commit:

```text
a3e4d8d508e1808e9e41629733b20d38ee52ce05
```

See `THIRD_PARTY_NOTICES.md` for license and citation notes.

## License

This course project code and documentation are released under the MIT License. Third-party SDTrack code keeps its original MIT License and copyright.
