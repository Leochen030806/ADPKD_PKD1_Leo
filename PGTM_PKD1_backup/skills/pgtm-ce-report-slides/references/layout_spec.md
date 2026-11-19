# Slide layout specification

Portrait **7.5 × 13.33 in** (750 × 1333 px at 100 dpi), two slides per marker: samples 1–8 then
9–16. Both slides are self-contained — the marker-level stats repeat — so either page can be
shown alone in a group meeting.

## Why this shape

An earlier version put all 16 samples on one page. It validated fine and was unreadable: each
trace collapsed to ~0.37 in tall. The split to 8-per-page with one row per sample is the single
change that made the deck usable, so resist requests to re-densify without seeing a rendered
page first.

## Page regions

```
y 0.28  kicker      PKD1 STR PANEL · CE GENOTYPING SUMMARY
y 0.52  title       STR <n>  ·  Marker <marker>            + repeat-unit chip at x 5.15
y 1.14  part pill   Page N / 2 · Samples 1 – 8
y 1.60  stat cards  [samples typed] [alleles/locus] [HET obs.] [alleles observed]   h 0.92
y 2.62  example     representative heterozygote + het/hom legend                    h 1.34
y 4.08  section     Per-sample CE traces · Samples 1 – 8
y 4.48  col heads   Sample / genotype | full trace (0–510 bp) | Zoom · ≈<lo>–<hi> bp
y 4.78  rows        8 rows, pitch 1.00, block 0.86
y 13.02 footer      marker · instrument · "IDs read from image (OCR)" · binning step
```

Row internals: label block at x 0.30 (het/hom dot + sample name + genotype + tag), full-trace
image at x 1.40 fitted into 3.35 × 0.74 in, zoom at x 4.90 fitted into 2.30 × 0.74 in, hairline
separator above each row. Images are fitted to the **box** (width *and* height capped) — fitting
width only caused overflow once zoom crops became tall.

## Palette and type

| token | value | use |
|---|---|---|
| ink | `#12303F` | titles, genotype text |
| teal | `#1C7293` | marker name, het accent, kicker |
| mint | `#02C39A` | section marker bar |
| panel | `#EDF3F5` | stat card fill |
| muted | `#5E6E76` | labels, footer |
| line | `#D5E0E4` | hairlines, image frames |
| hom | `#8A97A0` | homozygous dot/text |

Cambria for titles, Calibri for body. Every trace image gets a thin rounded frame — that repeated
frame is what makes 16 heterogeneous screenshots read as one system.

## Representative heterozygote

Each page picks its own example from *that page's* eight samples: prefer a het whose two alleles
are ≥ 2 repeat units apart (clearly resolved peaks), smallest such spacing first, else any het.
The image reused is that sample's already-cropped zoom, so the framing matches the rows below;
it is capped at 3.0 in wide to avoid colliding with the legend.

Pin a specific sample with `CONFIG.EXAMPLE`, keyed by **marker** plus page letter:

```js
EXAMPLE: { "1299a": "NA03815", "1299b": "NA09133" }
```

## Failed samples

A sample with no genotype renders "—" for both the call and the het/hom tag, keeps its grey dot,
and still shows its raw traces. Do not hide it: an empty trace is the evidence that the sample
failed, and reviewers expect to see all 16 rows. Marker 2517 (NA16243) and 1830 (NA11518) are the
worked examples.
