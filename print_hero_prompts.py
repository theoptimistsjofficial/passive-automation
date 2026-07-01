#!/usr/bin/env python
"""Print the AI-optimized prompts for hero slides of the next video in a niche.

Use this to plan cloud AI generation (Kling/Vidu/Hailuo). Copy the printed prompts,
paste into the cloud tool, generate the clips, drop them in io_data/heroshots/{niche}/.

Usage:
    python print_hero_prompts.py positive_thinking
    python print_hero_prompts.py devotional
"""
import sys

from core.config import CHANNEL_NAME, load_niche
from agents.topic_picker import pick_next_topic
from agents.script_writer import write_script
from agents.visual_planner import enrich_stock_queries
from agents.scene_director import (
    choose_hero_indices,
    enhance_prompt_for_ai,
    get_negative_prompt,
)


def main():
    if len(sys.argv) < 2:
        print("Usage: python print_hero_prompts.py <niche_key>")
        print("Available niches: positive_thinking, devotional")
        sys.exit(1)

    niche_key = sys.argv[1]
    niche = load_niche(niche_key)
    topic = pick_next_topic(niche)
    script = write_script(topic, niche, channel=CHANNEL_NAME)
    script = enrich_stock_queries(script, niche)
    hero_indices = choose_hero_indices(script, niche)
    negative = get_negative_prompt(niche)

    print("=" * 78)
    print(f"Niche:  {niche_key}")
    print(f"Topic:  {topic['id']} — {topic.get('title', '')}")
    print(f"Hero slides: {hero_indices} of {len(script.slides)}")
    print(f"Drop generated clips into: io_data/heroshots/{niche_key}/")
    print("=" * 78)
    print()

    for slide in script.slides:
        if slide.index not in hero_indices:
            continue
        prompt = enhance_prompt_for_ai(slide.narration, slide.stock_query, niche)
        filename = f"slide_{slide.index:02d}.mp4"
        print(f"### {filename}  (slide {slide.index})")
        print()
        print(f"NARRATION: {slide.narration[:150]}...")
        print()
        print(f"POSITIVE PROMPT (paste this):")
        print(prompt)
        print()
        print(f"NEGATIVE PROMPT (if the tool has one):")
        print(negative)
        print()
        print("-" * 78)
        print()


if __name__ == "__main__":
    main()
