#!/usr/bin/env python3
"""Illustrations: every picture description in build/scripts/ -> build/images/<key>.png

    python bin/make_images.py --lang de                     SDXL-Turbo, needs a graphics processor
    python bin/make_images.py --lang de --topics greetings  only some topics
    python bin/make_images.py --lang de --engine placeholder
                                                            plain stand-in pictures, instant,
                                                            for trial runs; replaced later

Resumable: finished pictures are skipped. Stand-in pictures are marked with a
.placeholder file beside them, and a real run replaces them.

Same model and settings as the earlier image notebook, so pictures made either
way are interchangeable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time

from cache import cache_key
from export_prompts import COMPONENT_VERSION
from language import PROFILE as P
from paths import IMAGES, REPORTS, SCRIPTS_JSON

MODEL_ID = "stabilityai/sdxl-turbo"
W, H, STEPS = 1024, 576, 4


def wanted(topics: list[str] | None) -> tuple[list[dict], str]:
    scripts = sorted(SCRIPTS_JSON.glob("*.json"))
    if topics:
        scripts = [p for p in scripts if p.stem in topics]
    if not scripts:
        raise SystemExit("no scene descriptions yet. Run the scene description stage first.")
    seen, style = {}, None
    for path in scripts:
        d = json.loads(path.read_text(encoding="utf-8"))
        style = style or d["style_prefix"]
        for w in d["words"]:
            for sc in w["scenes"]:
                key = cache_key(sc["visual_prompt"], COMPONENT_VERSION)
                seen.setdefault(key, {"key": key, "prompt": sc["visual_prompt"]})
    return sorted(seen.values(), key=lambda p: p["key"]), style


def is_done(key: str) -> bool:
    png = IMAGES / f"{key}.png"
    return png.exists() and png.stat().st_size > 0 and not (IMAGES / f"{key}.placeholder").exists()


def placeholder(key: str) -> None:
    from PIL import Image, ImageDraw
    h = hashlib.sha256(key.encode()).digest()
    base = (70 + h[0] % 60, 80 + h[1] % 60, 70 + h[2] % 60)
    img = Image.new("RGB", (W, H), base)
    d = ImageDraw.Draw(img)
    for i in range(0, H, 6):                                  # a quiet vertical gradient
        f = i / H
        d.line([(0, i), (W, i)], fill=tuple(int(c * (1.15 - 0.3 * f)) for c in base))
    d.ellipse([W // 2 - 90, H // 2 - 90, W // 2 + 90, H // 2 + 90],
              outline=(200, 200, 190), width=4)
    img.save(IMAGES / f"{key}.png")
    (IMAGES / f"{key}.placeholder").write_text("stand-in picture; a real image run replaces it\n")


def load_model():
    import torch
    from diffusers import AutoPipelineForText2Image
    if torch.cuda.is_available():
        device, dtype = "cuda", torch.float16
    elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        device, dtype = "mps", torch.float16
    else:
        device, dtype = "cpu", torch.float32
        print("  no graphics processor: this will be very slow (minutes per picture)")
    kw = {"torch_dtype": dtype}
    if dtype == torch.float16:
        kw["variant"] = "fp16"
    pipe = AutoPipelineForText2Image.from_pretrained(MODEL_ID, **kw).to(device)
    pipe.set_progress_bar_config(disable=True)
    print(f"  model ready on {device}")
    return pipe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["sdxl", "placeholder"], default="sdxl")
    ap.add_argument("--topics", nargs="*", default=None)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    items, style = wanted(a.topics)
    todo = [p for p in items if not is_done(p["key"])]
    if a.engine == "placeholder":
        todo = [p for p in todo if not (IMAGES / f"{p['key']}.png").exists()]
    if a.limit:
        todo = todo[:a.limit]
    print(f"[illustrations] {P.name}: {len(items)} needed, {len(items) - len(todo)} ready, "
          f"{len(todo)} to make ({a.engine})")
    if not todo:
        return

    if a.engine == "placeholder":
        for p in todo:
            placeholder(p["key"])
        print(f"  made {len(todo)} stand-in pictures")
    else:
        pipe = load_model()
        t0 = time.time()
        for i, item in enumerate(todo, 1):
            img = pipe(prompt=f"{style}, {item['prompt']}", num_inference_steps=STEPS,
                       guidance_scale=0.0, width=W, height=H).images[0]
            tmp = IMAGES / f"{item['key']}.part.png"
            img.save(tmp)
            tmp.replace(IMAGES / f"{item['key']}.png")
            (IMAGES / f"{item['key']}.placeholder").unlink(missing_ok=True)
            if i % 10 == 0 or i == len(todo):
                rate = i / max(time.time() - t0, 1e-9)
                print(f"  {i}/{len(todo)}  about {(len(todo) - i) / rate / 60:.0f} min left", flush=True)

    ready = sum(is_done(p["key"]) for p in items)
    msg = f"{ready} of {len(items)} illustrations ready"
    (REPORTS / "images_status.txt").write_text(msg + "\n", encoding="utf-8")
    print(msg)


if __name__ == "__main__":
    main()
