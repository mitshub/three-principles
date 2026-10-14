"""Audit item 3: wealth / poverty, Kenya.

a) Relative Wealth Index (Meta / Chi et al.): downloads the Kenya file from
   the HDX 'relative-wealth-index' package, lists every Kenya resource in that
   package (to detect multiple vintages), and summarises the file. The paper's
   statement on the reference period is quoted in REPORT.md (arXiv 2104.07761,
   SM7 and Table S1).
b) Repeated-year candidates, checked by download (not by name):
   - OPHI Kenya MPI on HDX (kenya-mpi): units and years in each file.
   - DHS Program indicator API: subnational 'Population in the lowest wealth
     quintile' (HC_WIXQ_P_LOW) by survey and geographic level.
   - KNBS Kenya Poverty Reports 2021/2022 (PDF): HTTP check only.

Run: .venv/bin/python -I scripts/03_wealth.py   (after 05_boundaries.py)
"""
import json
import sys

import geopandas as gpd
import pandas as pd
import requests

sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import DATA, UA, download, now, write_json  # noqa: E402

HDX = "https://data.humdata.org/api/3/action/package_show?id="
DHS_API = "https://api.dhsprogram.com/rest/dhs/data"
KNBS_PDFS = {
    "Kenya Poverty Report 2021": "https://new.knbs.or.ke/wp-content/uploads/2023/09/The-Kenya-Poverty-Report-2021.pdf",
    "Kenya Poverty Report 2022": "https://www.knbs.or.ke/wp-content/uploads/2024/10/The-Kenya-Poverty-Report-2022.pdf",
}


def hdx(pkg):
    r = requests.get(HDX + pkg, headers=UA, timeout=60)
    r.raise_for_status()
    return r.json()["result"]


def rwi():
    pkg = hdx("relative-wealth-index")
    ken = [x for x in pkg["resources"] if "kenya" in x["name"].lower() or "ken_" in x["url"].lower()]
    out = {"hdx_package": "https://data.humdata.org/dataset/relative-wealth-index",
           "license_title": pkg.get("license_title"), "dataset_date": pkg.get("dataset_date"),
           "n_resources": len(pkg["resources"]),
           "kenya_resources": [{"name": x["name"], "created": x.get("created"),
                                "last_modified": x.get("last_modified"), "url": x["url"]} for x in ken]}
    p, _ = download(ken[0]["url"], "rwi/ken_relative_wealth_index.csv")
    d = pd.read_csv(p)
    out["file"] = p.name
    out["rows"] = int(len(d))
    out["columns"] = d.columns.tolist()
    out["date_or_year_column_present"] = any(c.lower() in ("year", "date", "time") for c in d.columns)
    out["rwi_summary"] = {k: round(float(v), 3) for k, v in d["rwi"].describe().items()}
    out["error_summary"] = {k: round(float(v), 3) for k, v in d["error"].describe().items()}
    pts = gpd.GeoDataFrame(d, geometry=gpd.points_from_xy(d.longitude, d.latitude), crs=4326)
    for lvl, nm in [("ADM1", "counties"), ("ADM2", "subcounties"), ("ADM3", "wards")]:
        poly = gpd.read_file(DATA / "boundaries" / f"geoBoundaries-KEN-{lvl}.geojson")[["shapeID", "geometry"]]
        j = gpd.sjoin(pts, poly, how="left", predicate="within")
        c = j.groupby("shapeID").size().reindex(poly["shapeID"], fill_value=0)
        out[f"{nm}_with_ge1_cell"] = int((c >= 1).sum())
        out[f"{nm}_total"] = int(len(poly))
        out[f"{nm}_cells_median"] = float(c.median())
    return out


def mpi():
    pkg = hdx("kenya-mpi")
    out = {"hdx_package": "https://data.humdata.org/dataset/kenya-mpi", "license_title": pkg.get("license_title"),
           "files": {}}
    for x in pkg["resources"]:
        p, _ = download(x["url"], "wealth/" + x["url"].rsplit("/", 1)[1])
        d = pd.read_csv(p)
        units = d["Admin 1 Name"].fillna("(national)")
        out["files"][x["name"]] = {
            "file": p.name, "rows": int(len(d)),
            "survey_periods": sorted((d["Survey"] + " " + d["Start Date"].str[:4]).unique().tolist()),
            "units_per_period": {k: int(v) for k, v in
                                 (d.assign(u=units).groupby(d["Start Date"].str[:4])["u"].nunique()).items()},
            "unit_names_sample": sorted(units.unique().tolist())[:15],
        }
    return out


def dhs():
    r = requests.get(DHS_API, params={"countryIds": "KE", "indicatorIds": "HC_WIXQ_P_LOW",
                                      "breakdown": "subnational", "f": "json", "perpage": 5000},
                     headers=UA, timeout=120)
    d = pd.DataFrame(r.json()["Data"])
    t = d.groupby(["SurveyId", "LevelRank"]).size().unstack(fill_value=0)
    return {"url": r.url, "accessed_utc": now(), "http_status": r.status_code,
            "indicator": d["Indicator"].iloc[0], "records": int(len(d)),
            "units_by_survey_and_level": {s: {str(k) or "blank": int(v) for k, v in row.items() if v} for s, row in t.iterrows()},
            "level2_label_sample": d.loc[d.LevelRank.astype(str) == "2", "CharacteristicLabel"].head(10).tolist()}


def knbs():
    out = {}
    for name, url in KNBS_PDFS.items():
        try:
            r = requests.head(url, headers=UA, timeout=60, allow_redirects=True)
            out[name] = {"url": url, "accessed_utc": now(), "http_status": r.status_code,
                         "content_type": r.headers.get("content-type"), "bytes": r.headers.get("content-length")}
        except requests.RequestException as e:
            out[name] = {"url": url, "error": str(e)}
    return out


def knbs_2022_tables():
    """Which geography and years do the 2022 report's poverty tables cover?"""
    import re
    import pypdf
    p, _ = download(KNBS_PDFS["Kenya Poverty Report 2022"], "wealth/The-Kenya-Poverty-Report-2022.pdf")
    pages = [re.sub(r"\s+", " ", pg.extract_text() or "") for pg in pypdf.PdfReader(p).pages]
    titles = sorted({m.group(0) for t in pages for m in re.finditer(
        r"Table 4\.\d+: [^.]{0,120}?(?:20\d\d(?:/\d\d)?)", t)})
    return {"file": p.name, "pages": len(pages), "table_titles_chapter4": titles}


def main():
    out = {"rwi": rwi(), "ophi_mpi": mpi(), "dhs_api_lowest_wealth_quintile": dhs(), "knbs_pdfs": knbs(), "knbs_2022_tables": knbs_2022_tables()}
    write_json(out, "03_wealth.json")
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
