#!/usr/bin/env python3
"""
Stratified ALS vs RFU Analysis — Full Implementation
======================================================
Implements the 6-step analysis plan + 5 audit fixes:
  Step 1: Gross comparison (all rugby) + Adult 16–18 sub-output
  Step 2: Rugby Union only 16–18 (Adult vs RFU U16–U18) + Club Test 1
  Step 3: CYP any rugby U7–16 vs RFU U7–U16
  Step 4: School vs Outside-School vs Both setting + club caveat
  Step 5: Age-band aligned comparison (U7-8…16-18)
  Step 6: Timeline & variable documentation
  + Gender breakdowns in all steps
  + Regional/geographic analysis (Q6)
  + Cleaned yearly file exports

Run: cd path/ALS_RFU_Analysis && python als_rfu_stratified.py
"""

import os, logging
from pathlib import Path
from typing import Dict, Optional
import numpy as np, pandas as pd, pyreadstat
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.gridspec import GridSpec
import warnings; warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
BASE_DIR   = Path("path/ALS_RFU_Analysis")
OUTPUT_DIR = BASE_DIR / "output_stratified"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
log = logging.getLogger(__name__)

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"],
    "font.size": 11, "axes.titlesize": 13, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "savefig.facecolor": "white",
    "figure.dpi": 150, "savefig.dpi": 150,
})

C = {"als":"#2563EB","rfu":"#DC2626","gap":"#9333EA","male":"#0369A1",
     "female":"#BE185D","green":"#059669","school":"#D97706",
     "outschool":"#7C3AED","club":"#059669","grid":"#E5E7EB","text":"#1F2937"}
CAT = ["#2563EB","#DC2626","#059669","#D97706","#7C3AED","#0891B2","#DB2777","#65A30D"]

def _save(name):
    p = OUTPUT_DIR / f"{name}.png"
    plt.savefig(p, dpi=150, bbox_inches="tight"); plt.close()
    log.info("Saved: %s", p.name)

def _kfmt(ax, axis="y"):
    fmt = mticker.FuncFormatter(lambda x, _: f"{x:,.0f}")
    if axis in ("y","both"): ax.yaxis.set_major_formatter(fmt)
    if axis in ("x","both"): ax.xaxis.set_major_formatter(fmt)

# ── Column names ──
# Young CYP
YC_ALLRUGBY   = "onceawk_modplus_everywhere_GR_RUGBY_CC018"
YC_ALLR_SCH   = "onceawk_modplus_inschool_GR_RUGBY_CC018"
YC_ALLR_OUT   = "onceawk_modplus_outschool_GR_RUGBY_CC018"
YC_UNION      = "onceawk_modplus_everywhere_GR_RUGBYUNION_CD0182"
YC_UNION_SCH  = "onceawk_modplus_inschool_GR_RUGBYUNION_CD0182"
YC_UNION_OUT  = "onceawk_modplus_outschool_GR_RUGBYUNION_CD0182"
YC_AGE   = "age_11"
YC_GEND  = "gend3"
YC_WT    = "wt_gross"
# Region — varies by year
REGION_COLS = {
    "2017-18": "Region_name", "2018-19": "Region_name",
    "2019-20": "Region_name", "2020-21": "Region_name",
    "2021-22": "Region_name", "2022-23": "Region_name",
}
REGION_MAP = {1:"East",2:"East Midlands",3:"London",4:"North East",
              5:"North West",6:"South East",7:"South West",
              8:"West Midlands",9:"Yorkshire and the Humber"}

# Adult
AC_UNION  = "MONTHS_12_RUGBYUNION_F03"
AC_CLUB   = "CLUB_RUGBYUNION_F03"
AC_AGE    = "Age17"
AC_U19    = "Age19plus"
AC_GEND   = "Gend3"
AC_WT     = "wt_final"
AC_CSP    = "CSP"

# ── ONS Mid-Year Population Estimates: England, ages 16–18 combined ──
# Source: ONS, Mid-year population estimates (nomis.web)
# wt_final in Adult ALS is a normalised design weight (sums to sample N,
# mean ≈ 1.0). It is NOT a grossing weight. To produce population estimates
# comparable to RFU headcounts, we compute the weighted participation RATE
# from the survey, then multiply by the ONS population for 16–18 in England.
# These figures should be verified against the latest ONS release.
ONS_POP_16_18 = {
    "2017-18": 1_950_000,   # mid-2017 / mid-2018 average
    "2018-19": 1_920_000,
    "2019-20": 1_900_000,
    "2020-21": 1_880_000,
    "2021-22": 1_870_000,
    "2022-23": 1_890_000,
}

# Adult CSP → Region (Adult CSP has different codes from Young)
ADULT_CSP_TO_REGION = {
    1:"East",2:"South East",3:"West Midlands",4:"West Midlands",
    5:"South East",6:"East",7:"North West",8:"South West",9:"North West",
    10:"East Midlands",11:"South West",12:"South West",13:"North East",
    14:"East",15:"South West",16:"North West",17:"South East",
    18:"West Midlands",19:"East",20:"Yorkshire and the Humber",
    21:"South East",22:"North West",23:"East Midlands",24:"East Midlands",
    25:"London",30:"North West",31:"East",32:"Yorkshire and the Humber",
    33:"East Midlands",34:"North East",35:"East Midlands",36:"South East",
    37:"West Midlands",38:"South West",39:"South Yorkshire",
    40:"North East",41:"North East",42:"West Midlands",
    43:"South West",44:"Yorkshire and the Humber",45:"South West",
    46:"West Midlands",47:"South West",48:"Yorkshire and the Humber",
    49:"South West",
}

# RFU CB → Region
CB_TO_REGION = {
    "Eastern Counties Rugby Union (CB)":"East",
    "Essex County RFU (CB)":"East","Hertfordshire RFU (CB)":"East",
    "East Midlands Rugby Union (CB)":"East Midlands",
    "Notts, Lincs & Derbyshire RFU (CB)":"East Midlands",
    "Leicestershire Rugby Union Ltd (CB)":"East Midlands",
    "Middlesex County RFU (CB)":"London",
    "Durham County Rugby Union (CB)":"North East",
    "Northumberland Rugby Union (CB)":"North East",
    "Lancashire County RFU (CB)":"North West",
    "Cheshire RFU (CB)":"North West","Cumbria RFU Ltd. (CB)":"North West",
    "Kent County Rugby Football Union Limited (CB)":"South East",
    "Surrey Rugby (CB)":"South East","Sussex RFU Ltd. (CB)":"South East",
    "Hampshire RFU Ltd. (CB)":"South East",
    "Berkshire County RFU (CB)":"South East",
    "Buckinghamshire County RFU (CB)":"South East",
    "Oxfordshire RFU (CB)":"South East",
    "Cornwall RFU (CB)":"South West","Devon RFU (CB)":"South West",
    "Dorset & Wilts RFU (CB)":"South West",
    "Gloucestershire RFU (CB)":"South West",
    "Somerset County RFU Limited(CB)":"South West",
    "North Midlands RFU (CB)":"West Midlands",
    "Staffordshire County RFU (CB)":"West Midlands",
    "Warwickshire RFU (CB)":"West Midlands",
    "Yorkshire RFU (CB)":"Yorkshire and the Humber",
}

# Year configs
YOUNG_FILES = [
    {"file":"ALS_Young_2017-18.sav","year":"2017-18","has_union":False,"region_col":"Region_name"},
    {"file":"ALS_Young_2018-19.sav","year":"2018-19","has_union":False,"region_col":"Region_name"},
    {"file":"ALS_Young_2019-20.sav","year":"2019-20","has_union":False,"region_col":"Region_name"},
    {"file":"ALS_Young_2020-21.sav","year":"2020-21","has_union":False,"region_col":"Region_name"},
    {"file":"ALS_Young_2021-22.sav","year":"2021-22","has_union":False,"region_col":"Region_name"},
    {"file":"ALS_Young_2022-23.sav","year":"2022-23","has_union":True, "region_col":"Region_name"},
]
ADULT_FILES = [
    {"file":"ALS_Adult_2017-18.sav","year":"2017-18","fmt":"adult"},
    {"file":"ALS_Adult_2018-19.sav","year":"2018-19","fmt":"adult"},
    {"file":"ALS_Adult_2019-20.sav","year":"2019-20","fmt":"adult"},
    {"file":"ALS_Adult_2020-21.sav","year":"2020-21","fmt":"young_dup"},
    {"file":"ALS_Adult_2021-22.sav","year":"2021-22","fmt":"adult"},
    {"file":"ALS_Adult_2022-23.sav","year":"2022-23","fmt":"young_dup"},
]
RFU_FILE = "RFU_Data_2011_23.xlsx"
RFU_SHEETS = [7,9,11,13,15]
RFU_YEARS_OLD = ["2018","2019","2019 nov","2021 Jan","2023 May"]
RFU_NEW_FILE = "RFU_Data_New.xlsx"
RFU_NEW_YEAR = "2023-24"

ALIGN = [("2017-18","2017-18","2018"),("2018-19","2018-19","2019"),
         ("2019-20","2019-20","2019 nov"),("2020-21","2020-21","2021 Jan"),
         ("2022-23","2022-23","2023 May")]

AGE_BANDS = [
    ("U7–8",[7,8],["U7","U8"]),("U9–10",[9,10],["U9","U10"]),
    ("U11–12",[11,12],["U11","U12"]),("U13–14",[13,14],["U13","U14"]),
    ("U15–16",[15,16],["U15","U16"]),("16–18",[],["U16","U17","U18"]),
]

# ══════════════════════════════════════════════════════════════════════════════
# Data loading
# ══════════════════════════════════════════════════════════════════════════════

def load_young(cfg):
    path = BASE_DIR / cfg["file"]
    cols = [YC_ALLRUGBY, YC_ALLR_SCH, YC_ALLR_OUT, YC_AGE, YC_GEND, YC_WT, cfg["region_col"]]
    if cfg["has_union"]:
        cols += [YC_UNION, YC_UNION_SCH, YC_UNION_OUT]
    cols = list(dict.fromkeys(cols))
    df, _ = pyreadstat.read_sav(str(path), usecols=cols)
    # Standardise region column name
    if cfg["region_col"] != "Region":
        df["Region"] = df[cfg["region_col"]].map(REGION_MAP)
    log.info("Young %s: %d rows", cfg["year"], len(df))
    return df

def load_adult(cfg):
    if cfg["fmt"] != "adult": return None
    path = BASE_DIR / cfg["file"]
    cols = [AC_UNION, AC_CLUB, AC_AGE, AC_U19, AC_GEND, AC_WT, AC_CSP]
    df, _ = pyreadstat.read_sav(str(path), usecols=cols)
    df = df[(df[AC_AGE]==1.0)&(df[AC_U19]==0.0)].copy()
    df["Region"] = df[AC_CSP].map(ADULT_CSP_TO_REGION)
    log.info("Adult %s: %d under-19 (16–18)", cfg["year"], len(df))
    return df

def load_rfu():
    rfu = {}
    xls = pd.ExcelFile(BASE_DIR / RFU_FILE)
    for idx, year in zip(RFU_SHEETS, RFU_YEARS_OLD):
        df = xls.parse(sheet_name=xls.sheet_names[idx]).iloc[:-1].copy()
        rfu[year] = df
    # New file
    raw = pd.read_excel(BASE_DIR / RFU_NEW_FILE, sheet_name=0, header=None)
    r0, r1 = raw.iloc[0].tolist(), raw.iloc[1].tolist()
    cn, cur = [], None
    for i in range(len(r0)):
        a, g = r0[i], str(r1[i]).strip()
        if i==0: cn.append("Constituent Body"); continue
        if i==1: cn.append("Club"); continue
        if not pd.isna(a): cur = str(a).replace(".0","")
        if g=="Female": cn.append(f"{cur}F")
        elif g=="Male": cn.append(f"{cur}M")
        else: cn.append(f"{cur}_{g[:4]}")
    data = raw.iloc[2:].copy(); data.columns = cn
    data["Constituent Body"] = data["Constituent Body"].ffill()
    num = [c for c in cn if c not in ("Constituent Body","Club")]
    data[num] = data[num].apply(pd.to_numeric, errors="coerce").fillna(0)
    rfu[RFU_NEW_YEAR] = data.groupby("Constituent Body", as_index=False)[num].sum()
    return rfu

def rfu_sum(df, prefixes, gender=None):
    total = 0
    for p in prefixes:
        if gender in ("M","F"):
            col = f"{p}{gender}"
            if col in df.columns: total += df[col].sum()
        else:
            for g in ("M","F"):
                col = f"{p}{g}"
                if col in df.columns: total += df[col].sum()
    return total

def rfu_regional(df, prefixes, gender=None):
    """Sum RFU by region using CB→Region mapping."""
    if "Constituent Body" not in df.columns: return {}
    df = df.copy()
    df["_region"] = df["Constituent Body"].map(CB_TO_REGION)
    df = df.dropna(subset=["_region"])
    result = {}
    for reg, grp in df.groupby("_region"):
        result[reg] = rfu_sum(grp, prefixes, gender)
    return result

# ══════════════════════════════════════════════════════════════════════════════
# Union proportion
# ══════════════════════════════════════════════════════════════════════════════

def compute_union_proportion():
    """From 2022-23 where both columns coexist, compute union/all ratio.

    CRITICAL: The Rugby Union column (CD0182) is only populated for ages
    11–16 in the 2022-23 CYP survey. Ages 7–10 have NaN. So we must
    compute the proportion using ONLY rows where the union column is
    not NaN, to avoid deflating the denominator.
    """
    cfg = [c for c in YOUNG_FILES if c["year"]=="2022-23"][0]
    df = load_young(cfg)

    # Filter to rows where the union column IS populated (not NaN)
    has_union = df[df[YC_UNION].notna()].copy()
    log.info("Union proportion: %d/%d rows have union column data",
             len(has_union), len(df))

    all_wt = has_union.loc[has_union[YC_ALLRUGBY]==1, YC_WT].sum()
    uni_wt = has_union.loc[has_union[YC_UNION]==1, YC_WT].sum()
    prop = uni_wt / all_wt if all_wt > 0 else 1.0

    # Setting proportions (also filtered to rows with union data)
    sch_all = has_union.loc[has_union[YC_ALLR_SCH]==1, YC_WT].sum()
    out_all = has_union.loc[has_union[YC_ALLR_OUT]==1, YC_WT].sum()
    sch_u   = has_union.loc[has_union[YC_UNION_SCH]==1, YC_WT].sum()
    out_u   = has_union.loc[has_union[YC_UNION_OUT]==1, YC_WT].sum()
    log.info("Union proportion: %.4f (school=%.4f, outschool=%.4f)",
             prop, sch_u/sch_all if sch_all else 0, out_u/out_all if out_all else 0)

    # Also log which ages have data
    age = pd.to_numeric(has_union[YC_AGE], errors="coerce")
    log.info("Union column populated for ages: %s",
             sorted(age.dropna().unique().astype(int).tolist()))

    return {"overall": prop,
            "school": sch_u/sch_all if sch_all else prop,
            "outschool": out_u/out_all if out_all else prop}

# ══════════════════════════════════════════════════════════════════════════════
# FIX 4: Export cleaned yearly files
# ══════════════════════════════════════════════════════════════════════════════

def export_cleaned_files(young_data, adult_data, union_props):
    """Export standardised cleaned yearly CSVs with project variables."""
    log.info("Exporting cleaned yearly files")
    ratio = union_props["overall"]
    clean_dir = OUTPUT_DIR / "cleaned"
    clean_dir.mkdir(exist_ok=True)

    for cfg in YOUNG_FILES:
        ydf = young_data[cfg["year"]].copy()
        age = pd.to_numeric(ydf[YC_AGE], errors="coerce")
        out = pd.DataFrame()
        out["year"] = cfg["year"]
        out["sex"] = ydf[YC_GEND].map({1:"Male",2:"Female",3:"Other"})
        out["age"] = age
        out["age_band"] = pd.cut(age, bins=[6,8,10,12,14,16], right=True,
                                  labels=["U7–8","U9–10","U11–12","U13–14","U15–16"])
        out["weight"] = ydf[YC_WT]
        out["region"] = ydf["Region"] if "Region" in ydf.columns else np.nan
        out["rugby_any"] = (ydf[YC_ALLRUGBY]==1).astype(int)
        out["rugby_school"] = (ydf[YC_ALLR_SCH]==1).astype(int)
        out["rugby_outside_school"] = (ydf[YC_ALLR_OUT]==1).astype(int)
        out["rugby_school_and_outside"] = ((ydf[YC_ALLR_SCH]==1)&(ydf[YC_ALLR_OUT]==1)).astype(int)
        if cfg["has_union"]:
            out["rugby_union"] = (ydf[YC_UNION]==1).astype(int)
            out["rugby_union_school"] = (ydf[YC_UNION_SCH]==1).astype(int)
            out["rugby_union_outside_school"] = (ydf[YC_UNION_OUT]==1).astype(int)
        else:
            out["rugby_union"] = np.nan  # not available
        out["union_correction_applied"] = not cfg["has_union"]
        fname = f"ALS_CYP_{cfg['year']}_clean.csv"
        out.to_csv(clean_dir / fname, index=False)
        log.info("  %s (%d rows)", fname, len(out))

    for cfg in ADULT_FILES:
        if cfg["year"] not in adult_data: continue
        adf = adult_data[cfg["year"]].copy()
        out = pd.DataFrame()
        out["year"] = cfg["year"]
        out["sex"] = adf[AC_GEND].map({1:"Male",2:"Female",3:"Other"})
        out["age_band"] = "16–18"
        out["weight"] = adf[AC_WT]
        out["region"] = adf["Region"] if "Region" in adf.columns else np.nan
        out["rugby_union"] = (adf[AC_UNION]==1).astype(int)
        out["rugby_union_club"] = (adf[AC_CLUB]==1).astype(int)
        fname = f"ALS_Adult_{cfg['year']}_clean.csv"
        out.to_csv(clean_dir / fname, index=False)
        log.info("  %s (%d rows)", fname, len(out))


# ══════════════════════════════════════════════════════════════════════════════
# Helper: weighted counts with gender split
# ══════════════════════════════════════════════════════════════════════════════

def _wt_counts(df, flag_col, wt_col, gend_col):
    """Return overall, male, female weighted sums where flag_col==1."""
    sel = df[df[flag_col]==1]
    return {
        "overall": sel[wt_col].sum(),
        "male":    sel.loc[sel[gend_col]==1, wt_col].sum(),
        "female":  sel.loc[sel[gend_col]==2, wt_col].sum(),
    }

def _adult_pop_estimate(adf, flag_col, year):
    """Convert Adult ALS weighted rate to a population estimate.

    Adult ALS wt_final is normalised (sums to sample N, mean ≈ 1.0).
    We compute: weighted_rate = sum(wt[flag==1]) / sum(wt[all])
    Then: population_estimate = rate × ONS_16_18_population

    Returns dict with overall, male, female population estimates,
    plus the raw rate for transparency.
    """
    pop = ONS_POP_16_18.get(year, 1_900_000)
    total_wt = adf[AC_WT].sum()
    if total_wt == 0:
        return {"overall": 0, "male": 0, "female": 0, "rate": 0, "pop_denom": pop}

    sel = adf[adf[flag_col] == 1]
    rate = sel[AC_WT].sum() / total_wt
    rate_m = sel.loc[sel[AC_GEND]==1, AC_WT].sum() / adf.loc[adf[AC_GEND]==1, AC_WT].sum() if adf.loc[adf[AC_GEND]==1, AC_WT].sum() > 0 else 0
    rate_f = sel.loc[sel[AC_GEND]==2, AC_WT].sum() / adf.loc[adf[AC_GEND]==2, AC_WT].sum() if adf.loc[adf[AC_GEND]==2, AC_WT].sum() > 0 else 0

    # Approximate male/female split of 16-18 population (roughly 51/49)
    pop_m = pop * 0.51
    pop_f = pop * 0.49

    return {
        "overall": rate * pop,
        "male": rate_m * pop_m,
        "female": rate_f * pop_f,
        "rate": rate,
        "rate_m": rate_m, "rate_f": rate_f,
        "pop_denom": pop,
        "n_unweighted": len(sel),
    }

def _union_counts(filt, cfg, union_props, wt_col=YC_WT, gend_col=YC_GEND):
    """Get rugby union weighted counts, with smart fallback.

    For 2022-23: uses union column IF it has data for the filtered rows.
    If the union column is all NaN (e.g. ages 7-10), falls back to
    all-rugby × proportion.
    For all other years: always uses all-rugby × proportion.
    """
    ratio = union_props["overall"]

    if cfg["has_union"]:
        # Check if union column actually has data for these rows
        union_vals = filt[YC_UNION]
        n_valid = union_vals.notna().sum()
        n_participants = (union_vals == 1).sum()

        if n_valid > 0 and n_participants > 0:
            # Union column has data — use directly
            return _wt_counts(filt, YC_UNION, wt_col, gend_col)
        elif n_valid > 0 and n_participants == 0:
            # Column exists but nobody participates — genuine zero
            return {"overall": 0.0, "male": 0.0, "female": 0.0}
        else:
            # Column is all NaN for these ages — fall back to proportion
            raw = _wt_counts(filt, YC_ALLRUGBY, wt_col, gend_col)
            return {k: v * ratio for k, v in raw.items()}
    else:
        # No union column — always use proportion
        raw = _wt_counts(filt, YC_ALLRUGBY, wt_col, gend_col)
        return {k: v * ratio for k, v in raw.items()}

def _union_setting_counts(filt, cfg, union_props, wt_col=YC_WT, gend_col=YC_GEND):
    """Get school/outschool union counts with same fallback logic."""
    rs, ro = union_props["school"], union_props["outschool"]

    if cfg["has_union"]:
        n_valid = filt[YC_UNION_SCH].notna().sum()
        if n_valid > 0:
            sch = _wt_counts(filt, YC_UNION_SCH, wt_col, gend_col)
            out = _wt_counts(filt, YC_UNION_OUT, wt_col, gend_col)
            return sch, out
    # Fallback
    sch_raw = _wt_counts(filt, YC_ALLR_SCH, wt_col, gend_col)
    out_raw = _wt_counts(filt, YC_ALLR_OUT, wt_col, gend_col)
    return ({k: v*rs for k,v in sch_raw.items()},
            {k: v*ro for k,v in out_raw.items()})

def _wt_counts_region(df, flag_col, wt_col, gend_col):
    """Return dict of {region: {overall, male, female}}."""
    sel = df[df[flag_col]==1]
    reg = {}
    for r, g in sel.groupby("Region"):
        reg[r] = {"overall": g[wt_col].sum(),
                   "male": g.loc[g[gend_col]==1, wt_col].sum(),
                   "female": g.loc[g[gend_col]==2, wt_col].sum()}
    return reg


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1: Gross comparison + Adult 16–18 sub-output + gender
# ══════════════════════════════════════════════════════════════════════════════

def step1_gross(young_data, adult_data, rfu_data):
    log.info("STEP 1: Gross comparison — All rugby vs RFU + gender + 16–18")
    rows = []
    for label, als_y, rfu_y in ALIGN:
        ydf = young_data[als_y]
        rdf = rfu_data[rfu_y]
        age = pd.to_numeric(ydf[YC_AGE], errors="coerce")
        filt = ydf[(age>=7)&(age<=16)]

        als = _wt_counts(filt, YC_ALLRUGBY, YC_WT, YC_GEND)
        rfu_716 = rfu_sum(rdf, [f"U{a}" for a in range(7,17)])
        rfu_716_m = rfu_sum(rdf, [f"U{a}" for a in range(7,17)], "M")
        rfu_716_f = rfu_sum(rdf, [f"U{a}" for a in range(7,17)], "F")

        # FIX 3: Adult 16–18 sub-output (grossed to population via ONS)
        adf = adult_data.get(als_y)
        if adf is not None:
            a1618 = _adult_pop_estimate(adf, AC_UNION, als_y)
        else:
            a1618 = {"overall":np.nan, "male":np.nan, "female":np.nan}
        rfu_1618 = rfu_sum(rdf, ["U16","U17","U18"])

        rows.append({"Period": label,
            "ALS_AllRugby_7_16": als["overall"],
            "ALS_AllRugby_7_16_M": als["male"], "ALS_AllRugby_7_16_F": als["female"],
            "RFU_U7_U16": rfu_716, "RFU_U7_U16_M": rfu_716_m, "RFU_U7_U16_F": rfu_716_f,
            "ALS_Adult_Union_16_18": a1618["overall"],
            "ALS_Adult_Union_16_18_M": a1618["male"], "ALS_Adult_Union_16_18_F": a1618["female"],
            "RFU_U16_U18": rfu_1618,
        })
    df = pd.DataFrame(rows)
    df["Gap_7_16"] = df["ALS_AllRugby_7_16"] - df["RFU_U7_U16"]
    df.to_csv(OUTPUT_DIR / "step1_gross_comparison.csv", index=False)

    # ── Plot: 3-panel (overall, gender, 16–18) ──
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5.5), gridspec_kw={"wspace":0.30})

    x = np.arange(len(df)); w = 0.32
    ax1.bar(x-w/2, df["ALS_AllRugby_7_16"], w, color=C["als"], alpha=0.85, label="ALS All Rugby (7–16)")
    ax1.bar(x+w/2, df["RFU_U7_U16"], w, color=C["rfu"], alpha=0.85, label="RFU (U7–U16)")
    ax1.set_xticks(x); ax1.set_xticklabels(df["Period"])
    ax1.set_title("A   Overall 7–16"); ax1.legend(fontsize=8); ax1.grid(axis="y", color=C["grid"]); _kfmt(ax1)

    # Gender
    w2 = 0.20
    ax2.bar(x-1.5*w2, df["ALS_AllRugby_7_16_M"], w2, color=C["male"], alpha=0.85, label="ALS Male")
    ax2.bar(x-0.5*w2, df["RFU_U7_U16_M"], w2, color=C["male"], alpha=0.45, label="RFU Male", hatch="//")
    ax2.bar(x+0.5*w2, df["ALS_AllRugby_7_16_F"], w2, color=C["female"], alpha=0.85, label="ALS Female")
    ax2.bar(x+1.5*w2, df["RFU_U7_U16_F"], w2, color=C["female"], alpha=0.45, label="RFU Female", hatch="//")
    ax2.set_xticks(x); ax2.set_xticklabels(df["Period"])
    ax2.set_title("B   Gender Split (7–16)"); ax2.legend(fontsize=7); ax2.grid(axis="y", color=C["grid"]); _kfmt(ax2)

    # Adult 16-18
    has = df.dropna(subset=["ALS_Adult_Union_16_18"]).reset_index(drop=True)
    x3 = np.arange(len(has))
    ax3.bar(x3-w/2, has["ALS_Adult_Union_16_18"], w, color=C["als"], alpha=0.85, label="ALS Union (16–18)")
    ax3.bar(x3+w/2, has["RFU_U16_U18"], w, color=C["rfu"], alpha=0.85, label="RFU (U16–U18)")
    ax3.set_xticks(x3); ax3.set_xticklabels(has["Period"])
    ax3.set_title("C   Adult 16–18 vs RFU"); ax3.legend(fontsize=8); ax3.grid(axis="y", color=C["grid"]); _kfmt(ax3)

    fig.suptitle("Step 1: Gross Comparison — All Rugby + Gender + Adult 16–18", y=1.02, fontsize=14, fontweight="bold")
    _save("step1_gross_comparison")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2: Rugby Union 16–18 + Club Test 1 + gender
# ══════════════════════════════════════════════════════════════════════════════

def step2_union_16_18(adult_data, rfu_data):
    log.info("STEP 2: Rugby Union 16–18 + Club Test 1 + gender")
    rows = []
    for label, als_y, rfu_y in ALIGN:
        adf = adult_data.get(als_y)
        rdf = rfu_data[rfu_y]
        rfu_all = rfu_sum(rdf, ["U16","U17","U18"])
        rfu_m = rfu_sum(rdf, ["U16","U17","U18"], "M")
        rfu_f = rfu_sum(rdf, ["U16","U17","U18"], "F")
        if adf is not None:
            u = _adult_pop_estimate(adf, AC_UNION, als_y)
            cl = _adult_pop_estimate(adf, AC_CLUB, als_y)
        else:
            u = cl = {"overall":np.nan,"male":np.nan,"female":np.nan}
        rows.append({"Period":label,
            "ALS_Union":u["overall"],"ALS_Union_M":u["male"],"ALS_Union_F":u["female"],
            "ALS_Club":cl["overall"],"ALS_Club_M":cl["male"],"ALS_Club_F":cl["female"],
            "ALS_Union_Rate":u.get("rate",np.nan),"ALS_Club_Rate":cl.get("rate",np.nan),
            "ALS_N_Union":u.get("n_unweighted",0),"ALS_N_Club":cl.get("n_unweighted",0),
            "RFU":rfu_all,"RFU_M":rfu_m,"RFU_F":rfu_f})
    df = pd.DataFrame(rows)
    df["Gap_Union"] = df["ALS_Union"] - df["RFU"]
    df["Gap_Club"] = df["ALS_Club"] - df["RFU"]
    df.to_csv(OUTPUT_DIR / "step2_union_16_18.csv", index=False)

    has = df.dropna(subset=["ALS_Union"]).reset_index(drop=True)
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5), gridspec_kw={"wspace":0.28})
    x = np.arange(len(has)); w = 0.32

    # A: Union vs RFU
    ax = axes[0]
    ax.bar(x-w/2, has["ALS_Union"], w, color=C["als"], alpha=0.85, label="ALS Rugby Union")
    ax.bar(x+w/2, has["RFU"], w, color=C["rfu"], alpha=0.85, label="RFU U16–U18")
    for i,r in has.iterrows():
        ax.text(i, max(r["ALS_Union"],r["RFU"])*1.03, f"Δ {r['Gap_Union']:,.0f}",
                ha="center", fontsize=8, color=C["gap"], fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(has["Period"])
    ax.set_title("A   All Union vs RFU"); ax.legend(fontsize=8); ax.grid(axis="y",color=C["grid"]); _kfmt(ax)

    # B: Club Test 1
    ax = axes[1]
    ax.bar(x-w/2, has["ALS_Club"], w, color=C["club"], alpha=0.85, label="ALS Club Union")
    ax.bar(x+w/2, has["RFU"], w, color=C["rfu"], alpha=0.85, label="RFU U16–U18")
    for i,r in has.iterrows():
        ax.text(i, max(r["ALS_Club"],r["RFU"])*1.03, f"Δ {r['Gap_Club']:,.0f}",
                ha="center", fontsize=8, color=C["gap"], fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(has["Period"])
    ax.set_title("B   Club Only vs RFU (Test 1)"); ax.legend(fontsize=8); ax.grid(axis="y",color=C["grid"]); _kfmt(ax)

    # C: Gender
    ax = axes[2]
    w2 = 0.20
    ax.bar(x-1.5*w2, has["ALS_Union_M"], w2, color=C["male"], alpha=0.85, label="ALS Male")
    ax.bar(x-0.5*w2, has["RFU_M"], w2, color=C["male"], alpha=0.45, label="RFU Male", hatch="//")
    ax.bar(x+0.5*w2, has["ALS_Union_F"], w2, color=C["female"], alpha=0.85, label="ALS Female")
    ax.bar(x+1.5*w2, has["RFU_F"], w2, color=C["female"], alpha=0.45, label="RFU Female", hatch="//")
    ax.set_xticks(x); ax.set_xticklabels(has["Period"])
    ax.set_title("C   Gender (16–18)"); ax.legend(fontsize=7); ax.grid(axis="y",color=C["grid"]); _kfmt(ax)

    fig.suptitle("Step 2: Rugby Union 16–18 — Union, Club, Gender", y=1.02, fontsize=14, fontweight="bold")
    _save("step2_union_16_18")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3: CYP any rugby + union estimate + gender
# ══════════════════════════════════════════════════════════════════════════════

def step3_cyp(young_data, rfu_data, union_props):
    log.info("STEP 3: CYP any rugby + union estimate + gender")
    ratio = union_props["overall"]
    rows = []
    for label, als_y, rfu_y in ALIGN:
        ydf = young_data[als_y]; rdf = rfu_data[rfu_y]
        age = pd.to_numeric(ydf[YC_AGE], errors="coerce")
        filt = ydf[(age>=7)&(age<=16)]
        als = _wt_counts(filt, YC_ALLRUGBY, YC_WT, YC_GEND)
        rfu_t = rfu_sum(rdf, [f"U{a}" for a in range(7,17)])
        rfu_m = rfu_sum(rdf, [f"U{a}" for a in range(7,17)], "M")
        rfu_f = rfu_sum(rdf, [f"U{a}" for a in range(7,17)], "F")
        cfg = [c for c in YOUNG_FILES if c["year"]==als_y][0]
        u = _union_counts(filt, cfg, union_props)
        rows.append({"Period":label,
            "ALS_All":als["overall"],"ALS_All_M":als["male"],"ALS_All_F":als["female"],
            "ALS_Union":u["overall"],"ALS_Union_M":u["male"],"ALS_Union_F":u["female"],
            "RFU":rfu_t,"RFU_M":rfu_m,"RFU_F":rfu_f})
    df = pd.DataFrame(rows)
    df["Gap_All"] = df["ALS_All"] - df["RFU"]
    df["Gap_Union"] = df["ALS_Union"] - df["RFU"]
    df.to_csv(OUTPUT_DIR / "step3_cyp_any_rugby.csv", index=False)

    fig, (ax1,ax2) = plt.subplots(1, 2, figsize=(15,6), gridspec_kw={"wspace":0.28})
    x = np.arange(len(df)); w = 0.25

    ax1.bar(x-w, df["ALS_All"], w, color=C["als"], alpha=0.5, label="ALS All Rugby")
    ax1.bar(x, df["ALS_Union"], w, color=C["als"], alpha=0.85, label=f"ALS Union Est. (×{ratio:.2f})")
    ax1.bar(x+w, df["RFU"], w, color=C["rfu"], alpha=0.85, label="RFU U7–U16")
    ax1.set_xticks(x); ax1.set_xticklabels(df["Period"])
    ax1.set_title("A   Triple Comparison (7–16)"); ax1.legend(fontsize=8); ax1.grid(axis="y",color=C["grid"]); _kfmt(ax1)

    # Gender
    w2 = 0.20
    ax2.bar(x-1.5*w2, df["ALS_Union_M"], w2, color=C["male"], alpha=0.85, label="ALS Union Male")
    ax2.bar(x-0.5*w2, df["RFU_M"], w2, color=C["male"], alpha=0.45, label="RFU Male", hatch="//")
    ax2.bar(x+0.5*w2, df["ALS_Union_F"], w2, color=C["female"], alpha=0.85, label="ALS Union Female")
    ax2.bar(x+1.5*w2, df["RFU_F"], w2, color=C["female"], alpha=0.45, label="RFU Female", hatch="//")
    ax2.set_xticks(x); ax2.set_xticklabels(df["Period"])
    ax2.set_title("B   Gender Split — Union Est. vs RFU"); ax2.legend(fontsize=7); ax2.grid(axis="y",color=C["grid"]); _kfmt(ax2)

    fig.suptitle("Step 3: CYP Rugby (7–16) — All, Union Estimate, RFU + Gender", y=1.02, fontsize=14, fontweight="bold")
    _save("step3_cyp_any_rugby")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4: Setting decomposition + "Both" category + gender
# ══════════════════════════════════════════════════════════════════════════════

def step4_setting(young_data, rfu_data, union_props):
    log.info("STEP 4: Setting decomposition + Both + gender")
    rs, ro = union_props["school"], union_props["outschool"]
    rows = []
    for label, als_y, rfu_y in ALIGN:
        ydf = young_data[als_y]; rdf = rfu_data[rfu_y]
        age = pd.to_numeric(ydf[YC_AGE], errors="coerce")
        filt = ydf[(age>=7)&(age<=16)]
        cfg = [c for c in YOUNG_FILES if c["year"]==als_y][0]

        # Counts for each setting
        sch = _wt_counts(filt, YC_ALLR_SCH, YC_WT, YC_GEND)
        out = _wt_counts(filt, YC_ALLR_OUT, YC_WT, YC_GEND)
        # FIX 5: "Both" = school AND outside-school
        both_mask = (filt[YC_ALLR_SCH]==1) & (filt[YC_ALLR_OUT]==1)
        both_sel = filt[both_mask]
        both = {"overall": both_sel[YC_WT].sum(),
                "male": both_sel.loc[both_sel[YC_GEND]==1, YC_WT].sum(),
                "female": both_sel.loc[both_sel[YC_GEND]==2, YC_WT].sum()}

        if cfg["has_union"]:
            sch_u, out_u = _union_setting_counts(filt, cfg, union_props)
        else:
            sch_u = {k: v*rs for k,v in sch.items()}
            out_u = {k: v*ro for k,v in out.items()}

        rfu_t = rfu_sum(rdf, [f"U{a}" for a in range(7,17)])

        rows.append({"Period":label,
            "School_All":sch["overall"],"School_All_M":sch["male"],"School_All_F":sch["female"],
            "OutSchool_All":out["overall"],"OutSchool_All_M":out["male"],"OutSchool_All_F":out["female"],
            "Both_All":both["overall"],"Both_All_M":both["male"],"Both_All_F":both["female"],
            "School_Union":sch_u["overall"],"OutSchool_Union":out_u["overall"],
            "School_Union_M":sch_u["male"],"OutSchool_Union_M":out_u["male"],
            "School_Union_F":sch_u["female"],"OutSchool_Union_F":out_u["female"],
            "RFU":rfu_t})

    df = pd.DataFrame(rows)
    df["School_Share_%"] = df["School_Union"] / (df["School_Union"]+df["OutSchool_Union"]) * 100
    df.to_csv(OUTPUT_DIR / "step4_setting_decomposition.csv", index=False)

    fig, axes = plt.subplots(1, 3, figsize=(18,5.5), gridspec_kw={"wspace":0.30})
    x = np.arange(len(df)); w = 0.20

    # A: Setting bars
    ax = axes[0]
    ax.bar(x-1.5*w, df["School_Union"], w, color=C["school"], alpha=0.85, label="In-School Union")
    ax.bar(x-0.5*w, df["OutSchool_Union"], w, color=C["outschool"], alpha=0.85, label="Outside-School Union")
    ax.bar(x+0.5*w, df["Both_All"], w, color="#6366F1", alpha=0.7, label="Both Settings (all rugby)")
    ax.bar(x+1.5*w, df["RFU"], w, color=C["rfu"], alpha=0.85, label="RFU U7–U16")
    ax.set_xticks(x); ax.set_xticklabels(df["Period"])
    ax.set_title("A   Setting Decomposition"); ax.legend(fontsize=7); ax.grid(axis="y",color=C["grid"]); _kfmt(ax)

    # B: School share trend
    ax = axes[1]
    ax.plot(df["Period"], df["School_Share_%"], "o-", color=C["school"], lw=2.5, ms=8)
    ax.fill_between(df["Period"], df["School_Share_%"], alpha=0.15, color=C["school"])
    for i,r in df.iterrows():
        ax.text(i, r["School_Share_%"]+1.5, f"{r['School_Share_%']:.1f}%",
                ha="center", fontsize=9, fontweight="bold", color=C["school"])
    ax.set_ylabel("% at School"); ax.set_title("B   School Share Trend")
    ax.set_ylim(0,100); ax.grid(axis="y",color=C["grid"])

    # C: Gender by setting
    ax = axes[2]
    ax.bar(x-1.5*w, df["School_Union_M"], w, color=C["male"], alpha=0.85, label="School Male")
    ax.bar(x-0.5*w, df["School_Union_F"], w, color=C["female"], alpha=0.85, label="School Female")
    ax.bar(x+0.5*w, df["OutSchool_Union_M"], w, color=C["male"], alpha=0.45, label="OutSchool Male", hatch="//")
    ax.bar(x+1.5*w, df["OutSchool_Union_F"], w, color=C["female"], alpha=0.45, label="OutSchool Female", hatch="//")
    ax.set_xticks(x); ax.set_xticklabels(df["Period"])
    ax.set_title("C   Gender × Setting"); ax.legend(fontsize=7); ax.grid(axis="y",color=C["grid"]); _kfmt(ax)

    fig.suptitle("Step 4: School vs Outside-School Rugby Union (7–16)", y=1.02, fontsize=14, fontweight="bold")
    fig.text(0.5, -0.02, "Note: 'Outside school' includes club, informal, and other non-school settings — "
             "it is NOT equivalent to 'club only'.", ha="center", fontsize=8, color="#6B7280", style="italic")
    _save("step4_setting_decomposition")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# STEP 5: Age-band aligned + gender
# ══════════════════════════════════════════════════════════════════════════════

def step5_age_bands(young_data, adult_data, rfu_data, union_props):
    log.info("STEP 5: Age-band aligned + gender")
    ratio = union_props["overall"]
    rows = []
    for label, als_y, rfu_y in ALIGN:
        ydf = young_data[als_y]; rdf = rfu_data[rfu_y]; adf = adult_data.get(als_y)
        age = pd.to_numeric(ydf[YC_AGE], errors="coerce")
        cfg = [c for c in YOUNG_FILES if c["year"]==als_y][0]

        for bl, ages_y, pfx in AGE_BANDS:
            if bl == "16–18":
                if adf is not None:
                    u = _adult_pop_estimate(adf, AC_UNION, als_y)
                else:
                    u = {"overall":np.nan,"male":np.nan,"female":np.nan}
                rfu_t = rfu_sum(rdf, pfx)
                rfu_m = rfu_sum(rdf, pfx, "M")
                rfu_f = rfu_sum(rdf, pfx, "F")
            else:
                filt = ydf[age.isin(ages_y)]
                u = _union_counts(filt, cfg, union_props)
                rfu_t = rfu_sum(rdf, pfx)
                rfu_m = rfu_sum(rdf, pfx, "M")
                rfu_f = rfu_sum(rdf, pfx, "F")

            rows.append({"Period":label,"Age_Band":bl,
                "ALS":u["overall"],"ALS_M":u["male"],"ALS_F":u["female"],
                "RFU":rfu_t,"RFU_M":rfu_m,"RFU_F":rfu_f})

    df = pd.DataFrame(rows)
    df["Gap"] = df["ALS"] - df["RFU"]
    df["Capture_%"] = np.where(df["ALS"]>0, df["RFU"]/df["ALS"]*100, np.nan)
    df.to_csv(OUTPUT_DIR / "step5_age_bands.csv", index=False)

    # Heatmap
    pivot = df.pivot_table(index="Age_Band", columns="Period", values="Capture_%")
    order = [b[0] for b in AGE_BANDS]
    pivot = pivot.reindex([b for b in order if b in pivot.index])
    fig, ax = plt.subplots(figsize=(11,5.5))
    data = pivot.values
    im = ax.imshow(data, aspect="auto", cmap="RdYlGn", vmin=0, vmax=min(np.nanmax(data)*1.1,200))
    ax.set_xticks(range(pivot.shape[1])); ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(pivot.shape[0])); ax.set_yticklabels(pivot.index)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data[i,j]
            if np.isnan(v): ax.text(j,i,"N/A",ha="center",va="center",fontsize=9,color="#999"); continue
            c = "white" if v<40 or v>150 else C["text"]
            ax.text(j,i,f"{v:.0f}%",ha="center",va="center",fontsize=10,fontweight="bold",color=c)
    ax.set_title("Step 5: Capture Rate by Age Band × Period"); fig.colorbar(im, ax=ax, shrink=0.7)
    _save("step5_age_band_heatmap")

    # Latest year bars with gender
    latest = df[df["Period"]==ALIGN[-1][0]].copy().reset_index(drop=True)
    fig, (ax1,ax2) = plt.subplots(1, 2, figsize=(15,6), gridspec_kw={"wspace":0.25})
    x = np.arange(len(latest)); w = 0.32
    ax1.bar(x-w/2, latest["ALS"], w, color=C["als"], alpha=0.85, label="ALS Union")
    ax1.bar(x+w/2, latest["RFU"], w, color=C["rfu"], alpha=0.85, label="RFU")
    for i,(_,r) in enumerate(latest.iterrows()):
        if not np.isnan(r["Gap"]):
            ax1.text(i, max(r["ALS"],r["RFU"])*1.03, f"Δ {r['Gap']:,.0f}",
                     ha="center",fontsize=8,color=C["gap"],fontweight="bold")
    ax1.set_xticks(x); ax1.set_xticklabels(latest["Age_Band"])
    ax1.set_title(f"A   Age Bands — {ALIGN[-1][0]}"); ax1.legend(); ax1.grid(axis="y",color=C["grid"]); _kfmt(ax1)

    # Gender by age band
    w2 = 0.20
    ax2.bar(x-1.5*w2, latest["ALS_M"], w2, color=C["male"], alpha=0.85, label="ALS Male")
    ax2.bar(x-0.5*w2, latest["RFU_M"], w2, color=C["male"], alpha=0.45, label="RFU Male", hatch="//")
    ax2.bar(x+0.5*w2, latest["ALS_F"], w2, color=C["female"], alpha=0.85, label="ALS Female")
    ax2.bar(x+1.5*w2, latest["RFU_F"], w2, color=C["female"], alpha=0.45, label="RFU Female", hatch="//")
    ax2.set_xticks(x); ax2.set_xticklabels(latest["Age_Band"])
    ax2.set_title(f"B   Gender × Age Band — {ALIGN[-1][0]}"); ax2.legend(fontsize=7); ax2.grid(axis="y",color=C["grid"]); _kfmt(ax2)

    fig.suptitle("Step 5: Age-Band Comparison — Overall + Gender", y=1.02, fontsize=14, fontweight="bold")
    _save("step5_age_band_bars")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# STEP 6: Timeline documentation
# ══════════════════════════════════════════════════════════════════════════════

def step6_doc(union_props):
    log.info("STEP 6: Documentation")
    doc = pd.DataFrame([
        {"Dataset":"ALS CYP","Years":"2017–2023","Age":"5–16",
         "Union_Col":"GR_RUGBYUNION_CD0182 (2022-23 only)",
         "AllRugby_Col":"GR_RUGBY_CC018 (all years)",
         "Setting":"inschool/outschool (all years)","Club_Col":"N/A",
         "Weight":"wt_gross","Correction":f"×{union_props['overall']:.4f}"},
        {"Dataset":"ALS Adult","Years":"2017–2022","Age":"16–18 (filtered)",
         "Union_Col":"MONTHS_12_RUGBYUNION_F03","AllRugby_Col":"N/A",
         "Setting":"N/A","Club_Col":"CLUB_RUGBYUNION_F03",
         "Weight":"wt_final (normalised → rate × ONS pop)","Correction":"Grossed via ONS 16–18 population"},
        {"Dataset":"RFU GMS","Years":"2018–2024","Age":"U7–U18",
         "Union_Col":"All union by definition","AllRugby_Col":"N/A",
         "Setting":"Club only","Club_Col":"All club",
         "Weight":"Headcount","Correction":"None"},
    ])
    doc.to_csv(OUTPUT_DIR / "step6_variable_documentation.csv", index=False)

    fig, ax = plt.subplots(figsize=(14,5))
    ax.set_xlim(2016.5,2024.5); ax.set_ylim(-0.5,6.5); ax.set_yticks([])
    items = [
        ("ALS CYP All Rugby",0,2017,2023,C["als"],0.6),
        ("ALS CYP Rugby Union",1,2022,2023,C["als"],1.0),
        ("ALS CYP School/OutSchool",2,2017,2023,C["school"],0.7),
        ("ALS Adult Rugby Union",3,2017,2022,C["club"],0.8),
        ("ALS Adult Club Union",4,2017,2022,C["club"],1.0),
        ("RFU GMS (U7–U18)",5,2018,2024,C["rfu"],0.8),
    ]
    for lbl,y,s,e,col,a in items:
        ax.barh(y, e-s, left=s, height=0.6, color=col, alpha=a, edgecolor="white", lw=1.5)
        ax.text(s-0.1, y, lbl, ha="right", va="center", fontsize=9, fontweight="bold")
        ax.text((s+e)/2, y, f"{s}–{e}", ha="center", va="center", fontsize=8, color="white", fontweight="bold")
    ax.set_xlabel("Year"); ax.set_title("Step 6: Data Availability Timeline", pad=12)
    ax.grid(axis="x", color=C["grid"]); ax.invert_yaxis()
    _save("step6_timeline")
    return doc


# ══════════════════════════════════════════════════════════════════════════════
# FIX 1: Q6 Regional/Geographic Analysis
# ══════════════════════════════════════════════════════════════════════════════

def step_regional(young_data, adult_data, rfu_data, union_props):
    """Q6: Regional differences — ALS vs RFU by English region."""
    log.info("REGIONAL: Geographic gap analysis")
    ratio = union_props["overall"]
    rows = []

    for label, als_y, rfu_y in ALIGN:
        ydf = young_data[als_y]; rdf = rfu_data[rfu_y]
        age = pd.to_numeric(ydf[YC_AGE], errors="coerce")
        filt = ydf[(age>=7)&(age<=16)]
        cfg = [c for c in YOUNG_FILES if c["year"]==als_y][0]

        # ALS by region (7-16) — always use all-rugby × proportion
        # This avoids the NaN issue where union column doesn't cover ages 7-10
        als_reg_raw = _wt_counts_region(filt, YC_ALLRUGBY, YC_WT, YC_GEND)
        als_reg = {r: {k: v*ratio for k,v in d.items()} for r,d in als_reg_raw.items()}

        # Add Adult 17-18 by region (grossed to population)
        adf = adult_data.get(als_y)
        adult_reg = {}
        if adf is not None and "Region" in adf.columns:
            pop = ONS_POP_16_18.get(als_y, 1_900_000)
            total_wt = adf[AC_WT].sum()
            grossing_factor = pop / total_wt if total_wt > 0 else 1
            raw_reg = _wt_counts_region(adf, AC_UNION, AC_WT, AC_GEND)
            adult_reg = {r: {k: v * grossing_factor for k,v in d.items()}
                         for r, d in raw_reg.items()}

        # RFU by region
        rfu_reg = rfu_regional(rdf, [f"U{a}" for a in range(7,19)])

        all_regions = set(list(als_reg.keys()) + list(rfu_reg.keys()))
        for reg in all_regions:
            a = als_reg.get(reg, {"overall":0,"male":0,"female":0})
            ar = adult_reg.get(reg, {"overall":0,"male":0,"female":0})
            r_val = rfu_reg.get(reg, 0)
            als_combined = a["overall"] + ar["overall"]
            rows.append({"Period":label, "Region":reg,
                "ALS_7_16":a["overall"],"ALS_17_18":ar["overall"],
                "ALS_Combined":als_combined,
                "ALS_M":a["male"]+ar["male"], "ALS_F":a["female"]+ar["female"],
                "RFU":r_val})

    df = pd.DataFrame(rows)
    df["Gap"] = df["ALS_Combined"] - df["RFU"]
    df["Capture_%"] = np.where(df["ALS_Combined"]>0, df["RFU"]/df["ALS_Combined"]*100, np.nan)
    df.to_csv(OUTPUT_DIR / "regional_gap_analysis.csv", index=False)

    # Heatmap: capture % by region × period
    pivot = df.pivot_table(index="Region", columns="Period", values="Capture_%")
    pivot = pivot.loc[pivot.mean(axis=1).sort_values().index]

    fig, ax = plt.subplots(figsize=(11,6.5))
    data = pivot.values
    im = ax.imshow(data, aspect="auto", cmap="RdYlGn", vmin=0, vmax=min(np.nanmax(data)*1.1,200))
    ax.set_xticks(range(pivot.shape[1])); ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(pivot.shape[0])); ax.set_yticklabels(pivot.index)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data[i,j]
            if np.isnan(v): continue
            c = "white" if v<40 or v>150 else C["text"]
            ax.text(j,i,f"{v:.0f}%",ha="center",va="center",fontsize=9.5,fontweight="bold",color=c)
    ax.set_title("Q6: Regional Capture Rate (RFU ÷ ALS Rugby Union × 100)", pad=14)
    fig.colorbar(im, ax=ax, label="Capture %", shrink=0.7)
    _save("regional_capture_heatmap")

    # Gap bars latest
    latest = df[df["Period"]==ALIGN[-1][0]].sort_values("Gap", ascending=True)
    fig, (ax1,ax2) = plt.subplots(1, 2, figsize=(16,6), gridspec_kw={"wspace":0.30})

    cols = [C["gap"] if g>0 else C["green"] for g in latest["Gap"]]
    ax1.barh(latest["Region"], latest["Gap"], color=cols, height=0.6, edgecolor="white")
    ax1.axvline(0, color=C["text"], lw=0.8)
    for bar,v in zip(ax1.patches, latest["Gap"]):
        off = max(abs(latest["Gap"]).max()*0.02, 10)
        ax1.text(v+(off if v>=0 else -off), bar.get_y()+bar.get_height()/2,
                 f"{v:,.0f}", va="center", ha="left" if v>=0 else "right", fontsize=9, fontweight="bold")
    ax1.set_title(f"A   Regional Gap — {ALIGN[-1][0]}"); ax1.grid(axis="x",color=C["grid"]); _kfmt(ax1,"x")

    # Gender gap by region
    ax2.barh(latest["Region"], latest["ALS_M"]-latest["RFU"]*0.85, height=0.3,
             color=C["male"], alpha=0.85, label="Male gap (approx)")
    ax2.barh([r for r in latest["Region"]], latest["ALS_F"]-latest["RFU"]*0.15, height=0.3,
             color=C["female"], alpha=0.85, label="Female gap (approx)")
    ax2.axvline(0, color=C["text"], lw=0.8)
    ax2.set_title(f"B   Gender Gap by Region — {ALIGN[-1][0]}"); ax2.legend(fontsize=8)
    ax2.grid(axis="x",color=C["grid"]); _kfmt(ax2,"x")

    fig.suptitle("Q6: Regional Geographic Gap Analysis", y=1.02, fontsize=14, fontweight="bold")
    _save("regional_gap_bars")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# Summary Dashboard
# ══════════════════════════════════════════════════════════════════════════════

def summary_dashboard(s1, s2, s3, s4, s5, s_reg):
    log.info("Summary dashboard")
    fig = plt.figure(figsize=(18, 12))
    gs = GridSpec(3, 3, hspace=0.45, wspace=0.35)
    ll = ALIGN[-1][0]

    def _card(ax, title, items):
        ax.axis("off"); ax.set_title(title, fontsize=12, loc="left")
        for i,(lbl,val,col) in enumerate(items):
            ax.text(0.05, 0.78-i*0.22, lbl, fontsize=10, color="#6B7280", transform=ax.transAxes)
            ax.text(0.95, 0.78-i*0.22, val, fontsize=15, fontweight="bold", color=col, ha="right", transform=ax.transAxes)

    # Q1
    r2 = s2.dropna(subset=["ALS_Club"]).iloc[-1]
    _card(fig.add_subplot(gs[0,0]), "Q1: Club Rugby ≈ RFU?", [
        ("ALS Club Union 16–18", f"{r2['ALS_Club']:,.0f}", C["club"]),
        ("RFU U16–U18", f"{r2['RFU']:,.0f}", C["rfu"]),
        ("Δ", f"{r2['Gap_Club']:,.0f}", C["gap"])])

    # Q2
    r3 = s3[s3["Period"]==ll].iloc[0]
    _card(fig.add_subplot(gs[0,1]), "Q2: Non-Registered Players?", [
        ("ALS Union Est. (7–16)", f"{r3['ALS_Union']:,.0f}", C["als"]),
        ("RFU U7–U16", f"{r3['RFU']:,.0f}", C["rfu"]),
        ("Non-registered", f"{r3['Gap_Union']:,.0f}", C["gap"])])

    # Q3
    r4 = s4[s4["Period"]==ll].iloc[0]
    _card(fig.add_subplot(gs[0,2]), "Q3: School as Feeder?", [
        ("School Rugby Union", f"{r4['School_Union']:,.0f}", C["school"]),
        ("Outside-School Union", f"{r4['OutSchool_Union']:,.0f}", C["outschool"]),
        ("School Share", f"{r4['School_Share_%']:.1f}%", C["school"])])

    # Q4: Capture trend
    ax = fig.add_subplot(gs[1,0])
    cap = s3.copy()
    cap["Cap"] = np.where(cap["ALS_Union"]>0, cap["RFU"]/cap["ALS_Union"]*100, np.nan)
    ax.plot(cap["Period"], cap["Cap"], "o-", color=C["gap"], lw=2.5, ms=8)
    for i,r in cap.iterrows():
        if not np.isnan(r["Cap"]):
            ax.text(i, r["Cap"]+2, f"{r['Cap']:.0f}%", ha="center", fontsize=9, fontweight="bold", color=C["gap"])
    ax.set_title("Q4: Registration Trend"); ax.set_ylabel("Capture %"); ax.grid(axis="y",color=C["grid"])
    ax.tick_params(axis="x", rotation=30)

    # Q5: Age leakage
    ax = fig.add_subplot(gs[1,1:3])
    s5l = s5[s5["Period"]==ll].reset_index(drop=True)
    x = np.arange(len(s5l)); w = 0.32
    ax.bar(x-w/2, s5l["ALS"], w, color=C["als"], alpha=0.85, label="ALS Union")
    ax.bar(x+w/2, s5l["RFU"], w, color=C["rfu"], alpha=0.85, label="RFU")
    ax.set_xticks(x); ax.set_xticklabels(s5l["Age_Band"])
    ax.set_title("Q5: Age-Band Leakage"); ax.legend(); ax.grid(axis="y",color=C["grid"]); _kfmt(ax)

    # Q6: Regional
    ax = fig.add_subplot(gs[2,:])
    reg_latest = s_reg[s_reg["Period"]==ll].sort_values("Capture_%")
    x = np.arange(len(reg_latest))
    ax.barh(reg_latest["Region"], reg_latest["Capture_%"], color=C["gap"], alpha=0.8, height=0.6)
    for i,(_,r) in enumerate(reg_latest.iterrows()):
        if not np.isnan(r["Capture_%"]):
            ax.text(r["Capture_%"]+1, i, f"{r['Capture_%']:.0f}% (gap: {r['Gap']:,.0f})",
                    va="center", fontsize=9)
    ax.set_xlabel("Capture Rate (%)"); ax.set_title("Q6: Regional Capture Rate")
    ax.grid(axis="x",color=C["grid"])

    fig.suptitle("Stratified Analysis — All Core Questions", y=1.01, fontsize=16, fontweight="bold")
    _save("summary_dashboard")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def run_all():
    os.chdir(BASE_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log.info("Working dir: %s | Output: %s", BASE_DIR, OUTPUT_DIR)

    log.info("=" * 60); log.info("Loading data")
    young_data = {c["year"]: load_young(c) for c in YOUNG_FILES}
    adult_data = {c["year"]: load_adult(c) for c in ADULT_FILES if load_adult(c) is not None}
    # Reload adults properly (load_adult returns None for young_dups)
    adult_data = {}
    for c in ADULT_FILES:
        df = load_adult(c)
        if df is not None: adult_data[c["year"]] = df
    rfu_data = load_rfu()
    uprops = compute_union_proportion()

    log.info("=" * 60); log.info("Exporting cleaned yearly files")
    export_cleaned_files(young_data, adult_data, uprops)

    log.info("=" * 60)
    s1 = step1_gross(young_data, adult_data, rfu_data)
    log.info("=" * 60)
    s2 = step2_union_16_18(adult_data, rfu_data)
    log.info("=" * 60)
    s3 = step3_cyp(young_data, rfu_data, uprops)
    log.info("=" * 60)
    s4 = step4_setting(young_data, rfu_data, uprops)
    log.info("=" * 60)
    s5 = step5_age_bands(young_data, adult_data, rfu_data, uprops)
    log.info("=" * 60)
    s6 = step6_doc(uprops)
    log.info("=" * 60)
    s_reg = step_regional(young_data, adult_data, rfu_data, uprops)
    log.info("=" * 60)
    summary_dashboard(s1, s2, s3, s4, s5, s_reg)

    log.info("=" * 60)
    log.info("ALL STEPS COMPLETE ✓ — Outputs → %s", OUTPUT_DIR)


if __name__ == "__main__":
    run_all()
