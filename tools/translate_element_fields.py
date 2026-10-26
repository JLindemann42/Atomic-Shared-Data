#!/usr/bin/env python3
"""
Translate element_appearance and electrical_type in the eleven non-English element files.

Roadmap 0.8, Windows porting notes D12 and D58. Both fields were marked localized but never
translated: Swedish, Italian and Afrikaans held the English text in every row, and where something
did differ it was a word-for-word substitution rather than a translation ("Grayesth White",
"Pale Yellow Tdanst", "银白色 Metallic", "Silvery puti"). Other languages had "---" where English has
an electrical type. So every cell is rewritten from the tables here, not only the English ones.

The translations live in tools/translations/<field>.tsv, one English phrase per row and one column per
language, so a native speaker can correct a cell and re-run this. A phrase missing from a table is an
error rather than a silent English fallback.

English is corrected first, because the tables key on it: typos ("Lostrus Metallic", "Silvery White
Metall", "Reddish- Brown"), casing variants of the same phrase, and three wrong values - radon is a
colourless gas, not "unknown, probably metallic"; fluorine is a pale yellow gas, not "Yellow"; and
hydrogen, a gas, had no electrical type.

Two French cells damaged by the same substitution are repaired: beryllium's group ("Alkaldanse
earth métal", singular like beryllium's group in every other language) and plutonium's crystal
structure ("Monocldansic").

Idempotent. Usage:
    python tools/translate_element_fields.py            # report
    python tools/translate_element_fields.py --write
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import element_files  # noqa: E402

TABLES = pathlib.Path(__file__).resolve().parent / "translations"
FIELDS = ["element_appearance", "electrical_type"]
UNTRANSLATED = {"---", ""}

ENGLISH = {
    "element_appearance": {
        "iron": "Lustrous Metallic",
        "sodium": "Silvery White Metallic",
        "titanium": "Silvery White Metallic",
        "radium": "Silvery White Metallic",
        "bromine": "Reddish-Brown",
        "zinc": "Silver-Gray",
        "copper": "Red-orange metallic luster",
        "vanadium": "Blue-silver-gray metal",
        "chlorine": "Pale yellow-green gas",
        "radon": "Colorless Gas",
        "fluorine": "Pale Yellow Gas",
        "iridium": "Silvery White",
        "platinum": "Silvery White",
        "thallium": "Silvery White",
        "thorium": "Silvery White",
        "bismuth": "Brownish Silver",
        "astatine": "Unknown, probably metallic",
    },
    "electrical_type": {
        "hydrogen": "Insulator",
    },
}

# (language, element, field, value)
REPAIRS = [
    ("fr", "beryllium", "element_group", "Métal alcalino-terreux"),
    ("fr", "plutonium", "crystal_structure", "Monoclinique"),
]


def table(field: str) -> dict[str, dict[str, str]]:
    with open(TABLES / f"{field}.tsv", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t", quoting=csv.QUOTE_NONE))
    out = {}
    for row in rows:
        missing = [lang for lang in element_files.LANGUAGES if not row.get(lang)]
        if missing:
            raise SystemExit(f"{field}.tsv: {row['en']!r} has no {', '.join(missing)}")
        out[row["en"]] = row
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    tables = {field: table(field) for field in FIELDS}

    english = element_files.load("en")
    changed_en = 0
    for field, fixes in ENGLISH.items():
        for key, value in fixes.items():
            if english[key][field] != value:
                english[key][field] = value
                changed_en += 1
    print(f"en   {changed_en:4} corrected")
    if args.write and changed_en:
        element_files.save("en", english)

    unused = {field: set(t) for field, t in tables.items()}
    for lang in element_files.LANGUAGES[1:]:
        data = element_files.load(lang)
        changed = 0
        for key, row in english.items():
            for field in FIELDS:
                source = row[field]
                if source in UNTRANSLATED:
                    value = source
                else:
                    if source not in tables[field]:
                        raise SystemExit(f"{field}: no translation of {source!r} ({key})")
                    unused[field].discard(source)
                    value = tables[field][source][lang]
                if data[key].get(field) != value:
                    data[key][field] = value
                    changed += 1

        for repair_lang, key, field, value in REPAIRS:
            if repair_lang == lang and data[key][field] != value:
                data[key][field] = value
                changed += 1

        print(f"{lang:4} {changed:4} cells rewritten")
        if args.write and changed:
            element_files.save(lang, data)

    for field, phrases in unused.items():
        if phrases:
            print(f"note: {field}.tsv has unused rows: {sorted(phrases)}")
    if not args.write:
        print("dry run; --write to apply")
    return 0


if __name__ == "__main__":
    sys.exit(main())
