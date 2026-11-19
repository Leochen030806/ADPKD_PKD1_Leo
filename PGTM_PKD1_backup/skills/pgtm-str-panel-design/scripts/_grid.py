"""Shared constants and helpers for the panel-design scripts.

Self-contained copy of the universal-tail system so this skill's planner works without the
companion pgtm-str-panel-order skill loaded. Keep these in sync with that skill's
references/universal_tails.md.
"""

# dye channel -> (tail prefix, tail sequence 5'->3', tail length nt)
TAILS = {
    "FAM": ("M41", "GGTTTTCCCAGTCACGAC", 18),
    "HEX": ("M20", "GTAAAACGACGGCCAGTG", 18),
    "NED": ("MCM", "CATGGTCATAGCTGTTTCCTG", 21),
    "PET": ("M-Pet", "CCGCTAATTCAACCCATTGC", 20),
}
DYES = ["FAM", "HEX", "NED", "PET"]
PIGTAIL = "gttt"
PIGTAIL_LEN = 4


def tail_pair_len(dye):
    """Total bp added to a naked amplicon for this colour: dye tail + pigtail."""
    return TAILS[dye][2] + PIGTAIL_LEN


def naked_to_plus_tail(naked, dye):
    return naked + tail_pair_len(dye)


def plus_tail_to_naked(plus_tail, dye):
    return plus_tail - tail_pair_len(dye)


def assign_colours(markers):
    """Spread markers across the four dyes, balancing gene flank ('side') when present.

    `markers` is a list of dicts; each may carry 'side' ('5'/'3'/'cen'/'pter'/free text).
    Returns the same list with a 'dye' key added (existing 'dye' values are respected).
    Round-robins within each side so each colour gets a mix of both flanks.
    """
    by_side = {}
    for m in markers:
        by_side.setdefault(m.get("side", ""), []).append(m)
    # round-robin dye assignment, cycling per side so colours stay flank-balanced
    counter = 0
    for side, group in by_side.items():
        for m in group:
            if not m.get("dye"):
                m["dye"] = DYES[counter % len(DYES)]
                counter += 1
    return markers


def lane_targets(n, lo, hi):
    """Evenly spaced target sizes for n same-colour fragments across [lo, hi]."""
    if n <= 0:
        return []
    if n == 1:
        return [round((lo + hi) / 2)]
    step = (hi - lo) / n
    return [round(lo + (i + 0.5) * step) for i in range(n)]
