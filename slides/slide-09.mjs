import { C, base, title, image, img, label, formula, bullet } from "./theme.mjs";

export async function slide09(presentation, ctx) {
  const slide = presentation.slides.add();
  base(slide, ctx, 9, "BACKUP ATR-GTP");
  title(slide, ctx, "ATR-GTP 将固定轨迹衰减改成事件密度自适应输入重权重", "该改进只改变 GTP 第三通道，不修改 checkpoint、backbone 或 tracking head。");

  await image(slide, ctx, img("atr_gtp.png"), 54, 172, 596, 260, "ATR-GTP mechanism");
  await image(slide, ctx, img("atr_beta_curve.png"), 54, 448, 596, 174, "ATR-GTP beta curve");
  formula(slide, ctx, "I'_t = [C_t^+, C_t^-, β_t C_t^traj]", 690, 184, 390, 46, C.blue);
  formula(slide, ctx, "β_t = clip(β0 · Ebar/(E_t+ε), βmin, βmax)", 690, 246, 390, 46, C.cyan);
  formula(slide, ctx, "beta_smooth(t)=λ·beta_smooth(t-1)+(1-λ)·beta(t)", 690, 308, 390, 46, C.amber);
  bullet(slide, ctx, [
    "高事件密度: 降低轨迹记忆权重，抑制背景残影。",
    "低事件密度: 提升轨迹记忆权重，补充稀疏线索。",
    "七组消融: baseline, zero, weak, fixed1, strong, adaptive, adaptive_smooth。",
    "已有代码支持 protocol-only 与批量 GTP 图像重写。"
  ], 694, 380, 380, 31, C.green);
  label(slide, ctx, "适用答辩点: 该方案属于低成本输入级增强，固定 checkpoint、backbone、head 和 evaluator，使性能变化直接归因到 GTP 第三通道。", 690, 532, 390, 68, { size: 12.8, color: C.ink, fill: "#FDFBF7", line: C.line, insets: { left: 12, right: 12, top: 8, bottom: 8 } });
  return slide;
}
