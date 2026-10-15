"""Step 3: UCDP GED 26.1 precise events per ADM1/ADM2 unit, per WPdx+ country.

Country-level shares use the GED field `country` ("Name of the country in
which the event takes place", GED 26.1 codebook), mapped from ISO3 by the
explicit table UCDP_NAME below. Unit-level counts use a spatial join: every
GED event with where_prec == 1 (codebook: "exact location of the event known
and coded") dated YEAR_FROM-YEAR_TO is assigned to the geoBoundaries unit that
contains its coordinates, whatever its `country` value; mismatches are counted.

A unit qualifies on the violence side if it has >= MIN_EVENTS where_prec == 1
events in >= MIN_YEARS distinct years within YEAR_FROM-YEAR_TO.

Writes outputs/units/<ISO3>_<LEVEL>.csv (adds UCDP columns in place) and
outputs/03_ucdp.json.

Run:  .venv/bin/python -I scripts/03_ucdp.py   (after 02_boundaries_wpdx.py)
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
YEAR_FROM, YEAR_TO = 2010, 2025
MIN_EVENTS, MIN_YEARS = 3, 2
UCDP_NAME = {  # ISO3 (WPdx+ clean_country_id) -> GED `country` value, checked against the file
    "NGA": "Nigeria", "UGA": "Uganda", "SLE": "Sierra Leone", "LBR": "Liberia", "GHA": "Ghana",
    "ETH": "Ethiopia", "KEN": "Kenya", "BGD": "Bangladesh", "ZWE": "Zimbabwe (Rhodesia)",
    "TZA": "Tanzania", "IND": "India", "SWZ": "Kingdom of eSwatini (Swaziland)", "ZMB": "Zambia",
    "HTI": "Haiti", "RWA": "Rwanda", "SSD": "South Sudan", "CAF": "Central African Republic",
    "MWI": "Malawi", "GTM": "Guatemala",
}


def load_ged():
    z, _ = download(GED_ZIP, "ucdp/ged261-csv.zip")
    download(CODEBOOK, "ucdp/ged261.pdf")
    with zipfile.ZipFile(z) as zf:
        name = [n for n in zf.namelist() if n.endswith(".csv")][0]
        df = pd.read_csv(io.BytesIO(zf.read(name)), low_memory=False,
                         usecols=["id", "year", "country", "where_prec", "latitude", "longitude"])
    return name, df


def main():
    name, ged = load_ged()
    countries = json.loads((OUT / "01_wpdx_countries.json").read_text())["countries"]
    names_in_file = set(ged["country"].unique())
    win = ged[ged.year.between(YEAR_FROM, YEAR_TO)]
    p1 = win[win.where_prec == 1]
    pts = gpd.GeoDataFrame(p1, geometry=gpd.points_from_xy(p1.longitude, p1.latitude), crs=4326)
    res = {"file": name, "global_rows": int(len(ged)), "years": [YEAR_FROM, YEAR_TO],
           "min_events": MIN_EVENTS, "min_years": MIN_YEARS, "countries": {}}
    for c in countries:
        iso = c["iso3"]
        uname = UCDP_NAME[iso]
        k = win[win.country == uname]
        cres = {"ucdp_country": uname, "ucdp_country_in_file": uname in names_in_file,
                "events_window": int(len(k)), "events_window_prec1": int((k.where_prec == 1).sum()),
                "share_prec1_window": round(float((k.where_prec == 1).mean()), 4) if len(k) else None,
                "events_window_by_where_prec": {int(a): int(b) for a, b in k.where_prec.value_counts().sort_index().items()}}
        for lvl in ["ADM1", "ADM2"]:
            f = OUT / "units" / f"{iso}_{lvl}.csv"
            if not f.exists():
                continue
            u = pd.read_csv(f, index_col="shapeID").drop(columns=["ucdp_prec1_events", "ucdp_prec1_years"],
                                                          errors="ignore")
            g = gpd.read_file(DATA / "boundaries" / f"geoBoundaries-{iso}-{lvl}.geojson")[["shapeID", "geometry"]]
            j = gpd.sjoin(pts, g.to_crs(4326), how="inner", predicate="within")
            j = j[~j.index.duplicated()]
            agg = j.groupby("shapeID").agg(ucdp_prec1_events=("id", "size"), ucdp_prec1_years=("year", "nunique"))
            u = u.join(agg).fillna({"ucdp_prec1_events": 0, "ucdp_prec1_years": 0})
            u[["ucdp_prec1_events", "ucdp_prec1_years"]] = u[["ucdp_prec1_events", "ucdp_prec1_years"]].astype(int)
            u.to_csv(f)
            q = (u.ucdp_prec1_events >= MIN_EVENTS) & (u.ucdp_prec1_years >= MIN_YEARS)
            cres[lvl] = {"prec1_events_joined": int(len(j)),
                         "joined_events_with_other_ucdp_country": int((j.country != uname).sum()),
                         "units_with_any_prec1_event": int((u.ucdp_prec1_events > 0).sum()),
                         "units_qualifying_violence": int(q.sum())}
        res["countries"][iso] = cres
        print(iso, {k: v for k, v in cres.items() if k != "events_window_by_where_prec"})
    write_json(res, "03_ucdp.json")


if __name__ == "__main__":
    main()
