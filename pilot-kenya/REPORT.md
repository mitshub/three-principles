# Kenya small-area pilot: data-availability audit

Three Principles Initiative · audit date 2026-10-14 · branch `pilot-kenya-audit`

This report records what exists. It does not test anything. Every number here
was computed by a script in `scripts/` from a file downloaded on 2026-10-14
(see `README.md` to reproduce). Terms follow the brief: "persistence" is defined
in Appendix B, and threat, exposure and protective capacity in Section 4.

---

## a) Summary table

| Source | What it measures (brief category) | Smallest reliable geography | Years covered | Repeat measurement? | Access | Licence |
|---|---|---|---|---|---|---|
| **WPdx+** (`eqje-vguj`), Kenya | Water service persistence (water available on day of visit) | Water point (GPS). Enough repeat points for analysis in **6 of 47 counties** (≥30 points spanning ≥3 y) | Records dated 2011–2024. The 2016–2020 gap holds 284 of 23,482 records | Yes: 1,337 points with ≥2 dated records; 831 span ≥3 y; 319 span ≥10 y | Open (Socrata API, no key) | Not stated in dataset metadata. The website says "Data is fully open and free to access" and "© 2020 … All rights reserved". **Not resolved** |
| **WPdx-Basic** (`jfkt-jmqa`), Kenya | As above, every uploaded record | Water point (GPS) | 2011–2024 | Not linked: no `wpdx_id`. Proximity linkage only (sensitivity check) | Open | As above |
| **UCDP GED 26.1** | Threat (organised violence with ≥1 death) | Point for `where_prec`=1 (40.6% of Kenya events). Usable for county or sub-county, not ward (see 2a) | 1989–2025, plus 2026 candidate events Jan–Aug | Yes (event series) | Open download | CC BY 4.0 |
| **ACLED** event data | Threat (political violence, demonstrations) | Not checked: needs an account | n/a | n/a | **Registration required** | ACLED EULA (non-commercial, attribution) |
| **ACLED aggregates on HDX** | Threat, country totals only | **Country** | 1997-01 to 2026-10 | Monthly counts | Open (no account) | ACLED Terms of Use / EULA |
| **Relative Wealth Index** (Kenya file) | Wealth | 2.4 km grid cell (29,483 cells) | One vintage. Inputs "primarily generated in 2018"; Kenya training labels from DHS 2014 | **No: a single snapshot** | Open (HDX) | CC BY-NC 4.0 |
| **OPHI Kenya MPI** (HDX) | Wealth / multidimensional poverty | County (2022 only). Former province (8) for 2008, 2014, 2022 | 2008, 2014, 2022 | At province level only | Open | CC0 |
| **DHS indicator API** (lowest wealth quintile) | Wealth | County for 2022 only. Province/region for 1993–2014 | 1993–2022 (8 surveys) | At region level only | Open API (no key needed for this query) | Not checked |
| **KNBS Kenya Poverty Report 2022** | Wealth / consumption poverty | County (2022 only) | 2022. National/rural/urban trend for 2015/16, 2019, 2020, 2021, 2022 | Not at county level in this report | Open PDF | Not checked |
| **Uwezo Kenya 2014, 2015** (HDX) | Education (learning assessment, household survey) | District (154–155 pre-2010 districts) and sub-location names. No GPS | 2014, 2015 | 2 years, 1 year apart. 1,455 district+sub-location pairs appear in both | Open | CC BY |
| **Uwezo Kenya 2013 tables** (HDX) | Education | District (8 tables) / county (5 tables), going by table titles | 2013 | Single year | Open | CC BY-IGO |
| **School lists** (2005 CCK/OCHA; 2010 MoE sheet) | Education infrastructure (location only) | School point | 2005; 2010 | Different lists with no enrolment or results fields | Open | "Other" (legacy HR.info terms); CC BY |
| **geoBoundaries gbOpen KEN** | Boundaries | ADM1 47, ADM2 290, ADM3 1,452 | "Year represented" 2020; build Dec 2023 | n/a | Open | Public Domain (ADM1); CC BY 3.0 IGO (ADM2); CC BY 4.0 (ADM3) |
| **HDX COD-AB Kenya** | Boundaries | Admin 1 (47), Admin 2 (290) only | Created 2018-07-03, reviewed 2025-01-28 | n/a | Open | CC BY-IGO |

**Exposure** (people and assets within reach of a threat) and **protective
capacity** were not audited as separate sources. Exposure could be built
from the layers above (RWI cell locations, WPdx points, school points, UCDP
events), but only as a static overlay. No sub-national protective-capacity
measure was found or checked.

---

## b) Results by audit item

### 1. Water points (WPdx): `scripts/01_wpdx.py`

**Sources.** Both were accessed 2026-10-14 at about 12:25 UTC via the Socrata API, filtered with `clean_country_name='Kenya'`.

| Dataset | URL | Metadata `rowsUpdatedAt` | File | Rows |
|---|---|---|---|---|
| WPdx+ | `https://data.waterpointdata.org/resource/eqje-vguj.csv` | 2026-10-14 06:15 UTC | `data/wpdx/wpdx_plus_kenya.csv` | 21,953 |
| WPdx-Basic | `https://data.waterpointdata.org/resource/jfkt-jmqa.csv` | 2026-10-14 07:04 UTC | `data/wpdx/wpdx_basic_kenya.csv` | 39,959 |

Licence: the Socrata metadata `license` field is empty for both datasets.
The WPdx About page says "Data is fully open and free to access", and its
footer says "© 2020 Water Point Data Exchange. All rights reserved." We found
no explicit licence. **This should be clarified with WPdx before publishing
derived data.**

**Schema.** Descriptions below are quoted from the dataset metadata (`/api/views/<id>.json`).

- Location: `lat_deg` / `lon_deg`, "Provide the decimal value of the latitude [longitude] in WGS 1984." Admin names `clean_adm1..4` are "based on provided GPS coordinates and GADM boundaries". They contain only 39 distinct `clean_adm1` names, so we assigned counties by spatial join to geoBoundaries instead.
- Report date: `report_date`, "Provide the date that the data was collected on using ISO 8601."
- Functional status, which comes in two fields:
  - `status_id`: "Identify if any water is available on the day of the visit, recognizing that it may be a limited flow." Values: Yes / No / Unknown.
  - `status_clean`: "Categorized version of the #status parameter."
  - **Schema problem:** in Kenya, all 11,601 rows with an empty raw `status` have `status_clean = "Non-Functional"`. Of the 13,578 "Non-Functional" rows, 11,571 have `status_id = "Yes"`. `status_clean` therefore cannot be used for Kenya. **Transitions below use `status_id`**, which is also the only status field stored in the visit history.
  - `status_id` measures water available on the day of the visit, not mechanical functionality. These are not the same.
- Linking repeat records:
  - `wpdx_id` (WPdx+ only): "The Water Point Data Exchange ID. Assigned based on location and used to match records from water points over from different organizations and report dates." Values look like Open Location Codes (e.g. `6G8VRPR3+M55`). This is our reading of the format; the documentation does not say so.
  - `water_point_history` (WPdx+ only): "Summary of previous water point records with same WPdx_id. Only the most recent water point record is displayed in the row." It is a JSON object keyed by report date with `source`, `status_id`, `water_source_clean`, `water_tech_clean` and `photo_lnk`. Two visits on the same date would collapse into one key.
  - `is_latest`: "True/False value indicating if this data is the latest for each water point." All 21,953 Kenya rows are `True`, so WPdx+ holds one row per point.
  - `cluster_size`: "The number of times a location appears in the dataset." It matches the history length for 96.0% of points. By `cluster_size`, 1,938 points have ≥2 records; by history, 1,337 do. The documentation does not explain the difference. **We use the history.**
  - `activity_id`: the "Unique ID for the specific water point infrastructure, as reported by data collector". This is provider-specific, so it does not link across providers.
  - WPdx-Basic has no `wpdx_id` and no history.
- Records that WPdx+ does not show: WPdx-Basic has 39,959 Kenya records, while WPdx+ histories hold 23,482 dated entries. The largest gap is Evidence Action 2023: 13,936 Basic records against about 6,643 history entries. We found no documentation of which records WPdx+ drops or merges. **Not resolved.**

**Repeat records (WPdx+ history, primary).**

| Measure | Value |
|---|---|
| Water points | 21,953 |
| Dated records | 23,482 |
| Points with ≥2 records | **1,337** (2 records: 1,166; 3: 154; 4: 13; ≥5: 4) |
| Span first→last, among repeat points (years) | p10 0.31 · p25 2.59 · **median 6.99** · p75 9.88 · p90 11.4 · max 13.06 |
| Span histogram | <0.5 y: 143 · 0.5–1: 31 · 1–2: 88 · 2–3: 244 · 3–5: 70 · 5–10: 442 · ≥10: 319 |
| Span ≥3 / ≥5 / ≥10 years | **831 / 761 / 319** |
| Most common first→last year pairs (span ≥3 y) | 2012→2023: 188 · 2014→2023: 145 · 2015→2023: 88 · 2012→2024: 69 · 2014→2021: 59 |

Most long-span points have exactly one baseline visit (2011–2015) and one
revisit (2021–2024), with nothing in between.

**Status transitions** (consecutive record pairs, `status_id`):

| Pairs | Yes→Yes | Yes→No | No→Yes | No→No | involving Unknown | total |
|---|---|---|---|---|---|---|
| All | 1,359 | **84** | **45** | 6 | 35 | 1,529 |
| Same source | 708 | 51 | 6 | 5 | 21 | 791 |
| Different source | 651 | 33 | 39 | 1 | 14 | 738 |
| Gap ≥3 years | 751 | **47** | **19** | 0 | 18 | 835 |

84 points have at least one Yes→No and 45 have at least one No→Yes. Nearly
half of the pairs (738 of 1,529) compare records from different organisations,
which may define and survey status differently. Of the 45 No→Yes transitions,
39 are cross-source.

**When the point was built or repaired** (Appendix B treats a new or repaired
point as the "gain"). 10,166 of 21,953 points have `install_year` and **none**
has `rehab_year`. Among points with a span of ≥3 years, 484 of 831 have an
install year, and 458 of those are dated no later than the first record. For
a span of ≥10 years the figures are 278 of 319, and 275.

**Spatial coverage.** Points were joined to geoBoundaries ADM1/2/3 (3 points
fell outside every county). **Threshold: a unit is "analysable" if it has ≥30
repeat-record points.** We chose this because a proportion estimated from 30
points has a 95% interval of about ±18 percentage points at p = 0.5. It is a
minimum, not a recommendation.

| Repeat criterion | Counties ≥30 (of 47) | Counties below | Sub-counties ≥30 (157 with any record, of 290) | Wards ≥30 (591 with any record, of 1,452) |
|---|---|---|---|---|
| ≥2 records | 8: Bungoma, Busia, Homa Bay, Kakamega, Kisumu, Migori, Siaya, Vihiga | 39 | 14 | 8 |
| span ≥3 y | 6: Bungoma, Busia, Homa Bay, Kakamega, Migori, Vihiga | 41 | 11 | 2 |
| span ≥5 y | the same 6 | 41 | 10 | 2 |
| span ≥10 y | 2: Busia (255), Homa Bay (31) | 45 | 4 | 0 |

Eight counties have no records at all: Murang'a, Kirinyaga, Nyeri, Tharaka,
Lamu, Meru, Kwale and Mombasa. The five counties with the most repeat points
hold 83.3% of them. The full per-county table is in `outputs/01_wpdx_by_county.csv`.

| County | Points | Records | Repeat points | span ≥3 y | ≥5 y | ≥10 y |
|---|---|---|---|---|---|---|
| Busia | 3,647 | 4,317 | 542 | 400 | 394 | 255 |
| Kakamega | 4,940 | 5,176 | 206 | 78 | 56 | 7 |
| Migori | 1,356 | 1,541 | 172 | 124 | 124 | 7 |
| Siaya | 2,147 | 2,257 | 105 | 24 | 8 | 0 |
| Vihiga | 1,567 | 1,660 | 88 | 70 | 57 | 17 |
| Kisumu | 1,606 | 1,669 | 58 | 21 | 11 | 0 |
| Bungoma | 799 | 856 | 56 | 53 | 53 | 2 |
| Homa Bay | 860 | 909 | 46 | 41 | 40 | 31 |
| all other 39 counties | 5,028 | 5,093 | 63 | 19 | 17 | 0 |
| outside any county polygon | 3 | 4 | 1 | 1 | 1 | 0 |

**Biases visible in the data.**

- **A few contributors dominate.** There are 15 sources. Three of them (Evidence Action 11,430; USAID/KEA KIWASH 6,838; Virtual Kenya 3,547) provide 92.9% of history records. Repeat points by source combination: Evidence Action only 392; Evidence Action + KIWASH 287; Evidence Action + Virtual Kenya 280; Living Water International only 183.
- **Records cluster in a few years.** Records by year: 2011: 385 · 2012: 3,968 · 2013: 410 · 2014: 1,330 · 2015: 838 · 2016: 62 · 2017: 1 · 2018: 22 · 2019: 72 · 2020: 127 · 2021: 6,955 · 2022: 81 · 2023: 6,693 · 2024: 2,538. Only 284 records fall in 2016–2020, so failure timing between visits cannot be observed.
- **Coverage is geographic, following programmes.** Repeat points sit almost entirely in western Kenya (the Lake Victoria basin counties). The arid north and the coast have almost no repeat records.
- **We cannot see which points were not revisited.** Points that were never revisited, and the reasons, are not recorded.

**Sensitivity: proximity linkage of WPdx-Basic.** Records within r metres were
joined into clusters (connected components, so chaining is possible). This is
not a validated linkage.

| r | Clusters with ≥2 dates | span ≥3 y | ≥5 y | ≥10 y | Yes→No | No→Yes |
|---|---|---|---|---|---|---|
| 3 m | 598 | 283 | 236 | 47 | 47 | 7 |
| 10 m | 1,867 | 1,222 | 1,136 | 310 | 98 | 49 |
| 30 m | 3,666 | 2,608 | 2,488 | 711 | 165 | 110 |

**The repeat count depends heavily on the linkage rule.** The ≥5-year count
ranges from 236 to 2,488 depending on the radius, against 761 with the
official `wpdx_id` linkage. A persistence test would need a validated linkage,
for example checking photographs or `activity_id` for a sample.

### 2. Violence events

#### 2a. UCDP GED: `scripts/02a_ucdp.py`

- **Current version: GED 26.1** (`GEDEvent_v26_1.csv` dated 2026-03-30 inside the zip), covering 1989–2025, 417,968 events worldwide. URL: `https://ucdp.uu.se/downloads/ged/ged261-csv.zip`, accessed 2026-10-14 12:30 UTC. Codebook: `https://ucdp.uu.se/downloads/ged/ged261.pdf`.
- Licence (downloads page): "All datasets are free of charge and licensed under CC BY 4.0".
- Monthly **candidate** (preliminary) releases for 2026 exist: v26.01.26.06 (Jan–Jun), v26.0.7 (Jul) and v26.0.8 (Aug). They are counted separately below.

**Kenya events** (`country == "Kenya"`, `country_id` 501): **1,246 events**, 1989–2025. Every year has at least one event.

| Type | Events |
|---|---|
| non-state | 572 |
| state-based | 345 |
| one-sided | 329 |

Events by year (all types; `best` deaths in `outputs/02a_ucdp.json`):

| 1989 | 1990 | 1991 | 1992 | 1993 | 1994 | 1995 | 1996 | 1997 | 1998 | 1999 | 2000 | 2001 | 2002 | 2003 | 2004 | 2005 | 2006 | 2007 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 1 | 2 | 26 | 18 | 13 | 4 | 9 | 11 | 15 | 8 | 18 | 18 | 5 | 2 | 4 | 29 | 22 | 52 |

| 2008 | 2009 | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 117 | 25 | 28 | 26 | 71 | 49 | 85 | 42 | 48 | 107 | 69 | 51 | 65 | 54 | 31 | 57 | 30 | 31 |

Candidate events for Kenya in 2026: Jan–Jun 31 (3 with `where_prec`=1), Jul 5 (0), Aug 2 (1).

**Geographic precision.** The `where_prec` definitions are quoted from the GED 26.1 codebook:

> 1: exact location of the event known and coded. 2: event occurred within at maximum 25 km radius around a known point. The coded point is the known point. 3: only the second order administrative division where an event happened is known. That administrative division is coded with a point representing it (typically the centroid). 4: only the first order administrative division … 5: … a linear feature … or a fuzzy polygon … 6: only the country … 7: event in international waters or airspace.

| where_prec | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| Kenya events | 506 | 338 | 218 | 101 | 72 | 10 | 1 |
| share | **40.6%** | 27.1% | 17.5% | 8.1% | 5.8% | 0.8% | 0.1% |

- **Ward level** needs `where_prec`=1: **40.6%** of events. A 25 km radius (code 2) is larger than most wards.
- **Sub-county level:** code 1 is safe. Code 2 may place an event in the wrong sub-county. Code 3 gives a "second order administrative division", but the `adm_2` names on code-3 Kenya events mix pre-2010 *districts* ("Mt. Elgon district" 33, "Turkana district" 28) with *constituencies* ("Marakwet East constituency" 10). They do not map cleanly onto current sub-counties. So, for sub-county use: 40.6% certain, 67.7% at most with codes 1–2, and 85.2% for codes 1–3 if a crosswalk is built.
- **Precision is getting worse.** The code-1 share is 42.7% for 1989–99 (110 events), 43.2% for 2000–09 (292), 48.1% for 2010–19 (576) and **20.9% for 2020–25 (268)**.
- Other fields: `event_clarity` is 1 for 1,120 events and 2 for 126. `date_prec` is 1 (exact day) for 960 events.

**Where the precise events fall** (`where_prec`=1, spatial join to geoBoundaries):

| Level | Units | With ≥1 event | With events in ≥2 distinct years | …using 2010–2025 only |
|---|---|---|---|---|
| County | 47 | 39 | 30 | 19 |
| Sub-county | 290 | 96 | 49 | 32 |
| Ward | 1,452 | 156 | **66** | 50 |

**Overlap with the water data.** The six counties with ≥30 WPdx repeat points
spanning ≥3 years have very few precisely located UCDP events, 1989–2025:

| County | WPdx repeat ≥3 y | UCDP code-1 events | distinct years |
|---|---|---|---|
| Busia | 400 | 0 | 0 |
| Migori | 124 | 2 | 1 |
| Kakamega | 78 | 4 | 2 |
| Vihiga | 70 | 0 | 0 |
| Bungoma | 53 | 10 | 4 |
| Homa Bay | 41 | 4 | 3 |

#### 2b. ACLED: `scripts/02b_acled.py`

- **Event-level data need registration. We stopped there.**
  - An unauthenticated request to `https://acleddata.com/api/acled/read?country=Kenya&limit=1` on 2026-10-14 12:37 UTC returned **HTTP 403 `{"message":"Access denied"}`**.
  - The HDX package notes say: "To access full event data, please register to use the Data Export Tool and API on the ACLED website."
  - **Needed:** an ACLED (myACLED) account in the Initiative's own name, accepting the ACLED EULA. We used no credentials.
- **Openly published aggregates.** ACLED publishes Kenya country-month files on HDX (`https://data.humdata.org/dataset/kenya-acled-conflict-data`), which need no account. We downloaded three XLSX files dated "as of 09oct2026": political violence, civilian targeting and demonstrations. Each has 358 rows (Country, Month, Year, Events[, Fatalities]) covering 1997-01 to 2026-10.
  - **These are country totals only, so they cannot be used for sub-national work.**
  - The HDX notes describe them as "reported political violence, civilian-targeting, and demonstration events". The files do not define which ACLED event types make up "political violence", and we have not guessed.
- **Terms.** The HDX licence is "Other": "By using ACLED data you agree to abide by the Terms of Use and Attribution Policy". The ACLED EULA (last updated 8 July 2025) allows use "for non-commercial purposes". It also says "Licensee may only publish or distribute materials incorporating ACLED's data where such materials are transformative", and that content must not be reverse-engineerable. **Check that the comparison table below is acceptable under these terms before publishing this report.**

#### 2c. UCDP vs ACLED, Kenya events per year (country level)

| Year | UCDP GED 26.1 | ACLED political violence | ACLED civilian targeting | ratio ACLED PV / UCDP |
|---|---|---|---|---|
| 1997 | 11 | 106 | 56 | 9.6 |
| 1998 | 15 | 96 | 60 | 6.4 |
| 1999 | 8 | 134 | 55 | 16.8 |
| 2000 | 18 | 146 | 81 | 8.1 |
| 2001 | 18 | 149 | 46 | 8.3 |
| 2002 | 5 | 168 | 99 | 33.6 |
| 2003 | 2 | 92 | 53 | 46.0 |
| 2004 | 4 | 70 | 48 | 17.5 |
| 2005 | 29 | 118 | 72 | 4.1 |
| 2006 | 22 | 97 | 62 | 4.4 |
| 2007 | 52 | 270 | 144 | 5.2 |
| 2008 | 117 | 271 | 164 | 2.3 |
| 2009 | 25 | 96 | 47 | 3.8 |
| 2010 | 28 | 100 | 60 | 3.6 |
| 2011 | 26 | 107 | 64 | 4.1 |
| 2012 | 71 | 250 | 160 | 3.5 |
| 2013 | 49 | 378 | 266 | 7.7 |
| 2014 | 85 | 256 | 163 | 3.0 |
| 2015 | 42 | 161 | 102 | 3.8 |
| 2016 | 48 | 155 | 82 | 3.2 |
| 2017 | 107 | 498 | 286 | 4.7 |
| 2018 | 69 | 381 | 218 | 5.5 |
| 2019 | 51 | 280 | 195 | 5.5 |
| 2020 | 65 | 329 | 212 | 5.1 |
| 2021 | 54 | 393 | 245 | 7.3 |
| 2022 | 31 | 997 | 686 | 32.2 |
| 2023 | 57 | 1,109 | 741 | 19.5 |
| 2024 | 30 | 1,087 | 665 | 36.2 |
| 2025 | 31 | 1,375 | 941 | 44.4 |

The yearly counts correlate at Pearson 0.198 and Spearman 0.702 (1997–2025).
The two sources diverge sharply from 2022: ACLED rises about 2.5-fold while
UCDP falls. We have not established why. The datasets use different inclusion
rules (UCDP requires organised actors and at least one death), so **the choice
of source would change any recurrence result.**

### 3. Wealth: `scripts/03_wealth.py`

**Relative Wealth Index**

- **There is a Kenya file in the public release.** HDX package `relative-wealth-index` (organisation "AI for Good at Meta") has 112 resources, of which **exactly one** is for Kenya: `Kenya_relative_wealth_index.csv`, created 2021-04-08. Accessed 2026-10-14 12:38 UTC.
  - The file has 29,483 rows with columns `latitude, longitude, rwi, error`. **There is no date or year column.** `rwi`: mean −0.275, range −1.625 to 1.753. `error`: mean 0.412.
  - Coverage: at least one cell in 47 of 47 counties, 289 of 290 sub-counties and 1,375 of 1,452 wards. The median is 11 cells per ward.
  - Licence (HDX `license_other`): **CC BY-NC 4.0**.
- **Which year it represents.** The methods (arXiv 2104.07761, SM7 "Cross-sectional estimation") state:

  > "Our main objective is to produce accurate estimates of the current, cross-sectional distribution of wealth and poverty within LMICs. … The ground truth wealth measurements cover a wide range of years (Table S1); the input data are primarily generated in 2018 (Table S2). … our estimates are best at capturing within-country variation in wealth that does not change over a relatively short time horizon (i.e., between the prior survey date and 2018)."

  Table S1 lists Kenya's training survey as **DHS 2014** (36,224 households, 1,585 clusters). The file therefore represents roughly 2014–2018 relative wealth.
- **More than one vintage?** No other Kenya vintage is in the HDX package, and an HDX search for "relative wealth index" found no other RWI package. A web search found no documented newer release. This search was not exhaustive.
- **Conclusion: the RWI is a single snapshot. It cannot show change over time, so it cannot serve as a persistence outcome.** At most it is a baseline covariate. It is also relative within Kenya, so it carries no absolute level.

**Other wealth or poverty series with repeated years.** These were checked by downloading the files.

| Series | URL | Geography × years found | Small-area *and* repeated? |
|---|---|---|---|
| OPHI Kenya MPI (`ken_mpi.csv`) | https://data.humdata.org/dataset/kenya-mpi | 47 counties + national, **DHS 2022 only** | No |
| OPHI Kenya MPI trends (`ken_mpi_trends.csv`) | same | 8 former provinces + national, DHS 2008, 2014, 2022 | Repeated, but province level |
| DHS API, "Population in the lowest wealth quintile" | https://api.dhsprogram.com/rest/dhs/data?countryIds=KE&indicatorIds=HC_WIXQ_P_LOW&breakdown=subnational | 1993: 7 · 1998: 7 · 2003: 8 · 2008: 8 · 2014: 8 (+1 level-2: Nairobi) · 2015 MIS: 5 · 2020 MIS: 5 regions · **2022: 47 counties** | Repeated at region level only. County only in 2022 |
| KNBS, The Kenya Poverty Report 2022 | https://www.knbs.or.ke/wp-content/uploads/2024/10/The-Kenya-Poverty-Report-2022.pdf | Tables 4.3–4.5: county, **2022**. Table 4.2: national/rural/urban for 2015/16, 2019, 2020, 2021, 2022 | No (county tables for one year) |
| KNBS, The Kenya Poverty Report 2021 | https://new.knbs.or.ke/wp-content/uploads/2023/09/The-Kenya-Poverty-Report-2021.pdf | **Not checked:** the TLS certificate had expired (`CERTIFICATE_VERIFY_FAILED`) and we did not bypass it | Unknown |

**No small-area (finer than county) wealth or poverty series with repeated
years was verified.** Repeated, comparable estimates exist only at province or
region level (DHS 1993–2022; MPI 2008/2014/2022).

### 4. Education: `scripts/04_education.py`

Data verified to be finer than county:

- **Uwezo Kenya 2014 and 2015** (household learning assessments, microdata). Sources: https://data.humdata.org/dataset/learning-levels-in-kenya-2014 and https://data.humdata.org/dataset/learning-levels-in-kenya-2015. Licence CC BY.

  | File | Rows | Geography columns |
  |---|---|---|
  | KE14_hhld.csv | 169,274 | `id_district`/`id_districtName` (155 districts), `division_name`, `location`, `sub_location`, `County`, `id_village` (4,441) |
  | KE14_school.csv | 4,377 | as above |
  | KE14_village.csv | 4,443 | plus `constituency` |
  | KE15_hhld.csv | 191,294 | 154 districts, `eacode`, `location`, `sub_location`, `county`, `id_village` (4,550) |
  | KE15_school.csv | 4,704 | as above |
  | KE15_village.csv | 4,544 | plus `constituency` |

  - **No GPS columns** in any file. Columns named `english`, `swahili` and `math` exist in both household files (about 120,000 non-null values each). **We have not interpreted them: no codebook was found with the HDX files.**
  - **Unit of geography:** pre-2010 *districts* (154–155) and sub-locations. These are not the current county/sub-county/ward units, so a crosswalk would be needed.
  - **Repeat measurement:** two years, one year apart. `id_village` is re-numbered between years (ID 1 is in Gatanga in 2014; IDs in the 3000s are in Baringo in 2015), so overlap was matched on names: 3,585 district+sub-location pairs in 2014, 3,632 in 2015, **1,455 in both**.
- **Uwezo Kenya 2013 tables** (https://data.humdata.org/dataset/schooling-status-i-e-children-in-and-out-of-school, CC BY-IGO). These are 29 aggregated tables, 8 titled "per district" and 5 "per county". **Only the titles were checked, not the table contents.**
- **School lists, location only.**
  - 2005 CCK schools (https://data.humdata.org/dataset/kenya-education-0): 3,759 rows, columns `INSTITUTE, LATITUDE, LONGITUDE, DISTRICT, DIVISION`.
  - 2010 MoE sheet (https://data.humdata.org/dataset/kenya-schools): 72,019 rows, with `# Classrooms` but no enrolment or results.
  - These are different lists in different years, not a school panel.

**Conclusion:** we verified **no** public, multi-year education *outcome* series
finer than county that spans more than one year apart. Uwezo gives learning
data by district and sub-location for 2014 and 2015, with partial overlap of
sampled areas. That is too short for a persistence test. Candidates that may
exist but were **not** verified are listed in section (d).

### 5. Boundaries: `scripts/05_boundaries.py`

| Level | Source | Units | Vintage | Licence | Notes |
|---|---|---|---|---|---|
| County (ADM1) | geoBoundaries gbOpen, from RCMRD GeoPortal | 47 | "year represented" 2020; build 2023-12-12; commit `9469f09` | Public Domain | Covers 100% of ADM0 area |
| Sub-county (ADM2) | geoBoundaries gbOpen, from IEBC / OCHA ROSEA | 290 | 2020 | CC BY 3.0 IGO | 290 equals the IEBC constituency count (below), so these are constituencies, not KNBS administrative sub-counties |
| Ward (ADM3) | geoBoundaries gbOpen, from "Benedict Aboki Omare and George Omare" (github.com/benaboki/Kenya-County-Assembly-Boundaries) | **1,452** | 2020 | CC BY 4.0 | Community-made, not an official release. 43 ward names repeat, so join on `shapeID`. Covers 99.4% of ADM0 area |
| Admin 1–2 | HDX COD-AB Kenya (https://data.humdata.org/dataset/cod-ab-ken) | 47 / 290 | "boundaries created by the source" 2018-07-03; reviewed 2025-01-28 | CC BY-IGO | Source IEBC. **No ward level** |

- **Primary source for constituencies and wards.** The IEBC *Final Report on the First Review relating to the Delimitation of Boundaries of Constituencies and Wards*, 6 March 2012 (https://www.iebc.or.ke/uploads/resources/9fIr43YjUT.pdf), sets out the "Methodology for determination of 290 constituencies" and says the Commission "opted to maintain a cap of 1,450 County Assembly Wards". The geoBoundaries ward layer has 1,452 features. **We have not explained the difference of 2.**
- **Boundary changes that affect comparison over time:**
  - The sources use incompatible units. Uwezo 2014/15 uses about 155 pre-2010 districts. UCDP `adm_2` mixes old districts and constituencies. WPdx `clean_adm*` uses GADM names (only 39 counties named). Only point data (WPdx, UCDP code 1) can be re-assigned to current units without a crosswalk.
  - Current counties, constituencies and wards date from the 2010 Constitution and the 2012 IEBC review. Data before 2012 that are recorded by district need a district→county/constituency crosswalk, which we have not found or verified.
  - Whether wards or constituencies have changed since 2012: **not verified**. Press reports say the next IEBC boundary review has been postponed (see section d).

---

## c) What could be tested first

### Supported by data we verified

1. **Water-service persistence, point level, western Kenya, about 6–12 years.**
   - 831 points span ≥3 years and 761 span ≥5 years, but only **6 counties** have ≥30 such points (Busia, Migori, Kakamega, Vihiga, Bungoma, Homa Bay). At sub-county level, 11 units have ≥30 points spanning ≥3 years.
   - The outcome would be water availability at the revisit (`status_id`). Across pairs ≥3 years apart there are 47 Yes→No and 19 No→Yes transitions. Most pairs are Yes→Yes (751).
   - **What this supports:** a descriptive estimate of how often a water point that had water at the first visit (2011–2015) still had water at a revisit (2021–2024), for western Kenya only.
   - **What it does not support:**
     - When failure happened, because there are almost no visits in 2016–2020.
     - Persistence "after external input ended". There is no `rehab_year`, and input dates are not recorded beyond `install_year` (484 of 831 points).
     - National conclusions.
     - Results that are independent of linkage and source definitions. Half the pairs are cross-source, and the counts change several-fold with the linkage radius.
2. **Violence recurrence at county or sub-county level from UCDP GED.**
   - Using code-1 events, 30 counties and 49 sub-counties have events in ≥2 distinct years over 1989–2025. Using 2010–2025, the figures are 19 and 32.
   - A "recurrence within K years after a quiet period" test is possible at **county** level. At sub-county level it is thin, and only possible if code-2 events (within 25 km) are accepted. **At ward level it is not supported:** 66 wards have events in ≥2 years, and precision fell to 20.9% after 2020.
   - UCDP records organised violence with at least one death. Non-organised violence (criminal, communal, domestic: brief Section 4) is not covered. An absence of records is not evidence of peace.

### Would need new data or access

- **A 10-year water backtest (brief Section 8).** 319 points qualify, but only Busia (255) and Homa Bay (31) reach 30. A broader test needs other monitoring data, for example county water-department or WASH programme revisit records.
- **Testing water and safety together, including "does safety act as a gate?"** The counties with water repeat data have 0–10 code-1 UCDP events each over 37 years. The verified data cannot test the interaction. A pilot would need either water revisit data from violence-affected counties (the north and northeast have almost no WPdx repeats) or violence data covering non-organised violence in the west (ACLED event data needs registration, and is not verified at ward level).
- **Wealth persistence at small area.** RWI is a single snapshot, about 2018. Repeated estimates exist only at province or region level (DHS, MPI). County-level estimates were verified for 2022 only.
- **Education persistence at small area.** Uwezo covers only 2014–2015, by district, with partially overlapping samples and no verified codebook. We verified no school-level enrolment or results series.
- **Protective capacity and exposure:** no sub-national series audited.
- **ACLED event-level data:** requires an account (see 2b).

---

## d) Not verified / blocked

| Item | Status | Why |
|---|---|---|
| ACLED event-level Kenya data | **Blocked** | Needs a registered account. The API returned 403 without credentials. We did not register or use anyone's credentials |
| WPdx licence | Not resolved | No licence in the dataset metadata. The website says both "fully open" and "All rights reserved" |
| Why WPdx+ holds fewer records than WPdx-Basic (23,482 vs 39,959) | Not resolved | No documentation found |
| Meaning of the WPdx `cluster_size` vs history-length difference | Not resolved | Undocumented |
| Whether `wpdx_id` is an Open Location Code, and at what precision | Not verified | Format inferred, not documented |
| Composition of ACLED "political violence" aggregates | Not verified | Not defined in the files |
| Reason UCDP and ACLED diverge after 2021 | Not investigated | Out of scope for an audit |
| KNBS Kenya Poverty Report 2021 (and earlier county poverty reports) | **Blocked** | The new.knbs.or.ke TLS certificate had expired. We did not bypass certificate checks |
| KNBS ward/constituency poverty maps ("Spatial Dimensions of Well-Being", 2005/06 KIHBS + 2009 census) and "Exploring Kenya's Inequality" | Not verified | Found by web search only, not downloaded. These would be single snapshots anyway |
| Sub-county small-area poverty estimates (e.g. academic EBP work using 2019 KCHS + census) | Not verified | Found by web search only |
| DHS microdata (GPS-displaced clusters) | Not checked | Download not attempted; access terms not verified. Survey clusters are re-sampled each round, so they would not form a small-area panel |
| DHS API terms of use | Not checked | — |
| Uwezo codebook; Uwezo Kenya 2009–2013 and post-2015 microdata | Not verified | Not on HDX; Uwezo's own site not checked |
| Uwezo 2013 table contents | Partly verified | Titles only |
| KCPE results by school (Open Institute "kcpetrends", 2006–2011) | **Blocked** | apps.openinstitute.com does not resolve (DNS). kcpetrends.org does not resolve |
| openAFRICA / Kenya Open Data catalogue | **Blocked** | HTTP 403 with a browser challenge ("Just a moment…"). We did not work around it |
| Ministry of Education NEMIS / KNEC school-level data | Not checked | No public download located |
| Ward/constituency boundary changes since 2012; status of the overdue IEBC review | Not verified | Press reports (e.g. nation.africa, capitalfm.africa, thestandard.ke) say the review was postponed. Two articles returned 403 and the rest were not opened |
| The 1,452 vs 1,450 ward difference | Not resolved | — |
| District→county/constituency crosswalk | Not found | Needed for Uwezo and older UCDP `adm_2` |
| Exposure and protective-capacity sources | Not audited | Outside the five audit items |
| RWI later vintages beyond HDX | Not exhaustive | Only the HDX package and a web search were checked |

## Sources consulted for terms and definitions (not data)

- WPdx About: https://www.waterpointdata.org/about/
- UCDP downloads page (licence statement): https://ucdp.uu.se/downloads/
- ACLED EULA: https://acleddata.com/eula (last updated 8 July 2025)
- RWI methods: Chi, Fang, Chatterjee & Blumenstock, arXiv 2104.07761 (SM7, Tables S1–S2); PNAS 119(3) e2113658119
- IEBC First Review final report (2012): https://www.iebc.or.ke/uploads/resources/9fIr43YjUT.pdf
