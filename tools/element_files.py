"""
Read and write elements/elements_{lang}.json without reformatting them.

The files are 2-space indented, raw UTF-8 (nothing escaped) and end in a newline. Written any other
way, every one of their ~32,000 lines shows as changed and the real edit is lost in the diff, so
every script that rewrites them goes through here. The working copy's line endings are kept: CRLF
on a Windows checkout, LF elsewhere (see the README).
"""

from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
ELEMENTS = ROOT / "elements"

LANGUAGES = ["en", "af", "de", "es", "fil", "fr", "hi", "it", "pt", "sv", "ur", "zh"]


def path(lang: str) -> pathlib.Path:
    return ELEMENTS / f"elements_{lang}.json"


def load(lang: str) -> dict:
    return json.loads(path(lang).read_bytes().decode("utf-8"))


def save(lang: str, data: dict) -> None:
    target = path(lang)
    newline = "\r\n" if b"\r\n" in target.read_bytes() else "\n"
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    target.write_bytes(text.replace("\n", newline).encode("utf-8"))
