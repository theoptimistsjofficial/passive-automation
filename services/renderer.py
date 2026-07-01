from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    ImageClip, AudioFileClip, VideoFileClip, ColorClip,
    CompositeVideoClip, concatenate_videoclips, vfx,
)

from core.schemas import Slide
from core.logger import get_logger

log = get_logger("renderer")

W, H = 1920, 1080
FONT_CANDIDATES = [
    "C:\\Windows\\Fonts\\arialbd.ttf",
    "C:\\Windows\\Fonts\\segoeuib.ttf",
    "C:\\Windows\\Fonts\\arial.ttf",
    "C:\\Windows\\Fonts\\segoeui.ttf",
]


def _font_path() -> str:
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return p
    return ""


def _font(size: int) -> ImageFont.FreeTypeFont:
    path = _font_path()
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    h = hex_str.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> List[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _render_text_image(text: str, font_size: int, color_hex: str, max_width: int,
                       stroke_width: int = 3) -> Image.Image:
    font = _font(font_size)
    tmp = Image.new("RGBA", (max_width, 2000), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    lines = _wrap(d, text, font, max_width - stroke_width * 2)
    line_h = font_size + int(font_size * 0.15)
    total_h = line_h * len(lines)
    img = Image.new("RGBA", (max_width, max(total_h + 20, 100)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    color = _hex_to_rgb(color_hex) + (255,)
    y = 0
    for line in lines:
        d.text((stroke_width, y), line, font=font, fill=color,
               stroke_width=stroke_width, stroke_fill=(0, 0, 0, 220))
        y += line_h
    return img


def _bg_video(video_path: Path, duration: float) -> "VideoFileClip":
    """Load stock video, loop or trim to duration, apply subtle zoom drift."""
    clip = VideoFileClip(str(video_path)).without_audio()

    if clip.duration < duration:
        n_loops = int(duration / clip.duration) + 1
        clip = concatenate_videoclips([clip] * n_loops, method="compose")
    clip = clip.subclipped(0, duration)

    if clip.size != [W, H] and clip.size != (W, H):
        clip = clip.resized(height=H)
        if clip.w < W:
            clip = clip.resized(width=W)
        if clip.w > W or clip.h > H:
            clip = clip.cropped(x_center=clip.w / 2, y_center=clip.h / 2, width=W, height=H)

    clip = clip.resized(lambda t: 1.0 + 0.03 * (t / duration))
    return clip


def _ken_burns(image_path: Path, duration: float, zoom_end: float = 1.15) -> ImageClip:
    """Slow zoom-in with slight drift on a still image."""
    clip = ImageClip(str(image_path)).with_duration(duration)
    clip = clip.resized(lambda t: 1.0 + (zoom_end - 1.0) * (t / duration))
    clip = clip.with_position(lambda t: (
        -int(30 * (t / duration)),
        -int(20 * (t / duration)),
    ))
    return clip


def _vignette_overlay(duration: float) -> ImageClip:
    """Dark corners for text legibility."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i in range(120):
        alpha = int(180 * (i / 120) ** 2)
        d.rectangle([i, i, W - i, H - i], outline=(0, 0, 0, alpha))
    center_dark = Image.new("RGBA", (W, H), (0, 0, 0, 110))
    from PIL import ImageChops
    combined = ImageChops.add(center_dark, img)
    tmp = Path("_vignette_tmp.png")
    combined.save(tmp)
    clip = ImageClip(str(tmp)).with_duration(duration)
    return clip


def _accent_bar(duration: float, accent_hex: str, x: int = 100, y: int = 780,
                bar_w: int = 240, bar_h: int = 12) -> ImageClip:
    """Accent bar as brand mark — fades in with slide."""
    color = _hex_to_rgb(accent_hex)
    img = Image.new("RGBA", (bar_w, bar_h), color + (255,))
    tmp = Path(f"_bar_{accent_hex.lstrip('#')}.png")
    img.save(tmp)
    clip = ImageClip(str(tmp)).with_duration(duration).with_position((x, y))
    clip = clip.with_effects([vfx.CrossFadeIn(0.5)])
    return clip


def _text_overlay(text: str, font_size: int, color_hex: str, y_pos: int,
                  duration: float, start: float, fade_in: float = 0.5,
                  drift_up_px: int = 30, max_width: int = W - 200) -> ImageClip:
    """Render text with fade-in and slight upward drift."""
    img = _render_text_image(text, font_size, color_hex, max_width)
    tmp = Path(f"_text_{abs(hash(text)) % 10 ** 9}.png")
    img.save(tmp)

    clip_duration = max(0.1, duration - start)
    clip = ImageClip(str(tmp)).with_duration(clip_duration).with_start(start)

    def pos(t):
        progress = min(1.0, t / fade_in) if t < fade_in else 1.0
        offset = int(drift_up_px * (1 - progress))
        x = (W - img.width) // 2
        return (x, y_pos + offset)

    clip = clip.with_position(pos)
    clip = clip.with_effects([vfx.CrossFadeIn(fade_in)])
    return clip


def _slide_clip(slide: Slide, bg_path: Path, audio_path: Path,
                niche: dict) -> "CompositeVideoClip":
    audio = AudioFileClip(str(audio_path))
    duration = audio.duration + 0.8

    if bg_path.suffix.lower() == ".mp4":
        bg = _bg_video(bg_path, duration)
    else:
        bg = _ken_burns(bg_path, duration)

    dark = ColorClip((W, H), color=(0, 0, 0)).with_duration(duration).with_opacity(0.45)
    vignette = _vignette_overlay(duration)
    bar = _accent_bar(duration, niche.get("accent_color", "#f4a261"))

    heading = _text_overlay(
        slide.heading, font_size=96,
        color_hex=niche.get("text_color", "#ffffff"),
        y_pos=H // 2 - 140,
        duration=duration, start=0.4, fade_in=0.5,
    )
    body = _text_overlay(
        slide.body, font_size=52,
        color_hex=niche.get("text_color", "#ffffff"),
        y_pos=H // 2 + 40,
        duration=duration, start=1.2, fade_in=0.5,
    )

    composite = CompositeVideoClip(
        [bg, dark, vignette, bar, heading, body],
        size=(W, H),
    ).with_duration(duration).with_audio(audio)

    return composite


def build_video(
    slides: List[Slide],
    bg_paths: List[Path],
    audio_paths: List[Path],
    niche: dict,
    out_mp4: Path,
    workdir: Path,
) -> Tuple[Path, float]:
    workdir.mkdir(parents=True, exist_ok=True)

    slide_clips = []
    for i, (slide, bg, audio_path) in enumerate(zip(slides, bg_paths, audio_paths)):
        clip = _slide_clip(slide, bg, audio_path, niche)
        if i > 0:
            clip = clip.with_effects([vfx.CrossFadeIn(0.6)])
        slide_clips.append(clip)
        log.info(f"Slide {i + 1}/{len(slides)} composed ({clip.duration:.1f}s)")

    final = concatenate_videoclips(slide_clips, method="compose", padding=-0.6)
    total_duration = final.duration

    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(
        str(out_mp4),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=4,
        logger=None,
    )
    for c in slide_clips:
        c.close()
    final.close()

    for tmp in Path(".").glob("_text_*.png"):
        tmp.unlink(missing_ok=True)
    for tmp in Path(".").glob("_bar_*.png"):
        tmp.unlink(missing_ok=True)
    Path("_vignette_tmp.png").unlink(missing_ok=True)

    log.info(f"Video written: {out_mp4} ({total_duration:.1f}s)")
    return out_mp4, total_duration
