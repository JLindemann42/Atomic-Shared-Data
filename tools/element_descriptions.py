#!/usr/bin/env python3
"""
Finish the element descriptions in the eleven non-English element files (roadmap 1.10).

Most locales were translated whole, but Afrikaans, Filipino and Swedish were left part-English -
"Det är one of the least reactive chemical elements" - and French, Hindi, Italian and Portuguese
each kept a few English rows. The narrative answers are cut from these descriptions sentence by
sentence, so a mixed description produced a mixed answer.

The translations live in tools/translations/descriptions_<lang>.tsv, one element per row:

    element <TAB> reviewed <TAB> description

translated from the English description as a whole, not patched around the half that was already
there. "reviewed" stays blank until a native speaker has checked the row, then is "y"; a reviewer
corrects the cell and re-runs --write. Line breaks inside a description are written as \\n.

Every row is checked before it is written, against the English row:
  - English is gone: fewer than four English function words (the test
    Android's scripts/check_description_translations.py uses), not counting the ones that are
    words of the language itself (Afrikaans "is", "was", "of");
  - the element's symbol survives as a word ("symbolen No", not "प्रतीक नहीं");
  - every number in the English survives, decimal comma and spaced thousands allowed (table rows
    only: the older translations abridge, and dropping a figure there is not a defect);
  - no line break or tab inside a word;
  - no word-for-word substitution artefact ("Latdans", "est a" in French).

The same checks run over every description already in the files, so the report is the backlog.

Usage:
    python tools/element_descriptions.py            # report
    python tools/element_descriptions.py --check    # exit 1 on any failure
    python tools/element_descriptions.py --write    # apply the tables, then report
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import element_files  # noqa: E402

TABLES = pathlib.Path(__file__).resolve().parent / "translations"
HEADER = ["element", "reviewed", "description"]

ENGLISH_FUNCTION_WORDS = re.compile(
    r"\b(the|and|which|with|has|have|is|are|was|were|been|of|from|that|its|it|only|also|"
    r"most|used|found|other|than|but|such|these|those|there|their|when|while|into|about)\b"
)
THRESHOLD = 4
# Function words that are also words of the language itself: Afrikaans writes "Goud is 'n chemiese
# element", "dit was" and "of" (or). Counted, they marked 23 Afrikaans descriptions as English.
OWN_WORDS = {"af": {"is", "was", "of"}}
CITATION = re.compile(r"\[\d+\]")
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
SPACED_THOUSANDS = re.compile(r"(?<=\d)[   ](?=\d{3}\b)")
BROKEN_WORD = re.compile(r"\w[\t\n\r]+\w")
SYMBOL = re.compile(r"\bsymbol ([A-Z][a-z]?)\b")
# What a word-for-word substitution left in English text: French "dans" for "in" and "est" for "is",
# inside words as well as between them ("Latdans", "crystalldanse", "Britesth", "est a"). Two French
# descriptions carried it below the English-word threshold.
ARTEFACTS = {"fr": re.compile(r"\w+dans\w*|\w*dans\w+|\best a\b|\w+esth\w*|\w*esth\w+")}
# Repairs to rows that are otherwise translated, where a retranslation would lose more than it fixed.
# Nobelium's symbol, No, was translated as the word: French "Non", Urdu "نہیں" ("not"); Hindi's row
# had the same and is retranslated whole. The Chinese lanthanum row left out the sentence that names
# the symbol. Five German rows broke a word across a blank line ("zweiw\n\nertiges"), which --write
# joins in every row.
REPAIRS = [
    ("fr", "nobelium", "de symbole Non et", "de symbole No et"),
    ("ur", "nobelium", "جس کی علامت نہیں اور", "جس کی علامت No اور"),
    ("zh", "lanthanum", "镧是一种柔软的", "镧是一种化学元素，符号为La，原子序数为57。它是一种柔软的"),
]
JOIN_BROKEN_WORD = re.compile(r"(\w)[\t\n\r]+(\w)")


def table_path(lang: str) -> pathlib.Path:
    return TABLES / f"descriptions_{lang}.tsv"


def read_table(lang: str) -> dict[str, tuple[str, str]]:
    path = table_path(lang)
    if not path.exists():
        return {}
    rows = {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t", quoting=csv.QUOTE_NONE)
        header = next(reader)
        if header != HEADER:
            raise SystemExit(f"{path.name}: header must be {HEADER}, is {header}")
        for line, row in enumerate(reader, start=2):
            if len(row) != 3:
                raise SystemExit(f"{path.name}:{line}: {len(row)} columns, expected 3")
            element, reviewed, text = row
            if element in rows:
                raise SystemExit(f"{path.name}:{line}: {element} twice")
            rows[element] = (reviewed, text.replace("\\n", "\n"))
    return rows


def numbers(text: str) -> set[str]:
    """Digit strings, with the separators that differ between languages taken out."""
    text = SPACED_THOUSANDS.sub("", CITATION.sub("", text))
    return {re.sub(r"[.,]", "", n) for n in NUMBER.findall(text)}


def repaired(lang: str, element: str, text: str) -> str:
    text = JOIN_BROKEN_WORD.sub(r"\1\2", text)
    for where, which, old, new in REPAIRS:
        if (where, which) == (lang, element):
            text = text.replace(old, new)
    return text


def english_words(text: str, lang: str) -> int:
    own = OWN_WORDS.get(lang, set())
    return sum(1 for word in ENGLISH_FUNCTION_WORDS.findall(text.lower()) if word not in own)


def problems(lang: str, text: str, english: str, complete: bool) -> list[str]:
    """What is wrong with [text] as a translation of [english]; [complete] for a table row, which
    translates the whole English text, where the older translations abridge and may drop figures."""
    found = []
    if english_words(text, lang) >= THRESHOLD:
        found.append("still part English")
    symbol = SYMBOL.search(english)
    if symbol and not re.search(rf"(?<![A-Za-z]){symbol.group(1)}(?![a-z])", text):
        found.append(f"symbol {symbol.group(1)} lost")
    missing = numbers(english) - numbers(text) if complete else set()
    if missing:
        found.append("numbers lost: " + ", ".join(sorted(missing)))
    if BROKEN_WORD.search(text):
        found.append("line break inside a word")
    artefact = ARTEFACTS.get(lang)
    if artefact and artefact.search(text):
        found.append("substitution artefact: " + artefact.search(text).group())
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    english = element_files.load("en")
    failures = 0
    print(f'{"lang":5} {"table":>6} {"reviewed":>9} {"problems":>9}')
    for lang in element_files.LANGUAGES[1:]:
        data = element_files.load(lang)
        table = read_table(lang)
        for element, (reviewed, text) in table.items():
            if element not in data:
                raise SystemExit(f"descriptions_{lang}.tsv: unknown element {element}")
            if reviewed not in ("", "y"):
                raise SystemExit(f"descriptions_{lang}.tsv: {element}: reviewed must be blank or y")
            found = problems(lang, text, english[element]["description"], complete=True)
            if found:
                failures += 1
                print(f"  {lang} {element} (table): {'; '.join(found)}")
            elif args.write:
                data[element]["description"] = text
        changed = bool(table)
        backlog = 0
        for element, fields in data.items():
            if element in table:
                continue
            text = repaired(lang, element, fields["description"])
            if args.write and text != fields["description"]:
                fields["description"] = text
                changed = True
            found = problems(lang, text, english[element]["description"], complete=False)
            if found:
                backlog += 1
                failures += 1
                print(f"  {lang} {element}: {'; '.join(found)}")
        if args.write and changed:
            element_files.save(lang, data)
        reviewed = sum(1 for r, _ in table.values() if r == "y")
        print(f"{lang:5} {len(table):6} {reviewed:9} {backlog:9}")
    return 1 if args.check and failures else 0


if __name__ == "__main__":
    sys.exit(main())
