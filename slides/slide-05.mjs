import { C, base, title, image, img, label, formula, bullet, panel } from "./theme.mjs";

export async function slide05(presentation, ctx) {
  const slide = presentation.slides.add();
  base(slide, ctx, 5, "SNN BACKBONE");
  title(slide, ctx, "Spiking MetaFormer 保留 Transformer 交互，同时把主要计算推向 spike-driven 路径", "SDTrack 的骨干围绕 spike query/key/value 重写注意力计算，并把稀疏发放率纳入能耗逻辑。");

  await image(slide, ctx, img("snn_attention.png"), 54, 176, 590, 404, "SNN attention");
  panel(slide, ctx, 686, 176, 430, 404, C.white, C.line);
  label(slide, ctx, "SSA 计算路径", 710, 198, 160, 26, { size: 16, bold: true, color: C.blue, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  formula(slide, ctx, "SSA(Qs,Ks,Vs) = Qs Ks^T Vs · s", 710, 242, 342, 52, C.cyan);
  bullet(slide, ctx, [
    "SNN Conv Module 提供低层空间编码，token 化后进入 SNN Transformer。",
    "spike Q/K/V 降低连续值矩阵乘法强度，使能耗估计随发放率缩放。",
    "首层和 head 末层保留浮点卷积，保护坐标回归的连续精度。",
    "Tiny-1x4 通过较少 block 和 spike 时步取得能耗-精度折中。"
  ], 714, 320, 350, 34, C.green);
  label(slide, ctx, "结构理解: 预训练迁移负责语义起点，spike-driven 结构负责事件域稀疏推理，中心头负责连续框输出。", 54, 604, 990, 34, { size: 13, color: C.muted, fill: "#FDFBF7", line: C.line, insets: { left: 12, right: 12, top: 8, bottom: 8 } });
  return slide;
}
