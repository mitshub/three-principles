"""Step 1: WPdx+ repeat-record statistics, per country.

Generalises pilot-kenya/scripts/01_wpdx.py (WPdx+ part only) to take a
country argument. Countries are defined by the WPdx+ field
`clean_country_id` (ISO3), with `clean_country_name` as the label. The
metadata description of clean_country_name is "Cleaned version of the country
name based on provided GPS coordinates." The raw field `country_name` is NOT
used for selection; a cross-tab of the two is saved for reference.

Per country this reports: points; history records; points with >=2 dated
records in water_point_history; points whose first-to-last span is >=3, >=5,
>=10 years; status_id transitions between consecutive records (all pairs and
pairs >=3 years apart); number of contributing sources and the top-3 share of
history records; and the status_clean check from the Kenya audit.

Writes outputs/wpdx/<ISO3>.json and outputs/wpdx/<ISO3>_points.csv (one row
per wpdx_id with coordinates, record count and span, used by step 2), and
outputs/01_wpdx_countries.json.

Run:  .venv/bin/python -I scripts/01_wpdx.py all
      .venv/bin/python -I scripts/01_wpdx.py KEN
"""
import json
import sys

import pandas as pd

sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import DATA, OUT, download, write_json  # noqa: E402

SOCRATA = "https://data.waterpointdata.org"
PLUS = "eqje-vguj"
COUNTRY_FIELD = "clean_country_id"
NAME_FIELD = "clean_country_name"
COLUMNS = ["wpdx_id", "lat_deg", "lon_deg", "report_date", "status_id", "status", "status_clean",
           "source", "water_point_history", "cluster_size", NAME_FIELD, COUNTRY_FIELD]
SPANS = [3, 5, 10]
GAP_YEARS = 3  # transitions are counted for consecutive record pairs at least this far apart


def soql(params):
    import requests
    from common import UA
    r = requests.get(f"{SOCRATA}/resource/{PLUS}.json", params=params, headers=UA, timeout=120)
    r.raise_for_status()
    return r.json()


def list_countries():
    meta_path, _ = download(f"{SOCRATA}/api/views/{PLUS}.json", f"wpdx/meta_{PLUS}.json")
    meta = json.loads(meta_path.read_text())
    cols = {c["fieldName"]: c.get("description") for c in meta["columns"]}
    rows = soql({"$select": f"{NAME_FIELD},{COUNTRY_FIELD},count(*) AS n",
                 "$group": f"{NAME_FIELD},{COUNTRY_FIELD}", "$order": "n DESC", "$limit": 1000})
    xtab = soql({"$select": f"country_name,{NAME_FIELD},count(*) AS n",
                 "$group": f"country_name,{NAME_FIELD}", "$order": "n DESC", "$limit": 5000})
    total = soql({"$select": "count(*) AS n"})[0]["n"]
    out = {"dataset": f"{SOCRATA}/d/{PLUS}", "dataset_name": meta["name"],
           "rows_updated_at": pd.to_datetime(meta.get("rowsUpdatedAt"), unit="s").isoformat(),
           "license_in_metadata": meta.get("license") or meta.get("licenseId"),
           "country_field_used": COUNTRY_FIELD, "label_field": NAME_FIELD,
           "field_descriptions": {k: cols.get(k) for k in (COUNTRY_FIELD, NAME_FIELD, "country_name",
                                                           "status_id", "status_clean", "water_point_history")},
           "total_rows": int(total),
           "countries": [{"iso3": r.get(COUNTRY_FIELD), "name": r.get(NAME_FIELD), "rows": int(r["n"])} for r in rows],
           "raw_country_name_vs_clean": [{"country_name": r.get("country_name"), NAME_FIELD: r.get(NAME_FIELD),
                                          "rows": int(r["n"])} for r in xtab]}
    write_json(out, "01_wpdx_countries.json")
    return out


def fetch(iso3):
    p, _ = download(f"{SOCRATA}/resource/{PLUS}.csv", f"wpdx/wpdx_plus_{iso3}.csv",
                    params={"$select": ",".join(COLUMNS), "$where": f"{COUNTRY_FIELD}='{iso3}'",
                            "$limit": 500000, "$order": ":id"})
    return pd.read_csv(p, low_memory=False)


def expand_history(plus):
    rows, bad = [], 0
    for wid, h in zip(plus["wpdx_id"], plus["water_point_history"]):
        if not isinstance(h, str):
            bad += 1
            continue
        for d, v in json.loads(h).items():
            rows.append((wid, d, v.get("source"), v.get("status_id")))
    long = pd.DataFrame(rows, columns=["wpdx_id", "date", "source", "status_id"])
    long["date"] = pd.to_datetime(long["date"])
    return long.sort_values(["wpdx_id", "date"]).reset_index(drop=True), bad


def repeat_stats(long):
    g = long.groupby("wpdx_id")["date"]
    per = pd.DataFrame({"n": g.size(), "first": g.min(), "last": g.max()})
    per["span_y"] = (per["last"] - per["first"]).dt.days / 365.25
    rep = per[per["n"] >= 2]
    return per, {"history_records": int(per["n"].sum()),
                 "points_with_ge2_records": int(len(rep)),
                 **{f"points_span_ge_{s}y": int((rep["span_y"] >= s).sum()) for s in SPANS}}


def transitions(long):
    x = long.sort_values(["wpdx_id", "date"])
    nxt = x.groupby("wpdx_id").shift(-1)
    pairs = pd.DataFrame({"from": x["status_id"], "to": nxt["status_id"],
                          "gap_y": (nxt["date"] - x["date"]).dt.days / 365.25}).dropna(subset=["to"])
    far = pairs[pairs["gap_y"] >= GAP_YEARS]
    ct = lambda d: {f"{a}->{b}": int(v) for (a, b), v in d.groupby(["from", "to"]).size().items()}  # noqa: E731
    return {"consecutive_pairs": int(len(pairs)), "pairs_by_from_to": ct(pairs),
            f"pairs_gap_ge_{GAP_YEARS}y": int(len(far)), f"pairs_by_from_to_gap_ge_{GAP_YEARS}y": ct(far),
            f"Yes->No_gap_ge_{GAP_YEARS}y": int(((far["from"] == "Yes") & (far["to"] == "No")).sum()),
            f"No->Yes_gap_ge_{GAP_YEARS}y": int(((far["from"] == "No") & (far["to"] == "Yes")).sum())}


def sources(long):
    s = long["source"].fillna("(missing)").value_counts()
    return {"n_sources": int(s.size), "top3_sources_share_of_records": round(float(s.head(3).sum() / s.sum()), 3),
            "top3_sources": {k: int(v) for k, v in s.head(3).items()},
            "records_by_year": {str(k): int(v) for k, v in long["date"].dt.year.value_counts().sort_index().items()}}


def status_checks(plus, long):
    raw_missing = plus["status"].isna()
    nf = plus["status_clean"] == "Non-Functional"
    return {"history_status_id_values": {str(k): int(v) for k, v in long["status_id"].value_counts(dropna=False).items()},
            "latest_rows_raw_status_missing": int(raw_missing.sum()),
            "latest_rows_raw_status_missing_and_status_clean_NonFunctional": int((raw_missing & nf).sum()),
            "latest_rows_status_clean_NonFunctional_and_status_id_Yes": int((nf & (plus["status_id"] == "Yes")).sum())}


def run(iso3):
    plus = fetch(iso3)
    long, bad = expand_history(plus)
    per, st = repeat_stats(long)
    yrs = per[(per.n >= 2) & (per.span_y >= 3)]
    out = {"iso3": iso3, "name": plus[NAME_FIELD].iloc[0], "rows": int(len(plus)),
           "unique_wpdx_id": int(plus["wpdx_id"].nunique()), "rows_without_history": bad,
           "points": int(len(per)), **st,
           "transitions_status_id": transitions(long), "sources": sources(long),
           "status_checks": status_checks(plus, long),
           "first_last_year_pairs_span_ge_3y_top5": {
               f"{a}->{b}": int(v) for (a, b), v in yrs.groupby([yrs["first"].dt.year, yrs["last"].dt.year])
               .size().sort_values(ascending=False).head(5).items()}}
    (OUT / "wpdx").mkdir(parents=True, exist_ok=True)
    write_json(out, f"wpdx/{iso3}.json")
    pts = plus.drop_duplicates("wpdx_id").set_index("wpdx_id")[["lat_deg", "lon_deg"]].join(per, how="inner")
    pts.to_csv(OUT / "wpdx" / f"{iso3}_points.csv")
    print(f"{iso3} points={out['points']} rep={out['points_with_ge2_records']} "
          f"ge3={out['points_span_ge_3y']} ge5={out['points_span_ge_5y']} ge10={out['points_span_ge_10y']}")
    return out


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    OUT.mkdir(exist_ok=True)
    countries = list_countries()
    codes = [c["iso3"] for c in countries["countries"]] if arg == "all" else [arg.upper()]
    for c in codes:
        run(c)


if __name__ == "__main__":
    main()
