# UCSC Genome Browser workflow (anchoring, mining, hazards, in-silico PCR)

UCSC Genome Browser: `https://genome.ucsc.edu`. Use the **hg38 / GRCh38** assembly unless told
otherwise. Tools live under the top "Tools" menu.

## 1. Anchor the gene with BLAT

- Tools ▸ **BLAT** (`/cgi-bin/hgBlat`). Paste the gene sequence; pick Human / hg38. The hit gives the
  chromosome, strand, and coordinates. Click into the browser at that location.
- Note the reference accession for the chromosome (chr16 = `NC_000016.10`) — every later coordinate
  and in-silico check is in this frame.
- Immediately check for a **Segmental Dups** track signal and any pseudogenes near the gene (PKD1: the
  16p13.1 duplicated region with six pseudogenes). This decides how hard stage-8 specificity will be.

## 2. Choose flank windows

For linkage you want markers on **both** sides of the gene. Start each window at the gene's edge and
extend outward; closer markers recombine away from the mutation less often (see `marker_biology.md`).
A practical first pass is up to ~1–2 Mb each side, then tighten. Record the two window intervals.

## 3. Mine STR candidates (repeat tracks)

Primary track — **Simple Tandem Repeats** (Tandem Repeats Finder / TRF):
- Group: *Repeats*; Track: *Simple Tandem Repeats*; Table: `simpleRepeat`.
- Export via **Table Browser** (`/cgi-bin/hgTables`): set the assembly (hg38), group/track/table as
  above, set "region" to your flank window (`chr16:START-END`), output format "all fields from selected
  table", and get the tab-separated file. Useful columns: `chrom, chromStart, chromEnd, period`
  (motif length), `copyNum` (number of copies), `consensusSize`, `perMatch`/`perIndel` (purity),
  `sequence` (the consensus motif). Schema page: append `&hgta_doSchema=describe+table+schema`.
- Feed the export to `scripts/str_candidate_filter.py`.

Informativeness — **Tandem Repeat Variation** tracks (added 2026 on hg38):
- **WebSTR** — ~1.7M STR loci from the EnsembleTR panel with **per-population allele-frequency
  distributions** (1000 Genomes, five continental populations). This is a direct read on
  heterozygosity: prefer loci with many alleles at appreciable frequency.
- **STRchive** — disease-associated repeat-expansion loci; use it to *recognise/avoid* pathogenic
  expansion loci, not as panel markers.
- (TRExplorer V2 is a large combined catalogue if you need more candidates.)

## 4. Pull flank DNA and flag hazards

- Get genomic DNA around each candidate repeat (±~250–300 bp): browser **View ▸ DNA**, or Table
  Browser with output "sequence", or the **REST API** (`/cgi-bin/hubApi` / the documented `getData`
  endpoints) for scripted retrieval. Keep the repeat-tract coordinates — they become Primer3's
  `SEQUENCE_TARGET`.
- Turn on and read these tracks over the flanks:
  - **RepeatMasker** — Alu/LINE/etc. Exclude primer placement inside masked regions (mispriming).
  - **Common SNPs** (dbSNP common subset) — exclude SNPs under primers, *especially the 3′ end*
    (allele dropout risk).
  - **Segmental Dups** — confirm primer sites are outside duplicated/pseudogene blocks.

## 5. In-Silico PCR (validation, stage 8)

- Tools ▸ **In-Silico PCR** (`/cgi-bin/hgPcr`). Paste the **anchor** forward/reverse (no tails), pick
  hg38 genome target. It returns the predicted product(s), size, and location, and links into the
  browser. Expect exactly one product at the intended locus and size.
- In-Silico PCR uses BLAT-style matching and can **miss** highly similar paralogues that still
  co-amplify in the lab — so it is necessary but not sufficient. Always also BLAST the anchors
  (`validation_blast_idt.md`).

## Handy URL patterns

- Browser at a locus: `https://genome.ucsc.edu/cgi-bin/hgTracks?db=hg38&position=chr16:2,000,000-2,200,000`
- Table Browser: `https://genome.ucsc.edu/cgi-bin/hgTables?db=hg38&hgta_group=rep&hgta_track=simpleRepeat&hgta_table=simpleRepeat`
- In-Silico PCR: `https://genome.ucsc.edu/cgi-bin/hgPcr` (db=hg38)
- BLAT: `https://genome.ucsc.edu/cgi-bin/hgBlat`

(The browser rate-limits automated hits; for bulk work use the REST API or downloaded `simpleRepeat.txt.gz`.)
