#!/usr/bin/env python3
"""Sentence recordings: sentences.csv -> build/audio/<key>.wav, and audio_ref
written back into sentences.csv.

    python bin/make_audio.py --lang de                       voice from the profile
    python bin/make_audio.py --lang de --topics greetings    only some topics
    python bin/make_audio.py --lang de --limit 10            a short trial
    python bin/make_audio.py --lang de --engine dummy        test tones, no voice

Resumable: finished recordings are skipped.
"""
from __future__ import annotations

import argparse

import pandas as pd

from audio_common import render_all
from language import PROFILE as P
from paths import AUDIO, DATA, LANG_ROOT, REPORTS
from tts_adapters import ENGINES, get_adapter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", "--adapter", dest="engine", default="profile", choices=ENGINES)
    ap.add_argument("--topics", nargs="*", default=None)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    s = pd.read_csv(DATA / "sentences.csv", encoding="utf-8")
    rows = s
    if a.topics:
        v = pd.read_csv(DATA / "vocab.csv", encoding="utf-8")
        rows = s[s.vocab_id.isin(v[v.topic.isin(a.topics)].id)]
    if a.limit:
        rows = rows.head(a.limit)

    adapter = get_adapter(P, a.engine)
    print(f"[sentence recordings] {P.name}, {len(rows)} sentences, voice {adapter.component_version}")
    refs, made, skipped = render_all(list(zip(rows.id, rows.target_sentence)), adapter, AUDIO)

    s["audio_ref"] = s["audio_ref"].astype("string")
    mask = s.id.isin(refs)
    s.loc[mask, "audio_ref"] = s.loc[mask, "id"].map(refs)
    s.to_csv(DATA / "sentences.csv", index=False, encoding="utf-8")

    on_disk = sum((LANG_ROOT / p).exists() for p in s.audio_ref.dropna())
    lines = [f"voice: {adapter.component_version}",
             f"made {made}, already there {skipped}",
             f"coverage: {on_disk} of {len(s)} sentences have a recording"]
    (REPORTS / "audio_status.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
