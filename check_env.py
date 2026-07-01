#!/usr/bin/env python
"""Print .env key status — what's loaded, what's missing.

Usage:
    python check_env.py
"""
from core.config import (
    GEMINI_API_KEY,
    PEXELS_API_KEY,
    ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE_ID,
    ELEVENLABS_MODEL,
    GOOGLE_TTS_API_KEY,
    GOOGLE_TTS_VOICE,
    GOOGLE_TTS_LANG,
    FAL_API_KEY,
    FAL_MODEL,
    PIXABAY_API_KEY,
    CHANNEL_NAME,
)


def show(name: str, val: str, required: bool = False, secret: bool = True):
    if not val:
        marker = "[MISSING] required" if required else "[skip] not set (optional)"
        print(f"  {name:22} {marker}")
        return
    if secret and len(val) > 12:
        display = f"{val[:6]}...{val[-4:]} ({len(val)} chars)"
    else:
        display = val
    print(f"  {name:22} [OK]  {display}")


def main():
    print("=" * 70)
    print("PASSIVE AUTOMATION — .env status")
    print("=" * 70)

    print("\n[REQUIRED FOR AI VIDEO]")
    show("FAL_API_KEY", FAL_API_KEY, required=True)
    show("FAL_MODEL", FAL_MODEL, secret=False)

    print("\n[REQUIRED FOR HUMAN VOICE — set at least one]")
    show("GOOGLE_TTS_API_KEY", GOOGLE_TTS_API_KEY)
    show("GOOGLE_TTS_VOICE", GOOGLE_TTS_VOICE, secret=False)
    show("GOOGLE_TTS_LANG", GOOGLE_TTS_LANG, secret=False)
    show("ELEVENLABS_API_KEY", ELEVENLABS_API_KEY)
    show("ELEVENLABS_VOICE_ID", ELEVENLABS_VOICE_ID, secret=False)
    show("ELEVENLABS_MODEL", ELEVENLABS_MODEL, secret=False)

    print("\n[REQUIRED FOR REAL SCRIPT]")
    show("GEMINI_API_KEY", GEMINI_API_KEY, required=True)

    print("\n[REQUIRED FOR STOCK VIDEO]")
    show("PEXELS_API_KEY", PEXELS_API_KEY, required=True)

    print("\n[OPTIONAL — BGM]")
    show("PIXABAY_API_KEY", PIXABAY_API_KEY)

    print("\n[CHANNEL]")
    show("CHANNEL_NAME", CHANNEL_NAME, secret=False)

    print("\n" + "=" * 70)

    missing = []
    if not FAL_API_KEY:
        missing.append("FAL_API_KEY")
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not PEXELS_API_KEY:
        missing.append("PEXELS_API_KEY")
    if not GOOGLE_TTS_API_KEY and not ELEVENLABS_API_KEY:
        missing.append("GOOGLE_TTS_API_KEY or ELEVENLABS_API_KEY")

    if missing:
        print(f"WARNING: Missing {len(missing)} required key(s): {', '.join(missing)}")
        print("         Pipeline will still run but fall back to lower-quality alternatives.")
    else:
        print("SUCCESS: All required keys loaded. Ready to generate.")


if __name__ == "__main__":
    main()
