#!/usr/bin/env python3
"""Put this update into your project folder. Run it from anywhere:

    python3 ~/Downloads/language_system/install.py

It copies the code into ~/language_system (or the folder you give with
--into), and:
    - replaces the code folders: bin/, languages/, app/, notebooks/, docs/
    - adds data/de/, or updates it while no production has used it yet;
      never touches data/fr/
    - never touches work/ or anything generated
    - moves files this update replaces into _superseded/, never deletes

It prints every change. Add --dry-run to see the changes without making them.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = ["bin", "languages", "notebooks", "docs"]
FILES = ["README.md", "requirements.txt"]
APP_PARTS = ["src", "public", "dist", "index.html", "package.json", "package-lock.json",
             "tsconfig.json", "vite.config.ts", "README.md", "FIX_NODE.md"]
SUPERSEDED = ["tools/export_units_web.py", "tools/make_builds.py", "tools/export_web.py",
              "tools/build_units_v6.py", "bin/make_videos.py",
              "notebooks/00_control_panel.ipynb", "app/Start French Study.command"]
SKIP = {"__pycache__", ".DS_Store", "node_modules"}


def copy_tree(src: Path, dst: Path, dry: bool, counts: dict):
    for p in src.rglob("*"):
        if any(part in SKIP for part in p.parts) or not p.is_file():
            continue
        target = dst / p.relative_to(src)
        state = "update" if target.exists() else "add"
        if target.exists() and target.read_bytes() == p.read_bytes():
            continue
        counts[state] += 1
        if not dry:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)


def produced(folder: Path) -> bool:
    """True once recordings have been linked into the dataset."""
    import csv
    for name in ("sentences.csv", "vocab.csv"):
        f = folder / name
        if f.exists():
            with f.open(encoding="utf-8") as fh:
                if any((r.get("audio_ref") or "").strip() for r in csv.DictReader(fh)):
                    return True
    return False


def same(a: Path, b: Path) -> bool:
    return all((b / n).exists() and (a / n).read_bytes() == (b / n).read_bytes()
               for n in ("vocab.csv", "sentences.csv"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--into", default=str(Path.home() / "language_system"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    dest = Path(a.into).expanduser()
    if dest.resolve() == HERE:
        raise SystemExit("This is already the project folder; nothing to install.")
    if not dest.exists():
        raise SystemExit(f"{dest} not found. Give the project folder with --into.")
    dry = a.dry_run
    print(f"installing into {dest}" + ("  (dry run: nothing is changed)" if dry else ""))

    moved = []
    for rel in SUPERSEDED:
        old = dest / rel
        if old.exists():
            moved.append(rel)
            if not dry:
                target = dest / "_superseded" / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old), str(target))
    for rel in moved:
        print(f"  moved aside    {rel}  ->  _superseded/{rel}")

    for folder in CODE:
        counts = {"add": 0, "update": 0}
        copy_tree(HERE / folder, dest / folder, dry, counts)
        print(f"  {folder + '/':<14} {counts['add']} added, {counts['update']} updated")

    counts = {"add": 0, "update": 0}
    for part in APP_PARTS:
        src = HERE / "app" / part
        if src.is_dir():
            copy_tree(src, dest / "app" / part, dry, counts)
        elif src.is_file():
            t = dest / "app" / part
            if not (t.exists() and t.read_bytes() == src.read_bytes()):
                counts["update" if t.exists() else "add"] += 1
                if not dry:
                    t.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, t)
    print(f"  {'app/':<14} {counts['add']} added, {counts['update']} updated")

    for lang_dir in sorted((HERE / "data").iterdir()):
        target = dest / "data" / lang_dir.name
        if not (target / "vocab.csv").exists():
            print(f"  data/{lang_dir.name}/       added")
            if not dry:
                shutil.copytree(lang_dir, target, dirs_exist_ok=True)
        elif produced(target):
            print(f"  data/{lang_dir.name}/       kept yours (production has started on it)")
        elif same(lang_dir, target):
            print(f"  data/{lang_dir.name}/       already current")
        else:
            print(f"  data/{lang_dir.name}/       updated; your copy moved to _superseded/data/{lang_dir.name}/")
            if not dry:
                old = dest / "_superseded" / "data" / lang_dir.name
                old.parent.mkdir(parents=True, exist_ok=True)
                if old.exists():
                    shutil.rmtree(old)
                shutil.move(str(target), str(old))
                shutil.copytree(lang_dir, target)

    for rel in FILES:
        if not dry:
            shutil.copy2(HERE / rel, dest / rel)
    print("done." if not dry else "dry run finished; run again without --dry-run to install.")


if __name__ == "__main__":
    main()
