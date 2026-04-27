#!/usr/bin/env python3
"""
Lightweight check: find school/club setting columns in ALS data.
Uses metadata-only loading first, then targeted column loading.
Run: cd path/ALS_RFU_Analysis && python als_setting_check.py
"""
import pyreadstat
from pathlib import Path

BASE = Path("path/ALS_RFU_Analysis")

def get_column_names(filepath):
    """Get just column names without loading data."""
    _, meta = pyreadstat.read_sav(str(filepath), metadataonly=True)
    return meta.column_names

def load_cols(filepath, cols):
    """Load only specific columns."""
    available = get_column_names(filepath)
    keep = [c for c in cols if c in available]
    if not keep:
        return None
    df, _ = pyreadstat.read_sav(str(filepath), usecols=keep)
    return df

# ══════════════════════════════════════════════════════════════════
# 1. ALS Young 2022-23 — check setting columns
# ══════════════════════════════════════════════════════════════════
print("=" * 70)
print("ALS Young 2022-23 — Column name scan (metadata only)")
print("=" * 70)

cols_2223 = get_column_names(BASE / "ALS_Young_2022-23.sav")
print(f"Total columns: {len(cols_2223)}")

# Find all rugby union onceawk columns (these have setting info)
union_onceawk = sorted([c for c in cols_2223 if "RUGBYUNION" in c and "onceawk" in c])
generic_onceawk = sorted([c for c in cols_2223 if "GR_RUGBY_CC018" in c and "onceawk" in c])

print(f"\nRUGBYUNION onceawk columns ({len(union_onceawk)}):")
for c in union_onceawk:
    print(f"  {c}")

print(f"\nGeneric RUGBY onceawk columns ({len(generic_onceawk)}):")
for c in generic_onceawk:
    print(f"  {c}")

# Load just the key setting columns and show value counts
key_cols = [
    "onceawk_modplus_everywhere_GR_RUGBYUNION_CD0182",
    "onceawk_modplus_inschool_GR_RUGBYUNION_CD0182",
    "onceawk_modplus_outschool_GR_RUGBYUNION_CD0182",
    "onceawk_modplus_everywhere_GR_RUGBY_CC018",
    "onceawk_modplus_inschool_GR_RUGBY_CC018",
    "onceawk_modplus_outschool_GR_RUGBY_CC018",
]
print("\nLoading key columns for value counts...")
df = load_cols(BASE / "ALS_Young_2022-23.sav", key_cols)
if df is not None:
    for c in df.columns:
        vc = df[c].value_counts().sort_index()
        vals = ", ".join(f"{v}={n:,}" for v, n in vc.items())
        print(f"  {c}")
        print(f"    {vals}")

# ══════════════════════════════════════════════════════════════════
# 2. ALS Young 2017-18 — check setting columns exist
# ══════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ALS Young 2017-18 — Column name scan (metadata only)")
print("=" * 70)

cols_1718 = get_column_names(BASE / "ALS_Young_2017-18.sav")
generic_onceawk_17 = sorted([c for c in cols_1718 if "GR_RUGBY_CC018" in c and "onceawk" in c])
print(f"\nGeneric RUGBY onceawk columns ({len(generic_onceawk_17)}):")
for c in generic_onceawk_17:
    print(f"  {c}")

# Load and show values
print("\nLoading key columns...")
df17 = load_cols(BASE / "ALS_Young_2017-18.sav", [
    "onceawk_modplus_everywhere_GR_RUGBY_CC018",
    "onceawk_modplus_inschool_GR_RUGBY_CC018",
    "onceawk_modplus_outschool_GR_RUGBY_CC018",
])
if df17 is not None:
    for c in df17.columns:
        vc = df17[c].value_counts().sort_index()
        vals = ", ".join(f"{v}={n:,}" for v, n in vc.items())
        print(f"  {c}")
        print(f"    {vals}")

# ══════════════════════════════════════════════════════════════════
# 3. ALS Adult 2017-18 — check for setting/club columns
# ══════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ALS Adult 2017-18 — Setting/club column scan (metadata only)")
print("=" * 70)

cols_adult = get_column_names(BASE / "ALS_Adult_2017-18.sav")
print(f"Total columns: {len(cols_adult)}")

# Rugby union columns
ru_adult = sorted([c for c in cols_adult if "RUGBYUNION" in c.upper()])
print(f"\nRUGBYUNION columns ({len(ru_adult)}):")
for c in ru_adult[:30]:
    print(f"  {c}")
if len(ru_adult) > 30:
    print(f"  ... and {len(ru_adult)-30} more")

# Setting/club/school columns
setting_adult = sorted([c for c in cols_adult if any(k in c.lower() for k in
    ["club", "school", "setting", "venue", "where_"])])
print(f"\nSetting/club/school columns ({len(setting_adult)}):")
for c in setting_adult[:20]:
    print(f"  {c}")

# ACTYRA/B/C columns for rugby union (often = different settings in ALS Adult)
actyr_ru = sorted([c for c in cols_adult if "ACTYR" in c and "RUGBYUNION" in c])
print(f"\nACTYR RUGBYUNION columns ({len(actyr_ru)}):")
for c in actyr_ru:
    print(f"  {c}")

# Load ACTYRA/B/C and show values
if actyr_ru:
    print("\nLoading ACTYR columns...")
    dfa = load_cols(BASE / "ALS_Adult_2017-18.sav", actyr_ru)
    if dfa is not None:
        for c in dfa.columns:
            vc = dfa[c].value_counts().sort_index()
            vals = ", ".join(f"{v}={n:,}" for v, n in vc.items())
            print(f"  {c}")
            print(f"    {vals}")

# Check SPSS labels for ACTYR columns
print("\nChecking SPSS metadata labels for ACTYR columns...")
_, meta_adult = pyreadstat.read_sav(str(BASE / "ALS_Adult_2017-18.sav"),
    metadataonly=True)
for c in actyr_ru:
    if c in meta_adult.variable_value_labels:
        print(f"\n  {c} labels:")
        for k, v in sorted(meta_adult.variable_value_labels[c].items()):
            if k >= 0:
                print(f"    {k} = {v}")
    if c in meta_adult.column_names_to_labels:
        print(f"  Variable label: {meta_adult.column_names_to_labels[c]}")

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)
