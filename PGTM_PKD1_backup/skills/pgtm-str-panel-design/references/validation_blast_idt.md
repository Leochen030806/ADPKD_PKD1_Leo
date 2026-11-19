# Validation: in-silico PCR, BLAST / Primer-BLAST, IDT OligoAnalyzer

Run all of these on the **anchor sequences only** — strip the universal tail / pigtail first. The
tail is not genomic and does not prime template in the early cycles, so including it corrupts every
specificity and thermodynamic check.

## 1. UCSC In-Silico PCR (locus + size)

Tools ▸ **In-Silico PCR** (`https://genome.ucsc.edu/cgi-bin/hgPcr`, target = hg38 genome). Paste the
anchor forward and reverse. Accept a marker only when it returns **exactly one product, at the
intended locus, at the intended size**. Multiple products, a product on the wrong chromosome, or a
product in a pseudogene block → reject and redesign.

In-Silico PCR uses BLAT-style alignment and can **miss** highly similar paralogues that still
co-amplify in the lab. It is necessary but not sufficient — always also BLAST the anchors.

## 2. NCBI BLAST / Primer-BLAST (uniqueness + pseudogene specificity)

- **Primer-BLAST** (`https://www.ncbi.nlm.nih.gov/tools/primer-blast/`) takes the primer pair, runs
  Primer3 + BLAST against a chosen database (use the human genome / RefSeq), and reports predicted
  amplicons genome-wide, including unintended ones. This is the most direct check.
- Or BLAST each anchor (`blastn`, short-query settings) against the genome and require the only strong,
  full-length, 3′-anchored hit to be the intended site.

### The PKD1 pseudogene problem (why this stage is non-negotiable here)

PKD1 lies in the 16p13.1 segmentally-duplicated region and has **six pseudogenes** that are ~97-98%
identical to its 5′ two-thirds. A primer that looks fine in Primer3 (which only sees the short
template you pasted) can match a pseudogene copy elsewhere and co-amplify it, scrambling the
genotype. Require every anchor to sit on sequence that is **unique to the true gene / its flanks**,
not shared with a pseudogene. Markers and primers in the duplicated proximal region are the riskiest;
distal/3′ flanks are usually cleaner. (PKD2 on chr4 lacks this pseudogene burden, but still BLAST.)

## 3. IDT OligoAnalyzer (structure & dimers)

OligoAnalyzer (`https://www.idtdna.com/calc/analyzer`). For each anchor and each pair, check:

| Check | What to look at | Reject when |
|---|---|---|
| **Hairpin** | predicted hairpin structure Tm | hairpin Tm at/above the PCR annealing temp (~58-60 °C), especially if it sequesters the 3′ end |
| **Self-dimer** | most stable self-dimer ΔG | ΔG more negative than ~ **−9 kcal/mol**, or any 3′-end self-dimer |
| **Hetero-dimer** | F×R (and, for multiplex, all-vs-all anchor pairs) ΔG | ΔG more negative than ~ **−9 kcal/mol**, or 3′-end complementarity |

3′-end involvement matters more than raw ΔG: a weak dimer that ends in a primable 3′ overhang is
worse than a stronger internal one. Use **annealing-temp and salt settings that match your protocol**
(default IDT conditions are a reasonable start).

### Cross-dimer matrix for the multiplex

A panel multiplexes many primers in one tube, so check **every primer against every other** (anchors),
not just within a pair. Build the all-vs-all ΔG matrix, sort the most-negative pairs, and either
redesign an offender or note it so the lab knows which interaction to suspect if a spurious peak
appears. (`primer3.calc_heterodimer` reproduces these ΔG values locally if you want to pre-screen
before IDT — same nearest-neighbour thermodynamics.)

## What "pass" means before hand-off

A marker is ready for the order skill when: one specific In-Silico PCR product at the right size, a
unique BLAST/Primer-BLAST result with no pseudogene co-amplification, and no disqualifying hairpin or
dimer. Anything marginal is recorded as such — and because every de-novo marker is "never tested", it
must still clear a **singleplex PCR** before it joins the multiplex.
