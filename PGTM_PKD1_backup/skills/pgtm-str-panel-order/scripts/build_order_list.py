#!/usr/bin/env python3
"""Build the company oligo order list (下单表) from finalized per-marker records.

Generates a two-sheet .xlsx:
  - "Order List": one row per oligo (2 per marker) with name, sequence, dye, length,
    anchor Tm, location, and expected (+tail) amplicon size. Pair-level cells merged.
  - "Tails & Notes": the four universal tails + pigtail, and operational notes.

Usage:
    python build_order_list.py records.json -o order_list.xlsx [--title "..."]

Input schema: see references/table_schemas.md ("Record schema for the scripts").
"""
import argparse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from _common import load_records, primer_names, TAILS, DYE_FILL

FONT, MONO = "Arial", "Consolas"


def build(recs, out, title):
    thin = Side(style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    hdr_fill = PatternFill("solid", fgColor="1F4E79")
    hdr_font = Font(name=FONT, bold=True, color="FFFFFF", size=10)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Order List"
    ws["A1"] = title
    ws["A1"].font = Font(name=FONT, bold=True, size=13, color="1F4E79")
    ws["A2"] = (f"{2*len(recs)} oligos = {len(recs)} markers x 2 primers.  "
                "Sequences 5'->3' (universal 5' tail or pigtail + gene-specific anchor).")
    ws["A2"].font = Font(name=FONT, italic=True, size=9, color="595959")

    headers = ["No.", "Primer Name", "Marker (STR locus)", "Strand", "5' Dye",
               "Sequence (5'->3', tail+anchor)", "Length (nt)", "Tm (anchor, °C)",
               "Location (hg38)", "Expected amplicon (bp, incl. tails)"]
    hrow = 4
    for j, h in enumerate(headers, 1):
        c = ws.cell(hrow, j, h)
        c.font, c.fill, c.alignment, c.border = hdr_font, hdr_fill, center, border

    r = hrow + 1
    pairs = []
    for rec in recs:
        f_name, r_name = primer_names(rec)
        loc = f"{rec['reference']}\nChr16:{rec['str_locus']}" if rec.get("str_locus") else rec["reference"]
        start = r
        for strand in ("F", "R"):
            is_fluor = (strand == rec["fluor_strand"])
            seq = rec["f_seq"] if strand == "F" else rec["r_seq"]
            tm = rec.get("f_tm") if strand == "F" else rec.get("r_tm")
            length = rec["f_len"] if strand == "F" else rec["r_len"]
            ws.cell(r, 1, rec.get("no") if strand == "F" else None)
            ws.cell(r, 2, f_name if strand == "F" else r_name)
            if strand == "F":
                side = rec.get("gene_side", "")
                ws.cell(r, 3, f"{rec['marker']}\n{side}".strip())
                ws.cell(r, 9, loc)
                ws.cell(r, 10, rec["amplicon_with_tails"])
            ws.cell(r, 4, f"{strand} ({'fluor' if is_fluor else 'pigtail'})")
            ws.cell(r, 5, rec["dye"] if is_fluor else "—")
            ws.cell(r, 6, seq)
            ws.cell(r, 7, length)
            ws.cell(r, 8, tm)
            r += 1
        pairs.append((start, r - 1, rec["dye"], rec["fluor_strand"]))

    for (s, e, dye, fl) in pairs:
        for col in (1, 3, 9, 10):
            ws.merge_cells(start_row=s, start_column=col, end_row=e, end_column=col)

    for row in range(hrow + 1, r):
        for col in range(1, 11):
            c = ws.cell(row, col)
            c.border = border
            if col == 6:
                c.font = Font(name=MONO, size=9); c.alignment = Alignment(horizontal="left", vertical="center")
            elif col in (2, 3):
                c.font = Font(name=FONT, size=9); c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            elif col == 9:
                c.font = Font(name=MONO, size=8); c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            else:
                c.font = Font(name=FONT, size=9); c.alignment = center

    # tint dye cells on the fluorescent strand
    for (s, e, dye, fl) in pairs:
        row = s if fl == "F" else s + 1
        c = ws.cell(row, 5)
        c.fill = PatternFill("solid", fgColor=DYE_FILL[dye])
        c.font = Font(name=FONT, size=9, bold=True)

    for col, w in {1: 5, 2: 24, 3: 24, 4: 13, 5: 8, 6: 50, 7: 9, 8: 11, 9: 24, 10: 14}.items():
        ws.column_dimensions[get_column_letter(col)].width = w
    ws.row_dimensions[hrow].height = 42
    ws.freeze_panes = "A5"

    # --- sheet 2 ---
    ws2 = wb.create_sheet("Tails & Notes")
    ws2["A1"] = "Universal 5' tails (the vendor labels the tail's 5' end of the fluorescent primer with the listed dye)"
    ws2["A1"].font = Font(name=FONT, bold=True, size=11, color="1F4E79")
    for j, h in enumerate(["Dye (channel)", "Tail prefix", "Tail sequence (5'->3')", "Tail length (nt)"], 1):
        c = ws2.cell(3, j, h); c.font, c.fill, c.alignment, c.border = hdr_font, hdr_fill, center, border
    tr = 4
    for pfx, (dye, seq, ln) in TAILS.items():
        ws2.cell(tr, 1, dye); ws2.cell(tr, 2, pfx); ws2.cell(tr, 3, seq); ws2.cell(tr, 4, ln)
        ws2.cell(tr, 1).fill = PatternFill("solid", fgColor=DYE_FILL[dye])
        for col in range(1, 5):
            cc = ws2.cell(tr, col); cc.border = border
            cc.font = Font(name=(MONO if col == 3 else FONT), size=9)
            cc.alignment = Alignment(horizontal="left" if col == 3 else "center", vertical="center")
        tr += 1
    ws2.cell(tr + 1, 1, "Pigtail on the non-fluorescent primer: gttt (4 bp; occasionally trimmed). Forces uniform +A adenylation; not dye-labeled.")
    ws2.cell(tr + 1, 1).font = Font(name=FONT, size=9, italic=True)

    flagged = [r["marker"] for r in recs if r["needs_singleplex"]]
    notes = [
        "", "Notes",
        "1. 'Length (nt)' is the full synthesized oligo (tail or pigtail + anchor) — the vendor makes the whole sequence in column F.",
        "2. 'Tm (anchor, °C)' is the gene-specific anchor priming Tm; the 5' universal tail is not counted (universal-tail convention).",
        "3. 'Location (hg38)' = reference accession + STR repeat-region coordinates. For redesigned markers, reconfirm exact primer binding coordinates by in-silico PCR on the anchor (the part after the tail).",
        "4. 'Expected amplicon (bp, incl. tails)' = anchor-to-anchor product + both 5' tail lengths (the size observed on CE).",
        "5. Run a singleplex PCR check on never-used / recoloured markers before adding them to the multiplex.",
    ]
    if flagged:
        notes.append("   Markers needing singleplex verification: " + ", ".join(flagged))
    nr = tr + 3
    for line in notes:
        c = ws2.cell(nr, 1, line)
        c.font = Font(name=FONT, bold=True, size=11, color="1F4E79") if line == "Notes" else Font(name=FONT, size=9)
        nr += 1
    for col, w in {1: 22, 2: 14, 3: 26, 4: 14}.items():
        ws2.column_dimensions[get_column_letter(col)].width = w
    for row in range(tr + 3, nr):
        ws2.merge_cells(start_row=row, start_column=1, end_row=row, end_column=8)
        ws2.cell(row, 1).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    wb.save(out)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("records", help="path to records .json or .csv")
    ap.add_argument("-o", "--out", default="order_list.xlsx", help="output .xlsx path")
    ap.add_argument("--title", default="PGT-M STR Panel — Oligo Synthesis Order List")
    args = ap.parse_args()
    recs = load_records(args.records)
    out = build(recs, args.out, args.title)
    print(f"Wrote {out}  ({2*len(recs)} oligos, {len(recs)} markers)")


if __name__ == "__main__":
    main()
