"""AI video generation providers.

Providers implement generate(prompt, out_path, duration, aspect) -> bool.
The dispatcher tries configured providers in order; first success wins.
"""
import json
import shutil
import time
import uuid
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Optional

from core.config import FAL_API_KEY, FAL_MODEL, GEMINI_API_KEY, ROOT
from core.logger import get_logger

log = get_logger("ai_video")


class ProviderError(Exception):
    pass


def _autodetect_positive_prompt_node(workflow: dict) -> str:
    """Find the positive CLIPTextEncode node in a ComfyUI workflow.

    Heuristic: first CLIPTextEncode node whose title/inputs.text looks positive
    (i.e. NOT the negative prompt). If two exist, prefers the one linked to
    a sampler's 'positive' input.
    """
    text_nodes = {
        nid: n for nid, n in workflow.items()
        if isinstance(n, dict) and n.get("class_type", "").endswith("CLIPTextEncode")
    }
    if not text_nodes:
        raise ProviderError("No CLIPTextEncode node found in workflow — is this a Wan/SD text-to-video workflow?")

    if len(text_nodes) == 1:
        return next(iter(text_nodes))

    for nid, node in text_nodes.items():
        title = str(node.get("_meta", {}).get("title", "")).lower()
        text = str(node.get("inputs", {}).get("text", "")).lower()
        if "negative" in title or "negative" in text:
            continue
        if "positive" in title or (title == "" and text and "worst" not in text and "low quality" not in text):
            return nid

    return next(iter(text_nodes))


class ManualDropboxProvider:
    """Uses pre-generated hero clips from cloud AI tools (Kling, Vidu, Hailuo, etc.).

    Workflow:
      1. Generate clips in the tool's web UI (free daily credits).
      2. Download and rename to slide_{NN}.mp4 (e.g. slide_01.mp4, slide_04.mp4).
      3. Drop them in io_data/heroshots/{niche_key}/.
      4. Run the pipeline — this provider picks them up first, before Wan.

    If a matching file doesn't exist, generate() returns False and the pipeline
    falls through to the next provider (Wan, then Pexels stock).

    Naming rules:
      - File must match slide_{NN}.{ext} where NN is zero-padded slide index
      - Extensions checked: .mp4, .mov, .webm
      - Case-insensitive
    """
    VALID_EXTS = {".mp4", ".mov", ".webm", ".mkv"}

    def __init__(self, base_dir: str = "io_data/heroshots", niche_key: Optional[str] = None):
        self.base_dir = ROOT / base_dir
        self.niche_key = niche_key

    def _resolve_slide_num(self, out_path: Path) -> Optional[int]:
        # out_path stem is like "bg_01" or "slide_01"; extract the number
        stem = out_path.stem
        parts = stem.rsplit("_", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return int(parts[1])
        return None

    def generate(self, prompt: str, out_path: Path, duration_sec: float = 5.0,
                 aspect: str = "16:9") -> bool:
        if not self.niche_key:
            log.info("ManualDropbox: no niche_key supplied — skipping")
            return False

        slide_num = self._resolve_slide_num(out_path)
        if slide_num is None:
            log.info(f"ManualDropbox: could not parse slide index from {out_path.name} — skipping")
            return False

        niche_folder = self.base_dir / self.niche_key
        if not niche_folder.exists():
            log.info(f"ManualDropbox: folder not found {niche_folder} — skipping (falls through to next provider)")
            return False

        target_stem = f"slide_{slide_num:02d}"
        candidates = [
            p for p in niche_folder.iterdir()
            if p.is_file() and p.stem.lower() == target_stem and p.suffix.lower() in self.VALID_EXTS
        ]

        if not candidates:
            log.info(
                f"ManualDropbox: no pre-generated clip at {niche_folder}/{target_stem}.* — "
                "falling through to next provider"
            )
            return False

        src = candidates[0]
        try:
            shutil.copy2(src, out_path)
        except Exception as e:
            raise ProviderError(f"ManualDropbox: failed to copy {src} → {out_path}: {e}")

        size_mb = out_path.stat().st_size / (1024 * 1024)
        log.info(f"ManualDropbox: using pre-generated clip {src.name} ({size_mb:.1f}MB) for slide {slide_num}")
        return True


class WanLocalProvider:
    """Talks to ComfyUI running locally (default localhost:8188).
    Auto-detects the positive prompt node in any workflow JSON.
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 8188,
                 workflow_path: str = "config/workflows/wan22_5b.json",
                 prompt_node_id: Optional[str] = None,
                 poll_seconds: int = 10, timeout_seconds: int = 1800):
        self.base = f"http://{host}:{port}"
        self.workflow_path = ROOT / workflow_path
        self.prompt_node_id = prompt_node_id
        self.poll = poll_seconds
        self.timeout = timeout_seconds
        self.client_id = str(uuid.uuid4())

    def _load_workflow(self) -> dict:
        if not self.workflow_path.exists():
            raise ProviderError(
                f"Wan workflow not found: {self.workflow_path}\n"
                "Fix: In ComfyUI web UI, Workflow → Browse Templates → Video → 'Wan 2.2 5B'.\n"
                "     Then Workflow → Export (API) → save to that path."
            )
        try:
            return json.loads(self.workflow_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ProviderError(
                f"Workflow JSON is malformed at {self.workflow_path}: {e}\n"
                "Fix: re-export from ComfyUI using 'Save (API Format)' — not the regular Save."
            )

    def _health(self) -> tuple[bool, str]:
        try:
            r = urllib.request.urlopen(f"{self.base}/system_stats", timeout=3)
            return True, r.read()[:120].decode(errors="replace")
        except urllib.error.URLError as e:
            return False, f"{type(e).__name__}: {e}"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"

    def generate(self, prompt: str, out_path: Path, duration_sec: float = 5.0,
                 aspect: str = "16:9") -> bool:
        ok, info = self._health()
        if not ok:
            raise ProviderError(
                f"ComfyUI not reachable at {self.base}. Start `run_nvidia_gpu.bat` first.\n"
                f"Error: {info}"
            )

        wf = self._load_workflow()
        node_id = self.prompt_node_id or _autodetect_positive_prompt_node(wf)
        log.info(f"Wan: using prompt node '{node_id}' (autodetected)" if self.prompt_node_id is None
                 else f"Wan: using prompt node '{node_id}' (configured)")

        if node_id not in wf:
            raise ProviderError(f"Prompt node '{node_id}' not in workflow. Nodes: {list(wf.keys())[:10]}...")

        wf[node_id].setdefault("inputs", {})["text"] = prompt

        body = json.dumps({"prompt": wf, "client_id": self.client_id}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base}/prompt", data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:400]
            raise ProviderError(
                f"ComfyUI rejected workflow (HTTP {e.code}): {body}\n"
                "Common causes: missing model file, missing custom node, wrong workflow format."
            )

        prompt_id = resp.get("prompt_id")
        if not prompt_id:
            raise ProviderError(f"ComfyUI response missing prompt_id: {resp}")
        log.info(f"Wan queued: prompt_id={prompt_id} — polling every {self.poll}s (timeout {self.timeout}s)")

        start = time.time()
        last_status = ""
        while time.time() - start < self.timeout:
            time.sleep(self.poll)
            try:
                hist = urllib.request.urlopen(f"{self.base}/history/{prompt_id}", timeout=10)
                hist_data = json.loads(hist.read())
            except Exception as e:
                log.warning(f"Wan history poll error (retrying): {e}")
                continue

            if prompt_id not in hist_data:
                elapsed = int(time.time() - start)
                status = f"in-queue ({elapsed}s)"
                if status != last_status:
                    log.info(f"Wan: {status}")
                    last_status = status
                continue

            outputs = hist_data[prompt_id].get("outputs", {})
            for node_id_out, node_out in outputs.items():
                for kind in ("videos", "gifs", "images"):
                    for file_info in node_out.get(kind, []):
                        params = urllib.parse.urlencode({
                            "filename": file_info["filename"],
                            "subfolder": file_info.get("subfolder", ""),
                            "type": file_info.get("type", "output"),
                        })
                        data = urllib.request.urlopen(f"{self.base}/view?{params}", timeout=120).read()
                        out_path.write_bytes(data)
                        log.info(f"Wan output ({kind}): {out_path.name} ({len(data)//1024}KB)")
                        return True
            log.warning(f"Wan finished but no video/gif output in history for {prompt_id}: {list(outputs.keys())}")
            return False

        raise ProviderError(f"Wan timed out after {self.timeout}s — increase timeout or use a lighter model")


class FalAiProvider:
    """Fal.ai hosted video generation (Kling 2.0 Master by default).

    Fal.ai hosts most SOTA open + closed video models with pay-per-clip pricing.
    Kling 2.0 Master gives near-SOTA quality at ~$0.40/5-sec clip.

    Model options via FAL_MODEL env var:
      - fal-ai/kling-video/v2/master/text-to-video     (~$0.40/clip, recommended)
      - fal-ai/kling-video/v2-5/pro/text-to-video      (~$1.50/clip, SOTA)
      - fal-ai/hailuo-02/standard/text-to-video        (~$0.30/clip)
      - fal-ai/wan-t2v-14b                             (~$0.20/clip)
      - fal-ai/veo3-fast                               (~$0.75/clip)
      - fal-ai/ltx-video                               (~$0.02/clip, low quality)
    """
    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None,
                 poll_seconds: int = 5, timeout_seconds: int = 600):
        self.model = model or FAL_MODEL
        self.api_key = api_key or FAL_API_KEY
        self.base = "https://queue.fal.run"
        self.poll = poll_seconds
        self.timeout = timeout_seconds

    def _headers(self) -> dict:
        return {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
        }

    def _submit(self, payload: dict) -> str:
        url = f"{self.base}/{self.model}"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=self._headers(), method="POST")
        try:
            resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
        except urllib.error.HTTPError as e:
            err = e.read().decode(errors="replace")[:400]
            raise ProviderError(f"Fal.ai submit failed (HTTP {e.code}): {err}")
        request_id = resp.get("request_id")
        if not request_id:
            raise ProviderError(f"Fal.ai response missing request_id: {resp}")
        return request_id

    def _poll(self, request_id: str) -> dict:
        status_url = f"{self.base}/{self.model}/requests/{request_id}/status"
        result_url = f"{self.base}/{self.model}/requests/{request_id}"
        start = time.time()
        while time.time() - start < self.timeout:
            try:
                r = urllib.request.Request(status_url, headers=self._headers())
                status = json.loads(urllib.request.urlopen(r, timeout=15).read())
            except Exception as e:
                log.warning(f"Fal.ai status poll retry: {e}")
                time.sleep(self.poll)
                continue

            state = status.get("status")
            if state == "COMPLETED":
                r = urllib.request.Request(result_url, headers=self._headers())
                return json.loads(urllib.request.urlopen(r, timeout=30).read())
            if state in ("FAILED", "ERROR"):
                raise ProviderError(f"Fal.ai generation failed: {status}")
            log.info(f"Fal.ai: {state} (elapsed {int(time.time()-start)}s)")
            time.sleep(self.poll)
        raise ProviderError(f"Fal.ai timed out after {self.timeout}s")

    def generate(self, prompt: str, out_path: Path, duration_sec: float = 5.0,
                 aspect: str = "16:9", negative_prompt: str = "") -> bool:
        if not self.api_key:
            raise ProviderError(
                "FAL_API_KEY not set in .env — sign up at https://fal.ai and paste your key"
            )

        payload = {
            "prompt": prompt,
            "duration": str(int(duration_sec)) if "kling" in self.model else duration_sec,
            "aspect_ratio": aspect,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        log.info(f"Fal.ai [{self.model}] submitting prompt ({len(prompt)} chars)...")
        request_id = self._submit(payload)
        log.info(f"Fal.ai queued: {request_id}")

        result = self._poll(request_id)

        video_url = None
        if isinstance(result.get("video"), dict):
            video_url = result["video"].get("url")
        elif isinstance(result.get("video_url"), str):
            video_url = result["video_url"]
        elif isinstance(result.get("output"), dict) and result["output"].get("video"):
            video_url = result["output"]["video"].get("url")

        if not video_url:
            raise ProviderError(f"Fal.ai completed but no video URL in response: {result}")

        log.info(f"Fal.ai downloading: {video_url[:80]}...")
        try:
            data = urllib.request.urlopen(video_url, timeout=120).read()
        except Exception as e:
            raise ProviderError(f"Fal.ai download failed: {e}")

        out_path.write_bytes(data)
        size_mb = len(data) / (1024 * 1024)
        log.info(f"Fal.ai output: {out_path.name} ({size_mb:.1f}MB)")
        return True


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
    "manual_dropbox": ManualDropboxProvider,
    "fal_ai": FalAiProvider,
    "wan_local": WanLocalProvider,
    "veo": VeoProvider,
}


def generate_scene(prompt: str, out_path: Path, providers: List[str],
                   duration_sec: float = 5.0, aspect: str = "16:9",
                   niche_key: Optional[str] = None) -> Optional[Path]:
    """Try providers in order; return path on first success, None if all fail.

    niche_key is used by ManualDropboxProvider to locate pre-generated clips
    under io_data/heroshots/{niche_key}/. Other providers ignore it.
    """
    for name in providers:
        cls = PROVIDER_CLASSES.get(name)
        if not cls:
            log.warning(f"Unknown provider: {name}")
            continue
        try:
            if name == "manual_dropbox":
                provider = cls(niche_key=niche_key)
            else:
                provider = cls()
            if provider.generate(prompt, out_path, duration_sec, aspect):
                return out_path
        except ProviderError as e:
            log.warning(f"Provider '{name}' failed: {e}. Trying next.")
        except Exception as e:
            log.warning(f"Provider '{name}' error: {type(e).__name__}: {e}. Trying next.")
    return None
