#!/usr/bin/env python3
"""Review generated unit scripts before committing more machine time.

Usage:
    python scripts/inspect_scripts.py                 # all generated units
    python scripts/inspect_scripts.py basic_adjectives verbs body_health

For each word it prints the intro line and, per scene, the sentence next
to its visual prompt, with automatic FLAGS for the known failure modes so you
can skim for problems instead of reading everything.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

from paths import SCRIPTS_JSON as SCRIPTS_DIR, REPORTS

# heuristics for prompts that would make bad images
BANNED = ("abstract", "the word", "text", "letters", "concept", "symboliz")
MIN_WORDS = 8


def flags(prompt: str) -> list[str]:
    f = []
    low = prompt.lower()
    if len(prompt.split()) < MIN_WORDS:
        f.append("TOO-SHORT")
    if any(b in low for b in BANNED):
        f.append("ABSTRACT/TEXT")
    if not prompt.strip():
        f.append("EMPTY")
    return f


def main() -> None:
    units = sys.argv[1:]
    files = ([SCRIPTS_DIR / f"{u}.json" for u in units] if units
             else sorted(SCRIPTS_DIR.glob("*.json")))

    total_scenes = flagged = 0
    for path in files:
        if not path.exists():
            print(f"!! not generated yet: {path.name}\n")
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        print("=" * 78)
        print(f"UNIT: {d['topic']}   ({len(d['words'])} words, {sum(len(w['scenes']) for w in d['words'])} scenes)")
        print(f"style: {d['style_prefix']}")
        print("=" * 78)
        for w in d["words"]:
            print(f"\n[{w['vocab_id']}] {w['vocab']} — {w['english_meaning']}  ({w['pos']})")
            print(f"   intro: {w['intro_fr']}  /  {w['intro_en']}")
            for sc in w["scenes"]:
                total_scenes += 1
                fl = flags(sc["visual_prompt"])
                if fl:
                    flagged += 1
                mark = ("  <<< " + ",".join(fl)) if fl else ""
                print(f"   • [{sc['register'][:6]}] {sc['fr']}")
                print(f"       → {sc['visual_prompt']}{mark}")
        print()

    print("#" * 78)
    print(f"SUMMARY: {total_scenes} scenes reviewed, {flagged} auto-flagged "
          f"({100 * flagged / total_scenes:.1f}% need a look)" if total_scenes else "no scenes found")
    print("Judge the rest by eye: is each prompt a concrete scene that matches the sentence?")
    # full report to file as well
    import io, contextlib  # (report is what was just printed)


if __name__ == "__main__":
    main()
