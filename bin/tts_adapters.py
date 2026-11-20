"""Speech engines. Each turns text into (float32 samples, sample rate).

    piper    open-source, runs on an ordinary processor. German uses it.
    kokoro   open-source, French uses it.
    edge     online Microsoft voices, a fallback only.
    dummy    a short tone, for testing the pipeline without a voice.

Which engine and voice a language uses is set in its profile
(languages/<code>.json, "speech"). Caching, loudness and file writing live in
make_audio.py and make_vocab_audio.py, not here.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import numpy as np


class PiperAdapter:
    """Piper voices, for example de_DE-thorsten-high.

    The voice is downloaded once into WORK/voices/ (about 110 MB) and reused.
    """
    name = "piper"

    def __init__(self, voice: str, version: str, voices_dir: Path, length_scale: float = 1.0):
        self.voice_name = voice
        self.component_version = version
        self._dir = voices_dir
        self._length_scale = length_scale
        self._voice = None              # loaded on first use, so a finished run needs no voice

    def _load(self):
        from piper import PiperVoice
        self._dir.mkdir(parents=True, exist_ok=True)
        model = self._dir / f"{self.voice_name}.onnx"
        config = self._dir / f"{self.voice_name}.onnx.json"
        if not (model.exists() and config.exists()):
            print(f"  downloading voice {self.voice_name} into {self._dir} (once only)", flush=True)
            from piper.download_voices import download_voice
            download_voice(self.voice_name, self._dir)
        self._voice = PiperVoice.load(model, config_path=config, use_cuda=False)
        self._syn = None
        if self._length_scale and abs(self._length_scale - 1.0) > 1e-6:
            from piper import SynthesisConfig
            self._syn = SynthesisConfig(length_scale=self._length_scale)

    def synth(self, text: str):
        if self._voice is None:
            self._load()
        chunks, sr = [], self._voice.config.sample_rate
        for chunk in self._voice.synthesize(text, syn_config=self._syn):
            chunks.append(np.asarray(chunk.audio_float_array, dtype=np.float32))
            sr = chunk.sample_rate
        if not chunks:
            raise RuntimeError(f"the voice produced no sound for: {text!r}")
        return np.concatenate(chunks), sr


class KokoroAdapter:
    name = "kokoro"

    def __init__(self, voice: str = "ff_siwis", version: str = "kokoro-82M/ff_siwis/v1",
                 lang_code: str = "f"):
        self.voice_name = voice
        self.component_version = version
        self._lang_code = lang_code
        self._pipe = None               # loaded on first use

    def synth(self, text: str):
        if self._pipe is None:
            from kokoro import KPipeline
            self._pipe = KPipeline(lang_code=self._lang_code)
        chunks = []
        for _g, _p, audio in self._pipe(text, voice=self.voice_name):
            a = audio.numpy() if hasattr(audio, "numpy") else np.asarray(audio)
            chunks.append(a.astype(np.float32))
        return np.concatenate(chunks), 24000


class EdgeTTSAdapter:
    name = "edge"

    def __init__(self, voice: str, version: str):
        self.voice_name = voice
        self.component_version = version

    def synth(self, text: str):
        import asyncio

        import edge_tts
        import soundfile as sf
        with tempfile.TemporaryDirectory() as td:
            mp3, wav = Path(td) / "t.mp3", Path(td) / "t.wav"

            async def run():
                await edge_tts.Communicate(text, self.voice_name).save(str(mp3))
            asyncio.run(run())
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3),
                            "-ac", "1", "-ar", "24000", str(wav)], check=True)
            data, sr = sf.read(wav, dtype="float32")
            return data, sr


class DummyAdapter:
    """A short tone whose pitch depends on the text. For trial runs only."""
    name = "dummy"
    component_version = "dummy/v1"

    def synth(self, text: str):
        sr = 24000
        seconds = min(3.0, 0.4 + 0.03 * len(text))
        t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
        freq = 220 + (sum(map(ord, text)) % 220)
        return (0.2 * np.sin(2 * np.pi * freq * t)).astype(np.float32), sr


ENGINES = ("profile", "piper", "kokoro", "edge", "dummy")


def get_adapter(profile, engine: str = "profile", voices_dir: Path | None = None):
    """The engine a language's profile asks for, or an explicit override."""
    sp = dict(profile.speech)
    if engine in ("", "profile", None):
        engine = sp.get("adapter", "dummy")
    elif engine == "edge" and sp.get("adapter") != "edge" and sp.get("fallback"):
        sp = dict(sp["fallback"])                  # the profile's named fallback voice
    if engine == "dummy":
        return DummyAdapter()
    if engine == "piper":
        from paths import VOICES
        return PiperAdapter(sp["voice"], sp.get("version", f"piper/{sp['voice']}/v1"),
                            voices_dir or VOICES, float(sp.get("lengthScale", 1.0)))
    if engine == "kokoro":
        return KokoroAdapter(sp.get("voice", "ff_siwis"),
                             sp.get("version", "kokoro-82M/ff_siwis/v1"),
                             sp.get("lang_code", "f"))
    if engine == "edge":
        return EdgeTTSAdapter(sp["voice"], sp.get("version", f"edge-tts/{sp['voice']}/v1"))
    raise SystemExit(f"unknown speech engine: {engine}")
