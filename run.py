#!/usr/bin/env python
"""Entrypoint: generates one video end-to-end using the currently configured niche.

Usage:
    python run.py                     # uses DEFAULT_NICHE from .env
    python run.py positive_thinking   # override niche
    python run.py devotional --mark-done
"""
import sys
from pipeline.daily_run import run


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]

    niche = args[0] if args else None
    mark_done = "--mark-done" in flags

    result = run(niche_key=niche, mark_done=mark_done)

    print("\n" + "=" * 70)
    print(f"DONE: {result.mp4_path}")
    print(f"Duration: {result.duration_seconds:.1f}s")
    print(f"Title:    {result.seo.title}")
    print(f"Tags:     {', '.join(result.seo.tags[:6])}...")
    print("=" * 70)


if __name__ == "__main__":
    main()
