"""AI video generation providers.

Providers implement generate(prompt, out_path, duration, aspect) -> bool.
The dispatcher tries configured providers in order; first success wins.
"""
import json
import time
import uuid
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Optional

from core.config import GEMINI_API_KEY, ROOT
from core.logger import get_logger

log = get_logger("ai_video")


class ProviderError(Exception):
    pass


class WanLocalProvider:
    """Talks to ComfyUI running locally (default localhost:8188).
    User provides a Wan 2.2 workflow JSON exported from ComfyUI (Save API Format).
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 8188,
                 workflow_path: str = "config/workflows/wan22_5b.json",
                 prompt_node_id: str = "6",
                 poll_seconds: int = 10, timeout_seconds: int = 900):
        self.base = f"http://{host}:{port}"
        self.workflow_path = ROOT / workflow_path
        self.prompt_node_id = prompt_node_id
        self.poll = poll_seconds
        self.timeout = timeout_seconds
        self.client_id = str(uuid.uuid4())

    def _load_workflow(self) -> dict:
        if not self.workflow_path.exists():
            raise ProviderError(
                f"Wan workflow not found: {self.workflow_path}. "
                "See docs/setup_personal_laptop.md — export from ComfyUI as API JSON."
            )
        return json.loads(self.workflow_path.read_text())

    def _health(self) -> bool:
        try:
            urllib.request.urlopen(f"{self.base}/system_stats", timeout=3)
            return True
        except Exception:
            return False

    def generate(self, prompt: str, out_path: Path, duration_sec: float = 5.0,
                 aspect: str = "16:9") -> bool:
        if not self._health():
            raise ProviderError(f"ComfyUI not reachable at {self.base}. Start it first.")

        wf = self._load_workflow()
        if self.prompt_node_id in wf and "inputs" in wf[self.prompt_node_id]:
            wf[self.prompt_node_id]["inputs"]["text"] = prompt
        else:
            raise ProviderError(f"prompt_node_id '{self.prompt_node_id}' not found in workflow")

        body = json.dumps({"prompt": wf, "client_id": self.client_id}).encode("utf-8")
        req = urllib.request.Request(f"{self.base}/prompt", data=body,
                                     headers={"Content-Type": "application/json"})
        resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
        prompt_id = resp["prompt_id"]
        log.info(f"Wan queued: prompt_id={prompt_id}")

        start = time.time()
        while time.time() - start < self.timeout:
            time.sleep(self.poll)
            hist = urllib.request.urlopen(f"{self.base}/history/{prompt_id}", timeout=10)
            hist_data = json.loads(hist.read())
            if prompt_id in hist_data:
                outputs = hist_data[prompt_id].get("outputs", {})
                for node_id, node_out in outputs.items():
                    for file_info in node_out.get("gifs", []) + node_out.get("videos", []):
                        params = urllib.parse.urlencode({
                            "filename": file_info["filename"],
                            "subfolder": file_info.get("subfolder", ""),
                            "type": file_info.get("type", "output"),
                        })
                        data = urllib.request.urlopen(f"{self.base}/view?{params}", timeout=60).read()
                        out_path.write_bytes(data)
                        log.info(f"Wan output: {out_path.name} ({len(data)//1024}KB)")
                        return True
                log.warning(f"Wan history exists but no video output found for {prompt_id}")
                return False
        raise ProviderError(f"Wan generation timed out after {self.timeout}s")


class VeoProvider:
    """Google Veo 3.1 via google-genai SDK. Requires Gemini API key on Tier 1 (billing enabled).
    Free tier keys will 403 on video generation.
    """
    def __init__(self, model: str = "veo-3.1-fast-generate-preview",
                 resolution: str = "720p", poll_seconds: int = 15,
                 timeout_seconds: int = 300):
        self.model = model
        self.resolution = resolution
        self.poll = poll_seconds
        self.timeout = timeout_seconds

    def generate(self, prompt: str, out_path: Path, duration_sec: float = 5.0,
                 aspect: str = "16:9") -> bool:
        if not GEMINI_API_KEY:
            raise ProviderError("GEMINI_API_KEY not set")

        try:
            from google import genai
            from google.genai import types
        except ImportError as e:
            raise ProviderError(f"google-genai SDK not installed: {e}")

        client = genai.Client(api_key=GEMINI_API_KEY)
        try:
            operation = client.models.generate_videos(
                model=self.model,
                prompt=prompt,
                config=types.GenerateVideosConfig(
                    aspect_ratio=aspect,
                    resolution=self.resolution,
                ),
            )
        except Exception as e:
            raise ProviderError(f"Veo API call failed: {e}")

        start = time.time()
        while not operation.done and time.time() - start < self.timeout:
            time.sleep(self.poll)
            operation = client.operations.get(operation)

        if not operation.done:
            raise ProviderError(f"Veo generation timed out after {self.timeout}s")

        video = operation.response.generated_videos[0]
        client.files.download(file=video.video)
        video.video.save(str(out_path))
        log.info(f"Veo output: {out_path.name}")
        return True


PROVIDER_CLASSES = {
    "wan_local": WanLocalProvider,
    "veo": VeoProvider,
}


def generate_scene(prompt: str, out_path: Path, providers: List[str],
                   duration_sec: float = 5.0, aspect: str = "16:9") -> Optional[Path]:
    """Try providers in order; return path on first success, None if all fail."""
    for name in providers:
        cls = PROVIDER_CLASSES.get(name)
        if not cls:
            log.warning(f"Unknown provider: {name}")
            continue
        try:
            provider = cls()
            if provider.generate(prompt, out_path, duration_sec, aspect):
                return out_path
        except ProviderError as e:
            log.warning(f"Provider '{name}' failed: {e}. Trying next.")
        except Exception as e:
            log.warning(f"Provider '{name}' error: {type(e).__name__}: {e}. Trying next.")
    return None
