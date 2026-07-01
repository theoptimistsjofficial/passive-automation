from pathlib import Path
from datetime import datetime
import json

from core.config import ROOT, CHANNEL_NAME, load_niche
from core.schemas import RenderedVideo
from core.logger import get_logger
from agents.topic_picker import pick_next_topic
from agents.script_writer import write_script
from agents.visual_planner import enrich_stock_queries
from agents.seo_optimizer import build_seo
from agents.quality_reviewer import review
from services.tts import synthesize
from services.stock import fetch_scene
from services.renderer import build_video
from services.ai_video import generate_scene
from agents.scene_director import choose_hero_indices, enhance_prompt_for_ai

log = get_logger("pipeline")


def run(niche_key: str | None = None, mark_done: bool = False) -> RenderedVideo:
    niche = load_niche(niche_key)
    log.info(f"=== Pipeline start | channel={CHANNEL_NAME} | niche={niche['_key']} ===")

    topic = pick_next_topic(niche)

    script = write_script(topic, niche, channel=CHANNEL_NAME)
    script = enrich_stock_queries(script, niche)

    verdict = review(script, niche)
    if not verdict.approved:
        raise RuntimeError(f"Script rejected by QA: {verdict.reasons}")

    seo = build_seo(script, niche)

    workdir = ROOT / "io_data" / "output" / "temp" / topic["id"]
    workdir.mkdir(parents=True, exist_ok=True)

    audio_paths = []
    bg_paths = []
    prefer_video = niche.get("prefer_stock_video", True)

    ai_cfg = niche.get("ai_video", {})
    ai_enabled = ai_cfg.get("enabled", False)
    ai_providers = ai_cfg.get("providers", ["wan_local"])
    hero_indices = choose_hero_indices(script, niche) if ai_enabled else []

    for slide in script.slides:
        audio_path = workdir / f"narr_{slide.index:02d}.mp3"
        synthesize(slide.narration, audio_path, lang=niche["tts_lang"], slow=niche["tts_slow"])
        audio_paths.append(audio_path)

        bg_stem = workdir / f"bg_{slide.index:02d}"
        bg_path = None
        if slide.index in hero_indices:
            ai_prompt = enhance_prompt_for_ai(slide.narration, slide.stock_query, niche)
            ai_out = bg_stem.with_suffix(".mp4")
            log.info(f"Slide {slide.index}: AI video (hero) — providers={ai_providers}")
            bg_path = generate_scene(ai_prompt, ai_out, ai_providers, duration_sec=5.0, aspect="16:9")
            if bg_path is None:
                log.warning(f"Slide {slide.index}: all AI providers failed, falling back to stock")

        if bg_path is None:
            bg_path = fetch_scene(slide.stock_query, bg_stem, niche, prefer_video=prefer_video)
        bg_paths.append(bg_path)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_mp4 = ROOT / "io_data" / "output" / f"{topic['id']}_{stamp}.mp4"

    mp4_path, duration = build_video(script.slides, bg_paths, audio_paths, niche, out_mp4, workdir)

    meta_path = ROOT / "io_data" / "output" / f"{topic['id']}_{stamp}.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "topic": topic,
            "script": script.model_dump(),
            "seo": seo.model_dump(),
            "video_path": str(mp4_path),
            "duration_seconds": duration,
        }, f, indent=2, ensure_ascii=False)
    log.info(f"Metadata saved: {meta_path.name}")

    if mark_done:
        from agents.topic_picker import mark_complete
        mark_complete(niche, topic["id"])

    log.info(f"=== Pipeline complete | video={mp4_path.name} | {duration:.1f}s ===")
    return RenderedVideo(
        topic_id=topic["id"],
        mp4_path=str(mp4_path),
        duration_seconds=duration,
        seo=seo,
    )
