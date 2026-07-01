import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def load_niche(niche_key: str | None = None) -> dict:
    with open(ROOT / "config" / "niches.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    key = niche_key or env("DEFAULT_NICHE", "positive_thinking")
    if key not in cfg["niches"]:
        raise ValueError(f"Unknown niche '{key}'. Available: {list(cfg['niches'])}")
    niche = cfg["niches"][key]
    niche["_key"] = key
    return niche


GEMINI_API_KEY = env("GEMINI_API_KEY")
PEXELS_API_KEY = env("PEXELS_API_KEY")
ELEVENLABS_API_KEY = env("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = env("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel — default warm female
ELEVENLABS_MODEL = env("ELEVENLABS_MODEL", "eleven_turbo_v2_5")
FAL_API_KEY = env("FAL_API_KEY")
FAL_MODEL = env("FAL_MODEL", "fal-ai/kling-video/v2/master/text-to-video")
PIXABAY_API_KEY = env("PIXABAY_API_KEY")
YOUTUBE_CLIENT_SECRETS_JSON = env("YOUTUBE_CLIENT_SECRETS_JSON", "config/youtube_client_secret.json")
YOUTUBE_TOKEN_JSON = env("YOUTUBE_TOKEN_JSON", "config/youtube_token.json")
CHANNEL_NAME = env("CHANNEL_NAME", "OptimistMantra")
