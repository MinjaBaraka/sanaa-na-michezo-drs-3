#!/usr/bin/env python3
"""Synchronize local JSON and HTML resources into offline-preloader.js."""

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

    updated = []
    for key in inline:
        if not key.startswith("./"):
            continue

        path = (ROOT / key.removeprefix("./")).resolve()
        if ROOT not in path.parents or not path.is_file():
            continue

        if path.suffix == ".json":
            inline[key] = json.loads(path.read_text())
        elif path.suffix == ".html":
            inline[key] = path.read_text()
        else:
            continue
        updated.append(key)

    serialized = json.dumps(inline, ensure_ascii=False, separators=(",", ":"))
    PRELOADER.write_text(source[:start] + serialized + source[end:])
    print(f"Synchronized {len(updated)} local JSON/HTML resources for offline use.")


if __name__ == "__main__":
    main()
