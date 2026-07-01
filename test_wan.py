#!/usr/bin/env python
"""Standalone Wan smoke test — skips scripting/TTS/rendering, generates one AI clip.

Use this to iterate on ComfyUI setup without waiting 20 min per full pipeline run.

Usage:
    python test_wan.py                      # generate with default test prompt
    python test_wan.py "your custom prompt" # generate with your prompt
"""
import sys
from pathlib import Path
from datetime import datetime

from core.config import ROOT
from core.logger import get_logger
from services.ai_video import WanLocalProvider, ProviderError

log = get_logger("test_wan")


DEFAULT_PROMPT = (
    "a lone silhouetted figure walking up a mountain path at sunrise, "
    "cinematic uplifting, warm golden hour lighting, slow drone camera pulling back, "
    "hopeful atmosphere, professional colour grade, 24fps film aesthetic, "
    "no text, no logos"
)


def main():
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_PROMPT
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = ROOT / "io_data" / "output" / f"wan_test_{stamp}.mp4"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f"Prompt:  {prompt[:100]}...")
    print(f"Output:  {out_path}")
    print("=" * 70)

    provider = WanLocalProvider()

    print("\n[1/3] Checking ComfyUI health...")
    ok, info = provider._health()
    if not ok:
        print(f"  ❌ ComfyUI not reachable at {provider.base}")
        print(f"     Error: {info}")
        print("     Fix: start ComfyUI first — run 'run_nvidia_gpu.bat' in your ComfyUI folder.")
        sys.exit(2)
    print(f"  ✓ ComfyUI is up: {info[:80]}")

    print("\n[2/3] Loading workflow...")
    try:
        wf = provider._load_workflow()
        print(f"  ✓ Workflow loaded from {provider.workflow_path}")
        print(f"    Nodes: {len(wf)} — first few: {list(wf.keys())[:8]}")
    except ProviderError as e:
        print(f"  ❌ {e}")
        sys.exit(3)

    print("\n[3/3] Generating (this takes 3–7 min on RTX 4060 8GB)...")
    try:
        ok = provider.generate(prompt, out_path, duration_sec=5.0, aspect="16:9")
        if ok and out_path.exists():
            size_mb = out_path.stat().st_size / (1024 * 1024)
            print("\n" + "=" * 70)
            print(f"✅ SUCCESS: {out_path}")
            print(f"   Size:  {size_mb:.1f} MB")
            print(f"   Open:  start \"\" \"{out_path}\"")
            print("=" * 70)
        else:
            print("\n❌ Generation returned no output — check ComfyUI's console for errors.")
            sys.exit(4)
    except ProviderError as e:
        print(f"\n❌ Provider error: {e}")
        sys.exit(5)
    except Exception as e:
        print(f"\n❌ Unexpected error: {type(e).__name__}: {e}")
        sys.exit(6)


if __name__ == "__main__":
    main()
