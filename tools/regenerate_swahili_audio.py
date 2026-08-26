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
ROMAN_CARDINALS = {
    "i": "moja",
    "ii": "mbili",
    "iii": "tatu",
    "iv": "nne",
    "v": "tano",
    "vi": "sita",
    "vii": "saba",
    "viii": "nane",
    "ix": "tisa",
    "x": "kumi",
}
# A bare letter is often swallowed, interpreted as an English token, or (for
# ``i``) mistaken for a Roman numeral.  These are Tanzanian-Swahili letter
# names and are used only for synthesis; the visible textbook marker remains
# unchanged.
OPTION_LETTER_NAMES = {
    "a": "a",
    "b": "be",
    "c": "che",
    "d": "de",
    "e": "e",
    "f": "efu",
    "g": "gi",
    "h": "hech",
    # Doubling is phonetic only: it makes Rehema retain the Kiswahili /i/
    # sound instead of interpreting the marker as Roman numeral one.
    "i": "ii",
    "j": "je",
    "k": "ka",
    "l": "el",
    "m": "em",
    "n": "en",
    "o": "o",
    "p": "pe",
    "q": "ku",
    "r": "er",
    "s": "es",
    "t": "te",
    "u": "u",
    "v": "ve",
    "w": "we",
    "x": "eks",
    "y": "ye",
    "z": "zet",
}
ALPHABET_LABEL_PATTERN = re.compile(
    r"(?:\b(?:herufi|kipengele|chaguo|orodha)\s+(?:\(\s*)?[a-z](?=\s|[.)]))"
    r"|(?:^|\n)\s*(?:\([a-z]\)|[a-z]\.)",
    flags=re.IGNORECASE,
)


def speech_text(text: str) -> str:
    """Keep visible text intact while expanding symbols for natural speech."""
    # Guard against common TTS inflection errors without changing the reader's
    # visible textbook text.
    text = re.sub(r"\bne\b", "nne", text, flags=re.IGNORECASE)
    text = re.sub(r"\bshule\s+za\s+misingi\b", "shule za msingi", text, flags=re.IGNORECASE)
    text = re.sub(r"\bshule\s+ya\s+misingi\b", "shule ya msingi", text, flags=re.IGNORECASE)
    # Separating the repeated stem keeps Rehema from swallowing the initial
    # /m/ in “mbalimbali”; the visible textbook text remains unchanged.
    text = re.sub(r"\bvitu\s+mbalimbali\b", "vitu mbali mbali", text, flags=re.IGNORECASE)
    # The same repeated-stem issue occurs after “maumbo”; separating it makes
    # Rehema articulate the initial /m/ in “mbalimbali” clearly.
    text = re.sub(r"\bmaumbo\s+mbalimbali\b", "maumbo mbali mbali", text, flags=re.IGNORECASE)
    # Split the consonant cluster only for synthesis so Rehema retains the
    # /fi/ in “mfinyanzi” and does not stretch “wa”.
    text = re.sub(
        r"\budongo\s+wa\s+mfinyanzi\b",
        "udongo wa mfi nyanzi",
        text,
        flags=re.IGNORECASE,
    )
    # Keep both the /nj/ onset and every syllable of “mbalimbali” clear in
    # the “njia mbalimbali” construction.
    text = re.sub(r"\bnjia\s+mbalimbali\b", "ndjia mbali mbali", text, flags=re.IGNORECASE)
    text = re.sub(r"\bnjia\s+hizo\b", "ndjia hizo", text, flags=re.IGNORECASE)
    # A synthesis-only syllable break keeps Rehema from replacing the /ng/
    # cluster in “vyungu” with /mb/.
    text = re.sub(r"\bvyungu\b", "vyu ngu", text, flags=re.IGNORECASE)
    # Keep the /ng/ cluster in “viungo” distinct from /mb/, and give “hayo” a
    # natural boundary after “mazoezi”.
    text = re.sub(r"\bmazoezi\s+ya\s+viungo\b", "mazoezi ya vi u ngo", text, flags=re.IGNORECASE)
    text = re.sub(r"\bmazoezi\s+hayo\b", "mazoezi, hayo", text, flags=re.IGNORECASE)
    # Separate the English animal name into its two clear sound units for the
    # Swahili voice; the visible textbook spelling remains “kangaroo”.
    text = re.sub(r"\bkangaroo\b", "kanga roo", text, flags=re.IGNORECASE)
    # A brief word boundary keeps the singular “mchezo” from being blended
    # into the plural-sounding “michezo” before “huu”.
    text = re.sub(r"\bmchezo\s+huu\b", "mchezo, huu", text, flags=re.IGNORECASE)
    # Preserve the /p/ in “kukwepa”; Rehema can otherwise blend the cluster
    # into the unrelated verb “kukweta”.
    text = re.sub(r"\bkukwepa\b", "ku kwepa", text, flags=re.IGNORECASE)
    # Preserve the doubled /m/ onset in “mmoja” so it is not expanded into
    # the incorrect “mumoja”.
    text = re.sub(r"\bmmoja\b", "mmo ja", text, flags=re.IGNORECASE)
    # Keep the singular noun intact before “wa rede”; without a boundary the
    # voice can turn “mchezo” into the plural-sounding “michezo”.
    text = re.sub(r"\bmchezo\s+wa\s+rede\b", "mchezo, wa rede", text, flags=re.IGNORECASE)
    # These boundaries protect singular words and ordinal wording that Rehema
    # otherwise blends or expands incorrectly in the exercise instructions.
    text = re.sub(r"\bZoezi\s+la\s+2\b", "Zoezi la pili", text, flags=re.IGNORECASE)
    text = re.sub(r"\bmchezo\s+wa\s+kuchezea\b", "mchezo, wa kuchezea", text, flags=re.IGNORECASE)
    text = re.sub(r"\bkufanya\s+maandalizi\b", "kufanya, maandalizi", text, flags=re.IGNORECASE)
    text = re.sub(r"\blitafanyika;\s*na\b", "litafanyika, na", text, flags=re.IGNORECASE)
    text = re.sub(r"\bmchezo\s+husika\b", "mchezo, husika", text, flags=re.IGNORECASE)
    # Rehema softens the prenasalized affricate in “njuga” to /ny/.  The
    # synthesis-only spelling preserves the audible /nj/ while the textbook
    # continues to display the correct word, “njuga”.
    text = re.sub(r"\bnjuga\b", "ndjuga", text, flags=re.IGNORECASE)
    # A micro-pause prevents the voice from stretching the last vowel in
    # “mti” when it is immediately followed by “chenye”.
    text = re.sub(r"\bmti\s+(?=chenye\b)", "mti, ", text, flags=re.IGNORECASE)
    # Domains must be spelled out; passing the dotted form directly to a TTS
    # engine makes it treat portions as abbreviations or words.  Keep this
    # before the symbol substitutions so the visible text is never changed.
    text = re.sub(
        r"\bwww\.tie\.go\.tz\b",
        "w w w nukta t i e nukta g o nukta t z",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bdirector\.general@tie\.go\.tz\b",
        "director nukta general at t i e nukta g o nukta t z",
        text,
        flags=re.IGNORECASE,
    )
    # The Rehema voice can mistake the English airline name "Air" for a
    # Swahili letter name. This spelling directs the Swahili voice to the
    # English /eər/ sound without changing the displayed textbook text.
    text = re.sub(
        r"\bAir Tanzania\b", "Eir Tanzania", text, flags=re.IGNORECASE
    )
    expanded = (
        text.replace("S.L.P", "Sanduku la posta")
        .replace("©", "Hakimiliki ya ")
        .replace("+", "alama ya kujumlisha ")
        .replace("/", " mkwaju ")
        .replace("-", " dash ")
    )
    # Official titles and the book publisher's abbreviation are expanded only
    # for speech; the visible PDF text stays unchanged.
    expanded = re.sub(r"\bDkt\.\s*", "Daktari ", expanded, flags=re.IGNORECASE)
    expanded = re.sub(r"\bBw\.\s*", "Bwana ", expanded, flags=re.IGNORECASE)
    expanded = re.sub(r"\bTET\b", "T E T", expanded)
    # Rehema should pronounce the standalone digit 4 as the full Swahili word.
    # Do not change digits embedded in phone numbers, postcodes, or dates.
    expanded = re.sub(r"(?<!\d)4(?!\d)", "nne", expanded)
    # Standardize figure labels so variants such as "Kielelezo Na 5" are
    # spoken naturally as "Kielelezo namba 5".
    expanded = re.sub(
        r"\bKielelezo\s+(?:Na\.?|Namba)\s*(?=\d)",
        "Kielelezo namba ",
        expanded,
        flags=re.IGNORECASE,
    )
    # Convert Roman-numeral ranges before treating parenthesized single
    # letters as alphabet markers.
    expanded = re.sub(
        r"\((x|ix|viii|vii|vi|iv|iii|ii|v|i)\)\s*(?:[–-]|dash|hadi|mpaka)\s*\((x|ix|viii|vii|vi|iv|iii|ii|v|i)\)",
        lambda match: (
            f"Namba za kirumi {ROMAN_CARDINALS[match.group(1).lower()]} "
            f"hadi namba za kirumi {ROMAN_CARDINALS[match.group(2).lower()]}"
        ),
        expanded,
        flags=re.IGNORECASE,
    )
    # All alphabetic labels receive an explicit “Herufi” prefix.  This covers
    # existing “Herufi a”, answer choices, list items, and identification
    # labels while leaving ordinary words and people’s initials untouched.
    expanded = re.sub(
        r"\bHerufi\s*(?:\(\s*)?([a-z])\s*\)?\.?",
        lambda match: f"Herufi {OPTION_LETTER_NAMES[match.group(1).lower()] }.",
        expanded,
        flags=re.IGNORECASE,
    )
    expanded = re.sub(
        r"\b(Kipengele|Chaguo|Orodha)\s+([a-z])(?=\s|[.:;,)])",
        lambda match: (
            f"{match.group(1)} Herufi "
            f"{OPTION_LETTER_NAMES[match.group(2).lower()]}"
        ),
        expanded,
        flags=re.IGNORECASE,
    )
    expanded = re.sub(
        r"(?:^|\n)\s*(?:\(([a-z])\)|([a-z])\.)\s*",
        lambda match: (
            f"{match.group(0)[:1] if match.group(0).startswith(chr(10)) else ''}"
            f"Herufi {OPTION_LETTER_NAMES[(match.group(1) or match.group(2)).lower()]}. "
        ),
        expanded,
        flags=re.IGNORECASE,
    )
    # A remaining parenthesized single letter is an alphabet marker (for
    # example, “(i)”) and not a Roman range.  Explicit context avoids “moja”.
    expanded = re.sub(
        r"\(\s*([a-z])\s*\)",
        lambda match: f"Herufi {OPTION_LETTER_NAMES[match.group(1).lower()]}",
        expanded,
        flags=re.IGNORECASE,
    )
    return re.sub(
        r"\((x|ix|viii|vii|vi|iv|iii|ii|v|i)\)\s*",
        lambda match: f"Namba za kirumi {ROMAN_CARDINALS[match.group(1).lower()]}. ",
        expanded,
        flags=re.IGNORECASE,
    )


async def synthesize(text: str, destination: Path, voice: str) -> None:
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    for attempt in range(1, 4):
        try:
            await asyncio.wait_for(
                edge_tts.Communicate(speech_text(text), voice=voice).save(str(temporary)),
                timeout=45,
            )
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
        "--voice",
        default=VOICE,
        help=f"Microsoft neural voice to use (default: {VOICE}).",
    )
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
        "--ids-file",
        type=Path,
        help="JSON array of text IDs to generate (for audited narration batches).",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of Rehema requests to generate in parallel (default: 1).",
    )
    parser.add_argument(
        "--contains",
        action="append",
        metavar="TEXT",
        help="Generate entries whose text contains this value. Can repeat.",
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
        "--letter-items-only",
        action="store_true",
        help="Generate only entries beginning with a lettered item such as (a).",
    )
    parser.add_argument(
        "--alphabet-labels-only",
        action="store_true",
        help="Generate all entries that identify an alphabet letter or use it as a label.",
    )
    parser.add_argument(
        "--question-labels-only",
        action="store_true",
        help="Generate only labels beginning with 'Swali namba'.",
    )
    parser.add_argument(
        "--step-labels-only",
        action="store_true",
        help="Generate only labels beginning with 'Hatua ya'.",
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
    if args.ids_file:
        wanted = set(json.loads(args.ids_file.read_text()))
        jobs = [job for job in jobs if job[0] in wanted]
        missing = wanted - {job[0] for job in jobs}
        if missing:
            print(f"Error: no audio matches: {', '.join(sorted(missing))}", file=sys.stderr)
            return 2
    if args.contains:
        needles = [needle.casefold() for needle in args.contains]
        jobs = [job for job in jobs if all(needle in job[2].casefold() for needle in needles)]
    if args.numbered_items_only:
        jobs = [job for job in jobs if job[2].startswith("Swali la ")]
    if args.roman_items_only:
        roman_item = re.compile(
            r"\((?:x|ix|viii|vii|vi|iv|iii|ii|v|i)\)",
            flags=re.IGNORECASE,
        )
        jobs = [job for job in jobs if roman_item.search(job[2])]
    if args.letter_items_only:
        jobs = [job for job in jobs if re.match(r"\s*\([a-d]\)", job[2], re.IGNORECASE)]
    if args.alphabet_labels_only:
        jobs = [job for job in jobs if ALPHABET_LABEL_PATTERN.search(job[2])]
    if args.question_labels_only:
        jobs = [job for job in jobs if job[2].startswith("Swali namba ")]
    if args.step_labels_only:
        jobs = [job for job in jobs if job[2].startswith("Hatua ya ")]
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

    concurrency = max(1, args.concurrency)
    semaphore = asyncio.Semaphore(concurrency)

    async def generate(index: int, filename: str, text: str) -> None:
        async with semaphore:
            await synthesize(text, audio_directory / filename, args.voice)
            print(f"[{index}/{len(jobs)}] {filename}")

    await asyncio.gather(*(
        generate(index, filename, text)
        for index, (_, filename, text) in enumerate(jobs, start=1)
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
