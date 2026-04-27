#!/usr/bin/env python3
"""
ALS Adult Data – Diagnostic Probe
===================================
Run this on the server to discover the structure of ALS Adult .sav files.
It reports: column names matching rugby/age/gender/location patterns,
unique age values, gender codes, sport column values, and checks
whether the same column names from the Young data exist.

Usage:
    cd /home/reza/ALS_RFU_Analysis
    python als_adult_diagnostic.py
"""

import os
import re
import sys
from pathlib import Path
import pandas as pd
import pyreadstat

BASE_DIR = Path("/home/reza/ALS_RFU_Analysis")

ADULT_FILES = [
    "ALS_Adult_2017-18.sav",
    "ALS_Adult_2018-19.sav",
    "ALS_Adult_2019-20.sav",
    "ALS_Adult_2020-21.sav",
    "ALS_Adult_2021-22.sav",
    "ALS_Adult_2022-23.sav",
]

# Columns we know from ALS Young data
YOUNG_KNOWN = {
    "sport":    "onceawk_modplus_everywhere_GR_RUGBY_CC018",
    "age":      "age_11",
    "gender":   "gend3",
    "weight":   "wt_gross",
    "id":       "Respondent_Serial",
    "region":   "Region_name",
    "csp_base": "CSP_name",
    "csp_2019": "CSP_name2019",
    "csp_2020": "CSP_name2020",
}

# Regex patterns for column discovery
PATTERNS = {
    "rugby":    re.compile(r"rugby", re.IGNORECASE),
    "age":      re.compile(r"age", re.IGNORECASE),
    "gender":   re.compile(r"gend", re.IGNORECASE),
    "weight":   re.compile(r"wt_|weight", re.IGNORECASE),
    "location": re.compile(r"county|region|state|district|area|location|csp|la_", re.IGNORECASE),
}

SEP = "=" * 80


def diagnose_file(filepath: Path):
    """Load one .sav file and print a comprehensive diagnostic."""
    print(f"\n{SEP}")
    print(f"FILE: {filepath.name}")
    print(SEP)

    if not filepath.exists():
        print(f"  *** FILE NOT FOUND ***")
        return

    df, meta = pyreadstat.read_sav(str(filepath))
    print(f"  Shape: {df.shape[0]:,} rows × {df.shape[1]:,} columns")

    # ── 1. Check if known Young columns exist ──
    print(f"\n  --- Known columns from ALS Young ---")
    for label, col in YOUNG_KNOWN.items():
        present = col in df.columns
        extra = ""
        if present:
            nunique = df[col].nunique()
            extra = f"  (nunique={nunique})"
        status = "✓ FOUND" if present else "✗ MISSING"
        print(f"    {label:12s} | {col:55s} | {status}{extra}")

    # ── 2. Pattern-matched column discovery ──
    print(f"\n  --- Pattern-matched columns ---")
    for pat_name, pattern in PATTERNS.items():
        matches = [c for c in df.columns if pattern.search(c)]
        print(f"\n    [{pat_name.upper()}] ({len(matches)} matches):")
        for col in matches[:30]:  # cap at 30
            nunique = df[col].nunique()
            sample = df[col].dropna().head(5).tolist()
            print(f"      {col:60s} nunique={nunique:4d}  sample={sample}")
        if len(matches) > 30:
            print(f"      ... and {len(matches)-30} more")

    # ── 3. Age deep-dive ──
    print(f"\n  --- Age column deep-dive ---")
    # Try known column first
    age_col = None
    if "age_11" in df.columns:
        age_col = "age_11"
    else:
        # Look for age-like columns
        age_candidates = [c for c in df.columns if PATTERNS["age"].search(c)]
        # Prefer columns with reasonable unique counts (age bands typically 5-20)
        for c in age_candidates:
            nu = df[c].nunique()
            if 2 <= nu <= 30:
                age_col = c
                break

    if age_col:
        print(f"    Primary age column: {age_col}")
        vc = df[age_col].value_counts().sort_index()
        print(f"    Unique values ({len(vc)}):")
        for val, count in vc.items():
            print(f"      {val:>8} → {count:>8,} respondents")

        # Check if 17 and 18 exist
        vals = set(df[age_col].dropna().unique())
        for target in [17, 17.0, 18, 18.0, "17", "18", "17.0", "18.0"]:
            if target in vals:
                print(f"    ★ Age {target} IS PRESENT")
    else:
        print(f"    No suitable age column found automatically.")
        print(f"    All age-pattern columns: {[c for c in df.columns if PATTERNS['age'].search(c)]}")

    # ── 4. Gender deep-dive ──
    print(f"\n  --- Gender column deep-dive ---")
    gender_col = "gend3" if "gend3" in df.columns else None
    if not gender_col:
        gend_candidates = [c for c in df.columns if PATTERNS["gender"].search(c)]
        if gend_candidates:
            gender_col = gend_candidates[0]

    if gender_col:
        print(f"    Gender column: {gender_col}")
        vc = df[gender_col].value_counts().sort_index()
        for val, count in vc.items():
            print(f"      {val:>8} → {count:>8,}")
    else:
        print(f"    No gender column found.")

    # ── 5. Sport/Rugby deep-dive ──
    print(f"\n  --- Rugby/Sport columns deep-dive ---")
    rugby_cols = [c for c in df.columns if PATTERNS["rugby"].search(c)]
    print(f"    Total rugby-related columns: {len(rugby_cols)}")

    # Check the specific Young column
    sport_col = YOUNG_KNOWN["sport"]
    if sport_col in df.columns:
        print(f"\n    ★ EXACT Young column found: {sport_col}")
        vc = df[sport_col].value_counts().sort_index()
        for val, count in vc.items():
            print(f"      {val:>8} → {count:>8,}")
        # Cross-tab with age if possible
        if age_col:
            rugby_yes = df[df[sport_col] == 1]
            if len(rugby_yes) > 0:
                age_dist = rugby_yes[age_col].value_counts().sort_index()
                print(f"\n    Age distribution of rugby participants (sport=1):")
                for val, count in age_dist.items():
                    print(f"      Age {val:>6} → {count:>6,} participants")
    else:
        print(f"    Exact Young sport column NOT found.")
        print(f"    Listing all rugby columns with value counts:")
        for col in rugby_cols[:15]:
            vc = df[col].value_counts().sort_index()
            print(f"\n      {col}:")
            for val, count in vc.head(5).items():
                print(f"        {val:>8} → {count:>8,}")

    # ── 6. Location columns ──
    print(f"\n  --- Location columns ---")
    loc_cols = [c for c in df.columns if PATTERNS["location"].search(c)]
    for col in loc_cols[:20]:
        nunique = df[col].nunique()
        sample = df[col].dropna().head(3).tolist()
        print(f"    {col:55s} nunique={nunique:4d}  sample={sample}")

    # ── 7. Quick summary for integration ──
    print(f"\n  --- Integration summary ---")
    if age_col:
        age_vals = sorted(df[age_col].dropna().unique())
        has_17 = any(v in [17, 17.0] for v in age_vals)
        has_18 = any(v in [18, 18.0] for v in age_vals)
        print(f"    Age range: {min(age_vals)} – {max(age_vals)}")
        print(f"    Has age 17: {'YES ✓' if has_17 else 'NO ✗'}")
        print(f"    Has age 18: {'YES ✓' if has_18 else 'NO ✗'}")

        if sport_col in df.columns and (has_17 or has_18):
            target_ages = [v for v in age_vals if v in [17, 17.0, 18, 18.0]]
            subset = df[(df[age_col].isin(target_ages)) & (df[sport_col] == 1)]
            print(f"    Rugby players aged 17–18: {len(subset):,}")
            if gender_col:
                for gval, glabel in [(1, "Male"), (2, "Female")]:
                    n = len(subset[subset[gender_col] == gval])
                    print(f"      {glabel}: {n:,}")

    print(f"\n{'─'*80}")


def main():
    print("ALS Adult Data – Diagnostic Report")
    print(f"Directory: {BASE_DIR}")
    print(f"Files to probe: {len(ADULT_FILES)}")

    # Also list what's actually in the directory
    print(f"\nFiles matching 'ALS_Adult*' in {BASE_DIR}:")
    actual = sorted(BASE_DIR.glob("ALS_Adult*"))
    if actual:
        for f in actual:
            print(f"  {f.name}  ({f.stat().st_size / 1e6:.1f} MB)")
    else:
        print("  *** NONE FOUND ***")
        print("  Looking for any .sav files:")
        for f in sorted(BASE_DIR.glob("*.sav")):
            print(f"    {f.name}")

    # Run diagnostics
    for fname in ADULT_FILES:
        diagnose_file(BASE_DIR / fname)

    print(f"\n{SEP}")
    print("DIAGNOSTIC COMPLETE")
    print(f"Please share the output with Claude so the Adult data")
    print(f"can be integrated into the analysis pipeline.")
    print(SEP)


if __name__ == "__main__":
    main()
