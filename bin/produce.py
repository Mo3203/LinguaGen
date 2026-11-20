#!/usr/bin/env python3
"""One command for the whole production line of a language.

    python bin/produce.py --lang de                         everything not yet finished
    python bin/produce.py --lang de --topics greetings      a trial on one topic
    python bin/produce.py --lang de --publish               and put it online

Stages, in order. Each one skips work already done, so running this again
after an interruption simply continues:

    1  Dataset check          bin/validate.py
    2  Scene descriptions     bin/generate_scripts.py
    3  Sentence recordings    bin/make_audio.py
    4  Word recordings        bin/make_vocab_audio.py
    5  Illustrations          bin/make_images.py
    6  Study units            bin/build_units.py, bin/build_study_index.py
    7  Web content            bin/export_units_web.py
    8  Builds                 bin/make_builds.py
    9  Publish (optional)     bin/publish.py

Options:
    --scripts model|simple        how scene descriptions are written (default model)
    --speech profile|dummy        the profile's voice, or test tones (default profile)
    --images sdxl|placeholder|skip   real pictures, stand-ins, or leave as they are
    --phone-videos none|bilingual|target|both   videos carried by the phone build
    --stop-after <stage>          stop after a stage: dataset, scripts, audio, words,
                                  images, units, web, builds
    --publish                     publish the phone build at the end
The production page (bin/panel.py, "Production" tab) runs exactly this.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

BIN = Path(__file__).resolve().parent
STAGE_KEYS = ["dataset", "scripts", "audio", "words", "images", "units", "web", "builds", "publish"]


def plan(a) -> list[tuple[str, str, list[list[str]]]]:
    """(key, title, [commands]) for each stage."""
    topics = ["--topics", *a.topics] if a.topics else []
    speech = ["--engine", a.speech]
    steps = [
        ("dataset", "Dataset check", [["validate.py"]]),
        ("scripts", "Scene descriptions", [["generate_scripts.py", "--engine", a.scripts, *topics]]),
        ("audio", "Sentence recordings", [["make_audio.py", *speech, *topics]]),
        ("words", "Word recordings", [["make_vocab_audio.py", *speech, *topics]]),
    ]
    if a.images != "skip":
        steps.append(("images", "Illustrations", [["make_images.py", "--engine", a.images, *topics]]))
    steps += [
        ("units", "Study units", [["build_units.py", *topics], ["build_study_index.py"]]),
        # always the whole language, so a trial never shrinks what is published
        ("web", "Web content", [["export_units_web.py"]]),
        ("builds", "Builds", [["make_builds.py", "--phone-videos", a.phone_videos]]),
    ]
    if a.publish:
        steps.append(("publish", "Publish", [["publish.py", *(["--site", a.site] if a.site else [])]]))
    if a.stop_after:
        keys = [k for k, _, _ in steps]
        if a.stop_after in keys:
            steps = steps[:keys.index(a.stop_after) + 1]
    return steps


def run(cmd: list[str], env: dict) -> int:
    proc = subprocess.Popen([sys.executable, "-u", str(BIN / cmd[0]), *cmd[1:]], cwd=str(BIN.parent),
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            bufsize=1)
    for line in proc.stdout:
        print("    " + line.rstrip(), flush=True)
    return proc.wait()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lang", default=os.environ.get("LANGSYS_LANG", "fr"))
    ap.add_argument("--topics", nargs="*", default=None)
    ap.add_argument("--scripts", choices=["model", "simple"], default="model")
    ap.add_argument("--speech", choices=["profile", "dummy"], default="profile")
    ap.add_argument("--images", choices=["sdxl", "placeholder", "skip"], default="sdxl")
    ap.add_argument("--phone-videos", default="none",
                    choices=["none", "bilingual", "target", "both"])
    ap.add_argument("--stop-after", choices=STAGE_KEYS, default=None)
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--site", default="")
    a = ap.parse_args()

    env = {**os.environ, "LANGSYS_LANG": a.lang, "PYTHONUNBUFFERED": "1"}
    steps = plan(a)
    started = time.time()
    scope = f"topics {', '.join(a.topics)}" if a.topics else "every topic"
    print(f"PRODUCTION  language {a.lang}, {scope}", flush=True)
    print(f"            scenes {a.scripts}, voice {a.speech}, pictures {a.images}"
          + (", then publish" if a.publish else ""), flush=True)
    for n, (key, title, cmds) in enumerate(steps, 1):
        t0 = time.time()
        print(f"\n[{n}/{len(steps)}] {title}", flush=True)
        for cmd in cmds:
            code = run(cmd, env)
            if code != 0:
                print(f"\nSTOPPED at {title}. Fix the problem shown above and run again;"
                      " finished work is kept.", flush=True)
                return code
        print(f"    done in {time.time() - t0:.0f} s", flush=True)
    print(f"\nFINISHED in {(time.time() - started) / 60:.1f} min", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
