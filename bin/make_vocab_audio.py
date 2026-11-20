#!/usr/bin/env python3
"""Word recordings: one clip per word, and audio_ref written back into vocab.csv.

Nouns are spoken with their article, as the profile defines it:
    French   un chat, une maison, des lunettes
    German   der Kaffee, die Frau, das Haus, die Eltern; Deutschland alone
The plural marker (for example -s) is shown on screen and never spoken.

    python bin/make_vocab_audio.py --lang de [--topics ...] [--limit N] [--engine dummy]
"""
from __future__ import annotations

import argparse

import pandas as pd

from audio_common import render_all
from language import PROFILE as P
from paths import AUDIO, DATA, LANG_ROOT, REPORTS
from tts_adapters import ENGINES, get_adapter


def citation_form(vocab, pos, gender) -> str:
    """Kept for older scripts that import it."""
    return P.citation_form(vocab, pos, gender)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", "--adapter", dest="engine", default="profile", choices=ENGINES)
    ap.add_argument("--topics", nargs="*", default=None)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    v = pd.read_csv(DATA / "vocab.csv", encoding="utf-8")
    if "audio_ref" not in v.columns:
        v["audio_ref"] = pd.NA
    rows = v[v.topic.isin(a.topics)] if a.topics else v
    if a.limit:
        rows = rows.head(a.limit)

    adapter = get_adapter(P, a.engine)
    spoken = {r.id: P.citation_form(r.vocab, r.pos, getattr(r, "gender", None))
              for r in rows.itertuples()}
    print(f"[word recordings] {P.name}, {len(rows)} words, voice {adapter.component_version}")
    refs, made, skipped = render_all(list(spoken.items()), adapter, AUDIO)

    v["audio_ref"] = v["audio_ref"].astype("string")
    mask = v.id.isin(refs)
    v.loc[mask, "audio_ref"] = v.loc[mask, "id"].map(refs)
    v.to_csv(DATA / "vocab.csv", index=False, encoding="utf-8")

    on_disk = sum((LANG_ROOT / p).exists() for p in v.audio_ref.dropna())
    lines = [f"voice: {adapter.component_version}",
             f"made {made}, already there {skipped}",
             f"coverage: {on_disk} of {len(v)} words have a recording", "",
             "examples (written -> spoken):"]
    for r in rows.head(10).itertuples():
        lines.append(f"  {r.vocab:<18} -> {spoken[r.id]}")
    (REPORTS / "vocab_audio_status.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
