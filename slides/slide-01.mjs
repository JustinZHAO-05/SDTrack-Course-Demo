import { C, base, title, metric, label, panel, formula } from "./theme.mjs";

export async function slide01(presentation, ctx) {
  const slide = presentation.slides.add();
  base(slide, ctx, 1, "PAPER THESIS");
  title(slide, ctx, "SDTrack 把事件跟踪问题压缩为低能耗 SNN 推理问题", "CVPR 2026 | Event-based Tracking via Spiking Neural Networks | 3 分钟主讲版");

  label(slide, ctx, "核心判断", 54, 184, 92, 24, { size: 13, bold: true, color: C.blue, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  label(slide, ctx,
    "论文的关键贡献在于把异步事件流转换为兼容视觉预训练权重的 GTP 三通道输入，并用 IPL 与 Spiking MetaFormer 建立 template-search 交互。最终模型在 FE108/VisEvent/FELT 上保持强精度，同时理论能耗处于 mJ 级。",
    54, 216, 705, 92, { size: 17, color: C.ink, insets: { left: 0, right: 0, top: 0, bottom: 0 } });

  formula(slide, ctx, "e_k=(x_k,y_k,t_k,p_k),  p_k in {-1,+1}    ->    GTP(C+, C-, Ctraj)    ->    SNN tracker", 54, 332, 705, 54, C.cyan);
  panel(slide, ctx, 805, 166, 360, 302, C.ink, C.ink);
  label(slide, ctx, "报告交付证据链", 824, 186, 250, 30, { size: 18, bold: true, color: C.paper, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  label(slide, ctx,
    "1. 论文机制逐层拆解\n2. FE108 + VisEvent 官方结果包独立复算\n3. 机制图、曲线图、能耗图统一生成\n4. ATR-GTP 七组输入级改进与消融协议\n5. LaTeX PDF + editable PPTX + run_all",
    824, 228, 315, 170, { size: 15, color: C.paper, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  label(slide, ctx, "提交占位: 序号 + SDTrack + 姓名1-4", 824, 416, 320, 24, { size: 11, color: "#C9D7E3", insets: { left: 0, right: 0, top: 0, bottom: 0 } });

  metric(slide, ctx, 54, 500, 250, "59.0 / 91.3", "FE108 AUC / PR", "SDTrack-Tiny-1x4 paper", C.blue);
  metric(slide, ctx, 330, 500, 250, "19.61M", "parameters", "Tiny variant", C.green);
  metric(slide, ctx, 606, 500, 250, "8.16 mJ", "theoretical energy", "45 nm estimate", C.amber);
  metric(slide, ctx, 882, 500, 250, "204 seq.", "independent recompute", "153493 frames total", C.red);
  return slide;
}
