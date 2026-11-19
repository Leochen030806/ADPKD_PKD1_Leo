#!/usr/bin/env node
/*
 * make_gel_slide.js — build one "Simplex gel image" titration report slide.
 *
 *   node make_gel_slide.js <config.json> <out.pptx>
 *
 * The config is documented in references/layout_spec.md. Everything that
 * varies run-to-run lives in the config; every coordinate, colour and font
 * below is copied from the reference template and should not be touched
 * unless the template itself changes.
 *
 * Image-anchored annotations (ladder arrows, lane numbers, temperature
 * braces) are given as FRACTIONS of the gel box, so they stay aligned no
 * matter how the gel photo is scaled. You (the model running the skill) read
 * those fractions off the actual image before writing the config.
 */
const fs = require("fs");
const PptxGenJS = require("pptxgenjs");

const [, , cfgPath, outPath] = process.argv;
if (!cfgPath || !outPath) {
  console.error("usage: node make_gel_slide.js <config.json> <out.pptx>");
  process.exit(1);
}
const cfg = JSON.parse(fs.readFileSync(cfgPath, "utf8"));

// ---- fixed design tokens (from template) ---------------------------------
const BLUE = "4472C4";        // theme accent1 — headers, arrows, box border
const BLUE_DK = "2F5496";     // accent1 lumMod 75% — braces, temp labels
const BAND = "E9EBF5";        // table banding
const BLACK = "000000";
const FONT = "Calibri";

const pptx = new PptxGenJS();
pptx.defineLayout({ name: "W", width: 13.333, height: 7.5 });
pptx.layout = "W";
const s = pptx.addSlide();

const inch = (v) => v; // readability alias

// ---- 1. title block ------------------------------------------------------
// "Exp Ref: <ref> （<primers>）" then "Aim: <aim>" with the last word blue+underlined.
const aim = cfg.aim || "To determine whether the primers can amplify/temperature titration worksheet";
const aimWords = aim.split(" ");
const aimTail = aimWords.pop();            // last token rendered blue + underlined
const aimHead = aimWords.join(" ") + " ";
s.addText(
  [
    { text: "Exp Ref: ", options: { bold: true } },
    { text: cfg.expRef || "", options: {} },
    ...(cfg.expRefPrimers
      ? [{ text: "（", options: {} }, { text: cfg.expRefPrimers + "）", options: {} }]
      : []),
    { text: "\n", options: { breakLine: true } },
    { text: "Aim: " + aimHead, options: { bold: true } },
    { text: aimTail, options: { bold: true, color: BLUE, underline: { style: "sng" } } },
  ],
  { x: 0.28, y: 0.21, w: 8.0, h: 0.91, fontFace: FONT, fontSize: 16, valign: "top", isTextBox: true, margin: 0 }
);

// ---- 2. gel image box ----------------------------------------------------
// Default box matches template; override with cfg.gelBox {x,y,w,h}.
const gb = Object.assign({ x: 3.49, y: 1.52, w: 4.95, h: 2.95 }, cfg.gelBox || {});
s.addImage({ path: cfg.gelImage, x: gb.x, y: gb.y, w: gb.w, h: gb.h });
const fx = (f) => gb.x + f * gb.w;   // frac-of-box-width  -> absolute x
const fy = (f) => gb.y + f * gb.h;   // frac-of-box-height -> absolute y

// ---- 3. Avg size range + marker labels + lane numbers --------------------
s.addText("Avg size range: " + (cfg.avgSizeRange || ""), {
  x: gb.x - 0.06, y: gb.y - 0.32, w: 2.2, h: 0.28, fontFace: FONT, fontSize: 10.5,
  align: "left", valign: "bottom", isTextBox: true, margin: 0,
});
if (cfg.markerLabels !== false) {
  const mk = { fontFace: FONT, fontSize: 9, align: "center", valign: "bottom", isTextBox: true, margin: 0 };
  s.addText("marker", { x: gb.x - 0.11, y: gb.y - 0.14, w: 0.6, h: 0.22, ...mk });
  s.addText("marker", { x: gb.x + gb.w - 0.5, y: gb.y - 0.16, w: 0.6, h: 0.22, ...mk });
}
(cfg.laneLabels || []).forEach((L) => {
  s.addText(String(L.n), {
    x: fx(L.xFrac) - 0.15, y: gb.y - 0.10, w: 0.3, h: 0.2,
    fontFace: FONT, fontSize: 9, align: "center", valign: "bottom", isTextBox: true, margin: 0,
  });
});

// ---- 4. ladder size arrows (both flanks) ---------------------------------
// Left: label left of gel, arrow -> into gel edge. Right: arrow <- from edge, label right.
const ARROW = 0.27; // arrow length (in)
(cfg.ladderMarks || []).forEach((m) => {
  const y = fy(m.yFrac);
  // left arrow: from (gb.x-ARROW) to gb.x, head at right (into gel)
  s.addShape("line", {
    x: gb.x - ARROW, y, w: ARROW, h: 0,
    line: { color: BLACK, width: 1.25, endArrowType: "triangle" },
  });
  s.addText(String(m.label), {
    x: gb.x - ARROW - 0.62, y: y - 0.11, w: 0.6, h: 0.22,
    fontFace: FONT, fontSize: 9, align: "right", valign: "middle", isTextBox: true, margin: 0,
  });
  // right arrow: from (gb.x+gb.w+ARROW) to gb.x+gb.w, head at left (into gel)
  s.addShape("line", {
    x: gb.x + gb.w, y, w: ARROW, h: 0,
    line: { color: BLACK, width: 1.25, beginArrowType: "triangle" },
  });
  s.addText(String(m.label), {
    x: gb.x + gb.w + ARROW + 0.04, y: y - 0.11, w: 0.6, h: 0.22,
    fontFace: FONT, fontSize: 9, align: "left", valign: "middle", isTextBox: true, margin: 0,
  });
});

// ---- 5. temperature braces + labels --------------------------------------
const braceY = gb.y + gb.h + 0.02;
(cfg.tempBlocks || []).forEach((t) => {
  const x0 = fx(t.x0Frac), x1 = fx(t.x1Frac), w = x1 - x0;
  // leftBrace rotated 90° -> a top brace hugging the lanes above, opening up
  s.addShape("leftBrace", {
    x: x0 + w / 2 - 0.09, y: braceY - w / 2 + 0.09, w: 0.18, h: w,
    rotate: 90, line: { color: BLUE_DK, width: 1.25 }, fill: { type: "none" },
  });
  s.addText(String(t.label), {
    x: x0, y: braceY + 0.20, w, h: 0.26,
    fontFace: FONT, fontSize: 10, bold: true, color: BLUE_DK,
    align: "center", valign: "top", isTextBox: true, margin: 0,
  });
});

// ---- 6. method footer ----------------------------------------------------
const method = cfg.method || [
  "[1% Agarose/ 1X TBE/ 5.5V/cm / 45mins]",
  " marker:1 kb DNA ladder dye",
  "10ul product + 2ul loading dye - loading 10ul mixture",
];
let my = gb.y + gb.h + (cfg.tempBlocks && cfg.tempBlocks.length ? 0.55 : 0.18);
method.forEach((line, i) => {
  s.addText(line, {
    x: gb.x - 0.06, y: my + i * 0.2, w: 4.2, h: 0.22,
    fontFace: FONT, fontSize: 10.5, align: "left", valign: "top", isTextBox: true, margin: 0,
  });
});

// ---- 7. left tables ------------------------------------------------------
const thin = { color: "BFBFBF", pt: 0.75 };
// 7a. Sample no. / Sample name
if (cfg.sampleTable && cfg.sampleTable.length) {
  const rows = [[
    { text: "Sample no.:", options: hdr() },
    { text: "Sample name:", options: hdr() },
  ]];
  cfg.sampleTable.forEach((r, i) => {
    const f = i % 2 ? BAND : "FFFFFF";
    rows.push([cell(r.no, f), cell(r.name, f)]);
  });
  s.addTable(rows, {
    x: 0.2, y: 1.82, w: 2.12, colW: [0.75, 1.37], border: thin,
    fontFace: FONT, fontSize: 10, valign: "middle",
  });
}
// 7b. Samples loading map (lane -> id), single "Samples" header spanning 2 cols
if (cfg.loadingTable && cfg.loadingTable.rows && cfg.loadingTable.rows.length) {
  const rows = [
    [{ text: cfg.loadingTable.title || "Samples", options: { ...hdr(), colspan: 2, align: "center" } }],
  ];
  cfg.loadingTable.rows.forEach((r, i) => {
    const f = i % 2 ? BAND : "FFFFFF";
    rows.push([
      { text: String(r.lane), options: { fill: { color: BLUE }, color: "FFFFFF", bold: true, fontSize: 6, align: "center", valign: "middle", border: thin, margin: 1 } },
      { text: String(r.id), options: { fill: { color: f }, color: BLACK, align: "left", valign: "middle", border: thin, margin: [1, 2, 1, 4] } },
    ]);
  });
  s.addTable(rows, {
    x: 0.21, y: 3.11, w: 2.15, colW: [0.34, 1.81], border: thin,
    fontFace: FONT, fontSize: 9.5, valign: "middle",
  });
}
function hdr() {
  return { fill: { color: BLUE }, color: "FFFFFF", bold: true, align: "left", valign: "middle", border: thin, fontSize: 10, margin: [1, 2, 1, 3] };
}
function cell(t, fill) {
  return { text: String(t == null ? "" : t), options: { fill: { color: fill }, color: BLACK, align: "left", valign: "middle", border: thin, margin: [1, 2, 1, 3] } };
}

// ---- 8. right-side lane interpretation -----------------------------------
if (cfg.laneInterp && cfg.laneInterp.length) {
  const runs = [];
  cfg.laneInterp.forEach((li, i) => {
    if (i) runs.push({ text: "\n\n", options: { breakLine: true } });
    runs.push({ text: "Lane " + li.lanes + (li.cond ? li.cond : ""), options: {} });
    runs.push({ text: "\n" + (li.result || ""), options: { breakLine: true } });
  });
  s.addText(runs, {
    x: 9.3, y: 1.62, w: 3.77, h: 1.57, fontFace: FONT, fontSize: 10,
    valign: "top", isTextBox: true, margin: 0,
  });
}

// ---- 9. conclusions box (bordered) ---------------------------------------
if (cfg.conclusions && cfg.conclusions.length) {
  const runs = [];
  cfg.conclusions.forEach((c, i) => {
    if (i) runs.push({ text: "\n", options: { breakLine: true } });
    runs.push({ text: c.head, options: { bold: true, fontSize: 12 } });
    if (c.body) runs.push({ text: "\n" + c.body, options: { fontSize: 10, breakLine: true } });
  });
  s.addText(runs, {
    x: 9.14, y: 3.73, w: 3.99, h: 3.25, fontFace: FONT, fontSize: 10, valign: "top",
    line: { color: BLUE, width: 1 }, margin: 6, isTextBox: true,
  });
}

pptx.writeFile({ fileName: outPath }).then((f) => console.log("wrote", f));
