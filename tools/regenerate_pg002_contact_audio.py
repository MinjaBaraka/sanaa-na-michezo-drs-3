#!/usr/bin/env python3
"""Create mixed-voice contact and web-link narration.

The Swahili labels use Rehema Natural (sw-TZ), while the email address and
website use Imani (en-TZ) for clear letter-by-letter pronunciation.  Each
pair is concatenated into the single MP3 referenced by the book manifest.
"""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
from pathlib import Path

import edge_tts


ROOT = Path(__file__).resolve().parents[1]
AUDIO_DIR = ROOT / "content" / "i18n" / "sw-TZ" / "audio"
REHEMA = "sw-TZ-RehemaNeural"
IMANI = "en-TZ-ImaniNeural"
JOBS = {
    "pg002_n0013.mp3": ("Baruapepe:", "director dot general at t i e dot g o dot t z"),
    "pg002_n0013_easy_read.mp3": ("Baruapepe:", "director dot general at t i e dot g o dot t z"),
    "pg002_n0014.mp3": ("Tovuti:", "w w w dot t i e dot g o dot t z"),
    "pg002_n0014_easy_read.mp3": ("Tovuti:", "w w w dot t i e dot g o dot t z"),
    "pg006_n0016.mp3": ("Jifunze zaidi kupitia Maktaba Mtandao:", "H T T P S colon slash slash O L dot T I E dot G O dot T Z."),
    "pg006_n0016_easy_read.mp3": ("Jifunze zaidi kupitia Maktaba Mtandao:", "H T T P S colon slash slash O L dot T I E dot G O dot T Z."),
    "pg006_n0017.mp3": ("au", "O L dot T I E dot G O dot T Z."),
    "pg006_n0017_easy_read.mp3": ("au", "O L dot T I E dot G O dot T Z."),
}


async def save(text: str, voice: str, destination: Path) -> None:
    await edge_tts.Communicate(text, voice=voice).save(str(destination))


async def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pg002-contact-") as temp_name:
        temp = Path(temp_name)
        for filename, (label, contact) in JOBS.items():
            label_mp3 = temp / f"{filename}.label.mp3"
            contact_mp3 = temp / f"{filename}.contact.mp3"
            playlist = temp / f"{filename}.concat.txt"
            await save(label, REHEMA, label_mp3)
            await save(contact, IMANI, contact_mp3)
            playlist.write_text(
                f"file '{label_mp3}'\nfile '{contact_mp3}'\n",
                encoding="utf-8",
            )
            output = AUDIO_DIR / filename
            temporary = output.with_suffix(".tmp.mp3")
            subprocess.run(
                [
                    "ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", str(playlist), "-c:a", "libmp3lame", "-q:a", "2", str(temporary),
                ],
                check=True,
            )
            temporary.replace(output)
            print(f"Updated {filename}")


if __name__ == "__main__":
    asyncio.run(main())
