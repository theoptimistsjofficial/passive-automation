from core.schemas import VideoScript, SEOPackage
from core.logger import get_logger
from services.llm import generate_json

log = get_logger("seo")


PROMPT = """Generate YouTube SEO metadata for this video. Return STRICT JSON:

{{
  "title": "click-optimized title, max 100 chars, no clickbait spam",
  "description": "3-paragraph description. Para 1: hook. Para 2: what viewer learns. Para 3: CTAs + hashtags.",
  "tags": ["12-15 broad-to-narrow tags"],
  "hashtags": ["3-5 hashtags with # included"]
}}

Working title: {title}
Hook: {hook}
Niche: {niche}
Slides summary: {slides}
"""


def build_seo(script: VideoScript, niche: dict) -> SEOPackage:
    slides_summary = " | ".join([s.heading for s in script.slides])
    prompt = PROMPT.format(
        title=script.title_working,
        hook=script.hook,
        niche=niche["display_name"],
        slides=slides_summary,
    )
    try:
        raw = generate_json(prompt)
        pkg = SEOPackage(**raw)
        log.info(f"SEO built: {pkg.title[:60]}...")
        return pkg
    except Exception as e:
        log.warning(f"SEO LLM failed ({e}); using deterministic fallback")
        title = script.title_working[:97] + "..." if len(script.title_working) > 100 else script.title_working
        desc = (
            f"{script.hook}\n\n"
            f"In this video you'll learn: {slides_summary}.\n\n"
            f"{script.cta}\n\n"
            f"#OptimistMantra #Motivation #Inspiration"
        )
        base_tags = ["motivation", "inspiration", "real story", "resilience", "overcoming challenges"]
        if niche["_key"] == "devotional":
            base_tags = ["kanda shashti kavasam", "murugan", "tamil devotional", "verse meaning", "hindu spirituality"]
        return SEOPackage(
            title=title,
            description=desc,
            tags=base_tags + ["OptimistMantra", "shorts", "youtube shorts"],
            hashtags=["#OptimistMantra", "#Motivation", "#Shorts"],
        )
