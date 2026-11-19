---
name: "str-csv-allele-report"
description: "Process SeqStudio CSV export data from 16 Coriell reference samples to generate STR allele calls with Size Standard calibration, producing structured reports for comparison with GeneMapper."
---

# STR CSV Allele Calling Report — Size Standard Calibration

This skill processes raw SeqStudio peak CSV exports from multiple samples to generate STR marker allele calls with Size Standard (LIZ-500) calibration, then compiles results into structured reports for validation against GeneMapper official data.

## Fixed reference data

**Standard sample order** — the 16 Coriell reference samples:

```
1 NA03814    2 NA03815    3 NA04738    4 NA04776    5 NA04820    6 NA06075    7 NA06890    8 NA07425
9 NA07426   10 NA07428   11 NA09133   12 NA11518   13 NA16243   14 NA17942   15 NA22601   16 NA50194
```

**LIZ-500 Size Standard peaks** — 17 known sizes used for calibration:

```python
[35, 50, 75, 100, 139, 150, 160, 200, 250, 300, 340, 350, 400, 415, 450, 490, 500] bp
```

**STR allele valid range** — typical STR markers span 150–350 bp after calibration. Peaks outside this range indicate:
- Below 150 bp: noise or degradation
- Above 350 bp: likely Size Standard contamination

**Sample identification** — extract from filename pattern:

```
<Position>_<SampleID>-<ReplicateNum>_Sample_<DateTime>.fsa
Example: A1_NA03814-3_Sample_20260716_162325.fsa
```

Position uses: A1–A8 (samples 1–8), B1–B8 (samples 9–16).

## Pipeline

```
0. Input validation     Verify all 16 samples present, CSV format, dye labeling
1. Parse CSV peaks      Extract raw positions, heights, dyes from each sample file
2. Identify standards   Recognize Red/Blue/Yellow dye peaks as Size Standard candidates
3. Fit calibration      Build linear regression model: bp = slope × position + intercept
4. Calibrate all peaks  Convert raw positions to base-pair values using fitted model
5. Call alleles         Extract top-2 peaks in target dye, filter by STR range (150–350 bp)
6. Score quality        Calculate quality based on peak height ratio and count
7. Generate report      Compile per-sample genotypes, statistics, and comparison table
```

## Input format

SeqStudio exports one CSV per sample containing all peaks across all dyes:

```
Dye,Sample File Name,Size,Height,Area in Point,Area in BP,...
Orange,A1_NA03814-3_Sample_20260716_162325.fsa,10.939597315436245,280.0,1522.0,...
Orange,A1_NA03814-3_Sample_20260716_162325.fsa,13.255033557046985,903.0,6155.0,...
Red,A1_NA03814-3_Sample_20260716_162325.fsa,2.28188,274.0,3547.0,...
```

**Key columns:**
- `Dye`: Color designation (Orange/Green = sample; Red/Blue/Yellow = Size Standard)
- `Size`: Raw peak position (electropherogram units, NOT base pairs — this is calibrated)
- `Height`: Peak intensity in RFU (Relative Fluorescence Units)
- `Area in BP`: Peak area in base-pair units

**Marker-to-dye mapping** (from this dataset):
- Marker 1: Orange dye (VIC)
- Other markers: check dye assignment in data

## Processing steps

### Step 1 — Input audit

Verify before processing:

```bash
# Check all 16 samples present
ls *.fsa.csv | wc -l          # should be 16

# Verify sample IDs match Coriell standard
grep -h "Sample File Name" *.csv | sort -u

# Count peaks per sample (quality indicator)
wc -l *.csv
```

If any samples are missing or filenames don't match the expected pattern, stop and ask for clarification.

### Step 2 — Parse and calibrate

Run the Python processing pipeline:

```bash
python3 process_training_sampleN.py
```

This script:
1. Reads all CSV files in the directory
2. Extracts Orange dye peaks (marker 1 sample data) + Red/Blue/Yellow (Size Standard)
3. Fits a linear calibration model across Size Standard peaks
4. Applies calibration to all peaks
5. Calls alleles from top-2 peaks within 150–350 bp range
6. Outputs CSV with genotypes and quality scores

Expected output:

```
position,sample_id,allele_1,allele_2,genotype,quality_score,dye
A1,NA03814,207.9,209.9,207.9/209.9,0.996,Orange
A2,NA03815,187.5,189.3,187.5/189.3,0.991,Orange
...
```

### Step 3 — Generate comparison report

Create a structured report for comparison with GeneMapper:

```
## STR Marker 1 — Allele Calling Report

### Calibration Model
- R² = 0.9745 (excellent fit)
- bp = 5.925712 × position + (-21.151)
- Size Standard peaks used: 5 (out of 17 expected LIZ-500)

### Per-Sample Results

| Position | Sample_ID | Allele_1 | Allele_2 | Genotype       | Quality | Status |
|----------|-----------|----------|----------|----------------|---------|--------|
| A1       | NA03814   | 207.9    | 209.9    | 207.9/209.9    | 0.996   | ✓      |
| A2       | NA03815   | 187.5    | 189.3    | 187.5/189.3    | 0.991   | ✓      |
...

### Summary statistics

- Samples processed: 16/16
- High quality (Q > 0.9): 14
- Moderate quality (0.7 < Q ≤ 0.9): 2
- Low quality (Q ≤ 0.7): 0
- Size Standard contamination detected: 0
- Out-of-range alleles: 0

### Quality flags

No problematic samples identified.
```

### Step 4 — Output files

The pipeline generates:

1. **`markerN_allele_calls.csv`** — detailed per-sample genotypes
2. **`markerN_summary.csv`** — simplified comparison format (Position, Sample_ID, Allele_1, Allele_2, Genotype, Quality)
3. **`markerN_report.txt`** — human-readable report with statistics and flags
4. **`calibration_model.json`** — fitted model parameters for reference

## Comparison with GeneMapper

Prepare for comparison:

1. Extract your GeneMapper genotypes into a CSV:
   ```
   sample_id,allele_1_gm,allele_2_gm,genotype_gm
   NA03814,207.9,209.9,207.9/209.9
   NA03815,187.5,189.3,187.5/189.3
   ...
   ```

2. Merge with pipeline output:
   ```
   Position,Sample_ID,Our_Allele_1,Our_Allele_2,GM_Allele_1,GM_Allele_2,Δ1_bp,Δ2_bp,Match
   A1,NA03814,207.9,209.9,207.9,209.9,0.0,0.0,✓
   A2,NA03815,187.5,189.3,187.5,189.3,0.0,0.0,✓
   ...
   ```

3. Calculate match rate and identify discrepancies

## When to stop and ask

- **Missing samples**: fewer than 16 CSV files found
- **Filename parsing fails**: cannot extract sample ID from filename
- **Calibration failure**: fewer than 3 Size Standard peaks identified, or R² < 0.95
- **Data anomalies**: unusual peak patterns, extreme heights, or systematic dye misassignments
- **Validation mismatch**: expected 16 samples but processed count differs

Always report the specific issue and stop before proceeding.

## Reference

- **Process script**: `process_training_sampleN.py` (N = sample number)
- **Calibrator module**: `size_standard_calibrator.py` — independent Python LIZ-500 implementation
- **Input format**: SeqStudio CSV export from Applied Biosystems instruments
- **Validation**: compare allele calls against GeneMapper official genotypes