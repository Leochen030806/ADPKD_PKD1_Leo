"""Shared helpers for the PGT-M STR panel order-list scripts.

Loads finalized per-marker records (JSON or CSV), validates them, derives dye / pigtail
strand / oligo lengths, and cross-checks the amplicon arithmetic. See
references/table_schemas.md and references/universal_tails.md for the data model.
"""
import csv
import json

# tail prefix -> (dye, tail sequence 5'->3', tail length)
TAILS = {
    "M41":   ("FAM", "GGTTTTCCCAGTCACGAC", 18),
    "M20":   ("HEX", "GTAAAACGACGGCCAGTG", 18),
    "MCM":   ("NED", "CATGGTCATAGCTGTTTCCTG", 21),
    "M-Pet": ("PET", "CCGCTAATTCAACCCATTGC", 20),
}
DEFAULT_REF = "NC_000016.10"  # hg38 chromosome 16

# light dye tints for the workbook
DYE_FILL = {"FAM": "DCE6F7", "HEX": "DDEFD8", "NED": "FFF2CC", "PET": "F8D7DA", "": "FFFFFF"}


def _tail_len_on_strand(seq):
    """Infer the 5' addition length on a primer from its sequence prefix.

    A fluorescent primer starts with one of the four universal tails (matched case-
    insensitively); a pigtail primer starts with a short lowercase g/t run (gttt or gt).
    """
    up = seq.upper()
    for _pfx, (_dye, tseq, tlen) in TAILS.items():
        if up.startswith(tseq):
            return tlen, "fluor"
    # pigtail convention: lowercase 5' g/t run (gttt, occasionally trimmed to gt);
    # the gene-specific anchor that follows is uppercase. Count only the lowercase run.
    i = 0
    while i < len(seq) and seq[i] in "gt" and i < 5:
        i += 1
    if 1 <= i <= 4:
        return i, "pigtail"
    return 0, "unknown"


def normalize(rec):
    """Validate one record and return an enriched dict. Raises ValueError on inconsistency."""
    r = dict(rec)
    for k in ("marker", "fluor_strand", "tail_prefix", "f_seq", "r_seq"):
        if not r.get(k):
            raise ValueError(f"record {rec.get('marker','?')}: missing required field '{k}'")
    pfx = r["tail_prefix"]
    if pfx not in TAILS:
        raise ValueError(f"{r['marker']}: unknown tail_prefix '{pfx}' (expected one of {list(TAILS)})")
    if r["fluor_strand"] not in ("F", "R"):
        raise ValueError(f"{r['marker']}: fluor_strand must be 'F' or 'R'")

    r["dye"] = TAILS[pfx][0]
    r["reference"] = r.get("reference") or DEFAULT_REF
    r["f_len"] = len(r["f_seq"])
    r["r_len"] = len(r["r_seq"])

    f_tail, f_kind = _tail_len_on_strand(r["f_seq"])
    r_tail, r_kind = _tail_len_on_strand(r["r_seq"])
    r["f_tail_len"], r["r_tail_len"] = f_tail, r_tail

    # the fluorescent strand should carry the dye tail; the other carries the pigtail
    fluor_kind = f_kind if r["fluor_strand"] == "F" else r_kind
    if fluor_kind != "fluor":
        raise ValueError(
            f"{r['marker']}: fluor_strand={r['fluor_strand']} but that strand does not start "
            f"with a universal tail (detected '{fluor_kind}'). Check the sequence/tail.")

    naked = r.get("naked")
    amp = r.get("amplicon_with_tails")
    if naked is None and amp is None:
        raise ValueError(f"{r['marker']}: provide at least one of 'naked' or 'amplicon_with_tails'")
    if naked is not None:
        computed_amp = naked + f_tail + r_tail
        if amp is not None and amp != computed_amp:
            raise ValueError(
                f"{r['marker']}: amplicon arithmetic mismatch — naked({naked}) + tails"
                f"({f_tail}+{r_tail}) = {computed_amp}, but amplicon_with_tails={amp}. "
                "One of these is wrong; reconcile before ordering.")
        r["amplicon_with_tails"] = computed_amp
        r["naked"] = naked
    else:
        r["amplicon_with_tails"] = amp
        r["naked"] = amp - f_tail - r_tail

    r["needs_singleplex"] = str(r.get("plan", "")).strip().endswith("*")
    return r


def primer_names(r):
    """Return (f_name, r_name) following {tail}-{marker}-{F1/R1} / Pig-{marker}-{F1/R1}."""
    pfx, marker, fl = r["tail_prefix"], r["marker"], r["fluor_strand"]
    f = f"{pfx}-{marker}-F1" if fl == "F" else f"Pig-{marker}-F1"
    rr = f"{pfx}-{marker}-R1" if fl == "R" else f"Pig-{marker}-R1"
    return f, rr


def load_records(path):
    """Load records from a .json (list of objects) or .csv file."""
    if path.lower().endswith(".json"):
        with open(path) as fh:
            data = json.load(fh)
        if isinstance(data, dict) and "records" in data:
            data = data["records"]
    else:
        with open(path, newline="") as fh:
            data = list(csv.DictReader(fh))
        num = {"no", "f_tm", "r_tm", "naked", "amplicon_with_tails"}
        for d in data:
            for k in list(d):
                if k in num and d[k] not in (None, ""):
                    d[k] = float(d[k]) if k in ("f_tm", "r_tm") else int(float(d[k]))
                elif d[k] == "":
                    d[k] = None
    return [normalize(r) for r in data]
