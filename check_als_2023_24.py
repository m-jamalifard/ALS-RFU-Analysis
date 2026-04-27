#!/usr/bin/env python3
"""
ALS 2023-24 Extraction from .tab file — with numeric conversion fix.
"""
import os, logging, glob
from pathlib import Path
import numpy as np, pandas as pd

BASE_DIR   = Path("/home/reza/ALS_RFU_Analysis")
OUTPUT_DIR = BASE_DIR / "output_2023_24"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
log = logging.getLogger(__name__)

GENDER_COL = "GEND3"
KEEP = [
    "age_11", "wt_gross", GENDER_COL, "Region_name",
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


def find_tab_file():
    patterns = ["ALS_Young_2023-24*.tab", "*2023*24*.tab", "*.tab"]
    for pat in patterns:
        matches = glob.glob(str(BASE_DIR / pat))
        if matches:
            log.info("Found .tab file: %s", matches[0])
            return Path(matches[0])
    return None


def read_tab(path):
    log.info("Reading %s ...", path.name)
    header = pd.read_csv(path, sep="\t", nrows=0, encoding="latin1")
    log.info("Total columns in file: %d", len(header.columns))

    present = [c for c in KEEP if c in header.columns]
    missing = [c for c in KEEP if c not in header.columns]
    log.info("Target columns found: %d / %d", len(present), len(KEEP))
    if missing:
        log.warning("Missing columns: %s", missing)

    df = pd.read_csv(path, sep="\t", usecols=present, low_memory=False, encoding="latin1")
    log.info("Read %d rows x %d cols", len(df), len(df.columns))
    return df


def analyse(df):
    # Force ALL columns to numeric (tab file reads as strings)
    for col in df.columns:
        if col != "Region_name":
            df[col] = pd.to_numeric(df[col], errors="coerce")

    age = df["age_11"]
    f = df[(age >= 7) & (age <= 16)].copy()
    log.info("Ages 7-16: %d rows (of %d total)", len(f), len(df))

    w = "wt_gross"
    g = GENDER_COL

    R_ALL = "onceawk_modplus_everywhere_GR_RUGBY_CC018"
    R_UNI = "onceawk_modplus_everywhere_GR_RUGBYUNION_CD0182"
    R_SCH = "onceawk_modplus_inschool_GR_RUGBY_CC018"
    R_OUT = "onceawk_modplus_outschool_GR_RUGBY_CC018"
    FB    = "onceawk_modplus_everywhere_GR_FOOTBALL_CC014"
    FB_S  = "onceawk_modplus_inschool_GR_FOOTBALL_CC014"
    FB_O  = "onceawk_modplus_outschool_GR_FOOTBALL_CC014"
    CK    = "onceawk_modplus_everywhere_GR_CRICKET_CC017"
    CK_S  = "onceawk_modplus_inschool_GR_CRICKET_CC017"
    CK_O  = "onceawk_modplus_outschool_GR_CRICKET_CC017"

    def wt(mask): return f.loc[mask, w].sum()
    def wt_g(mask, gv): return f.loc[mask & (f[g]==gv), w].sum()

    out = open(OUTPUT_DIR / "als_2023_24_summary.txt", "w")
    def p(s): print(s); out.write(s + "\n")

    p("=" * 70)
    p("ALS Young 2023-24 — Full Extraction Summary (from .tab)")
    p(f"Total rows read: {len(df):,}   Ages 7-16: {len(f):,}")
    p(f"Gender column: {g} (1=Male, 2=Female, 3=Other)")
    p(f"Unweighted rugby participants (7-16): {(f[R_ALL]==1).sum():,}")
    p("=" * 70)

    m = f[R_ALL]==1
    rt = wt(m)
    p(f"\n--- Rugby All (CC018, ages 7-16) ---")
    p(f"  Total:  {rt:>12,.0f}")
    p(f"  Male:   {wt_g(m,1):>12,.0f}")
    p(f"  Female: {wt_g(m,2):>12,.0f}")
    p(f"  F%:     {wt_g(m,2)/rt*100 if rt>0 else 0:>8.1f}%")

    if R_UNI in f.columns:
        mu = f[R_UNI]==1
        ut = wt(mu)
        p(f"\n--- Rugby Union (CD0182, ages 7-16) ---")
        p(f"  Total:  {ut:>12,.0f}")
        p(f"  Male:   {wt_g(mu,1):>12,.0f}")
        p(f"  Female: {wt_g(mu,2):>12,.0f}")
        p(f"  F%:     {wt_g(mu,2)/ut*100 if ut>0 else 0:>8.1f}%")

        p(f"\n--- Rugby Union by Age ---")
        p(f"  {'Age':<6s} {'AllRugby':>12s} {'Union':>12s} {'Union%':>8s}")
        for a in range(7, 17):
            af = f[f["age_11"] == a]
            ar = af.loc[af[R_ALL]==1, w].sum()
            au = af.loc[af[R_UNI]==1, w].sum()
            pct = au/ar*100 if ar > 0 else 0
            p(f"  U{a:<4d} {ar:>12,.0f} {au:>12,.0f} {pct:>7.1f}%")

    if R_SCH in f.columns and R_OUT in f.columns:
        sch = wt(f[R_SCH]==1); ous = wt(f[R_OUT]==1)
        bth = wt((f[R_SCH]==1)&(f[R_OUT]==1)); so = sch - bth
        p(f"\n--- School Pipeline (All Rugby, 7-16) ---")
        p(f"  School:       {sch:>12,.0f}")
        p(f"  OutSchool:    {ous:>12,.0f}")
        p(f"  Both:         {bth:>12,.0f}")
        p(f"  School Only:  {so:>12,.0f}  ({so/sch*100 if sch>0 else 0:.1f}%)")

    if FB in f.columns:
        mf = f[FB]==1; ft = wt(mf)
        p(f"\n--- Football (CC014, ages 7-16) ---")
        p(f"  Total:  {ft:>12,.0f}")
        p(f"  Male:   {wt_g(mf,1):>12,.0f}")
        p(f"  Female: {wt_g(mf,2):>12,.0f}")
        p(f"  F%:     {wt_g(mf,2)/ft*100 if ft>0 else 0:>8.1f}%")
        if FB_S in f.columns and FB_O in f.columns:
            fs = wt(f[FB_S]==1); fb = wt((f[FB_S]==1)&(f[FB_O]==1))
            p(f"  School Only:  {fs-fb:>12,.0f}  ({(fs-fb)/fs*100 if fs>0 else 0:.1f}%)")

    if CK in f.columns:
        mc = f[CK]==1; ct = wt(mc)
        p(f"\n--- Cricket (CC017, ages 7-16) ---")
        p(f"  Total:  {ct:>12,.0f}")
        p(f"  Male:   {wt_g(mc,1):>12,.0f}")
        p(f"  Female: {wt_g(mc,2):>12,.0f}")
        p(f"  F%:     {wt_g(mc,2)/ct*100 if ct>0 else 0:>8.1f}%")
        if CK_S in f.columns and CK_O in f.columns:
            cs = wt(f[CK_S]==1); cb = wt((f[CK_S]==1)&(f[CK_O]==1))
            p(f"  School Only:  {cs-cb:>12,.0f}  ({(cs-cb)/cs*100 if cs>0 else 0:.1f}%)")

    if "Region_name" in f.columns:
        p(f"\n--- Regional All-Rugby (7-16) ---")
        p(f"  {'Region':<35s} {'Total':>12s} {'Male':>12s} {'Female':>12s}")
        rf = f[f[R_ALL]==1]
        for reg in sorted(rf["Region_name"].dropna().unique()):
            rm = rf[rf["Region_name"]==reg]
            p(f"  {str(reg):<35s} {rm[w].sum():>12,.0f} {rm.loc[rm[g]==1,w].sum():>12,.0f} {rm.loc[rm[g]==2,w].sum():>12,.0f}")

    out.close()
    log.info("Summary saved to %s", OUTPUT_DIR / "als_2023_24_summary.txt")


def main():
    os.chdir(BASE_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tab = find_tab_file()
    if tab is None:
        log.error("No .tab file found!")
        return
    df = read_tab(tab)
    analyse(df)
    log.info("DONE")

if __name__ == "__main__":
    main()