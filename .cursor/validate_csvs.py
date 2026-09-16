#!/usr/bin/env python3
"""Validate and summarize the Rukn-Eg WordPress content-import CSVs.

For every ``rukn-eltatawer-egypt-*.csv`` in the repo root this reports the
detected encoding, the true row count (fields contain embedded newlines/HTML),
missing required columns, and completeness of the Rank Math SEO fields. It
exits non-zero if any file is unreadable or missing a required column, so it
doubles as a lightweight data-quality gate.
"""
from __future__ import annotations

import glob
import os
import sys

import chardet
import pandas as pd
from tabulate import tabulate

REQUIRED_COLUMNS = [
    "post_type",
    "post_status",
    "categories",
    "post_title",
    "post_name",
    "rank_math_title",
    "rank_math_description",
    "post_content",
]


def detect_encoding(path: str) -> str:
    with open(path, "rb") as fh:
        raw = fh.read(200_000)
    guess = chardet.detect(raw)
    return guess.get("encoding") or "unknown"


def main() -> int:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = sorted(glob.glob(os.path.join(repo_root, "rukn-eltatawer-egypt-*.csv")))
    if not paths:
        print("No content CSVs found.", file=sys.stderr)
        return 1

    rows = []
    ok = True
    for path in paths:
        name = os.path.basename(path)
        encoding = detect_encoding(path)
        try:
            df = pd.read_csv(path, dtype=str, keep_default_na=False)
        except Exception as exc:  # noqa: BLE001
            print(f"FAILED to parse {name}: {exc}", file=sys.stderr)
            ok = False
            continue

        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            ok = False

        seo_title_filled = (df["rank_math_title"].str.strip() != "").mean() * 100 if "rank_math_title" in df else 0
        seo_desc_filled = (df["rank_math_description"].str.strip() != "").mean() * 100 if "rank_math_description" in df else 0

        rows.append([
            name,
            f"{len(df):,}",
            len(df.columns),
            encoding,
            "-" if not missing else ",".join(missing),
            f"{seo_title_filled:.0f}%",
            f"{seo_desc_filled:.0f}%",
        ])

    headers = ["file", "rows", "cols", "encoding", "missing req cols", "seo title", "seo desc"]
    print(tabulate(rows, headers=headers, tablefmt="github"))

    total_rows = sum(int(r[1].replace(",", "")) for r in rows)
    print(f"\nTotal content rows across {len(rows)} files: {total_rows:,}")
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
