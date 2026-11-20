#!/usr/bin/env python3
"""Web content: the built study units -> a folder the study application reads.

Reads, for the chosen language:
    build/units/<unit>/timing.csv       which words and sentences, and when
    build/units/<unit>/audio.wav        the practice track
    data/<lang>/vocab.csv, sentences.csv
    build/audio/*.wav, build/images/*.png

Writes (default: <generated>/<lang>/web/):
    bundle.json                         the manifest, with the language profile
    audio/<key>.opus                    word and sentence clips (64 kbps)
    images/<key>.webp                   pictures (640x360)
    units/<unit>/practice.opus          practice tracks
    units/<unit>_*.mp4                  videos (leave out with --no-videos)

    python bin/export_units_web.py --lang de
    python bin/export_units_web.py --lang de --topics greetings --no-videos

Resumable: files already converted are skipped.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import subprocess
from pathlib import Path

import pandas as pd
from PIL import Image

from language import PROFILE as P
from paths import DATA, IMAGES, UNITS, WEB


def sh(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def blank(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x)) or str(x).strip() in ("", "nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(WEB))
    ap.add_argument("--topics", nargs="*", default=None, help="only these topics")
    ap.add_argument("--no-videos", action="store_true", help="leave the videos out")
    ap.add_argument("--video-variant", choices=["both", "bilingual", "target", P.video_suffix],
                    default="both", help="which video variants to include")
    ap.add_argument("--no-practice", action="store_true", help="leave the practice tracks out")
    a = ap.parse_args()
    if a.video_variant == P.video_suffix:
        a.video_variant = "target"

    out = Path(a.out).expanduser().resolve()
    if not UNITS.is_dir():
        raise SystemExit(f"no study units at {UNITS}. Build units first.")
    (out / "audio").mkdir(parents=True, exist_ok=True)
    (out / "images").mkdir(exist_ok=True)

    v = pd.read_csv(DATA / "vocab.csv", encoding="utf-8")
    s = pd.read_csv(DATA / "sentences.csv", encoding="utf-8")
    vinfo = {r.id: r for r in v.itertuples()}
    sent_by_text = {}
    for r in s.itertuples():
        sent_by_text.setdefault(str(r.target_sentence).strip(), r)

    n = {"audio": 0, "audio_skip": 0, "image": 0, "image_skip": 0}

    def opus(src: Path | None) -> str | None:
        if src is None:
            return None
        dst = out / "audio" / f"{src.stem}.opus"
        if dst.exists():
            n["audio_skip"] += 1
        else:
            sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
                "-c:a", "libopus", "-b:a", "64k", str(dst)])
            n["audio"] += 1
        return f"audio/{src.stem}.opus"

    def webp(key: str) -> str | None:
        if not key:
            return None
        dst = out / "images" / f"{key}.webp"
        src = IMAGES / f"{key}.png"
        # reconvert when the picture is newer, e.g. a real one replaced a stand-in
        if dst.exists() and (not src.exists() or dst.stat().st_mtime >= src.stat().st_mtime):
            n["image_skip"] += 1
            return f"images/{key}.webp"
        if not src.exists():
            return None
        im = Image.open(src).convert("RGB")
        im.thumbnail((640, 360))
        im.save(dst, "WEBP", quality=75)
        n["image"] += 1
        return f"images/{key}.webp"

    unit_dirs = sorted(p for p in UNITS.iterdir()
                       if p.is_dir() and not p.name.startswith("_") and p.name.startswith(P.unit_prefix))
    topics: dict[str, list] = {}

    for ud in unit_dirs:
        timing = ud / "timing.csv"
        if not timing.exists():
            continue
        unit_id = ud.name
        topic = P.topic_of_unit(unit_id)
        if a.topics and topic not in a.topics:
            continue
        rows = list(csv.DictReader(timing.open(encoding="utf-8")))
        if not rows:
            continue

        segments = []
        for r in rows:
            try:
                segments.append({"kind": r["kind"], "start": round(float(r["start"]), 3),
                                 "end": round(float(r["end"]), 3), "fr": r["fr"]})
            except (KeyError, ValueError):
                pass

        words, order = {}, []
        for r in rows:
            vid = r["vocab_id"]
            info = vinfo.get(vid)
            if vid not in words:
                vocab = getattr(info, "vocab", vid) if info is not None else vid
                pos = str(getattr(info, "pos", "")) if info is not None else ""
                gender = getattr(info, "gender", None) if info is not None else None
                plural = getattr(info, "plural", None) if info is not None else None
                entry = {
                    "id": vid, "word": vocab, "pos": pos,
                    "gender": None if blank(gender) else str(gender),
                    "meaning": getattr(info, "english_meaning", "") if info is not None else "",
                    "sentences": [],
                }
                display = P.display_title(vocab, pos, gender, plural)
                if display != vocab:
                    entry["display"] = display
                if not blank(plural):
                    entry["plural"] = str(plural).strip()
                words[vid] = entry
                order.append(vid)
            w = words[vid]
            img = webp(r.get("image_key", ""))
            if r["kind"] == "word":
                spoken = P.citation_form(w["word"], w["pos"], w["gender"])
                w["spoken"] = spoken
                au = opus(P.resolve_audio(getattr(info, "audio_ref", None) if info is not None else None,
                                          spoken))
                if au:
                    w["audio"] = au
                if img:
                    w["image"] = img
            else:
                srow = sent_by_text.get(str(r["fr"]).strip())
                au = opus(P.resolve_audio(getattr(srow, "audio_ref", None), r["fr"])) if srow is not None else None
                sent = {
                    "id": getattr(srow, "id", f"{vid}_{len(w['sentences'])}") if srow is not None
                    else f"{vid}_{len(w['sentences'])}",
                    "register": getattr(srow, "register", "formal_statement") if srow is not None
                    else "formal_statement",
                    "fr": r["fr"], "en": r.get("en", ""),
                }
                if au:
                    sent["audio"] = au
                if img:
                    sent["image"] = img
                w["sentences"].append(sent)

        unit = {"id": unit_id,
                "title": f"{topic.replace('_', ' ').title()} · Unit {unit_id.rsplit('_', 1)[1]}",
                "words": [words[k] for k in order]}
        if segments:
            unit["segments"] = segments

        if not a.no_practice and (ud / "audio.wav").exists():
            (out / "units" / unit_id).mkdir(parents=True, exist_ok=True)
            dst = out / "units" / unit_id / "practice.opus"
            if not dst.exists() or dst.stat().st_mtime < (ud / "audio.wav").stat().st_mtime:
                sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(ud / "audio.wav"),
                    "-c:a", "libopus", "-b:a", "48k", str(dst)])
            unit["practice"] = f"units/{unit_id}/practice.opus"

        if not a.no_videos:
            wanted = [("bilingual", "videoBil", "bilingual"), (P.video_suffix, "videoFr", "target")]
            if a.video_variant != "both":
                wanted = [x for x in wanted if x[2] == a.video_variant]
            for suf, keyname, _ in wanted:
                src = ud / f"{unit_id}_{suf}.mp4"
                if src.exists():
                    (out / "units").mkdir(parents=True, exist_ok=True)
                    dst = out / "units" / src.name
                    if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
                        shutil.copy2(src, dst)
                    unit[keyname] = f"units/{src.name}"

        topics.setdefault(topic, []).append(unit)

    bundle = {"version": 2, "language": P.code, "profile": P.app_block(),
              "topics": [{"topic": t, "title": t.replace("_", " ").title(),
                          "units": sorted(u, key=lambda x: x["id"])}
                         for t, u in sorted(topics.items())]}
    (out / "bundle.json").write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")

    n_units = sum(len(t["units"]) for t in bundle["topics"])
    n_words = sum(len(u["words"]) for t in bundle["topics"] for u in t["units"])
    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file()) / 1e6
    vids = sum(f.stat().st_size for f in out.rglob("*.mp4")) / 1e6
    print(f"[web content] {P.name}: {len(bundle['topics'])} topics, {n_units} units, {n_words} words")
    print(f"  audio {n['audio']} converted, {n['audio_skip']} already there; "
          f"pictures {n['image']} converted, {n['image_skip']} already there")
    print(f"  size {size:.0f} MB" + (f" (videos {vids:.0f} MB)" if vids else ""))
    print(f"  written to {out}")


if __name__ == "__main__":
    main()
