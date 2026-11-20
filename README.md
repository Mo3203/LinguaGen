# language_system

Study material for a language, produced from a word list, and an offline study
application that installs on a phone. French is finished. German is set up.

---

## How the system works

Production happens on one page. Open it on Colab with
`notebooks/00_production.ipynb` (Runtime, then Run all), choose the language,
press **Start**. Read `docs/PRODUCTION.md` for the steps.

To see where a language stands from the command line:

    python bin/status.py --lang de

---

## Where things live

    bin/            every command; bin/produce.py runs them all in order
    languages/      one profile per language: fr.json, de.json
    data/<code>/    vocab.csv and sentences.csv, the only human input
    app/            the study application (app/dist is the built version)
    notebooks/      00_production.ipynb, the production page on Colab
    docs/           PRODUCTION.md (how to produce), LANGUAGES.md (how a
                    language is described)
    work/           generated material; on Colab this is your Drive folder

Generated material for each language is kept apart:

    <generated>/build/...        French, where it has always been
    <generated>/de/build/...     German
    <generated>/de/builds/       the laptop and phone builds

---

## The stages

    python bin/produce.py --lang de      all of them, skipping finished work

    1  validate.py            dataset check
    2  generate_scripts.py    scene descriptions
    3  make_audio.py          sentence recordings
    4  make_vocab_audio.py    word recordings
    5  make_images.py         illustrations
    6  build_units.py         study units (practice track and two videos)
    7  export_units_web.py    web content for the application
    8  make_builds.py         laptop build and phone build
    9  publish.py             phone build to Netlify

Every command accepts `--lang <code>`. Every stage is resumable.
