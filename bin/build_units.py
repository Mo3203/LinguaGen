#!/usr/bin/env python3
"""Study units: recordings + illustrations -> one practice track and two videos per unit.

Groups words into small STUDY UNITS (default 5 words each). For every unit it
builds a continuous audio track, MEASURES real segment durations, and emits a
timing table — then renders video from that table. Two variants per unit:

    <unit>_bilingual.mp4       the language studied + English on screen
    <unit>_<language>.mp4      the language studied only (immersion), e.g. _french, _german

Per-unit outputs (in build/units/<unit>/):
    audio.wav            the measured master track
    timing.csv           segment, kind, vocab_id, start, end, duration, texts, image_key
    <unit>_bilingual.mp4
    <unit>_<language>.mp4

Audio structure per word-row (your process):
    lead 0.5s | WORD x3 (short pause between) | long pause |
               SENTENCE1 x3 | long | SENTENCE2 x3 | long | SENTENCE3 x3 | long |
    entry pause between words
Flags:
    --unit-size 5      words per study unit
    --word-reps 3      --sent-reps 3
    --short 0.4        pause between repeats (seconds)
    --long 1.2         pause after a segment's repeats
    --word-gap 2.0     pause between words
    --lead 0.5         silence at unit start
    --limit-units N    only build first N units (trial)
    --force            rebuild even if finished
Needs ffmpeg.  Usage:  python bin/build_units.py --lang de [topic ...] [flags]

Names: French units keep their names (greetings_01). Other languages carry
their code (de_greetings_01) so file names, offline storage and progress never
collide between languages.

Resumable: a unit whose content and settings are unchanged is skipped.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, subprocess, tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

from paths import DATA, IMAGES, SCRIPTS_JSON, UNITS
from cache import cache_key
from language import PROFILE as P

# Part of every unit's fingerprint. Kept at the value your French units were
# built with so they are recognised as finished. Change it only when the look
# of the video changes, which rebuilds everything.
BUILD_UNITS_VERSION = "v6-professional-2026-07"
CODE_VERSION = "v7-languages"
SR = 24000
W, H, FPS = 1280, 720, 30
IMG_KEY_VERSION = "sdxl-turbo/style-v1"
BG, FG, SUB, ACCENT = (38, 40, 34), (236, 233, 224), (150, 152, 138), (150, 178, 166)
UNITS_DIR = UNITS
GENDER_LABEL = dict(P.genders)
TARGET = P.video_suffix          # "french", "german": the immersion variant's name


# ---------- audio helpers ----------
def load(path: Path) -> np.ndarray:
    a, sr = sf.read(path, dtype="float32")
    if a.ndim > 1:
        a = a.mean(axis=1)
    return a


def sil(seconds: float) -> np.ndarray:
    return np.zeros(int(SR * seconds), dtype=np.float32)


def repeat_block(clip: np.ndarray, reps: int, short: float) -> np.ndarray:
    parts = []
    for i in range(reps):
        parts.append(clip)
        if i < reps - 1:
            parts.append(sil(short))
    return np.concatenate(parts)


# ---------- fonts ----------
def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


F_VOC, F_VEN, F_SENT, F_SEN, F_SIDE, F_TAG = (font(54), font(30), font(42),
                                              font(28), font(26), font(26))
F_POS = font(32)
POS_COLOR = (214, 176, 130)  # warm, high-contrast; distinct from blue accents


def wrap(d, text, fnt, mw):
    words, lines, cur = str(text).split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=fnt) <= mw:
            cur = t
        else:
            lines.append(cur); cur = wd
    if cur:
        lines.append(cur)
    return lines


def centered(d, lines, fnt, y, color, gap=8):
    for ln in lines:
        d.text(((W - d.textlength(ln, font=fnt)) / 2, y), ln, font=fnt, fill=color)
        y += fnt.size + gap
    return y


def render_frame(image_path, topic, vocab_fr, vocab_en, pos, right_lines,
                 sent_fr, sent_en, target_only):
    """target_only: show the studied language only, without English."""
    c = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(c)
    t = topic.replace("_", " ")
    d.text((W - 40 - d.textlength(t, font=F_TAG), 24), t, font=F_TAG, fill=ACCENT)
    y = centered(d, [vocab_fr], F_VOC, 22, FG)
    if not target_only and vocab_en:
        centered(d, [vocab_en], F_VEN, y + 2, SUB)
    top_y, bot_y = 172, 540
    if image_path and Path(image_path).exists():
        img = Image.open(image_path).convert("RGB")
        ph = bot_y - top_y
        r = min((W - 340) / img.width, ph / img.height)
        img = img.resize((int(img.width * r), int(img.height * r)))
        c.paste(img, ((W - img.width) // 2, top_y + (ph - img.height) // 2))
    mid = (top_y + bot_y) // 2
    pos_clean = "" if pos is None else str(pos).strip().replace("_", " ")
    if pos_clean and pos_clean.lower() != "nan":
        d.text((36, mid - F_POS.size - 20), "Part of speech", font=F_TAG, fill=SUB)
        d.text((36, mid - F_POS.size + 12), pos_clean, font=F_POS, fill=POS_COLOR)
    ry = mid - len(right_lines) * (F_SIDE.size + 6) // 2
    for ln in right_lines:
        d.text((W - 36 - d.textlength(ln, font=F_SIDE), ry), ln, font=F_SIDE, fill=ACCENT)
        ry += F_SIDE.size + 6
    if sent_fr:
        y = centered(d, wrap(d, sent_fr, F_SENT, W - 140), F_SENT, 560, FG)
        if not target_only and sent_en:
            centered(d, wrap(d, sent_en, F_SEN, W - 160), F_SEN, y + 4, SUB)
    return c


# ---------- resume / idempotency ----------
OUTPUT_NAMES = ("audio.wav", "timing.csv", "study_sheet.csv")


def unit_signature(words, a) -> str:
    """Changes if the unit's content OR any pacing flag OR the builder changes."""
    payload = json.dumps(words, sort_keys=True, ensure_ascii=False)
    flags = (f"{a.word_reps}|{a.sent_reps}|{a.short}|{a.long}|"
             f"{a.word_gap}|{a.lead}|{BUILD_UNITS_VERSION}")
    return hashlib.sha256((payload + "|" + flags).encode("utf-8")).hexdigest()[:16]


def outputs_present(outdir: Path, unit_name: str) -> bool:
    names = list(OUTPUT_NAMES) + [f"{unit_name}_bilingual.mp4", f"{unit_name}_{TARGET}.mp4"]
    return all((outdir / n).exists() and (outdir / n).stat().st_size > 0 for n in names)


def provisional_tag(words, vmap, smap) -> str:
    """Empty for a unit made from final material. Otherwise a short tag naming
    the trial material it used (stand-in pictures, test tones or another
    voice), so the unit is rebuilt automatically once final material exists.
    Final units keep their old fingerprint, so nothing already built is redone."""
    parts = []
    for w in words:
        vrow = vmap.loc[w["vocab_id"]]
        spoken = P.citation_form(w["vocab"], str(vrow.pos), getattr(vrow, "gender", None))
        texts = [(getattr(vrow, "audio_ref", None), spoken)]
        texts += [(smap.loc[sc["sentence_id"]].audio_ref, sc["fr"]) for sc in w["scenes"]]
        for ref, text in texts:
            used = P.resolve_audio(ref, text)
            if used is not None and used.name != Path(P.audio_ref(text)).name:
                parts.append(used.name)
        for sc in w["scenes"]:
            key = cache_key(sc["visual_prompt"], IMG_KEY_VERSION)
            if (IMAGES / f"{key}.placeholder").exists():
                parts.append("stand-in:" + key)
    if not parts:
        return ""
    return "+provisional-" + hashlib.sha256("|".join(parts).encode()).hexdigest()[:10]


# ---------- build one unit ----------
def build_unit(unit_name, topic, words, v, s, a):
    vmap, smap = v.set_index("id"), s.set_index("id")
    outdir = UNITS_DIR / unit_name
    outdir.mkdir(parents=True, exist_ok=True)

    # ---- resume: skip work that is already done ----
    sig = unit_signature(words, a)
    sigfile = outdir / ".sig"
    if not a.force and outputs_present(outdir, unit_name):
        stored = sigfile.read_text().strip() if sigfile.exists() else ""
        tag = provisional_tag(words, vmap, smap) if stored.startswith(sig + "+") else ""
        if stored == sig + tag:
            return f"SKIP  {unit_name}  (already built" + (", with trial material)" if tag else ")")
        if not sigfile.exists():
            # built by an older version with the same settings -> adopt, don't redo
            sigfile.write_text(sig)
            return f"ADOPT {unit_name}  (existing outputs kept)"

    # every recording must exist first; a half-built unit would be kept as finished
    missing = 0
    for w in words:
        vrow = vmap.loc[w["vocab_id"]]
        spoken = P.citation_form(w["vocab"], str(vrow.pos), getattr(vrow, "gender", None))
        if not P.resolve_audio(getattr(vrow, "audio_ref", None), spoken):
            missing += 1
        for sc in w["scenes"]:
            if not P.resolve_audio(smap.loc[sc["sentence_id"]].audio_ref, sc["fr"]):
                missing += 1
    if missing:
        return f"WAIT  {unit_name}  ({missing} recordings missing)"

    track = [sil(a.lead)]
    cursor = a.lead
    timeline = []  # each: dict(kind, vocab_id, start, end, image_key, fr, en, pos, right)

    def add(clip, kind, meta):
        nonlocal cursor
        block = repeat_block(clip, a.word_reps if kind == "word" else a.sent_reps, a.short)
        start = cursor
        track.append(block)
        cursor += len(block) / SR
        track.append(sil(a.long)); cursor += a.long
        timeline.append({**meta, "kind": kind, "start": round(start, 3),
                         "end": round(cursor - a.long, 3),
                         "duration": round((cursor - a.long) - start, 3)})

    for wi, w in enumerate(words):
        vrow = vmap.loc[w["vocab_id"]]
        gender = getattr(vrow, "gender", None)
        gline = P.gender_label(gender)
        spoken = P.citation_form(w["vocab"], str(vrow.pos), gender)
        title = P.display_title(w["vocab"], str(vrow.pos), gender, getattr(vrow, "plural", None))
        img_key = cache_key(w["scenes"][0]["visual_prompt"], IMG_KEY_VERSION)
        vaudio = P.resolve_audio(getattr(vrow, "audio_ref", None), spoken)
        if vaudio:
            add(load(vaudio), "word",
                {"vocab_id": w["vocab_id"], "image_key": img_key, "fr": spoken, "title": title,
                 "en": w["english_meaning"], "pos": str(vrow.pos),
                 "right": [x for x in [gline] if x]})
        for sc in w["scenes"]:
            srow = smap.loc[sc["sentence_id"]]
            saudio = P.resolve_audio(srow.audio_ref, sc["fr"])
            if not saudio:
                continue
            add(load(saudio), "sentence",
                {"vocab_id": w["vocab_id"],
                 "image_key": cache_key(sc["visual_prompt"], IMG_KEY_VERSION),
                 "fr": sc["fr"], "en": sc["en"], "pos": str(vrow.pos), "vocab_fr": title,
                 "vocab_en": w["english_meaning"],
                 "right": [x for x in [gline, sc["register"].replace("_", " ")] if x]})
        if wi < len(words) - 1:
            track.append(sil(a.word_gap)); cursor += a.word_gap

    master = np.concatenate(track)
    m = float(np.max(np.abs(master))) or 1.0
    master = (master * (10 ** (-1 / 20) / m)).astype(np.float32)
    sf.write(outdir / "audio.wav", master, SR)

    # timing.csv
    with open(outdir / "timing.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["kind", "vocab_id", "start", "end", "duration", "fr", "en", "image_key"])
        for seg in timeline:
            wr.writerow([seg["kind"], seg["vocab_id"], seg["start"], seg["end"],
                         seg["duration"], seg["fr"], seg.get("en", ""), seg["image_key"]])

    # ---- study_sheet.csv : human-readable review sheet for this unit ----
    with open(outdir / "study_sheet.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["vocab_id", "word", "pos", "gender", "meaning",
                     "register", f"{P.name.lower()}_sentence", "english_sentence"])
        for w in words:
            vrow = vmap.loc[w["vocab_id"]]
            g = vrow.gender if isinstance(getattr(vrow, "gender", None), str) else ""
            # a word row (sentence columns blank) then its three sentence rows
            wr.writerow([w["vocab_id"], w["vocab"], str(vrow.pos), g,
                         w["english_meaning"], "", "", ""])
            for sc in w["scenes"]:
                wr.writerow([w["vocab_id"], w["vocab"], str(vrow.pos), g,
                             w["english_meaning"], sc["register"],
                             sc["fr"], sc["en"]])

    total = len(master) / SR
    for target_only in (False, True):
        render_variant(outdir, unit_name, topic, timeline, total, target_only)
    sigfile.write_text(sig + provisional_tag(words, vmap, smap))
    return f"OK  {unit_name}  ({len(words)} words, {len(timeline)} segments, {total:.0f}s)"


def render_variant(outdir, unit_name, topic, timeline, total, target_only):
    """One ffmpeg render: concat still-frames matching each segment's duration,
    with the single measured audio track over the top."""
    suffix = TARGET if target_only else "bilingual"
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        concat_lines, prev_end = [], 0.0
        idx = 0

        def emit(img, dur):
            nonlocal idx
            if dur <= 0:
                return
            p = tmp / f"f{idx}.png"; img.save(p); idx += 1
            concat_lines.append((p, dur))

        # leading silence -> title-ish first frame (blank word)
        for seg in timeline:
            gap = seg["start"] - prev_end
            if gap > 0.01 and concat_lines:  # extend previous frame through the pause
                p, d = concat_lines[-1]; concat_lines[-1] = (p, d + gap)
            elif gap > 0.01:
                emit(Image.new("RGB", (W, H), BG), gap)
            if seg["kind"] == "word":
                fr = render_frame(IMAGES / f"{seg['image_key']}.png", topic, seg.get("title", seg["fr"]),
                                  seg["en"], seg["pos"], seg["right"], "", "", target_only)
            else:
                fr = render_frame(IMAGES / f"{seg['image_key']}.png", topic,
                                  seg["vocab_fr"], seg["vocab_en"], seg["pos"], seg["right"],
                                  seg["fr"], seg["en"], target_only)
            emit(fr, seg["duration"])
            prev_end = seg["end"]
        if total - prev_end > 0.01 and concat_lines:
            p, d = concat_lines[-1]; concat_lines[-1] = (p, d + (total - prev_end))

        lst = tmp / "list.txt"
        with open(lst, "w") as f:
            for p, d in concat_lines:
                f.write(f"file '{p}'\nduration {d:.3f}\n")
            f.write(f"file '{concat_lines[-1][0]}'\n")  # ffmpeg concat demuxer quirk
        silent = tmp / "silent.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", str(lst), "-vf", f"fps={FPS},scale={W}:{H}",
                        "-pix_fmt", "yuv420p", "-c:v", "libx264", str(silent)], check=True)
        out = outdir / f"{unit_name}_{suffix}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent),
                        "-i", str(outdir / "audio.wav"), "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "128k", "-shortest", str(out)], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("topics", nargs="*")
    ap.add_argument("--topics", dest="topics_opt", nargs="*", default=None)
    ap.add_argument("--unit-size", type=int, default=5)
    ap.add_argument("--word-reps", type=int, default=3)
    ap.add_argument("--sent-reps", type=int, default=3)
    ap.add_argument("--short", type=float, default=0.4)
    ap.add_argument("--long", type=float, default=1.2)
    ap.add_argument("--word-gap", type=float, default=2.0)
    ap.add_argument("--lead", type=float, default=0.5)
    ap.add_argument("--limit-units", type=int, default=0)
    ap.add_argument("--force", action="store_true",
                    help="rebuild even if outputs already exist")
    a = ap.parse_args()
    print(f"[build_units {CODE_VERSION}] {P.name}  size={a.unit_size} word_reps={a.word_reps} sent_reps={a.sent_reps} "
          f"short={a.short} long={a.long} word_gap={a.word_gap}")

    v = pd.read_csv(DATA / "vocab.csv", encoding="utf-8")
    s = pd.read_csv(DATA / "sentences.csv", encoding="utf-8")
    topics = a.topics or a.topics_opt or sorted(p.stem for p in SCRIPTS_JSON.glob("*.json"))
    built = 0
    tally = {"OK": 0, "SKIP": 0, "ADOPT": 0, "WAIT": 0}
    for topic in topics:
        path = SCRIPTS_JSON / f"{topic}.json"
        if not path.exists():
            print(f"  skip {topic}: no script"); continue
        words = json.loads(path.read_text(encoding="utf-8"))["words"]
        for ui in range(0, len(words), a.unit_size):
            if a.limit_units and built >= a.limit_units:
                print("  (limit reached)"); return
            chunk = words[ui:ui + a.unit_size]
            name = P.unit_name(topic, ui // a.unit_size + 1)
            msg = build_unit(name, topic, chunk, v, s, a)
            print("  " + msg)
            tally[msg.split()[0]] = tally.get(msg.split()[0], 0) + 1
            built += 1
    print(f"\ndone: {tally['OK']} built, {tally['SKIP']} already finished, "
          f"{tally['ADOPT']} adopted, {tally['WAIT']} waiting for recordings"
          "  (--force rebuilds everything)")


if __name__ == "__main__":
    main()
