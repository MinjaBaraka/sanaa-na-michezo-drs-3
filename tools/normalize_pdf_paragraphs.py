#!/usr/bin/env python3
"""Keep source-PDF paragraphs intact in the Easy Read presentation.

An Easy Read value with hard line breaks is rendered by the ADT runtime as
``<br>`` elements.  When that value belongs to one source paragraph, those
breaks turn a PDF paragraph into an unintended list.  This audit locates text
IDs inside ``<p>`` elements across the exported book and restores only the
line-broken Easy Read entries to their source-text counterparts.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXTS_PATH = ROOT / "content/i18n/sw-TZ/texts.json"
CHANGED_IDS_PATH = ROOT / "content/i18n/sw-TZ/paragraph_source_ids.json"
PAGE_FILES = sorted(ROOT.glob("pg*_sec001.html")) + [ROOT / "index.html"]
PARAGRAPH_RE = re.compile(r"<p\b[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)
DATA_ID_RE = re.compile(r'data-id="([^"]+)"', re.IGNORECASE)


def paragraph_ids() -> set[str]:
    ids: set[str] = set()
    for page in PAGE_FILES:
        html = page.read_text(encoding="utf-8")
        for paragraph in PARAGRAPH_RE.findall(html):
            ids.update(DATA_ID_RE.findall(paragraph))
    return ids


def main() -> None:
    texts = json.loads(TEXTS_PATH.read_text(encoding="utf-8"))
    changed: list[str] = []
    for text_id in sorted(paragraph_ids()):
        easy_id = f"{text_id}_easy_read"
        source_text = texts.get(text_id)
        easy_text = texts.get(easy_id)
        if not isinstance(source_text, str) or not isinstance(easy_text, str):
            continue
        if "\n" not in easy_text:
            continue
        texts[easy_id] = source_text
        changed.append(easy_id)

    TEXTS_PATH.write_text(
        json.dumps(texts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    CHANGED_IDS_PATH.write_text(
        json.dumps(changed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Restored {len(changed)} source-PDF paragraph values.")


if __name__ == "__main__":
    main()
