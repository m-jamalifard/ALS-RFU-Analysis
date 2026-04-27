# ALS–RFU Youth Rugby Participation Analysis Pipeline

## Overview

This repository contains the analytical pipeline for triangulating youth rugby participation data from two sources:

- **RFU GMS** (Game Management System): Club-level registration data from the Rugby Football Union
- **ALS CYP** (Active Lives Survey, Children and Young People): National participation survey from Sport England via UK Data Service

The pipeline supports the University of Essex **REF2029 Impact Case Study** evaluating the Half Game Rule's effect on youth rugby participation.

## Authors

- **Dr Benjamin Jones** — University of Essex, School of Sport, Rehabilitation and Exercise Sciences
- **Mohammadreza Jamalifard** — University of Essex, School of Computer Science and Electronic Engineering (PhD student)

---

## Repository Structure

```
ALS_RFU_Analysis/
│
├── als_rfu_analysis.py          # Core pipeline (main analysis)
├── als_rfu_stratified.py        # Report 1: Stratified/internal analysis
├── als_rfu_impact.py            # Report 2: Impact/RFU-facing analysis
├── als_cross_sport.py           # Cross-sport comparison (football, cricket)
├── als_ses_analysis.py          # SES/IMD deprivation analysis
├── als_2023_24_from_tab_v2.py   # 2023-24 extraction (from .tab file)
├── als_2023_24_extract_v3.py    # 2023-24 extraction (from .sav, chunked)
│
├── output/                      # Core pipeline outputs
├── output_stratified/           # Report 1 CSVs and figures
├── output_impact/               # Report 2 CSVs and figures
├── output_cross_sport/          # Cross-sport CSVs and figures
├── output_ses/                  # SES/IMD CSVs and figures
│
├── ALS_Young_2017-18.sav        # ALS CYP data (not in repo — see Data below)
├── ALS_Young_2018-19.sav
├── ALS_Young_2019-20.sav
├── ALS_Young_2020-21.sav
├── ALS_Young_2021-22.sav
├── ALS_Young_2022-23.sav
├── ALS_Young_2023-24.sav        # .sav truncated — use .tab instead
├── ALS_Young_2023-24.tab        # .tab works: 131K rows, encoding=latin1
│
├── RFU_Data_2011_23.xlsx        # RFU GMS data (not in repo — see Data below)
├── RFU_Data_New.xlsx            # RFU GMS 2023-24 data
│
├── Report_1_Final.docx          # Report 1: Internal/stratified report
├── Report_2_Final.docx          # Report 2: Impact/RFU-facing report
│
├── README.md                    # This file
├── DATA_DICTIONARY.md           # Variable and file reference
└── requirements.txt             # Python dependencies
```

---

## Data Sources (Not Included — Download Required)

### ALS CYP Data
- **Source:** UK Data Service (https://ukdataservice.ac.uk)
- **Study Number:** SN 9533 (Active Lives Children and Young People Survey)
- **Files needed:** `ALS_Young_YYYY-YY.sav` for each wave (2017-18 through 2022-23)
- **Access:** Requires UK Data Service account and project registration
- **Format:** SPSS (.sav), approximately 80-130K rows × 2,000-5,500 columns per wave

### RFU GMS Data
- **Source:** Provided directly by the RFU Data Insights team
- **Files needed:**
  - `RFU_Data_2011_23.xlsx` — Historical data (2011-2023), one sheet per year, ~1,858 clubs
  - `RFU_Data_New.xlsx` — 2023-24 data, ~871 clubs, updated age group structure
- **Format:** Excel, club-level registrations by age group and gender

### Data Placement
Place all data files in the root `ALS_RFU_Analysis/` directory. The scripts expect the filenames listed above.

---

## Installation

### Requirements
- Python 3.10+
- Virtual environment recommended

### Setup
```bash
cd ALS_RFU_Analysis
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Dependencies
```
pandas>=1.5
numpy>=1.23
pyreadstat>=1.2
matplotlib>=3.6
openpyxl>=3.0
scipy>=1.9
```

---

## Running the Pipeline

### Step 1: Core Analysis
```bash
python als_rfu_analysis.py
```
Produces: `output/` — base tables and verification data.

### Step 2: Report 1 (Stratified/Internal)
```bash
python als_rfu_stratified.py
```
Produces: `output_stratified/` — figures and CSVs for Report 1.

### Step 3: Report 2 (Impact/RFU-facing)
```bash
python als_rfu_impact.py
```
Produces: `output_impact/` — figures and CSVs for Report 2.

### Step 4: Cross-Sport Comparison
```bash
python als_cross_sport.py
```
Produces: `output_cross_sport/` — football, cricket, and rugby comparison.

### Step 5: SES/IMD Deprivation Analysis
```bash
python als_ses_analysis.py
```
Produces: `output_ses/` — participation rates by IMD quintile.

### Step 6: ALS 2023-24 Extraction
```bash
python als_2023_24_from_tab_v2.py
```
Produces: `output_2023_24/` — all 2023-24 metrics extracted from the .tab file.

---

## Key Configuration

Each script contains a configuration block at the top. The critical settings are:

### ALS File List
```python
YOUNG_FILES = [
    {"file": "ALS_Young_2017-18.sav", "year": "2017-18", "has_union": False},
    ...
    {"file": "ALS_Young_2022-23.sav", "year": "2022-23", "has_union": True},
]
```
- `has_union`: Set `True` if the file contains `GR_RUGBYUNION_CD0182` (only 2022-23+)

### Year Alignment
```python
ALIGN = [
    ("2017-18", "2017-18", "2018"),       # (label, ALS year, RFU sheet name)
    ("2022-23", "2022-23", "2023 May"),
]
```

### Column Names
```python
COL_AGE    = "age_11"        # Age variable (integer 5-16)
COL_GENDER = "gend3"         # Gender (1=Male, 2=Female); NOTE: 2023-24 uses "GEND3" (uppercase)
COL_WEIGHT = "wt_gross"      # Grossing weight for population estimates
```

---

## Adding New Data Waves

### Adding a new ALS year:
1. Download the `.sav` file from UK Data Service
2. Place in root directory
3. Add entry to `YOUNG_FILES` in each script
4. Add year alignment to `ALIGN`
5. Check if Rugby Union variable exists (set `has_union` accordingly)
6. Run the pipeline

### Adding a new RFU year:
1. Place the Excel file in root directory
2. Update `RFU_NEW_FILE` / `RFU_NEW_YEAR` in each script
3. Verify column structure matches expected format
4. Run the pipeline

---

## Known Issues

### ALS 2023-24 File Integrity
The `ALS_Young_2023-24.sav` file (SN 9533, Year 7) has a known truncation issue: only ~8,125 of the expected 122,480 rows are readable via pyreadstat and PSPP. Both tools report "File ends in partial case." **Workaround:** The `.tab` (tab-delimited) export reads all 131,148 rows successfully when loaded with `encoding="latin1"`. A dedicated script (`als_2023_24_from_tab_v2.py`) handles the extraction. Critical notes: all columns must be converted to numeric via `pd.to_numeric(errors="coerce")` after loading, and the gender column is `GEND3` (uppercase).

### Gender Column Name Change
The gender column changed from `gend3` (lowercase) in waves up to 2022-23 to `GEND3` (uppercase) in 2023-24. Scripts handling 2023-24 must account for this.

---

## Output File Reference

See `DATA_DICTIONARY.md` for complete variable and output file documentation.

---

## Reports

| Report | Title | Audience |
|--------|-------|----------|
| Report 1 | Measuring the Half Game Rule's Impact | Internal/technical |
| Report 2 | Rugby Union Participation Insights | RFU Data Insights team |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03 | Initial pipeline (5 ALS waves, old RFU file) |
| 2.0 | 2026-04 | Added Rugby Union variable (2022-23), new RFU file (2023-24) |
| 2.1 | 2026-04 | Added cross-sport comparison (football, cricket) |
| 2.2 | 2026-04 | Added SES/IMD deprivation analysis |

---

## Licence

This code is provided for academic research purposes as part of the University of Essex REF2029 impact case study. Data files are subject to UK Data Service and RFU data sharing agreements.
