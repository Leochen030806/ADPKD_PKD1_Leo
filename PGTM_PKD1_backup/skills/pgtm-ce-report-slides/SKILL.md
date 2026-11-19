---
name: "pgtm-ce-report-slides"
description: "Maintain the PKD1 CE-summary workbook (PKD1_CE_summary_robust.xlsx, sheet 'CE Summary') and turn GeneMapper CE screenshots into the portrait PowerPoint report for a PGT-M STR linkage marker. Covers checking and repairing marker rows whose formulas are missing, mis-pointed, #REF!-broken, degraded from array formulas, or poisoned by a text-stored raw size, and keeping pre-formulated blank rows so a newly added STR computes as soon as it is typed; plus two slides per marker across the 16 Coriell reference samples, with auto-binned genotypes and marker stats, appended to one growing deck. Use whenever the user supplies CE / GeneMapper screenshots, mentions an STR or marker number (\"STR 7\", \"marker 1951\", \"1299\") with slides, a deck, a PPT, 报告 or 出图, or raises anything about the summary workbook — \"summary robust\", \"CE summary\", \"自动计算的表格\", \"新加的 STR 不会算\", \"公式没了\", or HET / allele counts looking wrong. Trigger on short continuations like \"接下来是 2517 的\" with attached images."
---

# PKD1 PGT-M — CE summary sheet + genotyping report slides

This skill covers the two halves of the PKD1 PGT-M STR linkage panel workflow across 16 Coriell
reference samples:

1. **The summary workbook** — `PKD1_CE_summary_robust.xlsx`, sheet `CE Summary`. Raw GeneMapper
   sizes go in; samples typed, allele count, observed heterozygosity, the sorted allele list and
   off-ladder flags come out automatically. `scripts/ce_sheet.py` checks, repairs and extends it.
2. **The slide deck** — one STR marker produces **two portrait slides**; markers accumulate into a
   single combined deck as they are validated. `scripts/make_str_slide.py` does the heavy lifting.

Your job is to check the inputs, run the scripts, verify the output structurally, and — most
importantly — **stop and ask whenever the sample identity is ambiguous.** This is clinical data; a
trace under the wrong sample name is much worse than a delayed slide.

## Pipeline

```
0. Sheet check CE Summary health check + repair + top up spare rows   <- do this FIRST, always
1. Inputs      CE-summary .xlsx (one row per STR) + GeneMapper screenshots for that STR
2. Audit       file count / -z pairing / filename sample-index audit   <- catches most problems
3. Identify    per panel: filename index (authoritative) > OCR label > constrained fuzzy
4. Crop        full trace cut at ~510 bp; zoom cropped to the marker peak window
5. Compose     2 slides: samples 1–8 and 9–16, one row per sample
6. Verify      pptx validation + coordinate/bounds check + genotype cross-check vs sheet
7. Combine     append the marker to the running multi-marker deck
```

## Fixed reference data

**Sample order** — every deck is arranged into this sequence regardless of capture order:

```
1 NA03814   2 NA03815   3 NA04738   4 NA04776   5 NA04820   6 NA06075   7 NA06890   8 NA07425
9 NA07426  10 NA07428  11 NA09133  12 NA11518  13 NA16243  14 NA17942  15 NA22601  16 NA50194
```

**Genotype binning**: snap each raw size to the nearest value in "alleles observed", then two
distinct bins = het, one = hom, missing = failed (rendered as "—" with its raw trace).
Never round raw sizes by hand — the sheet does this and the deck must match the sheet's HET value.

**Which markers are already built** is deliberately not listed here, because it goes stale. Ask
the script: `python make_str_slide.py --list` reports, per marker, whether sheet data and images
are present.

---

# Step 0 — Sheet health check and repair

**Run this before reading anything else out of the workbook, every time.** The deck's genotypes
are copied from this sheet, so a quietly broken row produces a confidently wrong slide.

```bash
python3 scripts/ce_sheet.py <workbook>.xlsx --check
```

If it reports problems:

```bash
python3 scripts/ce_sheet.py <workbook>.xlsx --repair --fix-decimals -o <workbook>_fixed.xlsx
python3 scripts/ce_sheet.py <workbook>_fixed.xlsx --check     # must come back clean
python3 scripts/ce_sheet.py <workbook>_fixed.xlsx --values    # recomputed stats, independent of Excel
```

Never edit the original in place — write a new file and tell the user both names.

## The sheet contract

One row per STR marker. Left to right: a region column (`cen` header, with merged
`5' Upstream` / `3' Downstream` blocks), STR No., Marker, Repeat unit, then 16 samples × 2 allele
columns of **raw** GeneMapper sizes (the yellow input cells), then the visible statistics —
Samples typed (n), No. of alleles, HET (obs.), Alleles observed (sorted), Off-ladder raw — and
finally a **hidden outline group** holding the working: repeat-unit length, one sum-of-squares
column per candidate ladder phase, the chosen phase, 32 binned allele cells, and 16 sorted-allele
slots. That comes to **59 computed cells per marker row.**

As of this writing those land in A / B / C / D / E–AJ / AK–AO / AQ–CT, but **do not rely on the
letters** — a column has already been inserted in front of column A once, which silently shifted
every hard-coded index and broke rows that had been fine for months. `ce_sheet.py` locates
everything from header text and from the template row's own formulas, and any new tooling must do
the same.

**The ladder phase is inferred, not assumed.** For each offset 0..3 the sheet computes the sum of
squared distances from every raw size to the nearest step of the repeat unit, and takes the offset
with the smallest total. So markers are not assumed odd or even. Python must mirror Excel's
`ROUND` (half **away from zero**, not Python's banker's rounding) or the two engines will disagree
on exact .5 boundaries.

## Failure modes `--check` detects

| kind | what happened | why it is dangerous |
|---|---|---|
| `empty` | the row has no formulas at all | a marker row was **inserted blank** instead of copied — it inherits formatting, so it looks right |
| `ref` | a formula contains `#REF!` | usually wrapped in `IFERROR`, so it shows as blank rather than an error |
| `misaligned` | a bin formula reads a **different sample's** raw cell than the template does | the worst one: produces a plausible but wrong genotype, with no visible symptom |
| `not-array` | an array formula was written back as an ordinary formula | see the warning below |
| `edited` | a formula differs from the translated template in any other way | someone hand-edited it |
| `constant` | a computed cell holds a typed-in value | the number stops tracking the data |
| `text-raw` | a raw size is stored as TEXT, e.g. `'192,61'` with a decimal comma | poisons the phase sum-of-squares and shifts **every** allele label for that marker by 1 bp; `--fix-decimals` converts it |

## ⚠ Array formulas — the subtlest way a "repaired" sheet is still wrong

**17 of the 59 computed cells are array (CSE) formulas**: the `SMALL(IF(...))` chain that sorts the
distinct alleles, and the off-ladder `TEXTJOIN`. openpyxl exposes them as `ArrayFormula` objects.
If you read one and write it back as a plain string, **Excel raises no error** — but the formula
collapses to a single value, so `Alleles observed` shows only the smallest allele and the marker
looks monomorphic. Always write them back with `ArrayFormula(ref=..., text=...)`;
`ce_sheet.py` does this, and `--check` reports a degraded one as `not-array`.

## Adding a new STR marker

The historical failure was that a hand-inserted row has formatting but no formulas, so nothing
computes. The sheet now carries **pre-formulated blank rows** below the table. Every formula is
guarded with `IF(Marker="","",...)`, so those rows look completely empty until a marker number is
typed into one — at which point all statistics appear immediately.

So the user's instruction is simply: **type the new STR into the next blank row.** No copying.

When the spare rows run low, top them up:

```bash
python3 scripts/ce_sheet.py <workbook>.xlsx --extend 20 -o <workbook>_extended.xlsx
```

`--repair` keeps at least 15 spare rows by default. The rows are inserted between the last marker
and the how-to prose block, styles copied from the template row, array formulas preserved.

## Verifying the repair

A repair is not finished until an independent engine agrees. `--values` recomputes every marker in
Python from the raw sizes alone. Cross-check that against a real recalculation:

```bash
soffice --headless --convert-to xlsx --outdir recalc <workbook>_fixed.xlsx
```

Then compare samples typed / allele count / HET / allele list per row. All rows must match. Also
re-test the add-a-marker path by typing a synthetic marker into a spare row, recalculating, and
confirming the allele list contains **every** allele rather than just the smallest — that is the
array-formula regression test.

Report markers with HET 0% or a single observed allele: they are monomorphic across the reference
panel and carry no linkage information, which is a result worth telling the user plainly.

---

# Step 1 — Inputs and naming

**Preferred layout — one folder per marker**, named by the marker number, inside the screenshot
directory. This is what the user maintains on their Desktop:

```
CE screen shoot/
├── 2517/     <- STR 3    six originals + six zooms
├── 2290/     <- STR 5
├── 1830/     <- STR 8
└── 1299/     <- STR 11
```

Marker folders are scanned **recursively**, so the six windows may sit flat in the folder or be
split into `thumbnail/` and `zoom/` subfolders.

Each folder holds six capture windows (3 stacked panels each) covering the 16 samples, every
window as an **original** (full 0–750 bp trace) plus a **zoom** (the marker's allele window):

| role | how it's recognised |
|---|---|
| original | anything else — e.g. `1_10_2.PNG`, `8-1_10_2.PNG`, `thumbnail/1_10_2.PNG` |
| zoom | name ends in `-z`, **or** `zoom` appears anywhere in the path below the marker folder |

Because the zoom test looks at the path, files in a `zoom/` subfolder need no `-z` suffix and may
share a filename with their thumbnail.

The marker or STR number as a filename prefix is optional — the folder already identifies the
marker. A flat directory with `<STR>-` prefixed files also still works, for older markers.

Two naming rules carry real weight:

1. **The `-z` suffix is not cosmetic.** Without it the zoom and original share a filename and
   one silently overwrites the other. This has already destroyed images several times
   (`11-10_11_12`, `11-13_14_15`, all of 2290, part of 1951). Always audit before building.
2. **Digits in the filename are sample indices, in panel order.** `16_9_5.PNG` means panel 1 =
   sample 16 (NA50194), panel 2 = sample 9 (NA07426), panel 3 = sample 5 (NA04820). `14.PNG` is a
   one-panel window showing sample 14. These indices **override the on-screen label**, because CE
   runs are sometimes mislabelled — marker 1830 had two panels labelled NA07426 and the filename
   is what disambiguated them.

Names do not have to be sequential, nor consistent between an original and its zoom: panels are
matched to samples by content, then paired by which sample they show. If the digits aren't a clean
index list, or the count doesn't match the number of panels, that file falls back to OCR.

# Step 2 — Audit the inputs before building

Do this every time. It takes seconds and catches the failures that would otherwise produce a
confidently wrong deck.

```powershell
python scripts/make_str_slide.py --list   # which markers have data + images
```

Then audit the marker's own folder:

```bash
python3 -c "import glob,os;from PIL import Image;[print(os.path.basename(f), Image.open(f).size) for f in sorted(glob.glob('<imgdir>/<marker>/*.PNG'))]"
```

Check three things:

- **Count.** Expect 12 files (6 originals + 6 zooms). Fewer means a `-z` collision. Identify
  *which* survived by pixel width — a ~1300 px file is an original, a narrower one is a zoom.
  Width alone is not always decisive (2290's zooms were captured full-width), so use it to
  diagnose collisions, not to classify.
- **Index audit.** Collect the digits from every filename. Every index 1–16 should appear, and
  none twice. A missing index paired with a duplicated one is the signature of a typo — that is
  exactly how the STR 7 problem surfaced (index 5 missing, index 10 twice).
- **Sheet coverage.** A sample with a genotype but no image is a gap worth raising; a sample with
  no genotype is fine and will render "—".

Report anything off **before** running, with the specific file names and what you infer. Ask for
the re-upload or the correction rather than guessing.

# Step 3 — Build

Two interchangeable implementations produce byte-for-byte equivalent decks. **Default to the
Python one** — the user's lab PC is domain-managed and cannot install Node.

| | `scripts/make_str_slide.py` | `scripts/make_str_slide.js` |
|---|---|---|
| install | `pip install openpyxl python-pptx pillow` | `npm install pptxgenjs xlsx sharp tesseract.js` |
| sample identity | filename indices only | filename indices, then OCR of the panel label |
| system components | none | Tesseract model (downloaded or local) |

The Python build has no OCR, so **every filename must carry its sample indices**. That is already
the user's convention and it is strictly more reliable than reading a label that the CE run may
have printed wrong. If a name can't be parsed the script names the file and the reason — fix the
filename rather than the script.

The normal command rebuilds the whole deck from every marker folder present, in STR order:

```powershell
python make_str_slide.py --auto
```

This is idempotent — adding a folder and re-running simply produces a longer deck, which is why
it's preferred over appending. Other modes:

```powershell
python make_str_slide.py --list                  # report readiness, build nothing
python make_str_slide.py 2290                    # one marker -> PKD1_Marker2290_CE_EN.pptx
python make_str_slide.py --combined 2517 2290    # explicit subset / explicit order
```

A marker can be named by its marker number (2290) or its STR number (5). Paths come from `CONFIG`
at the top of the script, or from `--xlsx` / `--imgdir` / `--outdir`, or from the
`CE_XLSX` / `CE_IMGDIR` / `CE_OUTDIR` environment variables. The Node build additionally takes
`--tessdata <dir>` for offline OCR.

If the sheet was repaired in Step 0, point the build at the **repaired** file, not the original.

The script prints how each sample was resolved. Read this every run:

```
STR 8 (Marker 1830)  images: .../CE screen shoot/1830
  NA03814: 1_10_2.PNG p1  |  1_10_2-z.PNG p1
  NA11518: 11_3_12.PNG p3 |  11_3_12-z.PNG p3  (no genotype)
  ! problems:
     no image for genotyped sample(s): NA04820
     possible filename typo — index 10 (NA07428) appears in both 10_3_11.PNG and 8_15_10.PNG
```

Anything under `! problems` is a stop-and-ask signal, not a warning to build through. The Node
build additionally tags each row `[named]` / `[read]` / `[inferred]`; `[inferred]` is the only tag
that deserves suspicion.

# Step 4 — Verify before delivering

The image preview tool is unreliable in this environment, so **do not rely on looking at the
rendered slide**. Verify structurally instead — this caught every real defect in practice:

```bash
python /mnt/skills/public/pptx/scripts/office/validate.py <out.pptx>
```

Then check, by parsing the pptx (see `references/verification.md` for ready-made snippets):

- **Bounds**: no shape outside 7.5 × 13.33 in; lowest element ≈ 13.24 in.
- **Image count**: 17 per slide (8 originals + 8 zooms + 1 representative example).
- **Aspect ratios**: originals ≈ 6.0 (confirms the 510 bp crop landed); zooms should be well
  under ~5 (a zoom still at ~9 means the peak-window crop failed).
- **Genotypes**: extract the rendered calls and reconcile against the sheet — het/hom counts
  must reproduce the sheet's observed heterozygosity.
- **Zoom label**: the column header shows the marker's own window, e.g. `≈415–445 bp` for 2517.

Tell the user plainly that visual QA was done structurally rather than by eye.

# Step 5 — Deliver, then stop

`--auto` already rebuilt the combined deck with every marker that has a folder, so there is
nothing to merge by hand. Deliver the combined deck (and the single-marker file if one was built)
and report: the Step 0 sheet check, the readiness scan, the identification summary, any mismatch
warnings, genotype counts vs the sheet, and the verification results.

Then **stop and wait.** The user's loop is: update one STR row in the spreadsheet, drop a new
marker folder into the screenshot directory, then tell you to go again. Don't prompt for the next
marker or speculate about which one is coming — just confirm what was built and what is still
pending (`--list` shows this), and wait for the next instruction.

## When to stop and ask

Ambiguity about *which sample a trace belongs to* is never resolved by guessing. Stop and ask when:

- a filename index list is internally inconsistent (missing/duplicate index),
- the filename and the on-screen label disagree in a way the user hasn't already explained,
- an original or a zoom is missing for a sample that has a genotype,
- a sample appears in two windows with conflicting identities,
- `ce_sheet.py --check` reports `misaligned` or `edited` cells you cannot explain — a mis-pointed
  bin is a wrong genotype, so confirm the repair before building slides from it.

Present the specific evidence (file names, indices, what the label reads, what the sheet says)
and your recommendation, then wait. The user has the lab context you don't.

## Reference files

- `scripts/ce_sheet.py` — the Step 0 engine: header-driven reader, checker, repairer and extender
  for the `CE Summary` sheet, plus an independent Python recomputation of every marker's
  statistics. **Required for Step 0.** If it is missing from this skill, say so rather than
  silently skipping the sheet check.
- `references/running_on_windows.md` — the user's actual Desktop layout (domain-managed PC:
  Python yes, Node no), one-time setup, the per-marker loop, the filename-index requirement, and
  common problems. **Read first** when running on their machine.
- `references/layout_spec.md` — slide geometry, palette, typography, what each region contains,
  and the per-page representative-heterozygote rule. Read when changing the visual design.
- `references/image_pipeline.md` — how panels are detected, the 510 bp calibration, the zoom
  peak-window logic (including why orange size-standard and cyan highlight pixels are excluded),
  and the OCR identification chain. Read when identification or cropping misbehaves.
- `references/verification.md` — copy-paste verification snippets and the failure signatures
  they detect. Read at step 4.