# Hero shots workflow — free cloud AI video for hook/middle/cta slides

Instead of waiting 16 min per clip on local Wan (which produces ~Runway Gen-2 quality),
this workflow uses free daily credits from Kling/Vidu/Hailuo to produce hero shots at
Kling 2.0 quality, then drops them into the pipeline.

## Why this exists

- Wan 2.2 5B on 8 GB VRAM ≈ mid-2023 SOTA. Fine for exploration, not for publishing.
- Cloud AI video tools (Kling 2.0, Vidu 2, Hailuo 02) give you 2024/2025 SOTA — for free — with daily credit limits.
- Total free budget: ~10 hero clips/day across all platforms combined.
- Publishing cadence of 2–3 videos/day needs 4–9 hero clips/day. Perfectly matches.

## Free tools ranked for this pipeline

| Tool | URL | Free/day | Best for |
|---|---|---|---|
| **Vidu 2** | vidu.studio | ~80 credits (~4 clips) | Devotional niche — reference-to-video keeps deity looking consistent across scenes |
| **Kling AI** | klingai.com | ~166 credits (~4–5 clips) | Positive-thinking niche — best general cinematic quality |
| **Hailuo AI** | hailuoai.video | ~100 credits (~2–3 clips) | Slow reverent camera work (both niches) |
| **PixVerse** | pixverse.ai | ~60 credits (~2 clips) | Overflow — permissive content policy |

All support Hindu deity imagery (unlike Sora/DALL·E which often refuse religious content).

## End-to-end workflow

### Step 1 — run the pipeline in "planning mode" first (optional but helpful)

To know what the AI is meant to depict on each hero slide, do a dry pipeline run with
`ai_video.enabled: false` (or just look at the temp folder from a prior run):

```bash
python run.py positive_thinking
# then inspect io_data/output/temp/{topic_id}/ for narration & stock_query per slide
```

Or programmatically:

```bash
python -c "
from core.config import load_niche
from agents.topic_picker import pick_next_topic
from agents.script_writer import write_script
from agents.visual_planner import enrich_stock_queries
from agents.scene_director import choose_hero_indices, enhance_prompt_for_ai
import json

niche = load_niche('positive_thinking')
topic = pick_next_topic(niche)
script = write_script(topic, niche, channel='OptimistMantra')
script = enrich_stock_queries(script, niche)
hero_indices = choose_hero_indices(script, niche)

for slide in script.slides:
    if slide.index in hero_indices:
        prompt = enhance_prompt_for_ai(slide.narration, slide.stock_query, niche)
        print(f'--- slide_{slide.index:02d} ---')
        print(prompt)
        print()
"
```

This gives you the exact prompt for each hero slide — copy it into the cloud tool's prompt box.

### Step 2 — generate the clip in the cloud tool

**In Kling AI (or Vidu / Hailuo — pick per the table above):**

1. Sign in (free account).
2. Paste the prompt from step 1.
3. Choose settings:
   - Aspect: **16:9** (or 9:16 if you're doing Shorts)
   - Duration: **5 seconds**
   - Quality: highest available in free tier (e.g. Kling 2.0 Standard)
4. Generate. Takes ~30 sec – 2 min in the cloud (vs ~16 min locally).
5. Download the MP4 when done.

### Step 3 — drop into the pipeline

Rename the downloaded file to match the slide index and drop into the niche folder:

```
io_data/heroshots/positive_thinking/slide_01.mp4    ← hook clip
io_data/heroshots/positive_thinking/slide_04.mp4    ← middle clip
```

For devotional (`["hook", "middle", "cta"]`), you'll also drop `slide_08.mp4` or whatever the CTA index is.

### Step 4 — run the full pipeline

```bash
python run.py positive_thinking
```

Pipeline log should print:
```
[ai_video] ManualDropbox: using pre-generated clip slide_01.mp4 (2.3MB) for slide 1
[ai_video] ManualDropbox: using pre-generated clip slide_04.mp4 (2.5MB) for slide 4
```

No Wan wait time. No 16-min-per-slide gen. Just MoviePy assembly (~2 min total).

## What happens if a clip is missing?

The pipeline falls through in this order:
1. **manual_dropbox** — your pre-generated clip
2. **wan_local** — local Wan on your Legion (16 min, if ComfyUI is running)
3. **veo** — Google Veo (requires paid Tier 1 API)
4. **fetch_scene** — Pexels stock footage

You can pre-populate any subset. Missing slides fall through automatically.

## Consistency across scenes (crucial for devotional)

For Kanda Shashti Kavasam / Murugan videos, upload the same reference images to every clip in **Vidu 2**:
- One image of Murugan's face (from a public temple art photo)
- One image of the peacock (Murugan's vahana)
- One image of the temple/setting

Vidu's "Multi-Elements" or "Reference-to-Video" feature will preserve these across all 3–4 hero clips in the same video → the deity actually looks like the same person from clip to clip.

Kling AI and Hailuo have similar (weaker) reference features. Wan has essentially none.

## Prompt tips that actually move the needle

- **Start with a subject verb** — "Lord Murugan raising his vel" beats "an image of Lord Murugan"
- **Include camera direction** — "slow dolly forward", "drone pullback", "handheld tracking"
- **Style anchors matter** — "sacred devotional art style", "warm temple lighting", "painterly aesthetic"
- **Negative prompt** — "no text, no modern elements, no distortion, no static frame"
- **Duration cue** — "over 5 seconds" helps some models pace motion correctly

The `enhance_prompt_for_ai()` function in `agents/scene_director.py` already assembles these
using the niche's `wan_prompt_style`. Just copy its output.

## Budget math per video

**Positive thinking** — 2 hero slides × 1 clip each = 2 free-tier clips per video
  - 5 videos/week = 10 clips/week
  - Kling alone (~30 credits/clip, 166 credits/day) = ~5 clips/day = plenty of headroom

**Devotional** — 3 hero slides × 1 clip each = 3 free-tier clips per video (Vidu preferred for consistency)
  - 3 videos/week = 9 clips/week
  - Vidu 2 (~20 credits/clip, ~80 credits/day) = ~4 clips/day = plenty

No paid tier needed until you scale past ~10 videos/day per niche.
