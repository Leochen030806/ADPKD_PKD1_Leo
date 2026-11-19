# Primer3 settings for STR flanking primers

Tool: **Primer3** — Primer3web (`https://primer3.ut.ee`) or Primer3Plus
(`https://www.primer3plus.com`). You design **anchors only** here (gene-specific sequence, no universal
tail). The tail is added in stage 7 and only affects size, not the priming Tm.

## Input construction

1. **Template** = the ±250–300 bp flank sequence around one candidate repeat (from UCSC).
2. **Target the repeat** so primers are forced to flank it, not sit inside it:
   `SEQUENCE_TARGET=<start>,<length>` where start/length are the repeat tract's offset within the
   template (0-based within the pasted sequence) and its length. Primer3 then puts one primer on each
   side of the target.
3. **Exclude hazards** found in stage 4:
   `SEQUENCE_EXCLUDED_REGION=<start>,<len> <start>,<len> ...` for the repeat tract itself plus any
   Alu/RepeatMasked stretches and any common-SNP positions in the flanks (keep primers off them,
   especially the 3′ end).

## Recommended settings (starting point)

```
PRIMER_TASK=generic
PRIMER_PICK_LEFT_PRIMER=1
PRIMER_PICK_RIGHT_PRIMER=1
PRIMER_OPT_SIZE=20
PRIMER_MIN_SIZE=18
PRIMER_MAX_SIZE=24
PRIMER_OPT_TM=60.0
PRIMER_MIN_TM=58.0
PRIMER_MAX_TM=62.0
PRIMER_PAIR_MAX_DIFF_TM=1.5
PRIMER_MIN_GC=40.0
PRIMER_MAX_GC=60.0
PRIMER_MAX_POLY_X=4
PRIMER_GC_CLAMP=1
PRIMER_MAX_SELF_ANY_TH=45
PRIMER_MAX_SELF_END_TH=35
PRIMER_PAIR_MAX_COMPL_ANY_TH=45
PRIMER_PAIR_MAX_COMPL_END_TH=35
PRIMER_PRODUCT_SIZE_RANGE=<NAKED_LO>-<NAKED_HI>
```

- **`PRIMER_PRODUCT_SIZE_RANGE` is the NAKED range** for this marker's colour lane — take it straight
  from `scripts/size_lane_planner.py` (it has already subtracted the colour's tail + pigtail length
  from the target +tail size). Never put the +tail target here, or your CE fragments will land a tail
  length too long.
- Keep the repeat comfortably inside the amplicon with real flank on both sides; don't let a primer
  end abut the repeat (slippage zone).
- The `_TH` thermodynamic-alignment limits keep Primer3 from picking self/cross-complementary primers;
  IDT OligoAnalyzer in stage 8 is the final dimer check, this is the first-pass filter.

## Iterating to hit a size lane

If Primer3 can't return a pair in the requested naked range (common when one flank is all Alu),
options in order: widen the range slightly; move the candidate to a different size slot of the same
colour; recolour it to a channel with room; or drop it for a spare candidate. Record which you did —
the order skill's master table wants that rationale.

A ready-to-edit block is in `assets/primer3_settings_template.txt`.
