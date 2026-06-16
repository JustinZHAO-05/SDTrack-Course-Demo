import { C, base, title, image, img, label, formula, metric, bullet, panel } from "./theme.mjs";

export async function slide06(presentation, ctx) {
  const slide = presentation.slides.add();
  base(slide, ctx, 6, "HEAD + ENERGY");
  title(slide, ctx, "中心头承担连续定位，能耗公式解释 AC/MAC 的数量级差异", "论文的低能耗结论来自 spike 发放率、AC 能耗常数和有限浮点保留的共同作用。");

  await image(slide, ctx, img("energy_formula.png"), 54, 178, 560, 310, "Energy formula");
  panel(slide, ctx, 654, 178, 456, 310, C.white, C.line);
  label(slide, ctx, "Head 输出分解", 678, 198, 180, 26, { size: 16, bold: true, color: C.blue, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  formula(slide, ctx, "B = decode(P_center, Δx, Δy, w, h)", 678, 236, 356, 46, C.blue);
  bullet(slide, ctx, [
    "中心概率图负责目标位置峰值。",
    "offset 修正离散网格到连续坐标的偏差。",
    "size 分支回归宽高，浮点末层用于稳定数值输出。",
    "训练损失通常由分类热图、L1/GIoU 框损失共同约束。"
  ], 680, 304, 350, 33, C.cyan);

  metric(slide, ctx, 60, 530, 210, "4.6 pJ", "one MAC", "45 nm reference", C.red);
  metric(slide, ctx, 300, 530, 210, "0.9 pJ", "one AC", "45 nm reference", C.green);
  metric(slide, ctx, 540, 530, 210, "fr_j", "spike rate", "dominates sparse terms", C.amber);
  metric(slide, ctx, 780, 530, 210, "8.16 mJ", "Tiny energy", "paper reported", C.blue);
  label(slide, ctx, "限定: 该能耗是理论估计；通用 GPU 上的实际功耗还取决于框架稀疏内核和硬件映射。", 60, 632, 922, 28, { size: 12, color: C.muted, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  return slide;
}
