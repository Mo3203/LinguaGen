#!/usr/bin/env python3
"""Combine every unit's study_sheet.csv into one master review file.

Run after build_units.py. Produces:
    reports/study_master.csv   — every unit stacked, with a 'unit' column
Useful for reading/printing the whole deck or importing into a review app.

Usage:  python bin/build_study_index.py --lang de
"""
from __future__ import annotations
import csv
from pathlib import Path

from paths import BUILD, REPORTS

UNITS = BUILD / "units"


def main():
    sheets = sorted(UNITS.glob("*/study_sheet.csv"))
    if not sheets:
        raise SystemExit("no study sheets yet — run bin/build_units.py first")
    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / "study_master.csv"
    n = 0
    with open(out, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        header_written = False
        for sheet in sheets:
            unit = sheet.parent.name
            rows = list(csv.reader(sheet.open(encoding="utf-8")))
            if not rows:
                continue
            if not header_written:
                wr.writerow(["unit"] + rows[0])
                header_written = True
            for r in rows[1:]:
                wr.writerow([unit] + r)
                n += 1
    print(f"wrote {out}  ({len(sheets)} units, {n} rows)")


if __name__ == "__main__":
    main()
