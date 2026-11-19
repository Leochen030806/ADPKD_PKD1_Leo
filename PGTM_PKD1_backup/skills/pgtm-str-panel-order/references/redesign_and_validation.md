# Retain vs redesign, and validation

## The decision, per marker

You are weighing **clinical proof** against **panel fit**. Use this order of reasoning:

1. **Has the marker been used in real cases?** Clinically-validated primers carry trust you
   cannot recreate from sequence alone. Default to keeping a proven anchor.
2. **Does the panel need it changed?** A marker must hit its assigned size lane (stage 2) and
   its assigned colour. If the proven primer already fits, RETAIN as-is.
3. **If it must change size:** can Primer3 produce a shorter/repositioned anchor that hits the
   lane *and* passes validation?
   - **Yes** → REDESIGN.
   - **No** (flanking Alu/repeat leaves no usable primer site; or redesign only saves a few bp;
     or the redesign comes out *longer*) → RETAIN, and instead solve the size clash by recolouring
     or by treating it as the long-fragment backup.
4. **If it only needs a different colour:** RETAIN the anchor and just swap the 5′ tail. The
   expected product stays at the original naked size.
5. **Never-used candidate markers:** prefer REDESIGN to hit the lane cleanly, and always mark
   them for singleplex verification before they enter the multiplex.

Record the rationale in plain words on the master table. Real examples from PKD1:

- *Retained, blocked:* `Chr16:2517` — flanking Alu makes it impossible to shorten; kept the
  original anchor, swapped tail M41→M-Pet (FAM→PET); kept as the long-fragment (429 bp) backup.
- *Retained, not worthwhile:* `Chr16:1604` — used in 4 cases; redesign would save only ~16 bp and
  was itself blocked; kept unchanged, colour unchanged (FAM).
- *Redesigned:* `Chr16:3067` — shortened from 175→133 bp naked to open its HEX lane.

## Primer3 constraints (starting point)

- Anchor (priming) Tm target ≈ 60 °C, F/R within ~1 °C of each other.
- Anchor length ~18–24 nt; GC ~40–60%.
- Avoid low-complexity / homopolymer runs and known repeat (Alu) elements in the primer site —
  these both misprime and inflate off-target product.
- Set the product-size range from the stage-2 size lane (remember: that lane is the **+tail**
  size; subtract the two tail lengths to get the naked product range to give Primer3).
- Keep the STR repeat tract comfortably inside the amplicon with flank on both sides.

## Validation (stage 5)

Run all of these on the **anchor only** (strip the 5′ tail first — see `universal_tails.md`):

1. **In-silico PCR / BLAST** against the reference assembly (`NC_000016.10` for chr16): expect a
   **single** product of the intended size at the intended locus.
2. **Pseudogene specificity** — essential for PKD1, which has six highly homologous pseudogenes
   (the *PKD1* duplicated region on 16p). Confirm the anchors do not co-amplify a pseudogene copy;
   a primer that is unique to the true gene is required. (PKD2 does not have this problem to the
   same degree, but still check.)
3. **Secondary structure / dimers** — hairpin, self-dimer, and cross-dimer (heterodimer) ΔG.
   Watch any anchor–anchor heterodimer more negative than about **−8 kcal/mol**; list the most
   negative pairs so that if you see spurious peaks on the instrument you check those first.
4. **Singleplex first** — any marker that is never-used or was recoloured/repositioned should pass
   a singleplex PCR (clean single product at expected size) before being added to the multiplex.
   Mark these in the order list (the `Redesigned*` plan flag) so the lab knows.

## What "location" means after redesign

A redesigned anchor has new genomic coordinates; the source table's old Start/End no longer
describe it. For the order list, give the **stable STR-locus region + reference accession** rather
than stale per-primer coordinates, and instruct the user to reconfirm exact binding coordinates by
in-silico PCR on the new anchor.
