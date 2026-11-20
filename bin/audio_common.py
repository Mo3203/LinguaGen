"""Shared by make_audio.py and make_vocab_audio.py: synthesise, level, write."""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from cache import cache_key, cached

PEAK = 10 ** (-1 / 20)          # -1 dBFS


def render_all(items: list[tuple[str, str]], adapter, audio_dir: Path) -> tuple[dict, int, int]:
    """items: (row id, text to speak). Returns ({row id: audio_ref}, made, skipped).
    Finished files are skipped, so an interrupted run resumes where it stopped."""
    import soundfile as sf
    refs, made, skipped = {}, 0, 0
    t0 = time.time()
    total = len(items)
    for i, (rid, text) in enumerate(items, 1):
        key = cache_key(text, adapter.component_version)
        path = audio_dir / f"{key}.wav"
        refs[rid] = f"build/audio/{key}.wav"
        if cached(path):
            skipped += 1
        else:
            samples, sr = adapter.synth(text)
            m = float(np.max(np.abs(samples))) or 1.0
            tmp = path.with_suffix(".part.wav")
            sf.write(tmp, (samples * (PEAK / m)).astype(np.float32), sr)
            tmp.replace(path)                     # never leaves a half-written file
            made += 1
        if i % 25 == 0 or i == total:
            rate = i / max(time.time() - t0, 1e-9)
            print(f"  {i}/{total}  made {made}, already there {skipped}, "
                  f"about {(total - i) / max(rate, 1e-9) / 60:.1f} min left", flush=True)
    return refs, made, skipped
