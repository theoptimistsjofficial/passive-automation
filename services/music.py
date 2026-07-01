"""Background music selection.

Uses a local library approach (Pixabay Music API deprecated as of 2026).

Structure:
  io_data/bgm/
  ├── positive_thinking/
  │   ├── uplifting_01.mp3
  │   ├── inspirational_02.mp3
  │   └── ...
  └── devotional/
      ├── sacred_01.mp3
      └── ...

Seed the library once (see docs/bgm_library_setup.md), then this service
random-picks a track per video. Falls back to trying Pixabay API if no
local tracks exist and PIXABAY_API_KEY is set.
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
import shutil

log = get_logger("music")

BGM_LIBRARY = ROOT / "io_data" / "bgm"
VALID_EXTS = {".mp3", ".wav", ".m4a", ".ogg"}


def _local_pick(niche_key: str, out_path: Path) -> Optional[Path]:
    niche_folder = BGM_LIBRARY / niche_key
    if not niche_folder.exists():
        return None
    tracks = [p for p in niche_folder.iterdir()
              if p.is_file() and p.suffix.lower() in VALID_EXTS]
    if not tracks:
        return None
    pick = random.choice(tracks)
    shutil.copy2(pick, out_path)
    size_kb = out_path.stat().st_size // 1024
    log.info(f"BGM (local): '{pick.name}' ({size_kb}KB) → {out_path.name}")
    return out_path


def _pixabay_pick(niche_key: str, out_path: Path) -> Optional[Path]:
    if not PIXABAY_API_KEY:
        return None
    queries = {
        "positive_thinking": "uplifting cinematic inspirational",
        "devotional": "sacred meditation spiritual",
    }
    query = queries.get(niche_key, "cinematic ambient")

    for endpoint in ("https://pixabay.com/api/music/", "https://pixabay.com/api/audio/"):
        try:
            url = f"{endpoint}?{urllib.parse.urlencode({'key': PIXABAY_API_KEY, 'q': query, 'per_page': 20})}"
            resp = urllib.request.urlopen(url, timeout=20)
            data = json.loads(resp.read())
            hits = data.get("hits", [])
            if not hits:
                continue
            track = random.choice(hits[:10])
            audio_url = track.get("audio") or track.get("audio_url")
            if not audio_url:
                continue
            audio_data = urllib.request.urlopen(audio_url, timeout=60).read()
            out_path.write_bytes(audio_data)
            log.info(f"BGM (Pixabay): {out_path.name} ({len(audio_data)//1024}KB)")
            return out_path
        except Exception as e:
            log.debug(f"Pixabay {endpoint} failed: {e}")
            continue
    return None


def fetch_bgm(niche_key: str, out_path: Path) -> Optional[Path]:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    local = _local_pick(niche_key, out_path)
    if local:
        return local

    pixabay = _pixabay_pick(niche_key, out_path)
    if pixabay:
        return pixabay

    log.info(
        f"No BGM available for '{niche_key}'. Seed io_data/bgm/{niche_key}/ "
        "with .mp3 tracks (see docs/bgm_library_setup.md)"
    )
    return None
