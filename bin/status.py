#!/usr/bin/env python3
"""Where a language stands, and what to run next.

    python bin/status.py --lang de
    python bin/status.py --lang de --json      for the production page
"""
from __future__ import annotations

import json

import pandas as pd

from cache import cache_key
from export_prompts import COMPONENT_VERSION as IMAGE_VERSION
from language import PROFILE as P
from paths import DATA, IMAGES, LANG_ROOT, REPORTS, SCRIPTS_JSON, UNITS, WEB


def counts() -> dict:
    """Every stage's progress as (have, need). Shared with produce.py."""
    c = {}
    try:
        v = pd.read_csv(DATA / "vocab.csv", encoding="utf-8")
        s = pd.read_csv(DATA / "sentences.csv", encoding="utf-8")
    except Exception:
        return {"dataset": (0, 1)}
    topics = sorted(v.topic.unique())
    c["dataset"] = (len(v), len(v))
    done_topics = [t for t in topics if (SCRIPTS_JSON / f"{t}.json").exists()]
    c["scripts"] = (len(done_topics), len(topics))

    sent = sum(P.resolve_audio(r.audio_ref, r.target_sentence) is not None for r in s.itertuples())
    c["audio"] = (sent, len(s))
    word = sum(P.resolve_audio(getattr(r, "audio_ref", None),
                               P.citation_form(r.vocab, r.pos, getattr(r, "gender", None))) is not None
               for r in v.itertuples())
    c["vocab_audio"] = (word, len(v))

    need = set()
    for t in done_topics:
        d = json.loads((SCRIPTS_JSON / f"{t}.json").read_text(encoding="utf-8"))
        for w in d["words"]:
            for sc in w["scenes"]:
                need.add(cache_key(sc["visual_prompt"], IMAGE_VERSION))
    real = sum((IMAGES / f"{k}.png").exists() and not (IMAGES / f"{k}.placeholder").exists()
               for k in need)
    stand = sum((IMAGES / f"{k}.placeholder").exists() for k in need)
    c["images"] = (real, len(need) or 1)
    c["images_standin"] = stand

    per_topic = v.groupby("topic").size()
    expected = int(sum(-(-n // 5) for n in per_topic))
    built = [u for u in UNITS.iterdir() if u.is_dir() and not u.name.startswith("_")
             and (u / f"{u.name}_bilingual.mp4").exists()] if UNITS.is_dir() else []
    c["units"] = (len(built), expected)
    c["export"] = (1 if (WEB / "bundle.json").exists() else 0, 1)
    return c


NAMES = {"dataset": "Dataset", "scripts": "Scene descriptions", "audio": "Sentence recordings",
         "vocab_audio": "Word recordings", "images": "Illustrations", "units": "Study units",
         "export": "Web content"}


def main():
    import sys
    c = counts()
    if "--json" in sys.argv:
        print(json.dumps({"language": P.code, "name": P.name, "root": str(LANG_ROOT),
                          "stages": {k: list(v) if isinstance(v, tuple) else v for k, v in c.items()}}))
        return
    lines = [f"{P.name}   generated material in {LANG_ROOT}", ""]
    nxt = None
    for key, name in NAMES.items():
        have, need = c.get(key, (0, 1))
        extra = ""
        if key == "images" and c.get("images_standin"):
            extra = f"   ({c['images_standin']} stand-in pictures to replace)"
        lines.append(f"  {name:<22} {have:>5} of {need:<5}{extra}")
        if have < need and nxt is None:
            nxt = name
    lines.append("")
    lines.append(f"NEXT  {nxt}" if nxt else "Everything is built.")
    lines.append(f"      python bin/produce.py --lang {P.code}   runs every stage that is not finished")
    out = "\n".join(lines)
    print(out)
    (REPORTS / "status.txt").write_text(out + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
