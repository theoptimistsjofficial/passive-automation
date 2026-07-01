# PASSIVE AUTOMATION — YouTube pipeline for @OptimistMantra

End-to-end video generation pipeline: topic → script → visuals → TTS → rendered MP4.

## Setup

```bash
cd "C:\DEV\PASSIVE AUTOMATION"
python -m venv .venv
.venv\Scripts\activate     # PowerShell/CMD
# or:  source .venv/Scripts/activate   # Git Bash
pip install -r requirements.txt

cp .env.example .env
# Edit .env — GEMINI_API_KEY and PEXELS_API_KEY are optional (fallbacks exist)
```

## Run

```bash
python run.py                     # generates one video using DEFAULT_NICHE
python run.py positive_thinking   # override
python run.py devotional
python run.py positive_thinking --mark-done   # marks the topic complete in content_plan.json
```

Output: `io_data/output/<topic-id>_<timestamp>.mp4` + a JSON metadata sidecar.

## Layers (strict — do not cross-import)

- `core/` — schemas, config, logger. No external deps.
- `agents/` — pure functions (topic_picker, script_writer, visual_planner, seo_optimizer, quality_reviewer). No I/O.
- `services/` — external I/O (llm, tts, stock, renderer). No agent imports.
- `pipeline/` — orchestrator. Only layer that imports agents + services.
- `io_data/` — content plans, per-video metadata, output MP4s.
- `config/` — YAML niche configs.

## Niches

Configured in `config/niches.yaml`. Add a new niche by:
1. Adding a `niches.<key>` block with tone, colors, banned topics.
2. Creating `io_data/content_plans/<key>.json` with `topics` array.
3. Running `python run.py <key>`.

## Fallback behavior

| Missing | Fallback |
|---------|----------|
| `GEMINI_API_KEY` | Hand-written template scripts (positive_thinking & devotional) |
| `PEXELS_API_KEY` | Deterministic gradient placeholder images |
| Both | Still generates a working MP4 for pipeline testing |

## Next steps (not built yet)

- YouTube upload (`services/youtube.py`)
- Thumbnail generation with A/B variants
- Vertical 9:16 Short parallel render
- GitHub Actions daily cron
- Analytics feedback loop into topic_picker
