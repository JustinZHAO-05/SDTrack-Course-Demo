import { C, base, title, image, img, label, formula, stage, arrow } from "./theme.mjs";

export async function slide04(presentation, ctx) {
  const slide = presentation.slides.add();
  base(slide, ctx, 4, "IPL GEOMETRY");
  title(slide, ctx, "IPL 在早期卷积前显式制造 template-search 几何邻接", "对角拼接让卷积核和后续 token 交互共同学习模板与搜索区域的空间关系。");

  await image(slide, ctx, img("ipl_diagonal.png"), 60, 180, 490, 390, "IPL diagonal concatenation");
  formula(slide, ctx, "U = IPL(X,Z) = [[X, O1], [O2, Z]]", 610, 188, 430, 50, C.blue);

  stage(slide, ctx, 610, 268, 170, 124, "输入层", "template Z 与 search X 都由 GTP 转为三通道图。", C.cyan);
  arrow(slide, ctx, 792, 328, 52, C.muted);
  stage(slide, ctx, 858, 268, 170, 124, "拼接层", "X 与 Z 置于对角区域，空块保持局部边界。", C.blue);
  arrow(slide, ctx, 1040, 328, 52, C.muted);
  stage(slide, ctx, 610, 428, 170, 124, "SNN Conv", "早期卷积在统一画布中捕获相对位置信息。", C.green);
  arrow(slide, ctx, 792, 488, 52, C.muted);
  stage(slide, ctx, 858, 428, 170, 124, "Transformer", "拆分 token 后通过 SSA 完成高层目标关联。", C.amber);

  label(slide, ctx, "消融证据: 去除 IPL 后 FE108 PR 由 91.30% 降至 89.66%，下降集中体现在中心定位置信度。", 60, 592, 980, 36, {
    size: 14,
    bold: true,
    color: C.ink,
    fill: "#FDFBF7",
    line: C.line,
    insets: { left: 12, right: 12, top: 8, bottom: 8 },
  });
  return slide;
}
