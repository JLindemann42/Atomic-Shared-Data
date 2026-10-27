#!/usr/bin/env python3
"""
Check the translated reference-table titles in datasets/titles_{lang}.tsv (roadmap 1.3).

The tables are English, so "vad är neutronens massa" shared no word with "Neutron mass" and could
not be answered. Each language file gives every translatable row a title in that language, with
other wordings after a "|", and both apps search them and show the first.

What --check enforces, for every file:

  * exactly the translatable keys of golden/dataset_keys.tsv - nothing missing, nothing extra,
    nothing twice. Ion and electrode rows are titled by an element, whose name the element files
    already translate, and solubility rows by an ion's formula, so those three tables are not here;
  * a title for every key;
  * the parts of a title that must not be translated, kept verbatim in the first wording: numbers,
    Greek letters and chemical formulas ("α-Quartz (SiO2)", "Square root of 2", "Activity #1");
  * "reviewed" blank or "y". Titles are machine-translated until a native speaker checks them.

A file may also name the tables themselves, as "dataset/<table>" - "dataset/poisson" is "Poissons
tal" in Swedish. Those names are searched with every row of the table: the row "Sandsten" is about
sandstone, but "Poissons tal för sandsten" asks for it by the table's name.

Usage:
    python tools/dataset_titles.py --check
    python tools/dataset_titles.py --new LANG     # a file of English titles to translate
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "golden" / "dataset_keys.tsv"
FOLDER = ROOT / "datasets"
TRANSLATABLE = {"alloy", "constant", "dictionary", "equation", "geology", "indicator", "poisson", "unit"}
LANGUAGES = ["af", "de", "es", "fil", "fr", "hi", "it", "pt", "sv", "ur", "zh"]
TABLES = {"alloy", "constant", "dictionary", "electrode", "equation", "geology", "indicator", "ion",
          "poisson", "solubility", "unit"}

NUMBER = re.compile(r"\d+")
GREEK = re.compile(r"[Ͱ-Ͽ]")
FORMULA_WORD = re.compile(r"^\d*(?:[A-Z][a-z]?\d*|[(),]\d*)+$")


def source_titles() -> dict[str, str]:
    rows = [line.rstrip("\n").split("\t") for line in GOLDEN.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")]
    return {key: title for key, dataset, title in rows[1:] if dataset in TRANSLATABLE}


def fixed_parts(title: str) -> list[str]:
    """What a translation must keep: numbers, Greek letters, and formulas in brackets."""
    parts = NUMBER.findall(title) + GREEK.findall(title)
    for inside in re.findall(r"\(([^()]*(?:\([^()]*\)[^()]*)*)\)", title):
        words = inside.split()
        if words and all(FORMULA_WORD.match(w) for w in words):
            parts.append(inside)
    return parts


def read(path: pathlib.Path) -> list[list[str]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or line.startswith("key\t"):
            continue
        rows.append(line.split("\t"))
    return rows


def check() -> int:
    source = source_titles()
    problems = []
    for path in sorted(FOLDER.glob("titles_*.tsv")):
        lang = path.stem.removeprefix("titles_")
        if lang not in LANGUAGES:
            problems.append(f"{path.name}: unknown language")
        seen = set()
        for cells in read(path):
            key = cells[0]
            title = cells[1].strip() if len(cells) > 1 else ""
            reviewed = cells[2].strip() if len(cells) > 2 else ""
            if key in seen:
                problems.append(f"{path.name}: {key} twice")
            seen.add(key)
            if key.startswith("dataset/"):
                if key.removeprefix("dataset/") not in TABLES:
                    problems.append(f"{path.name}: {key} is not a table")
                elif not title:
                    problems.append(f"{path.name}: {key} has no name")
                continue
            if key not in source:
                problems.append(f"{path.name}: {key} is not a translatable row")
                continue
            forms = [f.strip() for f in title.split("|") if f.strip()]
            if not forms:
                problems.append(f"{path.name}: {key} has no title")
                continue
            for part in fixed_parts(source[key]):
                if part not in forms[0]:
                    problems.append(f"{path.name}: {key} lost {part!r} ({forms[0]!r})")
            if reviewed not in ("", "y"):
                problems.append(f"{path.name}: {key} reviewed must be blank or y")
        for key in sorted(set(source) - seen):
            problems.append(f"{path.name}: {key} missing")
    for problem in problems:
        print(problem)
    print(f"{len(problems)} problem(s)")
    return 1 if problems else 0


def new(lang: str) -> int:
    path = FOLDER / f"titles_{lang}.tsv"
    if path.exists():
        print(f"{path.name} exists")
        return 1
    lines = [f"# Reference-table titles in {lang} (roadmap 1.3); translate the second column.",
             "key\ttitle\treviewed"]
    lines += [f"{key}\t{title}\t" for key, title in source_titles().items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {path.name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--new", metavar="LANG")
    args = parser.parse_args()
    return check() if args.check else new(args.new)


if __name__ == "__main__":
    sys.exit(main())
