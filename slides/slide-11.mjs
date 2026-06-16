import { C, base, title, label, miniTable, metric } from "./theme.mjs";

export async function slide11(presentation, ctx) {
  const slide = presentation.slides.add();
  base(slide, ctx, 11, "BACKUP ENV");
  title(slide, ctx, "复现工程把模型推理、评估、绘图、报告和 PPT 分离", "后续改图或改报告无需重跑模型；run_all 仍保留端到端入口。");

  miniTable(slide, ctx, [
    ["Layer", "Path / command", "Role"],
    ["raw data", "external_data/raw", "zip/tar/checkpoints"],
    ["staging", "external_data/work", "expanded data root"],
    ["official code", "external/SDTrack @ a3e4d8d5", "paper implementation"],
    ["metrics", "python -m src.eval_sdtrack", "AUC/PR/failure cases"],
    ["figures", "python -m src.make_figures", "mechanism and result charts"],
    ["report", ".\\run_report.ps1", "LaTeX PDF"],
    ["slides", ".\\run_slides.ps1", "editable PPTX"],
    ["all", ".\\run_all.ps1", "single entry point"]
  ], 64, 172, 720, 32);

  metric(slide, ctx, 836, 180, 230, "RTX 4050", "local GPU", "6GB laptop GPU", C.blue);
  metric(slide, ctx, 836, 294, 230, "TeX Live", "PDF build", "xelatex + latexmk", C.green);
  metric(slide, ctx, 836, 408, 230, "uv venv", "Python env", "report/eval stack", C.amber);
  label(slide, ctx,
    "当前状态记录: F 盘资源完成校验，E 盘数据根目录和仓库链接已建立；FE108 与 VisEvent 官方预测框已完成独立复算。全量数据展开与官方推理由 -ExtractDatasets all 和 -RunOfficial 显式触发，改图/改报告不会重跑模型。",
    64, 526, 1000, 62, { size: 14, color: C.ink, fill: "#FDFBF7", line: C.line, insets: { left: 12, right: 12, top: 10, bottom: 10 } });
  return slide;
}
