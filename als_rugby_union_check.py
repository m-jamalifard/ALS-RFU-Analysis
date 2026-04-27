#!/usr/bin/env python3
"""
Quick diagnostic: find Rugby Union-specific columns in each ALS Young .sav file.
Run: cd path/ALS_RFU_Analysis && python als_rugby_union_check.py
"""
import pyreadstat
from pathlib import Path

BASE = Path("path/ALS_RFU_Analysis")
FILES = [
    "ALS_Young_2017-18.sav",
    "ALS_Young_2018-19.sav",
    "ALS_Young_2019-20.sav",
    "ALS_Young_2020-21.sav",
    "ALS_Young_2021-22.sav",
    "ALS_Young_202223.sav",
]

CURRENT_COL = "onceawk_modplus_everywhere_GR_RUGBY_CC018"

for fname in FILES:
    path = BASE / fname
    if not path.exists():
        print(f"\n{'='*70}\n{fname}: NOT FOUND\n")
        continue

    df, meta = pyreadstat.read_sav(str(path))
    print(f"\n{'='*70}")
    print(f"FILE: {fname}  ({df.shape[0]:,} rows × {df.shape[1]:,} cols)")
    print(f"{'='*70}")

    # Find all rugby-related columns
    rugby_cols = sorted([c for c in df.columns if "rugby" in c.lower()])
    print(f"\nAll rugby columns ({len(rugby_cols)}):")

    # Group by type
    union_cols = [c for c in rugby_cols if "union" in c.lower()]
    league_cols = [c for c in rugby_cols if "league" in c.lower()]
    touch_cols = [c for c in rugby_cols if "touch" in c.lower()]
    tag_cols = [c for c in rugby_cols if "tag" in c.lower()]
    generic_cols = [c for c in rugby_cols if not any(x in c.lower() for x in ["union", "league", "touch", "tag"])]

    for label, cols in [("RUGBY UNION", union_cols), ("RUGBY LEAGUE", league_cols),
                         ("RUGBY TOUCH", touch_cols), ("RUGBY TAG", tag_cols),
                         ("GENERIC RUGBY", generic_cols)]:
        if cols:
            print(f"\n  [{label}] ({len(cols)} columns):")
            # Show the "onceawk" or "MONTHS_12" binary ones first
            key_cols = [c for c in cols if "onceawk" in c.lower() or "months_12" in c.lower() or "GR_" in c]
            for c in key_cols:
                vc = df[c].value_counts().sort_index()
                vc_str = ", ".join(f"{v}={n:,}" for v, n in vc.items())
                print(f"    ★ {c}")
                print(f"      values: {vc_str}")

                # Check SPSS labels
                if c in meta.variable_value_labels:
                    for k, v in sorted(meta.variable_value_labels[c].items()):
                        if k > 0:
                            print(f"      label {k} = {v}")

            # Show count of remaining
            other = [c for c in cols if c not in key_cols]
            if other:
                print(f"    ... plus {len(other)} other columns (duration, frequency, etc.)")

    # Check current column
    print(f"\n  Current script column: {CURRENT_COL}")
    if CURRENT_COL in df.columns:
        vc = df[CURRENT_COL].value_counts().sort_index()
        print(f"    ✓ FOUND — values: {', '.join(f'{v}={n:,}' for v, n in vc.items())}")
    else:
        print(f"    ✗ MISSING")

    # Check for the union-specific column we expect
    for candidate in ["onceawk_modplus_everywhere_GR_RUGBYUNION_CD0182",
                       "onceawk_modplus_everywhere_GR_RUGBYUNION_CC018",
                       "MONTHS_12_RUGBYUNION_F03"]:
        if candidate in df.columns:
            vc = df[candidate].value_counts().sort_index()
            print(f"\n  ★ UNION CANDIDATE: {candidate}")
            print(f"    values: {', '.join(f'{v}={n:,}' for v, n in vc.items())}")

print(f"\n{'='*70}")
print("DONE — share this output with Claude to update the script.")
print(f"{'='*70}")
