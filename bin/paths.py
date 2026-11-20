"""Every folder in the project, for any language, defined in one place.

Two roots:

    REPO       this repository: code, datasets, language profiles
    WORK       generated material (recordings, images, videos). Set it with the
               LANGSYS_WORK environment variable; defaults to REPO/work.

The language comes from `--lang <code>` on the command, or LANGSYS_LANG
(default fr). Generated material for a
language lives in its own folder so languages never mix:

    WORK/<lang>/build/...        for every language
    WORK/build/...               French material made before this layout
                                 existed is still found where it is

Datasets live in REPO/data/<lang>/. French data kept directly in REPO/data/
is still found.

Audio references stored in the datasets (audio_ref) are relative to
LANG_ROOT, so "build/audio/<key>.wav" always means LANG_ROOT/build/audio.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

def _take_lang_option() -> str | None:
    """Accept `--lang de` on any command. Removed from sys.argv so the
    command's own options are unaffected."""
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--lang" and i + 1 < len(sys.argv):
            value = sys.argv[i + 1]
            del sys.argv[i:i + 2]
            return value
        if arg.startswith("--lang="):
            del sys.argv[i]
            return arg.split("=", 1)[1]
    return None


_opt = _take_lang_option()
if _opt:
    os.environ["LANGSYS_LANG"] = _opt       # later steps started from here inherit it

REPO = Path(__file__).resolve().parents[1]
WORK = Path(os.environ.get("LANGSYS_WORK", REPO / "work")).expanduser()
LANG = os.environ.get("LANGSYS_LANG", "fr").strip().lower() or "fr"


def layout(lang: str) -> dict:
    """All folders for one language. Pure: creates nothing."""
    lang = lang.lower()
    data = REPO / "data" / lang
    if lang == "fr" and not (data / "vocab.csv").exists() and (REPO / "data" / "vocab.csv").exists():
        data = REPO / "data"                       # French data kept at the old place

    lang_root = WORK / lang
    legacy = WORK / "build" / "audio"
    if lang == "fr" and not (lang_root / "build").exists() and legacy.exists():
        lang_root = WORK                           # French material made before per-language folders

    build = lang_root / "build"
    return {
        "lang": lang,
        "data": data,
        "lang_root": lang_root,
        "build": build,
        "scripts": build / "scripts",
        "scriptgen": build / "scriptgen",
        "audio": build / "audio",
        "images": build / "images",
        "units": build / "units",
        "reports": lang_root / "reports",
        "web": lang_root / "web",
        "colab": lang_root / "colab",
        "voices": WORK / "voices",
    }


_L = layout(LANG)
DATA = _L["data"]
LANG_ROOT = _L["lang_root"]
BUILD = _L["build"]
SCRIPTS_JSON = _L["scripts"]
AUDIO = _L["audio"]
IMAGES = _L["images"]
UNITS = _L["units"]
REPORTS = _L["reports"]
WEB = _L["web"]
COLAB = _L["colab"]
VOICES = _L["voices"]
VIDEOS = BUILD / "videos"            # kept for older scripts

# Older scripts resolve audio references against ROOT.
ROOT = LANG_ROOT

for _p in (SCRIPTS_JSON, AUDIO, IMAGES, UNITS, REPORTS, COLAB):
    _p.mkdir(parents=True, exist_ok=True)
