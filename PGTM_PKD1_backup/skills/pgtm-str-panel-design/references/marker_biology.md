# Choosing markers: the genetics behind the panel

The goal is a set of polymorphic markers that lets you follow the mutation-carrying chromosome
through a family and into an embryo. Three properties decide whether a candidate STR is worth a slot.

## 1. Position — flank the gene on both sides, and stay close

- **Both flanks.** Put markers on the 5′ (centromeric) and 3′ (telomeric/pter) side of the gene. A
  single recombination between a marker and the mutation flips that marker's phase; having informative
  markers on both flanks means a crossover on one side is caught by the other.
- **Close linkage.** The chance of recombination between marker and mutation rises with genetic
  distance (~1 cM ≈ 1 Mb as a rough human average). Prefer markers within ~1 Mb of the gene; accept
  more distant ones only to fill informativeness gaps. A practical panel brackets the gene with
  several markers per side at increasing distances, so at least one stays linked.
- **Spread, don't cluster.** Markers very close together tend to co-segregate and add little
  independent information; space them out along each flank.

## 2. Informativeness — heterozygosity / PIC

A marker only helps when the relevant parent is **heterozygous** at it (so the two chromosomes carry
different alleles you can tell apart). Prefer high-heterozygosity loci:

- Use the UCSC **WebSTR** allele-frequency distributions (per population) to estimate heterozygosity /
  polymorphism information content (PIC). Many alleles at moderate frequencies = informative.
- Aim for expected heterozygosity ≳ 0.7 where possible. With several markers per flank, the chance
  that at least one is informative in a given couple becomes high even if any single one isn't.

## 3. Motif and quality — callability on a capillary sequencer

- **Motif length (period).** Tetranucleotide (period 4) repeats give the cleanest CE peaks with the
  least **stutter** (the −1-repeat shadow peaks PCR slippage produces). Trinucleotides are good.
  Dinucleotides are the most polymorphic but stutter most and are harder to call; use them only when
  they're the only informative option. **Avoid mononucleotide** runs (period 1) — heavy stutter.
- **Copy number.** More repeat units → more length variation → more alleles. Rough minimums for a
  useful marker: di ≥ ~12 copies, tri ≥ ~8, tetra ≥ ~6 (tune to what WebSTR shows as polymorphic).
- **Purity.** Prefer pure repeats (high `perMatch`, low `perIndel` in the simpleRepeat track);
  interrupted repeats genotype less cleanly.
- **Clean flanks.** The ~150–250 bp around the repeat must contain a unique, repeat-free, SNP-free
  primer site on each side (checked in stage 4). A perfect repeat in an Alu sea is useless.

## How many markers

A common target is ~10–14 markers, balanced across the two flanks and across the four dye colours
(~3 per colour for a 12-plex). Collect 2–3× that many candidates up front, because many will be lost
to pseudogene homology, Alu flanks, SNPs under primers, dimers, or simply not fitting their size lane.
`scripts/str_candidate_filter.py` helps you rank the surplus; the size-lane planner decides how many
slots you actually have per colour.
