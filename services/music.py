"""Background music selection.

Uses Pixabay Music API (free) to fetch royalty-free tracks matching niche mood.
Track is mixed under narration at -18 dB in MoviePy assembly.

If PIXABAY_API_KEY not set, returns None and pipeline skips BGM.
"""
import json
import random
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Optional
from core.config import PIXABAY_API_KEY, ROOT
from core.logger import get_logger

log = get_logger("music")

NICHE_MOOD_QUERIES = {
    "positive_thinking": ["uplifting cinematic", "inspirational hopeful", "warm cinematic piano"],
    "devotional": ["sacred ambient", "meditation indian", "spiritual peaceful"],
}


def fetch_bgm(niche_key: str, out_path: Path) -> Optional[Path]:
    if not PIXABAY_API_KEY:
        log.info("PIXABAY_API_KEY not set — skipping BGM")
        return None

    queries = NICHE_MOOD_QUERIES.get(niche_key, ["cinematic ambient"])
    query = random.choice(queries)

    url = "https://pixabay.com/api/audio/"
    params = {
        "key": PIXABAY_API_KEY,
        "q": query,
        "audio_type": "music",
        "per_page": 20,
        "order": "popular",
    }
    full_url = f"{url}?{urllib.parse.urlencode(params)}"

    try:
        resp = urllib.request.urlopen(full_url, timeout=30)
        data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        log.warning(f"Pixabay Music HTTP {e.code}: {e.read()[:200]}")
        return None
    except Exception as e:
        log.warning(f"Pixabay Music error: {type(e).__name__}: {e}")
        return None

    hits = data.get("hits", [])
    if not hits:
        log.warning(f"Pixabay Music: no results for '{query}'")
        return None

    track = random.choice(hits[:10])
    audio_url = track.get("audio") or track.get("audio_url")
    if not audio_url:
        log.warning(f"Pixabay Music: hit has no audio URL: {track}")
        return None

    try:
        audio_data = urllib.request.urlopen(audio_url, timeout=60).read()
    except Exception as e:
        log.warning(f"Pixabay Music download failed: {e}")
        return None

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(audio_data)
    duration = track.get("duration", 0)
    log.info(f"BGM: '{track.get('tags', '?')[:40]}...' ({duration}s, {len(audio_data)//1024}KB) → {out_path.name}")
    return out_path
