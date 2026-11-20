#!/usr/bin/env python3
"""Scene descriptions: dataset -> build/scripts/<topic>.json.

Each word gets an intro line and one picture description per sentence. Two ways
to write them:

    --engine model    a local language model through Ollama (default).
                      One word per call; each word is cached, so an
                      interrupted run resumes.
    --engine simple   no model: the picture description is built from the
                      English sentence. Instant; good for trials, and a
                      reasonable fallback.

    python bin/generate_scripts.py --lang de                 every topic
    python bin/generate_scripts.py --lang de greetings time  some topics
    python bin/generate_scripts.py --lang de --engine simple

The model's address comes from OLLAMA_HOST (default http://localhost:11434).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import pandas as pd
import requests

from cache import cache_key
from language import PROFILE as P
from paths import BUILD, DATA, SCRIPTS_JSON
from schema import BANNED_IN_PROMPTS, Scene, UnitScript, WordBlock

GEN_CACHE = BUILD / "scriptgen"
GEN_CACHE.mkdir(parents=True, exist_ok=True)
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
if not OLLAMA_HOST.startswith("http"):
    OLLAMA_HOST = "http://" + OLLAMA_HOST
MODEL = os.environ.get("LANGSYS_MODEL", "llama3.1:8b")
MAX_RETRIES = 4

LANGUAGE_NAME = P.prompt.get("languageName", P.name)
STYLE_PREFIX = P.prompt.get(
    "stylePrefix",
    f"Warm watercolor illustration, soft natural light, {P.prompt.get('styleSetting', 'everyday life')}, "
    "consistent flat-color palette, no text or letters in the image")
MODEL_VERSION = P.prompt.get("scriptVersion", f"{MODEL}/prompt-v1-{P.code}")
PROMPT_VERSION = MODEL_VERSION.split("/", 1)[-1]
SIMPLE_VERSION = "simple/v1"

SYSTEM_PROMPT = f"""You write image prompts and an intro line for ONE {LANGUAGE_NAME} \
vocabulary word used in a learning video. You receive the word and its three \
example sentences. Respond with ONLY valid JSON, no markdown, exactly:
{{"intro_fr":"...","intro_en":"...","scenes":[{{"sentence_id":"s_0001",\
"visual_prompt":"..."}},{{"sentence_id":"s_0002","visual_prompt":"..."}},\
{{"sentence_id":"s_0003","visual_prompt":"..."}}]}}
Rules:
- Provide a visual_prompt for EVERY sentence_id given, in the same order.
- intro_fr: one short natural {LANGUAGE_NAME} line introducing the word (<=12 words).
- intro_en: its English translation.
- visual_prompt: a CONCRETE photographable scene depicting that sentence's
  meaning (people, places, objects, actions), 20-60 words. Never depict text,
  letters, or abstract ideas. Family-friendly, culturally {LANGUAGE_NAME} where natural."""


def est_duration(text):
    return round(min(20.0, max(2.0, 1.2 + 0.055 * len(text))), 1)


def _clean_prompt(text: str) -> str:
    low = text
    for b in BANNED_IN_PROMPTS:
        low = low.replace(b, "").replace(b.capitalize(), "")
    return " ".join(low.split())


# ------------------------------------------------------------------ engines
def simple_word(word, ws):
    """No model: describe the scene from the English sentence."""
    prompts = {}
    for r in ws.itertuples():
        scene = _clean_prompt(str(r.english_sentence).strip().rstrip("?!."))
        prompts[r.id] = (f"An everyday scene that shows this moment: {scene}. "
                         f"Real people, a real place and ordinary objects, "
                         f"{P.prompt.get('styleSetting', 'everyday life')}.")[:390]
    first = ws.iloc[0]
    spoken = P.citation_form(word["vocab"], word["pos"], word["gender"])
    return {"intro_fr": f"{spoken}: {first.target_sentence}"[:118],
            "intro_en": f"{word['meaning']}: {first.english_sentence}"[:118],
            "prompts": prompts}


def llm_call(word, sentences, feedback):
    user = json.dumps({"vocab": word["vocab"], "meaning": word["meaning"],
                       "sentences": sentences}, ensure_ascii=False)
    if feedback:
        user += f"\n\nPrevious output was invalid: {feedback}\nReturn corrected JSON only."
    r = requests.post(f"{OLLAMA_HOST}/api/chat", json={
        "model": MODEL, "format": "json", "stream": False,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                     {"role": "user", "content": user}],
        "options": {"temperature": 0.4}}, timeout=300)
    r.raise_for_status()
    return json.loads(r.json()["message"]["content"])


def model_word(word, ws):
    payload = "\n".join(ws.target_sentence)
    key = cache_key(payload, MODEL_VERSION)
    cpath = GEN_CACHE / f"{word['id']}_{key}.json"
    if cpath.exists():
        return json.loads(cpath.read_text(encoding="utf-8"))
    sent_input = [{"sentence_id": r.id, "register": r.register, "fr": r.target_sentence}
                  for r in ws.itertuples()]
    ids = list(ws.id)
    feedback = None
    for _ in range(MAX_RETRIES):
        try:
            g = llm_call(word, sent_input, feedback)
            prompts = {sc["sentence_id"]: sc["visual_prompt"] for sc in g["scenes"]}
            miss = [i for i in ids if i not in prompts]
            if miss:
                raise ValueError(f"missing visual_prompt for {miss}")
            for k in ("intro_fr", "intro_en"):
                if not g.get(k):
                    raise ValueError(f"missing {k}")
            for i in ids:
                if any(b in prompts[i].lower() for b in BANNED_IN_PROMPTS):
                    raise ValueError(f"visual_prompt for {i} must depict a concrete scene")
                if not (20 <= len(prompts[i]) <= 400):
                    raise ValueError(f"visual_prompt for {i} must be 20 to 400 characters")
            out = {"intro_fr": g["intro_fr"][:120], "intro_en": g["intro_en"][:120],
                   "prompts": prompts}
            cpath.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
            return out
        except requests.ConnectionError:
            raise
        except Exception as e:
            feedback = str(e)[:300]
    raise RuntimeError(f"word {word['id']} ({word['vocab']}) failed: {feedback}")


# ------------------------------------------------------------------ units
def build_unit(topic, v, s, engine):
    version = MODEL_VERSION if engine == "model" else SIMPLE_VERSION
    words = v[v.topic == topic].sort_values("id")
    sents = s[s.vocab_id.isin(words.id)].sort_values("id")
    unit_key = cache_key("\n".join(sents.target_sentence), version)
    out_path = SCRIPTS_JSON / f"{topic}.json"
    if out_path.exists():
        old = json.loads(out_path.read_text(encoding="utf-8"))
        if old.get("cache_key") == unit_key:
            print(f"  SKIP  {topic}")
            return
        if engine == "simple" and old.get("engine", "model") == "model":
            print(f"  KEEP  {topic}  (written by the language model; not replaced by simple ones)")
            return
    blocks = []
    for n, w in enumerate(words.itertuples(), 1):
        ws = sents[sents.vocab_id == w.id]
        word = {"id": w.id, "vocab": w.vocab, "meaning": w.english_meaning,
                "pos": w.pos, "gender": getattr(w, "gender", None)}
        g = model_word(word, ws) if engine == "model" else simple_word(word, ws)
        scenes = [Scene(sentence_id=r.id, register=r.register, fr=r.target_sentence,
                        en=r.english_sentence, visual_prompt=g["prompts"][r.id],
                        est_duration_s=est_duration(r.target_sentence)) for r in ws.itertuples()]
        blocks.append(WordBlock(vocab_id=w.id, vocab=w.vocab, english_meaning=w.english_meaning,
                                pos=w.pos, intro_fr=g["intro_fr"], intro_en=g["intro_en"],
                                scenes=scenes))
        if engine == "model":
            print(f"    {topic}: {n}/{len(words)} words", flush=True)
    unit = UnitScript(topic=topic, prompt_version=version.split("/", 1)[-1],
                      style_prefix=STYLE_PREFIX, words=blocks)
    d = unit.model_dump()
    d["cache_key"] = unit_key
    d["engine"] = engine
    d["language"] = P.code
    tmp = out_path.with_suffix(".part")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(out_path)
    print(f"  OK    {topic}  ({unit.scene_count()} scenes)")


def model_reachable() -> bool:
    try:
        requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3).raise_for_status()
        return True
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("topics", nargs="*")
    ap.add_argument("--topics", dest="topics_opt", nargs="*", default=None)
    ap.add_argument("--engine", choices=["model", "simple"], default="model")
    a = ap.parse_args()

    v = pd.read_csv(DATA / "vocab.csv", encoding="utf-8")
    s = pd.read_csv(DATA / "sentences.csv", encoding="utf-8")
    topics = a.topics or a.topics_opt or sorted(v.topic.unique())
    unknown = sorted(set(topics) - set(v.topic))
    if unknown:
        raise SystemExit(f"not topics in the dataset: {unknown}")
    if a.engine == "model" and not model_reachable():
        raise SystemExit(f"The language model is not reachable at {OLLAMA_HOST}.\n"
                         "Start Ollama, or use --engine simple.")
    label = MODEL_VERSION if a.engine == "model" else SIMPLE_VERSION
    print(f"[scene descriptions] {P.name}, {len(topics)} topic(s), {label}")
    failures = []
    for t in topics:
        try:
            build_unit(t, v, s, a.engine)
        except RuntimeError as e:
            print(f"  FAIL  {e}")
            failures.append(t)
        except requests.ConnectionError:
            raise SystemExit(f"Lost the language model at {OLLAMA_HOST}. Run again to resume.")
    if failures:
        print(f"\nfailed: {failures}. Run again; finished words are kept.")
        sys.exit(1)


if __name__ == "__main__":
    main()
