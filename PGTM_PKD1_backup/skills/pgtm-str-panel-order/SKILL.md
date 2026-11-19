---
name: pgtm-str-panel-order
description: >
  End-to-end workflow for a PGT-M STR linkage marker panel: from a clinically-validated primer
  table, decide retain-vs-redesign per marker, redesign blocked primers in Primer3, assign the
  four CE dye channels with non-overlapping size lanes, apply the M13 universal-tail / pigtail
  system, validate by in-silico PCR + pseudogene/dimer checks, consolidate into a master table
  (总表), and export the clean company oligo order list (下单表). Use whenever the user is
  designing, redesigning, balancing, or ordering an STR / microsatellite linkage panel for PGT-M
  or haplotype carrier testing — PKD1/PKD2/ADPKD work, "12-plex panel", "universal tail", "M13
  tail", "pigtail", "CE color/size balancing", "primer order list", "下单表", "引物订购", "总表",
  or any request to turn a validated primer set into a synthesis order. Trigger even when only one
  stage is mentioned (e.g. "balance my dye channels" or "make the order list"), since the stages
  share one data model and amplicon arithmetic.
---

# PGT-M STR Panel: from validated primers to company order list

This skill encodes a repeatable pipeline for a microsatellite (STR) **linkage** panel used in
PGT-M — i.e. markers flanking a disease gene that let you track the mutant haplotype through
an embryo, rather than typing the mutation directly. The worked example is **PKD1 (ADPKD)**,
a 12-plex panel on chromosome 16; the same procedure applies to PKD2 or any monogenic locus.

The pipeline has seven stages. Do them in order. Each later stage consumes the previous one's
output, and the **amplicon-size arithmetic must stay consistent across all of them** — that
consistency is the single most common place errors hide.

```
0. Inputs        clinically-validated primer table  (+ any "never-used" candidate primers)
1. Triage        pick markers; drop weak/oversized ones; balance flanking sides of the gene
2. Channels      assign FAM/HEX/NED/PET; lay out non-overlapping size lanes (130–350 bp)
3. Redesign      per marker decide RETAIN vs REDESIGN (Primer3); record naked amplicon size
4. Tailing       add M13 universal tail (dye) + pigtail; compute +tail amplicon size
5. Validate      in-silico PCR / BLAST on the ANCHOR only; pseudogene + hairpin/dimer ΔG
6. Master table  consolidate source + landing + orderable columns, colour-coded
7. Order list    export the clean company 下单表 (name, seq, dye, length, Tm, location, amplicon)
```

## How to use this skill

1. Read this file top to bottom once to hold the whole pipeline in mind.
2. Open the reference file for the stage you are in (pointers below). Don't try to keep all
   the detail in head at once — pull each reference when its stage comes up.
3. For the deterministic parts (amplicon arithmetic, name generation, the formatted order-list
   workbook, the QC checks), **run the scripts** rather than doing it by hand. Hand arithmetic
   on 24 oligos is where size errors creep in.
4. Surface every judgement call (which markers to drop, retain vs redesign, any colour change)
   to the user before locking it — these decisions carry clinical history and you cannot infer
   them safely from sequence alone.

## Reference files

- `references/table_schemas.md` — the column model for the **source/validated table**, the
  **master table (总表)**, and the **order list**, with the Chinese↔English header mapping used
  in real worksheets. Read first; everything else refers to these column names.
- `references/universal_tails.md` — the four universal tails, dye mapping, pigtail mechanics,
  and the **amplicon-size arithmetic**. Read for stages 4 and 7.
- `references/color_size_balancing.md` — how to assign the four dye channels and keep
  same-colour fragments from overlapping. Read for stage 2.
- `references/redesign_and_validation.md` — the RETAIN-vs-REDESIGN decision rules, Primer3
  constraints, and the in-silico PCR / pseudogene / dimer validation. Read for stages 3 and 5.

## Scripts

- `scripts/build_order_list.py` — given a small JSON/CSV of finalized per-marker records, it
  computes lengths, generates primer names, derives the dye from the tail, **re-derives and
  cross-checks the +tail amplicon size**, and writes a formatted two-sheet order-list workbook
  (Order List + Tails & Notes). This is the stage-7 deliverable generator.
- `scripts/panel_qc.py` — given the same records, it checks the panel: same-colour fragments
  don't overlap, everything sits in the target size window, pigtail/tail arithmetic is
  internally consistent, and flags markers that need singleplex verification. Run before
  building the order list.

Run `python scripts/build_order_list.py --help` and `python scripts/panel_qc.py --help` for the
exact input schema; `references/table_schemas.md` documents the record fields.

---

## Stage 0 — Inputs

You start from a **clinically-validated primer table**: markers already used (and how many
real cases each was used in), their primer sequences (tail + gene-specific anchor), genomic
coordinates, Tm, naked and +tail lengths, and remarks. There may also be **candidate / never-used**
primers you are considering adding. Capture the "Used in N cases" / "Never used" status for
every marker — it is the primary input to the retain-vs-redesign decision and to which markers
need a fresh singleplex check.

Confirm the genome build (e.g. hg38) and the reference accession (chr16 = `NC_000016.10`) up
front, because every coordinate and every in-silico PCR check depends on it.

## Stage 1 — Marker triage

Goal: a balanced set (typically ~10–14 markers) that brackets the gene on **both** sides so a
crossover on either flank is still informative.

- Keep markers with strong, clean amplification and a good heterozygosity / repeat structure.
- **Drop** markers that amplify weakly, sit too far away, or force an oversized amplicon that
  won't fit the size window (in PKD1, `Chr16:2290` very weak and `Chr16:1876` very weak + 457 bp
  were dropped). Record *why* each dropped marker was dropped — that rationale is reused later.
- Balance the count on the 5′ upstream (centromeric) and 3′ downstream (telomeric/pter) sides.

## Stage 2 — Channel & size-lane assignment

Read `references/color_size_balancing.md`. In short: four dye channels (FAM/HEX/NED/PET), and
within any one channel the expected fragment sizes must not overlap — aim for even spacing
(~20 bp) across roughly **130–350 bp**, with at most one long-fragment backup beyond that.
This assignment sets a **size target** for each marker, which constrains stage 3.

## Stage 3 — Retain vs redesign

Read `references/redesign_and_validation.md`. For each marker decide:

- **RETAIN** the original clinically-validated anchor when it has real case history and a
  redesign is *blocked* (flanking Alu/repeat leaves no room) or *not worthwhile* (saves only a
  few bp, or comes out longer). A retained primer may still switch its **5′ tail** if the marker
  needs a different colour — the anchor (the part after the tail) is unchanged, so the expected
  product equals the original naked size.
- **REDESIGN** in Primer3 when you can meaningfully shorten the amplicon, hit the size lane from
  stage 2, or the marker was never used clinically. Redesign changes the anchor, hence the
  coordinates and the naked size.

Record, per marker: plan (RETAIN/REDESIGN), the orderable F and R sequences (tail+anchor), and
the **naked** amplicon size (anchor-to-anchor product, no tails).

## Stage 4 — Universal tailing

Read `references/universal_tails.md`. Put the dye-carrying universal tail on one strand and the
**pigtail** (`gttt`) on the other. Then:

```
+tail amplicon size = naked size + len(tail on F) + len(tail on R)
```

This is the size you will actually see on the CE instrument and the number that must match the
order list. Compute it with the script, not by hand.

## Stage 5 — Validation

Read `references/redesign_and_validation.md`. Run in-silico PCR / BLAST using **only the anchor**
(strip the 5′ tail first — the tail does not prime genomic DNA in early cycles). Confirm a single
product, confirm it does not co-amplify the gene's pseudogene region (critical for PKD1, which
has six pseudogenes), and check hairpin / self-dimer / cross-dimer ΔG. Flag every never-used or
recoloured marker for a **singleplex PCR** before it enters the multiplex.

## Stage 6 — Master table (总表)

Read `references/table_schemas.md`. Consolidate into one wide sheet: the source/validated columns,
the landing-result columns, and the final **orderable** column, colour-coded (e.g. green = newly
redesigned primer, blue = retained original). This is the audit trail; keep the rationale text
("保留原引物…", "重设计达标…") with each marker.

## Stage 7 — Company order list (下单表)

Run `panel_qc.py`, then `build_order_list.py`. The order list keeps only what a synthesis vendor
and the lab record need: **primer name, sequence (5′→3′, tail+anchor), 5′ dye, full oligo length,
anchor Tm, location (reference accession + STR locus), expected amplicon size (incl. tails)**.
Two oligos per marker. Put the universal-tail definitions and the operational notes on a second
sheet so the vendor knows what the tails are and the lab knows which markers still need singleplex
verification.

### Pitfalls that have actually bitten this pipeline

- **Stale coordinates after redesign.** Once you redesign an anchor, the source table's
  Start/End no longer describe the orderable primer. Don't carry old per-primer coordinates into
  the order list; give the (stable) STR-locus region + reference accession, and tell the user to
  reconfirm exact binding coordinates by in-silico PCR on the new anchor.
- **Tail-length drift in the amplicon math.** The four tails are different lengths (18/18/21/20)
  and the pigtail is usually 4 bp but occasionally trimmed (a 2 bp `gt` was used once). If the
  stated +tail size doesn't equal naked + both tail lengths, something is wrong — `panel_qc.py`
  catches this. Trust the arithmetic, then reconcile with the worksheet.
- **Counting tail Tm.** The reported Tm is the **anchor** Tm (priming Tm), not the full
  tailed-oligo Tm. Label it as such so it isn't misread.
- **Colour flips on redesign.** When a redesigned marker also changes colour, the dye can move
  from the R strand to the F strand. Derive "which strand is fluorescent" from the orderable
  sequence prefix (a long M13-type tail vs a short pigtail), not from the original role column.
