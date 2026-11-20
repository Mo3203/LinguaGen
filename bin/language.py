"""The language profile, and every rule that differs between languages.

A profile is languages/<code>.json. Code never names a language; it asks the
profile. Adding a language means adding a profile and a dataset, nothing else.

    from language import PROFILE
    PROFILE.citation_form("Kaffee", "noun", "m")    -> "der Kaffee"
    PROFILE.display_title("Kaffee", "noun", "m", "-s")  -> "der Kaffee, -s"
    PROFILE.gender_label("n")                       -> "Neuter"
    PROFILE.audio_ref(text)                         -> "build/audio/<key>.wav"
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from cache import cache_key
from paths import LANG, LANG_ROOT, REPO

LANGUAGES = REPO / "languages"


def available() -> list[str]:
    return sorted(p.stem for p in LANGUAGES.glob("*.json"))


def _blank(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x)) or str(x).strip() in ("", "nan")


class Profile:
    def __init__(self, data: dict):
        self.data = data
        self.code: str = data["code"]
        self.name: str = data.get("name", self.code)
        self.locale: str = data.get("locale", self.code)
        self.unit_prefix: str = data.get("unitPrefix", "")
        self.video_suffix: str = data.get("videoSuffix", "target")
        self.speech: dict = data.get("speech", {})
        self.pos: set[str] = set(data.get("partsOfSpeech", []))
        self.genders: dict[str, str] = data.get("genders", {})
        self.registers: list[str] = data.get("registers",
                                             ["formal_statement", "casual_question", "idiomatic"])
        self.prompt: dict = data.get("prompt", {})
        self.labels: dict = data.get("labels", {})
        self.characters: list[str] = data.get("characters", [])
        self.title_with_article: bool = bool(data.get("titleWithArticle", False))
        self.title_with_plural: bool = bool(data.get("titleWithPlural", False))
        c = data.get("citation", {})
        self._articles: dict = c.get("articles", {})
        self._plural_article: str = c.get("pluralArticle", "")
        self._plural_endings: tuple = tuple(c.get("pluralEndings", []))
        self._plural_exceptions: set = {w.lower() for w in c.get("pluralExceptions", [])}
        self._no_article: set = {w.lower() for w in c.get("noArticle", [])}

    # ------------------------------------------------------------ identity
    @property
    def id_pattern(self) -> str:
        return rf"^{self.code}_\d{{4}}$"

    def unit_name(self, topic: str, number: int) -> str:
        return f"{self.unit_prefix}{topic}_{number:02d}"

    def topic_of_unit(self, unit_name: str) -> str:
        topic = unit_name.rsplit("_", 1)[0]
        if self.unit_prefix and topic.startswith(self.unit_prefix):
            topic = topic[len(self.unit_prefix):]
        return topic

    # ------------------------------------------------------------ words
    def gender_label(self, gender) -> str:
        return "" if _blank(gender) else self.genders.get(str(gender), "")

    def article(self, vocab, pos, gender) -> str:
        """The article spoken and shown with a noun, or empty."""
        w = str(vocab).strip()
        if pos != "noun" or _blank(gender) or str(gender) not in self._articles:
            return ""
        if w.lower() in self._no_article:
            return ""
        if (self._plural_article and self._plural_endings
                and w.lower().endswith(self._plural_endings)
                and w.lower() not in self._plural_exceptions):
            return self._plural_article
        return self._articles[str(gender)]

    def citation_form(self, vocab, pos, gender) -> str:
        """What is spoken for a word: nouns with their article, the rest as written.
        The plural marker is never part of it."""
        w = str(vocab).strip()
        art = self.article(w, pos, gender)
        return f"{art} {w}" if art else w

    def display_title(self, vocab, pos, gender, plural=None) -> str:
        """What is printed as the word's heading, in dictionary style when the
        profile asks for it: "der Kaffee, -s". Printed only, never spoken."""
        title = self.citation_form(vocab, pos, gender) if self.title_with_article else str(vocab).strip()
        if self.title_with_plural and pos == "noun" and not _blank(plural):
            title = f"{title}, {str(plural).strip()}"
        return title

    @staticmethod
    def plural_label(plural) -> str:
        return "" if _blank(plural) else f"Plural  {str(plural).strip()}"

    # ------------------------------------------------------------ speech
    @property
    def speech_version(self) -> str:
        return self.speech.get("version", f"{self.speech.get('adapter', 'unknown')}/v1")

    def audio_ref(self, text: str, version: str | None = None) -> str:
        key = cache_key(str(text), version or self.speech_version)
        return f"build/audio/{key}.wav"

    def resolve_audio(self, stored_ref, text: str) -> Path | None:
        """The recording for a piece of text. Uses the reference stored in the
        dataset when that file exists, otherwise the one the current voice
        would have produced. Either way the file must exist."""
        if not _blank(stored_ref):
            p = LANG_ROOT / str(stored_ref)
            if p.exists():
                return p
        p = LANG_ROOT / self.audio_ref(text)
        return p if p.exists() else None

    # ------------------------------------------------------------ app
    def app_block(self) -> dict:
        """What the study application needs to know about the language."""
        return {
            "code": self.code,
            "name": self.name,
            "locale": self.locale,
            "genders": self.genders,
            "characters": self.characters,
            "labels": self.labels,
        }


def load(code: str | None = None) -> Profile:
    code = (code or LANG).lower()
    path = LANGUAGES / f"{code}.json"
    if not path.exists():
        raise SystemExit(f"no language profile at {path}. Available: {', '.join(available()) or 'none'}")
    return Profile(json.loads(path.read_text(encoding="utf-8")))


PROFILE = load()
