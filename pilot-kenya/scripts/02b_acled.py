"""Audit item 2b/2c: ACLED access for Kenya, and UCDP vs ACLED counts per year.

1. Probes the ACLED API without credentials and records the response. Does
   NOT register, log in, or use any key. Event-level data needs an account
   (HDX package notes: "To access full event data, please register").
2. Downloads ACLED's openly published Kenya aggregates (country-month counts)
   from HDX, which require no account, and sums them to country-year.
3. Compares with UCDP GED 26.1 Kenya events per year (from 02_ucdp.py).

Country-level only: the open ACLED files have no sub-national breakdown.
ACLED terms apply (non-commercial use, attribution; see REPORT.md).

Run: .venv/bin/python -I scripts/02b_acled.py   (after 02a_ucdp.py)
"""
import json
import sys

import pandas as pd
import requests

sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import OUT, UA, download, now, write_json  # noqa: E402

API_PROBE = "https://acleddata.com/api/acled/read?country=Kenya&limit=1"
HDX_PKG = "https://data.humdata.org/api/3/action/package_show?id=kenya-acled-conflict-data"


def main():
    out = {}
    r = requests.get(API_PROBE, headers=UA, timeout=60)
    out["api_probe"] = {"url": API_PROBE, "accessed_utc": now(), "http_status": r.status_code,
                        "body": r.text[:200]}

    pkg = requests.get(HDX_PKG, headers=UA, timeout=60).json()["result"]
    out["hdx_package"] = {"url": HDX_PKG, "accessed_utc": now(), "title": pkg["title"],
                          "license_title": pkg.get("license_title"), "license_other": pkg.get("license_other"),
                          "dataset_date": pkg.get("dataset_date"), "notes": pkg.get("notes")}
    series = {}
    for res in pkg["resources"]:
        p, _ = download(res["url"], "acled/" + res["url"].rsplit("/", 1)[1])
        d = pd.read_excel(p, sheet_name="Data")
        key = res["name"].replace("kenya_", "").replace("_by_month-year", "")
        months = pd.to_datetime(d["Month"] + " " + d["Year"].astype(str), format="%B %Y")
        series[key] = {"file": p.name, "rows": int(len(d)), "last_modified": res.get("last_modified"),
                       "first_month": months.min().strftime("%Y-%m"), "last_month": months.max().strftime("%Y-%m"),
                       "events_by_year": {int(k): int(v) for k, v in d.groupby("Year")["Events"].sum().items()}}
    out["acled_series"] = series

    ucdp = json.loads((OUT / "02a_ucdp.json").read_text())["kenya_events_by_year"]
    ucdp = pd.Series({int(k): v for k, v in ucdp.items()}, name="ucdp_ged_261")
    pv = pd.Series(series["political_violence_events_and_fatalities"]["events_by_year"], name="acled_political_violence")
    ct = pd.Series(series["civilian_targeting_events_and_fatalities"]["events_by_year"], name="acled_civilian_targeting")
    # Overlap: full calendar years in both (ACLED Kenya starts 1997; UCDP 26.1 ends 2025)
    yrs = range(max(pv.index.min(), ucdp.index.min()), min(2025, ucdp.index.max()) + 1)
    cmp_ = pd.concat([ucdp, pv, ct], axis=1).reindex(yrs)
    cmp_["ratio_acled_pv_to_ucdp"] = (cmp_["acled_political_violence"] / cmp_["ucdp_ged_261"]).round(1)
    cmp_.index.name = "year"
    cmp_.to_csv(OUT / "02b_ucdp_vs_acled_by_year.csv")
    out["comparison_years"] = [min(yrs), max(yrs)]
    out["comparison"] = {int(y): {k: (None if pd.isna(v) else float(v)) for k, v in r.items()} for y, r in cmp_.iterrows()}
    out["corr_pearson_yearly_counts"] = round(float(cmp_["ucdp_ged_261"].corr(cmp_["acled_political_violence"])), 3)
    out["corr_spearman_yearly_counts"] = round(float(cmp_["ucdp_ged_261"].rank().corr(cmp_["acled_political_violence"].rank())), 3)
    write_json(out, "02b_acled.json")
    print(json.dumps(out["api_probe"], indent=1))
    print({k: (v["first_month"], v["last_month"], v["rows"]) for k, v in series.items()})
    print(cmp_.to_string())
    print("pearson", out["corr_pearson_yearly_counts"], "spearman", out["corr_spearman_yearly_counts"])


if __name__ == "__main__":
    main()
