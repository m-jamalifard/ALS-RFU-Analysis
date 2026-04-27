#!/usr/bin/env python3
"""
Cross-Sport ALS Analysis — Football, Cricket, and Rugby
=========================================================
Replicates the rugby participation analysis for football and cricket:
  (a) Overall participation trend (ages 7–16, 2017-18 to 2022-23)
  (b) Gender breakdown (male/female share)
  (c) School vs outside-school setting

This mirrors Analyses 1/3/4 from the rugby impact report.

Usage:
  cd /home/reza/ALS_RFU_Analysis
  python als_cross_sport.py

Output:
  output_cross_sport/
    ├── step0_variable_discovery.csv
    ├── sport_participation_trend.csv
    ├── sport_gender_trend.csv
    ├── sport_school_pipeline.csv
    ├── fig_cross_sport_trend.png
    ├── fig_cross_sport_gender.png
    ├── fig_cross_sport_school.png
    └── fig_cross_sport_summary.png
"""

import os
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import pyreadstat
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import warnings
warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────

BASE_DIR   = Path("/home/reza/ALS_RFU_Analysis")
OUTPUT_DIR = BASE_DIR / "output_cross_sport"

LOG_FMT = "%(asctime)s | %(levelname)-8s | %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FMT)
log = logging.getLogger(__name__)

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"],
    "font.size": 11, "axes.titlesize": 13, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "savefig.facecolor": "white",
    "figure.dpi": 150, "savefig.dpi": 150,
})

# ── ALS CYP file config ──
COL_AGE    = "age_11"
COL_GENDER = "gend3"
COL_WEIGHT = "wt_gross"

YOUNG_FILES = [
    {"file": "ALS_Young_2017-18.sav",  "year": "2017-18"},
    {"file": "ALS_Young_2018-19.sav",  "year": "2018-19"},
    {"file": "ALS_Young_2019-20.sav",  "year": "2019-20"},
    {"file": "ALS_Young_2020-21.sav",  "year": "2020-21"},
    {"file": "ALS_Young_2021-22.sav",  "year": "2021-22"},
    {"file": "ALS_Young_2022-23.sav",  "year": "2022-23"},
]

# ── Sport variable patterns ──
# The ALS uses a naming convention:
#   onceawk_modplus_everywhere_GR_{SPORT}_{CODE}  = participated anywhere
#   onceawk_modplus_inschool_GR_{SPORT}_{CODE}    = in school
#   onceawk_modplus_outschool_GR_{SPORT}_{CODE}   = outside school
#
# Rugby:    GR_RUGBY_CC018 (all rugby)
# Football: GR_FOOTBALL_CC0XX — we discover the exact code below
# Cricket:  GR_CRICKET_CC0XX — we discover the exact code below
#
# "Any Football" in the ALS is the equivalent of "Any Rugby" — includes
# all football codes (association football / soccer in any setting).

SPORT_SEARCH_PATTERNS = {
    "rugby":    r"onceawk_modplus_everywhere_GR_RUGBY",
    "football": r"onceawk_modplus_everywhere_GR_FOOTBALL",
    "cricket":  r"onceawk_modplus_everywhere_GR_CRICKET",
}

# ── Colours ──
SPORT_COLOURS = {
    "rugby":    "#DC2626",  # red
    "football": "#2563EB",  # blue
    "cricket":  "#059669",  # green
}
GR = "#E5E7EB"
M_COL, F_COL = "#0369A1", "#BE185D"


# ══════════════════════════════════════════════════════════════
# Step 0: Variable Discovery
# ══════════════════════════════════════════════════════════════

def discover_sport_variables() -> Dict[str, Dict[str, str]]:
    """
    Scan the 2022-23 ALS CYP file (latest, most columns) to find
    the exact variable names for football, cricket, and rugby.
    Returns a dict keyed by sport with keys: everywhere, inschool, outschool.
    """
    log.info("Step 0: Discovering sport variables from 2022-23 file")
    path = BASE_DIR / "ALS_Young_2022-23.sav"
    _, meta = pyreadstat.read_sav(str(path), metadataonly=True)
    all_cols = list(meta.column_names)

    discovered = {}
    for sport, pattern in SPORT_SEARCH_PATTERNS.items():
        matches = [c for c in all_cols if re.search(pattern, c, re.IGNORECASE)]
        if not matches:
            log.warning("  %s: NO variables found matching '%s'", sport, pattern)
            continue

        log.info("  %s: found %d 'everywhere' variables: %s", sport, len(matches), matches)

        # Take the first match (there should typically be one per sport)
        everywhere_col = matches[0]

        # Derive inschool and outschool from the everywhere column
        inschool_col  = everywhere_col.replace("_everywhere_", "_inschool_")
        outschool_col = everywhere_col.replace("_everywhere_", "_outschool_")

        # Verify they exist
        inschool_ok  = inschool_col in all_cols
        outschool_ok = outschool_col in all_cols

        log.info("    everywhere: %s", everywhere_col)
        log.info("    inschool:   %s [%s]", inschool_col, "✓" if inschool_ok else "✗ NOT FOUND")
        log.info("    outschool:  %s [%s]", outschool_col, "✓" if outschool_ok else "✗ NOT FOUND")

        discovered[sport] = {
            "everywhere": everywhere_col,
            "inschool":   inschool_col if inschool_ok else None,
            "outschool":  outschool_col if outschool_ok else None,
        }

    # Also check older files (football/cricket variable names may differ)
    log.info("\n  Checking variable availability across all years...")
    availability = []
    for cfg in YOUNG_FILES:
        path = BASE_DIR / cfg["file"]
        _, meta = pyreadstat.read_sav(str(path), metadataonly=True)
        cols = set(meta.column_names)
        row = {"Year": cfg["year"]}
        for sport, vcols in discovered.items():
            for vtype, vname in vcols.items():
                if vname:
                    row[f"{sport}_{vtype}"] = vname in cols
        availability.append(row)

    avail_df = pd.DataFrame(availability)
    log.info("\n  Variable availability by year:")
    log.info("\n%s", avail_df.to_string(index=False))

    avail_df.to_csv(OUTPUT_DIR / "step0_variable_discovery.csv", index=False)
    return discovered


# ══════════════════════════════════════════════════════════════
# Step 1: Participation Trend (all ages 7-16, by sport)
# ══════════════════════════════════════════════════════════════

def analyse_participation_trend(sport_vars: Dict) -> pd.DataFrame:
    log.info("Step 1: Participation trend by sport")
    rows = []
    for cfg in YOUNG_FILES:
        path = BASE_DIR / cfg["file"]
        year = cfg["year"]

        # Load all needed columns
        load_cols = [COL_AGE, COL_GENDER, COL_WEIGHT]
        _, meta = pyreadstat.read_sav(str(path), metadataonly=True)
        all_cols = set(meta.column_names)

        for sport, vcols in sport_vars.items():
            ev = vcols["everywhere"]
            if ev in all_cols:
                load_cols.append(ev)

        df, _ = pyreadstat.read_sav(str(path), usecols=list(set(load_cols)))
        age = pd.to_numeric(df[COL_AGE], errors="coerce")
        filt = df[(age >= 7) & (age <= 16)]

        for sport, vcols in sport_vars.items():
            ev = vcols["everywhere"]
            if ev not in filt.columns:
                log.warning("  %s %s: column %s not found, skipping", year, sport, ev)
                rows.append({"Year": year, "Sport": sport,
                             "Total": np.nan, "Male": np.nan, "Female": np.nan, "Female_%": np.nan})
                continue

            players = filt[filt[ev] == 1]
            total = players[COL_WEIGHT].sum()
            male  = players.loc[players[COL_GENDER] == 1, COL_WEIGHT].sum()
            female = players.loc[players[COL_GENDER] == 2, COL_WEIGHT].sum()
            fem_pct = female / total * 100 if total > 0 else 0

            rows.append({"Year": year, "Sport": sport,
                         "Total": total, "Male": male, "Female": female, "Female_%": fem_pct})

            log.info("  %s %s: Total=%,.0f  M=%,.0f  F=%,.0f  F%%=%.1f%%",
                     year, sport, total, male, female, fem_pct)

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_DIR / "sport_participation_trend.csv", index=False)
    return df


# ══════════════════════════════════════════════════════════════
# Step 2: School vs Outside-School (by sport)
# ══════════════════════════════════════════════════════════════

def analyse_school_pipeline(sport_vars: Dict) -> pd.DataFrame:
    log.info("Step 2: School vs outside-school by sport")
    rows = []
    for cfg in YOUNG_FILES:
        path = BASE_DIR / cfg["file"]
        year = cfg["year"]

        _, meta = pyreadstat.read_sav(str(path), metadataonly=True)
        all_cols = set(meta.column_names)

        load_cols = [COL_AGE, COL_GENDER, COL_WEIGHT]
        for sport, vcols in sport_vars.items():
            for vtype in ["everywhere", "inschool", "outschool"]:
                v = vcols.get(vtype)
                if v and v in all_cols:
                    load_cols.append(v)

        df, _ = pyreadstat.read_sav(str(path), usecols=list(set(load_cols)))
        age = pd.to_numeric(df[COL_AGE], errors="coerce")
        filt = df[(age >= 7) & (age <= 16)]

        for sport, vcols in sport_vars.items():
            ev = vcols["everywhere"]
            ins = vcols.get("inschool")
            outs = vcols.get("outschool")

            if ev not in filt.columns:
                rows.append({"Year": year, "Sport": sport,
                             "School": np.nan, "OutSchool": np.nan, "Both": np.nan,
                             "School_Only": np.nan, "Pct_School_Only": np.nan})
                continue

            school_wt = filt.loc[filt[ins] == 1, COL_WEIGHT].sum() if ins and ins in filt.columns else np.nan
            out_wt    = filt.loc[filt[outs] == 1, COL_WEIGHT].sum() if outs and outs in filt.columns else np.nan

            # "Both" = plays in school AND outside school
            if ins and outs and ins in filt.columns and outs in filt.columns:
                both_mask = (filt[ins] == 1) & (filt[outs] == 1)
                both_wt = filt.loc[both_mask, COL_WEIGHT].sum()
            else:
                both_wt = np.nan

            school_only = school_wt - both_wt if not (np.isnan(school_wt) or np.isnan(both_wt)) else np.nan
            pct_school_only = school_only / school_wt * 100 if school_wt > 0 and not np.isnan(school_only) else np.nan

            rows.append({"Year": year, "Sport": sport,
                         "School": school_wt, "OutSchool": out_wt, "Both": both_wt,
                         "School_Only": school_only, "Pct_School_Only": pct_school_only})

            log.info("  %s %s: School=%,.0f  Out=%,.0f  Both=%,.0f  SchoolOnly=%,.0f (%.1f%%)",
                     year, sport,
                     school_wt if not np.isnan(school_wt) else 0,
                     out_wt if not np.isnan(out_wt) else 0,
                     both_wt if not np.isnan(both_wt) else 0,
                     school_only if not np.isnan(school_only) else 0,
                     pct_school_only if not np.isnan(pct_school_only) else 0)

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_DIR / "sport_school_pipeline.csv", index=False)
    return df


# ══════════════════════════════════════════════════════════════
# Visualisations
# ══════════════════════════════════════════════════════════════

def _save(name):
    p = OUTPUT_DIR / f"{name}.png"
    plt.savefig(p, dpi=150, bbox_inches="tight"); plt.close()
    log.info("Saved: %s", p.name)

def _kfmt(ax):
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))


def plot_participation_trend(trend_df: pd.DataFrame):
    """Fig 1: Overall participation trend by sport (ages 7-16)."""
    log.info("Plotting: participation trend")

    sports = [s for s in ["football", "rugby", "cricket"] if s in trend_df["Sport"].unique()]
    years = sorted(trend_df["Year"].unique())

    fig, ax = plt.subplots(figsize=(11, 6))
    for sport in sports:
        sdf = trend_df[trend_df["Sport"] == sport].sort_values("Year")
        sdf = sdf[sdf["Year"].isin(years)]
        ax.plot(sdf["Year"], sdf["Total"], "o-", color=SPORT_COLOURS[sport],
                lw=2.5, ms=8, label=f"{sport.title()}", alpha=0.85)
        for _, r in sdf.iterrows():
            if not np.isnan(r["Total"]):
                ax.text(r["Year"], r["Total"] * 1.03, f"{r['Total']:,.0f}",
                        ha="center", fontsize=7, color=SPORT_COLOURS[sport], fontweight="bold")

    ax.set_ylabel("ALS Weighted Participants (7–16)")
    ax.set_title("ALS CYP Participation Trend: Football, Rugby, Cricket (Ages 7–16)")
    ax.legend(fontsize=10); ax.grid(axis="y", color=GR); _kfmt(ax)
    ax.tick_params(axis="x", rotation=20)
    fig.subplots_adjust(bottom=0.15)
    fig.text(0.5, 0.01, "All-sport variables (any football / any rugby / any cricket). ALS CYP survey, ages 7–16.",
             ha="center", fontsize=8, color="#6B7280", style="italic")
    _save("fig_cross_sport_trend")


def plot_gender_comparison(trend_df: pd.DataFrame):
    """Fig 2: Female share by sport over time."""
    log.info("Plotting: gender comparison")

    sports = [s for s in ["football", "rugby", "cricket"] if s in trend_df["Sport"].unique()]
    years = sorted(trend_df["Year"].unique())

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw={"wspace": 0.30})

    # Panel A: Female % trend
    for sport in sports:
        sdf = trend_df[trend_df["Sport"] == sport].sort_values("Year")
        ax1.plot(sdf["Year"], sdf["Female_%"], "o-", color=SPORT_COLOURS[sport],
                 lw=2.5, ms=8, label=sport.title(), alpha=0.85)
        for _, r in sdf.iterrows():
            if not np.isnan(r["Female_%"]):
                ax1.text(r["Year"], r["Female_%"] + 1, f"{r['Female_%']:.0f}%",
                         ha="center", fontsize=7.5, color=SPORT_COLOURS[sport], fontweight="bold")

    ax1.set_ylabel("Female Share (%)")
    ax1.set_title("A   Female Share of Participation by Sport")
    ax1.legend(fontsize=9); ax1.grid(axis="y", color=GR)
    ax1.tick_params(axis="x", rotation=20)
    ax1.set_ylim(0, max(trend_df["Female_%"].dropna()) * 1.3)

    # Panel B: Latest year — male vs female bars
    latest_year = years[-1]
    latest = trend_df[trend_df["Year"] == latest_year].copy()
    latest = latest[latest["Sport"].isin(sports)]
    x = np.arange(len(latest)); w = 0.5
    ax2.bar(x, latest["Male"].values, w, color=M_COL, alpha=0.75, label="Male")
    ax2.bar(x, latest["Female"].values, w, bottom=latest["Male"].values,
            color=F_COL, alpha=0.75, label="Female")
    for i, (_, r) in enumerate(latest.iterrows()):
        if not np.isnan(r["Total"]):
            ax2.text(i, r["Total"] * 1.03, f"F:{r['Female_%']:.0f}%",
                     ha="center", fontsize=9, color=F_COL, fontweight="bold")
    ax2.set_xticks(x); ax2.set_xticklabels([s.title() for s in latest["Sport"]])
    ax2.set_title(f"B   Gender Breakdown ({latest_year})")
    ax2.set_ylabel("Players"); ax2.legend(fontsize=9)
    ax2.grid(axis="y", color=GR); _kfmt(ax2)
    ax2.set_ylim(0, latest["Total"].max() * 1.2)

    fig.subplots_adjust(bottom=0.15)
    _save("fig_cross_sport_gender")


def plot_school_pipeline(school_df: pd.DataFrame):
    """Fig 3: School-only % by sport over time."""
    log.info("Plotting: school pipeline")

    sports = [s for s in ["football", "rugby", "cricket"] if s in school_df["Sport"].unique()]
    years = sorted(school_df["Year"].unique())

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw={"wspace": 0.30})

    # Panel A: % school-only trend
    for sport in sports:
        sdf = school_df[school_df["Sport"] == sport].sort_values("Year")
        valid = sdf.dropna(subset=["Pct_School_Only"])
        ax1.plot(valid["Year"], valid["Pct_School_Only"], "o-", color=SPORT_COLOURS[sport],
                 lw=2.5, ms=8, label=sport.title(), alpha=0.85)
        for _, r in valid.iterrows():
            ax1.text(r["Year"], r["Pct_School_Only"] + 0.8, f"{r['Pct_School_Only']:.0f}%",
                     ha="center", fontsize=7.5, color=SPORT_COLOURS[sport], fontweight="bold")

    ax1.set_ylabel("% Playing at School ONLY")
    ax1.set_title("A   School-Only Participation by Sport")
    ax1.legend(fontsize=9); ax1.grid(axis="y", color=GR)
    ax1.tick_params(axis="x", rotation=20)

    # Panel B: Latest year — school vs outside bars
    latest_year = years[-1]
    latest = school_df[school_df["Year"] == latest_year].copy()
    latest = latest[latest["Sport"].isin(sports)].dropna(subset=["School"])
    x = np.arange(len(latest)); w = 0.35
    ax2.bar(x - w/2, latest["Both"].values, w, color="#059669", alpha=0.85, label="School + Outside")
    ax2.bar(x + w/2, latest["School_Only"].values, w, color="#D97706", alpha=0.85, label="School Only")
    for i, (_, r) in enumerate(latest.iterrows()):
        ax2.text(i - w/2, r["Both"] * 1.03, f"{r['Both']:,.0f}", ha="center", fontsize=7,
                 color="#059669", fontweight="bold")
        ax2.text(i + w/2, r["School_Only"] * 1.03, f"{r['School_Only']:,.0f}", ha="center", fontsize=7,
                 color="#D97706", fontweight="bold")
    ax2.set_xticks(x); ax2.set_xticklabels([s.title() for s in latest["Sport"]])
    ax2.set_title(f"B   School Transition ({latest_year})")
    ax2.set_ylabel("Players"); ax2.legend(fontsize=9)
    ax2.grid(axis="y", color=GR); _kfmt(ax2)
    ax2.set_ylim(0, max(latest["Both"].max(), latest["School_Only"].max()) * 1.25)

    fig.subplots_adjust(bottom=0.15)
    fig.text(0.5, 0.01, "All-sport variables (ages 7–16). 'Outside school' includes club, community, and informal.",
             ha="center", fontsize=8, color="#6B7280", style="italic")
    _save("fig_cross_sport_school")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def run_all():
    os.chdir(BASE_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log.info("Working directory: %s", BASE_DIR)
    log.info("Output: %s", OUTPUT_DIR)

    # Step 0: Discover variables
    log.info("=" * 60)
    sport_vars = discover_sport_variables()
    log.info("=" * 60)

    if not sport_vars:
        log.error("No sport variables found! Check ALS file location and column names.")
        return

    log.info("Discovered sports: %s", list(sport_vars.keys()))

    # If football or cricket not found, try broader search
    for sport in ["football", "cricket"]:
        if sport not in sport_vars:
            log.warning("'%s' not found with standard pattern. Trying broader search...", sport)
            path = BASE_DIR / "ALS_Young_2022-23.sav"
            _, meta = pyreadstat.read_sav(str(path), metadataonly=True)
            candidates = [c for c in meta.column_names
                         if sport.upper() in c.upper() and "onceawk" in c.lower() and "everywhere" in c.lower()]
            if candidates:
                log.info("  Found candidates: %s", candidates)
                ev = candidates[0]
                ins = ev.replace("_everywhere_", "_inschool_")
                outs = ev.replace("_everywhere_", "_outschool_")
                all_cols = set(meta.column_names)
                sport_vars[sport] = {
                    "everywhere": ev,
                    "inschool": ins if ins in all_cols else None,
                    "outschool": outs if outs in all_cols else None,
                }
                log.info("  Using: %s", sport_vars[sport])
            else:
                log.error("  No candidates found for '%s'. Listing all sport-like columns...", sport)
                all_sport = [c for c in meta.column_names if "onceawk" in c.lower() and "everywhere" in c.lower()]
                for c in sorted(all_sport)[:30]:
                    log.info("    %s", c)

    # Step 1: Participation trend
    log.info("=" * 60)
    trend = analyse_participation_trend(sport_vars)

    # Step 2: School pipeline
    log.info("=" * 60)
    school = analyse_school_pipeline(sport_vars)

    # Plots
    log.info("=" * 60)
    plot_participation_trend(trend)
    plot_gender_comparison(trend)
    plot_school_pipeline(school)

    log.info("=" * 60)
    log.info("CROSS-SPORT ANALYSIS COMPLETE ✓")
    log.info("Outputs → %s", OUTPUT_DIR)
    log.info("")
    log.info("Next steps:")
    log.info("  1. Check step0_variable_discovery.csv for variable availability")
    log.info("  2. If football/cricket variables have different names in older years,")
    log.info("     update the sport_vars dict and re-run")
    log.info("  3. Insert figures into impact report Analysis 6")


if __name__ == "__main__":
    run_all()
