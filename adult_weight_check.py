#!/usr/bin/env python3
"""
Diagnose the Adult 16-18 weight issue.
Run: cd path/ALS_RFU_Analysis && python adult_weight_check.py
"""
import pyreadstat
import numpy as np

for f in ['ALS_Adult_2017-18.sav', 'ALS_Adult_2021-22.sav']:
    print(f"\n{'='*60}")
    print(f"FILE: {f}")
    print(f"{'='*60}")
    
    df, meta = pyreadstat.read_sav(f,
        usecols=['Age17','Age19plus','wt_final','MONTHS_12_RUGBYUNION_F03',
                 'CLUB_RUGBYUNION_F03','Gend3'])
    
    # All respondents
    print(f"\nAll respondents: {len(df):,}")
    print(f"Sum wt_final (all): {df['wt_final'].sum():,.0f}")
    print(f"Mean wt_final (all): {df['wt_final'].mean():.4f}")
    
    # Under-19 (16-18)
    u19 = df[(df['Age17']==1.0) & (df['Age19plus']==0.0)]
    print(f"\nUnder-19 respondents: {len(u19):,}")
    print(f"Sum wt_final (under-19): {u19['wt_final'].sum():,.0f}")
    print(f"Mean wt_final (under-19): {u19['wt_final'].mean():.4f}")
    
    # Rugby union participants
    ru = u19[u19['MONTHS_12_RUGBYUNION_F03']==1]
    print(f"\nRugby union (under-19): {len(ru)} unweighted")
    print(f"Rugby union weighted: {ru['wt_final'].sum():,.0f}")
    
    # Club members
    cl = u19[u19['CLUB_RUGBYUNION_F03']==1]
    print(f"Club members (under-19): {len(cl)} unweighted")
    print(f"Club members weighted: {cl['wt_final'].sum():,.0f}")
    
    # Participation RATE
    rate = len(ru) / len(u19) * 100 if len(u19) > 0 else 0
    rate_wt = ru['wt_final'].sum() / u19['wt_final'].sum() * 100 if u19['wt_final'].sum() > 0 else 0
    print(f"\nParticipation rate (unweighted): {rate:.2f}%")
    print(f"Participation rate (weighted):   {rate_wt:.2f}%")
    
    # Check if there's a grossing weight
    for col_name in ['wt_gross', 'grossing_weight', 'wt_pop', 'weight_gross']:
        _, m = pyreadstat.read_sav(f, metadataonly=True)
        matches = [c for c in m.column_names if col_name.lower() in c.lower()]
        if matches:
            print(f"\nFound potential grossing weight: {matches}")
    
    # Check ALL weight columns
    _, m = pyreadstat.read_sav(f, metadataonly=True)
    wt_cols = [c for c in m.column_names if 'wt' in c.lower() or 'weight' in c.lower() or 'gross' in c.lower()]
    print(f"\nAll weight-related columns: {wt_cols}")

    # If wt_gross exists, check it
    if 'wt_gross' in m.column_names:
        df2, _ = pyreadstat.read_sav(f, usecols=['wt_gross','Age17','Age19plus','MONTHS_12_RUGBYUNION_F03'])
        u19_g = df2[(df2['Age17']==1.0) & (df2['Age19plus']==0.0)]
        ru_g = u19_g[u19_g['MONTHS_12_RUGBYUNION_F03']==1]
        print(f"\nUsing wt_gross instead:")
        print(f"  Sum wt_gross (under-19): {u19_g['wt_gross'].sum():,.0f}")
        print(f"  Rugby union weighted (wt_gross): {ru_g['wt_gross'].sum():,.0f}")

print(f"\n{'='*60}")
print("DONE — share output with Claude")
print(f"{'='*60}")
