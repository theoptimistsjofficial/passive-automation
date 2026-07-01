# Personal-laptop setup — Wan 2.2 local + optional Veo

Your hardware: Lenovo Legion 5, i7-13650HX, 24GB RAM, **RTX 4060 8GB VRAM**.

That fits the **Wan 2.2 5B** model with ComfyUI's built-in VRAM offloading.
The 14B model needs 24GB+ VRAM — out of reach on the 4060, so we use 5B.

---

## Part 1 — Move this project to your personal laptop

The project currently lives at `C:\DEV\PASSIVE AUTOMATION` on your office laptop.
Move it to personal (recommended path): `D:\Projects\passive-automation`

```powershell
# On office laptop — push to GitHub (private repo)
cd "C:\DEV\PASSIVE AUTOMATION"
git init
git add .
git commit -m "initial pipeline: Level 2+3 renderer + AI video hooks"
gh repo create passive-automation --private --source . --push
```

```powershell
# On personal laptop — clone
mkdir D:\Projects
cd D:\Projects
gh repo clone <your-user>/passive-automation
cd passive-automation
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

---

## Part 2 — Install ComfyUI (Windows portable)

1. Download the **ComfyUI Windows portable** release from
   <https://github.com/comfyanonymous/ComfyUI/releases> — look for `ComfyUI_windows_portable_nvidia.7z` (recent).
2. Extract to `D:\ComfyUI` (or wherever — must be on a drive with 30GB+ free).
3. Verify it runs: double-click `run_nvidia_gpu.bat`. It should open your browser at `http://127.0.0.1:8188`.
4. Stop it (`Ctrl+C` in the console) — we'll configure models first.

---

## Part 3 — Download Wan 2.2 5B model files

ComfyUI's model directory is `D:\ComfyUI\ComfyUI\models\`.

You need three model files (all from HuggingFace, free):

| File | Save to | Size | Link |
|------|---------|------|------|
| Wan 2.2 5B T2V diffusion | `models\diffusion_models\` | ~10GB | [Wan-AI/Wan2.2-T2V-A14B on HF](https://huggingface.co/Wan-AI) — pick the 5B variant |
| Wan text encoder (umt5) | `models\text_encoders\` | ~5GB | on same repo |
| Wan VAE | `models\vae\` | ~500MB | on same repo |

> **Note:** file names shift between releases. Use ComfyUI-Manager to auto-download if manual is confusing:
> Install ComfyUI-Manager from <https://github.com/ltdrdata/ComfyUI-Manager>, restart ComfyUI, click "Manager" → "Install Models" → search "wan 2.2 5b".

---

## Part 4 — Get a Wan 2.2 workflow

1. Open ComfyUI (`run_nvidia_gpu.bat`) → browser opens at 127.0.0.1:8188.
2. In the top menu: **Workflow → Browse Templates → Video → Wan 2.2 5B** (or use `Workflow → Open` and drop in a `.json` from the community).
3. Verify the workflow: click **Queue Prompt** with a test prompt like `"a peaceful mountain sunrise, cinematic"`.
4. Wait ~3–7 minutes. You should get a 5-second MP4 in `D:\ComfyUI\ComfyUI\output\`.

If that works, you're done with the ComfyUI side.

---

## Part 5 — Save the workflow as API format

1. In ComfyUI web UI: **top menu → Save (API Format)**. NOT the regular Save.
2. Save the file as `wan22_5b.json` into your project: `D:\Projects\passive-automation\config\workflows\wan22_5b.json`.
3. Open the JSON — find the **positive text prompt node**. It's usually a `CLIPTextEncode` node with an `inputs.text` field.
4. Note its **node ID** (the numeric key in the JSON, e.g. `"6"` or `"39"`).
5. Update `services/ai_video.py` if the node ID isn't `"6"`:
   ```python
   prompt_node_id: str = "6",   # ← change to your positive-prompt node ID
   ```

---

## Part 6 — Enable AI video in the pipeline

Edit `config/niches.yaml`:

```yaml
positive_thinking:
  # ...
  ai_video:
    enabled: true              # ← flip this
    providers: ["wan_local"]   # veo is optional; drop it if no billing account
    hero_slides: ["hook", "middle"]
```

Start ComfyUI (`run_nvidia_gpu.bat`) — leave the console open.

Then in another terminal:
```powershell
cd D:\Projects\passive-automation
.venv\Scripts\activate
python run.py
```

The pipeline will:
- Generate the hook + middle slides via Wan (~3–7 min each on your 4060)
- Fetch stock video for the rest via Pexels
- Assemble the final MP4

Expected total build time per video: **20–30 min** (2 AI clips × 5 min + assembly).

---

## Part 7 — Optional: also enable Veo 3.1 API

**Only if you're willing to add a card to Google Cloud** (needed for API tier).

1. Get key at <https://aistudio.google.com/apikey>
2. Enable billing at <https://console.cloud.google.com/billing>
3. Add key to `.env`: `GEMINI_API_KEY=xxxxx`
4. Update config: `providers: ["wan_local", "veo"]` — Veo becomes fallback when ComfyUI is offline.

Veo Fast: **~$0.15 per 8-second clip** past free trial credit.
Veo Standard: **~$0.40–0.75 per 8-second clip**.

---

## Troubleshooting on RTX 4060 8GB

| Problem | Fix |
|---------|-----|
| **CUDA out of memory** | In ComfyUI's launch args, add `--lowvram` or `--novram`. Also reduce workflow's resolution to 480p or frame count to 81. |
| **Very slow (>10 min per clip)** | Normal for 4060 8GB on 5B. Try FP8 quantized version of the model. |
| **ComfyUI can't find model** | Verify path matches ComfyUI's config — `models\diffusion_models\<file>.safetensors` |
| **Workflow errors "node not found"** | Install ComfyUI-Manager, then "Install Missing Custom Nodes" |
| **HTTP 404 from pipeline** | Confirm `run_nvidia_gpu.bat` is running and browser can reach 127.0.0.1:8188 |

---

## When you're done

Test with:
```powershell
python run.py positive_thinking
```

The console will show `AI video (hero) — providers=['wan_local']` for slides 1 and 4 (middle of 7), and `Pexels video` for the rest. Total: ~20 min. Output MP4 in `io_data\output\`.
