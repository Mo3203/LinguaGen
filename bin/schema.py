"""Contract for a unit script: build/scripts/<topic>.json.

The field names `fr` and `intro_fr` are kept from the first language for
compatibility with scripts already generated. They hold the sentence and the
intro line in the language being studied, whichever language that is.
"""
from __future__ import annotations

import warnings

from pydantic import BaseModel, Field, field_validator

from language import PROFILE as P

warnings.filterwarnings("ignore", message='Field name "register"')

BANNED_IN_PROMPTS = ("abstract concept", "the word", "text saying", "letters")


class Scene(BaseModel):
    sentence_id: str = Field(pattern=r"^s_\d{4}$")
    register: str
    fr: str = Field(min_length=2)
    en: str = Field(min_length=2)
    visual_prompt: str = Field(min_length=20, max_length=400)
    est_duration_s: float = Field(gt=0.5, lt=30)

    @field_validator("register")
    @classmethod
    def reg_ok(cls, v):
        assert v in P.registers, f"register must be one of {P.registers}"
        return v

    @field_validator("visual_prompt")
    @classmethod
    def concrete(cls, v):
        assert not any(b in v.lower() for b in BANNED_IN_PROMPTS), \
            "visual prompt must depict a concrete scene"
        return v


class WordBlock(BaseModel):
    vocab_id: str = Field(pattern=P.id_pattern)
    vocab: str
    english_meaning: str
    pos: str
    intro_fr: str = Field(min_length=3, max_length=120)
    intro_en: str = Field(min_length=3, max_length=120)
    scenes: list[Scene] = Field(min_length=3, max_length=3)


class UnitScript(BaseModel):
    topic: str
    prompt_version: str
    style_prefix: str = Field(min_length=10)
    words: list[WordBlock] = Field(min_length=1)

    def scene_count(self):
        return sum(len(w.scenes) for w in self.words)
