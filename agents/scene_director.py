"""Decides which slides should get AI-generated video vs stock footage.

Strategy: AI-generate the highest-impact slides (hook + climax), stock for the rest.
This keeps quota usage low while maximizing perceived quality where it matters.
"""
from typing import List
from core.schemas import VideoScript
from core.logger import get_logger

log = get_logger("scene_director")


def choose_hero_indices(script: VideoScript, niche: dict) -> List[int]:
    """Return 1-based slide indices that should use AI-generated video.

    Default: hook (slide 1) and the middle slide (climax proxy).
    Configurable via niche['ai_video']['hero_slides'] (list of 1-based ints or 'hook'/'middle'/'cta').
    """
    ai_cfg = niche.get("ai_video", {})
    hero_spec = ai_cfg.get("hero_slides", ["hook", "middle"])

    total = len(script.slides)
    if total == 0:
        return []

    aliases = {
        "hook": 1,
        "middle": (total // 2) + 1,
        "cta": total,
        "outro": total,
    }
    resolved = set()
    for item in hero_spec:
        if isinstance(item, str):
            idx = aliases.get(item.lower())
            if idx is not None and 1 <= idx <= total:
                resolved.add(idx)
        elif isinstance(item, int) and 1 <= item <= total:
            resolved.add(item)

    result = sorted(resolved)
    log.info(f"Hero slides for AI: {result} of {total}")
    return result


def enhance_prompt_for_ai(slide_narration: str, slide_query: str, niche: dict) -> str:
    """Craft a Wan-optimized prompt from the slide's stock query + narration.

    Wan 2.2 responds best to:
    - Concrete visual subjects (not abstract concepts)
    - Camera/lighting direction
    - Style anchors that match the niche
    - Motion cues ('slow zoom', 'gentle sway') — Wan tends to produce static clips otherwise
    """
    ai_cfg = niche.get("ai_video", {})
    style = ai_cfg.get("wan_prompt_style",
                       niche.get("stock_query_style", "cinematic, high production value"))

    subject = slide_query.strip()
    context_hint = slide_narration.strip()[:120]

    prompt = (
        f"{subject}. {style}. "
        f"Subject context: {context_hint}. "
        "Cinematic composition, deliberate slow camera motion, professional colour grade. "
        "No text overlays, no logos, no captions in frame."
    )
    return prompt


def get_negative_prompt(niche: dict) -> str:
    ai_cfg = niche.get("ai_video", {})
    return ai_cfg.get(
        "wan_negative_prompt",
        "text, watermark, logo, low quality, blurry, distorted, static image, still photo",
    )
