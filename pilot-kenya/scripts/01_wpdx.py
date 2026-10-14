"""Audit item 1: WPdx water points, Kenya.

Primary linkage: WPdx+ (Socrata eqje-vguj). One row per water point
(wpdx_id); earlier visits of the same point are listed in the JSON column
water_point_history, keyed by report date. We expand that history into one
row per (wpdx_id, report date) and compute repeat-record statistics.

Sensitivity check: WPdx-Basic (jfkt-jmqa) holds every uploaded record but has
no wpdx_id. We link its records by spatial proximity (connected components of
records within r metres) as a rough bound, not a validated linkage.

Run: .venv/bin/python -I scripts/01_wpdx.py
Requires: scripts/05_boundaries.py to have been run (for county joins).
"""
import json
import sys

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import DATA, OUT, download, write_json  # noqa: E402

SOCRATA = "https://data.waterpointdata.org"
PLUS, BASIC = "eqje-vguj", "jfkt-jmqa"
WHERE = {"$where": "clean_country_name='Kenya'", "$limit": 200000, "$order": ":id"}
SPANS = [3, 5, 10]
MIN_POINTS = 30   # county is "analysable" if it has >= this many repeat-record points
PROX_RADII = [3, 10, 30]
SCHEMA_FIELDS = ["wpdx_id", "lat_deg", "lon_deg", "report_date", "status_id", "status",
                 "status_clean", "water_point_history", "cluster_size", "is_latest",
                 "activity_id", "location_id", "source", "clean_adm1", "clean_adm2", "clean_adm3"]
EQUAL_AREA = "ESRI:102022"  # Africa Albers Equal Area Conic (metres)


def fetch():
    meta = {}
    for ds, name in [(PLUS, "wpdx_plus_kenya.csv"), (BASIC, "wpdx_basic_kenya.csv")]:
        download(f"{SOCRATA}/resource/{ds}.csv", f"wpdx/{name}", params=WHERE)
        mp, _ = download(f"{SOCRATA}/api/views/{ds}.json", f"wpdx/meta_{ds}.json")
        meta[ds] = json.loads(mp.read_text())
    plus = pd.read_csv(DATA / "wpdx/wpdx_plus_kenya.csv", low_memory=False)
    basic = pd.read_csv(DATA / "wpdx/wpdx_basic_kenya.csv", low_memory=False)
    return plus, basic, meta


def schema(meta):
    out = {}
    for ds, m in meta.items():
        cols = {c["fieldName"]: c for c in m["columns"]}
        out[ds] = {
            "name": m["name"],
            "row_label": m.get("metadata", {}).get("rowLabel"),
            "rows_updated_at": pd.to_datetime(m.get("rowsUpdatedAt"), unit="s").isoformat(),
            "license_in_metadata": m.get("license") or m.get("licenseId"),
            "n_columns": len(cols),
            "fields": {f: cols[f].get("description") for f in SCHEMA_FIELDS if f in cols},
            "missing_fields": [f for f in SCHEMA_FIELDS if f not in cols],
        }
    return out


def expand_history(plus):
    rows = []
    for wid, h in zip(plus["wpdx_id"], plus["water_point_history"]):
        for d, v in json.loads(h).items():
            rows.append((wid, d, v.get("source"), v.get("status_id")))
    long = pd.DataFrame(rows, columns=["wpdx_id", "date", "source", "status_id"])
    long["date"] = pd.to_datetime(long["date"])
    return long.sort_values(["wpdx_id", "date"]).reset_index(drop=True)


def repeat_stats(long, key):
    g = long.groupby(key)["date"]
    per = pd.DataFrame({"n": g.size(), "first": g.min(), "last": g.max()})
    per["span_y"] = (per["last"] - per["first"]).dt.days / 365.25
    rep = per[per["n"] >= 2]
    q = rep["span_y"].quantile([0, .1, .25, .5, .75, .9, 1]).round(2)
    bins = [-0.001, 0.5, 1, 2, 3, 5, 10, 100]
    labels = ["<0.5", "0.5-1", "1-2", "2-3", "3-5", "5-10", ">=10"]
    hist = pd.cut(rep["span_y"], bins=bins, labels=labels, right=False).value_counts().reindex(labels)
    return per, {
        "points": int(len(per)),
        "records": int(per["n"].sum()),
        "points_with_ge2_records": int(len(rep)),
        "records_per_point": {str(k): int(v) for k, v in per["n"].clip(upper=5).value_counts().sort_index().items()},
        "span_years_quantiles_among_repeat": {str(k): float(v) for k, v in q.items()},
        "span_years_histogram_among_repeat": {k: int(v) for k, v in hist.items()},
        **{f"points_span_ge_{s}y": int((rep["span_y"] >= s).sum()) for s in SPANS},
    }


def transitions(long, key):
    x = long.sort_values([key, "date"]).copy()
    nxt = x.groupby(key).shift(-1)
    pairs = pd.DataFrame({key: x[key], "from": x["status_id"], "to": nxt["status_id"],
                          "src_from": x["source"], "src_to": nxt["source"],
                          "gap_y": (nxt["date"] - x["date"]).dt.days / 365.25}).dropna(subset=["to"])
    pairs["same_source"] = pairs["src_from"] == pairs["src_to"]
    ct = pairs.groupby(["from", "to"]).size()
    res = {
        "consecutive_pairs": int(len(pairs)),
        "pairs_by_from_to": {f"{a}->{b}": int(v) for (a, b), v in ct.items()},
        "pairs_same_source": int(pairs["same_source"].sum()),
        "pairs_cross_source": int((~pairs["same_source"]).sum()),
    }
    for label, sub in [("same_source", pairs[pairs["same_source"]]),
                       ("cross_source", pairs[~pairs["same_source"]]),
                       ("gap_ge_3y", pairs[pairs["gap_y"] >= 3])]:
        c = sub.groupby(["from", "to"]).size()
        res[f"pairs_by_from_to_{label}"] = {f"{a}->{b}": int(v) for (a, b), v in c.items()}
    res["points_with_any_Yes->No"] = int(pairs.loc[(pairs["from"] == "Yes") & (pairs["to"] == "No"), key].nunique())
    res["points_with_any_No->Yes"] = int(pairs.loc[(pairs["from"] == "No") & (pairs["to"] == "Yes"), key].nunique())
    return res


def spatial(plus, per):
    b = DATA / "boundaries"
    pts = gpd.GeoDataFrame(plus[["wpdx_id"]], geometry=gpd.points_from_xy(plus.lon_deg, plus.lat_deg), crs=4326)
    for lvl in ["ADM1", "ADM2", "ADM3"]:
        poly = gpd.read_file(b / f"geoBoundaries-KEN-{lvl}.geojson")[["shapeName", "shapeID", "geometry"]]
        j = gpd.sjoin(pts, poly, how="left", predicate="within").drop_duplicates("wpdx_id")
        pts[f"{lvl}_name"] = j["shapeName"].values
        pts[f"{lvl}_id"] = j["shapeID"].values
    df = pd.DataFrame(pts.drop(columns="geometry")).merge(per, left_on="wpdx_id", right_index=True)
    df["rep"] = df["n"] >= 2
    for s in SPANS:
        df[f"rep_{s}y"] = df["rep"] & (df["span_y"] >= s)
    agg = {"points": ("wpdx_id", "size"), "records": ("n", "sum"), "repeat_points": ("rep", "sum"),
           **{f"repeat_span_ge_{s}y": (f"rep_{s}y", "sum") for s in SPANS}}
    all_counties = gpd.read_file(b / "geoBoundaries-KEN-ADM1.geojson")["shapeName"]
    county = df.groupby("ADM1_name").agg(**agg).reindex(all_counties).fillna(0).astype(int)
    county = county.sort_values("records", ascending=False)
    county.to_csv(OUT / "01_wpdx_by_county.csv")
    res = {"points_outside_any_county": int(df["ADM1_name"].isna().sum()),
           "counties_total": int(len(county)),
           "counties_with_zero_records": int((county["records"] == 0).sum()),
           "threshold_repeat_points": MIN_POINTS,
           "by_county": county.reset_index().rename(columns={"index": "county"}).to_dict("records")}
    for col in ["repeat_points"] + [f"repeat_span_ge_{s}y" for s in SPANS]:
        res[f"counties_below_threshold_{col}"] = int((county[col] < MIN_POINTS).sum())
        res[f"counties_at_or_above_threshold_{col}"] = sorted(county.index[county[col] >= MIN_POINTS].tolist())
    for lvl, name in [("ADM2", "subcounties"), ("ADM3", "wards")]:
        u = df.groupby(f"{lvl}_id").agg(**agg)
        res[f"{name}_with_any_record"] = int(len(u))
        for col in ["repeat_points"] + [f"repeat_span_ge_{s}y" for s in SPANS]:
            res[f"{name}_at_or_above_threshold_{col}"] = int((u[col] >= MIN_POINTS).sum())
    top5 = county["repeat_points"].nlargest(5)
    res["top5_counties_share_of_repeat_points"] = round(float(top5.sum() / max(county["repeat_points"].sum(), 1)), 3)
    return res


def bias(plus, long):
    by_src = long["source"].value_counts()
    rep_ids = long.groupby("wpdx_id").size()
    rep_ids = rep_ids[rep_ids >= 2].index
    combos = (long[long["wpdx_id"].isin(rep_ids)].groupby("wpdx_id")["source"]
              .agg(lambda s: " + ".join(sorted(set(s)))).value_counts())
    return {
        "records_by_source_top10": {k: int(v) for k, v in by_src.head(10).items()},
        "n_sources": int(by_src.size),
        "top3_sources_share_of_records": round(float(by_src.head(3).sum() / by_src.sum()), 3),
        "records_by_year": {str(k): int(v) for k, v in long["date"].dt.year.value_counts().sort_index().items()},
        "repeat_points_by_source_combination_top10": {k: int(v) for k, v in combos.head(10).items()},
        "latest_status_id": {k: int(v) for k, v in plus["status_id"].value_counts(dropna=False).items()},
        "latest_status_clean_by_raw_status_missing": {
            f"{c}|raw_status_missing={m}": int(v)
            for (c, m), v in plus.groupby([plus["status_clean"].fillna("NA"), plus["status"].isna()]).size().items()},
        "records_by_dataset_title_top10": {k: int(v) for k, v in plus["dataset_title"].value_counts().head(10).items()},
    }


def gain_dates(plus, per):
    """Appendix B defines the water 'gain' as a new or repaired point, so check
    how many repeat-record points carry an install or rehab year (latest row)."""
    df = plus[["wpdx_id", "install_year", "rehab_year"]].merge(per, left_on="wpdx_id", right_index=True)
    df["has_gain_year"] = df["install_year"].notna() | df["rehab_year"].notna()
    out = {"all_points_with_install_year": int(df["install_year"].notna().sum()),
           "all_points_with_rehab_year": int(df["rehab_year"].notna().sum())}
    for label, m in [("repeat", df["n"] >= 2)] + [(f"repeat_span_ge_{s}y", (df["n"] >= 2) & (df["span_y"] >= s))
                                                  for s in SPANS]:
        sub = df[m]
        gy = sub[["install_year", "rehab_year"]].max(axis=1)
        out[label] = {"points": int(len(sub)), "with_install_or_rehab_year": int(sub["has_gain_year"].sum()),
                      "gain_year_le_first_record_year": int((gy <= sub["first"].dt.year).sum())}
    return out


def proximity_linkage(basic):
    """Union-find over WPdx-Basic records within r metres (any date)."""
    g = gpd.GeoDataFrame(basic[["source", "report_date", "status_id"]].reset_index(drop=True),
                         geometry=gpd.points_from_xy(basic.lon_deg, basic.lat_deg), crs=4326).to_crs(EQUAL_AREA)
    g["date"] = pd.to_datetime(g["report_date"].str[:10])
    res = {"records": int(len(g)), "note": "connected components; chaining possible; not a validated linkage"}
    for r in PROX_RADII:
        j = gpd.sjoin(g[["geometry"]], g[["geometry"]], predicate="dwithin", distance=r)
        parent = np.arange(len(g))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        for a, b in zip(j.index.values, j["index_right"].values):
            if a != b:
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[ra] = rb
        g["cl"] = [find(i) for i in range(len(g))]
        # one record per (cluster, day), as WPdx+ history is keyed by date
        long = g.drop_duplicates(["cl", "date"])[["cl", "date", "status_id", "source"]]
        _, st = repeat_stats(long, "cl")
        tr = transitions(long, "cl")
        res[f"r{r}m"] = {**st, "transitions": {k: v for k, v in tr.items()
                                               if k in ("consecutive_pairs", "pairs_by_from_to")}}
    return res


def main():
    OUT.mkdir(exist_ok=True)
    plus, basic, meta = fetch()
    long = expand_history(plus)
    per, st = repeat_stats(long, "wpdx_id")
    out = {
        "schema": schema(meta),
        "counts": {"wpdx_plus_kenya_rows": int(len(plus)),
                   "wpdx_plus_is_latest_true": int(plus["is_latest"].sum()),
                   "wpdx_plus_unique_wpdx_id": int(plus["wpdx_id"].nunique()),
                   "wpdx_basic_kenya_rows": int(len(basic)),
                   "history_entries_total": int(len(long)),
                   "history_len_equals_cluster_size_share": round(float(
                       (plus["water_point_history"].map(lambda h: len(json.loads(h))) == plus["cluster_size"]).mean()), 4)},
        "repeat_wpdx_plus": st,
        "transitions_wpdx_plus": transitions(long, "wpdx_id"),
        "spatial_wpdx_plus": spatial(plus, per),
        "gain_dates_wpdx_plus": gain_dates(plus, per),
        "first_last_year_pairs_span_ge_3y_top10": {
            f"{a}->{b}": int(v) for (a, b), v in
            per[(per.n >= 2) & (per.span_y >= 3)].groupby([per["first"].dt.year, per["last"].dt.year])
            .size().sort_values(ascending=False).head(10).items()},
        "bias": bias(plus, long),
        "sensitivity_basic_proximity": proximity_linkage(basic),
    }
    write_json(out, "01_wpdx.json")
    s = out["repeat_wpdx_plus"]
    print(json.dumps({k: out[k] for k in ["counts"]}, indent=1))
    print(json.dumps(s, indent=1))
    print(json.dumps(out["transitions_wpdx_plus"], indent=1))


if __name__ == "__main__":
    main()
