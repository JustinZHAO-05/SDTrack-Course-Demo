import { C, base, title, image, img, label, formula, bullet, panel } from "./theme.mjs";

export async function slide03(presentation, ctx) {
  const slide = presentation.slides.add();
  base(slide, ctx, 3, "GTP INPUT");
  title(slide, ctx, "GTP 用三通道输入保留短时计数与跨窗轨迹记忆", "该表示同时满足事件流任务需要和 ImageNet 预训练迁移需要。");

  await image(slide, ctx, img("gtp_channels.png"), 54, 176, 660, 420, "GTP three-channel mechanism");
  panel(slide, ctx, 746, 176, 398, 420, C.white, C.line);
  label(slide, ctx, "三通道定义", 770, 196, 150, 24, { size: 16, bold: true, color: C.blue, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  formula(slide, ctx, "h_i^1 = α Σ δ(p_k-1),    h_i^2 = α Σ δ(p_k+1)", 770, 238, 334, 54, C.blue);
  formula(slide, ctx, "h_i^3 = β h_{i-1}^3 + α Σ_j C(h_{i-1}^j, h_i^j)", 770, 310, 334, 54, C.cyan);
  bullet(slide, ctx, [
    "C+ 与 C- 对应当前窗口内的正负极性事件计数。",
    "Ctraj 通过 β 控制历史轨迹衰减，补充跨窗口运动提示。",
    "三通道格式避免修改视觉骨干输入层，提升预训练权重利用率。",
    "潜在敏感点是固定 β 对噪声密度和遮挡阶段缺乏场景自适应。"
  ], 774, 394, 320, 32, C.amber);
  label(slide, ctx, "读图要点: 左侧三路箭头对应计数、计数、轨迹记忆；右侧公式给出固定 β 的信息遗忘速度。", 54, 616, 1030, 34, { size: 13, color: C.muted, fill: "#FDFBF7", line: C.line, insets: { left: 12, right: 12, top: 8, bottom: 8 } });
  return slide;
}
