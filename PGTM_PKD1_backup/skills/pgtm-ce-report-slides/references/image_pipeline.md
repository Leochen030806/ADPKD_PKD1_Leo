# Image pipeline — panel detection, cropping, sample identification

Every rule here exists because a specific screenshot broke an earlier version. When something
misbehaves, find the matching failure signature rather than tweaking thresholds blindly.

## Panel detection (`panelBands`)

GeneMapper stacks three sample panels per window. Each plot sits between two **grey header
bars** (RGB roughly equal, 205–250). Detect rows that are ≥60 % grey, group them into bars, and
take the gaps between consecutive bars as plot regions — the three tallest, sorted top to bottom.

**Trailing-panel rule.** Screenshots are often cut short so the *last* panel has no bar beneath
it. Without a fix that panel vanishes: `11-4_5_6-z.PNG` (545 px tall) yielded only two panels and
NA06075's zoom went missing entirely. So if the final bar ends more than 40 px above the image
bottom, the region below it counts as a plot too.

Single-panel windows (`8-14.PNG`, `7-16.PNG`, ~190 px tall) are normal and handled by the same
logic.

## Frame calibration (`frameX`)

The plot's left and right borders are near-black vertical runs (≥70 % of the plot height). They
mark **0 bp** and `CONFIG.BP_SPAN` bp (default 773 — GeneMapper's default view). Calibration was
confirmed by OCR-ing the axis numbers on marker 1299: `x = 63 + bp × 1.575` at W = 1303, putting
500 bp at x ≈ 850.

Everything positional derives from these two x values, so the crops stay correct across the
1299–1353 px width variation between captures.

## Full-trace crop (510 bp)

Cut the thumbnail at `CONFIG.CROP_BP` (510):

```
width = xL + (510 / BP_SPAN) × (xR − xL)
```

Keep `left = 0` so the y-axis labels survive. This drops the empty >500 bp tail; aspect goes from
~9:1 to ~6:1, so at the same column width the peaks render roughly 50 % taller. **An original at
aspect ~9 in the finished pptx means the crop silently failed** — check `frameX` found two border
columns.

## Zoom crop (marker peak window)

Some markers' zooms are captured narrow (~600 px, 1299) and some full-width (~1350 px, 2290) —
so width cannot classify original vs zoom, and full-width zooms would render as unreadable
slivers. For wide zooms, compute one **common peak window** across all genotyped samples and
crop every zoom to it, giving all rows a shared x-scale.

Finding peaks means finding strongly-coloured pixels, with two exclusions:

- **Orange size standard** `(255,146,51)` — present across the whole trace, so including it
  returns the full width and the crop does nothing. Excluded via `r>200 && 105≤g≤190 && b<100`.
- **Cyan active-panel highlight** `(0,255,255)` — GeneMapper outlines the selected panel, which
  spans the entire frame. Excluded via `g>180 && b>180 && r<120`. This one produced a peak range
  of `0…W` on exactly the panels that happened to be selected.

Marker dye peaks are pure and saturated (red `(255,0,0)`, blue, magenta) and survive both filters.
Panels whose detected range still exceeds 80 % of the frame are treated as detection failures and
skipped when combining the window, so one bad panel can't widen everyone's crop.

The zoom column header is derived from the sheet's observed alleles (outliers >40 bp from the
median dropped, rounded outward to 5 bp): 1299 → ≈240–265, 2290 → ≈365–400, 2517 → ≈415–445,
1830 → ≈355–390.

## Sample identification

Priority chain, per panel:

**1. Filename index — authoritative.** Digits in the name are sample indices in panel order
(`8-16_9_5` → samples 16, 9, 5). Applied only when the count matches the detected panel count,
which is what makes `11-16.PNG` (one index, three panels) fall through to OCR correctly. Tagged
`[named]`.

Filenames outrank the on-screen label because CE runs get mislabelled: marker 1830's window
`8-16_9_5` had panel 3 labelled NA07426 (a duplicate of panel 2) when it was really NA04820. The
script reports every such disagreement instead of resolving it silently.

**2. Exact OCR of the label bar.** The sample ID lives in the grey bar *above* the plot, not in
the plot — OCR-ing the plot region returns noise from the trace, which was a real early bug.
Crop `[plotTop−24, plotTop−2]`, upscale 4×, read two column bands (filename and sample-name
fields), optionally binarised at 140.

Post-processing that makes it reliable:
- letter→digit repair (`O`→0, `B`→8, `I`/`L`→1, `S`→5, `G`→6, `Z`→2, `A`→4, `Q`/`D`→0),
- truncate at the date anchor (`2026`/`2027`…) so the timestamp can't pollute the match,
- **exact contiguous substring** match of each known 5-digit ID against the digit stream.

Scoring by similarity alone was not discriminative enough; exact-substring plus the closed set of
16 IDs is what reached 32/32. Tagged `[read]`.

**3. Constrained fuzzy fallback.** For samples still unassigned, pick the best LCS match among
panels that were **not** positively identified. Excluding positively-identified panels matters:
capture windows overlap (`11-16` also shows samples 14–15), and those duplicate panels were
stealing slots — NA06075's zoom was once assigned to a panel showing NA17942. Tagged `[inferred]`;
worth an eyeball.

Originals and zooms are identified independently and joined by sample, so the two sets need no
filename correspondence at all.

## Failure signatures

| symptom | cause | fix |
|---|---|---|
| a sample's zoom or original is `—` | panel not detected (short screenshot) or file lost to `-z` collision | check image height and file count |
| originals at aspect ~9 in the pptx | `frameX` failed | verify the plot borders are dark and unbroken |
| zooms at aspect ~9 | peak window covered the full frame | a colour exclusion is missing |
| a zoom cropped to a thin sliver | peak range computed from one panel only | check the ≥80 % skip rule |
| wrong sample on a row | `[inferred]` chain, or a filename index typo | re-run the index audit; ask the user |
