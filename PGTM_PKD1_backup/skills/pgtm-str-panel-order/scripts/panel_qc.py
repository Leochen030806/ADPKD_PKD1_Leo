#!/usr/bin/env python3
"""Panel QC for a PGT-M STR dye panel.

Checks, from finalized per-marker records:
  - amplicon arithmetic is internally consistent (naked + both tails == +tail size)
  - no two same-colour fragments overlap (gap below threshold)
  - all fragments sit in the target size window
  - lists markers that still need singleplex verification

Usage:
    python panel_qc.py records.json [--window 130 350] [--min-gap 8]

Input schema: see references/table_schemas.md ("Record schema for the scripts").
"""
import argparse
from collections import defaultdict
from _common import load_records, TAILS


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("records", help="path to records .json or .csv")
    ap.add_argument("--window", nargs=2, type=int, default=[130, 350], metavar=("LO", "HI"),
                    help="target +tail size window (default 130 350)")
    ap.add_argument("--min-gap", type=int, default=8,
                    help="minimum bp gap warned-on between same-colour fragments (default 8)")
    args = ap.parse_args()

    recs = load_records(args.records)
    lo, hi = args.window
    problems = 0

    print(f"Panel QC — {len(recs)} markers, {2*len(recs)} oligos\n")

    # arithmetic (normalize already raised on hard mismatches; here we just report)
    print("Amplicon arithmetic:")
    for r in recs:
        print(f"  {r['marker']:<14} {r['dye']:<4} naked {r['naked']:>4}  + tails "
              f"({r['f_tail_len']}+{r['r_tail_len']})  = {r['amplicon_with_tails']:>4} bp")
    print()

    # window
    print(f"Size window {lo}-{hi} bp:")
    for r in recs:
        amp = r["amplicon_with_tails"]
        if amp < lo or amp > hi:
            tag = "backup/long" if amp > hi else "below window"
            print(f"  ! {r['marker']} {r['dye']} at {amp} bp is outside the window ({tag})")
            problems += 1
    if problems == 0:
        print("  all fragments inside window")
    print()

    # same-colour overlap
    print(f"Same-colour spacing (warn if gap < {args.min_gap} bp):")
    by_dye = defaultdict(list)
    for r in recs:
        by_dye[r["dye"]].append((r["amplicon_with_tails"], r["marker"]))
    for dye in [TAILS[p][0] for p in TAILS]:
        lst = sorted(by_dye.get(dye, []))
        if not lst:
            continue
        sizes = ", ".join(f"{s}({m.split(':')[-1]})" for s, m in lst)
        print(f"  {dye}: {sizes}")
        for (s1, m1), (s2, m2) in zip(lst, lst[1:]):
            gap = s2 - s1
            if gap < args.min_gap:
                print(f"    ! tight gap {gap} bp between {m1} ({s1}) and {m2} ({s2})")
                problems += 1
    print()

    # singleplex flags
    flagged = [r["marker"] for r in recs if r["needs_singleplex"]]
    if flagged:
        print("Singleplex verification required (plan marked '*'):")
        print("  " + ", ".join(flagged))
        print()

    print("=" * 48)
    if problems:
        print(f"QC finished with {problems} item(s) to review above.")
    else:
        print("QC passed: arithmetic consistent, no same-colour overlaps, all in window.")


if __name__ == "__main__":
    main()
