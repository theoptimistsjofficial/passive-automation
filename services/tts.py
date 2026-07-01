from pathlib import Path
from gtts import gTTS
from core.logger import get_logger

log = get_logger("tts")


def synthesize(text: str, out_path: Path, lang: str = "en", slow: bool = False) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tts = gTTS(text=text, lang=lang, slow=slow)
    tts.save(str(out_path))
    log.info(f"TTS saved: {out_path.name} ({len(text)} chars)")
    return out_path
