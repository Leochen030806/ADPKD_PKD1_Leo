#!/usr/bin/env python3
"""Plan the colour x length grid for a universal-tail STR panel.

Splits markers across the four dye channels (balancing gene flanks when 'side' is given),
lays out non-overlapping +tail size lanes across the window, and prints for each marker its
target +tail size and the NAKED PRODUCT_SIZE_RANGE to hand Primer3 (the colour's tail+pigtail
length is subtracted for you).

Usage (count mode):
    python size_lane_planner.py -n 12 [--window 130 350] [--band 15]

Usage (marker mode — lets you balance flanks and pin colours):
    python size_lane_planner.py markers.json [--window 130 350] [--band 15] [--json out.json]

markers.json: list of objects, each optionally {"name","side","dye"} ('dye' pins a colour).
"""
import argparse
import json
import sys
from collections import defaultdict

from _grid import DYES, TAILS, PIGTAIL_LEN, assign_colours, lane_targets, tail_pair_len


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("markers", nargs="?", help="markers .json (omit if using -n)")
    ap.add_argument("-n", type=int, help="number of markers (count mode)")
    ap.add_argument("--window", nargs=2, type=int, default=[130, 350], metavar=("LO", "HI"))
    ap.add_argument("--band", type=int, default=15, help="+/- bp band for the naked Primer3 range (default 15)")
    ap.add_argument("--json", help="write the plan to this JSON path")
    args = ap.parse_args()

    if args.markers:
        with open(args.markers) as fh:
            markers = json.load(fh)
        for i, m in enumerate(markers):
            m.setdefault("name", f"M{i+1}")
    elif args.n:
        markers = [{"name": f"M{i+1}"} for i in range(args.n)]
    else:
        ap.error("provide either a markers.json or -n N")

    assign_colours(markers)

    lo, hi = args.window
    by_dye = defaultdict(list)
    for m in markers:
        by_dye[m["dye"]].append(m)

    plan = []
    for dye in DYES:
        group = by_dye.get(dye, [])
        targets = lane_targets(len(group), lo, hi)
        tpair = tail_pair_len(dye)
        for m, t_plus in zip(group, targets):
            naked = t_plus - tpair
            rec = {
                "name": m["name"], "side": m.get("side", ""), "dye": dye,
                "tail_prefix": TAILS[dye][0],
                "target_plus_tail": t_plus,
                "target_naked": naked,
                "primer3_product_size_range": f"{naked - args.band}-{naked + args.band}",
            }
            plan.append(rec)

    plan.sort(key=lambda r: (DYES.index(r["dye"]), r["target_plus_tail"]))

    cols = ["name", "side", "dye", "tail_prefix", "target_plus_tail", "target_naked", "primer3_product_size_range"]
    hdr = ["Marker", "Side", "Dye", "Tail", "+tail", "naked", "Primer3 SIZE_RANGE (naked)"]
    w = [max(len(h), max(len(str(r[c])) for r in plan)) for h, c in zip(hdr, cols)]
    print("  ".join(h.ljust(w[i]) for i, h in enumerate(hdr)))
    print("  ".join("-" * w[i] for i in range(len(hdr))))
    for r in plan:
        print("  ".join(str(r[c]).ljust(w[i]) for i, c in enumerate(cols)))

    # warn on any naked target that is implausibly small
    floor = 90  # repeat + 2 primers + minimal flank
    small = [r["name"] for r in plan if r["target_naked"] < floor]
    if small:
        print(f"\n! naked target < {floor} bp for: {', '.join(small)} — widen the window low end "
              "or move these to a larger size slot.", file=sys.stderr)

    print(f"\nWindow {lo}-{hi} bp (+tail space). Tail+pigtail subtracted per colour "
          f"(FAM/HEX {TAILS['FAM'][2]+PIGTAIL_LEN}, NED {TAILS['NED'][2]+PIGTAIL_LEN}, "
          f"PET {TAILS['PET'][2]+PIGTAIL_LEN}). Give the naked range to Primer3 (stage 6).")

    if args.json:
        with open(args.json, "w") as fh:
            json.dump(plan, fh, indent=2)
        print(f"Wrote {args.json}")


if __name__ == "__main__":
    main()
