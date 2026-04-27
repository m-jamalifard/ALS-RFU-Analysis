#!/usr/bin/env python3
"""
Task 3: SES/IMD Analysis — Rugby Participation by Deprivation
==============================================================
Analyses rugby participation trends by IMD quintile across all
available ALS CYP waves (2017-18 through 2022-23).

Step 0: Check IMD_QUINTILE exists in all waves
Step 1: Classify by IMD quintile (Q1 most deprived → Q5 least deprived)
Step 2: Rugby participation by IMD quintile over time
Step 2B: Gender × IMD over time
Step 2C: Age groups × IMD
Step 3: Summary tables for Report 1

Run: cd path/ALS_RFU_Analysis && python als_ses_analysis.py

Output: output_ses/
"""

import os, logging
from pathlib import Path
import numpy as np, pandas as pd, pyreadstat
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import warnings; warnings.filterwarnings("ignore")

BASE_DIR   = Path("path/ALS_RFU_Analysis")
OUTPUT_DIR = BASE_DIR / "output_ses"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
log = logging.getLogger(__name__)

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 11,
    "axes.titlesize": 13, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white",
})

YOUNG_FILES = [
    {"file": "ALS_Young_2017-18.sav", "year": "2017-18"},
    {"file": "ALS_Young_2018-19.sav", "year": "2018-19"},
    {"file": "ALS_Young_2019-20.sav", "year": "2019-20"},
    {"file": "ALS_Young_2020-21.sav", "year": "2020-21"},
    {"file": "ALS_Young_2021-22.sav", "year": "2021-22"},
    {"file": "ALS_Young_2022-23.sav", "year": "2022-23"},
]

COL_AGE    = "age_11"
COL_GENDER = "gend3"
COL_WEIGHT = "wt_gross"
COL_RUGBY  = "onceawk_modplus_everywhere_GR_RUGBY_CC018"
COL_UNION  = "onceawk_modplus_everywhere_GR_RUGBYUNION_CD0182"
COL_IMD    = "IMD_QUINTILE"

# Also check these alternatives
IMD_ALTERNATIVES = ["IMD_QUINTILE", "IMDDECILE", "IMD10_GR3",
                     "IDACI_DECILE", "IDACI_QUNTILE", "IDACI10_GR3"]

GR = "#E5E7EB"
Q_COLOURS = {1: "#DC2626", 2: "#D97706", 3: "#059669", 4: "#2563EB", 5: "#7C3AED"}
Q_LABELS  = {1: "Q1 (Most deprived)", 2: "Q2", 3: "Q3", 4: "Q4", 5: "Q5 (Least deprived)"}
kfmt = mticker.FuncFormatter(lambda v, _: f"{v:,.0f}")


# ══════════════════════════════════════════════════════════════
# STEP 0: Check IMD variable availability across all waves
# ══════════════════════════════════════════════════════════════

def step0_check_imd():
    log.info("=" * 60)
    log.info("STEP 0: Checking IMD variable availability")
    log.info("=" * 60)

    results = []
    for cfg in YOUNG_FILES:
        path = BASE_DIR / cfg["file"]
        year = cfg["year"]
        try:
            _, meta = pyreadstat.read_sav(str(path), metadataonly=True)
            cols = set(meta.column_names)
            row = {"Year": year}
            for imd_var in IMD_ALTERNATIVES:
                row[imd_var] = imd_var in cols
            results.append(row)

            # Also check value labels if IMD_QUINTILE exists
            if COL_IMD in cols:
                labels = meta.variable_value_labels.get(COL_IMD, {})
                log.info("  %s: IMD_QUINTILE ✓ (labels: %s)", year, labels)
            else:
                # Check case variants
                matches = [c for c in cols if "IMD" in c.upper() and "QUINT" in c.upper()]
                log.info("  %s: IMD_QUINTILE ✗ (alternatives: %s)", year, matches)

        except Exception as e:
            log.error("  %s: FAILED (%s)", year, e)
            row = {"Year": year}
            for v in IMD_ALTERNATIVES:
                row[v] = "ERROR"
            results.append(row)

    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_DIR / "step0_imd_availability.csv", index=False)
    log.info("\n%s", df.to_string(index=False))
    return df


# ══════════════════════════════════════════════════════════════
# STEP 1-2: Extract rugby participation by IMD quintile
# ══════════════════════════════════════════════════════════════

def load_year(cfg):
    """Load one ALS year with target columns."""
    path = BASE_DIR / cfg["file"]
    _, meta = pyreadstat.read_sav(str(path), metadataonly=True)
    cols = set(meta.column_names)

    # Determine which columns to load
    want = [COL_AGE, COL_GENDER, COL_WEIGHT, COL_RUGBY]
    if COL_UNION in cols:
        want.append(COL_UNION)
    if COL_IMD in cols:
        want.append(COL_IMD)
    else:
        # Try case variants
        for c in cols:
            if c.upper() == COL_IMD.upper():
                want.append(c)
                break

    present = [c for c in want if c in cols]
    df, _ = pyreadstat.read_sav(str(path), usecols=present)

    # Filter to ages 7-16
    age = pd.to_numeric(df[COL_AGE], errors="coerce")
    df = df[(age >= 7) & (age <= 16)].copy()

    return df


def step2_participation_by_imd():
    log.info("=" * 60)
    log.info("STEP 2: Rugby participation by IMD quintile over time")
    log.info("=" * 60)

    rows_overall = []
    rows_gender = []
    rows_age = []

    for cfg in YOUNG_FILES:
        year = cfg["year"]
        log.info("Processing %s...", year)

        try:
            df = load_year(cfg)
        except Exception as e:
            log.error("  %s: FAILED to load (%s)", year, e)
            continue

        # Check if IMD column exists
        imd_col = None
        for c in df.columns:
            if c.upper() == COL_IMD.upper():
                imd_col = c
                break

        if imd_col is None:
            log.warning("  %s: No IMD column found, skipping", year)
            continue

        imd = pd.to_numeric(df[imd_col], errors="coerce")
        # Filter to valid quintiles 1-5
        valid_imd = imd.between(1, 5)
        df_imd = df[valid_imd].copy()
        df_imd["IMD_Q"] = imd[valid_imd].astype(int)

        log.info("  Rows with valid IMD: %d / %d", len(df_imd), len(df))

        # ── A: Overall participation by IMD ──
        for q in range(1, 6):
            qdf = df_imd[df_imd["IMD_Q"] == q]
            total_wt = qdf[COL_WEIGHT].sum()
            rugby_wt = qdf.loc[qdf[COL_RUGBY] == 1, COL_WEIGHT].sum()
            rate = rugby_wt / total_wt * 100 if total_wt > 0 else 0

            rows_overall.append({
                "Year": year, "IMD_Quintile": q,
                "Total_Weighted": total_wt,
                "Rugby_Weighted": rugby_wt,
                "Rugby_Rate_%": rate,
            })
            log.info("    Q%d: Total=%,.0f  Rugby=%,.0f  Rate=%.1f%%", q, total_wt, rugby_wt, rate)

        # ── B: Gender × IMD ──
        for q in range(1, 6):
            qdf = df_imd[df_imd["IMD_Q"] == q]
            for gv, glabel in [(1, "Male"), (2, "Female")]:
                gdf = qdf[qdf[COL_GENDER] == gv]
                total_wt = gdf[COL_WEIGHT].sum()
                rugby_wt = gdf.loc[gdf[COL_RUGBY] == 1, COL_WEIGHT].sum()
                rate = rugby_wt / total_wt * 100 if total_wt > 0 else 0
                rows_gender.append({
                    "Year": year, "IMD_Quintile": q, "Gender": glabel,
                    "Total_Weighted": total_wt,
                    "Rugby_Weighted": rugby_wt,
                    "Rugby_Rate_%": rate,
                })

        # ── C: Age group × IMD ──
        age = pd.to_numeric(df_imd[COL_AGE], errors="coerce")
        age_groups = {"7-10": (7, 10), "11-13": (11, 13), "14-16": (14, 16)}
        for ag_label, (lo, hi) in age_groups.items():
            for q in range(1, 6):
                mask = (df_imd["IMD_Q"] == q) & age.between(lo, hi)
                adf = df_imd[mask]
                total_wt = adf[COL_WEIGHT].sum()
                rugby_wt = adf.loc[adf[COL_RUGBY] == 1, COL_WEIGHT].sum()
                rate = rugby_wt / total_wt * 100 if total_wt > 0 else 0
                rows_age.append({
                    "Year": year, "IMD_Quintile": q, "Age_Group": ag_label,
                    "Total_Weighted": total_wt,
                    "Rugby_Weighted": rugby_wt,
                    "Rugby_Rate_%": rate,
                })

    # Save CSVs
    df_overall = pd.DataFrame(rows_overall)
    df_gender = pd.DataFrame(rows_gender)
    df_age = pd.DataFrame(rows_age)

    df_overall.to_csv(OUTPUT_DIR / "ses_rugby_by_imd.csv", index=False)
    df_gender.to_csv(OUTPUT_DIR / "ses_rugby_by_imd_gender.csv", index=False)
    df_age.to_csv(OUTPUT_DIR / "ses_rugby_by_imd_age.csv", index=False)

    log.info("CSVs saved to %s", OUTPUT_DIR)
    return df_overall, df_gender, df_age


# ══════════════════════════════════════════════════════════════
# PLOTS
# ══════════════════════════════════════════════════════════════

def plot_overall(df):
    """Fig 1: Rugby participation rate by IMD quintile over time."""
    log.info("Plotting: overall participation by IMD")

    fig, ax = plt.subplots(figsize=(11, 6))
    for q in range(1, 6):
        sdf = df[df["IMD_Quintile"] == q].sort_values("Year")
        ax.plot(sdf["Year"], sdf["Rugby_Rate_%"], "o-", color=Q_COLOURS[q],
                lw=2.5, ms=7, label=Q_LABELS[q])

    ax.set_ylabel("Rugby Participation Rate (%)")
    ax.set_title("Rugby Participation Rate by IMD Quintile (Ages 7–16)")
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(axis="y", color=GR)
    ax.tick_params(axis="x", rotation=20)
    plt.savefig(OUTPUT_DIR / "fig_ses_overall.png", dpi=150, bbox_inches="tight")
    plt.close()


def plot_gender(df):
    """Fig 2: Rugby participation rate by IMD × gender."""
    log.info("Plotting: gender × IMD")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw={"wspace": 0.30})

    for q in range(1, 6):
        # Male
        sdf = df[(df["IMD_Quintile"] == q) & (df["Gender"] == "Male")].sort_values("Year")
        ax1.plot(sdf["Year"], sdf["Rugby_Rate_%"], "o-", color=Q_COLOURS[q],
                 lw=2, ms=6, label=Q_LABELS[q])
        # Female
        sdf = df[(df["IMD_Quintile"] == q) & (df["Gender"] == "Female")].sort_values("Year")
        ax2.plot(sdf["Year"], sdf["Rugby_Rate_%"], "o-", color=Q_COLOURS[q],
                 lw=2, ms=6, label=Q_LABELS[q])

    ax1.set_title("A   Male Rugby Rate by IMD"); ax1.set_ylabel("Rate (%)")
    ax1.legend(fontsize=7); ax1.grid(axis="y", color=GR); ax1.tick_params(axis="x", rotation=20)
    ax2.set_title("B   Female Rugby Rate by IMD"); ax2.set_ylabel("Rate (%)")
    ax2.legend(fontsize=7); ax2.grid(axis="y", color=GR); ax2.tick_params(axis="x", rotation=20)

    plt.savefig(OUTPUT_DIR / "fig_ses_gender.png", dpi=150, bbox_inches="tight")
    plt.close()


def plot_age_groups(df):
    """Fig 3: Rugby participation rate by IMD × age group (latest year)."""
    log.info("Plotting: age group × IMD")

    latest = df[df["Year"] == df["Year"].max()]
    age_groups = sorted(latest["Age_Group"].unique())

    fig, axes = plt.subplots(1, len(age_groups), figsize=(5 * len(age_groups), 5),
                              gridspec_kw={"wspace": 0.30})
    if len(age_groups) == 1:
        axes = [axes]

    for i, ag in enumerate(age_groups):
        ax = axes[i]
        agdf = latest[latest["Age_Group"] == ag]
        x = np.arange(5)
        bars = ax.bar(x, agdf.sort_values("IMD_Quintile")["Rugby_Rate_%"],
                       color=[Q_COLOURS[q] for q in range(1, 6)], alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels([f"Q{q}" for q in range(1, 6)])
        ax.set_title(f"Ages {ag}")
        ax.set_ylabel("Rate (%)" if i == 0 else "")
        ax.grid(axis="y", color=GR)

        for j, (_, r) in enumerate(agdf.sort_values("IMD_Quintile").iterrows()):
            ax.text(j, r["Rugby_Rate_%"] + 0.3, f"{r['Rugby_Rate_%']:.1f}%",
                    ha="center", fontsize=8, fontweight="bold")

    fig.suptitle(f"Rugby Participation Rate by IMD Quintile and Age ({latest['Year'].iloc[0]})",
                  fontsize=13, fontweight="bold", y=1.02)
    plt.savefig(OUTPUT_DIR / "fig_ses_age.png", dpi=150, bbox_inches="tight")
    plt.close()


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    os.chdir(BASE_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Step 0: Check availability
    avail = step0_check_imd()

    # Check if we can proceed
    imd_available = avail[COL_IMD].sum() if COL_IMD in avail.columns else 0
    if imd_available == 0:
        log.error("IMD_QUINTILE not found in any wave! Check step0_imd_availability.csv")
        log.info("The script checked these variables: %s", IMD_ALTERNATIVES)
        log.info("Please check the column names in your ALS files and update COL_IMD if needed.")
        return

    log.info("\nIMD_QUINTILE available in %d / %d waves", imd_available, len(YOUNG_FILES))

    # Steps 1-2: Extract and analyse
    df_overall, df_gender, df_age = step2_participation_by_imd()

    if len(df_overall) == 0:
        log.error("No data extracted! Check logs above.")
        return

    # Plots
    log.info("=" * 60)
    log.info("Generating plots")
    log.info("=" * 60)
    plot_overall(df_overall)
    plot_gender(df_gender)
    plot_age_groups(df_age)

    log.info("=" * 60)
    log.info("SES ANALYSIS COMPLETE ✓")
    log.info("Outputs → %s", OUTPUT_DIR)
    log.info("")
    log.info("Files produced:")
    log.info("  step0_imd_availability.csv    — IMD variable check per wave")
    log.info("  ses_rugby_by_imd.csv          — overall rugby rate by IMD × year")
    log.info("  ses_rugby_by_imd_gender.csv   — rugby rate by IMD × gender × year")
    log.info("  ses_rugby_by_imd_age.csv      — rugby rate by IMD × age group × year")
    log.info("  fig_ses_overall.png           — trend plot")
    log.info("  fig_ses_gender.png            — gender × IMD plot")
    log.info("  fig_ses_age.png               — age group × IMD plot")
    log.info("")
    log.info("Send the output_ses/ folder and I'll incorporate into Report 1.")


if __name__ == "__main__":
    main()
