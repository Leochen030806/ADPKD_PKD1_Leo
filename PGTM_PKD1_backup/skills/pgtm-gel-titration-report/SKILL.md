---
name: pgtm-gel-titration-report
description: >
  Turn an agarose-gel photo from a primer temperature-titration (Ta gradient) or amplification
  check into the standard one-slide "Simplex gel image" report — Exp Ref block, gel with 1 kb
  ladder arrows on both flanks, lane numbers, per-temperature braces (e.g. 55/60/65 ℃), the two
  left sample tables (sample-no.→name and lane→loading id), the right lane interpretation, and a
  bordered conclusions box. Use whenever the user gives a gel / electrophoresis PHOTO (agarose,
  跑胶, 电泳图, 胶图) and wants it written up as slides, a report, a PPT, 出图, 分析模板, or
  "生成胶图分析" — including short continuations like "这是下一个 primer 的胶图" or "换了 Exp Ref
  帮我出一张". It reproduces one fixed template and only asks for the fields that change run-to-run
  (Exp Ref, primers, avg size range, temperatures, sample/lane map, interpretation). NOT the
  GeneMapper CE-trace deck — capillary-electrophoresis screenshots / STR peak traces go to
  pgtm-ce-report-slides; this skill is for actual gel-lane photographs.
---

# PGT-M — Simplex gel titration report slide

This builds the single-slide agarose-gel writeup Leo uses after a temperature titration /
amplification check on a primer pair. The layout is **fixed**; only the content changes. The
engine is `scripts/make_gel_slide.js` (pptxgenjs) — your job is to read the variable fields off
the image + from Leo, write a config JSON, run the script, and QA the result against the layout.

The reference this template was reverse-engineered from:
`Exp Ref: LC-20260624-01_PKD1_STR5 （M-Pet-2290-F1/Pig-2290-R2)` — a 9-lane, 3-temperature
(55/60/65 ℃) simplex check on two Coriell gDNAs (NA11518, NA06075) + HPLC-water NTCs. Keep that
run as the mental model for what "the same template" means.

## Pipeline

```
0. Receive     one gel photo (+ maybe a one-line note from Leo)
1. Read image  ladder band heights, lane count/positions, temperature groupings,
               which lanes show a band vs. are blank  -> fractions for the config
2. Ask Leo     only the fields that change run-to-run (see "What to ask"); carry the
               reference run's values as defaults so he can just say "same except …"
3. Draft       write the lane interpretation + conclusions FROM the gel, then confirm
4. Config      fill config.json (schema in references/layout_spec.md)
5. Build       node scripts/make_gel_slide.js config.json out.pptx
6. QA          render to image, check against the layout, fix, present the .pptx
```

## What is fixed vs. what changes

**Fixed (boilerplate — do not ask, copy verbatim unless Leo says otherwise):**
- The whole layout, fonts (Calibri), colours (accent blue `4472C4`), table styling.
- Both "marker" flank labels.
- The method footer, default:
  `[1% Agarose/ 1X TBE/ 5.5V/cm / 45mins]` / ` marker:1 kb DNA ladder dye` /
  `10ul product + 2ul loading dye - loading 10ul mixture`.
- The Aim line, default:
  `To determine whether the primers can amplify/temperature titration worksheet`
  (its last word renders blue + underlined automatically — don't mark it up yourself).

**Changes every run (this is what the config carries):**
- `expRef` and `expRefPrimers` — the reference string and the primer pair in （…）.
- `avgSizeRange` — expected amplicon size, e.g. `~350bp`.
- `tempBlocks` — the annealing temperatures tested and which lanes each spans.
- `laneLabels` — how many lanes and their positions.
- `sampleTable` — sample-no.→name legend (templates, gDNAs, NTC).
- `loadingTable` — the lane→loading-id map (the well plan actually loaded).
- `ladderMarks` — which ladder rungs are labelled and where they sit.
- `laneInterp` + `conclusions` — you draft these from the gel; see below.

## What to ask Leo (after you've looked at the image)

Look at the gel first, then ask **one concise, batched round** — present the reference-run
defaults so he can reply with only the deltas ("same except Exp Ref = …"). Cover:

1. **Exp Ref** and the **primer pair** for the （…） — almost always new.
2. **Avg size range** (expected amplicon).
3. **Temperatures** tested and the lane grouping (e.g. 55/60/65 ℃, 3 lanes each) — confirm what
   you inferred from the image.
4. **Sample / lane map** — which template(s) and NTC, at what concentration, and the exact
   lane→id loading list. **This is clinical loading data; if the mapping is at all ambiguous,
   stop and ask rather than guess** — a lane under the wrong sample is far worse than a delayed
   slide.
5. Anything unusual: extra ladder rungs to label, a different agarose %/run condition, more/fewer
   temperatures, a non-titration aim.

Don't re-ask the fixed boilerplate. If Leo just says "same layout, here's the new Exp Ref and
loading", take every other field from the reference run.

## Drafting the interpretation and conclusions

You write `laneInterp` and `conclusions` from what the gel actually shows — then confirm with Leo
before finalizing. Judge these from the image:
- **NTC / blank lanes clean?** This is the single most important signal on a titration gel — clean
  no-template controls across all Ta points are what clear a primer for multiplex use. Call it out
  explicitly (as conclusion #2 in the reference run).
- **Specific single band vs. smear / multiple bands / dimers** in the template lanes.
- **Ta trend** — compare band brightness across the temperature blocks; state the working range and
  optimum.
- Whether the band sits near the expected `avgSizeRange`.

Keep the tone and structure of the reference conclusions (numbered, a bold one-line verdict then a
sentence of evidence). Do **not** overstate: if a control shows a faint band or a lane failed, say
so plainly — this is a QC document.

## Reading image-anchored positions

Ladder arrows, lane numbers and temperature braces are placed as **fractions of the gel box**, so
they track the photo at any scale. Read them off the image:
- `ladderMarks[].yFrac` — vertical position of each labelled rung, 0 = top of the gel image, 1 =
  bottom. Measure where the 1000/750/500/250 (or whichever) bands actually migrated on *this* gel;
  never reuse another gel's values — migration distance varies with run time/voltage.
- `laneLabels[].xFrac` and `tempBlocks[].x0Frac/x1Frac` — horizontal centre of each lane and the
  span of each temperature block, 0 = left edge, 1 = right edge of the gel image.

If unsure, crop/zoom the image and measure; a quick vertical-intensity profile of a ladder lane and
a horizontal one across the wells makes the positions obvious. Getting these fractions right is what
makes the arrows and braces line up.

## Build and QA

```bash
node scripts/make_gel_slide.js config.json out.pptx
# render to inspect
python /mnt/skills/public/pptx/scripts/office/soffice.py --headless --convert-to pdf out.pptx
pdftoppm -jpeg -r 150 out.pdf slide && # view slide-1.jpg
python /mnt/skills/public/pptx/scripts/office/validate.py out.pptx
```

QA checklist (look at the render, not just the code):
- Ladder arrows point at the actual bands on both flanks; labels legible.
- Lane numbers sit over their wells; temperature braces span the right lanes with the right labels.
- Both tables: no phantom empty column, ids on one line, header spans correctly.
- Conclusions text fits inside the blue border (nothing clipped at the bottom edge).
- Exp Ref / primers / avg size / method footer all correct; Aim's last word is blue-underlined.

Then present the `.pptx`. The full config schema, every fixed coordinate, and a complete worked
example are in **`references/layout_spec.md`** — read it before writing your first config.

## Notes

- The gel image can be any format pptxgenjs accepts (PNG/JPEG). If Leo hands you a huge TIFF,
  convert to PNG first (`Pillow`) — it keeps the .pptx small without visible quality loss.
- Default gel box is the template's `{x:3.49, y:1.52, w:4.95, h:2.95}` inches. Override `gelBox`
  only if a very different aspect ratio would distort the photo; keep the top-left anchor so the
  surrounding annotations still frame it.
- More or fewer than 3 temperatures / 9 lanes is fine — the arrays are variable-length. Keep the
  lane→temperature grouping consistent between `tempBlocks`, `laneLabels` and `loadingTable`.
