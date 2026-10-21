"""Audit item 5: Kenya administrative boundaries.

Downloads geoBoundaries gbOpen KEN ADM0-ADM3 (API metadata + GeoJSON) and
queries the HDX COD-AB Kenya package metadata. Reports units per level,
vintage, licence and source, and checks geometry validity.

Run: .venv/bin/python -I scripts/05_boundaries.py
"""
import json
import sys

import pyogrio
import requests

sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import DATA, UA, download, now, write_json  # noqa: E402

API = "https://www.geoboundaries.org/api/current/gbOpen/KEN/ALL/"
HDX = "https://data.humdata.org/api/3/action/package_show?id=cod-ab-ken"
IEBC_2012 = "https://www.iebc.or.ke/uploads/resources/9fIr43YjUT.pdf"


def main():
    meta_path, _ = download(API, "boundaries/geoboundaries_api_KEN_ALL.json")
    meta = json.loads(meta_path.read_text())
    out = {"geoboundaries_api": API, "levels": []}
    for m in meta:
        lvl = m["boundaryType"]
        gj, _ = download(m["gjDownloadURL"], f"boundaries/geoBoundaries-KEN-{lvl}.geojson")
        info = pyogrio.read_info(gj)
        names = pyogrio.read_dataframe(gj, read_geometry=False)["shapeName"]
        rec = {
            "level": lvl,
            "canonical_name": m.get("boundaryCanonical"),
            "units_api": int(m["admUnitCount"]),
            "features_in_file": int(info["features"]),
            "year_represented": m.get("boundaryYearRepresented"),
            "source": m.get("boundarySource"),
            "license": m.get("boundaryLicense"),
            "license_source": m.get("licenseSource"),
            "source_data_update": m.get("sourceDataUpdateDate"),
            "build_date": m.get("buildDate"),
            "download_url": m["gjDownloadURL"],
            "file": gj.name,
        }
        rec["distinct_shapeName"] = int(names.nunique())
        out["levels"].append(rec)

    # Coverage check: does each level tile the national outline?
    import geopandas as gpd
    gdfs = {lv["level"]: gpd.read_file(DATA / "boundaries" / lv["file"]).to_crs("ESRI:102022")
            for lv in out["levels"]}  # Africa Albers equal-area
    a0 = gdfs["ADM0"].geometry.area.sum()
    for lv in out["levels"]:
        g = gdfs[lv["level"]]
        lv["area_share_of_adm0"] = round(float(g.geometry.area.sum() / a0), 4)
        lv["invalid_geometries"] = int((~g.geometry.is_valid).sum())
        lv["duplicate_shapeName"] = int(g["shapeName"].duplicated().sum())

    # HDX COD-AB (official common operational dataset) metadata only.
    try:
        r = requests.get(HDX, headers=UA, timeout=60)
        out["hdx_cod_ab"] = {"url": HDX, "accessed_utc": now(), "http_status": r.status_code}
        if r.ok:
            res = r.json()["result"]
            out["hdx_cod_ab"].update({
                "title": res.get("title"),
                "license": res.get("license_title"),
                "dataset_date": res.get("dataset_date"),
                "last_modified": res.get("last_modified") or res.get("metadata_modified"),
                "source": res.get("dataset_source"),
                "resources": [{"name": x.get("name"), "format": x.get("format"),
                               "url": x.get("url"), "last_modified": x.get("last_modified")}
                              for x in res.get("resources", [])],
                "notes": (res.get("notes") or "")[:1500],
            })
    except requests.RequestException as e:
        out["hdx_cod_ab"] = {"url": HDX, "error": str(e)}

    # IEBC First Review final report (2012): source of the constituency/ward layout.
    import re
    import pypdf
    p, _ = download(IEBC_2012, "boundaries/iebc_first_review_2012.pdf")
    txt = re.sub(r"\s+", " ", " ".join((pg.extract_text() or "") for pg in pypdf.PdfReader(p).pages))
    out["iebc_first_review_2012"] = {
        "url": IEBC_2012, "title_start": txt[:160],
        "mentions": {k: [txt[max(0, m.start() - 120):m.end() + 80] for m in re.finditer(k, txt)][:2]
                     for k in ("cap of 1,450", "290 CONST")}}

    write_json(out, "05_boundaries.json")
    for lv in out["levels"]:
        print(f"{lv['level']:5} {lv['canonical_name']:<14} units={lv['units_api']:>5} area_share={lv['area_share_of_adm0']} invalid={lv['invalid_geometries']} dupnames={lv['duplicate_shapeName']} "
              f"file={lv['features_in_file']:>5} year={lv['year_represented']} "
              f"licence={lv['license']} source={lv['source']}")
    h = out.get("hdx_cod_ab", {})
    print("HDX COD-AB:", h.get("http_status"), h.get("title"), h.get("license"), h.get("dataset_date"))
    for x in h.get("resources", []):
        print("   ", x["name"], x["format"], x["last_modified"])


if __name__ == "__main__":
    main()
