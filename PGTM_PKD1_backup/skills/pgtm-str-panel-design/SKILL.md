---
name: pgtm-str-panel-design
description: >
  De-novo design of a universal-tail STR linkage panel from only a gene sequence or name, using UCSC
  Genome Browser, Primer3, BLAST/Primer-BLAST, and IDT OligoAnalyzer. Covers anchoring the gene with
  BLAT, mining flanking STR markers from UCSC repeat tracks, choosing informative loci by motif and
  heterozygosity, planning a four-colour / size-lane grid so markers are told apart by dye
  AND length, designing flanking primers in Primer3, attaching the M13 universal tails, and validating
  by in-silico PCR + BLAST (pseudogene specificity) + IDT hairpin/dimer ΔG. Use whenever the user wants
  to design a fresh STR / microsatellite linkage panel from scratch, find markers near a gene, "design
  a universal panel", pick STR markers for PGT-M, use Primer3/UCSC/BLAST/OligoAnalyzer, or balance
  markers by colour and size for haplotype carrier testing of a monogenic disease (PKD1/PKD2/ADPKD or
  any locus). Trigger even when only one step is named. Its candidate table feeds the companion
  skill pgtm-str-panel-order.
---

# Designing a universal STR linkage panel from scratch

This skill is the **front half** of building a PGT-M marker panel: you start knowing only the gene
(its sequence or name) and finish with a validated set of tailed primers, each marker distinguishable
on a capillary sequencer by its **dye colour** and its **fragment length**. The output feeds the
companion skill **`pgtm-str-panel-order`**, which turns the finalized markers into the vendor order
list (下单表). The two skills share the same universal-tail system and amplicon arithmetic, so keep
them consistent.

Worked example throughout: **PKD1 / ADPKD** on chromosome 16 — chosen because it is hard (six
homologous pseudogenes in the 16p13.1 duplicated region), which is exactly when the validation steps
earn their keep.

## Why "linkage" markers, and why colour + length

PGT-M usually can't rely on typing the mutation directly in a single embryo cell; instead you track
the **haplotype** carrying the mutation using polymorphic STR markers that **flank the gene on both
sides**. If one flank recombines between marker and mutation, the other flank still reports — so you
need informative markers on the 5′ (centromeric) and 3′ (telomeric) sides, as close to the gene as
practical. On a capillary sequencer every fragment is read by two coordinates at once — **which dye
it carries** and **how long it is** — so a panel can run many markers in one tube as long as any two
markers either differ in colour or don't overlap in size. Designing that colour×length grid is the
core of a "universal panel".

## The pipeline (do in order)

```
1. Anchor       BLAT the gene sequence in UCSC -> genomic coordinates + assembly (hg38)
2. Mine STRs    pull candidate repeats in both flanks from UCSC repeat tracks
3. Choose       filter/rank candidates by motif, copy number, purity, population heterozygosity
4. Hazards      pull flank sequence; mark repeat tract; flag Alu/SNP/segmental-dup/pseudogene
5. Grid         plan the 4-colour x size-lane layout -> a target size (and Primer3 range) per marker
6. Primer3      design flanking primers to hit each marker's size lane (anchors, no tails yet)
7. Tails        attach the dye universal tail + pigtail; recompute +tail size; confirm it stays in lane
8. Validate     UCSC in-silico PCR + BLAST/Primer-BLAST (pseudogene!) + IDT hairpin/dimer matrix
9. Hand off     emit the candidate master table -> feed pgtm-str-panel-order for the order list
```

Stages 5 and 7 are the same arithmetic the order skill uses; `references/` and the scripts here make
it concrete. **Surface every judgement call** (which flank windows, which candidates, colour/size
assignment, any locus dropped for a pseudogene hit) to the user before locking it.

## Reference files (read the one for the stage you're in)

- `references/ucsc_workflow.md` — anchoring with BLAT, choosing flank windows, the repeat tracks to
  use (Simple Tandem Repeats / TRF, the 2026 WebSTR + STRchive Tandem-Repeat-Variation tracks),
  Table Browser export, pulling DNA, the SNP / RepeatMasker / segmental-dup tracks, and In-Silico PCR.
  Read for stages 1–4 and 8. Includes current URLs.
- `references/marker_biology.md` — the genetics: flanking both sides, distance vs recombination,
  heterozygosity / PIC, motif choice (why tetra-nucleotides are cleanest on CE), how many markers.
  Read for stages 2–3.
- `references/primer3_settings.md` — building the Primer3 input (SEQUENCE_TARGET on the repeat,
  excluded regions for Alu/SNPs, size/Tm/GC settings, per-lane product-size range). Read for stage 6.
  A copy-paste settings block is in `assets/primer3_settings_template.txt`.
- `references/validation_blast_idt.md` — In-Silico PCR, NCBI BLAST / Primer-BLAST specificity and the
  PKD1 pseudogene problem, and IDT OligoAnalyzer thresholds (hairpin Tm, self/hetero-dimer ΔG, the
  cross-dimer matrix). Read for stage 8.

For the universal-tail definitions, the colour↔dye mapping, the pigtail, and the +tail arithmetic,
see the companion skill `pgtm-str-panel-order` (`references/universal_tails.md`). They are repeated in
`scripts/_grid.py` so the planner here is self-contained.

## Scripts

- `scripts/str_candidate_filter.py` — parses a UCSC Table Browser **simpleRepeat** export, filters and
  ranks candidate STRs by motif length (period), copy number, purity, and (optionally) distance/side
  relative to the gene, and flags mononucleotide and impure repeats. Use in stage 3.
- `scripts/size_lane_planner.py` — given the number of markers, the size window, and the four dye
  channels, lays out a non-overlapping colour×size grid and prints, per marker, the **target +tail
  size** and the **naked PRODUCT_SIZE_RANGE to give Primer3** (it subtracts the right tail length for
  each colour). Use in stage 5; feeds stage 6.

Run each with `--help` for exact arguments. Both also emit JSON so the assignment can carry forward.

---

## Stage 1 — Anchor the gene (UCSC BLAT)

If you only have a sequence, paste it into UCSC **BLAT** (Tools ▸ BLAT) on the right assembly (use
**hg38 / GRCh38** unless told otherwise) to get the gene's chromosome and coordinates. Record the
reference accession (chr16 = `NC_000016.10`). Note immediately whether the gene sits in or beside a
**segmental duplication / pseudogene** region (PKD1 does) — that shapes every later specificity check.
See `references/ucsc_workflow.md`.

## Stage 2 — Mine STR candidates in both flanks

Pick flank **windows** on each side of the gene (start ~the gene's edges and extend outward, commonly
up to ~1–2 Mb — closer is better, see `references/marker_biology.md`). In UCSC **Table Browser**
(`hgTables`), export the **Simple Tandem Repeats** track (group: Repeats, track: *Simple Tandem
Repeats*, table: `simpleRepeat`) for each window as tab-separated output. For informativeness, also
consult the **Tandem Repeat Variation** tracks (WebSTR carries per-population allele-frequency
distributions — a direct read on heterozygosity). Collect a surplus (2–3× the final count), spread
across both flanks and a range of distances.

## Stage 3 — Choose informative loci

Run `scripts/str_candidate_filter.py` on each export. Prefer **tetra-** and tri-nucleotide motifs
(cleaner CE peaks, less stutter), require enough copies for polymorphism, drop mononucleotide runs and
impure repeats, and prefer loci that WebSTR shows as highly heterozygous. Keep candidates balanced
across the two flanks. Details and thresholds: `references/marker_biology.md`.

## Stage 4 — Pull flank sequence and flag hazards

For each kept candidate, get the genomic DNA around the repeat (±~250–300 bp) from UCSC (View ▸ DNA,
or Table Browser sequence output, or the REST API). The repeat tract becomes the Primer3
`SEQUENCE_TARGET` (primers must flank it). Turn on **RepeatMasker** (avoid placing primers in Alu/LINE),
**Common SNPs** (no SNPs under primers, especially the 3′ end), and **Segmental Dups** tracks; record
positions to exclude. See `references/ucsc_workflow.md`.

## Stage 5 — Plan the colour × length grid

Run `scripts/size_lane_planner.py`. It splits the markers across FAM/HEX/NED/PET, lays out
non-overlapping size lanes across the window (default 130–350 bp), and outputs each marker's target
**+tail** size plus the **naked** product-size range to hand Primer3 (subtracting that colour's tail +
pigtail length). Balance each colour across both gene flanks. Concept: `references/marker_biology.md`
and the order skill's `color_size_balancing.md`.

## Stage 6 — Design primers (Primer3)

For each candidate, build a Primer3 input from `assets/primer3_settings_template.txt`: the flank
sequence, `SEQUENCE_TARGET` = repeat, `SEQUENCE_EXCLUDED_REGION` = repeat + Alu + SNP positions,
`PRIMER_PRODUCT_SIZE_RANGE` = the naked range from stage 5, Tm ~60 °C (pair diff ≤ ~1 °C), length
18–24, GC 40–60%, `PRIMER_MAX_POLY_X` ~4. These are **anchors only** — no tails yet. Full guidance:
`references/primer3_settings.md`.

## Stage 7 — Attach universal tails

Put the colour's universal tail (M41→FAM, M20→HEX, MCM→NED, M-Pet→PET) on one primer and the pigtail
(`gttt`) on the other; choose which strand carries the dye so the product stays in its lane and
behaves in the dimer matrix. Recompute `+tail size = naked + tailF + tailR` and confirm it matches the
stage-5 target. Definitions and arithmetic live in the order skill (`references/universal_tails.md`).

## Stage 8 — Validate (in-silico PCR + BLAST + IDT)

For every marker, on the **anchor sequences only** (strip tails first):

1. **UCSC In-Silico PCR** (`hgPcr`): single product, right size, right locus.
2. **NCBI BLAST / Primer-BLAST**: specificity; one intended amplicon; **no pseudogene co-amplification**
   (the make-or-break check for PKD1).
3. **IDT OligoAnalyzer**: hairpin (structure Tm below your annealing temp), self-dimer and hetero-dimer
   ΔG **more positive than −9 kcal/mol**, watching 3′-end complementarity. For the multiplex, run a
   **cross-dimer matrix** over every primer pair and flag the most negative.

Anything that fails (off-target, pseudogene hit, bad dimer, or can't reach its lane) goes back to
Primer3, swaps to another candidate, or is recoloured. Thresholds and the pseudogene rationale:
`references/validation_blast_idt.md`.

## Stage 9 — Hand off to the order skill

Emit the **candidate master table** — per marker: gene side, STR locus + motif, the orderable F/R
(tail+anchor), naked size, dye, tail prefix, +tail size, and validation status (and a flag for any
never-tested marker that still needs a singleplex check). That table is exactly the input the
`pgtm-str-panel-order` skill consumes to produce the company order list.

### Pitfalls specific to de-novo design

- **Pseudogenes silently pass in-silico PCR but fail in the lab.** UCSC In-Silico PCR may show one
  product while BLAST reveals near-identical pseudogene copies. For PKD1 always BLAST the anchors and
  require a site unique to the true gene; In-Silico PCR alone is not enough.
- **Designing primers inside an Alu.** Alu/LINE elements are everywhere in these flanks and cause
  mispriming. Always exclude RepeatMasked regions from primer placement, not just the repeat tract.
- **SNP under the 3′ end.** A common SNP beneath a primer (especially the 3′ end) causes allele
  dropout — the worst failure mode in PGT-M. Check the Common SNPs track before finalizing.
- **Forgetting the tail when sizing.** Primer3's product size is the *naked* size; the CE size is
  naked + both tails. Plan lanes in +tail space, design Primer3 in naked space — the planner script
  does the conversion so you don't mix them.
- **Choosing high-stutter motifs.** Dinucleotide repeats stutter most; tetranucleotides give the
  cleanest, most callable peaks. Prefer tetra/tri unless a di-repeat is the only informative option.
