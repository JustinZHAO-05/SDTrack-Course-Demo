# SDTrack-Course-Demo

围绕 SDTrack 的课程研究项目，保留原创 **ATR-GTP 输入级改进**、独立评估器、实验与可视化脚本、报告、PPT 和分析图表。SDTrack 原算法归原作者所有，本项目不将其作为原创成果。

第三方 SDTrack 源码、FE108 原始帧与标注、官方结果分发包、预训练权重和原始帧衍生 contact sheets 已移除，不再随仓库分发。已有报告/PPT 是历史实验的作者撰写交付，包含引用的科学插图；它们不是可运行的数据包。机制示意图与汇总分析图保留。

## 安装

```bash
git clone https://github.com/JustinZHAO-05/SDTrack-Course-Demo.git
cd SDTrack-Course-Demo
git lfs install
git lfs pull
python -m pip install -r requirements-report.txt
```

LFS 现在仅用于保留的报告、PPT 和图表等资源；不会下载模型或数据。单独安装推理环境时使用 `requirements-sdtrack-cu121.txt`，完整模型推理还需要 CUDA。

### 自行安装官方 SDTrack

从[官方仓库](https://github.com/YmShan/SDTrack)获取项目使用的固定版本：

```bash
git clone https://github.com/YmShan/SDTrack.git external/SDTrack
git -C external/SDTrack checkout a3e4d8d508e1808e9e41629733b20d38ee52ce05
python -m src.configure_sdtrack
```

最后一条命令只写入本机上游 checkout 的路径配置，不分发上游源码。请同时遵循官方安装说明、许可与引用要求。

### 自行获取数据与权重

通过 [FE108 官方数据入口](https://zhangjiqing.com/dataset/)及 [SDTrack-Event 官方说明](https://github.com/YmShan/SDTrack/tree/a3e4d8d508e1808e9e41629733b20d38ee52ce05/SDTrack-Event)获取授权数据、GTP 预处理版本、模型和官方预测结果。具体资源链接保留在 [`data/resource_manifest.json`](data/resource_manifest.json)，有效性及使用条款以原作者入口为准。

现有脚本约定本地目录如下（全部忽略、不提交）：

- `data/FE108/test/<sequence>/inter1_stack_3008/*.png`：GTP 三通道帧。
- `data/FE108/test/<sequence>/groundtruth_rect.txt`：序列标注。
- `data/official_results_E/FE108_eval/FE108/annos/gt_rect/<sequence>.txt`：评估真值；可选 absent 标志放在相邻目录。
- `data/weights/SDTrack-tiny-1x4.pth`：官方初始化权重。
- `outputs/checkpoints/train/SDTrack/SDTrack-tiny-fe108/SDTrack_ep0100.pth.tar`：官方 FE108 checkpoint。

已有压缩包可通过 `run_data_setup.ps1` 整理；源目录与工作目录可设置 `SDTRACK_SOURCE_ROOT`、`SDTRACK_WORK_ROOT`，详见 `python -m src.data_setup --help`。

## 运行

无需第三方源码、模型或数据的合成演示：

```bash
python -m src.synthetic_demo
```

它生成合成 GTP 帧、运行 ATR-GTP 轨迹通道变换，并用已知框验证 IoU 评估器，不代表真实数据集性能。

完整 demo 在补齐上述外部依赖后运行：

```powershell
.\run_demo.ps1 -ListSequences
.\run_demo.ps1 -Sequence bike_low
.\run_demo.ps1 -NoBrowser
```

缺少资源时会列出缺失路径，并提示阅读本说明。`-ReplayOnly` 仍需要本地已经生成的 demo 结果。

## 报告与代码

- `src/`：原创 ATR-GTP、评估、分析与 demo 调度。
- `report/main.tex`、`report/refs.bib`：中文报告与参考文献。
- `slides/`：可编辑 PPT 源工程。
- `outputs/figures/`、`outputs/tables/`：保留的机制图、分析图与结果表。
- `outputs/*.pdf`、`outputs/*.pptx`、`outputs/pdf/main.pdf`：历史作者交付文件。

```powershell
.\run_report_fast.ps1  # 使用保留图表编译报告
.\run_figures.ps1      # 重画图表；真实案例需外部数据
.\run_experiments.ps1  # 外部数据与官方模型推理
.\run_slides.ps1
```

公开 LaTeX 源码中不再内嵌第三方原图或原始帧 contact sheets，相关位置保留说明框；自行获取数据后可用原有可视化脚本重新生成。完整实验不在本次清理中重跑。

## 引用与许可

原创课程项目代码和文档使用 [MIT License](LICENSE)。SDTrack、FE108、外部权重与结果遵循各自原作者的许可和访问条件。使用 SDTrack/GTP 请引用原论文，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
