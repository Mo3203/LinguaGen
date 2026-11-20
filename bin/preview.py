#!/usr/bin/env python3
"""Quick look at the video layout, without building a unit.

Draws the first word card and first sentence frame of a topic and saves them
as pictures. Two seconds.

    python bin/preview.py --lang de                first topic with a script
    python bin/preview.py --lang de greetings
Output: build/units/_preview/word.png and sentence.png
"""
from __future__ import annotations

import json
import sys

import pandas as pd

from build_units import BUILD_UNITS_VERSION, IMG_KEY_VERSION, render_frame
from cache import cache_key
from language import PROFILE as P
from paths import DATA, IMAGES, SCRIPTS_JSON, UNITS

OUT = UNITS / "_preview"


def main():
    scripts = sorted(SCRIPTS_JSON.glob("*.json"))
    if not scripts:
        raise SystemExit("no scene descriptions yet. Run that stage first.")
    topic = sys.argv[1] if len(sys.argv) > 1 else scripts[0].stem
    path = SCRIPTS_JSON / f"{topic}.json"
    if not path.exists():
        path, topic = scripts[0], scripts[0].stem
    OUT.mkdir(parents=True, exist_ok=True)

    v = pd.read_csv(DATA / "vocab.csv", encoding="utf-8").set_index("id")
    w = json.loads(path.read_text(encoding="utf-8"))["words"][0]
    vrow = v.loc[w["vocab_id"]]
    pos = str(vrow.pos)
    gender = getattr(vrow, "gender", None)
    gline = P.gender_label(gender)
    title = P.display_title(w["vocab"], pos, gender, getattr(vrow, "plural", None))

    print(f"[preview {BUILD_UNITS_VERSION}] {P.name}  topic={topic}")
    print(f"  heading : {title}")
    print(f"  spoken  : {P.citation_form(w['vocab'], pos, gender)}")
    print(f"  part of speech: {pos}   gender: {gline or '-'}")

    img = IMAGES / f"{cache_key(w['scenes'][0]['visual_prompt'], IMG_KEY_VERSION)}.png"
    render_frame(img, topic, title, w["english_meaning"], pos,
                 [x for x in [gline] if x], "", "", False).save(OUT / "word.png")
    sc = w["scenes"][0]
    render_frame(IMAGES / f"{cache_key(sc['visual_prompt'], IMG_KEY_VERSION)}.png", topic, title,
                 w["english_meaning"], pos,
                 [x for x in [gline, sc["register"].replace("_", " ")] if x],
                 sc["fr"], sc["en"], False).save(OUT / "sentence.png")
    print(f"  wrote {OUT}/word.png and sentence.png")


if __name__ == "__main__":
    main()
