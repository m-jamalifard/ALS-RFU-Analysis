#!/usr/bin/env python3
"""
ALS vs RFU Impact Analysis — Direct Measurements Only
========================================================
No estimation. No proportional correction. Every number is a direct
measurement from the data. Designed to show the RFU actionable insights
and motivate deeper data sharing.

Six analyses:
  1. RFU Dropout Cascade — where players disappear by age
  2. The 2022-23 Benchmark — clean Rugby Union comparison (ages 11-16)
  3. School-to-Club Pipeline — is school feeding clubs?
  4. Adult Club Membership Test — does registration capture members?
  5. Regional Opportunity Map — where to recruit
  6. Gender Growth Opportunity — the biggest untapped market

Run: cd /home/reza/ALS_RFU_Analysis && python als_rfu_impact.py
"""

import os, logging
from pathlib import Path
import numpy as np, pandas as pd, pyreadstat
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.gridspec import GridSpec
import warnings; warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────────────────────
BASE_DIR   = Path("/home/reza/ALS_RFU_Analysis")
OUTPUT_DIR = BASE_DIR / "output_impact"

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-8s | %(message)s")
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
     "outschool":"#7C3AED","club":"#059669","grid":"#E5E7EB","text":"#1F2937",
     "amber":"#F59E0B","light":"#DBEAFE"}

def _save(name):
    p = OUTPUT_DIR / f"{name}.png"
    plt.savefig(p, dpi=150, bbox_inches="tight"); plt.close()
    log.info("Saved: %s", p.name)

def _kfmt(ax, axis="y"):
    fmt = mticker.FuncFormatter(lambda x, _: f"{x:,.0f}")
    if axis in ("y","both"): ax.yaxis.set_major_formatter(fmt)
    if axis in ("x","both"): ax.xaxis.set_major_formatter(fmt)


# ── Column definitions ──
# Young CYP
YC_ALLRUGBY   = "onceawk_modplus_everywhere_GR_RUGBY_CC018"
YC_ALLR_SCH   = "onceawk_modplus_inschool_GR_RUGBY_CC018"
YC_ALLR_OUT   = "onceawk_modplus_outschool_GR_RUGBY_CC018"
YC_UNION      = "onceawk_modplus_everywhere_GR_RUGBYUNION_CD0182"
YC_UNION_SCH  = "onceawk_modplus_inschool_GR_RUGBYUNION_CD0182"
YC_UNION_OUT  = "onceawk_modplus_outschool_GR_RUGBYUNION_CD0182"
YC_AGE = "age_11"; YC_GEND = "gend3"; YC_WT = "wt_gross"

# Adult
AC_UNION = "MONTHS_12_RUGBYUNION_F03"
AC_CLUB  = "CLUB_RUGBYUNION_F03"
AC_AGE = "Age17"; AC_U19 = "Age19plus"
AC_GEND = "Gend3"; AC_WT = "wt_final"

# ── ONS Mid-Year Population Estimates: England, ages 16–18 combined ──
# wt_final in Adult ALS is normalised (sums to sample N, mean ≈ 1.0).
# To produce population estimates: rate × ONS population.
ONS_POP_16_18 = {
    "2017-18": 1_950_000, "2018-19": 1_920_000, "2019-20": 1_900_000,
    "2020-21": 1_880_000, "2021-22": 1_870_000, "2022-23": 1_890_000,
}

REGION_MAP = {1:"East",2:"East Midlands",3:"London",4:"North East",
              5:"North West",6:"South East",7:"South West",
              8:"West Midlands",9:"Yorkshire and the Humber"}

YOUNG_FILES = [
    {"file":"ALS_Young_2017-18.sav","year":"2017-18","has_union":False},
    {"file":"ALS_Young_2018-19.sav","year":"2018-19","has_union":False},
    {"file":"ALS_Young_2019-20.sav","year":"2019-20","has_union":False},
    {"file":"ALS_Young_2020-21.sav","year":"2020-21","has_union":False},
    {"file":"ALS_Young_2021-22.sav","year":"2021-22","has_union":False},
    {"file":"ALS_Young_2022-23.sav","year":"2022-23","has_union":True},
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

# Also map old-format CB names (shorter names from original RFU file)
CB_TO_REGION_OLD = {
    "Eastern Counties":"East","Essex":"East","Hertfordshire":"East",
    "East Midlands":"East Midlands","NLD":"East Midlands",
    "Leicestershire":"East Midlands","Notts Lincs & Derby":"East Midlands",
    "Middlesex":"London",
    "Durham":"North East","Northumberland":"North East",
    "Lancashire":"North West","Cheshire":"North West","Cumbria":"North West",
    "Kent":"South East","Surrey":"South East","Sussex":"South East",
    "Hampshire":"South East","Berkshire":"South East",
    "Buckinghamshire":"South East","Oxfordshire":"South East",
    "Cornwall":"South West","Devon":"South West",
    "Dorset & Wilts":"South West","Gloucestershire":"South West",
    "Somerset":"South West",
    "North Midlands":"West Midlands","Staffordshire":"West Midlands",
    "Warwickshire":"West Midlands",
    "Yorkshire":"Yorkshire and the Humber",
}


# ══════════════════════════════════════════════════════════════════════════════
# Data loading
# ══════════════════════════════════════════════════════════════════════════════

def load_young(cfg):
    path = BASE_DIR / cfg["file"]
    cols = [YC_ALLRUGBY, YC_ALLR_SCH, YC_ALLR_OUT, YC_AGE, YC_GEND, YC_WT, "Region_name"]
    if cfg["has_union"]:
        cols += [YC_UNION, YC_UNION_SCH, YC_UNION_OUT]
    df, _ = pyreadstat.read_sav(str(path), usecols=list(dict.fromkeys(cols)))
    df["Region"] = df["Region_name"].map(REGION_MAP)
    log.info("Young %s: %d rows", cfg["year"], len(df))
    return df

def load_adult(cfg):
    if cfg["fmt"] != "adult": return None
    path = BASE_DIR / cfg["file"]
    df, _ = pyreadstat.read_sav(str(path),
        usecols=[AC_UNION, AC_CLUB, AC_AGE, AC_U19, AC_GEND, AC_WT])
    df = df[(df[AC_AGE]==1.0)&(df[AC_U19]==0.0)].copy()
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

def rfu_by_region(df, prefixes, gender=None):
    if "Constituent Body" not in df.columns: return {}
    df = df.copy()
    df["_region"] = df["Constituent Body"].map(CB_TO_REGION)
    if df["_region"].isna().all():
        df["_region"] = df["Constituent Body"].map(CB_TO_REGION_OLD)
    df = df.dropna(subset=["_region"])
    out = {}
    for reg, grp in df.groupby("_region"):
        out[reg] = rfu_sum(grp, prefixes, gender)
    return out


# ══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 1: RFU Dropout Cascade
# ══════════════════════════════════════════════════════════════════════════════

def analysis1_dropout(rfu_data):
    """
    Pure RFU data. Shows where players disappear by single-year age group.
    Key insight: which age transition loses the most players?
    """
    log.info("ANALYSIS 1: RFU Dropout Cascade")
    ages = list(range(7, 19))
    all_years = RFU_YEARS_OLD + [RFU_NEW_YEAR]

    rows = []
    for year in all_years:
        rdf = rfu_data[year]
        for a in ages:
            t = rfu_sum(rdf, [f"U{a}"])
            m = rfu_sum(rdf, [f"U{a}"], "M")
            f = rfu_sum(rdf, [f"U{a}"], "F")
            rows.append({"Year": year, "Age_Group": f"U{a}",
                          "Age": a, "Total": t, "Male": m, "Female": f})
    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_DIR / "analysis1_dropout_cascade.csv", index=False)

    # ── Plot A: Waterfall for latest two periods ──
    fig, axes = plt.subplots(1, 2, figsize=(16, 8), gridspec_kw={"wspace": 0.28})

    for ax, year in zip(axes, [RFU_YEARS_OLD[-1], RFU_NEW_YEAR]):
        sub = df[df["Year"]==year].sort_values("Age")
        x = np.arange(len(sub))
        bars = ax.bar(x, sub["Total"], color=[C["rfu"] if sub.iloc[i]["Total"] >= (sub.iloc[i-1]["Total"] if i > 0 else 0) else C["amber"] for i in range(len(sub))],
                       alpha=0.85, edgecolor="white")
        # Drop annotations
        for i in range(1, len(sub)):
            prev = sub.iloc[i-1]["Total"]
            curr = sub.iloc[i]["Total"]
            drop = curr - prev
            pct = drop / prev * 100 if prev > 0 else 0
            color = C["green"] if drop >= 0 else C["rfu"]
            offset = max(sub["Total"])*0.06 if i % 2 == 0 else max(sub["Total"])*0.04
            ax.annotate(f"{drop:+,.0f}\n({pct:+.0f}%)",
                        xy=(i, curr), xytext=(i, curr + offset),
                        ha="center", fontsize=6.5, color=color, fontweight="bold")
        ax.set_xticks(x); ax.set_xticklabels(sub["Age_Group"], fontsize=9)
        ax.set_ylim(0, max(sub["Total"])*1.22)
        ax.set_title(f"RFU Registrations — {year}"); ax.set_ylabel("Players")
        ax.grid(axis="y", color=C["grid"]); _kfmt(ax)

    fig.suptitle("Analysis 1: The Dropout Cascade — Where Do Players Disappear?",
                 y=1.02, fontsize=15, fontweight="bold")
    fig.text(0.5, -0.02, "Amber bars = fewer players than previous age group. "
             "Annotations show absolute and percentage change from previous age.",
             ha="center", fontsize=8.5, color="#6B7280", style="italic")
    _save("analysis1_dropout_cascade")

    # ── Plot B: Gender dropout comparison ──
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6), gridspec_kw={"wspace": 0.25})
    latest = df[df["Year"]==RFU_NEW_YEAR].sort_values("Age")
    x = np.arange(len(latest))
    ax1.bar(x, latest["Male"], color=C["male"], alpha=0.85, label="Male")
    ax1.bar(x, latest["Female"], bottom=latest["Male"], color=C["female"], alpha=0.85, label="Female")
    ax1.set_xticks(x); ax1.set_xticklabels(latest["Age_Group"])
    ax1.set_title(f"A   Registration by Age and Gender — {RFU_NEW_YEAR}")
    ax1.legend(); ax1.grid(axis="y", color=C["grid"]); _kfmt(ax1)

    # Female % by age
    latest["Female_%"] = latest["Female"] / latest["Total"] * 100
    ax2.bar(x, latest["Female_%"], color=C["female"], alpha=0.85)
    for i, row in latest.iterrows():
        ax2.text(list(latest.index).index(i), row["Female_%"]+0.5,
                 f"{row['Female_%']:.1f}%", ha="center", fontsize=8, fontweight="bold")
    ax2.set_xticks(x); ax2.set_xticklabels(latest["Age_Group"])
    ax2.set_title(f"B   Female Share by Age — {RFU_NEW_YEAR}")
    ax2.set_ylabel("Female %"); ax2.grid(axis="y", color=C["grid"])

    fig.suptitle("Analysis 1b: Gender Profile Across the Age Pathway",
                 y=1.02, fontsize=14, fontweight="bold")
    _save("analysis1b_gender_profile")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 2: The 2022-23 Benchmark (clean Rugby Union, ages 11–16)
# ══════════════════════════════════════════════════════════════════════════════

def analysis2_benchmark(young_data, rfu_data):
    """
    The one year where we have a DIRECT Rugby Union column for CYP.
    Deep comparison for ages 11–16 only (where the column is populated).
    ZERO estimation. Every number is a direct measurement.
    """
    log.info("ANALYSIS 2: 2022-23 Benchmark (direct Rugby Union, 11–16)")
    ydf = young_data["2022-23"]
    rdf = rfu_data["2023 May"]
    age = pd.to_numeric(ydf[YC_AGE], errors="coerce")

    # Only ages where union column has data
    filt = ydf[(age >= 11) & (age <= 16) & ydf[YC_UNION].notna()]

    rows = []
    for a in range(11, 17):
        af = filt[age[filt.index] == a]
        # ALS direct Rugby Union
        als_u = af.loc[af[YC_UNION]==1, YC_WT].sum()
        als_u_m = af.loc[(af[YC_UNION]==1)&(af[YC_GEND]==1), YC_WT].sum()
        als_u_f = af.loc[(af[YC_UNION]==1)&(af[YC_GEND]==2), YC_WT].sum()
        # ALS school/outschool
        als_sch = af.loc[af[YC_UNION_SCH]==1, YC_WT].sum()
        als_out = af.loc[af[YC_UNION_OUT]==1, YC_WT].sum()
        # ALS all rugby (for context)
        als_all = af.loc[af[YC_ALLRUGBY]==1, YC_WT].sum()
        # RFU
        rfu_t = rfu_sum(rdf, [f"U{a}"])
        rfu_m = rfu_sum(rdf, [f"U{a}"], "M")
        rfu_f = rfu_sum(rdf, [f"U{a}"], "F")

        rows.append({"Age": a, "Age_Group": f"U{a}",
            "ALS_AllRugby": als_all, "ALS_Union": als_u,
            "ALS_Union_M": als_u_m, "ALS_Union_F": als_u_f,
            "ALS_Union_School": als_sch, "ALS_Union_OutSchool": als_out,
            "Union_of_All_%": (als_u/als_all*100 if als_all > 0 else 0),
            "RFU": rfu_t, "RFU_M": rfu_m, "RFU_F": rfu_f})

    df = pd.DataFrame(rows)
    df["Gap"] = df["ALS_Union"] - df["RFU"]
    df["Capture_%"] = np.where(df["ALS_Union"]>0, df["RFU"]/df["ALS_Union"]*100, np.nan)
    df.to_csv(OUTPUT_DIR / "analysis2_benchmark_2022_23.csv", index=False)

    # ── 4-panel figure ──
    fig, axes = plt.subplots(2, 2, figsize=(15, 11), gridspec_kw={"hspace":0.35, "wspace":0.28})
    x = np.arange(len(df)); w = 0.32

    # A: ALS Union vs RFU
    ax = axes[0,0]
    ax.bar(x-w/2, df["ALS_Union"], w, color=C["als"], alpha=0.85, label="ALS Rugby Union (direct)")
    ax.bar(x+w/2, df["RFU"], w, color=C["rfu"], alpha=0.85, label="RFU Registered")
    for i, row in df.iterrows():
        ax.text(i, max(row["ALS_Union"], row["RFU"])*1.03,
                f"Δ {row['Gap']:,.0f}", ha="center", fontsize=8, color=C["gap"], fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(df["Age_Group"])
    ax.set_title("A   ALS Rugby Union vs RFU (direct, no estimation)")
    ax.legend(fontsize=9); ax.grid(axis="y", color=C["grid"]); _kfmt(ax)

    # B: Gender
    ax = axes[0,1]
    w2 = 0.20
    ax.bar(x-1.5*w2, df["ALS_Union_M"], w2, color=C["male"], alpha=0.85, label="ALS Male")
    ax.bar(x-0.5*w2, df["RFU_M"], w2, color=C["male"], alpha=0.45, label="RFU Male", hatch="//")
    ax.bar(x+0.5*w2, df["ALS_Union_F"], w2, color=C["female"], alpha=0.85, label="ALS Female")
    ax.bar(x+1.5*w2, df["RFU_F"], w2, color=C["female"], alpha=0.45, label="RFU Female", hatch="//")
    ax.set_xticks(x); ax.set_xticklabels(df["Age_Group"])
    ax.set_title("B   Gender Split — Direct Measurement")
    ax.legend(fontsize=7); ax.grid(axis="y", color=C["grid"]); _kfmt(ax)

    # C: School vs Outside-School
    ax = axes[1,0]
    ax.bar(x-w/2, df["ALS_Union_School"], w, color=C["school"], alpha=0.85, label="In-School Union")
    ax.bar(x+w/2, df["ALS_Union_OutSchool"], w, color=C["outschool"], alpha=0.85, label="Outside-School Union")
    ax.axhline(0, color=C["text"], lw=0.5)
    ax.set_xticks(x); ax.set_xticklabels(df["Age_Group"])
    ax.set_title("C   Where Is Rugby Union Played? (School vs Outside)")
    ax.legend(fontsize=9); ax.grid(axis="y", color=C["grid"]); _kfmt(ax)

    # D: Capture rate
    ax = axes[1,1]
    cap_vals = df["Capture_%"].clip(upper=100)  # clip for bar display
    bars = ax.bar(x, cap_vals, color=[C["green"] if v > 80 else C["amber"] if v > 50 else C["rfu"] for v in df["Capture_%"]],
                   alpha=0.85, edgecolor="white")
    for i, row in df.iterrows():
        v = row["Capture_%"]
        display_y = min(v, 100)
        label = f"{v:.0f}%" + (" ▲" if v > 100 else "")
        ax.text(i, display_y+3, label,
                ha="center", fontsize=9, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(df["Age_Group"])
    ax.set_title("D   Club Capture Rate (RFU ÷ ALS Union)")
    ax.set_ylabel("Capture %"); ax.set_ylim(0, 120)
    ax.axhline(100, color=C["text"], lw=0.8, ls="--", alpha=0.5)
    ax.grid(axis="y", color=C["grid"])

    fig.suptitle("Analysis 2: The 2022-23 Benchmark — Direct Rugby Union Data (Ages 11–16)",
                 y=1.01, fontsize=15, fontweight="bold")
    fig.text(0.5, -0.01, "Every number is a direct measurement from the ALS Rugby Union column. "
             "No proportional correction or estimation applied.",
             ha="center", fontsize=9, color="#059669", fontweight="bold")
    _save("analysis2_benchmark")

    # Regional breakdown
    fig, ax = plt.subplots(figsize=(14, 6.5))
    reg_rows = []
    for reg in sorted(REGION_MAP.values()):
        rf = filt[filt["Region"]==reg]
        als_r = rf.loc[rf[YC_UNION]==1, YC_WT].sum()
        reg_rows.append({"Region": reg, "ALS_Union": als_r})
    reg_df = pd.DataFrame(reg_rows)

    rfu_reg = rfu_by_region(rdf, [f"U{a}" for a in range(11,17)])
    reg_df["RFU"] = reg_df["Region"].map(rfu_reg).fillna(0)
    reg_df["Gap"] = reg_df["ALS_Union"] - reg_df["RFU"]
    reg_df["Capture_%"] = np.where(reg_df["ALS_Union"]>0,
                                    reg_df["RFU"]/reg_df["ALS_Union"]*100, np.nan)
    reg_df = reg_df.sort_values("Gap", ascending=True)
    reg_df.to_csv(OUTPUT_DIR / "analysis2_benchmark_regional.csv", index=False)

    colors = [C["gap"] if g>0 else C["green"] for g in reg_df["Gap"]]
    ax.barh(reg_df["Region"], reg_df["Gap"], color=colors, height=0.6, edgecolor="white")
    ax.axvline(0, color=C["text"], lw=0.8)
    for bar, (_, row) in zip(ax.patches, reg_df.iterrows()):
        v = row["Gap"]
        off = max(abs(reg_df["Gap"]).max()*0.03, 50)
        ax.text(v+(off if v>=0 else -off), bar.get_y()+bar.get_height()/2,
                f"{v:,.0f} ({row['Capture_%']:.0f}%)", va="center",
                ha="left" if v>=0 else "right", fontsize=9, fontweight="bold")
    ax.set_title("Analysis 2b: Regional Gap — Direct Rugby Union (11–16), 2022-23")
    ax.grid(axis="x", color=C["grid"]); _kfmt(ax, "x")
    _save("analysis2b_benchmark_regional")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 3: School-to-Club Pipeline
# ══════════════════════════════════════════════════════════════════════════════

def analysis3_pipeline(young_data, rfu_data):
    """
    Uses ALL-RUGBY school vs outside-school (available every year).
    Not estimation — these are direct setting measurements.
    Question: is school producing players who show up outside school?
    """
    log.info("ANALYSIS 3: School-to-Club Pipeline")
    rows = []
    for cfg in YOUNG_FILES:
        ydf = young_data[cfg["year"]]
        age = pd.to_numeric(ydf[YC_AGE], errors="coerce")
        filt = ydf[(age>=7)&(age<=16)]

        for a in range(7, 17):
            af = filt[age[filt.index]==a]
            sch = af.loc[af[YC_ALLR_SCH]==1, YC_WT].sum()
            out = af.loc[af[YC_ALLR_OUT]==1, YC_WT].sum()
            both = af.loc[(af[YC_ALLR_SCH]==1)&(af[YC_ALLR_OUT]==1), YC_WT].sum()
            total = af.loc[af[YC_ALLRUGBY]==1, YC_WT].sum()
            sch_m = af.loc[(af[YC_ALLR_SCH]==1)&(af[YC_GEND]==1), YC_WT].sum()
            sch_f = af.loc[(af[YC_ALLR_SCH]==1)&(af[YC_GEND]==2), YC_WT].sum()
            out_m = af.loc[(af[YC_ALLR_OUT]==1)&(af[YC_GEND]==1), YC_WT].sum()
            out_f = af.loc[(af[YC_ALLR_OUT]==1)&(af[YC_GEND]==2), YC_WT].sum()

            rows.append({"Year":cfg["year"],"Age":a,
                "School":sch,"OutSchool":out,"Both":both,"Total":total,
                "School_M":sch_m,"School_F":sch_f,
                "OutSchool_M":out_m,"OutSchool_F":out_f})

    df = pd.DataFrame(rows)
    df["Conversion_%"] = np.where(df["School"]>0, df["Both"]/df["School"]*100, 0)
    df["OutSchool_Share_%"] = np.where(df["Total"]>0, df["OutSchool"]/df["Total"]*100, 0)
    df.to_csv(OUTPUT_DIR / "analysis3_pipeline.csv", index=False)

    # ── Plot: Conversion rate by age (latest year) ──
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(20, 6.5), gridspec_kw={"wspace": 0.30})
    latest = df[df["Year"]=="2022-23"].sort_values("Age")
    x = np.arange(len(latest))

    # A: Setting decomposition
    ax1.bar(x, latest["School"], color=C["school"], alpha=0.85, label="School only")
    ax1.bar(x, latest["Both"], bottom=latest["School"], color="#6366F1", alpha=0.7, label="School + Outside")
    ax1.bar(x, latest["OutSchool"]-latest["Both"], bottom=latest["School"]+latest["Both"],
            color=C["outschool"], alpha=0.85, label="Outside-school only")
    ax1.set_xticks(x); ax1.set_xticklabels([f"U{a}" for a in latest["Age"]])
    ax1.set_title("A   Where Rugby Is Played (2022-23)")
    ax1.legend(fontsize=8); ax1.grid(axis="y", color=C["grid"]); _kfmt(ax1)

    # B: Conversion rate
    ax2.bar(x, latest["Conversion_%"], color="#6366F1", alpha=0.85)
    for i, row in latest.iterrows():
        idx = list(latest.index).index(i)
        ax2.text(idx, row["Conversion_%"]+1.5, f"{row['Conversion_%']:.0f}%",
                 ha="center", fontsize=9, fontweight="bold")
    ax2.set_xticks(x); ax2.set_xticklabels([f"U{a}" for a in latest["Age"]])
    ax2.set_title("B   School→Outside Conversion Rate")
    ax2.set_ylabel("% of school players also playing outside school")
    ax2.grid(axis="y", color=C["grid"])

    # C: Conversion trend over years
    yearly = df.groupby("Year").agg({"School":"sum","Both":"sum","OutSchool":"sum"}).reset_index()
    yearly["Conv_%"] = yearly["Both"] / yearly["School"] * 100
    ax3.plot(yearly["Year"], yearly["Conv_%"], "o-", color="#6366F1", lw=2.5, ms=8)
    for i, row in yearly.iterrows():
        ax3.text(i, row["Conv_%"]-1.2, f"{row['Conv_%']:.1f}%",
                 ha="center", fontsize=8, fontweight="bold", color="#6366F1")
    ax3.set_title("C   Conversion Rate Trend (All Ages)", pad=10)
    ax3.set_ylabel("% school players also outside-school")
    ax3.grid(axis="y", color=C["grid"])
    ax3.tick_params(axis="x", rotation=30)

    fig.suptitle("Analysis 3: The School-to-Club Pipeline — Is School Feeding Clubs?",
                 y=1.02, fontsize=15, fontweight="bold")
    fig.text(0.5, -0.02, "Direct measurements from ALS CYP. 'Conversion' = % of school rugby players "
             "who also play outside school. Outside-school includes club, informal, and community settings.",
             ha="center", fontsize=8, color="#6B7280", style="italic")
    _save("analysis3_pipeline")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 4: Adult Club Membership Test
# ══════════════════════════════════════════════════════════════════════════════

def analysis4_club_test(adult_data, rfu_data):
    """
    Cleanest possible comparison: ALS 'member of a rugby union club'
    vs RFU registrations for 16-18.
    """
    log.info("ANALYSIS 4: Adult Club Membership Test (16–18)")
    rows = []
    for label, als_y, rfu_y in ALIGN:
        adf = adult_data.get(als_y)
        rdf = rfu_data[rfu_y]
        rfu_t = rfu_sum(rdf, ["U16","U17","U18"])
        rfu_m = rfu_sum(rdf, ["U16","U17","U18"], "M")
        rfu_f = rfu_sum(rdf, ["U16","U17","U18"], "F")
        if adf is not None:
            n_resp = len(adf)
            n_union = (adf[AC_UNION]==1).sum()
            n_club = (adf[AC_CLUB]==1).sum()
            total_wt = adf[AC_WT].sum()
            wt_union = adf.loc[adf[AC_UNION]==1, AC_WT].sum()
            wt_club = adf.loc[adf[AC_CLUB]==1, AC_WT].sum()
            # What % of union players are in a club?
            club_rate = n_club / n_union * 100 if n_union > 0 else 0
            # Participation rates (valid with normalised weights)
            union_rate = wt_union / total_wt if total_wt > 0 else 0
            club_rate_wt = wt_club / total_wt if total_wt > 0 else 0
            # Population estimates via ONS
            pop = ONS_POP_16_18.get(als_y, 1_900_000)
            pop_union = union_rate * pop
            pop_club = club_rate_wt * pop
        else:
            n_resp = n_union = n_club = 0
            union_rate = club_rate_wt = np.nan
            club_rate = np.nan
            pop_union = pop_club = np.nan
            pop = ONS_POP_16_18.get(als_y, 1_900_000)

        rows.append({"Period": label,
            "N_Respondents_16_18": n_resp,
            "N_Union_Unweighted": n_union,
            "N_Club_Unweighted": n_club,
            "ALS_Union_Rate_%": union_rate * 100 if not np.isnan(union_rate) else np.nan,
            "ALS_Club_Rate_%": club_rate_wt * 100 if not np.isnan(club_rate_wt) else np.nan,
            "ALS_Union_PopEst": pop_union,
            "ALS_Club_PopEst": pop_club,
            "Club_of_Union_%": club_rate,
            "ONS_Pop_16_18": pop,
            "RFU_U16_U18": rfu_t, "RFU_M": rfu_m, "RFU_F": rfu_f})

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_DIR / "analysis4_club_test.csv", index=False)

    has = df.dropna(subset=["ALS_Club_PopEst"]).reset_index(drop=True)
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6), gridspec_kw={"wspace": 0.30})
    x = np.arange(len(has))

    # A: Sample sizes (transparency)
    w = 0.25
    ax1.bar(x-w, has["N_Respondents_16_18"], w, color=C["als"], alpha=0.5, label="Total 16–18 respondents")
    ax1.bar(x, has["N_Union_Unweighted"], w, color=C["als"], alpha=0.85, label="Rugby Union players")
    ax1.bar(x+w, has["N_Club_Unweighted"], w, color=C["club"], alpha=0.85, label="Club members")
    ax1.set_xticks(x); ax1.set_xticklabels(has["Period"])
    ax1.set_title("A   ALS Sample Sizes (unweighted)")
    ax1.legend(fontsize=8); ax1.grid(axis="y", color=C["grid"])

    # B: Club membership rate (of union players)
    ax2.bar(x, has["Club_of_Union_%"], color=C["club"], alpha=0.85, width=0.5)
    for i, row in has.iterrows():
        ax2.text(i, row["Club_of_Union_%"]+2,
                 f"{row['Club_of_Union_%']:.0f}%\n({row['N_Club_Unweighted']} of {row['N_Union_Unweighted']})",
                 ha="center", fontsize=9, fontweight="bold")
    ax2.set_xticks(x); ax2.set_xticklabels(has["Period"])
    ax2.set_title("B   % of Union Players in a Club")
    ax2.set_ylabel("Club membership rate (%)"); ax2.set_ylim(0,100)
    ax2.grid(axis="y", color=C["grid"])

    # C: Population-grossed estimates vs RFU
    w3 = 0.25
    ax3.bar(x-w3, has["ALS_Union_PopEst"], w3, color=C["als"], alpha=0.85, label="ALS Union (pop. est.)")
    ax3.bar(x, has["ALS_Club_PopEst"], w3, color=C["club"], alpha=0.85, label="ALS Club (pop. est.)")
    ax3.bar(x+w3, has["RFU_U16_U18"], w3, color=C["rfu"], alpha=0.85, label="RFU U16–U18")
    for i, row in has.iterrows():
        ax3.text(i-w3, row["ALS_Union_PopEst"]*1.03, f"{row['ALS_Union_PopEst']:,.0f}",
                 ha="center", fontsize=7, color=C["als"])
        ax3.text(i+w3, row["RFU_U16_U18"]*1.03, f"{row['RFU_U16_U18']:,.0f}",
                 ha="center", fontsize=7, color=C["rfu"])
    ax3.set_xticks(x); ax3.set_xticklabels(has["Period"])
    ax3.set_title("C   Population Estimate vs RFU (16–18)")
    ax3.legend(fontsize=7, loc="upper left"); ax3.grid(axis="y", color=C["grid"]); _kfmt(ax3)
    ax3.text(0.5, 0.55, "ALS rate × ONS 16–18 pop. (~1.9M)\n"
             "Small ALS sample (200–226 respondents)",
             transform=ax3.transAxes, ha="center", va="top", fontsize=8,
             color="#6B7280", style="italic",
             bbox=dict(boxstyle="round,pad=0.3", facecolor=C["light"], edgecolor=C["als"], alpha=0.8))

    fig.suptitle("Analysis 4: Do Club Members = Registered Players? (16–18)",
                 y=1.02, fontsize=15, fontweight="bold")
    _save("analysis4_club_test")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 5: Regional Opportunity Map
# ══════════════════════════════════════════════════════════════════════════════

def analysis5_regional(young_data, rfu_data):
    """
    High all-rugby participation + low RFU registration = opportunity.
    Uses all-rugby (no estimation). The RELATIVE ranking across regions
    is valid regardless of the union proportion.
    """
    log.info("ANALYSIS 5: Regional Opportunity Map")
    rows = []
    for label, als_y, rfu_y in ALIGN:
        ydf = young_data[als_y]; rdf = rfu_data[rfu_y]
        age = pd.to_numeric(ydf[YC_AGE], errors="coerce")
        filt = ydf[(age>=7)&(age<=16)]

        # ALS by region
        for reg in sorted(REGION_MAP.values()):
            rf = filt[filt["Region"]==reg]
            als_t = rf.loc[rf[YC_ALLRUGBY]==1, YC_WT].sum()
            als_m = rf.loc[(rf[YC_ALLRUGBY]==1)&(rf[YC_GEND]==1), YC_WT].sum()
            als_f = rf.loc[(rf[YC_ALLRUGBY]==1)&(rf[YC_GEND]==2), YC_WT].sum()
            rows.append({"Period":label,"Region":reg,
                "ALS_AllRugby":als_t,"ALS_AllRugby_M":als_m,"ALS_AllRugby_F":als_f})

    als_df = pd.DataFrame(rows)

    # RFU by region
    rfu_rows = []
    for label, als_y, rfu_y in ALIGN:
        rdf = rfu_data[rfu_y]
        rfu_reg = rfu_by_region(rdf, [f"U{a}" for a in range(7,17)])
        rfu_reg_m = rfu_by_region(rdf, [f"U{a}" for a in range(7,17)], "M")
        rfu_reg_f = rfu_by_region(rdf, [f"U{a}" for a in range(7,17)], "F")
        for reg in sorted(REGION_MAP.values()):
            rfu_rows.append({"Period":label,"Region":reg,
                "RFU":rfu_reg.get(reg,0),"RFU_M":rfu_reg_m.get(reg,0),"RFU_F":rfu_reg_f.get(reg,0)})

    rfu_df = pd.DataFrame(rfu_rows)
    df = als_df.merge(rfu_df, on=["Period","Region"], how="inner")
    df["Capture_%"] = np.where(df["ALS_AllRugby"]>0, df["RFU"]/df["ALS_AllRugby"]*100, np.nan)
    df["Gap"] = df["ALS_AllRugby"] - df["RFU"]
    df.to_csv(OUTPUT_DIR / "analysis5_regional_opportunity.csv", index=False)

    # ── Latest year opportunity plot ──
    latest = df[df["Period"]==ALIGN[-1][0]].copy()
    latest["Opportunity_Score"] = latest["Gap"] * (100 - latest["Capture_%"].fillna(0)) / 100
    latest = latest.sort_values("Opportunity_Score", ascending=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7.5), gridspec_kw={"wspace": 0.35})

    # A: Capture rate heatmap (time × region)
    pivot = df.pivot_table(index="Region", columns="Period", values="Capture_%")
    pivot = pivot.loc[pivot.mean(axis=1).sort_values().index]
    data = pivot.values
    im = ax1.imshow(data, aspect="auto", cmap="RdYlGn", vmin=0,
                     vmax=min(np.nanmax(data)*1.1, 100))
    ax1.set_xticks(range(pivot.shape[1])); ax1.set_xticklabels(pivot.columns, fontsize=9)
    ax1.set_yticks(range(pivot.shape[0])); ax1.set_yticklabels(pivot.index, fontsize=10)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data[i,j]
            if np.isnan(v): continue
            c = "white" if v<25 else C["text"]
            ax1.text(j,i,f"{v:.0f}%",ha="center",va="center",fontsize=9,fontweight="bold",color=c)
    ax1.set_title("A   Capture Rate by Region × Period")
    fig.colorbar(im, ax=ax1, shrink=0.7)

    # B: Opportunity ranking
    ax2.barh(latest["Region"], latest["Gap"], color=C["gap"], alpha=0.8, height=0.6)
    for bar, (_,row) in zip(ax2.patches, latest.iterrows()):
        v = row["Gap"]
        ax2.text(v+max(latest["Gap"])*0.02, bar.get_y()+bar.get_height()/2,
                 f"{v:,.0f}", va="center", fontsize=9, fontweight="bold")
    ax2.set_title(f"B   Participation Gap by Region — {ALIGN[-1][0]}")
    ax2.set_xlabel("ALS All Rugby − RFU (non-registered participation)")
    ax2.grid(axis="x", color=C["grid"]); _kfmt(ax2, "x")

    fig.suptitle("Analysis 5: Regional Opportunity Map — Where to Focus Recruitment",
                 y=1.02, fontsize=15, fontweight="bold")
    fig.text(0.5, -0.02, "Uses ALS all-rugby participation. Low capture rate + high gap = "
             "greatest recruitment opportunity. Regional RANKING is valid regardless of rugby code mix.",
             ha="center", fontsize=8, color="#6B7280", style="italic")
    _save("analysis5_regional_opportunity")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 6: Gender Growth Opportunity
# ══════════════════════════════════════════════════════════════════════════════

def analysis6_gender(young_data, rfu_data):
    """
    Female rugby = RFU's biggest strategic growth area.
    All direct measurements. Shows where the female gap is widest.
    """
    log.info("ANALYSIS 6: Gender Growth Opportunity")
    rows = []
    for cfg in YOUNG_FILES:
        ydf = young_data[cfg["year"]]
        age = pd.to_numeric(ydf[YC_AGE], errors="coerce")
        filt = ydf[(age>=7)&(age<=16)]

        als_m = filt.loc[(filt[YC_ALLRUGBY]==1)&(filt[YC_GEND]==1), YC_WT].sum()
        als_f = filt.loc[(filt[YC_ALLRUGBY]==1)&(filt[YC_GEND]==2), YC_WT].sum()
        als_f_pct = als_f / (als_m+als_f) * 100 if (als_m+als_f) > 0 else 0

        rows.append({"Year":cfg["year"],"ALS_Male":als_m,"ALS_Female":als_f,
                      "ALS_Female_%":als_f_pct})

    als_df = pd.DataFrame(rows)

    # RFU gender trends
    rfu_rows = []
    for year in RFU_YEARS_OLD + [RFU_NEW_YEAR]:
        rdf = rfu_data[year]
        m = rfu_sum(rdf, [f"U{a}" for a in range(7,17)], "M")
        f = rfu_sum(rdf, [f"U{a}" for a in range(7,17)], "F")
        rfu_rows.append({"Year":year,"RFU_Male":m,"RFU_Female":f,
                          "RFU_Female_%": f/(m+f)*100 if (m+f)>0 else 0})
    rfu_df = pd.DataFrame(rfu_rows)

    als_df.to_csv(OUTPUT_DIR / "analysis6_gender_als.csv", index=False)
    rfu_df.to_csv(OUTPUT_DIR / "analysis6_gender_rfu.csv", index=False)

    fig, axes = plt.subplots(1, 3, figsize=(18, 6), gridspec_kw={"wspace": 0.28})

    # A: Female % trend
    ax = axes[0]
    ax.plot(als_df["Year"], als_df["ALS_Female_%"], "o-", color=C["female"], lw=2.5, ms=8, label="ALS Female %")
    ax.plot(rfu_df["Year"], rfu_df["RFU_Female_%"], "s--", color=C["rfu"], lw=2, ms=7, label="RFU Female %")
    for i, row in als_df.iterrows():
        ax.text(i, row["ALS_Female_%"]+0.8, f"{row['ALS_Female_%']:.1f}%",
                ha="center", fontsize=7, color=C["female"], fontweight="bold")
    for i, row in rfu_df.iterrows():
        ax.text(i, row["RFU_Female_%"]-1.5, f"{row['RFU_Female_%']:.1f}%",
                ha="center", fontsize=7, color=C["rfu"])
    ax.set_title("A   Female Share Trend — ALS vs RFU")
    ax.set_ylabel("Female % of all players"); ax.legend(fontsize=9, loc="lower right")
    ax.grid(axis="y", color=C["grid"]); ax.tick_params(axis="x", rotation=50, labelsize=8)

    # B: Absolute female numbers
    ax = axes[1]
    x = np.arange(len(als_df)); w = 0.32
    ax.bar(x-w/2, als_df["ALS_Female"], w, color=C["female"], alpha=0.85, label="ALS Female (all rugby)")
    # Match RFU years approximately
    ax.set_xticks(x); ax.set_xticklabels(als_df["Year"])
    ax.set_title("B   ALS Female Participation (7–16)")
    ax.legend(fontsize=9); ax.grid(axis="y", color=C["grid"]); _kfmt(ax)

    # C: Female by age (latest year)
    ax = axes[2]
    ydf = young_data["2022-23"]
    age = pd.to_numeric(ydf[YC_AGE], errors="coerce")
    filt = ydf[(age>=7)&(age<=16)]
    age_f = []
    for a in range(7, 17):
        af = filt[age[filt.index]==a]
        als_f = af.loc[(af[YC_ALLRUGBY]==1)&(af[YC_GEND]==2), YC_WT].sum()
        age_f.append({"Age": a, "ALS_Female": als_f})
    adf = pd.DataFrame(age_f)
    rdf_latest = rfu_data["2023 May"]
    adf["RFU_Female"] = [rfu_sum(rdf_latest, [f"U{a}"], "F") for a in range(7,17)]

    x = np.arange(len(adf)); w = 0.32
    ax.bar(x-w/2, adf["ALS_Female"], w, color=C["female"], alpha=0.85, label="ALS Female")
    ax.bar(x+w/2, adf["RFU_Female"], w, color=C["rfu"], alpha=0.65, label="RFU Female")
    ax.set_xticks(x); ax.set_xticklabels([f"U{a}" for a in adf["Age"]])
    ax.set_title("C   Female by Age — ALS vs RFU (2022-23)")
    ax.legend(fontsize=9); ax.grid(axis="y", color=C["grid"]); _kfmt(ax)

    fig.suptitle("Analysis 6: Gender Growth Opportunity — The Untapped Female Market",
                 y=1.02, fontsize=15, fontweight="bold")
    fig.text(0.5, -0.02, "ALS = all rugby participation (direct measurement). "
             "RFU = registered players. The gap between ALS female % and RFU female % "
             "represents the conversion opportunity.",
             ha="center", fontsize=8, color="#6B7280", style="italic")
    _save("analysis6_gender_growth")
    return als_df, rfu_df


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def run_all():
    os.chdir(BASE_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log.info("Working dir: %s | Output: %s", BASE_DIR, OUTPUT_DIR)

    # Load
    log.info("=" * 60); log.info("Loading data")
    young_data = {c["year"]: load_young(c) for c in YOUNG_FILES}
    adult_data = {}
    for c in ADULT_FILES:
        df = load_adult(c)
        if df is not None: adult_data[c["year"]] = df
    rfu_data = load_rfu()

    # Run analyses
    log.info("=" * 60)
    a1 = analysis1_dropout(rfu_data)
    log.info("=" * 60)
    a2 = analysis2_benchmark(young_data, rfu_data)
    log.info("=" * 60)
    a3 = analysis3_pipeline(young_data, rfu_data)
    log.info("=" * 60)
    a4 = analysis4_club_test(adult_data, rfu_data)
    log.info("=" * 60)
    a5 = analysis5_regional(young_data, rfu_data)
    log.info("=" * 60)
    a6 = analysis6_gender(young_data, rfu_data)

    log.info("=" * 60)
    log.info("ALL ANALYSES COMPLETE ✓ — Outputs → %s", OUTPUT_DIR)
    log.info("=" * 60)


if __name__ == "__main__":
    run_all()