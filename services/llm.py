import json
import re
from core.config import GEMINI_API_KEY
from core.logger import get_logger

log = get_logger("llm")


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in LLM output")
    return json.loads(text[start:end + 1])


def generate_json(prompt: str, model: str = "gemini-2.5-flash") -> dict:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set — running in offline fallback mode")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)
    resp = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
            response_mime_type="application/json",
        ),
    )
    text = resp.text or ""
    log.info(f"LLM response: {len(text)} chars")
    return _extract_json(text)
