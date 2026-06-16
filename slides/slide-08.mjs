import { C, base, title, image, img, label, miniTable, formula } from "./theme.mjs";

export async function slide08(presentation, ctx) {
  const slide = presentation.slides.add();
  base(slide, ctx, 8, "REPRODUCTION");
  title(slide, ctx, "公开预测框独立复算验证了 SDTrack 的跨数据集排序稳定性", "Python evaluator 统一读取作者结果包、FE108/VisEvent 真值，计算 IoU、Success Plot、AUC 与 PR20。");

  await image(slide, ctx, img("fe108_recomputed_auc.png"), 54, 170, 570, 236, "FE108 recomputed AUC");
  await image(slide, ctx, img("visevent_recomputed_auc.png"), 54, 420, 570, 202, "VisEvent recomputed AUC");
  miniTable(slide, ctx, [
    ["Tracker", "Seq.", "Frames", "AUC", "PR20"],
    ["SDTrack-Base", "32", "59688", "60.15", "90.83"],
    ["SDTrack-Tiny", "32", "59688", "59.29", "91.04"],
    ["VE Base", "172", "93805", "34.49", "45.19"],
    ["VE Tiny", "172", "93805", "33.21", "43.78"],
    ["VE SNNTrack", "172", "93805", "31.61", "44.12"]
  ], 660, 178, 486, 31);
  label(slide, ctx,
    "解释: FE108 中 Base/Tiny 位列前二，VisEvent 中二者仍位列前二。Tiny 的中心精度接近 Base，Base 的优势更多来自框重叠质量和复杂场景下的尺度控制。",
    660, 388, 486, 94, { size: 13.2, color: C.ink, fill: "#FDFBF7", line: C.line, insets: { left: 12, right: 12, top: 8, bottom: 8 } });
  formula(slide, ctx, "AUC = mean_θ mean_t 1[IoU_t >= θ],  PR20 = mean_t 1[||c_pred-c_gt||_2 <= 20]", 660, 506, 486, 48, C.cyan);
  label(slide, ctx, "代码入口: python -m src.eval_official_bundle --results-root ... --gt ... --out outputs/metrics/*_official_methods", 660, 574, 486, 38, { size: 10.5, color: C.muted, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  return slide;
}
