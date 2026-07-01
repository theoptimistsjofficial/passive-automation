"""Text-to-speech.

Provider chain (per synthesize() call):
  1. ElevenLabs Turbo v2.5 (if ELEVENLABS_API_KEY set) — studio quality, natural
  2. gTTS (fallback) — free but robotic

Falls through automatically on ElevenLabs quota exhaustion or missing key.
"""
import json
import urllib.request
import urllib.error
from pathlib import Path
from gtts import gTTS
from core.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL
from core.logger import get_logger

log = get_logger("tts")


def _elevenlabs_synthesize(text: str, out_path: Path, voice_id: str, model_id: str) -> bool:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    body = json.dumps({
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.2,
            "use_speaker_boost": True,
        },
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        data = resp.read()
        out_path.write_bytes(data)
        return True
    except urllib.error.HTTPError as e:
        err_body = e.read().decode(errors="replace")[:300]
        if e.code == 401:
            log.warning(f"ElevenLabs auth failed (check ELEVENLABS_API_KEY): {err_body}")
        elif e.code == 402 or "quota" in err_body.lower():
            log.warning(f"ElevenLabs quota exhausted, falling back to gTTS: {err_body}")
        elif e.code == 422:
            log.warning(f"ElevenLabs bad voice_id or model: {err_body}")
        else:
            log.warning(f"ElevenLabs HTTP {e.code}: {err_body}")
        return False
    except Exception as e:
        log.warning(f"ElevenLabs error: {type(e).__name__}: {e}")
        return False


def synthesize(text: str, out_path: Path, lang: str = "en", slow: bool = False) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if ELEVENLABS_API_KEY and lang.startswith("en"):
        if _elevenlabs_synthesize(text, out_path, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL):
            log.info(f"TTS (ElevenLabs {ELEVENLABS_MODEL}): {out_path.name} ({len(text)} chars)")
            return out_path
        log.info("Falling back to gTTS")

    tts = gTTS(text=text, lang=lang, slow=slow)
    tts.save(str(out_path))
    log.info(f"TTS (gTTS): {out_path.name} ({len(text)} chars)")
    return out_path
