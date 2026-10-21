"""Shared helpers: download with provenance logging.

Every download is recorded in data/manifest.jsonl (git-ignored) with URL,
UTC access time, HTTP status, file name, byte size and SHA-256, so the
report can cite exactly what was read.
"""
import datetime
import hashlib
import json
import pathlib
import sys
import time

import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs"
MANIFEST = DATA / "manifest.jsonl"
UA = {"User-Agent": "three-principles-pilot-screening/1.0 (research; data availability screening)"}


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url, dest, params=None, force=False, timeout=600):
    """Download url to dest (relative to data/). Returns (path, record).

    Skips the network if the file exists and force is False; the manifest
    keeps the original access record in that case.
    """
    dest = DATA / dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not force:
        return dest, None
    for attempt in range(4):  # retry transient connection errors only (not HTTP errors)
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout, stream=True)
            break
        except requests.ConnectionError:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))
    # Record the requested URL; strip query strings from redirects (signed
    # storage URLs carry temporary tokens that must not be logged).
    final = r.url.split("?", 1)[0] if r.history else r.url
    rec = {"url": requests.Request("GET", url, params=params).prepare().url, "final_url": final,
           "accessed_utc": now(), "http_status": r.status_code, "file": str(dest.relative_to(ROOT))}
    if r.status_code != 200:
        rec["error"] = r.text[:500]
        log(rec)
        raise RuntimeError(f"HTTP {r.status_code} for {r.url}: {r.text[:200]}")
    with open(dest, "wb") as f:
        for chunk in r.iter_content(1 << 20):
            f.write(chunk)
    rec["bytes"] = dest.stat().st_size
    rec["sha256"] = sha256(dest)
    log(rec)
    return dest, rec


def log(rec):
    DATA.mkdir(exist_ok=True)
    with open(MANIFEST, "a") as f:
        f.write(json.dumps(rec) + "\n")


def write_json(obj, name):
    OUT.mkdir(exist_ok=True)
    p = OUT / name
    p.write_text(json.dumps(obj, indent=2, default=str, ensure_ascii=False))
    print(f"wrote {p.relative_to(ROOT)}", file=sys.stderr)
    return p
