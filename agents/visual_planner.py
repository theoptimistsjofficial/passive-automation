from core.schemas import VideoScript
from core.logger import get_logger

log = get_logger("visual_planner")


def enrich_stock_queries(script: VideoScript, niche: dict) -> VideoScript:
    style = niche.get("stock_query_style", "")
    for slide in script.slides:
        if style and style not in slide.stock_query:
            slide.stock_query = f"{slide.stock_query} {style}".strip()
    log.info(f"Enriched {len(script.slides)} stock queries")
    return script
