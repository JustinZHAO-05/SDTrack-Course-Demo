import path from "node:path";

export const C = {
  ink: "#101820",
  paper: "#F7F3EA",
  paper2: "#EFE7D7",
  line: "#D7C9B0",
  muted: "#6D6A63",
  blue: "#1F5E9C",
  cyan: "#2EA6A6",
  red: "#C54A3D",
  amber: "#C98B27",
  green: "#41846A",
  white: "#FFFFFF",
  dark: "#17212B",
};

export function img(name) {
  return path.resolve("outputs", "figures", name);
}

export function caseImg(name) {
  return path.resolve("outputs", "cases", name);
}

export function base(slide, ctx, page, kickerText) {
  ctx.addShape(slide, { x: 0, y: 0, w: ctx.W, h: ctx.H, fill: C.paper, line: ctx.line(C.paper, 0) });
  ctx.addShape(slide, { x: 0, y: 0, w: 34, h: ctx.H, fill: C.ink, line: ctx.line(C.ink, 0) });
  ctx.addText(slide, {
    name: `kicker-${page}-marker`,
    text: String(page).padStart(2, "0"),
    x: 50,
    y: 34,
    w: 42,
    h: 26,
    fontSize: 13,
    bold: true,
    color: C.paper,
    fill: C.blue,
    align: "center",
    valign: "middle",
    insets: { left: 0, right: 0, top: 0, bottom: 0 },
  });
  ctx.addText(slide, {
    name: `kicker-${page}-label`,
    text: kickerText,
    x: 98,
    y: 34,
    w: 360,
    h: 26,
    fontSize: 13,
    bold: true,
    color: C.blue,
    align: "left",
    valign: "middle",
    insets: { left: 0, right: 0, top: 0, bottom: 0 },
  });
  ctx.addShape(slide, { x: 50, y: 674, w: 1100, h: 1.2, fill: C.line, line: ctx.line(C.line, 0) });
  ctx.addText(slide, {
    text: "SDTrack final report | CVPR 2026 paper reading + reproducible evidence",
    x: 50,
    y: 684,
    w: 700,
    h: 18,
    fontSize: 10,
    color: C.muted,
  });
  ctx.addText(slide, {
    text: `${page}/12`,
    x: 1170,
    y: 682,
    w: 55,
    h: 20,
    fontSize: 11,
    bold: true,
    color: C.muted,
    align: "right",
  });
}

export function title(slide, ctx, text, sub = "") {
  ctx.addText(slide, {
    text,
    x: 50,
    y: 76,
    w: 1060,
    h: 58,
    fontSize: text.length > 32 ? 26 : text.length > 24 ? 28 : 32,
    bold: true,
    color: C.ink,
    typeface: "Microsoft YaHei",
    insets: { left: 0, right: 0, top: 0, bottom: 0 },
  });
  if (sub) {
    ctx.addText(slide, {
      text: sub,
      x: 52,
      y: 142,
      w: 1060,
      h: 26,
      fontSize: 14,
      color: C.muted,
      typeface: "Microsoft YaHei",
      insets: { left: 0, right: 0, top: 0, bottom: 0 },
    });
  }
}

export function panel(slide, ctx, x, y, w, h, fill = C.white, line = C.line) {
  return ctx.addShape(slide, {
    x,
    y,
    w,
    h,
    fill,
    line: ctx.line(line, 1),
  });
}

export function label(slide, ctx, text, x, y, w, h, opts = {}) {
  return ctx.addText(slide, {
    text,
    x,
    y,
    w,
    h,
    fontSize: opts.size ?? 13,
    bold: opts.bold ?? false,
    color: opts.color ?? C.ink,
    fill: opts.fill ?? "#00000000",
    line: ctx.line(opts.line ?? "#00000000", opts.lineWidth ?? 0),
    align: opts.align ?? "left",
    valign: opts.valign ?? "top",
    typeface: opts.face ?? "Microsoft YaHei",
    insets: opts.insets ?? { left: 8, right: 8, top: 6, bottom: 6 },
  });
}

export function metric(slide, ctx, x, y, w, value, labelText, note, accent = C.blue) {
  panel(slide, ctx, x, y, w, 100, C.white, C.line);
  ctx.addShape(slide, { x, y, w: 4, h: 100, fill: accent, line: ctx.line(accent, 0) });
  label(slide, ctx, value, x + 15, y + 8, w - 24, 34, { size: 26, bold: true, color: accent, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  label(slide, ctx, labelText, x + 15, y + 44, w - 24, 18, { size: 12, bold: true, color: C.ink, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  label(slide, ctx, note, x + 15, y + 70, w - 24, 16, { size: 10, color: C.muted, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
}

export function bullet(slide, ctx, items, x, y, w, lineH = 32, accent = C.blue) {
  items.forEach((item, idx) => {
    const yy = y + idx * lineH;
    ctx.addShape(slide, { x, y: yy + 10, w: 6, h: 6, fill: accent, line: ctx.line(accent, 0) });
    label(slide, ctx, item, x + 16, yy, w - 16, lineH, { size: 12.5, color: C.ink, insets: { left: 0, right: 0, top: 2, bottom: 2 } });
  });
}

export function formula(slide, ctx, text, x, y, w, h = 44, accent = C.cyan) {
  panel(slide, ctx, x, y, w, h, "#FDFBF7", C.line);
  ctx.addShape(slide, { x, y, w: 3, h, fill: accent, line: ctx.line(accent, 0) });
  label(slide, ctx, text, x + 12, y + 4, w - 20, h - 8, {
    size: 14,
    bold: true,
    color: C.ink,
    face: "Cambria Math",
    valign: "middle",
    insets: { left: 0, right: 0, top: 0, bottom: 0 },
  });
}

export async function image(slide, ctx, file, x, y, w, h, alt = "") {
  panel(slide, ctx, x, y, w, h, C.white, C.line);
  return ctx.addImage(slide, { path: file, x: x + 6, y: y + 6, w: w - 12, h: h - 12, fit: "contain", alt });
}

export function miniTable(slide, ctx, rows, x, y, w, rowH = 30) {
  panel(slide, ctx, x, y, w, rowH * rows.length + 12, C.white, C.line);
  rows.forEach((row, idx) => {
    const yy = y + idx * rowH;
    const fill = idx === 0 ? C.ink : idx % 2 === 0 ? "#FAF7EF" : C.white;
    ctx.addShape(slide, { x, y: yy, w, h: rowH, fill, line: ctx.line(C.line, 0.5) });
    row.forEach((cell, cidx) => {
      const cw = w / row.length;
      label(slide, ctx, cell, x + cidx * cw + 4, yy + 6, cw - 8, rowH - 18, {
        size: idx === 0 ? 9.5 : 10,
        bold: idx === 0,
        color: idx === 0 ? C.paper : C.ink,
        align: cidx === 0 ? "left" : "center",
        valign: "middle",
        insets: { left: 2, right: 2, top: 0, bottom: 0 },
      });
    });
  });
}

export function stage(slide, ctx, x, y, w, h, head, body, accent = C.blue) {
  panel(slide, ctx, x, y, w, h, C.white, C.line);
  ctx.addShape(slide, { x, y, w, h: 5, fill: accent, line: ctx.line(accent, 0) });
  label(slide, ctx, head, x + 10, y + 11, w - 20, 24, { size: 13, bold: true, color: accent, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  label(slide, ctx, body, x + 10, y + 38, w - 20, h - 44, { size: 11.5, color: C.ink, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
}

export function arrow(slide, ctx, x, y, w, color = C.muted) {
  ctx.addShape(slide, { x, y, w, h: 2, fill: color, line: ctx.line(color, 0) });
  ctx.addShape(slide, { x: x + w - 8, y: y - 4, w: 8, h: 10, fill: color, line: ctx.line(color, 0) });
}
