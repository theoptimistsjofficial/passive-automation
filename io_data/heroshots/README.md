# Hero shots dropbox

Pre-generated AI video clips from cloud tools (Kling, Vidu, Hailuo, etc.) go here.
The pipeline picks them up before falling through to Wan or Pexels.

## Folder layout

```
io_data/heroshots/
├── positive_thinking/
│   ├── slide_01.mp4    ← hook slide
│   └── slide_04.mp4    ← middle slide
└── devotional/
    ├── slide_01.mp4
    ├── slide_04.mp4
    └── slide_08.mp4    ← cta slide
```

## Naming convention

- File name: `slide_{NN}.{ext}` where `NN` is the zero-padded slide index (`01`, `04`, `08`).
- Which slides are AI-driven is set by `niche.ai_video.hero_slides` in `config/niches.yaml`:
  - `positive_thinking`: `["hook", "middle"]` → slides 1 and 4
  - `devotional`: `["hook", "middle", "cta"]` → slides 1, 4 (or 5), and 8
- Accepted extensions: `.mp4`, `.mov`, `.webm`, `.mkv`

## Which slide index corresponds to which alias?

- `hook` → slide 1
- `middle` → floor(total_slides / 2) + 1  (e.g. 7-slide script → slide 4)
- `cta` / `outro` → last slide (e.g. slide 7 or slide 8)

Log output of `python run.py <niche>` will print the resolved hero indices on start.

## Free cloud generators (as of 2026)

| Tool | URL | Free credits/day | Notes |
|---|---|---|---|
| **Vidu 2** | vidu.studio | ~80 credits (~4 clips) | Best for consistency across scenes — supports reference images |
| **Kling AI** | klingai.com | ~166 credits (~4–5 clips) | Highest general quality (Kling 2.0 in free tier) |
| **Hailuo AI** | hailuoai.video | ~100 credits (~2–3 clips) | Strong cinematic motion |
| **Freepik Video** | freepik.com | ~20 credits (~1 clip) | Aggregator (Kling/Wan/MiniMax) |
| **PixVerse** | pixverse.ai | ~60 credits (~2 clips) | Fast, permissive |

Combined: ~10 hero clips per day, entirely free.

## Workflow

1. Load `io_data/output/temp/{topic_id}/` to see the narration for hook/middle/cta slides.
2. Craft a prompt in your favourite generator. Use the niche's `wan_prompt_style` as inspiration.
3. Download the resulting MP4.
4. Rename to `slide_{NN}.mp4` (matching the hero slide index).
5. Drop into `io_data/heroshots/{niche_key}/`.
6. Run `python run.py {niche_key}` — the pipeline uses your clip instead of generating with Wan.

If a slot is missing, the pipeline falls back to Wan (local, unlimited) then Pexels stock.
Nothing breaks — you can pre-populate any subset.
