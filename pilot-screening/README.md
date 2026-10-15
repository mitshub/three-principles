# Cross-country screening: water-point repeat records × precise violence events

This is a screening only, with no substantive analysis. The findings are in [REPORT.md](REPORT.md).
It follows on from `pilot-kenya/` (branch `pilot-kenya-audit`).

## Layout

```
pilot-screening/
  REPORT.md               findings (committed)
  README.md               this file (committed)
  requirements.txt        pinned Python packages, same as pilot-kenya (committed)
  run_all.sh              runs every step in order (committed)
  scripts/                one script per step (committed)
    common.py             download + provenance logging (manifest), retries on connection errors
    01_wpdx.py            step 1  WPdx+ repeat-record statistics per country  (arg: ISO3 or "all")
    02_boundaries_wpdx.py step 2  geoBoundaries ADM1/ADM2; WPdx+ points per unit
    03_ucdp.py            step 3  UCDP GED 26.1 where_prec=1 events per unit; precision shares
    04_overlap.py         step 4  units qualifying on both sides; ranked table
  data/                   raw downloads + manifest.jsonl     (git-ignored)
  outputs/                JSON/CSV results + logs            (git-ignored)
  .venv/                  virtual environment                (git-ignored)
```

## Reproduce

Tested with **Python 3.9.6** (macOS system Python, `/usr/bin/python3`) on 2026-10-15.

```bash
git checkout pilot-screening
cd pilot-screening
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./run_all.sh
```

To run one country through step 1 only: `.venv/bin/python -I scripts/01_wpdx.py KEN`.
Steps 2–4 read the outputs of step 1 for every country listed in `outputs/01_wpdx_countries.json`.

**Thresholds** are module constants:
- `MIN_REPEAT_POINTS`, `MIN_SPAN_YEARS` in `scripts/02_boundaries_wpdx.py`
- `MIN_EVENTS`, `MIN_YEARS`, `YEAR_FROM`, `YEAR_TO` in `scripts/03_ucdp.py`

`04_overlap.py` imports them from those two scripts. After changing a threshold, re-run steps 2–4.

- All downloads are public and need no account or API key. No credentials are used or stored.
- Every download is appended to `data/manifest.jsonl` with the URL, UTC access time, HTTP status, byte size and SHA-256.
- Re-runs reuse files already in `data/`. To refresh, delete `data/` first.
- Total download is about 564 MB:
  - 19 WPdx+ country extracts: 194 MB
  - 38 geoBoundaries GeoJSON files: 329 MB
  - UCDP GED zip: 39 MB

**The results can drift.** WPdx+ is a live Socrata dataset; its `rowsUpdatedAt`
was 2026-10-15T06:05:19 when we accessed it. UCDP GED 26.1 is a fixed release.
The geoBoundaries "current" API pointed to commit `9469f09`. If that commit changes, the boundaries change too.
