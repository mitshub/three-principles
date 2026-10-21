"""Step 2: assign WPdx+ points to geoBoundaries ADM1/ADM2 units, per country.

Boundary set: geoBoundaries gbOpen, current release, levels ADM1 and ADM2
(where gbOpen has ADM2). Full-resolution GeoJSON, not the simplified files.
A point is assigned to the polygon that contains it ("within"); points in no
polygon are counted as outside.

Per unit: points, repeat points (>=2 dated records) and repeat points whose
first-to-last span is >= MIN_SPAN_YEARS. A unit qualifies on the water side if
it has >= MIN_REPEAT_POINTS such points.

Writes outputs/units/<ISO3>_<LEVEL>.csv (all units, zero rows included) and
outputs/02_boundaries_wpdx.json.

Run:  .venv/bin/python -I scripts/02_boundaries_wpdx.py   (after 01_wpdx.py)
"""
import json
import sys

import geopandas as gpd
import pandas as pd

sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import DATA, OUT, download, write_json  # noqa: E402

API = "https://www.geoboundaries.org/api/current/gbOpen/{iso}/{lvl}/"
LEVELS = ["ADM1", "ADM2"]
MIN_REPEAT_POINTS = 30
MIN_SPAN_YEARS = 3


def boundary(iso, lvl):
    """Return (GeoDataFrame, metadata) or (None, reason)."""
    try:
        mp, _ = download(API.format(iso=iso, lvl=lvl), f"boundaries/api_{iso}_{lvl}.json")
    except RuntimeError as e:
        return None, {"available": False, "reason": str(e)[:200]}
    m = json.loads(mp.read_text())
    if isinstance(m, list):
        m = m[0]
    gj, _ = download(m["gjDownloadURL"], f"boundaries/geoBoundaries-{iso}-{lvl}.geojson")
    g = gpd.read_file(gj)[["shapeName", "shapeID", "geometry"]]
    return g, {"available": True, "units": int(len(g)), "units_api": int(m["admUnitCount"]),
               "year_represented": m.get("boundaryYearRepresented"), "source": m.get("boundarySource"),
               "license": m.get("boundaryLicense"), "build_date": m.get("buildDate"),
               "download_url": m["gjDownloadURL"], "invalid_geometries": int((~g.geometry.is_valid).sum())}


def main():
    countries = json.loads((OUT / "01_wpdx_countries.json").read_text())["countries"]
    (OUT / "units").mkdir(parents=True, exist_ok=True)
    res = {"boundary_set": "geoBoundaries gbOpen (current)", "min_repeat_points": MIN_REPEAT_POINTS,
           "min_span_years": MIN_SPAN_YEARS, "countries": {}}
    for c in countries:
        iso = c["iso3"]
        p = pd.read_csv(OUT / "wpdx" / f"{iso}_points.csv")
        p["rep"] = p["n"] >= 2
        p["rep_span"] = p["rep"] & (p["span_y"] >= MIN_SPAN_YEARS)
        pts = gpd.GeoDataFrame(p, geometry=gpd.points_from_xy(p.lon_deg, p.lat_deg), crs=4326)
        cres = {}
        for lvl in LEVELS:
            g, meta = boundary(iso, lvl)
            cres[lvl] = meta
            if g is None:
                continue
            j = gpd.sjoin(pts, g.to_crs(4326), how="left", predicate="within")
            cres[lvl]["points_in_multiple_units"] = int(j.index.duplicated().sum())
            j = j[~j.index.duplicated()]
            cres[lvl]["points_outside_any_unit"] = int(j["shapeID"].isna().sum())
            cres[lvl]["repeat_span_points_outside_any_unit"] = int((j["shapeID"].isna() & j["rep_span"]).sum())
            u = j.groupby("shapeID").agg(points=("wpdx_id", "size"), repeat_points=("rep", "sum"),
                                         repeat_span_points=("rep_span", "sum"))
            u = g[["shapeID", "shapeName"]].set_index("shapeID").join(u).fillna(0)
            u[["points", "repeat_points", "repeat_span_points"]] = u[["points", "repeat_points",
                                                                     "repeat_span_points"]].astype(int)
            u.to_csv(OUT / "units" / f"{iso}_{lvl}.csv")
            cres[lvl]["units_with_any_point"] = int((u["points"] > 0).sum())
            cres[lvl]["units_qualifying_water"] = int((u["repeat_span_points"] >= MIN_REPEAT_POINTS).sum())
            print(f"{iso} {lvl} units={len(u)} with_points={cres[lvl]['units_with_any_point']} "
                  f"qualifying={cres[lvl]['units_qualifying_water']} outside={cres[lvl]['points_outside_any_unit']}")
        res["countries"][iso] = cres
    write_json(res, "02_boundaries_wpdx.json")


if __name__ == "__main__":
    main()
