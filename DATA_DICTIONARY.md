# Data Dictionary — ALS–RFU Youth Rugby Analysis

## 1. Input Data Files

### 1.1 ALS CYP Survey Files

| File | Year | Rows | Cols | Rugby Union? | Gender Col | Notes |
|------|------|------|------|-------------|------------|-------|
| `ALS_Young_2017-18.sav` | 2017-18 | ~96K | ~2,100 | No | `gend3` | |
| `ALS_Young_2018-19.sav` | 2018-19 | ~98K | ~2,200 | No | `gend3` | |
| `ALS_Young_2019-20.sav` | 2019-20 | ~105K | ~2,300 | No | `gend3` | |
| `ALS_Young_2020-21.sav` | 2020-21 | ~87K | ~2,400 | No | `gend3` | COVID-affected |
| `ALS_Young_2021-22.sav` | 2021-22 | ~100K | ~2,500 | No | `gend3` | |
| `ALS_Young_2022-23.sav` | 2022-23 | ~110K | ~2,800 | **Yes** | `gend3` | First year with Rugby Union variable |
| `ALS_Young_2023-24.sav` | 2023-24 | 122,480* | 5,454 | **Yes** | `GEND3` | *.sav truncated at ~8K rows. Use .tab instead |
| `ALS_Young_2023-24.tab` | 2023-24 | 131,148 | 5,454 | **Yes** | `GEND3` | .tab works with encoding="latin1" + pd.to_numeric() |

### 1.2 RFU GMS Files

| File | Coverage | Clubs | Structure |
|------|----------|-------|-----------|
| `RFU_Data_2011_23.xlsx` | 2011–2023 (one sheet per year) | ~1,858 | Columns: Area, Region, CB, Club, U7M...U19F, 19+M/F |
| `RFU_Data_New.xlsx` | 2023-24 | ~871 | Two-row headers, wider age range (0-U19), "Prefer to self describe" at U14 |

---

## 2. Key ALS Variables

### 2.1 Demographics

| Variable | Label | Type | Values |
|----------|-------|------|--------|
| `age_11` | Age | Integer | 5–16 (negative = missing codes) |
| `gend3` / `GEND3` | Gender | Integer | 1=Male, 2=Female, 3=Other |
| `wt_gross` | Grossing weight | Float | Population weight for survey estimates |
| `Region_name` | English region | String/Float | 9 regions (may be coded numerically in .tab) |
| `IMD_QUINTILE` | IMD deprivation quintile | Integer | 1=Most deprived, 5=Least deprived |
| `IMDDECILE` | IMD deprivation decile | Integer | 1–10 |
| `IDACI_DECILE` | Income deprivation (children) decile | Integer | 1–10 |

### 2.2 Rugby Variables

| Variable | Label | Available From | Notes |
|----------|-------|---------------|-------|
| `onceawk_modplus_everywhere_GR_RUGBY_CC018` | Any rugby (union, league, touch, tag) | All waves | 1=Yes, 2=No |
| `onceawk_modplus_everywhere_GR_RUGBYUNION_CD0182` | Rugby Union specifically | 2022-23+ | 1=Yes, 2=No |
| `onceawk_modplus_inschool_GR_RUGBY_CC018` | Any rugby — in school | All waves | 1=Yes, 2=No |
| `onceawk_modplus_outschool_GR_RUGBY_CC018` | Any rugby — outside school | All waves | 1=Yes, 2=No |
| `onceawk_modplus_inschool_GR_RUGBYUNION_CD0182` | Rugby Union — in school | 2022-23+ | 1=Yes, 2=No |
| `onceawk_modplus_outschool_GR_RUGBYUNION_CD0182` | Rugby Union — outside school | 2022-23+ | 1=Yes, 2=No |

### 2.3 Cross-Sport Variables

| Variable | Sport |
|----------|-------|
| `onceawk_modplus_everywhere_GR_FOOTBALL_CC014` | Football (any code) |
| `onceawk_modplus_inschool_GR_FOOTBALL_CC014` | Football — in school |
| `onceawk_modplus_outschool_GR_FOOTBALL_CC014` | Football — outside school |
| `onceawk_modplus_everywhere_GR_CRICKET_CC017` | Cricket |
| `onceawk_modplus_inschool_GR_CRICKET_CC017` | Cricket — in school |
| `onceawk_modplus_outschool_GR_CRICKET_CC017` | Cricket — outside school |

---

## 3. RFU GMS Structure

### 3.1 Old File (`RFU_Data_2011_23.xlsx`)
- One sheet per year (e.g. "Players-2023 May")
- Columns: `Area`, `Region`, `Constituent Body`, `Club`, then age-gender columns: `U7M`, `U7F`, `U8M`, `U8F`, ... `U19M`, `U19F`, `19+M`, `19+F`
- Last row is a summary row (must be excluded)
- 34 Constituent Bodies

### 3.2 New File (`RFU_Data_New.xlsx`)
- Single sheet
- Two-row headers (row 1 = age group, row 2 = gender)
- Age range: 0 through U19
- "Prefer to self describe" category at U14+
- 30 Constituent Bodies
- No Area/Region columns

### 3.3 CB-to-Region Mapping
RFU Constituent Bodies are mapped to ALS 9 English regions:

| CB | ALS Region |
|----|-----------|
| Middlesex County RFU | London |
| Yorkshire RFU | Yorkshire and the Humber |
| Lancashire County RFU | North West |
| Cheshire RFU | North West |
| Cumbria RFU Ltd. | North West |
| Durham County Rugby Union | North East |
| Northumberland Rugby Union | North East |
| Eastern Counties Rugby Union | East |
| Essex County RFU | East |
| Hertfordshire RFU | East |
| East Midlands Rugby Union | East Midlands |
| Leicestershire Rugby Union Ltd | East Midlands |
| Notts, Lincs & Derbyshire RFU | East Midlands |
| North Midlands RFU | West Midlands |
| Staffordshire County RFU | West Midlands |
| Warwickshire RFU | West Midlands |
| Berkshire County RFU | South East |
| Buckinghamshire County RFU | South East |
| Hampshire RFU Ltd. | South East |
| Kent County RFU | South East |
| Oxfordshire RFU | South East |
| Surrey Rugby | South East |
| Sussex RFU Ltd. | South East |
| Cornwall RFU | South West |
| Devon RFU | South West |
| Dorset & Wilts RFU | South West |
| Gloucestershire RFU | South West |
| Somerset County RFU Limited | South West |

National/military CBs (Army, RAF, Students etc.) are excluded from regional analysis.

---

## 4. Output Files

### 4.1 Stratified Analysis (`output_stratified/`)

| File | Content |
|------|---------|
| `als_all_rugby_by_year.csv` | ALS all-rugby weighted totals by year, gender |
| `als_union_2022_23.csv` | Rugby Union variable (2022-23), by age and gender |
| `rfu_trend.csv` | RFU registration totals by year, gender |
| `rfu_age_profile.csv` | RFU registrations by single age group |
| `benchmark_comparison.csv` | ALS Union vs RFU by age (11-16) |

### 4.2 Impact Analysis (`output_impact/`)

| File | Content |
|------|---------|
| `analysis1_dropout_cascade.csv` | RFU registrations by age group (2023-24) |
| `analysis2_benchmark_2022_23.csv` | ALS Union vs RFU by age (single year) |
| `analysis2_benchmark_regional.csv` | Regional benchmark comparison |
| `analysis3_pipeline.csv` | School vs outside-school by year |
| `analysis5_regional_opportunity.csv` | Regional capture rates with gender split |
| `analysis6_gender_als.csv` | ALS gender trend |
| `analysis6_gender_rfu.csv` | RFU gender trend |

### 4.3 Cross-Sport (`output_cross_sport/`)

| File | Content |
|------|---------|
| `step0_variable_discovery.csv` | Variable availability per sport per wave |
| `sport_participation_trend.csv` | Total/male/female by sport by year |
| `sport_school_pipeline.csv` | School/outside-school by sport by year |

### 4.4 SES/IMD (`output_ses/`)

| File | Content |
|------|---------|
| `step0_imd_availability.csv` | IMD variable availability per wave |
| `ses_rugby_by_imd.csv` | Rugby rate by IMD quintile × year |
| `ses_rugby_by_imd_gender.csv` | Rugby rate by IMD × gender × year |
| `ses_rugby_by_imd_age.csv` | Rugby rate by IMD × age group × year |

### 4.5 ALS 2023-24 Extraction (`output_2023_24/`)

| File | Content |
|------|---------|
| `als_2023_24_summary.csv` | All extracted metrics in machine-readable format |
| `als_2023_24_summary.txt` | Human-readable summary with all key numbers |

---

## 5. Verified Data Points (Report 1 & 2)

These values have been verified against the pipeline CSVs and should be used as ground truth:

| Metric | Value | Source |
|--------|-------|--------|
| RFU peak year | 2019 (225,462) | `rfu_trend.csv` |
| RFU 2023 low | 162,658 (May 2023) | Old RFU file |
| RFU 2023-24 | 171,994 | New RFU file |
| RFU female share | 8% (2018) → 13% (2023-24) | `rfu_trend.csv` |
| ALS all-rugby 2022-23 | 534,605 | `als_all_rugby_by_year.csv` |
| ALS female share | 24-26% | Stable across waves |
| School-only rugby | 31% (~131,000 children, 2022-23) | `analysis3_pipeline.csv` |
| London capture rate | 8% (110 clubs, gap/club=502) | `analysis5_regional_opportunity.csv` |
| Football 2022-23 | 2,486K participants | `sport_participation_trend.csv` |
| Cricket 2022-23 | 490K participants | `sport_participation_trend.csv` |
| SES gap (Q5−Q1) | 2.6pp (2017) → 1.0pp (2022) | `ses_rugby_by_imd.csv` |
| ALS all-rugby 2023-24 | 525,096 | `als_2023_24_summary.csv` |
| ALS Rugby Union 2023-24 | 127,443 | `als_2023_24_summary.csv` |
| Football 2023-24 | 2,493,173 | `als_2023_24_summary.csv` |
| Cricket 2023-24 | 455,297 | `als_2023_24_summary.csv` |

---

## 6. Version Log

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-03-15 | 1.0 | Initial pipeline: 5 ALS waves, old RFU file | RSJ |
| 2026-03-30 | 1.1 | Added Rugby Union variable analysis (2022-23) | RSJ |
| 2026-04-01 | 1.2 | Added new RFU file (2023-24), regional analysis | RSJ |
| 2026-04-09 | 2.0 | Report 1 and Report 2 complete, all Ben comments addressed | RSJ |
| 2026-04-12 | 2.1 | Cross-sport comparison (football, cricket) | RSJ |
| 2026-04-17 | 2.2 | SES/IMD deprivation analysis | RSJ |
| 2026-04-17 | 2.3 | Task 2 (REF cross-sport) and Task 3 (SES) added to Report 1 | RSJ |
| 2026-04-27 | 2.4 | ALS 2023-24 extracted via .tab workaround; user guide and documentation finalised | RSJ |
