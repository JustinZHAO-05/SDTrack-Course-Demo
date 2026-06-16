import { C, base, title, label, panel, formula } from "./theme.mjs";

export async function slide12(presentation, ctx) {
  const slide = presentation.slides.add();
  base(slide, ctx, 12, "BACKUP Q&A");
  title(slide, ctx, "Q&A 聚焦三个高概率问题：表征、能耗和改进可验证性", "备份页用于 3 分钟问答，回答保持公式、数据和工程入口三类证据。");

  const qs = [
    ["Q1: GTP 为什么能利用视觉预训练？", "三通道 GTP 维持 image-like tensor 形式，首层卷积接口保持稳定；事件信息通过 C+、C-、Ctraj 进入通道语义。"],
    ["Q2: SNN 能耗结论如何理解？", "论文使用 45 nm 参考常数估计 MAC 与 AC 能耗，spike rate 控制 AC 项规模；真实 GPU 功耗需要硬件实测补充。"],
    ["Q3: ATR-GTP 如何验证？", "固定同一序列集合、checkpoint 和 evaluator，比较 baseline、zero、weak、fixed1、strong、adaptive、adaptive_smooth 七组输入。"]
  ];
  qs.forEach((q, idx) => {
    const y = 176 + idx * 126;
    panel(slide, ctx, 62, y, 700, 96, C.white, C.line);
    label(slide, ctx, q[0], 82, y + 12, 650, 22, { size: 15, bold: true, color: [C.blue, C.green, C.amber][idx], insets: { left: 0, right: 0, top: 0, bottom: 0 } });
    label(slide, ctx, q[1], 82, y + 42, 650, 40, { size: 13, color: C.ink, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  });
  panel(slide, ctx, 812, 176, 300, 348, C.ink, C.ink);
  label(slide, ctx, "一页式公式索引", 836, 202, 180, 28, { size: 17, bold: true, color: C.paper, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  formula(slide, ctx, "IoU = |Bpred ∩ Bgt| / |Bpred ∪ Bgt|", 836, 252, 230, 48, C.cyan);
  formula(slide, ctx, "AUC = mean Success(θ)", 836, 318, 230, 48, C.green);
  formula(slide, ctx, "E = T(E_MAC·FL + E_AC·FL·fr)", 836, 384, 230, 48, C.amber);
  label(slide, ctx, "答辩原则: 每个回答都落回模型部件、定量指标和复现实验入口。", 836, 458, 230, 44, { size: 12, color: C.paper, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  return slide;
}
