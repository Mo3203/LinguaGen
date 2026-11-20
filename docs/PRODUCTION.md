# Production

One page produces a language from the word list to a published site. It runs
on Colab because the pictures need a graphics processor. Everything it makes is
written to your Google Drive, in `My Drive/language_system`.

---

## Once: put the code where Colab can find it

1. Upload `language_system_production.zip` to **My Drive** (the top level, as
   the zip file; do not unzip it).
2. Open `notebooks/00_production.ipynb` in Colab. Upload it from the zip, or
   from `My Drive/language_system/notebooks/` after the first run.
3. Runtime, Change runtime type, **T4 GPU**. Save.

The notebook installs the code from the zip every time it runs, so a newer zip
is picked up by uploading it over the old one. Your datasets and everything
already generated are never overwritten.

### Once, optional: publishing from the page

1. On app.netlify.com: your avatar, User settings, Applications, Personal
   access tokens, New access token. Copy it.
2. In Colab: the key icon on the left, Add new secret, name
   `NETLIFY_AUTH_TOKEN`, paste the token, switch Notebook access on.

Without it everything works except the Publish option.

---

## Each time

1. Runtime, **Run all**. About five minutes the first time in a session
   (tools and the language model are installed).
2. The last cell prints a link ending in `gradio.live`, a user name and a
   password. Open the link and sign in.
3. On the page, choose the **Language**.
4. **First time for a language: a trial.** Scope: *A trial on chosen topics*,
   one topic, then Start. It takes a few minutes.
5. Open **Check the output**. Play a recording, look at the pictures, open the
   unit and watch the video. If something is wrong, stop here and say what.
6. **Then everything.** Scope: *Everything not yet finished*, Start. For
   German, expect four to five hours in total; the study units (videos) take
   the longest. Keep the Colab tab open. Watch the log or leave it.
7. If the session disconnects: Run all again, open the new link, Start again.
   Finished work is skipped.
8. When it has finished: tick **Publish when finished** and press Start once
   more. Nothing is redone; only the builds and publishing run.

The phone build is at `My Drive/language_system/de/builds/phone_build` and the
laptop build beside it, if you want to copy them.

---

## The choices on the page

| Choice | Options | Use |
|---|---|---|
| Scope | Trial on chosen topics, or everything | Trial first, always |
| Scene descriptions | Language model, or Simple | Language model, when step 4 of the notebook ran |
| Voice | The language's voice, or test tones | The voice. Test tones only check the line quickly |
| Pictures | Real, stand-in, or leave | Real on a GPU session |
| Videos in the phone build | None, bilingual, language only, both | None keeps the upload small |
| Publish when finished | tick or not | Needs the Netlify token |

Test tones and stand-in pictures are safe to use: units made with them are
rebuilt automatically when the real recordings and pictures exist.

---

## German specifics

**Voice:** Piper, `de_DE-thorsten-high`. Open source (MIT licence, voice data
CC0), runs on an ordinary processor, the same text always gives the same
recording. Downloaded once, about 110 MB, into `My Drive/language_system/voices`.

**What is spoken for a word:** nouns with their article: der Kaffee, die Frau,
das Haus, die Eltern. Deutschland, Deutsch and Englisch without one.

**What is shown:** dictionary style, `der Kaffee, -s`. The plural marker is
shown on the video and in the application, and never spoken.

**Names:** German units are named `de_greetings_01`, and the site is
`stractured-german-study.netlify.app` (created in your Netlify account on the
first publish; change the name on the page if you prefer another).

---

## From the command line instead

Everything the page does is one command:

    python bin/produce.py --lang de --topics greetings     a trial
    python bin/produce.py --lang de                        everything
    python bin/produce.py --lang de --publish              and publish

On the laptop, without a graphics processor, add `--images placeholder` to
finish everything except the pictures.
