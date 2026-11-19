#!/usr/bin/env python3
"""
make_str_slide.py — PKD1 PGT-M CE genotyping report slides (Python edition)

Two portrait slides per STR marker (8 of the 16 Coriell samples each): per-sample
full-trace + zoom electropherograms, auto-binned genotypes, marker-level stats.

Samples are identified from the SAMPLE INDICES IN THE FILENAME (no OCR), e.g.
    16_9_5.PNG      panel 1 = sample 16, panel 2 = sample 9, panel 3 = sample 5
    16_9_5-z.PNG    the matching zoom
    14.PNG          a one-panel window showing sample 14
The index list must have exactly as many numbers as the window has panels.

Dependencies (all plain pip wheels, no system components):
    pip install openpyxl python-pptx pillow

Usage
    python make_str_slide.py --list                 what's ready, build nothing
    python make_str_slide.py --auto                 rebuild the whole combined deck
    python make_str_slide.py 2290                   one marker (marker no. or STR no.)
    python make_str_slide.py --combined 2517 2290   explicit subset / order
Path overrides: --xlsx <f> --imgdir <d> --outdir <d> --outname <n> --cropbp <n> --bpspan <n>
"""

import os, re, sys, glob, shutil, tempfile

CONFIG = {
    "XLSX":   r"C:/Users/e1638543/Desktop/PKD1_CE_summary_robust.xlsx",
    "IMGDIR": r"C:/Users/e1638543/Desktop/CE screen shoot",
    "OUTDIR": r"C:/Users/e1638543/Desktop",
    "SHEET":  "CE Summary",
    "CROP_BP": 510,     # cut the full-trace thumbnail here (bp)
    "BP_SPAN": 773,     # bp across the plot frame in the GeneMapper view
    "OUTNAME": "PKD1_STR_panel_CE_EN",
    "EXAMPLE": {},      # pin a page's example, e.g. {"1299a": "NA03815"}
}

try:
    from openpyxl import load_workbook
    from PIL import Image
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
except ImportError as e:
    sys.exit(f'Missing dependency: {e.name}\n    pip install openpyxl python-pptx pillow')

# ---------------------------------------------------------------- palette
INK, TEAL, ACC = "12303F", "1C7293", "02C39A"
PANEL, MUTE, LINE = "EDF3F5", "5E6E76", "D5E0E4"
HET, HOM, WHITE, SOFT = TEAL, "8A97A0", "FFFFFF", "F6FAFB"
F, FS = "Calibri", "Cambria"
rgb = lambda h: RGBColor.from_string(h)

SAMPLE_ORDER = ["NA03814","NA03815","NA04738","NA04776","NA04820","NA06075","NA06890","NA07425",
                "NA07426","NA07428","NA09133","NA11518","NA16243","NA17942","NA22601","NA50194"]

# ================================================================ spreadsheet
def read_str(key):
    """Look up a row by STR number (col A) or marker number (col B)."""
    ws = load_workbook(CONFIG["XLSX"], data_only=True)[CONFIG["SHEET"]]
    cell = lambda r, c: ws.cell(row=r, column=c).value
    row = None
    for r in range(5, 18):
        if str(cell(r, 1)) == str(key): row = r; break
    if row is None:
        for r in range(5, 18):
            if str(cell(r, 2)) == str(key): row = r; break
    if row is None:
        raise ValueError(f'STR / marker "{key}" not found in sheet "{CONFIG["SHEET"]}"')

    str_no, marker = cell(row, 1), cell(row, 2)
    repeat = cell(row, 3) or "N"
    rep_len = len(str(repeat))

    def clean_num(v, nd=6):
        """IEEE-754 tidy-up: Excel stores 1 as 0.9999999999999999 and 15 as 15.000000000000002.
        Round to `nd` decimals, then drop a trailing .0 so counts read as integers."""
        if v is None or isinstance(v, str): return v
        try: f = round(float(v), nd)
        except (TypeError, ValueError): return v
        return int(f) if abs(f - round(f)) < 1e-9 else f

    typed, n_all = clean_num(cell(row, 36)), clean_num(cell(row, 37))
    het = clean_num(cell(row, 38))
    observed = [clean_num(float(x), 3) for x in re.findall(r"[\d.]+", str(cell(row, 39) or ""))]

    def snap(v):
        return min(observed, key=lambda a: abs(a - v)) if observed else v

    samples = {}
    for i, s in enumerate(SAMPLE_ORDER):
        a1, a2 = cell(row, 4 + i * 2), cell(row, 5 + i * 2)
        o = {"call": None, "tag": None}
        if a1 is not None:
            b1 = snap(float(a1))
            if a2 is None:
                o = {"call": f"{b1:g}", "tag": "hom"}
            else:
                b2 = snap(float(a2)); lo, hi = sorted((b1, b2))
                o = ({"call": f"{lo:g}", "tag": "hom"} if lo == hi
                     else {"call": f"{lo:g}/{hi:g}", "tag": "het"})
        samples[s] = o

    # zoom window = the main allele cluster, outliers dropped, rounded outward to 5 bp
    if observed:
        srt = sorted(observed); med = srt[len(srt) // 2]
        clust = [a for a in srt if abs(a - med) <= 40] or srt
        z_lo = int((min(clust) - 6) // 5 * 5); z_hi = int(-(-(max(clust) + 6) // 5) * 5)
    else:
        z_lo, z_hi = 240, 260

    het_pct = "—"
    if het is not None:
        v = het * 100
        het_pct = f"{v:.0f}%" if abs(v - round(v)) < 0.05 else f"{v:.1f}%"

    return {"strNo": str_no, "marker": marker, "repeat": repeat, "repLen": rep_len,
            "samples": samples, "typed": typed, "nAll": n_all,
            "hetPct": het_pct,
            "observed": observed, "zoomRange": f"≈{z_lo}–{z_hi} bp"}

# ================================================================ image geometry
_bands, _frame = {}, {}

def _pixels(path):
    im = Image.open(path).convert("RGB")
    return im, im.size[0], im.size[1], im.tobytes()

def panel_bands(path):
    """(W, H, [(y0,y1) ...]) plot regions between the grey header bars."""
    if path in _bands: return _bands[path]
    im, W, H, px = _pixels(path)
    def gray_row(y):
        n = t = 0
        for x in range(0, W, 4):
            i = (y * W + x) * 3; r, g, b = px[i], px[i+1], px[i+2]; t += 1
            if abs(r - g) < 12 and abs(g - b) < 12 and 205 < r < 250: n += 1
        return bool(t) and n / t > 0.6
    bars, run = [], None
    for y in range(H):
        if gray_row(y): run = [y, y] if run is None else [run[0], y]
        elif run: bars.append(run); run = None
    if run: bars.append(run)
    gaps = [[bars[i][1] + 2, bars[i+1][0] - 1]
            for i in range(len(bars) - 1) if bars[i+1][0] - bars[i][1] > 40]
    # a screenshot cut short leaves the last panel with no bar under it
    if bars and H - bars[-1][1] > 40: gaps.append([bars[-1][1] + 2, H - 1])
    gaps.sort(key=lambda g: -(g[1] - g[0]))
    gaps = sorted(gaps[:3])
    _bands[path] = (W, H, gaps)
    return _bands[path]

def frame_x(path):
    """x of the plot's left/right borders = 0 bp and BP_SPAN bp."""
    if path in _frame: return _frame[path]
    W, H, gaps = panel_bands(path)
    _, _, _, px = _pixels(path)
    y0, y1 = gaps[0]
    xs = []
    for x in range(W):
        n = sum(1 for y in range(y0, y1)
                if px[(y*W+x)*3] < 90 and px[(y*W+x)*3+1] < 90 and px[(y*W+x)*3+2] < 90)
        if n / (y1 - y0) > 0.7: xs.append(x)
    # need two borders far enough apart to be a real frame, else fall back to proportions
    if len(xs) >= 2 and xs[-1] - xs[0] > W * 0.3:
        _frame[path] = (xs[0], xs[-1])
    else:
        _frame[path] = (round(W * 0.048), round(W * 0.955))
    return _frame[path]

def peak_x_range(path, y0, y1):
    """Horizontal span of the marker's dye peaks, ignoring the size standard and the
    cyan 'selected panel' border — both span the whole frame and would defeat the crop."""
    _, W, H, px = _pixels(path)
    lo, hi = W, 0
    for x in range(W):
        hits = 0
        for y in range(y0, y1):
            i = (y*W+x)*3; r, g, b = px[i], px[i+1], px[i+2]
            strong = (max(r, g, b) - min(r, g, b) > 70) and max(r, g, b) > 120
            orange = r > 200 and 105 <= g <= 190 and b < 100          # LIZ size standard
            cyan   = g > 180 and b > 180 and r < 120                  # active-panel border
            if strong and not orange and not cyan: hits += 1
        if hits >= 3: lo, hi = min(lo, x), max(hi, x)
    if hi <= lo: return None
    pad = round((hi - lo) * 0.35)
    return (max(0, lo - pad), min(W, hi + pad))

def crop_panel(path, k, out, crop_bp=None):
    W, H, gaps = panel_bands(path)
    y0, y1 = gaps[k] if k < len(gaps) else gaps[-1]
    width = W - 6
    if crop_bp:
        xl, xr = frame_x(path)
        width = min(W, round(xl + (crop_bp / CONFIG["BP_SPAN"]) * (xr - xl)))
    Image.open(path).crop((0, y0, max(20, width), y1)).save(out)
    return out

def crop_zoom(path, k, out, frac):
    W, H, gaps = panel_bands(path)
    y0, y1 = gaps[k] if k < len(gaps) else gaps[-1]
    left, width = 0, W - 6
    if frac and W > 1000:
        xl, xr = frame_x(path)
        left = max(0, round(xl + frac[0] * (xr - xl)))
        width = min(W - left, round((frac[1] - frac[0]) * (xr - xl)))
    Image.open(path).crop((left, y0, left + max(20, width), y1)).save(out)
    return out

def zoom_peak_window(D, mapping):
    lo, hi, any_ = 1.0, 0.0, False
    for s in SAMPLE_ORDER:
        pz = mapping[s]["zoom"]
        if not pz or D["samples"][s]["call"] is None: continue
        W, H, gaps = panel_bands(pz["file"])
        y0, y1 = gaps[pz["k"]] if pz["k"] < len(gaps) else gaps[-1]
        pr = peak_x_range(pz["file"], y0, y1)
        if not pr: continue
        xl, xr = frame_x(pz["file"])
        a, b = (pr[0]-xl)/(xr-xl), (pr[1]-xl)/(xr-xl)
        if b - a > 0.8: continue                 # detection failure — don't widen everyone
        lo, hi, any_ = min(lo, a), max(hi, b), True
    if not any_ or hi <= lo: return None
    return (max(0.0, lo - 0.06), min(1.0, hi + 0.06))

# ================================================================ discovery
def _pngs_under(root):
    """Every .png under `root`, at any depth, as (path, path-relative-to-root)."""
    out = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in sorted(filenames):
            if fn.lower().endswith(".png"):
                p = os.path.join(dirpath, fn)
                out.append((p, os.path.relpath(p, root)))
    return sorted(set(out))

def find_images(str_no, marker):
    """One folder per marker (preferred), scanned recursively so thumbnail/ and zoom/
    subfolders work. A STR-number folder or a flat directory also work."""
    for folder in (str(marker), str(str_no)):
        d = os.path.join(CONFIG["IMGDIR"], folder)
        if os.path.isdir(d):
            files = _pngs_under(d)
            if files: return d, files
    pat = re.compile(rf"^({marker}|{str_no})[-_]", re.I)
    files = []
    if os.path.isdir(CONFIG["IMGDIR"]):
        files = [(os.path.join(CONFIG["IMGDIR"], f), f) for f in sorted(os.listdir(CONFIG["IMGDIR"]))
                 if f.lower().endswith(".png") and pat.match(f)]
    return CONFIG["IMGDIR"], files

def is_zoom(rel):
    """Zoom if the -z suffix is on the filename, or 'zoom' appears anywhere in the path
    below the marker folder (so a zoom/ subfolder needs no per-file suffix)."""
    return bool(re.search(r"-z\.png$", rel, re.I) or re.search(r"zoom", rel, re.I))

def idx_from_name(path, prefixes):
    """Sample indices encoded in the filename, in panel order. None if not a clean list."""
    b = os.path.basename(path)
    b = re.sub(r"\.png$", "", b, flags=re.I)
    b = re.sub(r"-z$", "", b, flags=re.I)
    b = re.sub(r"[_-]?zoom.*$", "", b, flags=re.I)
    for p in prefixes:
        m = re.match(rf"^{p}[-_]?(.*)$", b, re.I)
        if m: b = m.group(1); break
    b = re.sub(r"^(thumb(nail)?|orig(inal)?|full)[-_]?", "", b, flags=re.I)
    parts = [int(x) for x in re.split(r"[_\-]+", b) if x.isdigit()]
    if not parts: return None
    if any(n < 1 or n > len(SAMPLE_ORDER) for n in parts): return None
    if len(set(parts)) != len(parts): return None
    return parts

def map_files(pairs, prefixes, problems, dups):
    """{sample: {'file','k'}} from filename indices. First claim on a sample wins —
    capture windows legitimately overlap, so a repeat is normal, not an error. Repeats are
    recorded in `dups` and only surfaced if some sample ends up with no image at all."""
    out = {}
    for f, rel in pairs:
        W, H, gaps = panel_bands(f)
        idx = idx_from_name(f, prefixes)
        name = rel.replace("\\", "/")
        if idx is None:
            problems.append(f"{name}: no sample indices in the filename "
                            f"({len(gaps)} panels) — rename it to the sample numbers it shows, "
                            f"e.g. 12_13_14.PNG")
            continue
        if len(idx) != len(gaps):
            problems.append(f"{name}: filename lists {len(idx)} sample(s) {idx} but the image has "
                            f"{len(gaps)} panel(s) — rename it to list all {len(gaps)}")
            continue
        for k, i in enumerate(idx):
            s = SAMPLE_ORDER[i - 1]
            if s in out:
                dups.append(f"index {i} ({s}) appears in both {out[s]['rel']} and {name}")
                continue
            out[s] = {"file": f, "k": k, "rel": name}
    return out

# ================================================================ deck helpers
def _tf(shape, margin=0):
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Emu(margin)
    return tf

def _run(p, text, font=F, size=10, bold=False, color=INK, italic=False, spc=None):
    r = p.add_run(); r.text = text
    r.font.name, r.font.size, r.font.bold, r.font.italic = font, Pt(size), bold, italic
    r.font.color.rgb = rgb(color)
    if spc is not None:
        r.font._rPr.set("spc", str(int(spc * 100)))
    return r

def text_box(sl, x, y, w, h, runs, align=None, anchor=None, line_spacing=None):
    """runs = [(text, {opts}), ...]; a 'br' key on an option dict starts a new line."""
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = _tf(tb)
    if anchor: tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    if align: p.alignment = align
    if line_spacing: p.line_spacing = line_spacing
    for text, o in runs:
        o = dict(o)
        if o.pop("br", False):
            p = tf.add_paragraph()
            if align: p.alignment = align
            if line_spacing: p.line_spacing = line_spacing
        _run(p, text, **o)
    return tb

def round_rect(sl, x, y, w, h, radius=0.06, fill=None, line=None, lw=0.75):
    sh = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                             Inches(x), Inches(y), Inches(w), Inches(h))
    try: sh.adjustments[0] = min(0.5, radius / min(w, h))
    except Exception: pass
    if fill: sh.fill.solid(); sh.fill.fore_color.rgb = rgb(fill)
    else: sh.fill.background()
    if line: sh.line.color.rgb = rgb(line); sh.line.width = Pt(lw)
    else: sh.line.fill.background()
    sh.shadow.inherit = False
    return sh

def hline(sl, x, y, w, color=LINE, lw=0.5):
    c = sl.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x), Inches(y), Inches(x + w), Inches(y))
    c.line.color.rgb = rgb(color); c.line.width = Pt(lw)
    return c

def fit_box(pw, ph, mw, mh):
    s = min(mw / pw, mh / ph)
    return pw * s, ph * s

# ================================================================ page
def draw_page(prs, D, S, names, part_no, part_label, pin_key):
    sl = prs.slides.add_slide(prs.slide_layouts[6])

    text_box(sl, 0.35, 0.28, 6.8, 0.26,
             [("PKD1 STR PANEL · CE GENOTYPING SUMMARY",
               dict(size=10.5, bold=True, color=TEAL, spc=2))])
    text_box(sl, 0.32, 0.52, 4.7, 0.58,
             [(f"STR {D['strNo']}", dict(font=FS, size=29, bold=True, color=INK)),
              ("   ·   ",           dict(font=FS, size=29, color=LINE)),
              (f"Marker {D['marker']}", dict(font=FS, size=29, bold=True, color=TEAL))],
             anchor=MSO_ANCHOR.MIDDLE)

    round_rect(sl, 5.15, 0.58, 2.0, 0.48, 0.10, fill=INK)
    text_box(sl, 5.15, 0.58, 2.0, 0.48,
             [("Repeat unit  ", dict(size=10, color="BFD3DB")),
              (f"({D['repeat']})n", dict(font=FS, size=13, bold=True, color=WHITE, italic=True))],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    round_rect(sl, 0.35, 1.14, 2.15, 0.30, 0.15, fill=PANEL, line=LINE)
    text_box(sl, 0.35, 1.14, 2.15, 0.30,
             [(f"Page {part_no} / 2  ·  Samples {part_label}",
               dict(size=9, bold=True, color=TEAL))],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    cy, ch = 1.60, 0.92
    def card(x, w, big, bs, lab):
        txt = str(big)
        # shrink long values (e.g. "100%", "8 alleles") so they can't overflow the card
        est = bs * 0.55 / 72.0 * len(txt)          # rough width in inches
        if est > w - 0.16: bs = max(11, bs * (w - 0.16) / est)
        round_rect(sl, x, cy, w, ch, 0.06, fill=PANEL, line=LINE)
        text_box(sl, x, cy + 0.10, w, 0.46, [(txt, dict(size=bs, bold=True, color=INK))],
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        text_box(sl, x, cy + 0.58, w, 0.28, [(lab, dict(size=8.5, color=MUTE))],
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    card(0.35, 1.40, D["typed"], 26, "Samples typed (n)")
    card(1.85, 1.40, D["nAll"],  26, "Alleles / locus")
    card(3.35, 1.40, D["hetPct"], 22, "Heterozygosity (obs.)")
    round_rect(sl, 4.90, cy, 2.25, ch, 0.06, fill=PANEL, line=LINE)
    obs_txt = " · ".join(f"{a:g}" for a in D["observed"])
    obs_sz = 15 if len(obs_txt) <= 22 else (12 if len(obs_txt) <= 34 else 10)
    text_box(sl, 4.90, cy + 0.06, 2.25, 0.54, [(obs_txt, dict(size=obs_sz, bold=True, color=INK))],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text_box(sl, 4.90, cy + 0.58, 2.25, 0.28, [("Alleles observed (bp)", dict(size=8.5, color=MUTE))],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    # representative heterozygote
    ex = CONFIG["EXAMPLE"].get(pin_key)
    if not ex:
        hets = [n for n in names if D["samples"][n]["tag"] == "het" and S[n]["zoom"]]
        def spacing(n):
            a, b = (float(v) for v in D["samples"][n]["call"].split("/"))
            return round((b - a) / D["repLen"])
        wide = sorted([n for n in hets if spacing(n) >= 2], key=spacing)
        ex = wide[0] if wide else (hets[0] if hets else None)

    ex_y, ex_h = 2.62, 1.34
    round_rect(sl, 0.35, ex_y, 6.8, ex_h, 0.06, fill=SOFT, line=LINE)
    if ex and S[ex]["zoom"]:
        pw, ph = Image.open(S[ex]["zoom"]).size
        w, h = fit_box(pw, ph, 3.0, 1.00)
        x, y = 0.55, ex_y + (ex_h - h) / 2 + 0.05
        sl.shapes.add_picture(S[ex]["zoom"], Inches(x), Inches(y), Inches(w), Inches(h))
        round_rect(sl, x, y, w, h, 0.03, line=LINE)
        text_box(sl, x, ex_y + 0.11, w, 0.22,
                 [("Representative heterozygote", dict(size=9, bold=True, color=TEAL))])
        call = D["samples"][ex]["call"] or ""
        text_box(sl, x + w + 0.22, ex_y + 0.30, 1.75, 0.9,
                 [(ex, dict(size=12.5, bold=True, color=INK)),
                  (f"Alleles {call.replace('/', ' / ')} bp", dict(size=10, color=INK, br=True)),
                  ("Balanced peaks · well resolved · low stutter", dict(size=8.5, color=MUTE, br=True))],
                 line_spacing=1.1)

    lg = 5.55
    round_rect(sl, lg, ex_y + 0.22, 0.14, 0.14, 0.03, fill=HET)
    text_box(sl, lg + 0.22, ex_y + 0.16, 1.35, 0.26, [("Heterozygous (het)", dict(size=9.5))],
             anchor=MSO_ANCHOR.MIDDLE)
    round_rect(sl, lg, ex_y + 0.52, 0.14, 0.14, 0.03, fill=HOM)
    text_box(sl, lg + 0.22, ex_y + 0.46, 1.35, 0.26, [("Homozygous (hom)", dict(size=9.5))],
             anchor=MSO_ANCHOR.MIDDLE)
    text_box(sl, lg - 0.02, ex_y + 0.82, 1.6, 0.26,
             [(f"({D['repeat']})n · {D['repLen']} bp/repeat", dict(size=8.5, italic=True, color=MUTE))])

    # section header
    bar = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.35), Inches(4.16), Inches(0.11), Inches(0.20))
    bar.fill.solid(); bar.fill.fore_color.rgb = rgb(ACC); bar.line.fill.background(); bar.shadow.inherit = False
    text_box(sl, 0.54, 4.08, 6.6, 0.32,
             [(f"Per-sample CE traces  ·  Samples {part_label}", dict(font=FS, size=13.5, bold=True, color=INK))],
             anchor=MSO_ANCHOR.MIDDLE)
    hy = 4.48
    text_box(sl, 0.30, hy, 1.4, 0.22, [("Sample / genotype", dict(size=8.5, bold=True, color=MUTE))])
    text_box(sl, 1.40, hy, 3.4, 0.22,
             [(f"Raw electropherogram · full trace (0–{CONFIG['CROP_BP']} bp)", dict(size=8.5, bold=True, color=MUTE))])
    text_box(sl, 4.90, hy, 2.2, 0.22, [(f"Zoom · {D['zoomRange']}", dict(size=8.5, bold=True, color=MUTE))])

    # rows
    LX, LW, OX, ZX = 0.30, 1.02, 1.40, 4.90
    row_y, pitch, block = 4.78, 1.00, 0.86
    for nm in names:
        o = D["samples"][nm]
        hline(sl, 0.30, row_y - 0.04, 6.85)
        mid = row_y + block / 2
        round_rect(sl, LX, mid - 0.30, 0.10, 0.10, 0.02, fill=(HET if o["tag"] == "het" else HOM))
        text_box(sl, LX + 0.16, mid - 0.36, LW, 0.24, [(nm, dict(size=10.5, bold=True, color=INK))],
                 anchor=MSO_ANCHOR.MIDDLE)
        text_box(sl, LX + 0.16, mid - 0.06, LW, 0.36,
                 [(o["call"] or "—", dict(size=11, bold=True, color=(HET if o["tag"] == "het" else INK))),
                  (o["tag"] or "—", dict(size=8, color=MUTE, br=True))],
                 line_spacing=0.95)
        for key, x, maxw in (("orig", OX, 3.35), ("zoom", ZX, 2.30)):
            p = S[nm][key]
            if p:
                pw, ph = Image.open(p).size
                w, h = fit_box(pw, ph, maxw, 0.74)
                y = row_y + (block - h) / 2
                sl.shapes.add_picture(p, Inches(x), Inches(y), Inches(w), Inches(h))
                round_rect(sl, x, y, w, h, 0.03, line=LINE)
            else:
                text_box(sl, x, row_y + block / 2 - 0.1, maxw, 0.2,
                         [("(image pending)", dict(size=8, italic=True, color=HOM))],
                         align=PP_ALIGN.CENTER)
        row_y += pitch
    hline(sl, 0.30, row_y - 0.04, 6.85)
    text_box(sl, 0.35, 13.02, 6.8, 0.22,
             [(f"PKD1 PGT-M STR linkage marker  ·  Marker {D['marker']} (STR {D['strNo']})  ·  "
               f"GeneMapper / SeqStudio CE  ·  samples from filename indices  ·  "
               f"auto-binning {D['repLen']} bp ({D['repeat']})", dict(size=7.5, color=MUTE))])

# ================================================================ build
def prepare(key, work):
    D = read_str(key)
    tag = f"STR {D['strNo']} (Marker {D['marker']})"
    if D["typed"] is None:
        print(f"{tag}: no data in sheet — skipped."); return None
    d, files = find_images(D["strNo"], D["marker"])
    origs = [(f, rel) for f, rel in files if not is_zoom(rel)]
    zooms = [(f, rel) for f, rel in files if is_zoom(rel)]
    if not origs:
        print(f"{tag}: no images found in {d} — skipped."); return None

    prefixes = [D["marker"], D["strNo"]]
    problems, dups = [], []
    O = map_files(origs, prefixes, problems, dups)
    Z = map_files(zooms, prefixes, problems, dups)

    mapping = {s: {"orig": O.get(s), "zoom": Z.get(s)} for s in SAMPLE_ORDER}
    print(f"{tag}  images: {d}  ({len(origs)} full-trace, {len(zooms)} zoom)")
    for s in SAMPLE_ORDER:
        o, z = mapping[s]["orig"], mapping[s]["zoom"]
        note = "  (no genotype)" if D["samples"][s]["call"] is None else ""
        fmt = lambda p: f"{p['rel']} p{p['k']+1}" if p else "—"
        print(f"  {s}: {fmt(o)}  |  {fmt(z)}{note}")
    missing = [s for s in SAMPLE_ORDER
               if D["samples"][s]["call"] is not None and not mapping[s]["orig"]]
    if missing:
        problems.append("no image for genotyped sample(s): " + ", ".join(missing))
        # a missing sample next to a repeated index is the signature of a filename typo
        for d in dict.fromkeys(dups):
            problems.append("possible filename typo — " + d)
    if problems:
        print("  ! problems:")
        for p in problems: print("     " + p)

    zwin = zoom_peak_window(D, mapping)
    S = {}
    for s in SAMPLE_ORDER:
        S[s] = {"orig": None, "zoom": None}
        if mapping[s]["orig"]:
            p = mapping[s]["orig"]
            S[s]["orig"] = crop_panel(p["file"], p["k"], os.path.join(work, f"o_{D['strNo']}_{s}.png"),
                                      CONFIG["CROP_BP"])
        if mapping[s]["zoom"]:
            p = mapping[s]["zoom"]
            S[s]["zoom"] = crop_zoom(p["file"], p["k"], os.path.join(work, f"z_{D['strNo']}_{s}.png"), zwin)
    return D, S

def new_deck():
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(7.5), Inches(13.33)
    return prs

def add_pages(prs, D, S):
    draw_page(prs, D, S, SAMPLE_ORDER[:8], "1", "1 – 8",  f"{D['marker']}a")
    draw_page(prs, D, S, SAMPLE_ORDER[8:], "2", "9 – 16", f"{D['marker']}b")

def build_deck(key):
    work = tempfile.mkdtemp(prefix="ce_")
    try:
        prep = prepare(key, work)
        if not prep: return
        D, S = prep
        prs = new_deck(); add_pages(prs, D, S)
        out = os.path.join(CONFIG["OUTDIR"], f"PKD1_Marker{D['marker']}_CE_EN.pptx")
        prs.save(out); print("WROTE", out)
    finally:
        shutil.rmtree(work, ignore_errors=True)

def build_combined(keys):
    work = tempfile.mkdtemp(prefix="ce_")
    try:
        prs = new_deck(); done = []
        for k in keys:
            prep = prepare(k, work)
            if not prep: continue
            D, S = prep; add_pages(prs, D, S); done.append(str(D["marker"]))
        if not done: print("Nothing to combine."); return
        out = os.path.join(CONFIG["OUTDIR"], CONFIG["OUTNAME"] + ".pptx")
        prs.save(out)
        print(f"WROTE {out}  (markers: {', '.join(done)}, {len(done)*2} slides)")
    finally:
        shutil.rmtree(work, ignore_errors=True)

def discover():
    ws = load_workbook(CONFIG["XLSX"], data_only=True)[CONFIG["SHEET"]]
    cell = lambda r, c: ws.cell(row=r, column=c).value
    rows = []
    for r in range(5, 18):
        s, m, typed = cell(r, 1), cell(r, 2), cell(r, 36)
        if s is None or m is None: continue
        _, files = find_images(s, m)
        rows.append({"strNo": s, "marker": m, "typed": typed,
                     "n": len(files), "ready": typed is not None and len(files) > 0})
    return rows

def report(rows):
    print(f"Scanning {CONFIG['IMGDIR']}")
    for r in rows:
        why = "no image folder" if r["n"] == 0 else ("no data in sheet" if r["typed"] is None else f"{r['n']} images")
        print(f"  STR {str(r['strNo']):>2} · Marker {r['marker']}: {'READY' if r['ready'] else 'skip '}  ({why})")
    ready = [r for r in rows if r["ready"]]
    print(f"  -> {len(ready)} marker(s) ready: {', '.join(str(r['marker']) for r in ready) or 'none'}\n")
    return ready

# ================================================================ CLI
def main():
    argv = sys.argv[1:]
    flags = {"--xlsx": "XLSX", "--imgdir": "IMGDIR", "--outdir": "OUTDIR",
             "--sheet": "SHEET", "--outname": "OUTNAME"}
    ints = {"--cropbp": "CROP_BP", "--bpspan": "BP_SPAN"}
    for i, a in enumerate(argv):
        low = a.lower()
        if low in flags and i + 1 < len(argv): CONFIG[flags[low]] = argv[i + 1]
        if low in ints and i + 1 < len(argv): CONFIG[ints[low]] = int(argv[i + 1])
    for k in ("XLSX", "IMGDIR", "OUTDIR"):
        if os.environ.get("CE_" + k): CONFIG[k] = os.environ["CE_" + k]

    value_flags = set(flags) | set(ints)
    nums = [a for i, a in enumerate(argv)
            if a.isdigit() and not (i > 0 and argv[i - 1].lower() in value_flags)]

    if "--list" in argv: report(discover()); return
    if "--auto" in argv:
        ready = report(discover())
        if not ready: print("Nothing to build."); return
        build_combined([r["marker"] for r in ready]); return
    if not nums:
        print("Usage:  python make_str_slide.py --auto | --list | <marker> | --combined <m> <m> ...")
        return
    if any(a.lower() in ("--combined", "--all", "--merge") for a in argv):
        build_combined(nums)
    else:
        for n in nums:
            try: build_deck(n)
            except Exception as e: print(f'"{n}": {e}')

if __name__ == "__main__":
    main()
