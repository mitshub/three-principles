"""Step 4: overlap of water-side and violence-side qualifying units, per country.

A unit (ADM1 or ADM2, geoBoundaries gbOpen) is counted if it has BOTH
  >= MIN_REPEAT_POINTS WPdx+ points with >= 2 dated records spanning >= MIN_SPAN_YEARS
AND
  >= MIN_EVENTS UCDP GED 26.1 where_prec == 1 events in >= MIN_YEARS distinct years, YEAR_FROM-YEAR_TO.
Thresholds are imported from the step 2 and step 3 scripts so they stay in one place.

Writes outputs/04_overlap.csv, outputs/04_overlap_units.csv (every unit that
qualifies on either side) and outputs/04_overlap.json.

Run:  .venv/bin/python -I scripts/04_overlap.py   (after 03_ucdp.py)
"""
import importlib
import json
import sys

import geopandas as gpd
import pandas as pd

sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import DATA, OUT, write_json  # noqa: E402

s2 = importlib.import_module("02_boundaries_wpdx")
s3 = importlib.import_module("03_ucdp")
P = {"min_repeat_points": s2.MIN_REPEAT_POINTS, "min_span_years": s2.MIN_SPAN_YEARS,
     "min_events": s3.MIN_EVENTS, "min_years": s3.MIN_YEARS, "years": [s3.YEAR_FROM, s3.YEAR_TO]}


def unit_area(iso, lvl, shape_id):
    g = gpd.read_file(DATA / "boundaries" / f"geoBoundaries-{iso}-{lvl}.geojson")
    return round(float(g[g.shapeID == shape_id].to_crs("ESRI:54009").area.sum() / 1e6))  # Mollweide equal-area


def main():
    w = {c["iso3"]: json.loads((OUT / "wpdx" / f"{c['iso3']}.json").read_text())
         for c in json.loads((OUT / "01_wpdx_countries.json").read_text())["countries"]}
    uc = json.loads((OUT / "03_ucdp.json").read_text())["countries"]
    rows, units = [], []
    for iso, wc in w.items():
        r = {"iso3": iso, "country": wc["name"], "points": wc["points"],
             "repeat_points": wc["points_with_ge2_records"],
             f"repeat_span_ge_{P['min_span_years']}y": wc[f"points_span_ge_{P['min_span_years']}y"],
             "ucdp_events_window": uc[iso]["events_window"], "ucdp_share_prec1_window": uc[iso]["share_prec1_window"]}
        for lvl in ["ADM1", "ADM2"]:
            f = OUT / "units" / f"{iso}_{lvl}.csv"
            if not f.exists():
                r.update({f"{lvl}_units": None, f"{lvl}_water": None, f"{lvl}_violence": None, f"{lvl}_both": None})
                continue
            u = pd.read_csv(f)
            wq = u.repeat_span_points >= P["min_repeat_points"]
            vq = (u.ucdp_prec1_events >= P["min_events"]) & (u.ucdp_prec1_years >= P["min_years"])
            r.update({f"{lvl}_units": len(u), f"{lvl}_water": int(wq.sum()),
                      f"{lvl}_violence": int(vq.sum()), f"{lvl}_both": int((wq & vq).sum())})
            sel = u[wq | vq].assign(iso3=iso, level=lvl, water_ok=wq[wq | vq], violence_ok=vq[wq | vq])
            units.append(sel)
        rows.append(r)
    t = pd.DataFrame(rows).sort_values(["ADM2_both", "ADM1_both", "repeat_span_ge_3y"],
                                       ascending=False, na_position="last")
    t.to_csv(OUT / "04_overlap.csv", index=False)
    pd.concat(units).to_csv(OUT / "04_overlap_units.csv", index=False)
    both = pd.concat(units)
    both = both[both.water_ok & both.violence_ok].copy()
    both["area_km2"] = [unit_area(i, l, s) for i, l, s in zip(both.iso3, both.level, both.shapeID)]
    write_json({"thresholds": P, "table": t.to_dict("records"),
                "overlap_units": both.drop(columns=["water_ok", "violence_ok"]).to_dict("records")}, "04_overlap.json")
    print("thresholds:", P)
    print(t.to_string(index=False))
    print(both.to_string(index=False))


if __name__ == "__main__":
    main()
