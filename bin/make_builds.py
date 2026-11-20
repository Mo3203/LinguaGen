#!/usr/bin/env python3
"""Produce the two deployable builds from one exported content folder.

    laptop_build/   application + full content, videos included
    phone_build/    application + content, with the video variants you choose
                    via --phone-videos (default none, for a small upload)

    python bin/make_builds.py --lang de
    python bin/make_builds.py --lang de --phone-videos bilingual

Defaults: the application from app/dist, the content from <generated>/<lang>/web,
the builds into <generated>/<lang>/builds.

The phone build's manifest has its video references removed, so the
application does not look for files that are not there. Each build is named
for its language (window title, home-screen name).

Nothing is modified in place; both builds are fresh copies.
"""
from __future__ import annotations
import argparse
import json
import re
import shutil
from pathlib import Path

from language import PROFILE as P
from paths import LANG_ROOT, REPO, WEB

APP_SKIP = {"__pycache__", ".DS_Store"}
DOCS = {"OFFLINE_GUIDE.md", "RUN_ME.md", "INSTALL_CONTENT.md", "DEPLOY_PHONE.md"}


def folder_mb(p: Path) -> float:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1e6


def copy_app(app: Path, dest: Path, keep_launcher: bool) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for item in app.iterdir():
        if item.name in APP_SKIP or item.name == "content":
            continue
        if not keep_launcher and item.name.endswith(".command"):
            continue
        if item.is_dir():
            shutil.copytree(item, dest / item.name, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest / item.name)


def name_the_app(build: Path) -> None:
    """Give a build its language's name: page title and home-screen name."""
    name = P.data.get("appName", f"{P.name} Study")
    short = P.data.get("shortName", P.name)
    idx = build / "index.html"
    if idx.exists():
        html = idx.read_text(encoding="utf-8")
        html = re.sub(r"<title>.*?</title>", f"<title>{name}</title>", html, count=1)
        html = html.replace('<html lang="en">', f'<html lang="en" data-language="{P.code}">')
        idx.write_text(html, encoding="utf-8")
    man = build / "manifest.webmanifest"
    if man.exists():
        m = json.loads(man.read_text(encoding="utf-8"))
        m["name"], m["short_name"] = name, short
        man.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
    for launcher in build.glob("*.command"):
        text = launcher.read_text(encoding="utf-8").replace("Language Study", name)
        # each language on its own port, so the two never share a browser origin
        text = re.sub(r"^PORT=\d+", f"PORT={P.data.get('laptopPort', 8000)}", text, flags=re.M)
        target = build / f"Start {name}.command"
        launcher.unlink()
        target.write_text(text, encoding="utf-8")
        target.chmod(0o755)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", default=str(REPO / "app" / "dist"),
                    help="folder with index.html, assets/, sw.js")
    ap.add_argument("--content", default=str(WEB), help="exported content folder")
    ap.add_argument("--out", default=str(LANG_ROOT / "builds"))
    ap.add_argument("--phone-videos", choices=["none", "bilingual", "target", P.video_suffix, "both"],
                    default="none",
                    help="which unit videos to include in the phone build "
                         "(default none; 'bilingual' roughly halves the video size)")
    args = ap.parse_args()
    if args.phone_videos == P.video_suffix:
        args.phone_videos = "target"

    app = Path(args.app).resolve()
    content = Path(args.content).resolve()
    out = Path(args.out).resolve()

    if not (app / "index.html").exists():
        raise SystemExit(f"no index.html in {app}")
    manifest_path = content / "bundle.json"
    if not manifest_path.exists():
        raise SystemExit(f"no bundle.json in {content}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # ---------------- laptop build: everything ----------------
    laptop = out / "laptop_build"
    if laptop.exists():
        shutil.rmtree(laptop)
    copy_app(app, laptop, keep_launcher=True)
    shutil.copytree(content, laptop / "content")
    name_the_app(laptop)

    # ---------------- phone build: no videos ----------------
    phone = out / "phone_build"
    if phone.exists():
        shutil.rmtree(phone)
    copy_app(app, phone, keep_launcher=False)
    name_the_app(phone)
    pc = phone / "content"
    pc.mkdir(parents=True, exist_ok=True)

    for sub in ("audio", "images"):
        if (content / sub).is_dir():
            shutil.copytree(content / sub, pc / sub)

    # which video variants the phone build should carry
    want = {"none": set(), "bilingual": {"bilingual"},
            "target": {"target"}, "both": {"bilingual", "target"}}[args.phone_videos]

    def variant_of(name: str) -> str | None:
        if name.endswith("_bilingual.mp4"):
            return "bilingual"
        if name.endswith(f"_{P.video_suffix}.mp4"):
            return "target"
        return None

    src_units = content / "units"
    kept_practice = kept_video = 0
    if src_units.is_dir():
        for item in src_units.rglob("*"):
            if not item.is_file():
                continue
            if item.suffix.lower() == ".mp4":
                if variant_of(item.name) not in want:
                    continue
                kept_video += 1
            else:
                kept_practice += 1
            rel = item.relative_to(src_units)
            dst = pc / "units" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dst)

    # remove references to variants the phone build does not carry
    stripped = 0
    for topic in manifest.get("topics", []):
        for unit in topic.get("units", []):
            for key, variant in (("videoBil", "bilingual"), ("videoFr", "target")):
                if variant not in want and unit.pop(key, None) is not None:
                    stripped += 1
    (pc / "bundle.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    # ---------------- report ----------------
    n_videos = len(list((laptop / "content").rglob("*.mp4")))
    print(f"laptop_build  {folder_mb(laptop):7.0f} MB   videos: {n_videos}")
    print(f"phone_build   {folder_mb(phone):7.0f} MB   videos: {kept_video} "
          f"({args.phone_videos})"
          + (f", removed {stripped} references" if stripped else "")
          + f", kept {kept_practice} practice tracks")
    print()
    print(f"builds in {out}")
    print(f"laptop: double-click the Start command inside {laptop.name}")
    print(f"phone : publish the {phone.name} folder, then install it from Safari")
    pm = folder_mb(phone)
    if args.phone_videos != "none":
        print()
        print(f"The phone build now carries videos ({pm:.0f} MB). Upload takes longer, and on "
              f"iPhone you may prefer to store videos for selected topics rather than all of them.")


if __name__ == "__main__":
    main()
