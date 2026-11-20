#!/usr/bin/env python3
"""Phase 3b: copy downloaded images into build/images/ and verify coverage.
Usage: python bin/import_images.py --lang de ~/Downloads/images
(Only needed if you make pictures outside the production page.)"""
import json, shutil, sys
from pathlib import Path
from paths import COLAB, IMAGES, REPORTS, SCRIPTS_JSON
from cache import cache_key
from export_prompts import COMPONENT_VERSION

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: import_images.py <downloaded-folder>")
    src = Path(sys.argv[1]).expanduser()
    if not src.is_dir():
        raise SystemExit(f"not a folder: {src}")
    copied = present = 0
    for png in src.glob("*.png"):
        dst = IMAGES / png.name
        stand_in = IMAGES / f"{png.stem}.placeholder"
        if dst.exists() and dst.stat().st_size > 0 and not stand_in.exists():
            present += 1
        else:
            shutil.copy2(png, dst); copied += 1
            stand_in.unlink(missing_ok=True)
    missing, style, scenes = {}, None, 0
    for path in sorted(SCRIPTS_JSON.glob("*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        style = d["style_prefix"]
        for w in d["words"]:
            for sc in w["scenes"]:
                scenes += 1
                key = cache_key(sc["visual_prompt"], COMPONENT_VERSION)
                p = IMAGES / f"{key}.png"
                if not (p.exists() and p.stat().st_size > 0) or (IMAGES / f"{key}.placeholder").exists():
                    missing.setdefault(key, {"key": key, "prompt": sc["visual_prompt"]})
    lines = [f"copied {copied}, already present {present}",
             f"coverage: {scenes - sum(1 for _ in missing)}"]
    if missing:
        (COLAB / "prompts_missing.json").write_text(json.dumps(
            {"component_version": COMPONENT_VERSION, "style_prefix": style,
             "prompts": sorted(missing.values(), key=lambda p: p["key"])},
            ensure_ascii=False, indent=1), encoding="utf-8")
        msg = f"MISSING {len(missing)} image(s) — upload colab/prompts_missing.json to fill gaps"
        print(f"copied {copied}, already present {present}\n{msg}")
        (REPORTS / "images_status.txt").write_text(msg + "\n", encoding="utf-8")
        sys.exit(1)
    msg = f"coverage complete: all {scenes} scenes have images. Phase 3 done."
    print(f"copied {copied}, already present {present}\n{msg}")
    (REPORTS / "images_status.txt").write_text(msg + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
