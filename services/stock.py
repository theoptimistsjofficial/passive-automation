import hashlib
import random
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFilter

from core.config import PEXELS_API_KEY
from core.logger import get_logger

log = get_logger("stock")

W, H = 1920, 1080


def _placeholder(seed: str, out_path: Path, accent_hex: str, bg_hex: str) -> Path:
    """Deterministic gradient placeholder — used when Pexels key missing or fetch fails."""
    rng = random.Random(int(hashlib.md5(seed.encode()).hexdigest(), 16) % (2 ** 32))
    bg = Image.new("RGB", (W, H), bg_hex)
    draw = ImageDraw.Draw(bg)
    accent = tuple(int(accent_hex.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    for _ in range(8):
        cx, cy = rng.randint(0, W), rng.randint(0, H)
        r = rng.randint(300, 700)
        for i in range(r, 0, -25):
            alpha = int(35 * (1 - i / r))
            draw.ellipse([cx - i, cy - i, cx + i, cy + i],
                         fill=tuple(min(255, c + alpha) for c in accent))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=45))
    bg.save(out_path, "JPEG", quality=88)
    return out_path


def _cover_fit(img: Image.Image, w: int, h: int) -> Image.Image:
    src_w, src_h = img.size
    src_ratio = src_w / src_h
    dst_ratio = w / h
    if src_ratio > dst_ratio:
        new_h, new_w = h, int(h * src_ratio)
    else:
        new_w, new_h = w, int(w / src_ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left, top = (new_w - w) // 2, (new_h - h) // 2
    return img.crop((left, top, left + w, top + h))


def _try_pexels_video(query: str, out_path: Path) -> bool:
    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            params={"query": query, "per_page": 8, "orientation": "landscape", "size": "medium"},
            headers={"Authorization": PEXELS_API_KEY},
            timeout=20,
        )
        r.raise_for_status()
        videos = r.json().get("videos", [])
        for video in videos:
            files = [f for f in video.get("video_files", [])
                     if f.get("width", 0) >= 1280 and f.get("width", 0) <= 1920
                     and f.get("file_type") == "video/mp4"]
            files.sort(key=lambda f: abs(f.get("width", 0) - 1920))
            if not files:
                continue
            url = files[0]["link"]
            data = requests.get(url, timeout=45).content
            out_path.write_bytes(data)
            log.info(f"Pexels video: '{query}' -> {out_path.name} ({len(data)//1024}KB)")
            return True
    except Exception as e:
        log.warning(f"Pexels video fetch failed for '{query}': {e}")
    return False


def _try_pexels_image(query: str, out_path: Path) -> bool:
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            params={"query": query, "per_page": 5, "orientation": "landscape", "size": "large"},
            headers={"Authorization": PEXELS_API_KEY},
            timeout=15,
        )
        r.raise_for_status()
        photos = r.json().get("photos", [])
        if not photos:
            return False
        url = photos[0]["src"]["large2x"]
        data = requests.get(url, timeout=20).content
        out_path.write_bytes(data)
        img = Image.open(out_path).convert("RGB")
        img = _cover_fit(img, W, H)
        img.save(out_path, "JPEG", quality=88)
        log.info(f"Pexels image: '{query}' -> {out_path.name}")
        return True
    except Exception as e:
        log.warning(f"Pexels image fetch failed for '{query}': {e}")
    return False


def fetch_scene(query: str, out_stem: Path, niche: dict, prefer_video: bool = True) -> Path:
    """Fetch a scene asset. Returns Path with .mp4 (video) or .jpg (image) suffix.
    Renderer sniffs the suffix to decide how to composite.
    """
    out_stem.parent.mkdir(parents=True, exist_ok=True)

    if PEXELS_API_KEY:
        if prefer_video:
            video_path = out_stem.with_suffix(".mp4")
            if _try_pexels_video(query, video_path):
                return video_path
        image_path = out_stem.with_suffix(".jpg")
        if _try_pexels_image(query, image_path):
            return image_path

    fallback = out_stem.with_suffix(".jpg")
    log.info(f"Placeholder: '{query}' -> {fallback.name}")
    return _placeholder(query, fallback,
                        niche.get("accent_color", "#f4a261"),
                        niche.get("background_color", "#0d1b2a"))


fetch_background = fetch_scene
