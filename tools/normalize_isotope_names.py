#!/usr/bin/env python3
"""
Write every isotope name as Symbol-MassNumber: Sb-103, not 103-Sb, Astatine-191 or 259Sg.

Roadmap 0.8. 691 names in each language were not in that form, in three shapes:

  * 103-Sb       antimony, iodine, tellurium and xenon, mass number first (154 names)
  * Astatine-191 22 heavy elements, by English name, so Swedish read "Astatine-191" too (525)
  * 259Sg        seaborgium, no hyphen at all (12)

The names are display text only. Both apps take the mass number from iso_A, and the script refuses
to rename an isotope whose name disagrees with its iso_A, so the number shown cannot change. A
metastable suffix ("m", "m1") is kept. Placeholders such as "---" are left alone.

Idempotent: a second run changes nothing.

Usage:
    python tools/normalize_isotope_names.py            # report
    python tools/normalize_isotope_names.py --write
"""

from __future__ import annotations

import argparse
import collections
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import element_files  # noqa: E402

MAX_SLOTS = 60
SHAPES = [
    ("Sym-A", re.compile(r"^(?P<sym>[A-Z][a-z]?)-(?P<a>\d+)(?P<m>m\d*)?$")),
    ("A-Sym", re.compile(r"^(?P<a>\d+)(?P<m>m\d*)?-(?P<sym>[A-Z][a-z]?)$")),
    ("ASym", re.compile(r"^(?P<a>\d+)(?P<m>m\d*)?(?P<sym>[A-Z][a-z]?)$")),
    ("Name-A", re.compile(r"^(?P<name>[A-Z][a-z]{2,})-(?P<a>\d+)(?P<m>m\d*)?$")),
]


def normalise(name: str, symbol: str, mass_number: str | None) -> tuple[str, str] | None:
    """The canonical name and the shape it came from, or None for a placeholder."""
    for shape, pattern in SHAPES:
        match = pattern.match(name.strip())
        if not match:
            continue
        if "sym" in match.groupdict() and match["sym"] != symbol:
            raise ValueError(f"{name!r} names {match['sym']}, not {symbol}")
        if mass_number is not None and str(mass_number).strip() != match["a"]:
            raise ValueError(f"{name!r} disagrees with iso_A {mass_number!r}")
        return f"{symbol}-{match['a']}{match['m'] or ''}", shape
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    english = element_files.load("en")
    total = collections.Counter()
    for lang in element_files.LANGUAGES:
        data = element_files.load(lang)
        changed = collections.Counter()
        for key, row in data.items():
            symbol = english[key]["short"]
            for slot in range(1, MAX_SLOTS + 1):
                name = row.get(f"iso_{slot}")
                if not isinstance(name, str):
                    continue
                result = normalise(name, symbol, row.get(f"iso_A_{slot}"))
                if result is None:
                    continue
                canonical, shape = result
                if canonical != name:
                    row[f"iso_{slot}"] = canonical
                    changed[shape] += 1
        print(f"{lang:4} {sum(changed.values()):4} renamed  {dict(changed)}")
        total.update(changed)
        if args.write and changed:
            element_files.save(lang, data)

    print(f"total {sum(total.values())}" + ("" if args.write else "  (dry run; --write to apply)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
