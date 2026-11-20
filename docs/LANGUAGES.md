# How a language is described

Each language has a profile, `languages/<code>.json`. The code never names a
language; it asks the profile. Adding a language means adding a profile and
`data/<code>/vocab.csv` and `sentences.csv`.

| Field | What it decides | French | German |
|---|---|---|---|
| speech | engine, voice, and the voice's version | Kokoro, ff_siwis | Piper, de_DE-thorsten-high |
| citation.articles | article spoken before a noun | un, une | der, die, das, die (plural only) |
| citation.noArticle | nouns spoken without one | none | Deutschland, Deutsch, Englisch |
| titleWithArticle, titleWithPlural | heading on video and in the app | chat | der Kaffee, -s |
| genders | gender names | Masculine, Feminine | also Neuter, Plural only |
| partsOfSpeech | allowed values in vocab.csv | 11 | 13 (adds article, modal verb, particle) |
| characters | letters on the extra keyboard | é è ê ... | ä ö ü ß ... |
| labels | wording in the application | Bonjour, French only | Guten Tag, German only |
| unitPrefix, videoSuffix | file names | none, `_french.mp4` | `de_`, `_german.mp4` |
| deploy.site | Netlify site | stractured-french-study | stractured-german-study |
| laptopPort | port of the laptop build | 8000 | 8100 |

French keeps every name and setting it was built with, so none of the 129
French units is rebuilt.

## The voice's version

`speech.version` is part of every recording's file name. Changing the voice or
its settings means changing the version, and the recordings are made again.
Leave it alone otherwise.
