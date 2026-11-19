#!/usr/bin/env python3
"""Filter and rank STR candidates from a UCSC Table Browser `simpleRepeat` export.

Reads a tab-separated simpleRepeat export (the "all fields from selected table" output),
drops mononucleotide and weak/impure repeats, scores the rest by motif length, copy number,
and purity (and by distance/side if you give the gene position), and prints a ranked table.

Usage:
    python str_candidate_filter.py export.tsv \
        [--gene-pos chr16:2138711-2185899] \
        [--min-copy-di 12 --min-copy-tri 8 --min-copy-tetra 6] \
        [--min-purity 90] [--top 30] [--json out.json]

simpleRepeat columns used (matched by header name; UCSC header may start with '#'):
    chrom chromStart chromEnd period copyNum perMatch perIndel sequence
"""
import argparse
import csv
import json
import sys


def parse_gene_pos(s):
    if not s:
        return None
    chrom, rng = s.split(":")
    a, b = rng.replace(",", "").split("-")
    return chrom, int(a), int(b)


def load(path):
    with open(path, newline="") as fh:
        first = fh.readline()
        header = first.lstrip("#").rstrip("\n").split("\t")
        rdr = csv.DictReader(fh, fieldnames=header, delimiter="\t")
        rows = [dict(r) for r in rdr]
    return rows


def motif_class(period):
    return {1: "mono", 2: "di", 3: "tri", 4: "tetra"}.get(period, f"{period}-mer")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("export", help="UCSC simpleRepeat TSV export")
    ap.add_argument("--gene-pos", help="gene locus chrN:start-end (for distance/side)")
    ap.add_argument("--min-copy-di", type=float, default=12)
    ap.add_argument("--min-copy-tri", type=float, default=8)
    ap.add_argument("--min-copy-tetra", type=float, default=6)
    ap.add_argument("--min-purity", type=float, default=90, help="min perMatch %% (default 90)")
    ap.add_argument("--keep-di", action="store_true", help="keep dinucleotides (default keeps them but down-weights)")
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--json", help="write ranked candidates to this JSON path")
    args = ap.parse_args()

    gene = parse_gene_pos(args.gene_pos)
    rows = load(args.export)
    min_copy = {2: args.min_copy_di, 3: args.min_copy_tri, 4: args.min_copy_tetra}

    cands = []
    for r in rows:
        try:
            period = int(float(r["period"]))
            copynum = float(r["copyNum"])
            start = int(r["chromStart"]); end = int(r["chromEnd"])
            permatch = float(r.get("perMatch", 100))
            perindel = float(r.get("perIndel", 0))
        except (KeyError, ValueError):
            continue
        if period == 1:
            continue  # mononucleotide: too much stutter
        if permatch < args.min_purity:
            continue
        if period in min_copy and copynum < min_copy[period]:
            continue

        rec = {
            "chrom": r["chrom"], "start": start, "end": end,
            "period": period, "motif_class": motif_class(period),
            "motif": r.get("sequence", ""), "copyNum": round(copynum, 1),
            "perMatch": permatch, "perIndel": perindel,
            "span_bp": end - start,
        }
        # signed position relative to the gene. NOTE: the biological 5'/3' (upstream/
        # downstream) and cen/pter labels depend on gene STRAND and chromosome ARM, which a
        # coordinate alone cannot give — so report a neutral lower/higher-coord side and let
        # the user map it (the planner only needs two distinct groups to balance colours).
        if gene:
            _, gstart, gend = gene
            mid = (start + end) // 2
            if mid < gstart:
                rec["side"] = "lower-coord"; rec["distance_bp"] = gstart - mid
            elif mid > gend:
                rec["side"] = "higher-coord"; rec["distance_bp"] = mid - gend
            else:
                rec["side"] = "inside-gene"; rec["distance_bp"] = 0

        # score: motif preference (tetra best) + copy number + purity, minus distance
        motif_pref = {4: 3.0, 3: 2.5, 2: 1.0}.get(period, 0.5)
        score = motif_pref * 2 + min(copynum, 30) * 0.1 + (permatch - 90) * 0.05 - perindel * 0.05
        if gene:
            score -= min(rec["distance_bp"], 2_000_000) / 1_000_000  # ~1 pt per Mb away
        rec["score"] = round(score, 2)
        cands.append(rec)

    cands.sort(key=lambda c: c["score"], reverse=True)
    cands = cands[: args.top]

    if not cands:
        print("No candidates passed the filters. Loosen --min-* thresholds or widen the window.", file=sys.stderr)
        sys.exit(1)

    cols = ["chrom", "start", "end", "motif_class", "motif", "copyNum", "perMatch"]
    has_gene = gene is not None
    if has_gene:
        cols += ["side", "distance_bp"]
    cols += ["score"]
    w = {c: max(len(c), max(len(str(r.get(c, ""))) for r in cands)) for c in cols}
    print("  ".join(c.ljust(w[c]) for c in cols))
    print("  ".join("-" * w[c] for c in cols))
    for r in cands:
        print("  ".join(str(r.get(c, "")).ljust(w[c]) for c in cols))
    print(f"\n{len(cands)} candidates (showing top {args.top}). "
          "Tetra > tri > di; rank is a heuristic — confirm informativeness in WebSTR.")
    if has_gene:
        print("Side = lower/higher genomic coordinate relative to the gene. Map to biological "
              "5'/3' (cen/pter) yourself using the gene strand and chromosome arm.")

    if args.json:
        with open(args.json, "w") as fh:
            json.dump(cands, fh, indent=2)
        print(f"Wrote {args.json}")


if __name__ == "__main__":
    main()
