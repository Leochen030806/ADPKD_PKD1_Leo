# Universal M13-type tails, pigtail, and amplicon arithmetic

## Why universal tails

Labelling every locus-specific primer with a fluorophore is expensive and inflexible. Instead,
each fluorescent primer carries a **universal 5′ tail**; the dye is on a single universal primer
that anneals to that tail after the first couple of cycles (the three-primer / M13 system). To
recolour a marker you just swap which tail it carries — the gene-specific anchor never changes.

## The four tails (one per dye channel)

| Dye (channel) | Tail prefix | Tail sequence (5′→3′) | Tail length (nt) |
|---|---|---|---|
| FAM (blue) | M41 | `GGTTTTCCCAGTCACGAC` | 18 |
| HEX (green) | M20 | `GTAAAACGACGGCCAGTG` | 18 |
| NED (yellow) | MCM | `CATGGTCATAGCTGTTTCCTG` | 21 |
| PET (red) | M-Pet | `CCGCTAATTCAACCCATTGC` | 20 |

The dye is fully determined by the tail prefix; never assign a dye independently of the tail.

## Pigtail on the opposite strand

The **non-fluorescent** primer of the pair gets a short **pigtail** (`gttt`, 4 bp) on its 5′ end.
Its job is to force uniform +A non-templated adenylation so the dye-labelled strand gives a single
clean peak instead of a split (−A / +A) doublet. It is **not** dye-labelled.

- Default pigtail = `gttt` (4 bp).
- It can occasionally be trimmed (a 2 bp `gt` has been used on one PKD1 marker to hit an exact
  target size). If you see a non-`gttt` pigtail, treat it as deliberate but verify the arithmetic.

## Amplicon-size arithmetic (the rule that must never break)

```
naked size        = anchor-to-anchor genomic product, NO tails
+tail size (CE)   = naked size + len(tail on F primer) + len(tail on R primer)
```

The tail on each strand is whichever 5′ addition it actually carries — a full universal tail
(18/18/21/20) on the fluorescent strand, the pigtail (4, sometimes 2) on the other. So a FAM
marker (M41 = 18) with a 4 bp pigtail adds 22 bp; a NED marker (MCM = 21) with a 4 bp pigtail
adds 25 bp; etc.

**Worked check (PKD1 examples):**

| Marker | naked | tail F | tail R | +tail (computed) | +tail (stated) |
|---|---|---|---|---|---|
| Chr16:1604 (FAM, M41 on F, gttt on R) | 154 | 18 | 4 | 176 | 176 ✓ |
| Chr16:2343 (NED, MCM on F, gttt on R) | 133 | 21 | 4 | 158 | 158 ✓ |
| Chr16:1299 (PET, gt on F, M-Pet on R) | 223 | 2 | 20 | 245 | 245 ✓ |
| Chr16:2517 (PET, gttt on F, M-Pet on R) | 405 | 4 | 20 | 429 | 429 ✓ |

If a worksheet's stated +tail size disagrees with `naked + tailF + tailR`, that is a real bug —
find which value is wrong before ordering. (In one case a detail sheet listed the 1299 pigtail
as `gttt` while the landing sheet had `gt`; only `gt` matched the stated 245 bp, so `gt` was the
correct orderable sequence and the detail sheet had the typo.)

## In-silico checks use the ANCHOR only

When you run BLAST / in-silico PCR, strip the 5′ tail and search with the **anchor** sequence
(the part after the tail). The tail is not genomic and does not prime template in the early
cycles, so including it corrupts the specificity check.
