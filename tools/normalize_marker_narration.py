#!/usr/bin/env python3
"""Normalize spoken list markers without changing their visible textbook form.

The character ``i`` is ambiguous.  In a run such as ``(a) … (i) … (j)`` it
is the letter i; in ``(i) (ii) (iii)`` it is a Roman numeral.  This script
uses the other markers on the same page as context, then makes the visible
marker aria-hidden and stores the unambiguous Swahili narration in a
screen-reader-only data-id sibling.  The same text ids drive Rehema audio.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LANG_DIR = ROOT / "content" / "i18n" / "sw-TZ"
TEXTS_PATH = LANG_DIR / "texts.json"
AUDIO_PATH = LANG_DIR / "audios.json"
CHANGED_IDS_PATH = LANG_DIR / "marker_narration_ids.json"

ROMAN = {
    "i": "moja", "ii": "mbili", "iii": "tatu", "iv": "nne",
    "v": "tano", "vi": "sita", "vii": "saba", "viii": "nane",
    "ix": "tisa", "x": "kumi",
}
LETTERS = set("abcdefghij")
MARKER = re.compile(r"\((x|ix|viii|vii|vi|iv|iii|ii|v|i|[a-j])\)", re.I)
ROMAN_RANGE = re.compile(
    r"\((x|ix|viii|vii|vi|iv|iii|ii|v|i)\)\s*[–-]\s*\((x|ix|viii|vii|vi|iv|iii|ii|v|i)\)",
    re.I,
)


def page_id(text_id: str) -> str | None:
    match = re.match(r"(pg\d{3})_", text_id)
    return match.group(1) if match else None


def classify_markers(texts: dict[str, str]) -> dict[str, set[str]]:
    """Return letter markers per text id, using adjacent marker context.

    The same page can contain both a Roman matching list and an alphabetical
    exercise.  For ambiguous `(i)`, immediate `(ii)/(iii)` neighbours win;
    otherwise adjacent `(a)`–`(h)` or `(j)` neighbours identify an alphabetic
    run.  A lone `(i)` remains Roman by default.
    """
    by_page: dict[str, list[tuple[str, list[str]]]] = defaultdict(list)
    for text_id, text in texts.items():
        if text_id.endswith("_easy_read"):
            continue
        page = page_id(text_id)
        markers = [match.group(1).lower() for match in MARKER.finditer(text)]
        if page and markers:
            by_page[page].append((text_id, markers))

    result: dict[str, set[str]] = defaultdict(set)
    for entries in by_page.values():
        labels = [(text_id, marker) for text_id, markers in entries for marker in markers]
        for index, (text_id, marker) in enumerate(labels):
            if marker != "i":
                if marker in LETTERS:
                    result[text_id].add(marker)
                continue
            neighbours = [
                other for _, other in labels[max(0, index - 2): index]
                + labels[index + 1: index + 3]
            ]
            if any(other in ROMAN and len(other) > 1 for other in neighbours):
                continue
            if any(other in LETTERS - {"i"} for other in neighbours):
                result[text_id].add(marker)
    return result


def spoken_text(text: str, letter_markers: set[str]) -> str:
    def replace_range(match: re.Match[str]) -> str:
        first, last = match.group(1).lower(), match.group(2).lower()
        return f"Namba za kirumi {ROMAN[first]} hadi namba za kirumi {ROMAN[last]}"

    text = ROMAN_RANGE.sub(replace_range, text)

    def replace_marker(match: re.Match[str]) -> str:
        marker = match.group(1).lower()
        if marker in letter_markers:
            return f"Herufi {marker}."
        if marker in ROMAN:
            return f"Namba za kirumi {ROMAN[marker]}."
        # This cannot occur for the current pattern, but keeps the visible
        # content safe if a new marker is introduced later.
        return match.group(0)

    return MARKER.sub(replace_marker, text)


def replace_html_id(source: str, text_id: str, spoken: str) -> tuple[str, bool]:
    """Keep the visual element, but move its data-id to an sr-only sibling."""
    escaped = re.escape(text_id)
    existing_sr = re.compile(
        rf'(<span[^>]*\sdata-id="{escaped}"[^>]*\bclass="[^"]*\bsr-only\b[^"]*"[^>]*>).*?(</span>)',
        re.DOTALL,
    )
    source, existing_count = existing_sr.subn(rf"\1{spoken}\2", source, count=1)
    if existing_count:
        return source, True
    pattern = re.compile(
        rf"<(?P<tag>[a-zA-Z][\w:-]*)(?P<before>[^>]*?)\sdata-id=\"{escaped}\"(?P<after>[^>]*)>(?P<body>.*?)</(?P=tag)>",
        re.DOTALL,
    )

    def replace(match: re.Match[str]) -> str:
        attrs = match.group("before") + match.group("after")
        if re.search(r'\bclass=\"[^\"]*\bsr-only\b', attrs):
            return match.group(0)
        if "aria-hidden=" not in attrs:
            attrs += ' aria-hidden="true"'
        visible = f"<{match.group('tag')}{attrs}>{match.group('body')}</{match.group('tag')}>"
        spoken_html = f'<span data-id="{text_id}" class="sr-only">{spoken}</span>'
        return visible + spoken_html

    updated, count = pattern.subn(replace, source, count=1)
    return updated, bool(count)


def main() -> None:
    texts = json.loads(TEXTS_PATH.read_text())
    audio = json.loads(AUDIO_PATH.read_text())
    # The source marker can already have been normalized by an interrupted
    # earlier run.  Read the committed source when available so reruns repair
    # rather than preserve a wrong earlier classification.
    try:
        baseline = json.loads(subprocess.check_output(
            ["git", "show", "HEAD:content/i18n/sw-TZ/texts.json"], cwd=ROOT, text=True
        ))
    except (subprocess.CalledProcessError, FileNotFoundError):
        baseline = texts
    letter_markers = classify_markers(baseline)
    changed: dict[str, str] = {}

    for text_id, value in baseline.items():
        page = page_id(text_id)
        if not page or text_id not in audio:
            continue
        normalized = spoken_text(
            value,
            letter_markers.get(text_id.removesuffix("_easy_read"), set()),
        )
        if normalized != value:
            changed[text_id] = normalized

    # This page uses a dedicated read-aloud id for its last visible Roman
    # marker.  Keep it aligned with the adjacent `(v)` item.
    for suffix in ("", "_easy_read"):
        if f"pg042_n0025_read{suffix}" in texts:
            changed[f"pg042_n0025_read{suffix}"] = "Namba za kirumi tano."

    for text_id, normalized in changed.items():
        texts[text_id] = normalized
    TEXTS_PATH.write_text(json.dumps(texts, ensure_ascii=False, indent=2) + "\n")
    CHANGED_IDS_PATH.write_text(json.dumps(sorted(changed), ensure_ascii=False, indent=2) + "\n")

    for html_path in sorted(ROOT.glob("pg*_sec*.html")):
        source = html_path.read_text()
        page_changes = [
            (text_id, spoken)
            for text_id, spoken in changed.items()
            if text_id.startswith(html_path.stem.split("_")[0] + "_") and not text_id.endswith("_easy_read")
        ]
        for text_id, spoken in page_changes:
            source, _ = replace_html_id(source, text_id, spoken)
        html_path.write_text(source)

    print(f"Normalized {len(changed)} marker narration entries using page context.")
    print("Alphabetical '(i)' entries:", ", ".join(
        key for key, value in sorted(changed.items()) if "Herufi i." in value
    ))
    print("Roman '(i)' entries:", ", ".join(
        key for key, value in sorted(changed.items()) if "Namba za kirumi moja." in value
    ))


if __name__ == "__main__":
    main()
