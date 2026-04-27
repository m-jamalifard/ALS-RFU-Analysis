#!/usr/bin/env python3
"""
ALS 2023-24 Chunked Reader
============================
The ALS_Young_2023-24.sav file has a truncation issue that prevents
full reads. This script reads in chunks using row_limit + row_offset,
finds the correct gender column, and produces the same output CSVs
that the main scripts would generate.

Run: cd path/ALS_RFU_Analysis && python als_2023_24_extract.py

Output: output_2023_24/
  ├── als_2023_24_cleaned.csv          (full extracted data, key cols only)
  ├── als_2023_24_summary.txt          (verification summary)
  └── als_2023_24_column_check.csv     (gender column discovery)
"""

import os
import logging
from pathlib import Path
import numpy as np
import pandas as pd
import pyreadstat

BASE_DIR   = Path("/home/reza/ALS_RFU_Analysis")
OUTPUT_DIR = BASE_DIR / "output_2023_24"
SAV_FILE   = BASE_DIR / "ALS_Young_2023-24.sav"
CHUNK_SIZE = 20000  # rows per chunk

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
log = logging.getLogger(__name__)

# ── Step 1: Find gender column ──
def find_gender_column():
    log.info("Step 1: Finding gender column name")
    _, meta = pyreadstat.read_sav(str(SAV_FILE), metadataonly=True, encoding="latin1")
    candidates = [c for c in meta.column_names if "gend" in c.lower() or "gender" in c.lower() or "sex" in c.lower()]
    log.info("  Gender candidates: %s", candidates)

    # Read a small sample to check values
    if candidates:
        df, _ = pyreadstat.read_sav(str(SAV_FILE), usecols=candidates,
                                     encoding="latin1", row_limit=1000)
        for c in candidates:
            vals = df[c].dropna().unique()
            log.info("  %s: unique values = %s (n=%d)", c, sorted(vals)[:10], len(vals))

    # Also check Region column
    region_candidates = [c for c in meta.column_names if "region" in c.lower()]
    log.info("  Region candidates: %s", region_candidates)

    return candidates, region_candidates, meta.column_names


# ── Step 2: Read file in chunks ──
def read_chunked(target_cols, gender_col):
    log.info("Step 2: Reading file in chunks of %d rows", CHUNK_SIZE)

    all_cols = target_cols + [gender_col] if gender_col else target_cols
    # Remove duplicates
    all_cols = list(dict.fromkeys(all_cols))

    chunks = []
    offset = 0
    while True:
        try:
            df, _ = pyreadstat.read_sav(str(SAV_FILE), usecols=all_cols,
                                         encoding="latin1",
                                         row_limit=CHUNK_SIZE,
                                         row_offset=offset)
            if len(df) == 0:
                break
            chunks.append(df)
            offset += CHUNK_SIZE
            log.info("  Read rows %d–%d (%d rows)", offset - CHUNK_SIZE, offset, len(df))
            if len(df) < CHUNK_SIZE:
                break  # last chunk
        except Exception as e:
            log.warning("  Chunk at offset %d failed: %s — stopping here", offset, e)
            break

    if not chunks:
        log.error("No data read!")
        return None

    full = pd.concat(chunks, ignore_index=True)
    log.info("  Total rows read: %d", len(full))
    return full


# ── Step 3: Process and produce outputs ──
def process(df, gender_col):
    log.info("Step 3: Processing extracted data")

    COL_AGE    = "age_11"
    COL_WEIGHT = "wt_gross"
    COL_ALLRUGBY  = "onceawk_modplus_everywhere_GR_RUGBY_CC018"
    COL_UNION     = "onceawk_modplus_everywhere_GR_RUGBYUNION_CD0182"
    COL_UNION_SCH = "onceawk_modplus_inschool_GR_RUGBYUNION_CD0182"
    COL_UNION_OUT = "onceawk_modplus_outschool_GR_RUGBYUNION_CD0182"
    COL_ALL_SCH   = "onceawk_modplus_inschool_GR_RUGBY_CC018"
    COL_ALL_OUT   = "onceawk_modplus_outschool_GR_RUGBY_CC018"
    COL_FOOTBALL  = "onceawk_modplus_everywhere_GR_FOOTBALL_CC014"
    COL_CRICKET   = "onceawk_modplus_everywhere_GR_CRICKET_CC017"
    COL_FB_SCH    = "onceawk_modplus_inschool_GR_FOOTBALL_CC014"
    COL_FB_OUT    = "onceawk_modplus_outschool_GR_FOOTBALL_CC014"
    COL_CK_SCH    = "onceawk_modplus_inschool_GR_CRICKET_CC017"
    COL_CK_OUT    = "onceawk_modplus_outschool_GR_CRICKET_CC017"

    age = pd.to_numeric(df[COL_AGE], errors="coerce")
    filt = df[(age >= 7) & (age <= 16)].copy()
    log.info("  Ages 7-16: %d rows", len(filt))

    results = {}

    # ── Rugby (all-rugby) ──
    rugby_all = filt[filt[COL_ALLRUGBY] == 1]
    results["rugby_all_total"]  = rugby_all[COL_WEIGHT].sum()
    results["rugby_all_male"]   = rugby_all.loc[rugby_all[gender_col] == 1, COL_WEIGHT].sum() if gender_col else np.nan
    results["rugby_all_female"] = rugby_all.loc[rugby_all[gender_col] == 2, COL_WEIGHT].sum() if gender_col else np.nan

    # ── Rugby Union (direct) ──
    union = filt[filt[COL_UNION] == 1] if COL_UNION in filt.columns else pd.DataFrame()
    results["rugby_union_total"]  = union[COL_WEIGHT].sum() if len(union) else np.nan
    results["rugby_union_male"]   = union.loc[union[gender_col] == 1, COL_WEIGHT].sum() if gender_col and len(union) else np.nan
    results["rugby_union_female"] = union.loc[union[gender_col] == 2, COL_WEIGHT].sum() if gender_col and len(union) else np.nan

    # ── School/outside-school (all rugby) ──
    if COL_ALL_SCH in filt.columns and COL_ALL_OUT in filt.columns:
        school   = filt.loc[filt[COL_ALL_SCH] == 1, COL_WEIGHT].sum()
        outsch   = filt.loc[filt[COL_ALL_OUT] == 1, COL_WEIGHT].sum()
        both_m   = (filt[COL_ALL_SCH] == 1) & (filt[COL_ALL_OUT] == 1)
        both     = filt.loc[both_m, COL_WEIGHT].sum()
        results["school_allrugby"]      = school
        results["outschool_allrugby"]   = outsch
        results["both_allrugby"]        = both
        results["school_only_allrugby"] = school - both
        results["pct_school_only"]      = (school - both) / school * 100 if school > 0 else 0

    # ── School/outside-school (rugby union) ──
    if COL_UNION_SCH in filt.columns and COL_UNION_OUT in filt.columns:
        sch_u  = filt.loc[filt[COL_UNION_SCH] == 1, COL_WEIGHT].sum()
        out_u  = filt.loc[filt[COL_UNION_OUT] == 1, COL_WEIGHT].sum()
        both_u = filt.loc[(filt[COL_UNION_SCH]==1)&(filt[COL_UNION_OUT]==1), COL_WEIGHT].sum()
        results["school_union"]      = sch_u
        results["outschool_union"]   = out_u
        results["both_union"]        = both_u

    # ── Rugby Union by age (for benchmark table) ──
    log.info("\n  Rugby Union by age (ages 11-16):")
    for a in range(11, 17):
        age_filt = filt[pd.to_numeric(filt[COL_AGE], errors="coerce") == a]
        if COL_UNION in age_filt.columns:
            u_count = age_filt.loc[age_filt[COL_UNION] == 1, COL_WEIGHT].sum()
            a_count = age_filt.loc[age_filt[COL_ALLRUGBY] == 1, COL_WEIGHT].sum()
            results[f"union_age_{a}"] = u_count
            results[f"allrugby_age_{a}"] = a_count
            log.info("    U%d: AllRugby=%,.0f  Union=%,.0f", a, a_count, u_count)

    # ── Football ──
    if COL_FOOTBALL in filt.columns:
        fb = filt[filt[COL_FOOTBALL] == 1]
        results["football_total"]  = fb[COL_WEIGHT].sum()
        results["football_male"]   = fb.loc[fb[gender_col] == 1, COL_WEIGHT].sum() if gender_col else np.nan
        results["football_female"] = fb.loc[fb[gender_col] == 2, COL_WEIGHT].sum() if gender_col else np.nan
        if COL_FB_SCH in filt.columns and COL_FB_OUT in filt.columns:
            fb_sch  = filt.loc[filt[COL_FB_SCH]==1, COL_WEIGHT].sum()
            fb_out  = filt.loc[filt[COL_FB_OUT]==1, COL_WEIGHT].sum()
            fb_both = filt.loc[(filt[COL_FB_SCH]==1)&(filt[COL_FB_OUT]==1), COL_WEIGHT].sum()
            results["football_school"]      = fb_sch
            results["football_outschool"]   = fb_out
            results["football_both"]        = fb_both
            results["football_school_only"] = fb_sch - fb_both

    # ── Cricket ──
    if COL_CRICKET in filt.columns:
        ck = filt[filt[COL_CRICKET] == 1]
        results["cricket_total"]  = ck[COL_WEIGHT].sum()
        results["cricket_male"]   = ck.loc[ck[gender_col] == 1, COL_WEIGHT].sum() if gender_col else np.nan
        results["cricket_female"] = ck.loc[ck[gender_col] == 2, COL_WEIGHT].sum() if gender_col else np.nan
        if COL_CK_SCH in filt.columns and COL_CK_OUT in filt.columns:
            ck_sch  = filt.loc[filt[COL_CK_SCH]==1, COL_WEIGHT].sum()
            ck_out  = filt.loc[filt[COL_CK_OUT]==1, COL_WEIGHT].sum()
            ck_both = filt.loc[(filt[COL_CK_SCH]==1)&(filt[COL_CK_OUT]==1), COL_WEIGHT].sum()
            results["cricket_school"]      = ck_sch
            results["cricket_outschool"]   = ck_out
            results["cricket_both"]        = ck_both
            results["cricket_school_only"] = ck_sch - ck_both

    return results


def main():
    os.chdir(BASE_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Find gender column
    gender_cands, region_cands, all_cols = find_gender_column()

    # Pick the best gender column
    gender_col = None
    for c in ["gend3", "Gend3", "gend4", "Gender", "gender", "Sex", "sex"]:
        if c in all_cols:
            gender_col = c
            break
    if not gender_col and gender_cands:
        gender_col = gender_cands[0]
    log.info("Using gender column: %s", gender_col)

    # Step 2: Define target columns
    target_cols = [
        "age_11", "wt_gross",
        "onceawk_modplus_everywhere_GR_RUGBY_CC018",
        "onceawk_modplus_everywhere_GR_RUGBYUNION_CD0182",
        "onceawk_modplus_inschool_GR_RUGBYUNION_CD0182",
        "onceawk_modplus_outschool_GR_RUGBYUNION_CD0182",
        "onceawk_modplus_inschool_GR_RUGBY_CC018",
        "onceawk_modplus_outschool_GR_RUGBY_CC018",
        "onceawk_modplus_everywhere_GR_FOOTBALL_CC014",
        "onceawk_modplus_inschool_GR_FOOTBALL_CC014",
        "onceawk_modplus_outschool_GR_FOOTBALL_CC014",
        "onceawk_modplus_everywhere_GR_CRICKET_CC017",
        "onceawk_modplus_inschool_GR_CRICKET_CC017",
        "onceawk_modplus_outschool_GR_CRICKET_CC017",
    ]
    # Add region if available
    if region_cands:
        target_cols.append(region_cands[0])

    # Filter to columns that actually exist
    existing = set(all_cols)
    target_cols = [c for c in target_cols if c in existing]
    log.info("Target columns (%d): %s", len(target_cols), target_cols)

    # Step 3: Read in chunks
    df = read_chunked(target_cols, gender_col)
    if df is None:
        return

    # Step 4: Process
    results = process(df, gender_col)

    # Step 5: Save outputs
    summary = pd.DataFrame([results])
    summary.to_csv(OUTPUT_DIR / "als_2023_24_summary.csv", index=False)

    with open(OUTPUT_DIR / "als_2023_24_summary.txt", "w") as f:
        f.write("ALS 2023-24 Extraction Summary\n")
        f.write("=" * 50 + "\n")
        f.write(f"Total rows read: {len(df):,}\n")
        f.write(f"Ages 7-16: {((pd.to_numeric(df['age_11'],errors='coerce')>=7)&(pd.to_numeric(df['age_11'],errors='coerce')<=16)).sum():,}\n")
        f.write(f"Gender column: {gender_col}\n\n")
        for k, v in sorted(results.items()):
            if isinstance(v, float):
                f.write(f"  {k:<30s}: {v:>12,.0f}\n")
            else:
                f.write(f"  {k:<30s}: {v}\n")

    log.info("\nResults saved to %s", OUTPUT_DIR)
    log.info("\n=== KEY RESULTS ===")
    for k in sorted(results.keys()):
        v = results[k]
        if isinstance(v, float) and not np.isnan(v):
            log.info("  %s: %,.0f", k, v)


if __name__ == "__main__":
    main()
