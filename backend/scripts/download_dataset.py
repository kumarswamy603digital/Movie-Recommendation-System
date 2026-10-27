"""Reproducible MovieLens dataset download + integrity check.

Usage (from `backend/`):
    python -m scripts.download_dataset

Behaviour:
- Verifies the target folder already contains a valid dataset before hitting
  the network (idempotent).
- Downloads the official MovieLens zip from grouplens.org over HTTPS.
- Verifies the extracted folder contains the expected files.
- Prints a manifest describing what was acquired.

This script NEVER fabricates or replaces a failed download with synthetic
data. On failure it exits with a non-zero status and a clear message.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

# Add repo root so `app` is importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402


DATASET_URLS = {
    "ml-100k": "https://files.grouplens.org/datasets/movielens/ml-100k.zip",
    "ml-1m":   "https://files.grouplens.org/datasets/movielens/ml-1m.zip",
    "ml-25m":  "https://files.grouplens.org/datasets/movielens/ml-25m.zip",
}

# Files we require after extraction, per dataset version.
REQUIRED = {
    "ml-100k": ["u.data", "u.item", "u.genre"],
    "ml-1m":   ["ratings.dat", "movies.dat"],
    "ml-25m":  ["ratings.csv", "movies.csv"],
}


def _expected_dir() -> Path:
    return Path(settings.data_dir) / settings.movielens_dataset


def _verify_extracted(base: Path) -> list[str]:
    """Return list of missing filenames (empty if all present)."""
    return [f for f in REQUIRED[settings.movielens_dataset] if not (base / f).exists()]


def download(url: str, dst: Path) -> None:
    print(f"Downloading {url} -> {dst}")
    with urllib.request.urlopen(url, timeout=90) as r:
        data = r.read()
    dst.write_bytes(data)
    print(f"Downloaded {len(data):,} bytes.")


def extract(zip_path: Path, dst_dir: Path) -> None:
    print(f"Extracting {zip_path} -> {dst_dir.parent}")
    with zipfile.ZipFile(io.BytesIO(zip_path.read_bytes())) as z:
        z.extractall(dst_dir.parent)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default=None, choices=list(DATASET_URLS), help="Override dataset version.")
    ap.add_argument("--force", action="store_true", help="Re-download even if files exist.")
    args = ap.parse_args(argv)

    if args.dataset:
        settings.movielens_dataset = args.dataset

    base = _expected_dir()
    zip_path = Path(settings.data_dir) / (base.name + ".zip")

    if not args.force and base.exists() and not _verify_extracted(base):
        print(f"Dataset already present at {base} (integrity OK).")
    else:
        url = DATASET_URLS[settings.movielens_dataset]
        base.parent.mkdir(parents=True, exist_ok=True)
        try:
            download(url, zip_path)
            extract(zip_path, base)
        except Exception as exc:
            print(f"Download failed: {exc}", file=sys.stderr)
            print("NOT fabricating data. Fix the network or download manually and place files in:", file=sys.stderr)
            print(f"  {base}", file=sys.stderr)
            return 2

    missing = _verify_extracted(base)
    if missing:
        print(f"Missing files after extraction: {missing}", file=sys.stderr)
        return 3

    manifest = {
        "dataset": settings.movielens_dataset,
        "source_url": DATASET_URLS[settings.movielens_dataset],
        "local_dir": str(base),
        "files_present": [f for f in REQUIRED[settings.movielens_dataset] if (base / f).exists()],
        "attribution": "GroupLens Research. https://grouplens.org/datasets/movielens/",
    }
    (base / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
