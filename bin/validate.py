#!/usr/bin/env python3
"""Quality gate for a language's dataset.

    python bin/validate.py --lang de
Exit code 0 means the dataset is ready. Any failure prints the reason and exits 1.

Checks, in order:
  0. Encoding: the files must be UTF-8.
  1. Columns: types, allowed values, uniqueness, id format. Allowed parts of
     speech, genders and registers come from the language profile.
  2. Relations: every sentence belongs to a word, exactly 3 sentences per word,
     one per register, nouns have a gender and nothing else does, no sentence
     shared between different words.
  3. Information only: sentences that do not contain the word's exact form
     (inflection and elision make this normal).

Never edit the CSV files with Excel or Numbers: they silently re-encode on save.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Check, Column

from language import PROFILE as P
from paths import DATA


def vocab_schema() -> pa.DataFrameSchema:
    return pa.DataFrameSchema(
        {
            "id": Column(str, Check.str_matches(P.id_pattern), unique=True),
            "language": Column(str, Check.isin({P.code})),
            "vocab": Column(str, unique=True, checks=Check.str_length(min_value=1)),
            "english_meaning": Column(str, Check.str_length(min_value=1)),
            "pos": Column(str, Check.isin(P.pos)),
            "gender": Column(str, Check.isin(set(P.genders)), nullable=True),
            "topic": Column(str, Check.str_matches(r"^[a-z0-9_]+$")),
            "tier": Column(int, Check.isin({1, 2, 3})),
            # optional columns
            "plural": Column(str, nullable=True, required=False),
            "notes": Column(str, nullable=True, required=False),
            "audio_ref": Column(str, nullable=True, required=False),
        },
        strict=True, coerce=True,
    )


def sentences_schema() -> pa.DataFrameSchema:
    return pa.DataFrameSchema(
        {
            "id": Column(str, Check.str_matches(r"^s_\d{4}$"), unique=True),
            "vocab_id": Column(str, Check.str_matches(P.id_pattern)),
            "vocab": Column(str),
            "register": Column(str, Check.isin(set(P.registers))),
            "target_sentence": Column(str, Check.str_length(min_value=2)),
            "english_sentence": Column(str, Check.str_length(min_value=2)),
            "audio_ref": Column(str, nullable=True),
        },
        strict=True, coerce=True,
    )


def fail(msg: str) -> None:
    print(f"  FAIL  {msg}")
    sys.exit(1)


def read_utf8(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, encoding="utf-8")
    except UnicodeDecodeError as e:
        print(f"  FAIL  {path.name} is not UTF-8 (byte {e.object[e.start]:#04x} at position {e.start}).")
        print("        Likely cause: the file was opened and saved by Excel or Numbers.")
        print("        Restore the previous copy, then edit only with a text editor or VS Code.")
        sys.exit(1)
    except FileNotFoundError:
        fail(f"{path} not found. Put vocab.csv and sentences.csv in data/{P.code}/")


def main() -> None:
    print(f"[validate] {P.name}  ({DATA})")
    v = read_utf8(DATA / "vocab.csv")
    s = read_utf8(DATA / "sentences.csv")

    try:
        v = vocab_schema().validate(v, lazy=True)
        s = sentences_schema().validate(s, lazy=True)
    except pa.errors.SchemaErrors as e:
        print(e.failure_cases.head(30).to_string(index=False))
        fail("column checks (first 30 problems shown above)")

    if ((v.pos == "noun") & v.gender.isna()).any():
        fail(f"nouns missing gender: {list(v[(v.pos == 'noun') & v.gender.isna()].vocab)[:5]}")
    if ((v.pos != "noun") & v.gender.notna()).any():
        fail(f"non-nouns carrying gender: {list(v[(v.pos != 'noun') & v.gender.notna()].vocab)[:5]}")
    if not s.vocab_id.isin(set(v.id)).all():
        fail("sentence belongs to no word (vocab_id not found)")
    per = s.groupby("vocab_id")
    if not per.size().eq(3).all():
        fail(f"words without exactly 3 sentences: {list(per.size()[per.size() != 3].index)[:5]}")
    if not per["register"].nunique().eq(len(P.registers)).all():
        fail("words missing a register")
    missing = set(v.id) - set(s.vocab_id)
    if missing:
        fail(f"words with no sentences: {sorted(missing)[:5]}")
    dup = s[s.duplicated("target_sentence", keep=False)]
    cross = dup.groupby("target_sentence")["vocab_id"].nunique()
    if (cross > 1).any():
        fail(f"identical sentence used by different words: {list(cross[cross > 1].index)[:3]}")

    joined = s.merge(v[["id", "vocab", "pos"]], left_on="vocab_id", right_on="id", suffixes=("", "_v"))
    nonverb = joined[~joined.pos.isin({"verb", "modal_verb", "phrase"})]
    miss = (~nonverb.apply(lambda r: r["vocab_v"].lower() in r["target_sentence"].lower(), axis=1)).sum()

    print(f"  OK    words           : {len(v)}")
    print(f"  OK    sentences       : {len(s)}")
    print(f"  OK    topics          : {v.topic.nunique()}")
    print("  OK    encoding, columns, relations, registers, duplicates")
    print(f"  INFO  sentences using another form of the word (normal): {miss}")
    print("READY  the dataset passes every check.")


if __name__ == "__main__":
    main()
