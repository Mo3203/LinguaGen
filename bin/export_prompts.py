#!/usr/bin/env python3
"""Phase 3a: collect all visual prompts into colab/prompts.json for the notebook.
Usage: python bin/export_prompts.py --lang de   (only for making pictures outside the production page)"""
import json
from paths import COLAB, SCRIPTS_JSON
from cache import cache_key

COMPONENT_VERSION = "sdxl-turbo/style-v1"

def main():
    units = sorted(SCRIPTS_JSON.glob("*.json"))
    if not units:
        raise SystemExit("no unit scripts yet — finish Phase 1 first (bin/generate_scripts.py)")
    styles, seen, scenes = set(), {}, 0
    for path in units:
        d = json.loads(path.read_text(encoding="utf-8"))
        styles.add(d["style_prefix"])
        for w in d["words"]:
            for sc in w["scenes"]:
                scenes += 1
                key = cache_key(sc["visual_prompt"], COMPONENT_VERSION)
                seen.setdefault(key, {"key": key, "prompt": sc["visual_prompt"]})
    if len(styles) != 1:
        raise SystemExit("mixed style_prefix across units — regenerate offenders first")
    (COLAB / "prompts.json").write_text(json.dumps(
        {"component_version": COMPONENT_VERSION, "style_prefix": styles.pop(),
         "prompts": sorted(seen.values(), key=lambda p: p["key"])},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"units {len(units)} | scenes {scenes} | unique prompts {len(seen)}")
    print("wrote colab/prompts.json — upload it in the Colab notebook")

if __name__ == "__main__":
    main()
