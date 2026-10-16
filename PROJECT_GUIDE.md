# 项目使用说明

当前安装、目录和复现步骤以 [README.md](README.md) 为准。第三方代码、数据、官方结果与权重需要自行从原作者获取，仓库不再附带默认 FE108 demo 子集。

- 轻量演示：`python -m src.synthetic_demo`。
- 上游路径配置：`python -m src.configure_sdtrack`（先获取 README 指定版本）。
- 数据整理：`python -m src.data_setup --help`，支持 `SDTRACK_SOURCE_ROOT` 与 `SDTRACK_WORK_ROOT`。
- 完整演示：`run_demo.ps1`；实验评估：`run_experiments.ps1`。
- 报告：`report/main.tex`；PPT：`slides/`；原创评估与 ATR-GTP：`src/`。

模型推理依赖 CUDA、上游 SDTrack、合法获取的数据和权重。报告中的量化结果是历史实验结果，缺少外部资源时不自动伪造或重新生成。
