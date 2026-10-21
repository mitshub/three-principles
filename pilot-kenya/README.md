# Kenya small-area pilot: data-availability audit

An audit only, with no substantive analysis. The findings are in [REPORT.md](REPORT.md).

## Layout

```
pilot-kenya/
  REPORT.md            findings (committed)
  README.md            this file (committed)
  requirements.txt     pinned Python packages (committed)
  run_all.sh           runs every script in order (committed)
  scripts/             one script per audit item (committed)
    common.py          download + provenance logging helpers
    01_wpdx.py         item 1  water points (WPdx+ and WPdx-Basic)
    02a_ucdp.py        item 2  UCDP GED 26.1 (+ 2026 candidate events)
    02b_acled.py       item 2  ACLED access check; UCDP vs ACLED per year
    03_wealth.py       item 3  Relative Wealth Index; repeated wealth series
    04_education.py    item 4  education data finer than county
    05_boundaries.py   item 5  administrative boundaries
  data/                raw downloads + manifest.jsonl     (git-ignored)
  outputs/             JSON/CSV results + per-script logs (git-ignored)
  .venv/               virtual environment                (git-ignored)
```

## Reproduce from a clean checkout

Tested with **Python 3.9.6** (macOS system Python, `/usr/bin/python3`) on 2026-10-14.

```bash
git checkout pilot-kenya-audit
cd pilot-kenya
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./run_all.sh
```

`run_all.sh` runs the scripts in dependency order:
`05_boundaries` → `01_wpdx` → `02a_ucdp` → `02b_acled` → `03_wealth` → `04_education`.
Each script can also be run alone, for example `.venv/bin/python -I scripts/01_wpdx.py`,
once the scripts it depends on have run (each docstring names them).

- All downloads are public and need no account or API key. No credentials are used or stored.
- Every download is appended to `data/manifest.jsonl` with the URL, UTC access time, HTTP status, byte size and SHA-256.
- Re-runs reuse files already in `data/`. To refresh, delete `data/` first.
- Total download is about 320 MB. The largest items are the Uwezo household files (157 MB), the two WPdx extracts (59 MB) and the UCDP global CSV zip (39 MB).

**The results can drift.** WPdx is a live Socrata dataset (`rowsUpdatedAt` was
2026-10-14 when we accessed it), and the ACLED/HDX aggregates are refreshed weekly.
A later run may give slightly different WPdx and ACLED numbers. UCDP GED 26.1,
the RWI file, the Uwezo files and geoBoundaries (pinned to commit `9469f09`) are fixed releases.
