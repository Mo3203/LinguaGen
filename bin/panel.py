#!/usr/bin/env python3
"""The production page: produce a language's material, check it, publish it.

    python bin/panel.py                   open on this machine
    python bin/panel.py --share           also give a web link (used on Colab),
                                          protected by a password

Tabs:
    Production        choose a language and press Start. Every stage runs in
                      order and skips what is already finished.
    Progress          where each stage stands.
    Check the output  listen to recordings, look at pictures, watch a unit.
    Single stage      run one stage by itself, for when you know what you want.

The page holds no state of its own. It reads the files and runs the same
commands in bin/, so it can never disagree with the command line.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import secrets
import shutil
import signal
import subprocess
import sys
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BIN = REPO / "bin"
WORK = Path(os.environ.get("LANGSYS_WORK", REPO / "work")).expanduser()
sys.path.insert(0, str(BIN))

_running: dict = {"proc": None}
_lock = threading.Lock()


# ------------------------------------------------------------------ machine
def capabilities() -> dict:
    caps = {"ffmpeg": shutil.which("ffmpeg") is not None, "gpu": False, "ollama": False,
            "colab": "google.colab" in sys.modules or Path("/content").is_dir(),
            "netlify": bool(os.environ.get("NETLIFY_AUTH_TOKEN"))}
    try:
        import torch
        caps["gpu"] = bool(torch.cuda.is_available() or
                           (getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()))
    except Exception:
        pass
    try:
        import requests
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        if not host.startswith("http"):
            host = "http://" + host
        requests.get(f"{host}/api/tags", timeout=1.5).raise_for_status()
        caps["ollama"] = True
    except Exception:
        pass
    return caps


def machine_summary(caps: dict) -> str:
    where = "Cloud session" if caps["colab"] else "This computer"
    bits = ["graphics processor available" if caps["gpu"] else "no graphics processor",
            "language model running" if caps["ollama"] else "language model not running",
            "ffmpeg present" if caps["ffmpeg"] else "ffmpeg missing",
            "Netlify token set" if caps["netlify"] else "no Netlify token"]
    return f"**{where}:** " + ", ".join(bits)


# ------------------------------------------------------------------ languages
def languages() -> list[tuple[str, str]]:
    out = []
    for p in sorted((REPO / "languages").glob("*.json")):
        try:
            out.append((json.loads(p.read_text(encoding="utf-8")).get("name", p.stem), p.stem))
        except Exception:
            out.append((p.stem, p.stem))
    return out or [("French", "fr")]


def profile(lang: str) -> dict:
    try:
        return json.loads((REPO / "languages" / f"{lang}.json").read_text(encoding="utf-8"))
    except Exception:
        return {"code": lang, "name": lang}


def lang_env(lang: str) -> dict:
    return {**os.environ, "LANGSYS_LANG": lang, "LANGSYS_WORK": str(WORK), "PYTHONUNBUFFERED": "1"}


def layout(lang: str) -> dict:
    """Folders for a language, computed the same way the commands do."""
    code = ("import json, paths; L = paths.layout(%r); "
            "print(json.dumps({k: str(v) for k, v in L.items()}))" % lang)
    try:
        out = subprocess.run([sys.executable, "-c", code], cwd=str(BIN), env=lang_env(lang),
                             capture_output=True, text=True, timeout=30)
        return json.loads(out.stdout.strip().splitlines()[-1])
    except Exception:
        return {"build": str(WORK / lang / "build"), "lang_root": str(WORK / lang)}


def topics(lang: str) -> list[str]:
    data = REPO / "data" / lang
    if not (data / "vocab.csv").exists() and lang == "fr":
        data = REPO / "data"
    try:
        with (data / "vocab.csv").open(encoding="utf-8") as f:
            return sorted({r["topic"] for r in csv.DictReader(f) if r.get("topic")})
    except Exception:
        return []


# ------------------------------------------------------------------ progress
STAGES = [("dataset", "Dataset"), ("scripts", "Scene descriptions"), ("audio", "Sentence recordings"),
          ("vocab_audio", "Word recordings"), ("images", "Illustrations"),
          ("units", "Study units"), ("export", "Web content")]


def progress_markdown(lang: str) -> str:
    try:
        out = subprocess.run([sys.executable, str(BIN / "status.py"), "--json"], cwd=str(REPO),
                             env=lang_env(lang), capture_output=True, text=True, timeout=600)
        st = json.loads(out.stdout.strip().splitlines()[-1])
    except Exception as e:
        return f"Could not read progress: {e}"
    lines = [f"### {st['name']}", f"Generated material: `{st['root']}`", "",
             "| Stage | Progress | |", "|---|---|---|"]
    nxt = None
    for key, name in STAGES:
        have, need = st["stages"].get(key, [0, 1])
        pct = int(100 * min(have, need) / max(1, need))
        note = ""
        if key == "images" and st["stages"].get("images_standin"):
            note = f"{st['stages']['images_standin']} stand-in pictures to replace"
        if have < need and nxt is None:
            nxt = name
        lines.append(f"| **{name}** | {pct} percent ({have} of {need}) | {note} |")
    lines += ["", f"**Next unfinished stage:** {nxt}" if nxt else "**Everything is built.**"]
    return "\n".join(lines)


# ------------------------------------------------------------------ running
def stream(cmd: list[str], lang: str, header: str):
    """Run a command, yielding the growing log. One command at a time."""
    with _lock:
        if _running["proc"] and _running["proc"].poll() is None:
            yield "Something is already running. Stop it first, or wait for it to finish."
            return
        log = [header, ""]
        yield "\n".join(log)
        try:
            proc = subprocess.Popen(cmd, cwd=str(REPO), env=lang_env(lang), stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, bufsize=1,
                                    start_new_session=True)
        except Exception as e:
            yield "\n".join(log + [f"could not start: {e}"])
            return
        _running["proc"] = proc
    for line in proc.stdout:
        log.append(line.rstrip())
        if len(log) > 600:
            log = log[:2] + ["(earlier lines trimmed)"] + log[-450:]
        yield "\n".join(log)
    code = proc.wait()
    _running["proc"] = None
    log += ["", "Finished." if code == 0 else
            ("Stopped." if code in (-signal.SIGTERM, -signal.SIGKILL) else f"Stopped with code {code}.")]
    yield "\n".join(log)


def stop_running() -> str:
    proc = _running.get("proc")
    if not proc or proc.poll() is not None:
        return "Nothing is running."
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except Exception:
        proc.terminate()
    return "Stopping. Finished work is kept; press Start again to continue."


def produce(lang, scope, chosen, scripts, speech, images, phone_videos, publish, site):
    cmd = [sys.executable, "-u", str(BIN / "produce.py"), "--lang", lang,
           "--scripts", scripts, "--speech", speech, "--images", images,
           "--phone-videos", phone_videos]
    if scope == "trial":
        pick = chosen or topics(lang)[:1]
        if not pick:
            yield "No topics found for this language."
            return
        cmd += ["--topics", *pick]
    if publish:
        cmd += ["--publish"]
        if site.strip():
            cmd += ["--site", site.strip()]
    yield from stream(cmd, lang, "$ python bin/produce.py " + " ".join(cmd[3:]))


def run_single(script: str, lang: str, extra: str):
    cmd = [sys.executable, "-u", str(BIN / script), *extra.split()]
    yield from stream(cmd, lang, f"$ python bin/{script} {extra}".rstrip())


# ------------------------------------------------------------------ previews
def sample_audio(lang: str):
    d = Path(layout(lang)["build"]) / "audio"
    files = list(d.glob("*.wav"))[:500] if d.is_dir() else []
    if not files:
        return None, "No recordings yet."
    f = random.choice(files)
    return str(f), f"One of {len(list(d.glob('*.wav')))} recordings."


def sample_images(lang: str):
    d = Path(layout(lang)["build"]) / "images"
    files = [p for p in d.glob("*.png") if not (d / f"{p.stem}.placeholder").exists()][:500] \
        if d.is_dir() else []
    if not files:
        return [], "No finished pictures yet."
    return [str(p) for p in random.sample(files, min(6, len(files)))], f"{len(files)} finished pictures."


def unit_list(lang: str) -> list[str]:
    d = Path(layout(lang)["build"]) / "units"
    if not d.is_dir():
        return []
    return sorted(p.name for p in d.iterdir() if p.is_dir() and not p.name.startswith("_"))


def unit_preview(lang: str, unit: str):
    if not unit:
        return None, None, "Choose a unit."
    d = Path(layout(lang)["build"]) / "units" / unit
    videos = sorted(d.glob("*_bilingual.mp4")) or sorted(d.glob("*.mp4"))
    note = []
    sheet = d / "study_sheet.csv"
    if sheet.exists():
        with sheet.open(encoding="utf-8") as f:
            words = sorted({r["word"] for r in csv.DictReader(f) if r.get("word")})
        note.append(f"**{unit}**: {len(words)} words: {', '.join(words)}")
    sig = d / ".sig"
    if sig.exists() and "+provisional" in sig.read_text():
        note.append("Built with trial material (test tones or stand-in pictures). "
                    "It is rebuilt automatically when the final material exists.")
    audio = d / "audio.wav"
    return (str(videos[0]) if videos else None, str(audio) if audio.exists() else None,
            "\n\n".join(note) or "Nothing built for this unit yet.")


# ------------------------------------------------------------------ page
GUIDE = """
### What Start does

It runs every stage in order for the chosen language, and skips anything
already finished. Stopping part-way loses nothing: press Start again and it
continues.

1. **Dataset check.** Stops early if the word list has a problem.
2. **Scene descriptions.** A picture description for every sentence.
3. **Sentence recordings** and 4. **Word recordings**, in the language's voice.
5. **Illustrations**, one picture per sentence.
6. **Study units**: practice track and two videos per unit of five words.
7. **Web content** for the study application.
8. **Builds**: a laptop build and a phone build.
9. **Publish** the phone build, if ticked.

### Choices

**Scope.** Start with a trial on one topic. Check it in *Check the output*.
Then run everything.

**Scene descriptions.** *Language model* writes a fitting picture description
for every sentence; it needs Ollama running. *Simple* builds the description
from the English sentence; instant, and good enough to start.

**Voice.** *The language's voice* is the real one. *Test tones* check the
line quickly without a voice; they are replaced automatically later.

**Pictures.** *Real pictures* need a graphics processor (a Colab GPU
session). *Stand-in pictures* let everything else be finished now; they are
replaced, and the affected units rebuilt, the next time real pictures are made.

### Where things go

Everything for a language is kept in its own folder under the generated
material, shown in *Progress*. French keeps its existing folders.
"""


def build_ui():
    import gradio as gr
    caps = capabilities()
    langs = languages()
    codes = [c for _, c in langs]
    default = os.environ.get("LANGSYS_LANG", "de" if "de" in codes else codes[0])
    if default not in codes:
        default = codes[0]

    def voice_choices(lang):
        sp = profile(lang).get("speech", {})
        return [(f"The language's voice ({sp.get('voice', sp.get('adapter', 'profile'))})", "profile"),
                ("Test tones", "dummy")]

    with gr.Blocks(title="Production") as ui:
        gr.Markdown("# Production")
        gr.Markdown(machine_summary(caps))
        with gr.Row():
            lang = gr.Dropdown(langs, value=default, label="Language", scale=2)
            refresh = gr.Button("Refresh", scale=0)

        with gr.Tab("Production"):
            with gr.Row():
                scope = gr.Radio([("A trial on chosen topics", "trial"),
                                  ("Everything not yet finished", "all")],
                                 value="trial", label="Scope")
                chosen = gr.Dropdown(topics(default), value=topics(default)[:1], multiselect=True,
                                     label="Topics for the trial")
            with gr.Row():
                scripts = gr.Radio([("Language model", "model"), ("Simple", "simple")],
                                   value="model" if caps["ollama"] else "simple",
                                   label="Scene descriptions")
                speech = gr.Radio(voice_choices(default), value="profile", label="Voice")
                images = gr.Radio([("Real pictures", "sdxl"), ("Stand-in pictures", "placeholder"),
                                   ("Leave as they are", "skip")],
                                  value="sdxl" if caps["gpu"] else "placeholder", label="Pictures")
            with gr.Row():
                phone_videos = gr.Radio([("None", "none"), ("Bilingual", "bilingual"),
                                         ("Language only", "target"), ("Both", "both")],
                                        value="none", label="Videos in the phone build")
                publish = gr.Checkbox(value=False, label="Publish when finished",
                                      interactive=caps["netlify"],
                                      info=None if caps["netlify"] else
                                      "Needs NETLIFY_AUTH_TOKEN; see docs/PRODUCTION.md")
                site = gr.Textbox(value=profile(default).get("deploy", {}).get("site", ""),
                                  label="Netlify site name")
            with gr.Row():
                start = gr.Button("Start", variant="primary")
                stop = gr.Button("Stop")
            stop_note = gr.Markdown()
            log = gr.Textbox(label="Progress log", lines=22, max_lines=22, autoscroll=True)

        with gr.Tab("Progress"):
            status = gr.Markdown(progress_markdown(default))

        with gr.Tab("Check the output"):
            with gr.Row():
                a_btn = gr.Button("Play a random recording")
                i_btn = gr.Button("Show sample pictures")
            a_out = gr.Audio(label="Recording", type="filepath")
            a_note = gr.Markdown()
            i_out = gr.Gallery(label="Pictures", columns=3)
            i_note = gr.Markdown()
            gr.Markdown("### A finished unit")
            with gr.Row():
                unit_pick = gr.Dropdown(unit_list(default), label="Unit", scale=2)
                u_btn = gr.Button("Open", scale=0)
            u_video = gr.Video(label="Unit video")
            u_audio = gr.Audio(label="Practice track", type="filepath")
            u_note = gr.Markdown()

        with gr.Tab("Single stage"):
            gr.Markdown("Run one stage by itself. Production runs all of them for you.")
            with gr.Row():
                stage_pick = gr.Dropdown(
                    [("Dataset check", "validate.py"), ("Scene descriptions", "generate_scripts.py"),
                     ("Sentence recordings", "make_audio.py"), ("Word recordings", "make_vocab_audio.py"),
                     ("Illustrations", "make_images.py"), ("Study units", "build_units.py"),
                     ("Layout preview", "preview.py"), ("Web content", "export_units_web.py"),
                     ("Builds", "make_builds.py"), ("Publish", "publish.py"), ("Status", "status.py")],
                    value="status.py", label="Stage")
                extra = gr.Textbox(label="Options", placeholder="--topics greetings", scale=2)
            s_run = gr.Button("Run", variant="primary")
            s_log = gr.Textbox(label="Output", lines=18, max_lines=18, autoscroll=True)

        with gr.Tab("Guide"):
            gr.Markdown(GUIDE)

        def on_lang(l):
            t = topics(l)
            return (progress_markdown(l), gr.update(choices=t, value=t[:1]),
                    gr.update(choices=unit_list(l), value=None),
                    gr.update(choices=voice_choices(l), value="profile"),
                    profile(l).get("deploy", {}).get("site", ""))

        outs = [status, chosen, unit_pick, speech, site]
        lang.change(on_lang, lang, outs)
        refresh.click(on_lang, lang, outs)
        start.click(produce, [lang, scope, chosen, scripts, speech, images, phone_videos, publish, site],
                    log).then(lambda l: (progress_markdown(l), gr.update(choices=unit_list(l))),
                              lang, [status, unit_pick])
        stop.click(stop_running, None, stop_note)
        s_run.click(run_single, [stage_pick, lang, extra], s_log)
        a_btn.click(sample_audio, lang, [a_out, a_note])
        i_btn.click(sample_images, lang, [i_out, i_note])
        u_btn.click(unit_preview, [lang, unit_pick], [u_video, u_audio, u_note])
    return ui


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--share", action="store_true", help="also give a web link")
    ap.add_argument("--port", type=int, default=7860)
    a = ap.parse_args()
    caps = capabilities()
    print(machine_summary(caps).replace("**", ""))
    print(f"repository: {REPO}")
    print(f"generated:  {WORK}")

    import gradio as gr
    share = a.share or caps["colab"]
    kw = dict(share=share, server_port=a.port,
              server_name="0.0.0.0" if caps["colab"] else "127.0.0.1",
              allowed_paths=[str(WORK)])
    if share:
        password = os.environ.get("LANGSYS_PANEL_PASSWORD") or secrets.token_urlsafe(6)
        kw["auth"] = ("studio", password)
        print(f"sign-in: user studio, password {password}")
    if int(gr.__version__.split(".")[0]) >= 6:
        kw["theme"] = gr.themes.Soft()
    ui = build_ui()
    ui.queue(default_concurrency_limit=2)
    try:
        ui.launch(**kw)
    except TypeError:
        kw.pop("theme", None)
        ui.launch(**kw)
    return 0


if __name__ == "__main__":
    sys.exit(main())
