#!/usr/bin/env python3
"""
Propose stopword candidates per language, for review (roadmap 1.1).

Retrieval scores a dataset row by how much of the query's content it covers. Function words are not
content, and IDF alone cannot discount them here: the index is reference text, which is declarative,
so "what" appears in two documents of ~800 and outweighs "electron". The stopword list has to come
from somewhere other than the index.

Two sources, both text the app already ships:

  * element descriptions in that language - a word in most of the 118 is grammar, not subject
    ("the", "och", "der");
  * the assistant's own suggested questions and prompts in strings.xml - the words questions are
    built from ("what", "vilken", "welche"), which reference text never contains.

The output is candidates, not the list. A reviewed list lives in the Android app's nlu/Lexicon.kt as
STOPWORDS, and Windows generates its copy from there. Domain words that happen to be frequent
("element", "atomic") are candidates too and are exactly what review is for: they must not be
stopwords, because they are what a dataset query is about.

Usage:
    python tools/stopword_candidates.py [path/to/app/src/main/res] > candidates.tsv
"""

from __future__ import annotations

import collections
import pathlib
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import element_files  # noqa: E402

RES_FOLDERS = {
    "en": "values", "af": "values-af", "de": "values-de", "es": "values-es", "fil": "values-b+fil",
    "fr": "values-fr", "hi": "values-hi", "it": "values-it-rIT", "pt": "values-pt-rBR",
    "sv": "values-sv-rSE", "ur": "values-ur", "zh": "values-zh-rCN",
}

# A word in at least this share of descriptions is grammar.
DESCRIPTION_SHARE = 0.35
# A word in at least this many of the assistant's question strings is a question word.
QUESTION_STRINGS = 4


def fold(text: str) -> str:
    """Lowercase and strip Latin diacritics only: in Devanagari and Arabic script the combining
    marks are vowels, and stripping them turns तत्व into ततव."""
    out = []
    for c in text.lower():
        if c.isascii() or not unicodedata.name(c, "").startswith("LATIN"):
            out.append(c)
            continue
        decomposed = unicodedata.normalize("NFKD", c)
        out.append("".join(d for d in decomposed if unicodedata.category(d) not in ("Mn", "Mc", "Me")))
    return "".join(out)


def words(text: str) -> set[str]:
    # On whitespace and punctuation, not on \w: Python's \w excludes Devanagari vowel signs, so it
    # split Hindi words in half.
    return {w for w in re.split(r"[\s.,;:!?¿¡\"'()\[\]{}…।؟،%/-]+", fold(text)) if w and not w.isdigit()}


def question_strings(res: pathlib.Path, folder: str) -> list[str]:
    path = res / folder / "strings.xml"
    if not path.is_file():
        return []
    out = []
    for node in ET.parse(path).getroot():
        name = node.get("name", "")
        if not name.startswith("ai_"):
            continue
        texts = [node.text or ""] if node.tag == "string" else [i.text or "" for i in node.iter("item")]
        out.extend(t for t in texts if "?" in t or "？" in t or "؟" in t)
    return out


def main() -> int:
    res = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else element_files.ROOT.parent / "app" / "src" / "main" / "res"
    print("lang\tword\tsource\tshare")
    for lang in element_files.LANGUAGES:
        data = element_files.load(lang)
        descriptions = [row.get("description") or "" for row in data.values()]
        df = collections.Counter(w for d in descriptions for w in words(d))
        for word, count in sorted(df.items(), key=lambda x: -x[1]):
            share = count / len(descriptions)
            if share < DESCRIPTION_SHARE:
                break
            print(f"{lang}\t{word}\tdescriptions\t{share:.2f}")

        questions = question_strings(res, RES_FOLDERS[lang])
        qf = collections.Counter(w for q in questions for w in words(q))
        for word, count in sorted(qf.items(), key=lambda x: -x[1]):
            if count < QUESTION_STRINGS:
                break
            if df[word] / len(descriptions) < DESCRIPTION_SHARE:
                print(f"{lang}\t{word}\tquestions\t{count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
