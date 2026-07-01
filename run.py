#!/usr/bin/env python
"""Entrypoint: generates one video end-to-end using the currently configured niche.

Usage:
    python run.py                                        # uses DEFAULT_NICHE from .env
    python run.py positive_thinking                      # override niche
    python run.py devotional --mark-done                 # mark topic complete after
    python run.py positive_thinking --upload             # also upload to YouTube (unlisted)
    python run.py positive_thinking --upload --public    # publish publicly
"""
import sys
from pipeline.daily_run import run


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]

    niche = args[0] if args else None
    mark_done = "--mark-done" in flags
    upload = "--upload" in flags
    if "--public" in flags:
        privacy = "public"
    elif "--private" in flags:
        privacy = "private"
    else:
        privacy = "unlisted"

    result = run(niche_key=niche, mark_done=mark_done, upload=upload, privacy=privacy)

    print("\n" + "=" * 70)
    print(f"DONE: {result.mp4_path}")
    print(f"Duration: {result.duration_seconds:.1f}s")
    print(f"Title:    {result.seo.title}")
    print(f"Tags:     {', '.join(result.seo.tags[:6])}...")
    if result.youtube_video_id:
        print(f"YouTube:  https://youtu.be/{result.youtube_video_id} ({privacy})")
    print("=" * 70)


if __name__ == "__main__":
    main()
