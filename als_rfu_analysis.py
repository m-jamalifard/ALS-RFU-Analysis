#!/usr/bin/env python3
"""
ALS & RFU Rugby Union Participation Analysis – Enhanced Edition
=================================================================
  • Rugby Union-specific: 2022-23 uses union column directly; older years
    corrected using the 2022-23 union/all-rugby proportion.
  • ALS 7–18: Young survey (ages 7–16) + Adult survey 17–18 estimate.
  • RFU U7–U18: club registrations including 2023-24 new dataset.
  • Publication-quality visualizations and full gap analysis.

Expected working directory: /home/reza/ALS_RFU_Analysis
  ├── ALS_Young_2017-18.sav … ALS_Young_2022-23.sav
  ├── ALS_Adult_2017-18.sav … ALS_Adult_2022-23.sav
  ├── RFU Data 2011_23.xlsx
  ├── RFU_Data_New.xlsx
  └── output/
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import pyreadstat
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.gridspec import GridSpec
import warnings

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────────────────────
# Global style
# ──────────────────────────────────────────────────────────────────────────────

plt.rcParams.update({
    "font.family":       "sans-serif",
    "font.sans-serif":   ["DejaVu Sans", "Helvetica", "Arial"],
    "font.size":         11,
    "axes.titlesize":    14,
    "axes.titleweight":  "bold",
    "axes.labelsize":    12,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "figure.facecolor":  "white",
    "savefig.facecolor": "white",
    "figure.dpi":        150,
    "savefig.dpi":       150,
    "legend.framealpha":  0.9,
    "legend.edgecolor":  "#cccccc",
})

# ── Colour palette ──
PAL = {
    "als":       "#2563EB",   # blue
    "rfu":       "#DC2626",   # red
    "gap":       "#9333EA",   # purple
    "male":      "#0369A1",
    "female":    "#BE185D",
    "als_fill":  "#BFDBFE",
    "rfu_fill":  "#FECACA",
    "gap_fill":  "#E9D5FF",
    "grid":      "#E5E7EB",
    "text":      "#1F2937",
    "green":     "#059669",
}

CAT_COLORS = [
    "#2563EB", "#DC2626", "#059669", "#D97706", "#7C3AED",
    "#0891B2", "#DB2777", "#65A30D", "#EA580C", "#4F46E5",
]

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

BASE_DIR   = Path("/home/reza/ALS_RFU_Analysis")
OUTPUT_DIR = BASE_DIR / "output"

LOG_FMT = "%(asctime)s | %(levelname)-8s | %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FMT)
log = logging.getLogger(__name__)

GENERIC_COLS = ["Respondent_Serial", "wt_gross"]
GENDER_COL   = "gend3"
AGE_COL      = "age_11"
WEIGHT_COL   = "wt_gross"

# ── Sport columns ──
# GR_RUGBY_CC018 = "all rugby" (union + league + touch + tag) — available in all years
# GR_RUGBYUNION_CD0182 = "rugby union only" — available in 2022-23 only
# For years without a union-specific column, we apply a proportional correction
# factor derived from 2022-23 where both columns coexist.
SPORT_COL_ALLRUGBY = "onceawk_modplus_everywhere_GR_RUGBY_CC018"
SPORT_COL_UNION    = "onceawk_modplus_everywhere_GR_RUGBYUNION_CD0182"

YEAR_CONFIG = [
    {"file": "ALS_Young_2017-18.sav",  "year": "2017-18", "loc_cols": ["Region_name", "CSP_name"],     "csp_src": "CSP_name",     "sport_col": SPORT_COL_ALLRUGBY},
    {"file": "ALS_Young_2018-19.sav",  "year": "2018-19", "loc_cols": ["Region_name", "CSP_name"],     "csp_src": "CSP_name",     "sport_col": SPORT_COL_ALLRUGBY},
    {"file": "ALS_Young_2019-20.sav",  "year": "2019-20", "loc_cols": ["Region_name", "CSP_name2019"], "csp_src": "CSP_name2019", "sport_col": SPORT_COL_ALLRUGBY},
    {"file": "ALS_Young_2020-21.sav",  "year": "2020-21", "loc_cols": ["Region_name", "CSP_name2020"], "csp_src": "CSP_name2020", "sport_col": SPORT_COL_ALLRUGBY},
    {"file": "ALS_Young_2021-22.sav",  "year": "2021-22", "loc_cols": ["Region_name", "CSP_name2020"], "csp_src": "CSP_name2020", "sport_col": SPORT_COL_ALLRUGBY},
    {"file": "ALS_Young_2022-23.sav",  "year": "2022-23", "loc_cols": ["Region_name", "CSP_name2019"], "csp_src": "CSP_name2019", "sport_col": SPORT_COL_UNION},
]

RFU_FILE      = "RFU_Data_2011_23.xlsx"
RFU_SHEET_IDX = [7, 9, 11, 13, 15]
RFU_YEARS_OLD = ["2018", "2019", "2019 nov", "2021 Jan", "2023 May"]
RFU_NEW_FILE  = "RFU_Data_New.xlsx"
RFU_NEW_YEAR  = "2023-24"
RFU_YEARS     = RFU_YEARS_OLD + [RFU_NEW_YEAR]

RFU_AGE_COLUMNS = [
    "U7M", "U7F", "U8M", "U8F", "U9M", "U9F", "U10M", "U10F",
    "U11M", "U11F", "U12M", "U12F", "U13M", "U13F", "U14M", "U14F",
    "U15M", "U15F", "U16M", "U16F", "U17M", "U17F", "U18M", "U18F",
]

# ── ALS age coverage ──
# The ALS "Young" data contains ages 5–16.  RFU U7–U18 ≈ ages 6–18.
# For consistent gap analysis we compare the OVERLAP: ages 7–16.
# ALS ages below 7 are excluded; RFU U17–U18 (≈ ages 16–18) have no
# ALS counterpart and are shown separately.
ALS_AGE_MIN = 7.0     # inclusive — filter out ages 5, 6
ALS_AGE_MAX = 16.0    # inclusive — max in the ALS Young data

# ── ALS Adult configuration ──
# 2020-21 and 2022-23 are Young-format duplicates (ages 5–16); skip them.
# The other 4 have Adult format: Age17 coded bands, different column names.
ADULT_YEAR_CONFIG = [
    {"file": "ALS_Adult_2017-18.sav", "year": "2017-18", "fmt": "adult"},
    {"file": "ALS_Adult_2018-19.sav", "year": "2018-19", "fmt": "adult"},
    {"file": "ALS_Adult_2019-20.sav", "year": "2019-20", "fmt": "adult"},
    {"file": "ALS_Adult_2020-21.sav", "year": "2020-21", "fmt": "young_dup"},
    {"file": "ALS_Adult_2021-22.sav", "year": "2021-22", "fmt": "adult"},
    {"file": "ALS_Adult_2022-23.sav", "year": "2022-23", "fmt": "young_dup"},
]

# Adult format column names
ADULT_SPORT_COL  = "MONTHS_12_RUGBYUNION_F03"   # binary: 1=yes
ADULT_AGE_COL    = "Age17"                       # coded bands; 1.0 = "16–19"
ADULT_U19_COL    = "Age19plus"                   # 0.0 = under 19
ADULT_GENDER_COL = "Gend3"                       # 1=Male, 2=Female, 3=Other
ADULT_WEIGHT_COL = "wt_final"
ADULT_CSP_COL    = "CSP"

# Adult CSP codes → CSP names (note: 26–29 unused, jumps from 25 to 30)
ADULT_CSP_MAP = {
    1.0: "Bedfordshire & Luton", 2.0: "Berkshire", 3.0: "Birmingham",
    4.0: "Black Country", 5.0: "Buckinghamshire and Milton Keynes",
    6.0: "Peterborough & Cambridgeshire", 7.0: "Cheshire",
    8.0: "Cornwall and Isles of Scilly", 9.0: "Cumbria", 10.0: "Derbyshire",
    11.0: "Devon", 12.0: "Dorset", 13.0: "Durham", 14.0: "Greater Essex",
    15.0: "Gloucestershire", 16.0: "Greater Manchester",
    17.0: "Hampshire and Isle of Wight",
    18.0: "Herefordshire and Worcestershire", 19.0: "Hertfordshire",
    20.0: "Humber", 21.0: "Kent", 22.0: "Lancashire",
    23.0: "Leicester, Leicestershire and Rutland", 24.0: "Lincolnshire",
    25.0: "London",
    30.0: "Merseyside", 31.0: "Norfolk", 32.0: "North Yorkshire",
    33.0: "Northamptonshire", 34.0: "Northumberland",
    35.0: "Nottinghamshire", 36.0: "Oxfordshire",
    37.0: "Shropshire and Telford and the Wrekin", 38.0: "Somerset",
    39.0: "South Yorkshire", 40.0: "Staffordshire and Stoke-on-Trent",
    41.0: "Suffolk", 42.0: "Surrey", 43.0: "Sussex",
    44.0: "Tees Valley", 45.0: "Tyne and Wear",
    46.0: "Coventry, Solihull & Warwickshire",
    47.0: "Bristol and West of England", 48.0: "West Yorkshire",
    49.0: "Wiltshire & Swindon",
}

# CSP name → ALS Region (used for both Young and Adult data)
CSP_TO_REGION = {
    "Bedfordshire & Luton": "East", "Peterborough & Cambridgeshire": "East",
    "Greater Essex": "East", "Hertfordshire": "East",
    "Norfolk": "East", "Suffolk": "East",
    "Derbyshire": "East Midlands",
    "Leicester, Leicestershire and Rutland": "East Midlands",
    "Lincolnshire": "East Midlands", "Northamptonshire": "East Midlands",
    "Nottinghamshire": "East Midlands",
    "London": "London",
    "Durham": "North East", "Northumberland": "North East",
    "Tees Valley": "North East", "Tyne and Wear": "North East",
    "Cheshire": "North West", "Cumbria": "North West",
    "Greater Manchester": "North West", "Lancashire": "North West",
    "Merseyside": "North West",
    "Berkshire": "South East", "Buckinghamshire and Milton Keynes": "South East",
    "Hampshire and Isle of Wight": "South East", "Kent": "South East",
    "Oxfordshire": "South East", "Surrey": "South East", "Sussex": "South East",
    "Cornwall and Isles of Scilly": "South West", "Devon": "South West",
    "Dorset": "South West", "Gloucestershire": "South West",
    "Somerset": "South West", "Bristol and West of England": "South West",
    "Wiltshire & Swindon": "South West",
    "Birmingham": "West Midlands", "Black Country": "West Midlands",
    "Herefordshire and Worcestershire": "West Midlands",
    "Shropshire and Telford and the Wrekin": "West Midlands",
    "Staffordshire and Stoke-on-Trent": "West Midlands",
    "Coventry, Solihull & Warwickshire": "West Midlands",
    "Humber": "Yorkshire and the Humber",
    "North Yorkshire": "Yorkshire and the Humber",
    "South Yorkshire": "Yorkshire and the Humber",
    "West Yorkshire": "Yorkshire and the Humber",
}

# ── Mappings ──
REGION_MAP = {
    1.0: "East", 2.0: "East Midlands", 3.0: "London", 4.0: "North East",
    5.0: "North West", 6.0: "South East", 7.0: "South West",
    8.0: "West Midlands", 9.0: "Yorkshire and the Humber",
}

CSP_MAP_BASE = {
    1.0: "Bedfordshire & Luton", 2.0: "Berkshire", 3.0: "Birmingham",
    4.0: "Black Country", 5.0: "Buckinghamshire and Milton Keynes",
    6.0: "Peterborough & Cambridgeshire", 7.0: "Cheshire",
    8.0: "Cornwall and Isles of Scilly", 9.0: "Cumbria", 10.0: "Derbyshire",
    11.0: "Devon", 12.0: "Dorset", 13.0: "Durham", 14.0: "Greater Essex",
    15.0: "Gloucestershire", 16.0: "Greater Manchester",
    17.0: "Hampshire and Isle of Wight",
    18.0: "Herefordshire and Worcestershire", 19.0: "Hertfordshire",
    20.0: "Humber", 21.0: "Kent", 22.0: "Lancashire",
    23.0: "Leicester, Leicestershire and Rutland", 24.0: "Lincolnshire",
    25.0: "London", 26.0: "Merseyside", 27.0: "Norfolk",
    28.0: "North Yorkshire", 29.0: "Northamptonshire",
    30.0: "Northumberland", 31.0: "Nottinghamshire", 32.0: "Oxfordshire",
    33.0: "Shropshire and Telford and the Wrekin", 34.0: "Somerset",
    35.0: "South Yorkshire", 36.0: "Staffordshire and Stoke-on-Trent",
    37.0: "Suffolk", 38.0: "Surrey", 39.0: "Sussex", 40.0: "Tees Valley",
    41.0: "Tyne and Wear", 42.0: "Coventry, Solihull & Warwickshire",
    43.0: "Bristol and West of England", 44.0: "West Yorkshire",
    45.0: "Wiltshire & Swindon",
}

CSP_MAP_EXT = {-1.0: "No information", **CSP_MAP_BASE,
               46.0: "Derbyshire and Nottinghamshire",
               47.0: "West and South Yorkshire", 48.0: "Rise North East"}

def _csp_map_for(csp_src):
    return CSP_MAP_BASE if csp_src == "CSP_name" else CSP_MAP_EXT

# ── RFU CB → ALS Region mapping (approximate geographic alignment) ──
CB_TO_REGION = {
    "Eastern Counties Rugby Union (CB)":               "East",
    "Essex County RFU (CB)":                           "East",
    "Hertfordshire RFU (CB)":                          "East",
    "East Midlands Rugby Union (CB)":                  "East Midlands",
    "Notts, Lincs & Derbyshire RFU (CB)":              "East Midlands",
    "Leicestershire Rugby Union Ltd (CB)":             "East Midlands",
    "Middlesex County RFU (CB)":                       "London",
    "Durham County Rugby Union (CB)":                  "North East",
    "Northumberland Rugby Union (CB)":                 "North East",
    "Lancashire County RFU (CB)":                      "North West",
    "Cheshire RFU (CB)":                               "North West",
    "Cumbria RFU Ltd. (CB)":                           "North West",
    "Kent County Rugby Football Union Limited (CB)":   "South East",
    "Surrey Rugby (CB)":                               "South East",
    "Sussex RFU Ltd. (CB)":                            "South East",
    "Hampshire RFU Ltd. (CB)":                         "South East",
    "Berkshire County RFU (CB)":                       "South East",
    "Buckinghamshire County RFU (CB)":                 "South East",
    "Oxfordshire RFU (CB)":                            "South East",
    "Cornwall RFU (CB)":                               "South West",
    "Devon RFU (CB)":                                  "South West",
    "Dorset & Wilts RFU (CB)":                         "South West",
    "Gloucestershire RFU (CB)":                        "South West",
    "Somerset County RFU Limited(CB)":                 "South West",
    "North Midlands RFU (CB)":                         "West Midlands",
    "Staffordshire County RFU (CB)":                   "West Midlands",
    "Warwickshire RFU (CB)":                           "West Midlands",
    "Yorkshire RFU (CB)":                              "Yorkshire and the Humber",
}

# ── Year alignment for ALS↔RFU comparison ──
YEAR_ALIGNMENT = [
    ("2017-18", "2017-18", "2018"),
    ("2018-19", "2018-19", "2019"),
    ("2019-20", "2019-20", "2019 nov"),
    ("2020-21", "2020-21", "2021 Jan"),
    ("2022-23", "2022-23", "2023 May"),
    # ALS 2021-22 has no close RFU match; RFU 2023-24 has no ALS match
]


# ══════════════════════════════════════════════════════════════════════════════
# 1.  File loading
# ══════════════════════════════════════════════════════════════════════════════

def load_sav(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"SPSS file not found: {path}")
    df, _ = pyreadstat.read_sav(str(path))
    log.info("Loaded SPSS  : %s  (%d × %d)", path.name, *df.shape)
    return df

def load_excel_sheets(path, sheet_indices):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {path}")
    xls = pd.ExcelFile(path)
    out = []
    for idx in sheet_indices:
        name = xls.sheet_names[idx]
        df = xls.parse(sheet_name=name)
        log.info("Loaded sheet  : '%s' (%d × %d)", name, *df.shape)
        out.append(df)
    return out


# ══════════════════════════════════════════════════════════════════════════════
# 2.  ALS preprocessing
# ══════════════════════════════════════════════════════════════════════════════

def preprocess_als_year(raw_df, cfg):
    """Preprocess one ALS Young year using the year-specific sport column."""
    sport_col = cfg["sport_col"]
    keep = GENERIC_COLS + [sport_col, AGE_COL, GENDER_COL] + cfg["loc_cols"]
    # Also load the all-rugby column if different (needed for ratio computation)
    if sport_col != SPORT_COL_ALLRUGBY and SPORT_COL_ALLRUGBY in raw_df.columns:
        keep.append(SPORT_COL_ALLRUGBY)
    keep = list(dict.fromkeys(keep))  # deduplicate
    df = raw_df[keep].copy()
    csp_src = cfg["csp_src"]
    df["CSP"]    = df[csp_src].map(_csp_map_for(csp_src))
    df["Region"] = df["Region_name"].map(REGION_MAP)
    df.drop(columns=cfg["loc_cols"], inplace=True, errors="ignore")
    df.rename(columns={AGE_COL: "Age"}, inplace=True)
    df["Age"] = df["Age"].astype(str)
    # Sport participation flag: 1 = yes in both generic and union columns
    df["_sport"] = (df[sport_col] == 1).astype(int)
    df["weighted_total"] = df["_sport"] * df[WEIGHT_COL]
    return df


def _compute_union_proportion(raw_df_2223):
    """
    From the 2022-23 file where both columns coexist, compute the
    weighted ratio of rugby union to all rugby.

    Returns a dict of proportions: {"overall": float, by_age: {age: float}, ...}
    """
    if SPORT_COL_UNION not in raw_df_2223.columns or SPORT_COL_ALLRUGBY not in raw_df_2223.columns:
        log.warning("Cannot compute union proportion — columns missing.")
        return {"overall": 1.0}

    all_rugby = raw_df_2223[raw_df_2223[SPORT_COL_ALLRUGBY] == 1].copy()
    union     = raw_df_2223[raw_df_2223[SPORT_COL_UNION] == 1].copy()

    wt = "wt_gross"
    all_wt   = all_rugby[wt].sum()
    union_wt = union[wt].sum()

    overall_prop = union_wt / all_wt if all_wt > 0 else 1.0
    log.info("Union proportion (2022-23): %.4f  (union_wt=%.0f / all_wt=%.0f)",
             overall_prop, union_wt, all_wt)

    return {"overall": overall_prop}


def build_als_datasets():
    """
    Load all 6 ALS Young years. For 2022-23 use the Rugby Union column
    directly. For older years (all-rugby only), apply the union proportion
    from 2022-23 to scale weighted totals down to a union-only estimate.
    """
    overall, males, females = {}, {}, {}

    # First pass: load 2022-23 to compute the union proportion
    cfg_2223 = [c for c in YEAR_CONFIG if c["year"] == "2022-23"][0]
    raw_2223 = load_sav(BASE_DIR / cfg_2223["file"])
    union_props = _compute_union_proportion(raw_2223)
    union_ratio = union_props["overall"]

    for cfg in YEAR_CONFIG:
        if cfg["year"] == "2022-23":
            raw = raw_2223  # already loaded
        else:
            raw = load_sav(BASE_DIR / cfg["file"])

        sport_col = cfg["sport_col"]
        df = preprocess_als_year(raw, cfg)
        sport_df = df[df["_sport"] == 1].copy()

        # If this year uses the all-rugby column, apply the union correction
        is_allrugby = (sport_col == SPORT_COL_ALLRUGBY)
        if is_allrugby:
            sport_df["weighted_total"] = sport_df["weighted_total"] * union_ratio
            log.info("ALS %s: applied union proportion %.4f to all-rugby data",
                     cfg["year"], union_ratio)
        else:
            log.info("ALS %s: using Rugby Union column directly (no correction needed)",
                     cfg["year"])

        csv_name = f"Sport_{cfg['year'].replace('-','_')}_young_adults_new.csv"
        sport_df.to_csv(OUTPUT_DIR / csv_name, index=False)
        male_df   = sport_df[sport_df[GENDER_COL] == 1].copy()
        female_df = sport_df[sport_df[GENDER_COL] == 2].copy()
        y = cfg["year"]
        overall[y], males[y], females[y] = sport_df, male_df, female_df

    # Save the union proportion for documentation
    pd.DataFrame([{
        "source_year": "2022-23",
        "union_proportion": union_ratio,
        "applied_to": "2017-18 through 2021-22 (years without union-specific column)",
        "method": "weighted_total * union_proportion",
    }]).to_csv(OUTPUT_DIR / "union_proportion_correction.csv", index=False)
    log.info("Union proportion saved to union_proportion_correction.csv")

    return overall, males, females


# ══════════════════════════════════════════════════════════════════════════════
# 3.  RFU preprocessing
# ══════════════════════════════════════════════════════════════════════════════

def load_rfu_new(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"New RFU file not found: {path}")
    df_raw = pd.read_excel(path, sheet_name=0, header=None)
    row0, row1 = df_raw.iloc[0].tolist(), df_raw.iloc[1].tolist()
    col_names, cur = [], None
    for i in range(len(row0)):
        a, g = row0[i], str(row1[i]).strip()
        if i == 0: col_names.append("Constituent Body"); continue
        if i == 1: col_names.append("Club"); continue
        if not pd.isna(a): cur = str(a).replace(".0", "")
        if g == "Female":         col_names.append(f"{cur}F")
        elif g == "Male":         col_names.append(f"{cur}M")
        elif "self" in g.lower(): col_names.append(f"{cur}_PTSD")
        else:                     col_names.append(f"{cur}_{g}")
    data = df_raw.iloc[2:].copy()
    data.columns = col_names
    data["Constituent Body"] = data["Constituent Body"].ffill()
    num = [c for c in col_names if c not in ("Constituent Body", "Club")]
    data[num] = data[num].apply(pd.to_numeric, errors="coerce").fillna(0)
    cb = data.groupby("Constituent Body", as_index=False)[num].sum()
    keep = [c for c in RFU_AGE_COLUMNS if c in cb.columns]
    return cb[["Constituent Body"] + keep].set_index("Constituent Body")

def build_rfu_datasets():
    sheets = load_excel_sheets(BASE_DIR / RFU_FILE, RFU_SHEET_IDX)
    dfs = []
    for sheet, year in zip(sheets, RFU_YEARS_OLD):
        df = sheet.iloc[:-1].copy()               # remove summary row only

        # Explicitly select only the age columns we care about (+ metadata)
        # This replaces the fragile `iloc[:, :-7]` positional trim.
        target_m = [c for c in RFU_AGE_COLUMNS if c.endswith("M") and c in df.columns]
        target_f = [c for c in RFU_AGE_COLUMNS if c.endswith("F") and c in df.columns]
        age_avail = target_m + target_f

        df["count_col"]   = df[age_avail].sum(axis=1)
        df["count_col_m"] = df[target_m].sum(axis=1)
        df["count_col_f"] = df[target_f].sum(axis=1)

        log.info("RFU %s : %d rows, %d age cols (of %d requested)",
                 year, len(df), len(age_avail), len(RFU_AGE_COLUMNS))
        dfs.append(df)
    ndf = load_rfu_new(BASE_DIR / RFU_NEW_FILE)
    mc = [c for c in ndf.columns if c.endswith("M")]
    fc = [c for c in ndf.columns if c.endswith("F")]
    ndf["count_col"]   = ndf[mc + fc].sum(axis=1)
    ndf["count_col_m"] = ndf[mc].sum(axis=1)
    ndf["count_col_f"] = ndf[fc].sum(axis=1)
    ndf = ndf.reset_index()
    log.info("RFU %s : %d rows", RFU_NEW_YEAR, len(ndf))
    dfs.append(ndf)
    return dfs


# ══════════════════════════════════════════════════════════════════════════════
# 3b. ALS Adult — extract 17–18 year-old rugby estimates
# ══════════════════════════════════════════════════════════════════════════════

def build_adult_17_18(als_young_overall: Dict[str, pd.DataFrame]):
    """
    For each Adult-format year, extract the 16–18 under-19 band,
    weight rugby union participation, then subtract the Young data's
    age-16 contribution to produce a 17–18 estimate.

    Returns dict keyed by year with:
      {"overall": float, "male": float, "female": float,
       "by_region": {region_name: float, ...},
       "by_region_m": {...}, "by_region_f": {...},
       "available": True}
    Years without Adult data return {"available": False}.
    """
    estimates = {}

    for cfg in ADULT_YEAR_CONFIG:
        year = cfg["year"]

        if cfg["fmt"] != "adult":
            log.info("Adult %s: Young-format duplicate — skipping", year)
            estimates[year] = {"available": False}
            continue

        path = BASE_DIR / cfg["file"]
        if not path.exists():
            log.warning("Adult %s: file not found — %s", year, path)
            estimates[year] = {"available": False}
            continue

        # Load only the columns we need (the files are huge — 1.5+ GB)
        need_cols = [ADULT_SPORT_COL, ADULT_AGE_COL, ADULT_U19_COL,
                     ADULT_GENDER_COL, ADULT_WEIGHT_COL, ADULT_CSP_COL]
        df, _ = pyreadstat.read_sav(str(path), usecols=need_cols)
        log.info("Adult %s: loaded %d rows (cols: %s)", year, len(df), need_cols)

        # Filter to under-19, 16-19 age band, rugby union participants
        mask = (
            (df[ADULT_AGE_COL] == 1.0) &       # 16–19 band
            (df[ADULT_U19_COL] == 0.0) &        # under 19
            (df[ADULT_SPORT_COL] == 1.0)         # played rugby union
        )
        rugby = df[mask].copy()
        log.info("Adult %s: %d rugby union participants aged 16–18", year, len(rugby))

        # Weighted totals for the 16-18 band
        rugby["_wt"] = rugby[ADULT_WEIGHT_COL]
        adult_16_18_all = rugby["_wt"].sum()
        adult_16_18_m   = rugby.loc[rugby[ADULT_GENDER_COL] == 1, "_wt"].sum()
        adult_16_18_f   = rugby.loc[rugby[ADULT_GENDER_COL] == 2, "_wt"].sum()

        # Map CSP → Region for Adult data
        rugby["_csp_name"] = rugby[ADULT_CSP_COL].map(ADULT_CSP_MAP)
        rugby["_region"]   = rugby["_csp_name"].map(CSP_TO_REGION)
        adult_by_reg   = rugby.groupby("_region")["_wt"].sum().to_dict()
        adult_by_reg_m = rugby[rugby[ADULT_GENDER_COL] == 1].groupby("_region")["_wt"].sum().to_dict()
        adult_by_reg_f = rugby[rugby[ADULT_GENDER_COL] == 2].groupby("_region")["_wt"].sum().to_dict()

        # Subtract Young age-16 to avoid double-counting
        young_16_all, young_16_m, young_16_f = 0.0, 0.0, 0.0
        young_16_reg, young_16_reg_m, young_16_reg_f = {}, {}, {}

        if year in als_young_overall:
            ydf = als_young_overall[year]
            age_num = pd.to_numeric(ydf["Age"], errors="coerce")
            y16 = ydf[age_num == 16.0]
            young_16_all = y16["weighted_total"].sum()
            young_16_m   = y16.loc[y16[GENDER_COL] == 1, "weighted_total"].sum()
            young_16_f   = y16.loc[y16[GENDER_COL] == 2, "weighted_total"].sum()
            if "Region" in y16.columns:
                young_16_reg   = y16.groupby("Region")["weighted_total"].sum().to_dict()
                young_16_reg_m = y16[y16[GENDER_COL] == 1].groupby("Region")["weighted_total"].sum().to_dict()
                young_16_reg_f = y16[y16[GENDER_COL] == 2].groupby("Region")["weighted_total"].sum().to_dict()

        est_all = max(adult_16_18_all - young_16_all, 0)
        est_m   = max(adult_16_18_m   - young_16_m,   0)
        est_f   = max(adult_16_18_f   - young_16_f,   0)

        est_reg, est_reg_m, est_reg_f = {}, {}, {}
        all_regions = set(list(adult_by_reg.keys()) + list(young_16_reg.keys()))
        for r in all_regions:
            est_reg[r]   = max(adult_by_reg.get(r, 0)   - young_16_reg.get(r, 0),   0)
            est_reg_m[r] = max(adult_by_reg_m.get(r, 0) - young_16_reg_m.get(r, 0), 0)
            est_reg_f[r] = max(adult_by_reg_f.get(r, 0) - young_16_reg_f.get(r, 0), 0)

        log.info("Adult %s: 16-18 weighted=%.0f, Young age-16=%.0f → 17-18 est=%.0f",
                 year, adult_16_18_all, young_16_all, est_all)

        estimates[year] = {
            "available": True,
            "overall": est_all, "male": est_m, "female": est_f,
            "adult_16_18_total": adult_16_18_all,
            "young_16_subtracted": young_16_all,
            "by_region": est_reg, "by_region_m": est_reg_m, "by_region_f": est_reg_f,
        }

    return estimates


# ══════════════════════════════════════════════════════════════════════════════
# 4.  Helpers
# ══════════════════════════════════════════════════════════════════════════════

def group_by_columns(dfs, years, groupby_cols, count_col):
    parts = {}
    for df, year in zip(dfs, years):
        parts[year] = df.groupby(groupby_cols)[count_col].sum()
    return pd.DataFrame(parts)

def _save(name):
    out = OUTPUT_DIR / f"{name}.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    log.info("Saved: %s", out.name)

def _fmt_thousands(ax, axis="y"):
    fmt = mticker.FuncFormatter(lambda x, _: f"{x:,.0f}")
    if axis in ("y", "both"): ax.yaxis.set_major_formatter(fmt)
    if axis in ("x", "both"): ax.xaxis.set_major_formatter(fmt)

def _rfu_national_totals(dfs, years):
    rows = []
    for df, y in zip(dfs, years):
        target_m = [c for c in RFU_AGE_COLUMNS if c.endswith("M") and c in df.columns]
        target_f = [c for c in RFU_AGE_COLUMNS if c.endswith("F") and c in df.columns]
        mt, ft = df[target_m].sum().sum(), df[target_f].sum().sum()
        rows.append({"Year": y, "Male": mt, "Female": ft, "Overall": mt + ft})
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# 5.  ALS VISUALISATIONS (improved)
# ══════════════════════════════════════════════════════════════════════════════

def viz_als_national(overall, males, females):
    """Dual-panel: overall bar+line  |  gender stacked area."""
    years = list(overall.keys())
    tot = [df["weighted_total"].sum() for df in overall.values()]
    m   = [df["weighted_total"].sum() for df in males.values()]
    f   = [df["weighted_total"].sum() for df in females.values()]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5),
                                    gridspec_kw={"wspace": 0.30})
    ax1.bar(years, tot, color=PAL["als"], alpha=0.35, width=0.55,
            edgecolor=PAL["als"], linewidth=0.8)
    ax1.plot(years, tot, "o-", color=PAL["als"], lw=2.2, zorder=5)
    for i, v in enumerate(tot):
        ax1.text(i, v + max(tot)*0.02, f"{v:,.0f}",
                 ha="center", fontsize=8.5, color=PAL["text"], fontweight="bold")
    ax1.set_title("A   Overall Weighted Rugby Union Participation (ALS)")
    ax1.set_ylabel("Weighted participants"); ax1.set_xlabel("Survey year")
    ax1.grid(axis="y", color=PAL["grid"], lw=0.6); _fmt_thousands(ax1)

    mf_sum = [a+b for a, b in zip(m, f)]
    ax2.fill_between(years, 0, m, alpha=0.30, color=PAL["male"], label="Male")
    ax2.fill_between(years, m, mf_sum, alpha=0.30, color=PAL["female"], label="Female")
    ax2.plot(years, m, "s-", color=PAL["male"], lw=2)
    ax2.plot(years, f, "^--", color=PAL["female"], lw=1.5, alpha=0.7,
             label="Female (standalone)")
    ax2.set_title("B   Gender Breakdown")
    ax2.set_ylabel("Weighted participants"); ax2.legend(fontsize=9)
    ax2.grid(axis="y", color=PAL["grid"], lw=0.6); _fmt_thousands(ax2)

    fig.suptitle("Active Lives Survey — Youth Rugby Union Participation",
                 y=1.02, fontsize=15, fontweight="bold")
    _save("als_01_national_trend")
    return pd.DataFrame({"Year": years, "Overall": tot, "Male": m, "Female": f})


def viz_als_region_heatmap(overall, years_als):
    ds = [overall[y] for y in years_als]
    reg = group_by_columns(ds, years_als, ["Region"], "weighted_total")
    reg = reg.sort_values(years_als[-1], ascending=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    data = reg.values
    im = ax.imshow(data, aspect="auto", cmap="YlOrRd")
    ax.set_xticks(range(len(years_als)));  ax.set_xticklabels(years_als, fontsize=10)
    ax.set_yticks(range(len(reg)));        ax.set_yticklabels(reg.index, fontsize=10)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data[i, j]
            c = "white" if v > data.max() * 0.65 else PAL["text"]
            ax.text(j, i, f"{v:,.0f}", ha="center", va="center", fontsize=8.5, color=c)
    ax.set_title("ALS Region × Year — Weighted Rugby Union Participation", pad=12)
    fig.colorbar(im, ax=ax, label="Weighted total", shrink=0.8)
    _save("als_02_region_heatmap")
    return reg


def viz_als_top_bottom_csp(regionwise, first, last, n=8):
    chg = regionwise[last] - regionwise[first]
    top = chg.nlargest(n); bot = chg.nsmallest(n)
    sel = pd.concat([top, bot]).sort_values()
    labels = [str(idx) if isinstance(idx, str)
              else " / ".join(str(x) for x in idx) for idx in sel.index]
    labels = [l[:42]+"…" if len(l) > 44 else l for l in labels]

    fig, ax = plt.subplots(figsize=(11, 7))
    colors = [PAL["rfu"] if v < 0 else PAL["als"] for v in sel.values]
    ax.barh(range(len(sel)), sel.values, color=colors, edgecolor="white", height=0.65)
    ax.set_yticks(range(len(sel))); ax.set_yticklabels(labels, fontsize=9)
    ax.axvline(0, color=PAL["text"], lw=0.8)
    ax.set_xlabel("Change in weighted participation")
    ax.set_title(f"ALS Rugby Union: Biggest Gainers & Losers by Region/CSP\n({first} → {last})", pad=10)
    ax.grid(axis="x", color=PAL["grid"], lw=0.5); _fmt_thousands(ax, "x")
    for bar, v in zip(ax.patches, sel.values):
        off = max(abs(sel).max() * 0.015, 5)
        ax.text(v + (off if v >= 0 else -off), bar.get_y()+bar.get_height()/2,
                f"{v:+,.0f}", va="center", ha="left" if v >= 0 else "right", fontsize=8)
    _save("als_03_csp_gainers_losers")


def viz_als_gender_ratio(overall, males, years_als):
    m_share = []
    for y in years_als:
        t = overall[y]["weighted_total"].sum()
        m_share.append(males[y]["weighted_total"].sum() / t * 100 if t else 0)
    f_share = [100 - ms for ms in m_share]

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(years_als, m_share, color=PAL["male"], label="Male %", width=0.55)
    ax.bar(years_als, f_share, bottom=m_share, color=PAL["female"],
           label="Female %", width=0.55)
    for i, (mv, fv) in enumerate(zip(m_share, f_share)):
        ax.text(i, mv/2, f"{mv:.1f}%", ha="center", va="center",
                fontsize=9, color="white", fontweight="bold")
        ax.text(i, mv+fv/2, f"{fv:.1f}%", ha="center", va="center",
                fontsize=9, color="white", fontweight="bold")
    ax.set_ylabel("Share (%)"); ax.set_ylim(0, 105)
    ax.set_title("ALS — Male vs Female Share of Youth Rugby Union", pad=10)
    ax.legend(loc="upper right")
    _save("als_04_gender_ratio")


# ══════════════════════════════════════════════════════════════════════════════
# 6.  RFU VISUALISATIONS (improved)
# ══════════════════════════════════════════════════════════════════════════════

def viz_rfu_national(dfs, years):
    t = _rfu_national_totals(dfs, years)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5),
                                    gridspec_kw={"wspace": 0.30})
    ax1.bar(t["Year"], t["Overall"], color=PAL["rfu"], alpha=0.35, width=0.55,
            edgecolor=PAL["rfu"], linewidth=0.8)
    ax1.plot(t["Year"], t["Overall"], "o-", color=PAL["rfu"], lw=2.2, zorder=5)
    for i, row in t.iterrows():
        ax1.text(i, row["Overall"]+t["Overall"].max()*0.02,
                 f"{row['Overall']:,.0f}", ha="center", fontsize=8.5,
                 color=PAL["text"], fontweight="bold")
    ax1.set_title("A   Total Club-Registered Rugby Union Players (U7–U18)")
    ax1.set_ylabel("Registered players"); ax1.tick_params(axis="x", rotation=35)
    ax1.grid(axis="y", color=PAL["grid"], lw=0.6); _fmt_thousands(ax1)

    ax2.fill_between(range(len(t)), 0, t["Male"], alpha=0.30, color=PAL["male"])
    ax2.fill_between(range(len(t)), t["Male"], t["Overall"], alpha=0.30, color=PAL["female"])
    ax2.plot(range(len(t)), t["Male"], "s-", color=PAL["male"], lw=2, label="Male")
    ax2.plot(range(len(t)), t["Female"], "^--", color=PAL["female"], lw=2, label="Female")
    ax2.set_xticks(range(len(t))); ax2.set_xticklabels(t["Year"], rotation=35)
    ax2.set_title("B   Gender Breakdown (RFU)")
    ax2.set_ylabel("Registered players"); ax2.legend(fontsize=9)
    ax2.grid(axis="y", color=PAL["grid"], lw=0.6); _fmt_thousands(ax2)

    fig.suptitle("RFU Club Registration — Youth Rugby Union Players (U7–U18)",
                 y=1.02, fontsize=15, fontweight="bold")
    _save("rfu_01_national_trend")
    return t


def viz_rfu_age_pyramid(dfs, years):
    df = dfs[-1]
    age_groups = [f"U{i}" for i in range(7, 19)]  # U7–U18
    m_vals = [df[f"{ag}M"].sum() if f"{ag}M" in df.columns else 0 for ag in age_groups]
    f_vals = [df[f"{ag}F"].sum() if f"{ag}F" in df.columns else 0 for ag in age_groups]

    fig, ax = plt.subplots(figsize=(10, 6))
    y_pos = np.arange(len(age_groups))
    ax.barh(y_pos, [-v for v in m_vals], height=0.65, color=PAL["male"], alpha=0.85, label="Male")
    ax.barh(y_pos, f_vals, height=0.65, color=PAL["female"], alpha=0.85, label="Female")
    ax.set_yticks(y_pos); ax.set_yticklabels(age_groups)
    ax.set_xlabel("Number of players")
    ax.set_title(f"RFU Age-Gender Pyramid — {years[-1]}", pad=10)
    ax.legend(loc="lower right"); ax.axvline(0, color=PAL["text"], lw=0.8)
    for i, (mv, fv) in enumerate(zip(m_vals, f_vals)):
        ax.text(-mv - max(m_vals)*0.03, i, f"{mv:,.0f}", va="center", ha="right",
                fontsize=8, color=PAL["male"])
        ax.text(fv + max(f_vals)*0.03, i, f"{fv:,.0f}", va="center", ha="left",
                fontsize=8, color=PAL["female"])
    xabs = max(max(m_vals), max(f_vals)) * 1.25
    ax.set_xlim(-xabs, xabs)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{abs(x):,.0f}"))
    ax.grid(axis="x", color=PAL["grid"], lw=0.5)
    _save("rfu_02_age_pyramid")


def viz_rfu_cb_heatmap(dfs, years):
    region_df = group_by_columns(dfs, years, ["Constituent Body"], "count_col")
    region_df = region_df[(region_df != 0).all(axis=1)]
    region_df = region_df.sort_values(years[-1], ascending=True)

    fig, ax = plt.subplots(figsize=(12, max(8, len(region_df)*0.35)))
    data = region_df.values
    im = ax.imshow(data, aspect="auto", cmap="YlGnBu")
    ax.set_xticks(range(len(years))); ax.set_xticklabels(years, fontsize=9, rotation=30)
    ax.set_yticks(range(len(region_df))); ax.set_yticklabels(region_df.index, fontsize=8)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data[i, j]
            c = "white" if v > data.max()*0.6 else PAL["text"]
            ax.text(j, i, f"{v:,.0f}", ha="center", va="center", fontsize=7, color=c)
    ax.set_title("RFU CB × Year — Registered Rugby Union Players (U7–U18)", pad=12)
    fig.colorbar(im, ax=ax, label="Total players", shrink=0.6)
    _save("rfu_03_cb_heatmap")
    return region_df


def viz_rfu_top_bottom_cb(dfs, years, n=8):
    region_df = group_by_columns(dfs, years, ["Constituent Body"], "count_col")
    region_df = region_df[(region_df != 0).all(axis=1)]
    first, last = years[0], years[-1]
    chg = region_df[last] - region_df[first]
    sel = pd.concat([chg.nlargest(n), chg.nsmallest(n)]).sort_values()

    fig, ax = plt.subplots(figsize=(11, 7))
    colors = [PAL["rfu"] if v < 0 else PAL["green"] for v in sel.values]
    ax.barh(range(len(sel)), sel.values, color=colors, edgecolor="white", height=0.65)
    ax.set_yticks(range(len(sel))); ax.set_yticklabels([str(x)[:45] for x in sel.index], fontsize=9)
    ax.axvline(0, color=PAL["text"], lw=0.8)
    ax.set_xlabel("Change in registered players")
    ax.set_title(f"RFU: Biggest Gainers & Losers by CB\n({first} → {last})", pad=10)
    ax.grid(axis="x", color=PAL["grid"], lw=0.5); _fmt_thousands(ax, "x")
    for bar, v in zip(ax.patches, sel.values):
        off = max(abs(sel).max()*0.015, 10)
        ax.text(v+(off if v >= 0 else -off), bar.get_y()+bar.get_height()/2,
                f"{v:+,.0f}", va="center", ha="left" if v >= 0 else "right", fontsize=8)
    _save("rfu_04_cb_gainers_losers")


# ══════════════════════════════════════════════════════════════════════════════
# 7.  ★  COMPARISON / GAP ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def _build_comparison_df(als_overall, als_males, als_females,
                         rfu_dfs, rfu_years, adult_17_18=None):
    """
    Build master comparison with aligned ALS/RFU national totals.

    Three tiers:
      • Core 7–16: ALS ages 7–16 vs RFU U7–U16
      • 17–18 supplement: ALS Adult 17–18 estimate vs RFU U17+U18
      • Combined 7–18: sum of both tiers
    """
    rfu_lookup = dict(zip(rfu_years, rfu_dfs))
    if adult_17_18 is None:
        adult_17_18 = {}

    rfu_overlap_ages = [c for c in RFU_AGE_COLUMNS
                        if int(c[1:-1]) <= int(ALS_AGE_MAX)]
    rfu_1718_ages    = [c for c in RFU_AGE_COLUMNS
                        if int(c[1:-1]) in (17, 18)]
    rfu_all_m   = [c for c in RFU_AGE_COLUMNS if c.endswith("M")]
    rfu_all_f   = [c for c in RFU_AGE_COLUMNS if c.endswith("F")]
    rfu_ovlp_m  = [c for c in rfu_overlap_ages if c.endswith("M")]
    rfu_ovlp_f  = [c for c in rfu_overlap_ages if c.endswith("F")]
    rfu_1718_m  = [c for c in rfu_1718_ages if c.endswith("M")]
    rfu_1718_f  = [c for c in rfu_1718_ages if c.endswith("F")]

    rows = []
    for label, als_y, rfu_y in YEAR_ALIGNMENT:
        adf = als_overall[als_y]
        rdf = rfu_lookup[rfu_y]

        # ALS core 7–16
        age_num = pd.to_numeric(adf["Age"], errors="coerce")
        als_filt = adf[(age_num >= ALS_AGE_MIN) & (age_num <= ALS_AGE_MAX)]
        als_t = als_filt["weighted_total"].sum()
        als_m = als_filt.loc[als_filt[GENDER_COL] == 1, "weighted_total"].sum()
        als_f = als_filt.loc[als_filt[GENDER_COL] == 2, "weighted_total"].sum()

        # RFU full U7–U18
        av_m = [c for c in rfu_all_m if c in rdf.columns]
        av_f = [c for c in rfu_all_f if c in rdf.columns]
        rfu_t = rdf[av_m + av_f].sum().sum()
        rfu_m = rdf[av_m].sum().sum()
        rfu_f = rdf[av_f].sum().sum()

        # RFU overlap U7–U16
        ov_m = [c for c in rfu_ovlp_m if c in rdf.columns]
        ov_f = [c for c in rfu_ovlp_f if c in rdf.columns]
        rfu_ov   = rdf[ov_m + ov_f].sum().sum()
        rfu_ov_m = rdf[ov_m].sum().sum()
        rfu_ov_f = rdf[ov_f].sum().sum()

        # RFU U17+U18
        r17_m = [c for c in rfu_1718_m if c in rdf.columns]
        r17_f = [c for c in rfu_1718_f if c in rdf.columns]
        rfu_17_18   = rdf[r17_m + r17_f].sum().sum()
        rfu_17_18_m = rdf[r17_m].sum().sum()
        rfu_17_18_f = rdf[r17_f].sum().sum()

        # ALS Adult 17–18 estimate
        est = adult_17_18.get(als_y, {})
        has_1718 = est.get("available", False)
        als_17_18   = est.get("overall", 0) if has_1718 else np.nan
        als_17_18_m = est.get("male", 0)    if has_1718 else np.nan
        als_17_18_f = est.get("female", 0)  if has_1718 else np.nan

        # Combined 7–18
        als_combined   = als_t + (als_17_18 if has_1718 else 0)
        als_combined_m = als_m + (als_17_18_m if has_1718 else 0)
        als_combined_f = als_f + (als_17_18_f if has_1718 else 0)

        rows.append({
            "Period": label, "ALS_Year": als_y, "RFU_Year": rfu_y,
            "Has_17_18": has_1718,
            # Core 7-16
            "ALS_7_16": als_t, "ALS_7_16_M": als_m, "ALS_7_16_F": als_f,
            "RFU_U7_U16": rfu_ov, "RFU_U7_U16_M": rfu_ov_m, "RFU_U7_U16_F": rfu_ov_f,
            # 17-18 layer
            "ALS_17_18": als_17_18, "ALS_17_18_M": als_17_18_m, "ALS_17_18_F": als_17_18_f,
            "RFU_U17_U18": rfu_17_18, "RFU_U17_U18_M": rfu_17_18_m, "RFU_U17_U18_F": rfu_17_18_f,
            # Combined 7-18
            "ALS_7_18": als_combined, "ALS_7_18_M": als_combined_m, "ALS_7_18_F": als_combined_f,
            "RFU_U7_U18": rfu_t, "RFU_U7_U18_M": rfu_m, "RFU_U7_U18_F": rfu_f,
            # ★ Backward-compat aliases → ALL point to 7-18 combined (primary view)
            "ALS_Overall": als_combined, "ALS_Male": als_combined_m, "ALS_Female": als_combined_f,
            "RFU_Overlap": rfu_t, "RFU_Overlap_M": rfu_m, "RFU_Overlap_F": rfu_f,
            "RFU_Overall": rfu_t,
        })

    df = pd.DataFrame(rows)
    # ★ PRIMARY gaps/capture = combined 7-18 (ALS 7-18 vs RFU U7-U18)
    df["Gap_Overall"] = df["ALS_7_18"] - df["RFU_U7_U18"]
    df["Gap_Male"]    = df["ALS_7_18_M"] - df["RFU_U7_U18_M"]
    df["Gap_Female"]  = df["ALS_7_18_F"] - df["RFU_U7_U18_F"]
    df["Capture_%"]   = np.where(df["ALS_7_18"] > 0,
                                  df["RFU_U7_U18"] / df["ALS_7_18"] * 100, np.nan)
    df["Capture_%_M"] = np.where(df["ALS_7_18_M"] > 0,
                                  df["RFU_U7_U18_M"] / df["ALS_7_18_M"] * 100, np.nan)
    df["Capture_%_F"] = np.where(df["ALS_7_18_F"] > 0,
                                  df["RFU_U7_U18_F"] / df["ALS_7_18_F"] * 100, np.nan)
    # Core 7-16 gaps (secondary — kept for reference)
    df["Gap_7_16"]      = df["ALS_7_16"] - df["RFU_U7_U16"]
    df["Capture_%_7_16"] = df["RFU_U7_U16"] / df["ALS_7_16"] * 100
    # 17-18 gaps
    df["Gap_17_18"]   = df["ALS_17_18"] - df["RFU_U17_U18"]
    df["Gap_17_18_M"] = df["ALS_17_18_M"] - df["RFU_U17_U18_M"]
    df["Gap_17_18_F"] = df["ALS_17_18_F"] - df["RFU_U17_U18_F"]
    # Combined 7-18 (aliases for clarity in combined-specific code)
    df["Gap_7_18"]      = df["Gap_Overall"]
    df["Gap_7_18_M"]    = df["Gap_Male"]
    df["Gap_7_18_F"]    = df["Gap_Female"]
    df["Capture_%_7_18"]   = df["Capture_%"]
    df["Capture_%_7_18_M"] = df["Capture_%_M"]
    df["Capture_%_7_18_F"] = df["Capture_%_F"]
    return df


_GAP_FOOTNOTE = (
    "ALS ages 7–18 (Rugby Union estimates). 2022-23 uses union-specific column; "
    "older years corrected using 2022-23 union/all-rugby proportion. "
    "17–18 from Adult survey (RUGBYUNION) where available. RFU = club registrations U7–U18."
)

def viz_gap_national(comp):
    """Side-by-side bars with gap annotation — ALS 7–18 vs RFU U7–U18."""
    fig, ax = plt.subplots(figsize=(12, 6.5))
    x = np.arange(len(comp)); w = 0.32
    ax.bar(x-w/2, comp["ALS_Overall"], w, color=PAL["als"], alpha=0.85,
           label="ALS Rugby Union est. (7–18)", edgecolor="white")
    ax.bar(x+w/2, comp["RFU_Overlap"], w, color=PAL["rfu"], alpha=0.85,
           label="RFU Club Registered (U7–U18)", edgecolor="white")
    for i, row in comp.iterrows():
        gap = row["Gap_Overall"]; mid = (row["ALS_Overall"]+row["RFU_Overlap"])/2
        ax.annotate(f"Gap\n{gap:,.0f}", xy=(i, mid), fontsize=8.5, ha="center",
                    va="center", color=PAL["gap"], fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.3", fc=PAL["gap_fill"],
                              ec=PAL["gap"], alpha=0.85))
    ax.set_xticks(x); ax.set_xticklabels(comp["Period"], fontsize=10)
    ax.set_ylabel("Number of young people")
    ax.set_title("ALS Rugby Union Estimate (7–18) vs RFU Registrations (U7–U18)", pad=12)
    ax.legend(fontsize=10); ax.grid(axis="y", color=PAL["grid"], lw=0.6); _fmt_thousands(ax)
    fig.text(0.5, -0.02, _GAP_FOOTNOTE, ha="center", fontsize=8, color="#6B7280", style="italic")
    _save("gap_01_national_comparison")


def viz_capture_rate(comp):
    """Line chart: % captured by clubs."""
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(comp["Period"], comp["Capture_%"], "o-", color=PAL["gap"], lw=2.5, ms=9,
            zorder=5, label="Overall")
    ax.plot(comp["Period"], comp["Capture_%_M"], "s--", color=PAL["male"], lw=2, ms=7,
            label="Male")
    ax.plot(comp["Period"], comp["Capture_%_F"], "^--", color=PAL["female"], lw=2, ms=7,
            label="Female")
    ax.fill_between(comp["Period"], 0, comp["Capture_%"], alpha=0.10, color=PAL["gap"])
    for i, row in comp.iterrows():
        ax.text(i, row["Capture_%"]+1.5, f"{row['Capture_%']:.1f}%",
                ha="center", fontsize=9, color=PAL["gap"], fontweight="bold")
    ax.set_ylabel("Club capture rate (%)")
    ax.set_title("What % of ALS Rugby Union Players (7–18) Are RFU Club-Registered (U7–U18)?", pad=12)
    ax.legend(fontsize=10); ax.grid(axis="y", color=PAL["grid"], lw=0.6)
    ax.set_ylim(0, max(comp[["Capture_%", "Capture_%_M", "Capture_%_F"]].max()) * 1.25)
    fig.text(0.5, -0.02, _GAP_FOOTNOTE, ha="center", fontsize=8, color="#6B7280", style="italic")
    _save("gap_02_capture_rate")


def viz_hidden_rugby(comp):
    """Stacked bar: club-registered vs non-club (7–18 combined)."""
    fig, ax = plt.subplots(figsize=(12, 6.5))
    x = np.arange(len(comp)); w = 0.50
    ax.bar(x, comp["RFU_Overlap"], w, color=PAL["rfu"], alpha=0.80,
           label="Club-registered (RFU U7–U18)", edgecolor="white")
    # Only stack positive gaps
    pos_gap = comp["Gap_Overall"].clip(lower=0)
    ax.bar(x, pos_gap, w, bottom=comp["RFU_Overlap"],
           color=PAL["gap"], alpha=0.65,
           label="Non-club / informal ('hidden rugby union')", edgecolor="white")
    for i, row in comp.iterrows():
        ax.text(i, row["RFU_Overlap"]/2, f"{row['RFU_Overlap']:,.0f}",
                ha="center", va="center", fontsize=8.5, color="white", fontweight="bold")
        gap = row["Gap_Overall"]
        if gap > 0:
            gap_mid = row["RFU_Overlap"] + gap/2
            ax.text(i, gap_mid, f"{gap:,.0f}",
                    ha="center", va="center", fontsize=8.5, color="white", fontweight="bold")
        ax.text(i, row["ALS_Overall"]+comp["ALS_Overall"].max()*0.015,
                f"ALS: {row['ALS_Overall']:,.0f}", ha="center", fontsize=8, color=PAL["text"])
    ax.set_xticks(x); ax.set_xticklabels(comp["Period"])
    ax.set_ylabel("Young people")
    ax.set_title("Decomposing Youth Rugby Union: Club-Registered vs Non-Club Participation",
                 pad=12, fontsize=14)
    ax.legend(fontsize=10, loc="upper right")
    ax.grid(axis="y", color=PAL["grid"], lw=0.6); _fmt_thousands(ax)
    fig.text(0.5, -0.02, _GAP_FOOTNOTE, ha="center", fontsize=8, color="#6B7280", style="italic")
    _save("gap_03_hidden_rugby")


def viz_gender_gap(comp):
    """Male and female gaps side by side (7–18 combined)."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.5), gridspec_kw={"wspace": 0.28})
    for ax, gl, ca, cr, cg, pal in [
        (axes[0], "Male",   "ALS_Male",   "RFU_Overlap_M", "Gap_Male",   PAL["male"]),
        (axes[1], "Female", "ALS_Female", "RFU_Overlap_F", "Gap_Female", PAL["female"]),
    ]:
        x = np.arange(len(comp)); w = 0.32
        ax.bar(x-w/2, comp[ca], w, color=PAL["als"], alpha=0.80,
               label=f"ALS ({gl}, 7–18)", edgecolor="white")
        ax.bar(x+w/2, comp[cr], w, color=pal, alpha=0.80,
               label=f"RFU ({gl}, U7–U18)", edgecolor="white")
        for i, row in comp.iterrows():
            ax.annotate(f"Δ {row[cg]:,.0f}",
                        xy=(i, max(row[ca], row[cr])*1.04),
                        fontsize=8, ha="center", color=PAL["gap"], fontweight="bold")
        ax.set_xticks(x); ax.set_xticklabels(comp["Period"], fontsize=9)
        ax.set_title(f"{gl} — ALS vs RFU"); ax.set_ylabel("Participants")
        ax.legend(fontsize=9); ax.grid(axis="y", color=PAL["grid"], lw=0.6); _fmt_thousands(ax)
    fig.suptitle("Gender-Specific Gap: Rugby Union Survey Estimates vs Club Registrations",
                 y=1.02, fontsize=14, fontweight="bold")
    fig.text(0.5, -0.02, _GAP_FOOTNOTE, ha="center", fontsize=8, color="#6B7280", style="italic")
    _save("gap_04_gender_gap")


# ── Plot C5: Combined 7–18 comparison (stacked: core + 17-18 layer) ──

def viz_combined_7_18(comp):
    """
    Three-panel figure showing:
      A) Stacked bar: ALS 7–16 + ALS 17–18 estimate vs RFU U7–U18
      B) Capture rate: core 7–16 vs combined 7–18
      C) 17–18 age band zoom: ALS vs RFU side by side
    """
    # Only show years where 17-18 data is available
    has = comp[comp["Has_17_18"]].copy().reset_index(drop=True)
    if has.empty:
        log.warning("No years with 17–18 Adult data — skipping combined viz.")
        return

    fig, axes = plt.subplots(1, 3, figsize=(20, 6.5),
                              gridspec_kw={"wspace": 0.32})

    # ── Panel A: Stacked ALS vs RFU ──
    ax = axes[0]
    x = np.arange(len(has)); w = 0.32

    # ALS stacked: 7-16 (blue) + 17-18 (light blue)
    ax.bar(x - w/2, has["ALS_7_16"], w, color=PAL["als"], alpha=0.85,
           label="ALS 7–16", edgecolor="white")
    ax.bar(x - w/2, has["ALS_17_18"], w, bottom=has["ALS_7_16"],
           color="#93C5FD", alpha=0.85, label="ALS 17–18 (est.)", edgecolor="white")

    # RFU stacked: U7-U16 (red) + U17-U18 (light red)
    ax.bar(x + w/2, has["RFU_U7_U16"], w, color=PAL["rfu"], alpha=0.85,
           label="RFU U7–U16", edgecolor="white")
    ax.bar(x + w/2, has["RFU_U17_U18"], w, bottom=has["RFU_U7_U16"],
           color="#FCA5A5", alpha=0.85, label="RFU U17–U18", edgecolor="white")

    # Gap annotation
    for i, row in has.iterrows():
        gap = row["Gap_7_18"]
        top = max(row["ALS_7_18"], row["RFU_U7_U18"])
        ax.text(i, top + top*0.02, f"Gap: {gap:,.0f}",
                ha="center", fontsize=8, color=PAL["gap"], fontweight="bold")

    ax.set_xticks(x); ax.set_xticklabels(has["Period"], fontsize=9)
    ax.set_ylabel("Participants"); ax.set_title("A   Full 7–18 Comparison")
    ax.legend(fontsize=7.5, loc="upper right")
    ax.grid(axis="y", color=PAL["grid"], lw=0.6); _fmt_thousands(ax)

    # ── Panel B: Capture rate comparison ──
    ax = axes[1]
    ax.plot(has["Period"], has["Capture_%"], "o-", color=PAL["als"],
            lw=2.2, ms=8, label="Core 7–16")
    ax.plot(has["Period"], has["Capture_%_7_18"], "s--", color=PAL["gap"],
            lw=2.2, ms=8, label="Combined 7–18")
    for i, row in has.iterrows():
        ax.text(i, row["Capture_%"] + 1, f"{row['Capture_%']:.1f}%",
                ha="center", fontsize=8, color=PAL["als"])
        ax.text(i, row["Capture_%_7_18"] - 2.5, f"{row['Capture_%_7_18']:.1f}%",
                ha="center", fontsize=8, color=PAL["gap"])
    ax.set_ylabel("Capture rate (%)")
    ax.set_title("B   Capture Rate: Core vs Combined")
    ax.legend(fontsize=9); ax.grid(axis="y", color=PAL["grid"], lw=0.6)

    # ── Panel C: 17–18 zoom ──
    ax = axes[2]
    w2 = 0.30
    ax.bar(x - w2/2, has["ALS_17_18"], w2, color=PAL["als"], alpha=0.85,
           label="ALS 17–18 (est.)", edgecolor="white")
    ax.bar(x + w2/2, has["RFU_U17_U18"], w2, color=PAL["rfu"], alpha=0.85,
           label="RFU U17–U18", edgecolor="white")
    for i, row in has.iterrows():
        gap = row["Gap_17_18"]
        if not np.isnan(gap):
            top = max(row["ALS_17_18"], row["RFU_U17_U18"])
            ax.text(i, top + top*0.04, f"Δ {gap:,.0f}",
                    ha="center", fontsize=8.5, color=PAL["gap"], fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(has["Period"], fontsize=9)
    ax.set_ylabel("Participants"); ax.set_title("C   17–18 Age Band Zoom")
    ax.legend(fontsize=9); ax.grid(axis="y", color=PAL["grid"], lw=0.6)
    _fmt_thousands(ax)

    fig.suptitle("ALS Rugby Union (7–18) vs RFU (U7–U18) — Full Youth Pipeline",
                 y=1.02, fontsize=15, fontweight="bold")
    note = ("ALS 17–18 estimated from Adult survey 16–18 band minus Young age-16. "
            "ALS uses all-rugby; RFU uses Rugby Union clubs only.")
    fig.text(0.5, -0.02, note, ha="center", fontsize=8, color="#6B7280", style="italic")
    _save("gap_15_combined_7_18")


def viz_combined_summary_table(comp):
    """Save a clear summary table of both tiers to CSV and log."""
    cols = ["Period", "Has_17_18",
            "ALS_7_16", "RFU_U7_U16", "Gap_Overall", "Capture_%",
            "ALS_17_18", "RFU_U17_U18", "Gap_17_18",
            "ALS_7_18", "RFU_U7_U18", "Gap_7_18", "Capture_%_7_18"]
    summary = comp[[c for c in cols if c in comp.columns]].copy()
    summary.to_csv(OUTPUT_DIR / "comparison_combined_7_18.csv", index=False)
    log.info("Combined 7–18 summary:\n%s", summary.to_string(index=False))


def viz_regional_comparison(als_overall, rfu_dfs, rfu_years, adult_17_18=None):
    """Regional capture-rate heatmap + gap bar chart — ALS 7–18 vs RFU U7–U18."""
    rfu_lookup = dict(zip(rfu_years, rfu_dfs))
    if adult_17_18 is None:
        adult_17_18 = {}

    rfu_all = RFU_AGE_COLUMNS  # full U7–U18

    als_rows, rfu_rows = [], []
    for label, als_y, rfu_y in YEAR_ALIGNMENT:
        # ALS 7–16 by region
        adf = als_overall[als_y].copy()
        age_num = pd.to_numeric(adf["Age"], errors="coerce")
        adf = adf[(age_num >= ALS_AGE_MIN) & (age_num <= ALS_AGE_MAX)]
        a_reg = adf.groupby("Region")["weighted_total"].sum()

        # Add Adult 17-18 regional estimates
        est = adult_17_18.get(als_y, {})
        est_reg = est.get("by_region", {}) if est.get("available", False) else {}

        for reg, val in a_reg.items():
            als_rows.append({"Period": label, "Region": reg,
                             "ALS": val + est_reg.get(reg, 0)})

        # RFU full U7–U18
        rdf = rfu_lookup[rfu_y].copy()
        if "Constituent Body" not in rdf.columns and rdf.index.name == "Constituent Body":
            rdf = rdf.reset_index()
        if "Constituent Body" in rdf.columns:
            avail = [c for c in rfu_all if c in rdf.columns]
            rdf["_rfu_all"] = rdf[avail].sum(axis=1)
            rdf["_region"] = rdf["Constituent Body"].map(CB_TO_REGION)
            rdf = rdf.dropna(subset=["_region"])
            for reg, val in rdf.groupby("_region")["_rfu_all"].sum().items():
                rfu_rows.append({"Period": label, "Region": reg, "RFU": val})

    merged = pd.DataFrame(als_rows).merge(pd.DataFrame(rfu_rows),
                                           on=["Period", "Region"], how="inner")
    merged["Gap"] = merged["ALS"] - merged["RFU"]
    merged["Capture_%"] = np.where(merged["ALS"] > 0,
                                    merged["RFU"] / merged["ALS"] * 100, np.nan)

    _AGE_NOTE = "ALS ages 7–18 vs RFU U7–U18"

    # ── Heatmap ──
    pivot = merged.pivot_table(index="Region", columns="Period",
                               values="Capture_%", aggfunc="first")
    pivot = pivot.loc[pivot.mean(axis=1).sort_values().index]

    fig, ax = plt.subplots(figsize=(11, 6.5))
    data = pivot.values
    im = ax.imshow(data, aspect="auto", cmap="RdYlGn", vmin=0,
                   vmax=min(np.nanmax(data)*1.1, 200))
    ax.set_xticks(range(pivot.shape[1])); ax.set_xticklabels(pivot.columns, fontsize=10)
    ax.set_yticks(range(pivot.shape[0])); ax.set_yticklabels(pivot.index, fontsize=10)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data[i, j]
            if np.isnan(v): continue
            c = "white" if v < 40 or v > 150 else PAL["text"]
            ax.text(j, i, f"{v:.0f}%", ha="center", va="center",
                    fontsize=9.5, fontweight="bold", color=c)
    ax.set_title("Regional Club Capture Rate (RFU ÷ ALS × 100)\n"
                 f"Lower = more non-club rugby union  |  {_AGE_NOTE}", pad=14)
    fig.colorbar(im, ax=ax, label="Capture rate (%)", shrink=0.7)
    _save("gap_05_regional_capture_heatmap")

    # ── Bar chart: latest-year gap ──
    latest_label = YEAR_ALIGNMENT[-1][0]
    latest = merged[merged["Period"] == latest_label].sort_values("Gap", ascending=True)

    fig, ax = plt.subplots(figsize=(11, 6))
    colors = [PAL["gap"] if g > 0 else PAL["green"] for g in latest["Gap"]]
    ax.barh(latest["Region"], latest["Gap"], color=colors, height=0.6, edgecolor="white")
    ax.axvline(0, color=PAL["text"], lw=0.8)
    ax.set_xlabel("ALS − RFU (non-club participation estimate)")
    ax.set_title(f"Regional Non-Club Rugby Union Estimate — {latest_label}\n{_AGE_NOTE}", pad=12)
    ax.grid(axis="x", color=PAL["grid"], lw=0.5); _fmt_thousands(ax, "x")
    for bar, v in zip(ax.patches, latest["Gap"]):
        off = max(abs(latest["Gap"]).max()*0.02, 10)
        ax.text(v+(off if v >= 0 else -off), bar.get_y()+bar.get_height()/2,
                f"{v:,.0f}", va="center", ha="left" if v >= 0 else "right",
                fontsize=9, fontweight="bold")
    _save("gap_06_regional_gap_bars")
    return merged


def viz_scouting_opportunity(comp, regional):
    """Scouting Opportunity Index by region."""
    latest_label = YEAR_ALIGNMENT[-1][0]
    latest = regional[regional["Period"] == latest_label].copy()
    if latest.empty:
        log.warning("No regional data for scouting analysis."); return None

    gap_max = latest["Gap"].clip(lower=0).max()
    if gap_max == 0: gap_max = 1
    latest["Opportunity_Score"] = (
        latest["Gap"].clip(lower=0) / gap_max * 50 +
        (100 - latest["Capture_%"].clip(upper=100)) / 100 * 50
    )
    latest = latest.sort_values("Opportunity_Score", ascending=True)

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.barh(latest["Region"], latest["Opportunity_Score"],
            color=PAL["gap"], alpha=0.8, height=0.6, edgecolor="white")
    for i, (_, row) in enumerate(latest.iterrows()):
        txt = f"Gap: {row['Gap']:,.0f}  |  Capture: {row['Capture_%']:.0f}%"
        ax.text(row["Opportunity_Score"]+1.2, i, txt,
                va="center", fontsize=8.5, color=PAL["text"])
    ax.set_xlabel("Scouting Opportunity Index (higher = more untapped potential)")
    ax.set_title(f"Rugby Union Scouting & Recruitment Opportunity by Region — {latest_label}",
                 pad=12, fontsize=13)
    ax.grid(axis="x", color=PAL["grid"], lw=0.5)
    ax.set_xlim(0, latest["Opportunity_Score"].max()*1.45)
    _save("gap_07_scouting_opportunity")
    return latest


# ── Extended regional builder (with gender) ──

def _build_regional_df(als_overall, als_males, als_females,
                       rfu_dfs, rfu_years, adult_17_18=None):
    """
    Region × period table: ALS 7–18 (Young + Adult 17-18 est.) vs RFU U7–U18.
    """
    rfu_lookup = dict(zip(rfu_years, rfu_dfs))
    if adult_17_18 is None:
        adult_17_18 = {}

    rfu_all_m = [c for c in RFU_AGE_COLUMNS if c.endswith("M")]
    rfu_all_f = [c for c in RFU_AGE_COLUMNS if c.endswith("F")]

    rows = []
    for label, als_y, rfu_y in YEAR_ALIGNMENT:
        # ALS 7–16 by region
        adf = als_overall[als_y].copy()
        age_num = pd.to_numeric(adf["Age"], errors="coerce")
        adf = adf[(age_num >= ALS_AGE_MIN) & (age_num <= ALS_AGE_MAX)]

        a_all = adf.groupby("Region")["weighted_total"].sum()
        a_m   = adf[adf[GENDER_COL] == 1].groupby("Region")["weighted_total"].sum()
        a_f   = adf[adf[GENDER_COL] == 2].groupby("Region")["weighted_total"].sum()

        # Add Adult 17-18 regional estimates
        est = adult_17_18.get(als_y, {})
        has_1718 = est.get("available", False)
        est_reg   = est.get("by_region", {})   if has_1718 else {}
        est_reg_m = est.get("by_region_m", {}) if has_1718 else {}
        est_reg_f = est.get("by_region_f", {}) if has_1718 else {}

        # RFU full U7–U18
        rdf = rfu_lookup[rfu_y].copy()
        if "Constituent Body" not in rdf.columns and rdf.index.name == "Constituent Body":
            rdf = rdf.reset_index()
        if "Constituent Body" not in rdf.columns:
            continue
        rdf["_region"] = rdf["Constituent Body"].map(CB_TO_REGION)
        rdf = rdf.dropna(subset=["_region"])

        am = [c for c in rfu_all_m if c in rdf.columns]
        af = [c for c in rfu_all_f if c in rdf.columns]
        rdf["_rfu"]   = rdf[am + af].sum(axis=1)
        rdf["_rfu_m"] = rdf[am].sum(axis=1)
        rdf["_rfu_f"] = rdf[af].sum(axis=1)

        r_all = rdf.groupby("_region")["_rfu"].sum()
        r_m   = rdf.groupby("_region")["_rfu_m"].sum()
        r_f   = rdf.groupby("_region")["_rfu_f"].sum()

        for reg in a_all.index:
            if reg not in r_all.index:
                continue
            als_reg   = a_all.get(reg, 0) + est_reg.get(reg, 0)
            als_reg_m = a_m.get(reg, 0)   + est_reg_m.get(reg, 0)
            als_reg_f = a_f.get(reg, 0)   + est_reg_f.get(reg, 0)
            rows.append({
                "Period": label, "Region": reg,
                "ALS":   als_reg,            "RFU":   r_all.get(reg, 0),
                "ALS_M": als_reg_m,          "RFU_M": r_m.get(reg, 0),
                "ALS_F": als_reg_f,          "RFU_F": r_f.get(reg, 0),
            })

    df = pd.DataFrame(rows)
    df["Gap"]       = df["ALS"]   - df["RFU"]
    df["Gap_M"]     = df["ALS_M"] - df["RFU_M"]
    df["Gap_F"]     = df["ALS_F"] - df["RFU_F"]
    df["Capture_%"] = np.where(df["ALS"] > 0, df["RFU"] / df["ALS"] * 100, np.nan)
    return df


# ── Plot G1: Small-multiples — ALS vs RFU per region over time ──

def viz_geo_faceted_gap(regional):
    """
    One subplot per region: ALS line vs RFU line with the gap shaded.
    Immediately shows the scale and direction of the gap in every region.
    """
    regions = sorted(regional["Region"].unique())
    n = len(regions)
    ncols = 3
    nrows = int(np.ceil(n / ncols))

    fig, axes = plt.subplots(nrows, ncols, figsize=(5.5 * ncols, 4.2 * nrows),
                              sharex=True)
    axes = axes.flatten()

    for i, region in enumerate(regions):
        ax = axes[i]
        sub = regional[regional["Region"] == region].sort_values("Period")

        ax.fill_between(sub["Period"], sub["RFU"], sub["ALS"],
                        alpha=0.22, color=PAL["gap"], label="Gap (non-club rugby union)")
        ax.plot(sub["Period"], sub["ALS"], "o-", color=PAL["als"], lw=2,
                ms=6, label="ALS")
        ax.plot(sub["Period"], sub["RFU"], "s-", color=PAL["rfu"], lw=2,
                ms=6, label="RFU")

        ax.set_title(region, fontsize=11, fontweight="bold")
        ax.tick_params(axis="x", rotation=40, labelsize=8)
        ax.grid(axis="y", color=PAL["grid"], lw=0.5)
        _fmt_thousands(ax)

        # Annotate latest gap
        last = sub.iloc[-1]
        ax.text(len(sub)-1, (last["ALS"] + last["RFU"]) / 2,
                f"Δ {last['Gap']:,.0f}", fontsize=8, ha="center",
                color=PAL["gap"], fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=PAL["gap"], alpha=0.8))

    # Legend on first subplot
    axes[0].legend(fontsize=7.5, loc="upper left")

    # Hide empty subplots
    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle("ALS vs RFU Rugby Union — Year-by-Year Regional Gap",
                 y=1.01, fontsize=16, fontweight="bold")
    fig.tight_layout()
    _save("gap_09_geo_faceted_gap")


# ── Plot G2: Absolute gap heatmap (Region × Year) ──

def viz_geo_gap_heatmap(regional):
    """
    Annotated heatmap: actual gap (ALS − RFU) for every region and period.
    Darker purple = larger informal participation estimate.
    """
    pivot = regional.pivot_table(index="Region", columns="Period",
                                 values="Gap", aggfunc="first")
    pivot = pivot.loc[pivot.mean(axis=1).sort_values(ascending=True).index]

    fig, ax = plt.subplots(figsize=(11, 6))
    vmax = max(abs(pivot.values.min()), abs(pivot.values.max()))
    im = ax.imshow(pivot.values, aspect="auto", cmap="PuOr_r",
                   vmin=-vmax, vmax=vmax)

    ax.set_xticks(range(pivot.shape[1]))
    ax.set_xticklabels(pivot.columns, fontsize=10)
    ax.set_yticks(range(pivot.shape[0]))
    ax.set_yticklabels(pivot.index, fontsize=10)

    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            v = pivot.values[i, j]
            if np.isnan(v):
                continue
            c = "white" if abs(v) > vmax * 0.55 else PAL["text"]
            ax.text(j, i, f"{v:,.0f}", ha="center", va="center",
                    fontsize=9, fontweight="bold", color=c)

    ax.set_title("Rugby Union Participation Gap (ALS − RFU) by Region × Year\n"
                 "Purple = ALS > RFU (hidden rugby)  |  Orange = RFU > ALS",
                 pad=14)
    fig.colorbar(im, ax=ax, label="Gap (ALS − RFU)", shrink=0.7)
    _save("gap_10_geo_gap_heatmap")
    return pivot


# ── Plot G3: Stacked area — gap decomposition by region ──

def viz_geo_gap_stack(regional):
    """
    Stacked area showing how the national gap decomposes into
    regional contributions over time.
    """
    pivot = regional.pivot_table(index="Period", columns="Region",
                                 values="Gap", aggfunc="first").fillna(0)
    # Sort regions by total contribution
    order = pivot.sum().sort_values(ascending=False).index
    pivot = pivot[order]

    fig, ax = plt.subplots(figsize=(12, 6))
    x = range(len(pivot))

    # Only stack positive gaps (negative gaps would invert the visual)
    pos = pivot.clip(lower=0)
    ax.stackplot(x, *[pos[c] for c in pos.columns], alpha=0.75,
                 labels=pos.columns, colors=CAT_COLORS[:len(pos.columns)])

    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index, fontsize=10)
    ax.set_ylabel("Non-club participation estimate (ALS − RFU)")
    ax.set_title("Rugby Union Gap Decomposition — Which Regions Contribute Most\n"
                 "to Non-Club Rugby Union?", pad=12)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8.5,
              title="Region")
    ax.grid(axis="y", color=PAL["grid"], lw=0.5)
    _fmt_thousands(ax)
    _save("gap_11_geo_gap_stack")


# ── Plot G4: Year-over-year gap change (Δ heatmap) ──

def viz_geo_gap_delta(regional):
    """
    Heatmap showing year-over-year CHANGE in gap.
    Green = gap shrinking (clubs capturing more), Red = gap growing.
    """
    pivot = regional.pivot_table(index="Region", columns="Period",
                                 values="Gap", aggfunc="first")
    delta = pivot.diff(axis=1).iloc[:, 1:]  # drop first NaN column
    delta = delta.loc[delta.abs().mean(axis=1).sort_values(ascending=True).index]

    fig, ax = plt.subplots(figsize=(10, 6))
    vmax = np.nanmax(np.abs(delta.values))
    im = ax.imshow(delta.values, aspect="auto", cmap="RdYlGn_r",
                   vmin=-vmax, vmax=vmax)

    cols = [f"{delta.columns[i-1]}→\n{delta.columns[i]}"
            if i > 0 else delta.columns[i]
            for i in range(len(delta.columns))]
    # Build transition labels
    periods = list(pivot.columns)
    trans_labels = [f"{periods[i]} →\n{periods[i+1]}" for i in range(len(periods)-1)]

    ax.set_xticks(range(delta.shape[1]))
    ax.set_xticklabels(trans_labels, fontsize=9)
    ax.set_yticks(range(delta.shape[0]))
    ax.set_yticklabels(delta.index, fontsize=10)

    for i in range(delta.shape[0]):
        for j in range(delta.shape[1]):
            v = delta.values[i, j]
            if np.isnan(v):
                continue
            c = "white" if abs(v) > vmax * 0.55 else PAL["text"]
            ax.text(j, i, f"{v:+,.0f}", ha="center", va="center",
                    fontsize=9, fontweight="bold", color=c)

    ax.set_title("Year-over-Year Change in Rugby Union Gap (ALS − RFU)\n"
                 "Red = gap growing  |  Green = gap shrinking (clubs capturing more rugby union players)",
                 pad=14)
    fig.colorbar(im, ax=ax, label="Δ Gap", shrink=0.7)
    _save("gap_12_geo_gap_yoy_delta")


# ── Plot G5: Gender-specific regional gap ──

def viz_geo_gender_gap(regional):
    """
    Grouped horizontal bars for the latest period:
    male gap vs female gap by region, side by side.
    """
    latest_label = YEAR_ALIGNMENT[-1][0]
    latest = regional[regional["Period"] == latest_label].copy()
    if latest.empty:
        return
    latest = latest.sort_values("Gap", ascending=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6),
                                    gridspec_kw={"wspace": 0.35})

    # ── Male gap ──
    ax1.barh(latest["Region"], latest["Gap_M"], height=0.55,
             color=PAL["male"], alpha=0.85, edgecolor="white")
    ax1.axvline(0, color=PAL["text"], lw=0.8)
    for bar, v in zip(ax1.patches, latest["Gap_M"]):
        off = max(abs(latest["Gap_M"]).max() * 0.025, 10)
        ax1.text(v + (off if v >= 0 else -off),
                 bar.get_y() + bar.get_height() / 2,
                 f"{v:,.0f}", va="center",
                 ha="left" if v >= 0 else "right", fontsize=8.5,
                 fontweight="bold", color=PAL["male"])
    ax1.set_xlabel("Male gap (ALS − RFU)")
    ax1.set_title("Male — Non-Club Estimate by Region")
    ax1.grid(axis="x", color=PAL["grid"], lw=0.5)
    _fmt_thousands(ax1, "x")

    # ── Female gap ──
    latest_f = latest.sort_values("Gap_F", ascending=True)
    ax2.barh(latest_f["Region"], latest_f["Gap_F"], height=0.55,
             color=PAL["female"], alpha=0.85, edgecolor="white")
    ax2.axvline(0, color=PAL["text"], lw=0.8)
    for bar, v in zip(ax2.patches, latest_f["Gap_F"]):
        off = max(abs(latest_f["Gap_F"]).max() * 0.025, 10)
        ax2.text(v + (off if v >= 0 else -off),
                 bar.get_y() + bar.get_height() / 2,
                 f"{v:,.0f}", va="center",
                 ha="left" if v >= 0 else "right", fontsize=8.5,
                 fontweight="bold", color=PAL["female"])
    ax2.set_xlabel("Female gap (ALS − RFU)")
    ax2.set_title("Female — Non-Club Estimate by Region")
    ax2.grid(axis="x", color=PAL["grid"], lw=0.5)
    _fmt_thousands(ax2, "x")

    fig.suptitle(f"Gender-Specific Regional Gap — {latest_label}",
                 y=1.02, fontsize=14, fontweight="bold")
    _save("gap_13_geo_gender_gap")


# ── Plot G6: Bubble scatter — gap landscape ──

def viz_geo_bubble_scatter(regional):
    """
    Each bubble = one region in the latest period.
    x-axis  = capture rate (%)
    y-axis  = absolute gap (hidden rugby estimate)
    size    = ALS survey estimate (total potential market)
    colour  = gap trend (improving / worsening vs prior period)
    """
    periods = sorted(regional["Period"].unique())
    if len(periods) < 2:
        return
    latest_label = periods[-1]
    prev_label   = periods[-2]

    latest = regional[regional["Period"] == latest_label].copy()
    prev   = regional[regional["Period"] == prev_label].set_index("Region")

    if latest.empty:
        return

    latest["Gap_Change"] = latest.apply(
        lambda r: r["Gap"] - prev.loc[r["Region"], "Gap"]
        if r["Region"] in prev.index else 0, axis=1)

    fig, ax = plt.subplots(figsize=(12, 7))

    # Bubble size proportional to ALS estimate
    size_scale = 6000 / latest["ALS"].max()

    for _, row in latest.iterrows():
        color = PAL["green"] if row["Gap_Change"] < 0 else PAL["rfu"]
        edge  = PAL["green"] if row["Gap_Change"] < 0 else PAL["rfu"]
        ax.scatter(row["Capture_%"], row["Gap"],
                   s=row["ALS"] * size_scale, alpha=0.55,
                   color=color, edgecolors=edge, linewidths=1.2)
        ax.annotate(row["Region"],
                    xy=(row["Capture_%"], row["Gap"]),
                    fontsize=8.5, ha="center", va="bottom",
                    xytext=(0, 8), textcoords="offset points",
                    fontweight="bold", color=PAL["text"])

    ax.axhline(0, color=PAL["grid"], lw=0.8, ls="--")
    ax.set_xlabel("Club Capture Rate (%)")
    ax.set_ylabel("Absolute Gap (ALS − RFU)")
    ax.set_title(f"Regional Gap Landscape — {latest_label}\n"
                 f"Bubble size ∝ ALS survey estimate  |  "
                 f"Green = gap shrinking vs {prev_label}  "
                 f"Red = gap growing", pad=14)
    ax.grid(True, color=PAL["grid"], lw=0.5, alpha=0.7)
    _fmt_thousands(ax)

    # Quadrant labels
    xlim = ax.get_xlim(); ylim = ax.get_ylim()
    mid_x = (xlim[0] + xlim[1]) / 2
    mid_y = max(ylim[1] * 0.92, (ylim[0] + ylim[1]) / 2)
    ax.text(xlim[0] + (xlim[1]-xlim[0])*0.05, ylim[1]*0.95,
            "LOW capture\nHIGH gap\n→ top scouting target",
            fontsize=8, color=PAL["gap"], alpha=0.6, va="top",
            style="italic")
    ax.text(xlim[1] - (xlim[1]-xlim[0])*0.05, ylim[0] + (ylim[1]-ylim[0])*0.05,
            "HIGH capture\nLOW gap\n→ well-served",
            fontsize=8, color=PAL["green"], alpha=0.6, va="bottom", ha="right",
            style="italic")

    _save("gap_14_geo_bubble_scatter")


def viz_summary_dashboard(comp):
    """Four-quadrant key-metrics dashboard (age-consistent)."""
    latest, first = comp.iloc[-1], comp.iloc[0]

    fig = plt.figure(figsize=(14, 9))
    gs = GridSpec(2, 2, hspace=0.35, wspace=0.30)

    # Q1: headline numbers — always 7–18 (primary comparison)
    ax1 = fig.add_subplot(gs[0, 0]); ax1.axis("off")
    note_17_18 = "" if latest.get("Has_17_18", False) else " *"
    metrics = [
        ("ALS (7–18)" + note_17_18, f"{latest['ALS_7_18']:,.0f}", PAL["als"]),
        ("RFU (U7–U18)",            f"{latest['RFU_U7_U18']:,.0f}", PAL["rfu"]),
        ("Gap (7–18)",              f"{latest['Gap_Overall']:,.0f}", PAL["gap"]),
        ("Capture Rate",            f"{latest['Capture_%']:.1f}%", PAL["gap"]),
    ]
    spacing = 0.20
    for i, (lbl, val, col) in enumerate(metrics):
        y = 0.85 - i * spacing
        ax1.text(0.05, y, lbl, fontsize=11, color="#6B7280", transform=ax1.transAxes)
        ax1.text(0.95, y, val, fontsize=17, fontweight="bold", color=col,
                 ha="right", transform=ax1.transAxes)
    if note_17_18:
        ax1.text(0.05, 0.05, "* 17–18 estimate not available for this period",
                 fontsize=7.5, color="#9CA3AF", transform=ax1.transAxes, style="italic")
    ax1.set_title(f"Key Figures — {latest['Period']}", fontsize=13, loc="left")

    # Q2: gap trend
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.fill_between(comp["Period"], comp["Gap_Overall"], alpha=0.25, color=PAL["gap"])
    ax2.plot(comp["Period"], comp["Gap_Overall"], "o-", color=PAL["gap"], lw=2.5, ms=8)
    for i, row in comp.iterrows():
        ax2.text(i, row["Gap_Overall"]+comp["Gap_Overall"].max()*0.03,
                 f"{row['Gap_Overall']:,.0f}", ha="center", fontsize=8.5,
                 fontweight="bold", color=PAL["gap"])
    ax2.set_title("Non-Club Rugby Union Participation Gap Over Time")
    ax2.set_ylabel("ALS − RFU (ages 7–18 vs U7–U18)")
    ax2.grid(axis="y", color=PAL["grid"], lw=0.6); _fmt_thousands(ax2)

    # Q3: gender capture rate bars
    ax3 = fig.add_subplot(gs[1, 0])
    x = np.arange(len(comp)); w = 0.30
    ax3.bar(x-w/2, comp["Capture_%_M"], w, color=PAL["male"], alpha=0.8, label="Male")
    ax3.bar(x+w/2, comp["Capture_%_F"], w, color=PAL["female"], alpha=0.8, label="Female")
    ax3.set_xticks(x); ax3.set_xticklabels(comp["Period"], fontsize=9)
    ax3.set_ylabel("Capture rate (%)")
    ax3.set_title("Rugby Union Club Capture Rate by Gender (7–18 vs U7–U18)")
    ax3.legend(fontsize=9); ax3.grid(axis="y", color=PAL["grid"], lw=0.6)

    # Q4: period-over-period changes — always 7–18
    ax4 = fig.add_subplot(gs[1, 1]); ax4.axis("off")
    changes = [
        ("ALS (7–18)",     first["ALS_7_18"],     latest["ALS_7_18"],     False),
        ("RFU (U7–U18)",   first["RFU_U7_U18"],   latest["RFU_U7_U18"],   False),
        ("Gap (7–18)",     first["Gap_Overall"],   latest["Gap_Overall"],  True),
        ("Capture Rate",   first["Capture_%"],     latest["Capture_%"],    False),
    ]
    ax4.set_title(f"Change: {first['Period']} → {latest['Period']}", fontsize=13, loc="left")
    n_chg = len(changes)
    sp = 0.20
    for i, (lbl, v0, v1, gap_logic) in enumerate(changes):
        y = 0.90 - i * sp
        delta = v1 - v0
        if np.isnan(delta):
            continue
        arrow = "▲" if delta > 0 else "▼"
        if "Capture" in lbl:
            color = PAL["green"] if delta > 0 else PAL["rfu"]
            txt = f"{arrow} {abs(delta):.1f} pp"
        else:
            color = (PAL["green"] if delta < 0 else PAL["rfu"]) if gap_logic \
                    else (PAL["green"] if delta > 0 else PAL["rfu"])
            txt = f"{arrow} {abs(delta):,.0f}"
        ax4.text(0.05, y, lbl, fontsize=10, color="#6B7280", transform=ax4.transAxes)
        ax4.text(0.95, y, txt, fontsize=14, fontweight="bold", color=color,
                 ha="right", transform=ax4.transAxes)

    fig.suptitle("ALS vs RFU — Rugby Union Participation Gap Dashboard",
                 y=1.01, fontsize=16, fontweight="bold")
    fig.text(0.5, -0.01, _GAP_FOOTNOTE, ha="center", fontsize=8, color="#6B7280", style="italic")
    _save("gap_08_summary_dashboard")


# ══════════════════════════════════════════════════════════════════════════════
# 8.  Legacy category-trend plots
# ══════════════════════════════════════════════════════════════════════════════

VALID_MODES = {
    "largest", "smallest", "most_improved_custom", "least_improved_custom",
    "percent_growth", "percent_fall", "recovery", "weakest_recovery",
}

def plot_category_trends(df, top_n=5, mode="largest", first_col=None,
                         last_col=None, xlabel="Year",
                         ylabel="Participation Count",
                         title="Participation Trends", save_tag=""):
    if mode not in VALID_MODES:
        raise ValueError(f"Unknown mode '{mode}'")
    if mode == "largest":       sel = df.sum(axis=1).nlargest(top_n);  pt = f"Top {top_n} {title}"
    elif mode == "smallest":    sel = df.sum(axis=1).nsmallest(top_n); pt = f"Bottom {top_n} {title}"
    elif mode == "most_improved_custom":
        sel = (df[last_col]-df[first_col]).nlargest(top_n);  pt = f"Most Improved {top_n} {title}"
    elif mode == "least_improved_custom":
        sel = (df[last_col]-df[first_col]).nsmallest(top_n); pt = f"Least Improved {top_n} {title}"
    elif mode == "percent_growth":
        sel = ((df[last_col]-df[first_col])/df[first_col]*100).nlargest(top_n)
        pt = f"Top {top_n} % Growth {title}"
    elif mode == "percent_fall":
        sel = ((df[last_col]-df[first_col])/df[first_col]*100).nsmallest(top_n)
        pt = f"Top {top_n} % Fall {title}"
    elif mode == "recovery":
        mid = df.loc[:,first_col:last_col].iloc[:,1:-1].columns
        sel = (df[last_col]-df[mid].min(axis=1)).nlargest(top_n)
        pt = f"Top {top_n} Recovery {title}"
    elif mode == "weakest_recovery":
        mid = df.loc[:,first_col:last_col].iloc[:,1:-1].columns
        sel = (df[last_col]-df[mid].min(axis=1)).nsmallest(top_n)
        pt = f"Weakest {top_n} Recovery {title}"

    fig, ax = plt.subplots(figsize=(10, 6))
    for j, cat in enumerate(sel.index):
        c = CAT_COLORS[j % len(CAT_COLORS)]
        lbl = str(cat) if isinstance(cat, str) else " / ".join(str(x) for x in cat)
        ax.plot(df.columns, df.loc[cat], "o-", lw=2, color=c, label=lbl[:50])
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(pt)
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", color=PAL["grid"], lw=0.6)
    ax.legend(loc="upper left", bbox_to_anchor=(1, 1), fontsize=8)
    _fmt_thousands(ax)
    _save(f"{save_tag}_{mode}" if save_tag else f"trend_{mode}")
    return sel.to_frame(name="Summary Value")


# ══════════════════════════════════════════════════════════════════════════════
# 9.  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def run_all():
    os.chdir(BASE_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log.info("Working directory: %s", BASE_DIR)

    # ━━ PHASE 1: Load ALS ━━
    log.info("=" * 65)
    log.info("PHASE 1 : Loading & preprocessing ALS data")
    log.info("=" * 65)
    als_overall, als_males, als_females = build_als_datasets()
    years_als = list(als_overall.keys())
    for y in years_als:
        t = als_overall[y]["weighted_total"].sum()
        m = als_males[y]["weighted_total"].sum()
        f = als_females[y]["weighted_total"].sum()
        log.info("ALS %s : overall=%10.0f  male=%10.0f  female=%10.0f", y, t, m, f)

    # ━━ PHASE 2: Load RFU ━━
    log.info("=" * 65)
    log.info("PHASE 2 : Loading & preprocessing RFU data")
    log.info("=" * 65)
    rfu_dfs = build_rfu_datasets()

    # ━━ PHASE 3: Grouped tables ━━
    log.info("=" * 65)
    log.info("PHASE 3 : Building grouped tables")
    log.info("=" * 65)
    ds = [als_overall[y] for y in years_als]
    ml = [als_males[y]   for y in years_als]
    fl = [als_females[y] for y in years_als]

    rw_o = group_by_columns(ds, years_als, ["Region","CSP"], "weighted_total")
    rw_m = group_by_columns(ml, years_als, ["Region","CSP"], "weighted_total")
    rw_f = group_by_columns(fl, years_als, ["Region","CSP"], "weighted_total")

    rfu_cb_o = group_by_columns(rfu_dfs, RFU_YEARS, ["Constituent Body"], "count_col")
    rfu_cb_m = group_by_columns(rfu_dfs, RFU_YEARS, ["Constituent Body"], "count_col_m")
    rfu_cb_f = group_by_columns(rfu_dfs, RFU_YEARS, ["Constituent Body"], "count_col_f")

    rfu_nz  = rfu_cb_o[(rfu_cb_o != 0).all(axis=1)]
    rfu_nzm = rfu_cb_m[(rfu_cb_m != 0).any(axis=1)]
    rfu_nzf = rfu_cb_f[(rfu_cb_f != 0).any(axis=1)]

    # ━━ PHASE 4: Enhanced ALS plots ━━
    log.info("=" * 65)
    log.info("PHASE 4 : Enhanced ALS visualisations")
    log.info("=" * 65)
    viz_als_national(als_overall, als_males, als_females)
    viz_als_region_heatmap(als_overall, years_als)
    viz_als_top_bottom_csp(rw_o, "2017-18", "2022-23")
    viz_als_gender_ratio(als_overall, als_males, years_als)

    # ━━ PHASE 5: Enhanced RFU plots ━━
    log.info("=" * 65)
    log.info("PHASE 5 : Enhanced RFU visualisations")
    log.info("=" * 65)
    viz_rfu_national(rfu_dfs, RFU_YEARS)
    viz_rfu_age_pyramid(rfu_dfs, RFU_YEARS)
    viz_rfu_cb_heatmap(rfu_dfs, RFU_YEARS)
    viz_rfu_top_bottom_cb(rfu_dfs, RFU_YEARS)

    # ━━ PHASE 5b: Legacy mode-based trend plots ━━
    log.info("PHASE 5b: Legacy category-trend plots")
    fa, la = "2017-18", "2022-23"
    fr, lr = "2018",    "2023-24"

    def run_modes(gdf, tag, f, l, mt=None):
        if mt is None:
            mt = [("largest",5),("smallest",5),("most_improved_custom",5),
                  ("least_improved_custom",5),("percent_growth",5),("percent_fall",5)]
        for mode, n in mt:
            try: plot_category_trends(gdf, top_n=n, mode=mode,
                                      first_col=f, last_col=l, save_tag=tag)
            except Exception as e: log.warning("Skipped %s/%s: %s", tag, mode, e)

    run_modes(rw_o, "als_overall", fa, la)
    run_modes(rw_m, "als_males",   fa, la)
    run_modes(rw_f, "als_females", fa, la)
    rm = [("largest",5),("smallest",8),("most_improved_custom",5),
          ("least_improved_custom",8),("percent_growth",5),("percent_fall",8)]
    run_modes(rfu_nz,  "rfu_overall", fr, lr, rm)
    run_modes(rfu_nzm, "rfu_males",   fr, lr, rm)
    run_modes(rfu_nzf, "rfu_females", fr, lr, rm)

    # Age-based
    for gdf, tag, dsets in [(ds,"als_age_overall",None), (ml,"als_age_males",None),
                             (fl,"als_age_females",None)]:
        ag = group_by_columns(gdf, years_als, ["Age"], "weighted_total")
        plot_category_trends(ag, save_tag=tag)

    # ━━ PHASE 5c: Load ALS Adult 17–18 estimates ━━
    log.info("=" * 65)
    log.info("PHASE 5c: Loading ALS Adult data for 17–18 estimates")
    log.info("=" * 65)
    adult_17_18 = build_adult_17_18(als_overall)

    # ━━ PHASE 6: ★ COMPARISON / GAP ANALYSIS ━━
    log.info("=" * 65)
    log.info("PHASE 6 : ★ ALS vs RFU Gap Analysis")
    log.info("=" * 65)

    comp = _build_comparison_df(als_overall, als_males, als_females,
                                rfu_dfs, RFU_YEARS, adult_17_18)
    comp.to_csv(OUTPUT_DIR / "comparison_als_vs_rfu.csv", index=False)
    log.info("Comparison table:\n%s", comp.to_string(index=False))

    # Core 7-16 plots (existing)
    viz_gap_national(comp)
    viz_capture_rate(comp)
    viz_hidden_rugby(comp)
    viz_gender_gap(comp)

    # Combined 7-18 plots (new)
    viz_combined_7_18(comp)
    viz_combined_summary_table(comp)

    regional = viz_regional_comparison(als_overall, rfu_dfs, RFU_YEARS, adult_17_18)
    regional.to_csv(OUTPUT_DIR / "comparison_regional.csv", index=False)
    scouting = viz_scouting_opportunity(comp, regional)
    if scouting is not None:
        scouting.to_csv(OUTPUT_DIR / "scouting_opportunity.csv", index=False)
    viz_summary_dashboard(comp)

    # ━━ PHASE 6b: ★ Extended geographic gap analysis ━━
    log.info("=" * 65)
    log.info("PHASE 6b: Geographic gap deep-dive")
    log.info("=" * 65)

    regional_ext = _build_regional_df(als_overall, als_males, als_females,
                                       rfu_dfs, RFU_YEARS, adult_17_18)
    regional_ext.to_csv(OUTPUT_DIR / "comparison_regional_extended.csv", index=False)

    viz_geo_faceted_gap(regional_ext)       # G1: small multiples per region
    viz_geo_gap_heatmap(regional_ext)       # G2: absolute gap heatmap
    viz_geo_gap_stack(regional_ext)         # G3: stacked area decomposition
    viz_geo_gap_delta(regional_ext)         # G4: year-over-year Δ heatmap
    viz_geo_gender_gap(regional_ext)        # G5: male vs female gap per region
    viz_geo_bubble_scatter(regional_ext)    # G6: bubble scatter landscape

    # ━━ PHASE 7: Save tables ━━
    log.info("=" * 65)
    log.info("PHASE 7 : Saving summary tables")
    log.info("=" * 65)
    rw_o.to_csv(OUTPUT_DIR / "als_regionwise_overall.csv")
    rw_m.to_csv(OUTPUT_DIR / "als_regionwise_males.csv")
    rw_f.to_csv(OUTPUT_DIR / "als_regionwise_females.csv")
    rfu_cb_o.to_csv(OUTPUT_DIR / "rfu_regionwise_overall.csv")
    rfu_cb_m.to_csv(OUTPUT_DIR / "rfu_regionwise_males.csv")
    rfu_cb_f.to_csv(OUTPUT_DIR / "rfu_regionwise_females.csv")

    log.info("All outputs → %s", OUTPUT_DIR)
    log.info("DONE ✓")


if __name__ == "__main__":
    run_all()