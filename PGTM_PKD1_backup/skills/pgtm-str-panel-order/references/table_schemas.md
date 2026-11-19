# Table schemas (source → master → order list)

Three tables flow through the pipeline. They share a vocabulary; this file is the canonical
column model and the Chinese↔English header map (real worksheets are usually in Chinese).

## Common term glossary (中 / EN)

| Chinese | English | Meaning |
|---|---|---|
| 目标通道 | Target channel | Dye lane: FAM / HEX / NED / PET |
| Marker | Marker | STR locus label, e.g. `Chr16:1604` |
| 基因侧 | Gene side | `5' Upstream (cen)` or `3' Downstream (pter)` relative to the gene |
| STR 位置 (重复区) | STR locus (repeat region) | hg38 coordinates of the repeat tract |
| 重复 | Repeat | repeat motif and count, e.g. `21.5x CA` |
| Het | Heterozygosity | population informativeness (often filled later) |
| 引物名 | Primer name | e.g. `M41-Chr16:1604-F1` |
| 角色 | Role | `荧光尾 (fluor tail)` or `pigtail` |
| 尾+锚定 | tail + anchor | 5′ universal tail (or pigtail) concatenated to the gene-specific anchor |
| 锚定 | anchor | the gene-specific 3′ part that actually primes genomic DNA |
| 裸长 | naked length | amplicon size with NO tails (anchor-to-anchor) |
| +tail | +tail length | amplicon size including both 5′ tails (what CE shows) |
| 落地 | landing (final) | the finalized decision/value for this marker |
| 落地色 | landing dye | final dye after any colour change |
| 落地尾前缀 | landing tail prefix | final tail: M41 / M20 / MCM / M-Pet |
| 落地方案 | landing plan | `保留 (RETAIN)` or `重设计 (REDESIGN)` |
| 可下单序列 | orderable sequence | the exact sequence to synthesize (tail+anchor, 5′→3′) |

## 1. Source / clinically-validated primer table

One block per marker, two primer rows (F, R). Captures, per primer:
`role`, `original tail+anchor sequence`, `Start`, `End`, `mer (length)`, `GC#/AT#`, `Tm`,
`naked length`, `+tail length`; and per marker: `target channel`, `gene side`, `STR locus`,
`repeat`, and a **clinical/remarks** field — crucially **how many real cases the marker was used
in** (`Used in N PKD1 cases` / `Never used 未用过`). That usage count is the main driver of stage 3.

## 2. Master table (总表)

A wide consolidation with three column groups (keep them visually separated):

1. **Marker info** — channel, No., marker, gene side, STR locus, repeat, Het.
2. **Source (original) primer data** — original name, role, sequence, Start/End, length, GC, Tm,
   naked length, +tail length, clinical remarks.
3. **Landing result** — landing dye, landing tail prefix, landing +tail size, landing naked size,
   Δ(+tail) vs original, and a free-text **plan/rationale** ("保留原引物(用过4次)…", "重设计达标; 裸长133…").
4. **Orderable** — the final `可下单序列` (tail+anchor) for F and R.

Colour convention in the orderable column: **green = redesigned new primer**, **blue = retained
original**. This is the audit trail — never discard the rationale text.

## 3. Order list (下单表) — the stage-7 deliverable

Lean, vendor-facing. One row per oligo (2 per marker). Exact columns produced by
`scripts/build_order_list.py`:

| Column | Source | Notes |
|---|---|---|
| No. | marker index | merged across the F/R pair |
| Primer Name | generated | `{tail-prefix}-{marker}-{F1/R1}` for the fluor primer; `Pig-{marker}-{F1/R1}` for the pigtail primer |
| Marker (STR locus) | master | merged across pair; includes gene side |
| Strand | F / R + (fluor/pigtail) | |
| 5′ Dye | derived from tail prefix | only on the fluorescent strand |
| Sequence (5′→3′, tail+anchor) | orderable column | full synthesized oligo |
| Length (nt) | computed | full oligo length = tail + anchor |
| Tm (anchor, °C) | master | anchor priming Tm, NOT the tailed-oligo Tm |
| Location (hg38) | reference + STR locus | accession (`NC_000016.10`) + repeat-region coords; not stale per-primer coords |
| Expected amplicon (bp, incl. tails) | computed/checked | merged across pair = naked + both tail lengths |

Second sheet ("Tails & Notes"): the four universal tail definitions + pigtail, and operational
notes (Tm meaning, location caveat for redesigned markers, retain/redesign rationale, singleplex
flags, dropped markers, and any sequence discrepancies found between worksheet versions).

## Record schema for the scripts

`build_order_list.py` and `panel_qc.py` take a JSON list of finalized per-marker records:

```json
{
  "no": 1,
  "marker": "Chr16:1604",
  "gene_side": "3' Downstream (pter)",
  "str_locus": "1,604,317-1,604,275",
  "fluor_strand": "F",                 // which strand carries the dye tail: "F" or "R"
  "tail_prefix": "M41",                // M41|M20|MCM|M-Pet  -> dye derived automatically
  "f_seq": "GGTTTTCCCAGTCACGACAGGTGAAAGTGGCTAAGTGGC",
  "r_seq": "gtttCAGTATATGGAGGAGCCTGCTG",
  "f_tm": 60.5,
  "r_tm": 60.0,
  "amplicon_with_tails": 176,          // optional; if omitted, script computes from naked+tails
  "naked": 154,                        // optional; provide one of naked / amplicon_with_tails
  "plan": "Retained",                  // Retained | Redesigned | Redesigned*  (* = needs singleplex)
  "reference": "NC_000016.10"          // optional, defaults to NC_000016.10 (hg38 chr16)
}
```

The script derives dye from `tail_prefix`, figures out the pigtail strand as the non-fluor strand,
computes oligo lengths from the sequences, and cross-checks `amplicon_with_tails` against
`naked + tail_F_len + tail_R_len`. If both `naked` and `amplicon_with_tails` are given and they
disagree with the tail lengths, it raises a clear error — that mismatch is a real design bug.
