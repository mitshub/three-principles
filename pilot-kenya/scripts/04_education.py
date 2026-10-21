"""Audit item 4: Kenya education data finer than county, more than one year.

Checks, by download (not by name):
- Uwezo learning assessments, Kenya 2014 and 2015 (HDX, household/school/
  village CSV). Reports rows, geography columns, number of districts and
  sub-locations, and how many district+sub-location pairs appear in both years.
  Variable meanings for test scores are NOT interpreted here: no codebook was
  found alongside the HDX files.
- Uwezo Kenya 2013 tables (HDX): aggregated tables; records unit per table.
- School lists: HDX 'kenya-education-0' (2005) and 'kenya-schools' (2010 MoE
  Google Sheet): columns, rows, whether enrolment/results fields exist.
- KCPE trends (Open Institute, 2013): HTTP check of the app link.
- openAFRICA CKAN search: HTTP check (was behind a browser challenge).

Run: .venv/bin/python -I scripts/04_education.py
"""
import io
import json
import sys
import zipfile

import pandas as pd
import requests

sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import DATA, UA, download, now, write_json  # noqa: E402

HDX = "https://data.humdata.org/api/3/action/package_show?id="
UWEZO = {"2014": "learning-levels-in-kenya-2014", "2015": "learning-levels-in-kenya-2015"}
UWEZO_2013 = "schooling-status-i-e-children-in-and-out-of-school"
SCHOOLS_2005 = "kenya-education-0"
SCHOOLS_2010_SHEET = ("https://docs.google.com/spreadsheets/d/1t8S_POnyZnSJWMtgutAdKYnhQXu4L6nS_XKPcryImso/"
                      "export?format=csv")
PROBES = {"kcpetrends_app": "http://apps.openinstitute.com/kcpetrends/",
          "openafrica_ckan_search": "https://open.africa/api/3/action/package_search?q=kenya%20kcpe"}
ENROL_WORDS = ("enrol", "enroll", "pupil", "student", "boys", "girls", "kcpe", "score", "mean")


def hdx(pkg):
    r = requests.get(HDX + pkg, headers=UA, timeout=60)
    r.raise_for_status()
    return r.json()["result"]


def read(p):
    return pd.read_csv(p, low_memory=False, encoding="latin1")


def uwezo():
    out = {}
    v = {}
    for year, pkg in UWEZO.items():
        meta = hdx(pkg)
        files = {}
        for x in meta["resources"]:
            p, _ = download(x["url"], "education/" + x["name"])
            d = read(p)
            files[x["name"]] = {"rows": int(len(d)), "n_columns": int(d.shape[1]),
                                "geo_columns": [c for c in d.columns if any(k in c.lower() for k in (
                                    "district", "county", "constituency", "division", "location", "village",
                                    "region", "eacode", "lat", "lon", "gps"))]}
            if x["name"].endswith("_hhld.csv"):
                files[x["name"]]["n_districts"] = int(d["id_district"].nunique())
                files[x["name"]]["n_village_ids"] = int(d["id_village"].nunique())
                files[x["name"]]["test_columns_present"] = [c for c in ("english", "swahili", "math") if c in d]
                files[x["name"]]["test_columns_nonnull"] = {c: int(d[c].notna().sum())
                                                           for c in ("english", "swahili", "math") if c in d}
            if x["name"].endswith("_village.csv"):
                sub = "sub_location" if "sub_location" in d else "location_sub_location"
                v[year] = set(zip(d["id_districtName"].astype(str).str.lower().str.strip(),
                                  d[sub].astype(str).str.lower().str.strip()))
                files[x["name"]]["n_district_names"] = int(d["id_districtName"].nunique())
        out[year] = {"hdx": f"https://data.humdata.org/dataset/{pkg}", "license": meta.get("license_title"),
                     "dataset_date": meta.get("dataset_date"), "files": files}
    out["district_sublocation_pairs_2014"] = len(v["2014"])
    out["district_sublocation_pairs_2015"] = len(v["2015"])
    out["district_sublocation_pairs_in_both"] = len(v["2014"] & v["2015"])
    out["note"] = ("id_village values are not stable across years (e.g. id 1 is in Gatanga in 2014; "
                   "ids in the 3000s are in Baringo in 2015), so overlap is matched on names.")
    return out


def uwezo_2013():
    meta = hdx(UWEZO_2013)
    names = [x["name"] for x in meta["resources"]]
    return {"hdx": f"https://data.humdata.org/dataset/{UWEZO_2013}", "license": meta.get("license_title"),
            "n_tables": len(names),
            "tables_by_district": [n for n in names if "district" in n.lower()],
            "tables_by_county": [n for n in names if "county" in n.lower() and "district" not in n.lower()]}


def school_lists():
    out = {}
    meta = hdx(SCHOOLS_2005)
    x = meta["resources"][0]
    p, _ = download(x["url"], "education/kenschools_2005.zip")
    with zipfile.ZipFile(p) as zf:
        dbf = [n for n in zf.namelist() if n.lower().endswith(".dbf")]
        import pyogrio
        tmp = DATA / "education" / "kenschools_2005"
        zf.extractall(tmp)
    shp = next(tmp.rglob("*.shp"))
    df = pyogrio.read_dataframe(shp, read_geometry=False)
    out["2005_ocha_cck"] = {"hdx": f"https://data.humdata.org/dataset/{SCHOOLS_2005}",
                            "license": meta.get("license_title"), "rows": int(len(df)),
                            "columns": df.columns.tolist(), "dbf_files": dbf,
                            "enrolment_or_results_like_columns": [c for c in df.columns
                                                                  if any(w in c.lower() for w in ENROL_WORDS)]}
    p, _ = download(SCHOOLS_2010_SHEET, "education/kenya_moe_schools_2010.csv")
    d = read(p)
    out["2010_moe_sheet"] = {"hdx": "https://data.humdata.org/dataset/kenya-schools",
                             "license": hdx("kenya-schools").get("license_title"), "rows": int(len(d)),
                             "columns": d.columns.tolist(),
                             "enrolment_or_results_like_columns": [c for c in d.columns
                                                                   if any(w in c.lower() for w in ENROL_WORDS)]}
    return out


def probes():
    out = {}
    for k, url in PROBES.items():
        try:
            r = requests.get(url, headers=UA, timeout=60)
            out[k] = {"url": url, "accessed_utc": now(), "http_status": r.status_code,
                      "browser_challenge": "Just a moment" in r.text[:2000], "body_start": r.text[:120]}
        except requests.RequestException as e:
            out[k] = {"url": url, "accessed_utc": now(), "error": type(e).__name__ + ": " + str(e)[:200]}
    return out


def main():
    out = {"uwezo_microdata": uwezo(), "uwezo_2013_tables": uwezo_2013(),
           "school_lists": school_lists(), "probes": probes()}
    write_json(out, "04_education.json")
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
