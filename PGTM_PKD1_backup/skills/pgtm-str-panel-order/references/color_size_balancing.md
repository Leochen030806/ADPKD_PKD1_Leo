# CE dye-channel & fragment-size balancing

In capillary electrophoresis (CE) genotyping, fragments are resolved by **size** and **dye
colour** together. Two fragments can share a size if they are different colours, but two
fragments of the **same colour must not overlap in size**, or their peaks collide and you can't
read the genotype. Each STR is a range, not a point — the repeat is polymorphic — so leave room.

## Rules

1. **Four channels**: FAM (blue), HEX (green), NED (yellow), PET (red). A fifth dye is normally
   reserved for the size standard; don't use it for markers.
2. **Working window**: place expected `+tail` fragment sizes roughly within **130–350 bp**. This
   is where CE sizing is most accurate and where common size standards have dense ladders.
3. **Within a colour, don't overlap**: order the same-colour markers by size and leave a gap
   that comfortably exceeds the allele range of each STR. Even ~20 bp spacing across the window
   is a good target; tighter is risky because each allele spans several repeat units.
4. **Spread the load**: aim for a similar number of markers per colour so no single channel is
   crowded. With ~12 markers that is ~3 per channel.
5. **Long-fragment backups are OK but lonely**: one marker can sit beyond 350 bp as a backup
   (PKD1 keeps a PET fragment at 429 bp), but it must still be the only PET fragment in that size
   neighbourhood and you accept slightly noisier sizing.

## How this constrains redesign

The size lane you assign in this stage becomes the **target naked size** for stage 3:
`target naked ≈ target +tail − (tailF + tailR)`. If a marker can't be redesigned down to its lane
(blocked by flanking repeat/Alu), either (a) move it to a less crowded part of its colour, (b)
recolour it to a channel with room, or (c) accept it as the long-fragment backup. Recolouring is
cheap — it's just a different 5′ tail — which is exactly why the universal-tail system is used.

## Quick layout sanity check

`scripts/panel_qc.py` reports, per colour, the sorted `+tail` sizes and the minimum gap between
adjacent same-colour fragments, and warns when any gap is below a threshold or a fragment falls
outside the window. Run it before committing the panel.
