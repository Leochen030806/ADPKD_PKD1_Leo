# Running this on the user's Windows machine

The user's PC is domain-managed: **Python is available, Node.js is not, and portable/green
executables are blocked by policy.** So use `scripts/make_str_slide.py`. The `.js` version is
functionally identical and kept for machines that do have Node.

Layout on their Desktop — one folder per marker, added one at a time:

```
C:\Users\e1638543\Desktop\
├── PKD1_CE_summary_robust.xlsx      one row per STR, filled in as each marker validates
├── CE screen shoot\
│   ├── 2517\   ├── 2290\   ├── 1830\   ├── 1299\      folder name = marker number
└── PKD1_STR_panel_CE_EN.pptx        the growing deck (script output)
```

Marker folders are scanned **recursively**, so either arrangement inside them works:

```
1830\                          1830\
├── 1_10_2.PNG                 ├── thumbnail\
├── 1_10_2-z.PNG               │   ├── 1_10_2.PNG   ...
└── ...                        └── zoom\
                                   ├── 1_10_2.PNG   ...
```

An image counts as a zoom if its name ends in `-z` **or** the word `zoom` appears anywhere in
its path below the marker folder — so files inside a `zoom\` subfolder need no suffix, and the
thumbnail and its zoom may share a filename.

## One-time setup

```powershell
pip install openpyxl python-pptx pillow
```

All three are ordinary pip wheels — no system components, no admin rights, nothing to unzip.
On a corporate network pip may need the proxy, e.g.
`pip install --proxy http://proxy:port openpyxl python-pptx pillow`, or
`pip install --user ...` if global site-packages is locked down.

Then edit `CONFIG` at the top of the script once, so no flags are ever needed:

```python
"XLSX":   r"C:/Users/e1638543/Desktop/PKD1_CE_summary_robust.xlsx",
"IMGDIR": r"C:/Users/e1638543/Desktop/CE screen shoot",
"OUTDIR": r"C:/Users/e1638543/Desktop",
```

## The per-marker loop

```powershell
python make_str_slide.py --list     # which markers have data + images
python make_str_slide.py --auto     # rebuild the whole deck from every marker folder
```

`--auto` is idempotent: it rebuilds `PKD1_STR_panel_CE_EN.pptx` from scratch using every marker
folder that also has a filled-in spreadsheet row, in STR order. Adding a folder and re-running is
the entire workflow — nothing is appended in place, so a re-run cannot duplicate or corrupt
earlier markers. Other modes: `python make_str_slide.py 2290` (one marker) and
`--combined 2517 2290` (explicit subset and order).

Roughly 30–60 s per marker; the pixel scanning is the slow part.

## The one hard requirement: filenames must carry sample indices

The Python build has **no OCR** (Tesseract can't be installed on this machine), so sample identity
comes entirely from the digits in the filename, in panel order:

```
16_9_5.PNG      panel 1 = sample 16, panel 2 = sample 9, panel 3 = sample 5
16_9_5-z.PNG    the matching zoom
14.PNG          a one-panel window showing sample 14
```

The count of indices must equal the number of panels in the image. A marker/STR number prefix
(`1830-16_9_5.PNG`) is stripped automatically, so both styles work. If a name can't be parsed the
script says exactly which file and what's wrong instead of guessing — never work around that by
editing the script; fix the filename.

This also handles mislabelled CE runs for free: marker 1830 had two panels both labelled NA07426
on screen, and the filename `16_9_5` is what put NA04820 in the right row.

Overlapping capture windows are fine — if the last window repeats samples 14 and 15, the first
window to claim a sample wins and nothing is reported. A repeated index only becomes a warning
when some sample ends up with no image at all, which is the signature of a typo.

## Renaming the four existing marker folders

Folders built before the Python switch relied on OCR for a few files. These six need renaming
(the new names were verified against the panel labels):

| folder | old name | new name |
|---|---|---|
| 2517 | `3-13empty.PNG` | `12_13_14.PNG` |
| 2517 | `3-13-empty-z.PNG` | `12_13_14-z.PNG` |
| 2290 | `5-16.PNG` | `5-14_15_16.PNG` |
| 2290 | `5-16-z.PNG` | `5-14_15_16-z.PNG` |
| 1299 | `11-16.PNG` | `11-14_15_16.PNG` |
| 1299 | `11-16-z.PNG` | `11-14_15_16-z.PNG` |

Everything else in those folders already parses (`3-1_2_3`, `3_14_15_16`, `5-13_14_15`,
`8-16_9_5`, …). Folder 1830 needs no changes.

## Common problems

| symptom | cause | fix |
|---|---|---|
| `Missing dependency: pptx` | packages not installed for this interpreter | `pip install openpyxl python-pptx pillow` |
| marker shows `skip (no image folder)` | folder name ≠ marker number in column B | rename the folder |
| marker shows `skip (no data in sheet)` | spreadsheet row not filled in yet | fill in the row |
| `no sample indices in the filename` | name has no usable digits | rename to the sample numbers the window shows |
| `lists N sample(s) but the image has M panel(s)` | index count ≠ panel count | list every panel, e.g. `14_15_16` |
| only 6 files in a folder | zooms saved without `-z`, overwriting the originals | re-export the zooms with `-z` |
| `no image for genotyped sample(s)` | a window is missing, or an index typo | check the listed samples and the duplicate-index hints |
