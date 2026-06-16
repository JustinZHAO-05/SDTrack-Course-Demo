import { C, base, title, image, caseImg, label, miniTable } from "./theme.mjs";

export async function slide10(presentation, ctx) {
  const slide = presentation.slides.add();
  base(slide, ctx, 10, "BACKUP CASES");
  title(slide, ctx, "成功与失败案例应按属性归因，而非只展示单帧框图", "报告中将失败样例转化为低照度、高速、背景干扰和相似目标四类机制解释。");

  await image(slide, ctx, caseImg("caseboard_schematic.png"), 54, 166, 650, 418, "case board schematic");
  miniTable(slide, ctx, [
    ["Case type", "Primary signal", "Expected SDTrack behavior"],
    ["low light", "event edge dominates", "RGB ambiguity reduced"],
    ["fast motion", "temporal trail", "GTP trajectory helps localization"],
    ["similar target", "template-search attention", "risk of identity switch"],
    ["background burst", "event density spike", "downweight trail"]
  ], 744, 190, 400, 38);
  label(slide, ctx,
    "答辩讲法: 每一类案例都对应一个模型部件。GTP 对运动边界敏感，IPL 对 template-search 几何关系敏感，SNN attention 对目标相关 token 敏感，ATR-GTP 对事件密度变化敏感。",
    744, 424, 400, 94, { size: 13.5, color: C.ink, fill: "#FDFBF7", line: C.line, insets: { left: 12, right: 12, top: 8, bottom: 8 } });
  label(slide, ctx, "素材生成: python -m src.visualize_cases --cases outputs/metrics/.../failure_cases.json --out outputs/cases", 744, 548, 400, 40, { size: 10.5, color: C.muted, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  return slide;
}
