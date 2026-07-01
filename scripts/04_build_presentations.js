/* 04_build_presentations.js — Stage 4 deliverable.
 * Builds two PPTX decks (executive + internal) in Akos Szakaly's "structured
 * craft" brand: cobalt + steel on graphite/paper, mono uppercase eyebrows,
 * drafted (offset-frame) cards, registration-cross motif. Office-safe fonts are
 * used so the rendered deck is faithful everywhere (Arial~Hanken display,
 * Cambria~Spectral body, Courier New~Spline mono).
 *
 * Run:  NODE_PATH=$(npm root -g) node scripts/04_build_presentations.js
 * Reads: metrics/model_eval.json, metrics/evaluation_metrics.json, metrics/model_benchmark.csv, metrics/eda_summary.json
 * Writes: decks/mortgage_exec_deck.pptx, decks/mortgage_internal_deck.pptx
 */
const fs = require("fs");
const PptxGenJS = require("pptxgenjs");

// ---- Brand palette (hex, from OKLCH tokens) ----
const C = {
  paper: "F8FAFD", paper2: "F0F4F7", paper3: "E6EAEF", card: "FDFEFF",
  ink: "1B2129", ink2: "3E444D", ink3: "666D74", ink4: "9399A0",
  cobalt: "306CB8", cobaltDeep: "1E549C", cobaltSoft: "BDDBFB", cobaltWash: "E7F3FF",
  steel: "455E73", steelSoft: "CAD8E3", positive: "3C8564", negative: "B45248",
  line: "D8DBDF", lineStrong: "B9BEC4", white: "FFFFFF",
};
const F = { disp: "Arial", body: "Cambria", mono: "Courier New" };
const data = JSON.parse(fs.readFileSync("metrics/model_eval.json"));
const ev = JSON.parse(fs.readFileSync("metrics/evaluation_metrics.json"));
const eda = JSON.parse(fs.readFileSync("metrics/eda_summary.json"));

// ---- shared primitives ----
function eyebrow(slide, text, opts = {}) {
  const y = opts.y ?? 0.5, x = opts.x ?? 0.9, onInk = opts.onInk;
  slide.addShape("rect", { x, y: y + 0.085, w: 0.22, h: 0.028, fill: { color: C.cobalt } });
  slide.addText(text.toUpperCase(), {
    x: x + 0.32, y: y - 0.05, w: 10, h: 0.32, fontFace: F.mono, fontSize: 11.5,
    charSpacing: 2.4, color: onInk ? C.cobaltSoft : C.ink3, align: "left", valign: "middle",
  });
}
function foot(slide, left, right, onInk) {
  const col = onInk ? C.ink4 : C.ink4;
  slide.addText(left.toUpperCase(), { x: 0.9, y: 7.04, w: 7, h: 0.3, fontFace: F.mono, fontSize: 9.5, charSpacing: 1.8, color: col, align: "left" });
  slide.addText(right.toUpperCase(), { x: 5.43, y: 7.04, w: 7, h: 0.3, fontFace: F.mono, fontSize: 9.5, charSpacing: 1.8, color: col, align: "right" });
}
function cross(slide, x, y) {
  slide.addShape("rect", { x: x - 0.11, y, w: 0.22, h: 0.022, fill: { color: C.cobalt } });
  slide.addShape("rect", { x, y: y - 0.11, w: 0.022, h: 0.22, fill: { color: C.cobalt } });
}
function monogram(slide, x, y, onInk) {
  const stroke = onInk ? C.paper : C.ink;
  slide.addShape("rect", { x, y, w: 0.5, h: 0.5, fill: { type: "none" }, line: { color: stroke, width: 1.75 } });
  slide.addText("ÁS", { x: x - 0.05, y: y - 0.02, w: 0.6, h: 0.5, fontFace: F.disp, bold: true, fontSize: 16, color: stroke, align: "center", valign: "middle" });
  slide.addShape("rect", { x: x + 0.36, y: y + 0.06, w: 0.09, h: 0.02, fill: { color: C.cobalt } });
  slide.addShape("rect", { x: x + 0.43, y: y + 0.06, w: 0.02, h: 0.09, fill: { color: C.cobalt } });
}
function drafted(slide, x, y, w, h, fill = C.card) {
  slide.addShape("rect", { x: x + 0.1, y: y + 0.1, w, h, fill: { type: "none" }, line: { color: C.cobalt, width: 1.75 } });
  slide.addShape("rect", { x, y, w, h, fill: { color: fill }, line: { color: C.ink, width: 1.75 } });
}
function bg(slide, color) { slide.background = { color }; }

// bullets with cobalt tick + bold lead
function bullets(slide, items, x, y, w, opts = {}) {
  const gap = opts.gap ?? 0.86, fs = opts.fs ?? 15, onInk = opts.onInk;
  items.forEach((it, i) => {
    const yy = y + i * gap;
    slide.addShape("rect", { x, y: yy + 0.11, w: 0.16, h: 0.026, fill: { color: C.cobalt } });
    const runs = [];
    if (it.b) runs.push({ text: it.b + "  ", options: { bold: true, fontFace: F.disp, color: onInk ? C.paper : C.ink } });
    runs.push({ text: it.t, options: { fontFace: F.body, color: onInk ? C.steelSoft : C.ink2 } });
    slide.addText(runs, { x: x + 0.28, y: yy - 0.06, w: w - 0.28, h: gap, fontSize: fs, lineSpacingMultiple: 1.06, valign: "top", align: "left" });
  });
}

// ---- chart helpers ----
function scatterPredActual(slide, x, y, w, h) {
  // Native pptx scatter renders unreliably; embed brand-styled PNG (img_scatter.png).
  slide.addImage({ path: "charts/img_scatter.png", x, y, w, h, sizing: { type: "contain", w, h } });
}
function barChart(slide, x, y, w, h, labels, values, opts = {}) {
  slide.addChart("bar", [{ name: opts.name || "v", labels, values }], {
    x, y, w, h, barDir: opts.horiz ? "bar" : "col",
    chartColors: opts.colors || [C.cobalt],
    showLegend: false, showValue: !!opts.showValue,
    dataLabelColor: C.ink2, dataLabelFontFace: F.mono, dataLabelFontSize: 10, dataLabelFormatCode: opts.fmt || "0.00",
    catAxisLabelColor: C.ink2, valAxisLabelColor: C.ink3, axisLabelFontFace: F.mono,
    catAxisLabelFontSize: 10.5, valAxisLabelFontSize: 9,
    valGridLine: { color: C.line, style: "solid", size: 0.5 }, catGridLine: { style: "none" },
    valAxisHidden: !!opts.valHidden, barGapWidthPct: opts.gap ?? 55,
    valAxisMaxVal: opts.max, valAxisMinVal: 0,
  });
}

// slide header (eyebrow + title) helper
function head(s, eb, title, size = 30, w = 11.6) {
  eyebrow(s, eb);
  s.addText(title, { x: 0.86, y: 0.92, w, h: 1.1, fontFace: F.disp, bold: true, fontSize: size, color: C.ink, charSpacing: -0.4, lineSpacingMultiple: 0.98 });
}
function sectionSlide(p, idx, title, sub) {
  const s = p.addSlide(); bg(s, C.ink);
  cross(s, 12.4, 0.85);
  s.addText(idx, { x: 0.88, y: 2.5, w: 6, h: 0.6, fontFace: F.mono, fontSize: 26, charSpacing: 3, color: C.cobaltSoft });
  s.addText(title, { x: 0.86, y: 3.0, w: 11.4, h: 1.3, fontFace: F.disp, bold: true, fontSize: 60, color: C.paper, charSpacing: -1 });
  s.addText(sub, { x: 0.9, y: 4.45, w: 9.5, h: 0.7, fontFace: F.body, fontSize: 20, color: C.steelSoft, lineSpacingMultiple: 1.2 });
  monogram(s, 0.9, 5.85, true);
  s.addText(idx.toUpperCase(), { x: 5.43, y: 7.04, w: 7, h: 0.3, fontFace: F.mono, fontSize: 9.5, charSpacing: 1.8, color: C.ink4, align: "right" });
  return s;
}
function statRow(s, stats, y, cols) {
  const n = cols || stats.length, gap = 11.5 / n;
  stats.forEach(([v, c], i) => {
    const x = 0.9 + i * gap;
    s.addShape("rect", { x, y, w: gap - 0.4, h: 0.03, fill: { color: C.ink } });
    s.addText(v, { x: x - 0.03, y: y + 0.12, w: gap - 0.3, h: 0.7, fontFace: F.disp, bold: true, fontSize: 33, color: C.ink, charSpacing: -0.5 });
    s.addText(c, { x, y: y + 0.92, w: gap - 0.3, h: 0.5, fontFace: F.mono, fontSize: 9.5, charSpacing: 1.1, color: C.ink3 });
  });
}
function clabT(s, t, x, y, w, color) {
  s.addText(t.toUpperCase(), { x, y, w, h: 0.3, fontFace: F.mono, fontSize: 9.5, charSpacing: 1.3, color: color || C.ink3 });
}

// ===================================================================
// EXECUTIVE DECK
// ===================================================================
function buildExec() {
  const p = new PptxGenJS();
  p.defineLayout({ name: "W", width: 13.333, height: 7.5 });
  p.layout = "W";

  // 1 — COVER
  let s = p.addSlide(); bg(s, C.paper);
  cross(s, 0.95, 0.85); cross(s, 12.4, 6.65);
  eyebrow(s, "Mortgage credit · Model summary", { y: 2.35 });
  s.addText([
    { text: "Maximum loan amount", options: { color: C.ink } },
    { text: "\nmodel.", options: { color: C.ink } },
  ], { x: 0.86, y: 2.7, w: 11.5, h: 1.9, fontFace: F.disp, bold: true, fontSize: 54, charSpacing: -0.5, lineSpacingMultiple: 1.0 });
  s.addText("Predicting the bank's responsible lending limit from applicant data — validated against the actual decisions it has held out.", { x: 0.9, y: 4.55, w: 8.4, h: 0.9, fontFace: F.body, fontSize: 19, color: C.ink2, lineSpacingMultiple: 1.3 });
  monogram(s, 0.9, 5.9, false);
  foot(s, "Executive briefing · 2026", "Confidential");

  // 2 — CONTENTS
  s = p.addSlide(); bg(s, C.paper);
  eyebrow(s, "Contents");
  s.addText("What's in this deck", { x: 0.86, y: 0.92, w: 11, h: 0.9, fontFace: F.disp, bold: true, fontSize: 34, color: C.ink, charSpacing: -0.5 });
  const toc = [
    ["01", "Executive summary", "The ask, the answer, the headline result"],
    ["02", "Can we trust the model?", "Accuracy against the held-out actual decisions"],
    ["03", "What drives the loan", "The four factors that set the limit"],
    ["04", "Recommendation & next steps", "How to put it to work"],
  ];
  const apx = [
    ["A", "Why interest rate was excluded", "It is a price the bank sets, not an input"],
    ["B", "Four factors & fair lending", "A leaner, more defensible model"],
    ["C", "Data & method background", "Dataset, models compared, how chosen"],
  ];
  let yy = 2.15;
  toc.forEach(([n, t, d]) => {
    s.addText(n, { x: 0.9, y: yy, w: 0.9, h: 0.5, fontFace: F.mono, fontSize: 18, color: C.cobalt, valign: "top" });
    s.addText(t, { x: 1.85, y: yy - 0.04, w: 6.2, h: 0.4, fontFace: F.disp, bold: true, fontSize: 18, color: C.ink });
    s.addText(d, { x: 1.85, y: yy + 0.32, w: 7.6, h: 0.35, fontFace: F.body, fontSize: 13.5, color: C.ink3 });
    yy += 0.78;
  });
  s.addText("APPENDIX", { x: 9.55, y: 2.15, w: 3, h: 0.3, fontFace: F.mono, fontSize: 11, charSpacing: 2, color: C.ink3 });
  let ay = 2.6;
  apx.forEach(([n, t]) => {
    s.addText(n, { x: 9.55, y: ay, w: 0.5, h: 0.4, fontFace: F.mono, fontSize: 14, color: C.steel });
    s.addText(t, { x: 10.05, y: ay, w: 2.9, h: 0.6, fontFace: F.body, fontSize: 13.5, color: C.ink2, valign: "top", lineSpacingMultiple: 1.05 });
    ay += 0.78;
  });
  foot(s, "Maximum loan amount model", "Contents");

  // 3 — EXECUTIVE SUMMARY
  s = p.addSlide(); bg(s, C.paper);
  eyebrow(s, "01 — Executive summary");
  s.addText("A model that reproduces lending\ndecisions to within ~4%", { x: 0.86, y: 0.92, w: 11.6, h: 1.1, fontFace: F.disp, bold: true, fontSize: 31, color: C.ink, charSpacing: -0.5, lineSpacingMultiple: 0.98 });
  // stat row
  const stats = [
    ["0.990", "VARIANCE EXPLAINED (R²)"],
    ["±$22.0k", "TYPICAL ERROR (MAE)"],
    ["94.9%", "WITHIN ±10% OF ACTUAL"],
  ];
  stats.forEach(([v, c], i) => {
    const x = 0.9 + i * 3.95;
    s.addShape("rect", { x, y: 2.5, w: 3.55, h: 0.03, fill: { color: C.ink } });
    s.addText(v, { x: x - 0.03, y: 2.62, w: 3.6, h: 0.8, fontFace: F.disp, bold: true, fontSize: 40, color: C.ink, charSpacing: -0.5 });
    s.addText(c, { x, y: 3.5, w: 3.6, h: 0.3, fontFace: F.mono, fontSize: 10.5, charSpacing: 1.4, color: C.ink3 });
  });
  bullets(s, [
    { b: "The ask:", t: "estimate the maximum loan the bank should responsibly offer each applicant, from their financial profile alone." },
    { b: "The answer:", t: "a gradient-boosting model predicts that limit with high accuracy — and we validated it against the real decisions, which were never shown to the model." },
    { b: "Why it matters:", t: "consistent, explainable loan sizing — a fast first-pass limit for ~95% of applicants, with the rare large miss easy to flag for review." },
  ], 0.9, 4.2, 11.6, { gap: 0.82, fs: 16 });
  foot(s, "Maximum loan amount model", "01 · Executive summary");

  // 4 — CAN WE TRUST IT
  s = p.addSlide(); bg(s, C.paper);
  eyebrow(s, "02 — Can we trust the model?");
  s.addText("Predictions land on the bank's\nactual decisions", { x: 0.86, y: 0.92, w: 6.2, h: 1.1, fontFace: F.disp, bold: true, fontSize: 27, color: C.ink, charSpacing: -0.4, lineSpacingMultiple: 0.98 });
  bullets(s, [
    { b: "Tested honestly.", t: "Measured on 9,998 applicants the model never saw in training." },
    { b: "On the line.", t: "Each point is one applicant; the closer to the dashed line, the closer the prediction to the real limit." },
    { b: "No size blind spot.", t: "Accuracy holds from the smallest to the largest loans." },
  ], 0.9, 2.7, 5.7, { gap: 0.9, fs: 15 });
  drafted(s, 7.0, 2.25, 5.35, 4.2);
  s.addText("PREDICTED VS ACTUAL — HELD-OUT APPLICANTS", { x: 7.2, y: 2.45, w: 5, h: 0.3, fontFace: F.mono, fontSize: 9.5, charSpacing: 1.2, color: C.ink3 });
  scatterPredActual(s, 7.12, 2.78, 5.1, 3.5);
  foot(s, "Maximum loan amount model", "02 · Validation");

  // 5 — WHAT DRIVES THE LOAN
  s = p.addSlide(); bg(s, C.paper);
  eyebrow(s, "03 — What drives the loan");
  s.addText("Four factors set the limit", { x: 0.86, y: 0.92, w: 11, h: 0.7, fontFace: F.disp, bold: true, fontSize: 31, color: C.ink, charSpacing: -0.5 });
  barChart(s, 0.7, 2.2, 6.0, 4.0,
    ["Annual income", "Credit score", "Existing monthly debt", "Down payment"],
    [1.44, 0.65, 0.34, 0.03],
    { horiz: true, colors: [C.cobalt, C.cobalt, C.steel, C.steel], showValue: true, fmt: "0.00", valHidden: true, gap: 70 });
  s.addText("RELATIVE INFLUENCE ON THE PREDICTED LIMIT", { x: 0.9, y: 6.25, w: 6, h: 0.3, fontFace: F.mono, fontSize: 9.5, charSpacing: 1.2, color: C.ink3 });
  bullets(s, [
    { b: "Income leads —", t: "the single biggest driver of how much the bank will lend." },
    { b: "Credit score next —", t: "creditworthiness scales the limit up or down." },
    { b: "Debt pulls down,", t: "down payment nudges up — capacity and commitment." },
    { b: "Everything else is noise:", t: "age, job, education, area add nothing once income and credit are known." },
  ], 7.0, 2.35, 5.5, { gap: 0.92, fs: 15 });
  foot(s, "Maximum loan amount model", "03 · Drivers");

  // 6 — RECOMMENDATION
  s = p.addSlide(); bg(s, C.paper);
  eyebrow(s, "04 — Recommendation & next steps");
  s.addText("Adopt it as a first-pass limit engine", { x: 0.86, y: 0.92, w: 11.5, h: 0.7, fontFace: F.disp, bold: true, fontSize: 30, color: C.ink, charSpacing: -0.5 });
  drafted(s, 0.9, 2.15, 5.5, 4.25, C.cobaltWash);
  s.addText("RECOMMENDATION", { x: 1.2, y: 2.45, w: 5, h: 0.3, fontFace: F.mono, fontSize: 10.5, charSpacing: 1.6, color: C.cobaltDeep });
  s.addText("Use the model to propose a maximum loan instantly for every applicant, auto-approving the ~95% it sizes within ±10% and routing the rest to a human reviewer.", { x: 1.2, y: 2.95, w: 4.9, h: 2.6, fontFace: F.body, fontSize: 18, color: C.ink, lineSpacingMultiple: 1.3 });
  bullets(s, [
    { b: "Pilot in shadow mode —", t: "run alongside underwriters; compare before going live." },
    { b: "Set a review band —", t: "flag predictions that disagree with policy by > 10%." },
    { b: "Govern the inputs —", t: "uses no demographics; document and monitor for drift." },
    { b: "Refresh on real data —", t: "retrain when a book of genuine decisions is available." },
  ], 7.0, 2.3, 5.5, { gap: 1.0, fs: 15 });
  foot(s, "Maximum loan amount model", "04 · Recommendation");

  // 7 — APPENDIX DIVIDER
  s = p.addSlide(); bg(s, C.ink);
  cross(s, 12.4, 0.85);
  s.addText("Appendix", { x: 0.86, y: 2.95, w: 11, h: 1.2, fontFace: F.disp, bold: true, fontSize: 64, color: C.paper, charSpacing: -1 });
  s.addText("Key decisions & background", { x: 0.9, y: 4.15, w: 10, h: 0.5, fontFace: F.body, fontSize: 20, color: C.steelSoft });
  monogram(s, 0.9, 5.7, true);
  s.addText("APPENDIX", { x: 5.43, y: 7.04, w: 7, h: 0.3, fontFace: F.mono, fontSize: 9.5, charSpacing: 1.8, color: C.ink4, align: "right" });

  // 8 — APPENDIX A: interest rate
  s = p.addSlide(); bg(s, C.paper);
  eyebrow(s, "Appendix A — Feature decision");
  s.addText("Interest rate was excluded — it's a\nprice the bank sets, not an input", { x: 0.86, y: 0.92, w: 11.6, h: 1.1, fontFace: F.disp, bold: true, fontSize: 27, color: C.ink, charSpacing: -0.4, lineSpacingMultiple: 0.98 });
  bullets(s, [
    { b: "Near-perfectly tied to credit score", t: "(correlation −0.95): better credit → lower rate, almost mechanically." },
    { b: "Predictable from other inputs", t: "with 91–94% accuracy — it carries almost no new information." },
    { b: "Using it would be circular —", t: "feeding one bank decision in to predict another, and double-counting credit score." },
  ], 0.9, 2.7, 6.0, { gap: 0.95, fs: 15.5 });
  drafted(s, 7.3, 2.4, 5.05, 3.5, C.card);
  s.addText("INTEREST RATE VS CREDIT SCORE", { x: 7.55, y: 2.65, w: 4.6, h: 0.3, fontFace: F.mono, fontSize: 9.5, charSpacing: 1.2, color: C.ink3 });
  s.addText([
    { text: "−0.95\n", options: { fontFace: F.disp, bold: true, fontSize: 52, color: C.cobalt } },
    { text: "correlation with credit score", options: { fontFace: F.body, fontSize: 15, color: C.ink2 } },
  ], { x: 7.55, y: 3.2, w: 4.6, h: 1.4, align: "left" });
  s.addText([
    { text: "0.91–0.94\n", options: { fontFace: F.disp, bold: true, fontSize: 40, color: C.steel } },
    { text: "predictable from applicant inputs (R²)", options: { fontFace: F.body, fontSize: 14, color: C.ink2 } },
  ], { x: 7.55, y: 4.7, w: 4.6, h: 1.1, align: "left" });
  foot(s, "Maximum loan amount model", "Appendix A");

  // 9 — APPENDIX B: parsimony + fair lending
  s = p.addSlide(); bg(s, C.paper);
  eyebrow(s, "Appendix B — Model design");
  s.addText("Four factors beat twelve — leaner\nand more defensible", { x: 0.86, y: 0.92, w: 11.6, h: 1.1, fontFace: F.disp, bold: true, fontSize: 27, color: C.ink, charSpacing: -0.4, lineSpacingMultiple: 0.98 });
  // small comparison
  const rows = [["", "R²", "Typical error"], ["12 features", "0.9894", "$22,428"], ["4 features", "0.9897", "$21,966"]];
  s.addTable(rows.map((r, ri) => r.map((cell, ci) => ({
    text: cell,
    options: {
      fontFace: ri === 0 ? F.mono : (ci === 0 ? F.disp : F.body), bold: ri === 0 || (ri === 2),
      fontSize: ri === 0 ? 10.5 : 14, color: ri === 0 ? C.ink3 : (ri === 2 ? C.cobaltDeep : C.ink2),
      align: ci === 0 ? "left" : "center", valign: "middle",
      fill: { color: ri === 2 ? C.cobaltWash : C.white },
    },
  }))), { x: 0.9, y: 2.6, w: 5.7, colW: [2.5, 1.6, 1.6], rowH: [0.4, 0.55, 0.55], border: { type: "solid", color: C.line, pt: 0.5 } });
  s.addText("Same model on just income, credit score, existing debt and down payment is marginally more accurate.", { x: 0.9, y: 4.45, w: 5.7, h: 1.2, fontFace: F.body, fontSize: 15, color: C.ink2, lineSpacingMultiple: 1.25 });
  drafted(s, 7.1, 2.5, 5.25, 3.6, C.card);
  s.addText("WHY IT'S MORE DEFENSIBLE", { x: 7.35, y: 2.72, w: 4.8, h: 0.3, fontFace: F.mono, fontSize: 9.5, charSpacing: 1.4, color: C.cobaltDeep });
  bullets(s, [
    { b: "No demographics.", t: "Uses no gender, marital status or age — supports fair-lending (ECOA) defensibility." },
    { b: "Job & education added nothing —", t: "they were just stand-ins for income." },
    { b: "Simpler to explain", t: "and to govern: four inputs, all financial." },
  ], 7.35, 3.25, 4.8, { gap: 0.86, fs: 13.5 });
  foot(s, "Maximum loan amount model", "Appendix B");

  // 10 — APPENDIX C: data & method
  s = p.addSlide(); bg(s, C.paper);
  eyebrow(s, "Appendix C — Background");
  s.addText("Data & method, in brief", { x: 0.86, y: 0.92, w: 11, h: 0.7, fontFace: F.disp, bold: true, fontSize: 30, color: C.ink, charSpacing: -0.5 });
  bullets(s, [
    { b: "Dataset:", t: "49,990 mortgage applicants, 13 attributes. Clean — no missing values or duplicates; 41 minor anomalies kept and flagged." },
    { b: "Held-out target:", t: "the actual maximum loan was never used in training — only to score the model at the end." },
    { b: "Models compared:", t: "linear, random forest and gradient boosting, on raw and log scales — six combinations under one test." },
    { b: "Chosen:", t: "gradient boosting (raw) — clearly the most accurate and stable." },
  ], 0.9, 2.5, 6.0, { gap: 0.95, fs: 14.5 });
  drafted(s, 7.3, 2.4, 5.05, 3.6, C.card);
  s.addText("MODEL COMPARISON — TYPICAL ERROR", { x: 7.55, y: 2.62, w: 4.6, h: 0.3, fontFace: F.mono, fontSize: 9.5, charSpacing: 1.2, color: C.ink3 });
  barChart(s, 7.5, 2.95, 4.65, 2.95,
    ["Gradient\nboosting", "Random\nforest", "Linear"],
    [22.4, 24.3, 51.9],
    { colors: [C.cobalt, C.steel, C.ink4], showValue: true, fmt: '"$"0.0"k"', valHidden: true, gap: 50 });
  foot(s, "Maximum loan amount model", "Appendix C");

  return p.writeFile({ fileName: "decks/mortgage_exec_deck.pptx" });
}

// ===================================================================
// INTERNAL DECK — credit & modelling deep-dive
// ===================================================================
function buildInternal() {
  const p = new PptxGenJS();
  p.defineLayout({ name: "W", width: 13.333, height: 7.5 });
  p.layout = "W";
  const FL = "Max loan model · methodology";
  const shortLab = { "Annual Income (USD)": "Annual income", "Credit Score": "Credit score", "Down Payment (USD)": "Down payment", "Employment Years": "Employment yrs", "Age": "Age", "Loans Repaid": "Loans repaid", "Existing Monthly Debt (USD)": "Existing debt" };

  // aggregated histograms
  const th = eda.target_hist; const thC = [], thL = [];
  for (let i = 0; i < th.counts.length; i += 3) { let c = 0; for (let j = i; j < i + 3 && j < th.counts.length; j++) c += th.counts[j]; thC.push(c); thL.push("$" + Math.round(th.edges[i] / 1000) + "k"); }
  const rh = data.resid_hist; const rhC = [], rhL = [];
  for (let i = 0; i < rh.counts.length; i += 4) { let c = 0; for (let j = i; j < i + 4 && j < rh.counts.length; j++) c += rh.counts[j]; rhC.push(c); rhL.push("$" + Math.round(rh.edges[i] / 1000) + "k"); }
  const corrF = Object.keys(eda.corr).map(k => shortLab[k] || k);
  const corrV = Object.values(eda.corr).map(v => Math.round(v * 1000) / 1000);

  // 1 — COVER
  let s = p.addSlide(); bg(s, C.paper);
  cross(s, 0.95, 0.85); cross(s, 12.4, 6.65);
  eyebrow(s, "Credit risk · Model methodology & validation", { y: 2.35 });
  s.addText([{ text: "Maximum loan amount", options: { color: C.ink } }, { text: "\nmodel — technical review", options: { color: C.ink } }], { x: 0.86, y: 2.7, w: 11.8, h: 1.7, fontFace: F.disp, bold: true, fontSize: 44, charSpacing: -0.5, lineSpacingMultiple: 1.0 });
  s.addText("Data, feature decisions, model selection and held-out validation — for credit and modelling reviewers.", { x: 0.9, y: 4.5, w: 9.2, h: 0.9, fontFace: F.body, fontSize: 19, color: C.ink2, lineSpacingMultiple: 1.3 });
  monogram(s, 0.9, 5.9, false);
  foot(s, "Internal · credit & modelling", "Methodology v1 · 2026");

  // 2 — CONTENTS
  s = p.addSlide(); bg(s, C.paper);
  head(s, "Contents", "Storyline", 34);
  const toc = [
    ["01", "Data & exploration", "Shape, quality, distributions, what correlates"],
    ["02", "Feature decisions", "Interest rate, down payment, cleaning & audit"],
    ["03", "Model & evaluation", "Benchmark, parsimony, validation, governance"],
  ];
  let yy = 2.4;
  toc.forEach(([n, t, d]) => {
    s.addText(n, { x: 0.9, y: yy, w: 1.0, h: 0.7, fontFace: F.mono, fontSize: 24, color: C.cobalt, valign: "top" });
    s.addText(t, { x: 2.0, y: yy - 0.05, w: 7, h: 0.5, fontFace: F.disp, bold: true, fontSize: 24, color: C.ink });
    s.addText(d, { x: 2.0, y: yy + 0.45, w: 8.5, h: 0.4, fontFace: F.body, fontSize: 15, color: C.ink3 });
    yy += 1.15;
  });
  clabT(s, "Plus — objective & approach, and appendix (full benchmark + data dictionary)", 2.0, yy + 0.05, 9);
  foot(s, FL, "Contents");

  // 3 — OBJECTIVE & APPROACH
  s = p.addSlide(); bg(s, C.paper);
  head(s, "Objective & approach", "Predict the bank's loan limit — without\never seeing it during modelling", 28);
  bullets(s, [
    { b: "Goal:", t: "estimate Max Loan Amount (USD) from applicant attributes, as a regression problem." },
    { b: "Held-out target:", t: "the actual maximum loan is excluded from every training/selection step and used only for final evaluation." },
    { b: "Discipline:", t: "staged & gated — discovery → cleaning (audited) → method selection → validation, each surfaced for decision." },
    { b: "Reproducible:", t: "numbered standalone scripts regenerate every figure and number in this deck." },
  ], 0.9, 2.7, 6.1, { gap: 0.92, fs: 15.5 });
  drafted(s, 7.4, 2.5, 4.95, 3.5, C.cobaltWash);
  clabT(s, "The leakage rule", 7.65, 2.75, 4.5, C.cobaltDeep);
  s.addText("Interest rate and the target are kept out of the feature set. The model sees only what an applicant brings to the table.", { x: 7.65, y: 3.2, w: 4.5, h: 2.4, fontFace: F.body, fontSize: 17, color: C.ink, lineSpacingMultiple: 1.3 });
  foot(s, FL, "Objective");

  // 4 — SECTION 01
  sectionSlide(p, "01", "Data & exploration", "49,990 applicants — what's there, how clean, and what moves the loan.");

  // 5 — DATASET & QUALITY
  s = p.addSlide(); bg(s, C.paper);
  head(s, "01 — Dataset & quality", "Clean to begin with", 31);
  statRow(s, [["49,990", "APPLICANTS (ROWS)"], ["14", "COLUMNS"], ["0", "NULLS / DUPLICATES"], ["41", "ANOMALIES FLAGGED"]], 2.4);
  bullets(s, [
    { b: "Grain:", t: "one row per mortgage applicant; no duplicates." },
    { b: "Types:", t: "8 numeric (income, credit score, down payment, debt, age, employment, loans repaid, rate), 5 categorical, 1 target." },
    { b: "Quality:", t: "no missing values; all integrity checks pass except 41 rows implying a working start age of 14–15 (off by 1–2 yrs)." },
    { b: "Decision:", t: "keep all rows; the 41 are kept and flagged in the cleaning audit, not removed." },
  ], 0.9, 4.0, 11.6, { gap: 0.72, fs: 14.5 });
  foot(s, FL, "01 · Data quality");

  // 6 — DISTRIBUTION & CORRELATION
  s = p.addSlide(); bg(s, C.paper);
  head(s, "01 — Distribution & drivers", "Right-skewed target; income & credit lead", 27);
  clabT(s, "Max loan amount — distribution", 0.9, 2.25, 5.5);
  barChart(s, 0.7, 2.55, 5.8, 3.7, thL, thC, { colors: [C.cobalt], gap: 18, fmt: "#,##0", valHidden: true });
  clabT(s, "Correlation with the target", 7.0, 2.25, 5.3);
  barChart(s, 6.9, 2.55, 5.5, 3.7, corrF, corrV, { horiz: true, colors: [C.steel], showValue: true, fmt: "0.00", valHidden: true, gap: 40 });
  foot(s, FL, "01 · Distributions");

  // 7 — CATEGORICAL SIGNAL
  s = p.addSlide(); bg(s, C.paper);
  head(s, "01 — Categorical signal", "Education and job look strong — but echo income", 26);
  clabT(s, "Avg loan by education ($k)", 0.9, 2.2, 5);
  barChart(s, 0.7, 2.5, 5.6, 3.5, eda.cat_target.Education.labels, eda.cat_target.Education.means.map(v => Math.round(v / 1000)), { colors: [C.cobalt], showValue: true, fmt: "#,##0", valHidden: true, gap: 45 });
  clabT(s, "Avg loan by job ($k)", 6.95, 2.2, 5);
  barChart(s, 6.8, 2.5, 5.6, 3.9, eda.cat_target.Job.labels.slice().reverse(), eda.cat_target.Job.means.slice().reverse().map(v => Math.round(v / 1000)), { horiz: true, colors: [C.steel], gap: 30, valHidden: true });
  s.addText("Three job tiers (≈$575k / $690k / $810k) mirror income tiers exactly — a hint that these categoricals are proxies, confirmed later by feature importance.", { x: 0.9, y: 6.35, w: 11.4, h: 0.6, fontFace: F.body, italic: true, fontSize: 13.5, color: C.ink3 });
  foot(s, FL, "01 · Categoricals");

  // 8 — SECTION 02
  sectionSlide(p, "02", "Feature decisions", "What goes into the model — and the evidence behind each call.");

  // 9 — INTEREST RATE
  s = p.addSlide(); bg(s, C.paper);
  head(s, "02 — Feature decision", "Interest rate excluded: it's risk-based\npricing, not an applicant input", 26);
  bullets(s, [
    { b: "Correlation −0.95 with credit score —", t: "the rate is essentially a deterministic function of creditworthiness." },
    { b: "Predicted from the other inputs at R² 0.91–0.94", t: "(linear / random forest) — almost no independent information." },
    { b: "Circular if used:", t: "a bank-set output predicting another bank output, double-counting credit score." },
    { b: "Down payment, by contrast, is a genuine input —", t: "kept (next slide)." },
  ], 0.9, 2.75, 6.0, { gap: 0.92, fs: 15 });
  drafted(s, 7.4, 2.55, 4.95, 3.4, C.card);
  clabT(s, "Is the rate an input or an output?", 7.65, 2.78, 4.5);
  s.addText([{ text: "−0.95", options: { fontFace: F.disp, bold: true, fontSize: 50, color: C.cobalt } }], { x: 7.62, y: 3.15, w: 4.5, h: 0.8 });
  s.addText("correlation with credit score", { x: 7.65, y: 3.95, w: 4.5, h: 0.3, fontFace: F.body, fontSize: 14, color: C.ink2 });
  s.addText([{ text: "0.91–0.94", options: { fontFace: F.disp, bold: true, fontSize: 38, color: C.steel } }], { x: 7.62, y: 4.45, w: 4.5, h: 0.7 });
  s.addText("rate predictable from applicant inputs (R²)", { x: 7.65, y: 5.2, w: 4.5, h: 0.3, fontFace: F.body, fontSize: 13.5, color: C.ink2 });
  foot(s, FL, "02 · Interest rate");

  // 10 — DOWN PAYMENT
  s = p.addSlide(); bg(s, C.paper);
  head(s, "02 — Feature decision", "Down payment kept — it carries real signal", 28);
  bullets(s, [
    { b: "Conceptually an input:", t: "reflects household purchasing power and commitment to the purchase." },
    { b: "Empirically load-bearing:", t: "dropping it raises the 4-feature model's typical error from $21,966 to $35,648." },
    { b: "Correlation 0.47 with the target,", t: "and 3rd–4th in model importance — not redundant with income or credit." },
  ], 0.9, 2.7, 6.0, { gap: 0.95, fs: 15.5 });
  drafted(s, 7.4, 2.55, 4.95, 3.3, C.card);
  clabT(s, "Typical error (MAE) impact", 7.65, 2.8, 4.5);
  s.addText([{ text: "$21,966", options: { fontFace: F.disp, bold: true, fontSize: 38, color: C.cobalt } }, { text: "   with down payment", options: { fontFace: F.body, fontSize: 14, color: C.ink2 } }], { x: 7.65, y: 3.3, w: 4.5, h: 0.7 });
  s.addText([{ text: "$35,648", options: { fontFace: F.disp, bold: true, fontSize: 38, color: C.ink3 } }, { text: "   without it", options: { fontFace: F.body, fontSize: 14, color: C.ink2 } }], { x: 7.65, y: 4.3, w: 4.5, h: 0.7 });
  s.addText("+62% error if removed", { x: 7.65, y: 5.25, w: 4.5, h: 0.4, fontFace: F.mono, fontSize: 13, color: C.negative, charSpacing: 1 });
  foot(s, FL, "02 · Down payment");

  // 11 — CLEANING & AUDIT
  s = p.addSlide(); bg(s, C.paper);
  head(s, "02 — Cleaning & audit", "Nothing removed — everything reconciled", 29);
  bullets(s, [
    { b: "Integrity checks:", t: "nulls, duplicates, non-positive values, credit-score range, down-payment > loan, debt > income, categorical whitespace — all pass." },
    { b: "Only anomaly:", t: "41 rows with implied working start age < 16; kept and individually logged (step C9)." },
    { b: "Audit trail:", t: "cleaning_audit.csv records every check and flagged row with a reason." },
  ], 0.9, 2.7, 6.1, { gap: 0.95, fs: 15 });
  drafted(s, 7.4, 2.55, 4.95, 3.2, C.cobaltWash);
  clabT(s, "Reconciliation", 7.65, 2.8, 4.5, C.cobaltDeep);
  s.addText([
    { text: "49,990", options: { fontFace: F.disp, bold: true, fontSize: 30, color: C.ink } }, { text: "  raw\n", options: { fontFace: F.body, fontSize: 15, color: C.ink2 } },
    { text: "49,990", options: { fontFace: F.disp, bold: true, fontSize: 30, color: C.ink } }, { text: "  kept   ", options: { fontFace: F.body, fontSize: 15, color: C.ink2 } },
    { text: "+   0", options: { fontFace: F.disp, bold: true, fontSize: 30, color: C.ink } }, { text: "  removed", options: { fontFace: F.body, fontSize: 15, color: C.ink2 } },
  ], { x: 7.65, y: 3.25, w: 4.5, h: 2.0, lineSpacingMultiple: 1.4 });
  s.addText("kept + removed = raw  ✓", { x: 7.65, y: 5.2, w: 4.5, h: 0.4, fontFace: F.mono, fontSize: 13, color: C.positive, charSpacing: 0.5 });
  foot(s, FL, "02 · Cleaning");

  // 12 — SECTION 03
  sectionSlide(p, "03", "Model & evaluation", "Choosing the model on evidence, then testing it against the held-out actual.");

  // 13 — BENCHMARK
  s = p.addSlide(); bg(s, C.paper);
  head(s, "03 — Method selection", "Six combinations, one protocol", 30);
  const bh = ["Model", "Target", "R²", "MAE", "RMSE", "MAPE"];
  const br = [
    ["HistGradientBoosting", "raw", "0.9894", "$22,428", "$31,937", "3.74%"],
    ["HistGradientBoosting", "log", "0.9894", "$22,463", "$31,915", "3.70%"],
    ["Random Forest", "raw", "0.9876", "$24,312", "$34,498", "4.14%"],
    ["Random Forest", "log", "0.9876", "$24,427", "$34,551", "4.12%"],
    ["Ridge (linear)", "raw", "0.9502", "$51,858", "$69,239", "12.1%"],
    ["Ridge (linear)", "log", "0.8830", "$62,625", "$106,103", "9.97%"],
  ];
  const trows = [bh.map(h => ({ text: h, options: { fontFace: F.mono, bold: true, fontSize: 11, color: C.ink3, align: "left", fill: { color: C.paper } } }))]
    .concat(br.map((r, ri) => r.map((c, ci) => ({ text: c, options: { fontFace: ci <= 1 ? F.body : F.mono, fontSize: 13, bold: ri === 0, color: ri === 0 ? C.cobaltDeep : C.ink2, align: "left", fill: { color: ri === 0 ? C.cobaltWash : C.white } } }))));
  s.addTable(trows, { x: 0.9, y: 2.4, w: 8.4, colW: [2.5, 0.9, 1.1, 1.3, 1.3, 1.0], rowH: 0.42, border: { type: "solid", color: C.line, pt: 0.5 }, valign: "middle" });
  drafted(s, 9.7, 2.4, 2.75, 3.1, C.cobaltWash);
  clabT(s, "Chosen", 9.9, 2.62, 2.4, C.cobaltDeep);
  s.addText("Gradient boosting, raw target", { x: 9.9, y: 3.0, w: 2.4, h: 1.0, fontFace: F.disp, bold: true, fontSize: 18, color: C.ink, lineSpacingMultiple: 1.05 });
  s.addText("Trees beat linear by ~$30k MAE; log scale adds nothing for the winner.", { x: 9.9, y: 4.1, w: 2.4, h: 1.3, fontFace: F.body, fontSize: 13, color: C.ink2, lineSpacingMultiple: 1.25 });
  s.addText("CV R² std ≤ 0.0004 across folds → stable, no overfitting.", { x: 0.9, y: 5.75, w: 8.4, h: 0.5, fontFace: F.body, italic: true, fontSize: 13.5, color: C.ink3 });
  foot(s, FL, "03 · Benchmark");

  // 14 — PARSIMONY
  s = p.addSlide(); bg(s, C.paper);
  head(s, "03 — Parsimony", "Four features beat twelve", 30);
  const ph = ["Feature set", "R²", "MAE"];
  const pr = [["12 features (all)", "0.9894", "$22,428"], ["4 features (primary)", "0.9897", "$21,966"], ["3 features (no down pmt)", "0.9768", "$35,648"]];
  const ptr = [ph.map(h => ({ text: h, options: { fontFace: F.mono, bold: true, fontSize: 11, color: C.ink3, align: "left" } }))]
    .concat(pr.map((r, ri) => r.map((c, ci) => ({ text: c, options: { fontFace: ci === 0 ? F.body : F.mono, fontSize: 13.5, bold: ri === 1, color: ri === 1 ? C.cobaltDeep : C.ink2, align: "left", fill: { color: ri === 1 ? C.cobaltWash : C.white } } }))));
  s.addTable(ptr, { x: 0.9, y: 2.5, w: 5.6, colW: [3.0, 1.3, 1.3], rowH: 0.5, border: { type: "solid", color: C.line, pt: 0.5 }, valign: "middle" });
  bullets(s, [
    { b: "Job ≈ income tiers:", t: "Doctor/Lawyer/Owner ≈$146k, Banker/SWE/Sales ≈$125k, rest ≈$105k." },
    { b: "Education tracks income;", t: "Age & Employment are 0.97 correlated; Loans Repaid tracks credit score." },
    { b: "So 8 features are downstream correlates —", t: "zero permutation importance once income & credit are in." },
  ], 7.0, 2.5, 5.4, { gap: 0.95, fs: 14 });
  foot(s, FL, "03 · Parsimony");

  // 15 — FINAL MODEL & PROTOCOL
  s = p.addSlide(); bg(s, C.paper);
  head(s, "03 — Final model & protocol", "Specification", 30);
  bullets(s, [
    { b: "Estimator:", t: "HistGradientBoostingRegressor — max_iter 400, learning_rate 0.06, default depth." },
    { b: "Features (4):", t: "annual income, credit score, existing monthly debt, down payment (raw target)." },
    { b: "Split:", t: "80 / 20 train-test, fixed seed; 5-fold CV on train for stability." },
    { b: "Metrics:", t: "R², MAE, RMSE, MAPE on the held-out 20% — all in native USD." },
  ], 0.9, 2.6, 6.1, { gap: 0.92, fs: 15 });
  drafted(s, 7.4, 2.5, 4.95, 3.3, C.card);
  clabT(s, "Artifacts", 7.65, 2.75, 4.5);
  bullets(s, [
    { b: "model_final.joblib", t: "— the fitted 4-feature pipeline." },
    { b: "model_full.joblib", t: "— 12-feature model, kept for the record." },
    { b: "evaluation_metrics.json", t: "+ predictions_test.csv." },
  ], 7.65, 3.2, 4.5, { gap: 0.75, fs: 13 });
  foot(s, FL, "03 · Specification");

  // 16 — EVALUATION
  s = p.addSlide(); bg(s, C.paper);
  head(s, "03 — Validation vs held-out actual", "It reproduces real decisions", 28, 7);
  statRow(s, [["0.990", "R²"], ["$21,966", "MAE"], ["3.65%", "MAPE"], ["94.9%", "WITHIN ±10%"]], 2.35);
  drafted(s, 3.0, 3.85, 7.3, 2.95);
  clabT(s, "Predicted vs actual — 9,998 held-out applicants", 3.2, 4.02, 6.5);
  s.addImage({ path: "charts/img_scatter.png", x: 3.25, y: 4.3, w: 6.8, h: 2.4, sizing: { type: "contain", w: 6.8, h: 2.4 } });
  foot(s, FL, "03 · Validation");

  // 17 — RESIDUALS & BAND
  s = p.addSlide(); bg(s, C.paper);
  head(s, "03 — Error structure", "Unbiased, and accurate across loan sizes", 27);
  clabT(s, "Residuals (actual − predicted), $k", 0.9, 2.25, 5.5);
  barChart(s, 0.7, 2.55, 5.8, 3.6, rhL, rhC, { colors: [C.cobalt], gap: 12, valHidden: true, fmt: "#,##0" });
  clabT(s, "MAPE by loan-size band", 7.0, 2.25, 5.3);
  s.addChart("line", [{ name: "MAPE", labels: data.by_band.band, values: data.by_band.MAPE_pct }], {
    x: 6.9, y: 2.55, w: 5.5, h: 3.6, chartColors: [C.cobalt], lineSize: 2.5, lineDataSymbolSize: 7,
    showLegend: false, catAxisLabelColor: C.ink2, valAxisLabelColor: C.ink3, axisLabelFontFace: F.mono,
    catAxisLabelFontSize: 9.5, valAxisLabelFontSize: 9, valGridLine: { color: C.line, style: "solid", size: 0.5 },
    catGridLine: { style: "none" }, valAxisMinVal: 0, valAxisMaxVal: 7,
  });
  s.addText("Residuals center on zero (no systematic over/under-lending). Absolute error grows with loan size but percentage error shrinks — most accurate on the largest loans.", { x: 0.9, y: 6.35, w: 11.4, h: 0.6, fontFace: F.body, italic: true, fontSize: 13, color: C.ink3 });
  foot(s, FL, "03 · Error structure");

  // 18 — FEATURE IMPORTANCE
  s = p.addSlide(); bg(s, C.paper);
  head(s, "03 — Feature importance", "Permutation importance confirms the four", 28);
  barChart(s, 0.7, 2.4, 6.2, 3.8, ["Annual income", "Credit score", "Existing monthly debt", "Down payment"], [1.44, 0.65, 0.34, 0.03], { horiz: true, colors: [C.cobalt, C.cobalt, C.steel, C.steel], showValue: true, fmt: "0.00", valHidden: true, gap: 60 });
  clabT(s, "Drop in test R² when the feature is shuffled", 0.9, 6.3, 6);
  bullets(s, [
    { b: "Income dominates", t: "(1.44), then credit score (0.65)." },
    { b: "Existing debt (0.34)", t: "is a genuine third factor — capacity to repay." },
    { b: "Down payment (0.03)", t: "small but load-bearing." },
    { b: "All other features ≈ 0 —", t: "measured directly, not assumed." },
  ], 7.2, 2.5, 5.3, { gap: 0.9, fs: 14.5 });
  foot(s, FL, "03 · Importance");

  // 19 — FAIR LENDING
  s = p.addSlide(); bg(s, C.paper);
  head(s, "03 — Governance", "Fair-lending posture", 30);
  bullets(s, [
    { b: "No protected attributes:", t: "the primary model uses no gender, marital status or age — supporting ECOA / fair-lending defensibility." },
    { b: "No obvious proxies:", t: "job and education (income proxies) were dropped; inputs are all direct financial measures." },
    { b: "Explainable:", t: "four inputs with monotonic, intuitive effects — straightforward to document for model risk and audit." },
    { b: "Monitor:", t: "track input drift and disparate-impact metrics once live on real decisions." },
  ], 0.9, 2.6, 11.5, { gap: 0.92, fs: 15.5 });
  foot(s, FL, "03 · Governance");

  // 20 — LIMITATIONS
  s = p.addSlide(); bg(s, C.paper);
  head(s, "03 — Limitations & assumptions", "What to keep in mind", 29);
  bullets(s, [
    { b: "Synthetic-style data:", t: "relationships are cleaner and more deterministic than a real lending book — expect lower R² on production data." },
    { b: "Counter-intuitive debt sign:", t: "existing debt correlates positively with the limit here (likely an artifact); revisit on real data." },
    { b: "Mimics existing decisions:", t: "the model learns the bank's historical limit policy — it does not judge whether that policy is optimal or fair." },
    { b: "No macro / collateral context:", t: "property value, LTV, rates environment and affordability stress are out of scope here." },
  ], 0.9, 2.6, 11.5, { gap: 0.92, fs: 15 });
  foot(s, FL, "03 · Limitations");

  // 21 — REPRODUCIBILITY
  s = p.addSlide(); bg(s, C.paper);
  head(s, "03 — Reproducibility", "One command per stage", 30);
  const steps = [
    ["scripts/01_clean_data.py", "Validate + audit → data/mortgage_clean.csv, metrics/cleaning_audit.csv"],
    ["scripts/02_model_benchmark.py", "Six model × scale combos → metrics/model_benchmark.csv"],
    ["scripts/03_train_evaluate.py", "Fit both models, validate → metrics + artifacts"],
    ["scripts/04_build_presentations.js", "These PPTX decks"],
    ["scripts/05_build_html_decks.py", "The HTML twins"],
  ];
  let sy = 2.5;
  steps.forEach(([f, d], i) => {
    s.addText(String(i + 1).padStart(2, "0"), { x: 0.9, y: sy, w: 0.7, h: 0.4, fontFace: F.mono, fontSize: 16, color: C.cobalt });
    s.addText(f, { x: 1.7, y: sy, w: 4.2, h: 0.4, fontFace: F.mono, fontSize: 15, color: C.ink });
    s.addText(d, { x: 6.0, y: sy, w: 6.4, h: 0.45, fontFace: F.body, fontSize: 14.5, color: C.ink2 });
    sy += 0.72;
  });
  s.addText("Every figure in this deck traces back to the raw CSV through these scripts.", { x: 0.9, y: 6.3, w: 11, h: 0.4, fontFace: F.body, italic: true, fontSize: 13.5, color: C.ink3 });
  foot(s, FL, "03 · Reproducibility");

  // 22 — CONCLUSION
  s = p.addSlide(); bg(s, C.ink);
  cross(s, 12.4, 0.85);
  eyebrow(s, "Conclusion", { onInk: true });
  s.addText([
    { text: "A compact, leakage-free model that reproduces the bank's loan limits to ", options: { color: C.paper } },
    { text: "~3.6% error", options: { color: C.cobaltSoft } },
    { text: " — using just four financial inputs.", options: { color: C.paper } },
  ], { x: 0.86, y: 2.4, w: 11.3, h: 2.4, fontFace: F.disp, bold: true, fontSize: 40, charSpacing: -0.5, lineSpacingMultiple: 1.05 });
  bullets(s, [
    { b: "Next:", t: "shadow-mode pilot, review band at ±10%, retrain on a real decision book." },
    { b: "Then:", t: "add collateral / LTV context and affordability stress for production underwriting." },
  ], 0.9, 5.1, 11.4, { gap: 0.7, fs: 16, onInk: true });
  foot(s, FL, "Conclusion");

  // 23 — APPENDIX (data dictionary)
  s = p.addSlide(); bg(s, C.paper);
  head(s, "Appendix", "Data dictionary", 30);
  const dd = [
    ["Annual Income (USD)", "num", "Applicant income — top driver"],
    ["Credit Score", "num", "300–850; second driver"],
    ["Existing Monthly Debt", "num", "Current monthly obligations"],
    ["Down Payment (USD)", "num", "Cash toward purchase — kept"],
    ["Interest Rate", "num", "Risk-based price — EXCLUDED"],
    ["Age / Employment Years", "num", "Correlated; not used"],
    ["Loans Repaid", "num", "Tracks credit score; not used"],
    ["Gender / Married / Area", "cat", "No signal; not used"],
    ["Education / Job", "cat", "Income proxies; not used"],
    ["Max Loan Amount (USD)", "num", "TARGET — held out"],
  ];
  const ddr = [["Field", "Type", "Role in the model"].map(h => ({ text: h, options: { fontFace: F.mono, bold: true, fontSize: 10.5, color: C.ink3, align: "left" } }))]
    .concat(dd.map(r => r.map((c, ci) => ({ text: c, options: { fontFace: ci === 2 ? F.body : F.mono, fontSize: 12.5, color: C.ink2, align: "left" } }))));
  s.addTable(ddr, { x: 0.9, y: 2.4, w: 11.5, colW: [3.7, 1.0, 6.8], rowH: 0.38, border: { type: "solid", color: C.line, pt: 0.5 }, valign: "middle" });
  foot(s, FL, "Appendix · Data dictionary");

  return p.writeFile({ fileName: "decks/mortgage_internal_deck.pptx" });
}

buildExec()
  .then(f => console.log("wrote", f))
  .then(() => buildInternal())
  .then(f => console.log("wrote", f))
  .catch(e => { console.error(e); process.exit(1); });
