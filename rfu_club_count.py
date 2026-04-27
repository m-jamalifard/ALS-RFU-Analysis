#!/usr/bin/env python3
"""
Count RFU clubs per region from RFU_Data_New.xlsx (2023-24).
Also computes clubs-per-capita and clubs relative to ALS participation.
Run: cd path/ALS_RFU_Analysis && python rfu_club_count.py
"""
import pandas as pd
import numpy as np
from pathlib import Path

BASE = Path("path/ALS_RFU_Analysis")

# ── Load club-level data ──
raw = pd.read_excel(BASE / "RFU_Data_New.xlsx", sheet_name=0, header=None)
r0 = raw.iloc[0].tolist()
data = raw.iloc[2:].copy()
data.columns = ["Constituent Body", "Club"] + [f"col_{i}" for i in range(2, len(data.columns))]
data["Constituent Body"] = data["Constituent Body"].ffill()

# Remove rows where Club is NaN (these are CB-level summaries if any)
clubs = data[data["Club"].notna()].copy()

# ── CB to Region mapping (new-format CB names) ──
CB_TO_REGION = {
    "Eastern Counties Rugby Union (CB)": "East",
    "Essex County RFU (CB)": "East",
    "Hertfordshire RFU (CB)": "East",
    "East Midlands Rugby Union (CB)": "East Midlands",
    "Notts, Lincs & Derbyshire RFU (CB)": "East Midlands",
    "Leicestershire Rugby Union Ltd (CB)": "East Midlands",
    "Middlesex County RFU (CB)": "London",
    "Durham County Rugby Union (CB)": "North East",
    "Northumberland Rugby Union (CB)": "North East",
    "Lancashire County RFU (CB)": "North West",
    "Cheshire RFU (CB)": "North West",
    "Cumbria RFU Ltd. (CB)": "North West",
    "Kent County Rugby Football Union Limited (CB)": "South East",
    "Surrey Rugby (CB)": "South East",
    "Sussex RFU Ltd. (CB)": "South East",
    "Hampshire RFU Ltd. (CB)": "South East",
    "Berkshire County RFU (CB)": "South East",
    "Buckinghamshire County RFU (CB)": "South East",
    "Oxfordshire RFU (CB)": "South East",
    "Cornwall RFU (CB)": "South West",
    "Devon RFU (CB)": "South West",
    "Dorset & Wilts RFU (CB)": "South West",
    "Gloucestershire RFU (CB)": "South West",
    "Somerset County RFU Limited(CB)": "South West",
    "North Midlands RFU (CB)": "West Midlands",
    "Staffordshire County RFU (CB)": "West Midlands",
    "Warwickshire RFU (CB)": "West Midlands",
    "Yorkshire RFU (CB)": "Yorkshire and the Humber",
}

clubs["Region"] = clubs["Constituent Body"].map(CB_TO_REGION)

# Show unmapped CBs
unmapped = clubs[clubs["Region"].isna()]["Constituent Body"].unique()
if len(unmapped) > 0:
    print(f"Unmapped CBs (excluded from regional analysis): {list(unmapped)}")
    for cb in unmapped:
        n = len(clubs[clubs["Constituent Body"] == cb])
        print(f"  {cb}: {n} clubs")

clubs_mapped = clubs[clubs["Region"].notna()]

# ── Count clubs per region ──
print("\n" + "=" * 80)
print("RFU CLUBS PER REGION (2023-24)")
print("=" * 80)

region_counts = clubs_mapped.groupby("Region")["Club"].count().sort_values(ascending=False)
print(f"\nTotal clubs (mapped): {region_counts.sum()}")
print(f"Total clubs (all): {len(clubs)}")

print(f"\n{'Region':<32s} {'Clubs':>6s} {'Share':>7s}")
print("-" * 50)
for reg, n in region_counts.items():
    pct = n / region_counts.sum() * 100
    print(f"{reg:<32s} {n:>6d} {pct:>6.1f}%")

# ── Clubs per CB ──
print("\n" + "=" * 80)
print("CLUBS PER CONSTITUENT BODY")
print("=" * 80)

cb_counts = clubs_mapped.groupby(["Region", "Constituent Body"])["Club"].count()
for reg in sorted(region_counts.index):
    print(f"\n{reg}:")
    for (r, cb), n in cb_counts.items():
        if r == reg:
            print(f"  {cb:<55s} {n:>4d} clubs")

# ── Cross-reference with ALS participation gap ──
print("\n" + "=" * 80)
print("CLUBS vs ALS PARTICIPATION GAP")
print("=" * 80)

# ALS all-rugby 2022-23 by region (from previous analysis)
# These are approximate — from the output CSVs
als_regional = {
    "London": 60286, "Yorkshire and the Humber": 55128,
    "North West": 77227, "East": 73959,
    "West Midlands": 54069, "North East": 19943,
    "South West": 76563, "East Midlands": 35450,
    "South East": 81980,
}

rfu_regional = {
    "London": 5112, "Yorkshire and the Humber": 9316,
    "North West": 14544, "East": 15022,
    "West Midlands": 14274, "North East": 6427,
    "South West": 28690, "East Midlands": 15211,
    "South East": 36746,
}

print(f"\n{'Region':<30s} {'Clubs':>6s} {'ALS':>10s} {'RFU':>8s} {'Gap':>10s} {'Capture':>8s} {'Gap/Club':>10s}")
print("-" * 90)
for reg in region_counts.sort_values(ascending=True).index:
    n_clubs = region_counts[reg]
    als = als_regional.get(reg, 0)
    rfu = rfu_regional.get(reg, 0)
    gap = als - rfu
    capture = rfu / als * 100 if als > 0 else 0
    gap_per_club = gap / n_clubs if n_clubs > 0 else 0
    print(f"{reg:<30s} {n_clubs:>6d} {als:>10,d} {rfu:>8,d} {gap:>10,d} {capture:>7.1f}% {gap_per_club:>9.0f}")

print("\n" + "=" * 80)
print("DONE — share output with Claude")
print("=" * 80)
