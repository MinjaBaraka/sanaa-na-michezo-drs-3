#!/usr/bin/env python3
"""Synchronize editable localization manifests into offline-preloader.js."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRELOADER = ROOT / "assets" / "offline-preloader.js"
START = "  var INLINE = "
END = ";\n  var BASE_DIR = "


def main() -> None:
    source = PRELOADER.read_text()
    start = source.index(START) + len(START)
    end = source.index(END, start)
    inline = json.loads(source[start:end])

    json_resources = [
        "content/i18n/sw-TZ/texts.json",
        "content/i18n/sw-TZ/audios.json",
    ]
    for resource in json_resources:
        key = f"./{resource}"
        if key in inline:
            inline[key] = json.loads((ROOT / resource).read_text())

    serialized = json.dumps(inline, ensure_ascii=False, separators=(",", ":"))
    PRELOADER.write_text(source[:start] + serialized + source[end:])
    print("Synchronized offline texts and audio mappings.")


if __name__ == "__main__":
    main()
