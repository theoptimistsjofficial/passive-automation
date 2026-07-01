"""Text-to-speech provider chain.

Order (per synthesize() call):
  1. Google Cloud TTS Neural (if GOOGLE_TTS_API_KEY set) — free 1M chars/mo, near-human
  2. ElevenLabs Turbo v2.5 (if ELEVENLABS_API_KEY set, paid tier only for library voices)
  3. gTTS — always available, robotic

Falls through automatically on auth failure, quota exhaustion, or missing key.
"""
import base64
import json
import urllib.request
import urllib.error
from pathlib import Path
from gtts import gTTS
from core.config import (
    ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL,
    GOOGLE_TTS_API_KEY, GOOGLE_TTS_VOICE, GOOGLE_TTS_LANG,
)
from core.logger import get_logger

log = get_logger("tts")


def _google_tts_synthesize(text: str, out_path: Path,
                           voice: str = None, lang: str = None) -> bool:
    voice = voice or GOOGLE_TTS_VOICE
    lang = lang or GOOGLE_TTS_LANG
    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_API_KEY}"
    body = json.dumps({
        "input": {"text": text},
        "voice": {"languageCode": lang, "name": voice},
        "audioConfig": {
            "audioEncoding": "MP3",
            "speakingRate": 1.0,
            "pitch": 0.0,
        },
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        audio = base64.b64decode(data["audioContent"])
        out_path.write_bytes(audio)
        return True
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors="replace")[:300]
        if e.code == 403:
            log.warning(f"Google TTS 403 (enable Cloud TTS API in your Google Cloud project): {err}")
        elif e.code == 400:
            log.warning(f"Google TTS bad request (check voice name '{voice}'): {err}")
        else:
            log.warning(f"Google TTS HTTP {e.code}: {err}")
        return False
    except Exception as e:
        log.warning(f"Google TTS error: {type(e).__name__}: {e}")
        return False


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
        out_path.write_bytes(resp.read())
        return True
    except urllib.error.HTTPError as e:
        err_body = e.read().decode(errors="replace")[:300]
        if e.code == 401:
            if "paid_plan_required" in err_body or "library voices" in err_body:
                log.warning("ElevenLabs free tier can no longer use library voices via API. Upgrade Starter ($5/mo) or use Google Cloud TTS.")
            else:
                log.warning(f"ElevenLabs auth failed: {err_body}")
        elif e.code == 402 or "quota" in err_body.lower():
            log.warning(f"ElevenLabs quota exhausted: {err_body}")
        else:
            log.warning(f"ElevenLabs HTTP {e.code}: {err_body}")
        return False
    except Exception as e:
        log.warning(f"ElevenLabs error: {type(e).__name__}: {e}")
        return False


def synthesize(text: str, out_path: Path, lang: str = "en", slow: bool = False) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if GOOGLE_TTS_API_KEY and lang.startswith("en"):
        if _google_tts_synthesize(text, out_path):
            log.info(f"TTS (Google Cloud {GOOGLE_TTS_VOICE}): {out_path.name} ({len(text)} chars)")
            return out_path
        log.info("Falling back to ElevenLabs")

    if ELEVENLABS_API_KEY and lang.startswith("en"):
        if _elevenlabs_synthesize(text, out_path, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL):
            log.info(f"TTS (ElevenLabs {ELEVENLABS_MODEL}): {out_path.name} ({len(text)} chars)")
            return out_path
        log.info("Falling back to gTTS")

    tts = gTTS(text=text, lang=lang, slow=slow)
    tts.save(str(out_path))
    log.info(f"TTS (gTTS — robotic fallback): {out_path.name} ({len(text)} chars)")
    return out_path
