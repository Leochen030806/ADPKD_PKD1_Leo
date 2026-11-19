# Layout spec & config schema — simplex gel titration slide

Slide is **13.333 × 7.5 in** (16:9 wide). All coordinates below are in inches and are baked into
`scripts/make_gel_slide.js`; you normally only touch the **config**, not the script.

## Design tokens (fixed)

| token | value | used for |
|---|---|---|
| accent blue | `4472C4` | table headers, box border, ladder-label side, brace/temperature |
| dark blue | `2F5496` | temperature braces + labels (accent1 @ 75%) |
| band fill | `E9EBF5` | alternating table rows |
| font | Calibri | everything |
| title size | 16 pt | Exp Ref / Aim block |
| method + avg-size | 10.5 pt | footer, "Avg size range" |
| tables / interp / temp | 10 pt | (lane-number column in loading table = 6 pt) |
| conclusions | 12 pt bold heads / 10 pt body | bordered box |
| ladder / lane / marker | 9 pt | flank + top annotations |

## Fixed element coordinates (x, y, w, h in inches)

| element | x | y | w | h |
|---|---|---|---|---|
| title block | 0.28 | 0.21 | 8.00 | 0.91 |
| gel box (default) | 3.49 | 1.52 | 4.95 | 2.95 |
| Avg size range | gel.x−0.06 | gel.y−0.32 | 2.2 | 0.28 |
| marker (left/right) | at gel flanks | gel.y−0.15 | 0.6 | 0.22 |
| sample-no./name table | 0.20 | 1.82 | 2.12 | auto |
| loading (Samples) table | 0.21 | 3.11 | 2.15 | auto |
| lane interpretation | 9.30 | 1.62 | 3.77 | 1.57 |
| conclusions box | 9.14 | 3.73 | 3.99 | 3.25 |
| method footer | gel.x−0.06 | below braces | 4.2 | per line |

Ladder arrows, lane numbers and temperature braces are positioned **relative to the gel box** via
fractions (see below), so they do not have fixed coordinates.

## Config schema

```jsonc
{
  // ---- title block ----
  "expRef": "LC-20260624-01_PKD1_STR5",       // string before （…）
  "expRefPrimers": "M-Pet-2290-F1/Pig-2290-R2", // goes inside （…）; omit to drop the parens
  "aim": "To determine whether the primers can amplify/temperature titration worksheet",
                                               // optional; last word auto blue+underlined

  // ---- gel image ----
  "gelImage": "/abs/path/to/gel.png",          // PNG or JPEG
  "gelBox": { "x": 3.49, "y": 1.52, "w": 4.95, "h": 2.95 }, // optional override

  "avgSizeRange": "~350bp",                     // expected amplicon
  "markerLabels": true,                          // "marker" on both flanks; false to hide

  // ---- top: lane numbers (fraction of gel width, 0=left .. 1=right) ----
  "laneLabels": [ { "n": 1, "xFrac": 0.13 }, { "n": 2, "xFrac": 0.22 }, ... ],

  // ---- flanks: ladder size arrows (yFrac 0=top .. 1=bottom of gel) ----
  "ladderMarks": [ { "label": "1000", "yFrac": 0.30 }, { "label": "750", "yFrac": 0.35 }, ... ],

  // ---- below gel: temperature braces (x0/x1 = span as fraction of gel width) ----
  "tempBlocks": [ { "label": "55℃", "x0Frac": 0.10, "x1Frac": 0.35 }, ... ],

  // ---- left table 1: sample no. -> name ----
  "sampleTable": [
    { "no": "1、4、7:", "name": "NA11518，5ng/μl" },
    { "no": "3、6、9:", "name": "HPLC water" }
  ],

  // ---- left table 2: lane -> loading id (the actual well plan) ----
  "loadingTable": {
    "title": "Samples",
    "rows": [ { "lane": 1, "id": "NA11518-55" }, { "lane": 4, "id": "Blank-55" }, ... ]
  },

  // ---- right: lane interpretation (you draft from the gel) ----
  "laneInterp": [
    { "lanes": "3、6、9", "cond": "(blank, HPLC water): ", "result": "No bands observed" },
    { "lanes": "1、2、4、5、7、8", "cond": " (gDNA3, 10 ng): ", "result": "single, specific band" }
  ],

  // ---- right: bordered conclusions box (you draft from the gel) ----
  "conclusions": [
    { "head": "1. Amplification confirmed.", "body": "All 9 template wells yielded …" },
    { "head": "2. All three NTC wells are clean across all Ta points.", "body": "…" },
    { "head": "3. Working Ta ≥ 55–65°C, optimum at 55–60°C.", "body": "…" }
  ],

  // ---- footer (fixed default; override only if run conditions differ) ----
  "method": [
    "[1% Agarose/ 1X TBE/ 5.5V/cm / 45mins]",
    " marker:1 kb DNA ladder dye",
    "10ul product + 2ul loading dye - loading 10ul mixture"
  ]
}
```

### Field notes

- **Variable-length arrays.** `laneLabels`, `ladderMarks`, `tempBlocks`, both tables,
  `laneInterp`, `conclusions` can each be any length. A 12-lane / 4-temperature gel just has
  longer arrays.
- **Lane vs. loading id.** In the reference run the *photographed* lanes are numbered 1–9
  (`laneLabels`), but the loading table lists the *plate* wells (1,2,4,5,6,8,9,10,12) — the
  well-plate numbering skips columns. Keep `laneLabels` = what's on the gel, `loadingTable` = what
  was pipetted. Don't force them to match.
- **Grouping consistency.** The lanes named in each `tempBlocks` span, the `laneLabels`, and the
  temperature suffixes in `loadingTable` ids should agree (lanes 1–3 = 55 ℃, etc.).
- **`cond` spacing.** `laneInterp[].cond` is concatenated right after `"Lane <lanes>"` — include a
  leading space if you want one (the reference mixes `"(blank…"` with `" (gDNA3…"`).
- **Fractions are per-gel.** Never copy `ladderMarks[].yFrac` from another run; bands migrate to
  different heights each gel.

## Worked example

A complete config that reproduces the reference template lives alongside the skill as the test
config used to validate the engine. Its structure is exactly the schema above. To regenerate:

```bash
node scripts/make_gel_slide.js <that-config>.json out.pptx
```

## When the gel isn't a 3-temperature titration

The template still fits most simplex agarose checks:
- **Plain amplify/no-amplify (no titration):** drop `tempBlocks` (or give one block), set the aim to
  the amplification-check wording, and label lanes/samples normally.
- **More temperatures or a gradient:** add more `tempBlocks` and extend the tables; the braces and
  labels lay out automatically across the gel width.
- **Multiplex / different panel:** same layout; the interpretation should foreground dimer/control
  cleanliness, since that's what gates multiplex inclusion.
