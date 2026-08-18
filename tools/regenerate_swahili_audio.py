#!/usr/bin/env python3
"""Regenerate this bundle's Swahili audio with Microsoft Edge TTS.

Speech-only substitutions make symbols unambiguous: ``-`` is spoken as
"dash", ``©`` as "Hakimiliki ya", and ``+`` as "alama ya kujumlisha".
``/`` is spoken as "mkwaju" and ``S.L.P`` is expanded to "Sanduku la posta".
The visible textbook text is unchanged.

The generator uses the Microsoft voice ``sw-TZ-RehemaNeural`` and does not
require an Azure Speech key. It requires the ``edge-tts`` Python package.

Run from the bundle root:
  python3 tools/regenerate_swahili_audio.py

Use --dry-run to inspect the scope, --page to target a page, and --limit for a
small verification batch.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

try:
    import edge_tts
except ModuleNotFoundError as error:
    raise SystemExit(
        "edge-tts is required. Install it with: python3 -m pip install edge-tts"
    ) from error


ROOT = Path(__file__).resolve().parents[1]
LANGUAGE = "sw-TZ"
VOICE = "sw-TZ-RehemaNeural"
ROMAN_ORDINALS = {
    "i": "kwanza",
    "ii": "pili",
    "iii": "tatu",
    "iv": "nne",
    "v": "tano",
    "vi": "sita",
    "vii": "saba",
    "viii": "nane",
    "ix": "tisa",
    "x": "kumi",
}
OPTION_LETTER_NAMES = {"a": "a", "b": "be", "c": "si", "d": "di"}


def speech_text(text: str) -> str:
    """Keep visible text intact while expanding symbols for natural speech."""
    expanded = (
        text.replace("S.L.P", "Sanduku la posta")
        .replace("©", "Hakimiliki ya ")
        .replace("+", "alama ya kujumlisha ")
        .replace("/", " mkwaju ")
        .replace("-", " dash ")
    )
    # Rehema should pronounce the standalone digit 4 as the full Swahili word.
    # Do not change digits embedded in phone numbers, postcodes, or dates.
    expanded = re.sub(r"(?<!\d)4(?!\d)", "nne", expanded)
    # Read answer labels as question items. In particular, C must not be read
    # as the Roman numeral one hundred.
    expanded = re.sub(
        r"^\s*\(?([a-d])\)?\.?\s*",
        lambda match: f"Kipengele {OPTION_LETTER_NAMES[match.group(1).lower()]}. ",
        expanded,
        flags=re.IGNORECASE,
    )
    expanded = re.sub(
        r"\((x|ix|viii|vii|vi|iv|iii|ii|v|i)\)\s*(?:[–-]|dash|hadi|mpaka)\s*\((x|ix|viii|vii|vi|iv|iii|ii|v|i)\)",
        lambda match: (
            f"kipengele cha {ROMAN_ORDINALS[match.group(1).lower()]} "
            f"mpaka kipengele cha {ROMAN_ORDINALS[match.group(2).lower()]}"
        ),
        expanded,
        flags=re.IGNORECASE,
    )
    return re.sub(
        r"\((x|ix|viii|vii|vi|iv|iii|ii|v|i)\)\s*",
        lambda match: f"Kipengele cha {ROMAN_ORDINALS[match.group(1).lower()]}. ",
        expanded,
        flags=re.IGNORECASE,
    )


async def synthesize(text: str, destination: Path) -> None:
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    for attempt in range(1, 4):
        try:
            await edge_tts.Communicate(speech_text(text), voice=VOICE).save(str(temporary))
            break
        except Exception:
            temporary.unlink(missing_ok=True)
            if attempt == 3:
                raise
            await asyncio.sleep(attempt)
    if temporary.stat().st_size == 0:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"Edge TTS returned an empty response for {destination.name}")
    temporary.replace(destination)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--page",
        action="append",
        metavar="NUMBER",
        help="Generate one page only (for example, --page 1 or --page 001). Can repeat.",
    )
    parser.add_argument("--limit", type=int, help="Generate only the first N files.")
    parser.add_argument(
        "--id",
        action="append",
        metavar="TEXT_ID",
        help="Generate one text ID only. Can repeat.",
    )
    parser.add_argument(
        "--numbered-items-only",
        action="store_true",
        help="Generate only activity labels expanded to 'Swali la …'.",
    )
    parser.add_argument(
        "--roman-items-only",
        action="store_true",
        help="Generate only entries containing Roman-numbered activity items.",
    )
    parser.add_argument(
        "--standalone-number",
        metavar="NUMBER",
        help="Generate entries containing this standalone numeral (for example, 4).",
    )
    parser.add_argument(
        "--skip",
        type=int,
        default=0,
        help="Skip the first N matching files (useful for resuming an interrupted batch).",
    )
    args = parser.parse_args()

    texts = json.loads((ROOT / "content/i18n" / LANGUAGE / "texts.json").read_text())
    audio_map = json.loads((ROOT / "content/i18n" / LANGUAGE / "audios.json").read_text())
    jobs = [(text_id, filename, texts[text_id]) for text_id, filename in audio_map.items() if text_id in texts]
    missing_text = sorted(set(audio_map) - set(texts))
    if missing_text:
        print(f"Error: {len(missing_text)} audio mappings have no text entry.", file=sys.stderr)
        return 2
    if args.page:
        prefixes = {f"pg{int(page):03d}_" for page in args.page}
        jobs = [job for job in jobs if job[0].startswith(tuple(prefixes))]
        if not jobs:
            print("Error: no audio matches the requested page number(s).", file=sys.stderr)
            return 2
    if args.id:
        wanted = set(args.id)
        jobs = [job for job in jobs if job[0] in wanted]
        missing = wanted - {job[0] for job in jobs}
        if missing:
            print(f"Error: no audio matches: {', '.join(sorted(missing))}", file=sys.stderr)
            return 2
    if args.numbered_items_only:
        jobs = [job for job in jobs if job[2].startswith("Swali la ")]
    if args.roman_items_only:
        roman_item = re.compile(
            r"\((?:x|ix|viii|vii|vi|iv|iii|ii|v|i)\)|"
            r"\bKipengele cha (?:kwanza|pili|tatu|nne|tano|sita|saba|nane|tisa|kumi)\b",
            flags=re.IGNORECASE,
        )
        jobs = [job for job in jobs if roman_item.search(job[2])]
    if args.standalone_number:
        number = re.escape(args.standalone_number)
        jobs = [job for job in jobs if re.search(rf"(?<!\d){number}(?!\d)", job[2])]
    if args.skip:
        jobs = jobs[args.skip :]
    if args.limit is not None:
        jobs = jobs[: args.limit]

    hyphenated = sum("-" in text for _, _, text in jobs)
    print(f"{len(jobs)} files queued; {hyphenated} contain a hyphen to pronounce as 'dash'.")
    if args.dry_run:
        return 0

    audio_directory = ROOT / "content/i18n" / LANGUAGE / "audio"

    for index, (_, filename, text) in enumerate(jobs, start=1):
        destination = audio_directory / filename
        await synthesize(text, destination)
        print(f"[{index}/{len(jobs)}] {filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
