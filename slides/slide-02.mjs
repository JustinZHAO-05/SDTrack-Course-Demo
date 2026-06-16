import { C, base, title, image, img, label, panel, bullet, formula, stage, arrow } from "./theme.mjs";

export async function slide02(presentation, ctx) {
  const slide = presentation.slides.add();
  base(slide, ctx, 2, "EVENT + SNN");
  title(slide, ctx, "事件相机与 SNN 的匹配点是稀疏时空增量", "高动态范围和微秒级响应提供鲁棒观测，脉冲神经元把稀疏活动转化为低 AC 计算。");

  stage(slide, ctx, 56, 188, 230, 142, "RGB tracker 风险", "低照度、过曝、运动模糊、相似背景会使纹理与颜色线索失效，中心位置和尺度回归同步漂移。", C.red);
  arrow(slide, ctx, 302, 257, 60, C.muted);
  stage(slide, ctx, 378, 188, 230, 142, "事件表示优势", "像素只在亮度变化时触发事件，观测项天然关注边缘运动和时间顺序，背景静止区域被压缩。", C.blue);
  arrow(slide, ctx, 624, 257, 60, C.muted);
  stage(slide, ctx, 700, 188, 230, 142, "SNN 推理优势", "膜电位积累、阈值发放、重置过程带来稀疏激活，理论能耗由 MAC 主导转向 AC 主导。", C.green);

  await image(slide, ctx, img("ilif_neuron.png"), 56, 370, 522, 246, "I-LIF neuron dynamics");
  panel(slide, ctx, 620, 370, 470, 246, "#FDFBF7", C.line);
  label(slide, ctx, "机制解释", 640, 390, 128, 26, { size: 16, bold: true, color: C.blue, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  bullet(slide, ctx, [
    "事件流记录 log-intensity crossing，保留运动边界而减少冗余帧。",
    "I-LIF 通过 H[t], U[t], S[t] 形成离散时间状态机。",
    "spike rate fr_j 决定 AC 项规模，直接进入能耗公式。"
  ], 642, 430, 405, 34, C.cyan);
  formula(slide, ctx, "U[t] = H[t-1] + X[t];   S[t] = Θ(U[t]-Vth);   H[t] = U[t](1-S[t])", 642, 548, 398, 46, C.green);
  return slide;
}
