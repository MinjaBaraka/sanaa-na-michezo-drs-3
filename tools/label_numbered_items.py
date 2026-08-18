#!/usr/bin/env python3
"""Make numbered activity items speak as Swahili question labels.

Visible numbers stay in the HTML; only the Read Aloud text is expanded.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXTS = ROOT / "content/i18n/sw-TZ/texts.json"
PRELOADER = ROOT / "assets/offline-preloader.js"
WORDS = {
    1: "kwanza", 2: "pili", 3: "tatu", 4: "nne", 5: "tano", 6: "sita",
    7: "saba", 8: "nane", 9: "tisa", 10: "kumi", 11: "kumi na moja", 12: "kumi na mbili",
}

texts = json.loads(TEXTS.read_text())
audio = json.loads((ROOT / "content/i18n/sw-TZ/audios.json").read_text())
changed = {}
for text_id, value in texts.items():
    match = re.fullmatch(r"\s*(\d+)[.)]\s*", value)
    if match and text_id in audio and int(match.group(1)) in WORDS:
        changed[text_id] = f"Swali la {WORDS[int(match.group(1))]}"

# Include labels already converted during an earlier run so the offline audio
# cache can always be repaired idempotently.
numbered_label_ids = {
    text_id for text_id, value in texts.items()
    if text_id in audio and value.startswith("Swali la ")
}

for text_id, value in changed.items():
    texts[text_id] = value
TEXTS.write_text(json.dumps(texts, ensure_ascii=False, indent=2) + "\n")

for html in ROOT.glob("pg*_sec*.html"):
    source = html.read_text()
    for text_id, spoken in changed.items():
        if text_id.endswith("_easy_read"):
            continue
        pattern = rf'(<(?P<tag>\w+)(?P<attrs>[^>]*?)\sdata-id="{re.escape(text_id)}"(?P<after>[^>]*)>)(?P<number>\s*\d+[.)]\s*)(</(?P=tag)>)'
        def replace(match):
            attrs = match.group("attrs") + match.group("after")
            attrs = re.sub(r'\sdata-id="[^"]+"', "", attrs)
            return (f'<{match.group("tag")}{attrs} aria-hidden="true">{match.group("number")}</{match.group("tag")}>'
                    f'<span data-id="{text_id}" class="sr-only">{spoken}</span>')
        source = re.sub(pattern, replace, source)
    html.write_text(source)

preloader = PRELOADER.read_text()
# The preloader contains both texts.json and audios.json.  Only replace values
# in the texts cache; altering the audio cache would turn an MP3 filename into
# spoken text and stop Read Aloud at that item.
texts_start = preloader.index('"./content/i18n/sw-TZ/texts.json":')
audios_start = preloader.index('"./content/i18n/sw-TZ/audios.json":')
texts_cache = preloader[texts_start:audios_start]
for text_id, spoken in changed.items():
    texts_cache = re.sub(
        rf'("{re.escape(text_id)}":)"[^"]*"',
        rf'\1{json.dumps(spoken, ensure_ascii=False)}',
        texts_cache,
    )
preloader = preloader[:texts_start] + texts_cache + preloader[audios_start:]

# Repair the audio cache from the authoritative audio mapping. This also fixes
# caches written by an earlier version of this script.
for text_id in numbered_label_ids:
    filename = audio[text_id]
    pattern = rf'("{re.escape(text_id)}":)"[^"]*"'
    before = preloader[:audios_start]
    after = preloader[audios_start:]
    after = re.sub(pattern, rf'\1{json.dumps(filename)}', after, count=1)
    preloader = before + after
PRELOADER.write_text(preloader)
print(f"Updated {len(changed)} Read Aloud labels.")
