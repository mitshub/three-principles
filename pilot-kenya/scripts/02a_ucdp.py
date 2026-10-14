"""Audit item 2a: UCDP GED, Kenya.

Downloads UCDP GED 26.1 (global CSV) and the codebook, filters Kenya
(country == 'Kenya'), and reports events by year, by type of violence and by
geographic precision (where_prec). Also counts the 2026 candidate events
(preliminary monthly releases), kept separate from the released version.

where_prec codes (GED 26.1 codebook, quoted in REPORT.md):
 1 exact location; 2 within max 25 km radius of a known point; 3 only ADM2
 known (centroid); 4 only ADM1 known; 5 linear feature / fuzzy polygon;
 6 only country; 7 international waters/airspace.

Run: .venv/bin/python -I scripts/02a_ucdp.py   (after 05_boundaries.py; uses 01_wpdx.py output if present)
"""
import io
import json
import sys
import zipfile

import geopandas as gpd
import pandas as pd

sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import DATA, OUT, download, write_json  # noqa: E402

GED_ZIP = "https://ucdp.uu.se/downloads/ged/ged261-csv.zip"
CODEBOOK = "https://ucdp.uu.se/downloads/ged/ged261.pdf"
CANDIDATE = {
    "26.01.26.06 (Jan-Jun 2026)": "https://ucdp.uu.se/downloads/candidateged/GEDEvent_v26_01_26_06.csv",
    "26.0.7 (Jul 2026)": "https://ucdp.uu.se/downloads/candidateged/GEDEvent_v26_0_7.csv",
    "26.0.8 (Aug 2026)": "https://ucdp.uu.se/downloads/candidateged/GEDEvent_v26_0_8.csv",
}
TYPES = {1: "state-based", 2: "non-state", 3: "one-sided"}


def load_ged():
    z, _ = download(GED_ZIP, "ucdp/ged261-csv.zip")
    download(CODEBOOK, "ucdp/ged261.pdf")
    with zipfile.ZipFile(z) as zf:
        name = [n for n in zf.namelist() if n.endswith(".csv")][0]
        df = pd.read_csv(io.BytesIO(zf.read(name)), low_memory=False)
    return name, df


def main():
    OUT.mkdir(exist_ok=True)
    name, ged = load_ged()
    ke = ged[ged["country"] == "Kenya"].copy()
    out = {"file": name, "global_rows": int(len(ged)), "global_year_range": [int(ged.year.min()), int(ged.year.max())],
           "kenya_events": int(len(ke)), "kenya_year_range": [int(ke.year.min()), int(ke.year.max())],
           "kenya_country_id_values": sorted(ke["country_id"].unique().tolist())}
    years = range(int(ged.year.min()), int(ged.year.max()) + 1)
    by_year = ke.groupby("year").size().reindex(years, fill_value=0)
    out["kenya_events_by_year"] = {int(k): int(v) for k, v in by_year.items()}
    out["kenya_best_deaths_by_year"] = {int(k): int(v) for k, v in
                                        ke.groupby("year")["best"].sum().reindex(years, fill_value=0).items()}
    out["kenya_years_with_zero_events"] = [int(y) for y, v in by_year.items() if v == 0]
    tv = ke.groupby(["year", "type_of_violence"]).size().unstack(fill_value=0).rename(columns=TYPES)
    out["kenya_events_by_year_type"] = {int(y): {k: int(v) for k, v in r.items()} for y, r in tv.iterrows()}
    out["kenya_events_by_type"] = {TYPES[k]: int(v) for k, v in ke["type_of_violence"].value_counts().items()}

    wp = ke["where_prec"].value_counts().sort_index()
    out["where_prec_counts"] = {int(k): int(v) for k, v in wp.items()}
    out["where_prec_share"] = {int(k): round(float(v / len(ke)), 4) for k, v in wp.items()}
    out["share_prec1_exact"] = round(float((ke.where_prec == 1).mean()), 4)
    out["share_prec1_2_within_25km"] = round(float((ke.where_prec <= 2).mean()), 4)
    out["share_prec1_3_adm2_or_better"] = round(float((ke.where_prec <= 3).mean()), 4)
    # by decade: precision may change over time
    ke["period"] = pd.cut(ke.year, [1988, 1999, 2009, 2019, 2030], labels=["1989-99", "2000-09", "2010-19", "2020+"])
    out["share_prec1_by_period"] = {str(k): round(float(v), 3) for k, v in
                                    ke.groupby("period", observed=True)["where_prec"].apply(lambda s: (s == 1).mean()).items()}
    out["events_by_period"] = {str(k): int(v) for k, v in ke["period"].value_counts().sort_index().items()}
    out["adm_2_sample_where_prec_3"] = ke.loc[ke.where_prec == 3, "adm_2"].value_counts().head(15).to_dict()
    out["event_clarity_counts"] = {int(k): int(v) for k, v in ke["event_clarity"].value_counts().items()}
    out["date_prec_counts"] = {int(k): int(v) for k, v in ke["date_prec"].value_counts().items()}

    # Spatial: exact events (where_prec 1) per ward / sub-county / county
    b = DATA / "boundaries"
    pts = gpd.GeoDataFrame(ke[["id", "year", "where_prec"]],
                           geometry=gpd.points_from_xy(ke.longitude, ke.latitude), crs=4326)
    for lvl, nm in [("ADM1", "counties"), ("ADM2", "subcounties"), ("ADM3", "wards")]:
        poly = gpd.read_file(b / f"geoBoundaries-KEN-{lvl}.geojson")[["shapeID", "geometry"]]
        j = gpd.sjoin(pts, poly, how="left", predicate="within").drop_duplicates("id")
        ok = j[j.where_prec == 1]
        out[f"{nm}_total"] = int(len(poly))
        out[f"{nm}_with_any_prec1_event"] = int(ok["shapeID"].nunique())
        out[f"{nm}_with_prec1_events_in_ge2_distinct_years"] = int((ok.groupby("shapeID")["year"].nunique() >= 2).sum())
        out[f"{nm}_with_prec1_events_in_ge2_distinct_years_after_2010"] = int(
            (ok[ok.year >= 2010].groupby("shapeID")["year"].nunique() >= 2).sum())
        out[f"events_outside_{nm}"] = int(j["shapeID"].isna().sum())
        if lvl == "ADM1":
            names = gpd.read_file(b / "geoBoundaries-KEN-ADM1.geojson")[["shapeID", "shapeName"]]
            county_prec1 = ok.merge(names, on="shapeID").groupby("shapeName")["year"].agg(["size", "nunique"])

    # Overlap with water: counties with >= 30 WPdx repeat-record points spanning >= 3 years
    wp = OUT / "01_wpdx_by_county.csv"
    if wp.exists():
        w = pd.read_csv(wp, index_col=0)
        sel = w[w["repeat_span_ge_3y"] >= 30]
        out["wpdx_counties_ge30_repeat3y_ucdp_prec1"] = {
            c: {"wpdx_repeat_span_ge_3y": int(sel.loc[c, "repeat_span_ge_3y"]),
                "ucdp_prec1_events": int(county_prec1["size"].get(c, 0)),
                "ucdp_prec1_distinct_years": int(county_prec1["nunique"].get(c, 0))} for c in sel.index}

    # Candidate (preliminary) events for 2026
    cand = {}
    for label, url in CANDIDATE.items():
        try:
            p, _ = download(url, "ucdp/" + url.rsplit("/", 1)[1])
            c = pd.read_csv(p, low_memory=False)
            ck = c[c["country"] == "Kenya"]
            cand[label] = {"rows_global": int(len(c)), "kenya_events": int(len(ck)),
                           "kenya_months": sorted(pd.to_datetime(ck["date_start"]).dt.strftime("%Y-%m").unique().tolist()),
                           "kenya_where_prec": {int(k): int(v) for k, v in ck["where_prec"].value_counts().sort_index().items()}}
        except Exception as e:  # report, don't hide
            cand[label] = {"error": str(e)}
    out["candidate_2026"] = cand

    write_json(out, "02a_ucdp.json")
    pd.Series(out["kenya_events_by_year"]).rename("ucdp_ged_261_events").to_csv(OUT / "02a_ucdp_kenya_by_year.csv")
    print(json.dumps({k: v for k, v in out.items() if k != "kenya_events_by_year_type"}, indent=1))


if __name__ == "__main__":
    main()
