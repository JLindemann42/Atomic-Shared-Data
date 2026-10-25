#!/usr/bin/env python3
"""
Freeze a held-out split of the corpus (roadmap 0.5).

Moves about a fifth of each corpus file into heldout/<same name>.tsv. The everyday gate in both apps
runs corpus/ only; heldout/ is scored at release, so a change tuned against the corpus can still be
measured on questions nobody tuned against. Phase 3 trains on corpus/ and never on heldout/.

What moves is decided by a hash, not by hand, so the split is reproducible and unbiased:

  * The unit is a session (all turns of a multi-turn conversation share a dialogue state and must
    move together) or a standalone row.
  * A unit is held out when crc32("<file>:<session or id>") % 5 == 0.
  * regressions.tsv and reported.tsv are never split. Every row there is a reported defect, and
    hiding one until release would let it come back unnoticed.

This is a one-time freeze. It refuses to run when heldout/ already exists, because re-running it
over a corpus that has since grown would quietly move rows people have been tuning against. New
rows go to corpus/; the held-out set only grows by a deliberate, separate freeze.

Usage:
    python tools/split_heldout.py            # report what would move
    python tools/split_heldout.py --write
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import zlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
HELDOUT = ROOT / "heldout"

NEVER_SPLIT = {"regressions", "reported"}
MODULUS = 5

HELDOUT_NOTE = (
    "# HELD OUT (roadmap 0.5). Scored at release only, never in the everyday gate, and never used\n"
    "# for training. Frozen by tools/split_heldout.py from corpus/{name}.tsv: do not tune against\n"
    "# these rows, and do not move them back.\n"
)


def units(lines: list[str]) -> tuple[list[str], list[str], dict[str, list[str]], list[str]]:
    """Split a file into its comment lines, header, units (key -> rows in file order) and unit order."""
    comments: list[str] = []
    header: str | None = None
    by_key: dict[str, list[str]] = {}
    order: list[str] = []
    for line in lines:
        if not line.strip() or line.startswith("#"):
            if header is None:
                comments.append(line)
            continue
        if header is None:
            header = line
            continue
        cols = line.split("\t")
        names = header.split("\t")
        row = dict(zip(names, cols))
        key = row.get("session", "").strip() or row["id"]
        if key not in by_key:
            by_key[key] = []
            order.append(key)
        by_key[key].append(line)
    if header is None:
        raise SystemExit("no header")
    return comments, [header], by_key, order


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    if args.write and HELDOUT.exists():
        print(f"{HELDOUT} exists: the split is frozen. See the module docstring.", file=sys.stderr)
        return 1

    total_rows = held_rows = 0
    plan: dict[str, tuple[str, str]] = {}
    for path in sorted(CORPUS.glob("*.tsv")):
        name = path.stem
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        comments, header, by_key, order = units(lines)
        rows = sum(len(v) for v in by_key.values())
        total_rows += rows
        if name in NEVER_SPLIT:
            print(f"{name:26} {rows:5} rows   kept whole (defect tripwire)")
            continue

        held = [k for k in order if zlib.crc32(f"{name}:{k}".encode("utf-8")) % MODULUS == 0]
        held_set = set(held)
        n_held = sum(len(by_key[k]) for k in held)
        held_rows += n_held
        print(f"{name:26} {rows:5} rows   {n_held:4} held out ({len(held)} of {len(order)} units)")

        keep_lines = [l for l in lines if not (l and not l.startswith("#") and l != header[0]
                                                and l in {r for k in held_set for r in by_key[k]})]
        out_lines = [HELDOUT_NOTE.format(name=name).rstrip("\n")] + header + \
                    [r for k in order if k in held_set for r in by_key[k]]
        plan[name] = ("\n".join(keep_lines) + "\n", "\n".join(out_lines) + "\n")

    print(f"\n{held_rows} of {total_rows} rows held out ({held_rows / total_rows:.1%})")

    if args.write:
        HELDOUT.mkdir()
        for name, (keep, out) in plan.items():
            (CORPUS / f"{name}.tsv").write_text(keep, encoding="utf-8", newline="\n")
            (HELDOUT / f"{name}.tsv").write_text(out, encoding="utf-8", newline="\n")
        print(f"wrote {len(plan)} files to {HELDOUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
