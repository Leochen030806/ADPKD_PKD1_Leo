# Verification

The image preview tool is unreliable in this environment — it returned blank for an entire
multi-marker session. Every defect that actually shipped was caught by parsing the pptx, so treat
structural verification as the primary QA and say so when reporting to the user.

Always start with the built-in validator:

```bash
python /mnt/skills/public/pptx/scripts/office/validate.py <out.pptx>
```

## Input audit (before building)

First ask the script what it can see:

```bash
node scripts/make_str_slide.js --list
```

Then audit the new marker's folder in detail:

```bash
python3 - <<'PY'
import glob, os, re
from PIL import Image
MARKER="1830"; IMGDIR="C:/Users/e1638543/Desktop/CE screen shoot"
order=['NA03814','NA03815','NA04738','NA04776','NA04820','NA06075','NA06890','NA07425',
       'NA07426','NA07428','NA09133','NA11518','NA16243','NA17942','NA22601','NA50194']
files=sorted(glob.glob(os.path.join(IMGDIR,MARKER,"*.PNG")))
print(f"{len(files)} files (expect 12)")
for f in files:
    w,h=Image.open(f).size
    print(f"  {os.path.basename(f):28s} {w}x{h}  {'orig?' if w>1000 else 'zoom?'}")
seen={}
for f in files:
    b=os.path.basename(f)[:-4]
    b=re.sub(r'-z$','',b,flags=re.I)
    b=re.sub(rf'^{MARKER}[-_]?','',b)
    for i in [int(x) for x in re.split(r'[_-]+',b) if x.isdigit()]:
        seen.setdefault(i,set()).add(b)
for i in range(1,17):
    s=sorted(seen.get(i,[]))
    tag=" <-- MISSING" if not s else (" <-- DUPLICATE" if len(s)>1 else "")
    print(f"{i:2d} {order[i-1]}: {s}{tag}")
PY
```

A missing index alongside a duplicated one is a filename typo — raise it, don't guess.

## Output checks (after building)

```bash
python3 - <<'PY'
import zipfile, re, io
from PIL import Image
from collections import Counter
F="out.pptx"; EMU=914400.0; PW,PH=7.5,13.33
z=zipfile.ZipFile(F)
slides=sorted([n for n in z.namelist() if re.match(r'ppt/slides/slide\d+\.xml$',n)],
              key=lambda s:int(re.search(r'(\d+)',s).group()))
print("slides:",len(slides))
for s in slides:
    x=z.read(s).decode()
    b=re.findall(r'<a:off x="(-?\d+)" y="(-?\d+)"/><a:ext cx="(\d+)" cy="(\d+)"/>',x)
    over=sum(1 for X,Y,CX,CY in b if int(X)/EMU<-.02 or int(Y)/EMU<-.02
             or (int(X)+int(CX))/EMU>PW+.02 or (int(Y)+int(CY))/EMU>PH+.02)
    low=max((int(Y)+int(CY))/EMU for X,Y,CX,CY in b)
    print(f"  {s.split('/')[-1]}: STR {re.findall(r'STR (\d+)',x)[:1]} "
          f"Marker {re.findall(r'Marker (\d+)',x)[:1]} "
          f"zoom={re.findall(r'Zoom · ([^<]+)',x)[:1]} "
          f"imgs={x.count('<p:pic>')} overflow={over} lowest={low:.2f}")
asp=[Image.open(io.BytesIO(z.read(n))).size
     for n in z.namelist() if n.startswith('ppt/media/') and n.lower().endswith('.png')]
print("aspect dist:", dict(sorted(Counter(round(w/h,1) for w,h in asp).items())))
for s in slides:
    x=z.read(s).decode()
    print(s.split('/')[-1], "GT:", re.findall(r'>(\d{3}/\d{3}|\d{3}|—)<',x))
PY
```

**Expected values**

| check | expected | failure means |
|---|---|---|
| slides | 2 per marker | a marker silently skipped (no data / no images) |
| imgs per slide | 17 | a sample lost its original or zoom |
| overflow | 0 | something spills off the page |
| lowest | ≈ 13.24 (< 13.33) | row geometry drifted |
| original aspect | ≈ 6.0 | 510 bp crop failed (see image_pipeline.md) |
| zoom aspect | < ~5 | peak-window crop failed |
| zoom label | the marker's own window | wrong marker's alleles used |

## Genotype reconciliation

The strongest single check: the rendered calls must reproduce the sheet. Count het and hom from
the extracted genotypes and compare to the sheet's observed heterozygosity — e.g. marker 1299
gives 10 het / 6 hom = 0.625, marker 1830 gives 10 het / 5 hom / 1 failed = 0.667. A mismatch
means binning or sample assignment went wrong, and it will point at which.

Failed samples appear as two consecutive `—` tokens (the call and the het/hom tag).

## Reporting

State which checks ran and that visual inspection was structural rather than by eye, then invite
the user to open the deck. Also surface, every time: the `[inferred]` assignments, any
filename/label mismatch warnings, and any sample lacking an image.
