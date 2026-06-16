import { C, base, title, image, img, label, miniTable, metric } from "./theme.mjs";

export async function slide07(presentation, ctx) {
  const slide = presentation.slides.add();
  base(slide, ctx, 7, "PAPER RESULTS");
  title(slide, ctx, "论文结果显示 SDTrack 处于能耗-参数-精度前沿", "相同 FE108 主基准下，Tiny 版本以较低参数量和理论能耗保持高 AUC/PR。");

  await image(slide, ctx, img("benchmark_bubble.png"), 54, 172, 635, 430, "Benchmark energy-performance bubble");
  miniTable(slide, ctx, [
    ["Method", "Params", "FE108 AUC", "PR20"],
    ["SDTrack-Tiny", "19.61M", "59.0", "91.3"],
    ["SDTrack-Base", "78.41M", "61.6", "92.1"],
    ["HiT", "21.0M", "56.5", "88.5"],
    ["OSTrack", "92.1M", "53.7", "87.4"],
    ["SimTrack", "26.7M", "55.7", "89.1"]
  ], 730, 185, 390, 32);
  metric(slide, ctx, 730, 410, 178, "+3.3 AUC", "Tiny vs OSTrack", "paper table delta", C.blue);
  metric(slide, ctx, 930, 410, 178, "mJ-level", "energy region", "SNN estimate", C.green);
  label(slide, ctx,
    "读图方式: 横轴表示理论能耗或参数成本，纵轴表示 AUC/PR 精度；位于左上区域的方法具备更优综合效率。SDTrack 的优势来自输入表示、预训练迁移和 spike-driven backbone 的叠加。",
    730, 526, 390, 86, { size: 13, color: C.ink, fill: "#FDFBF7", line: C.line, insets: { left: 12, right: 12, top: 8, bottom: 8 } });
  return slide;
}
