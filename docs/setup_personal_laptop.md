# Wan 2.2 setup for RTX 4060 8GB — precise sequence

Total time: ~90 min (30 min download + 30 min ComfyUI setup + 30 min first-video verification).

Do these in **exact order** — deviations tend to bite.

---

## Step 0 — pull latest code

```bash
cd /c/JAI/passive-automation
git pull origin main    # gets the load_dotenv(override=True) fix + test_wan.py + auto-detect
source .venv/Scripts/activate
```

---

## Step 1 — download ComfyUI portable

1. Open <https://github.com/comfyanonymous/ComfyUI/releases/latest> in a browser.
2. Download the latest release asset named **`ComfyUI_windows_portable_nvidia.7z`** (~1.5 GB). NOT the CPU or intel version.
3. Extract with 7-Zip to `D:\ComfyUI\` (or wherever you have 30 GB free).
4. Expected structure after extract:
   ```
   D:\ComfyUI\
   ├── ComfyUI\              ← the app
   │   └── models\           ← models go here
   ├── python_embeded\       ← bundled Python
   ├── update\
   ├── run_nvidia_gpu.bat    ← launcher
   └── run_cpu.bat
   ```

Double-click `run_nvidia_gpu.bat` once to sanity check — a console opens, then a browser tab opens at `http://127.0.0.1:8188`. If it does, hit `Ctrl+C` in the console to stop it. If it doesn't, your NVIDIA driver isn't recent enough — update via GeForce Experience first.

---

## Step 2 — install ComfyUI-Manager (makes everything else easier)

1. Open a **new** terminal.
2. Clone the manager into ComfyUI's custom_nodes folder:

   ```bash
   cd /d/ComfyUI/ComfyUI/custom_nodes
   git clone https://github.com/ltdrdata/ComfyUI-Manager.git
   ```

3. Restart ComfyUI (`run_nvidia_gpu.bat`). You should now see a **"Manager"** button in the browser UI's top right.

---

## Step 3 — download Wan 2.2 5B model files (~15 GB total)

Two options — pick one.

### Option A — via ComfyUI-Manager (easier, no CLI)

1. In ComfyUI browser UI: **Manager → Model Manager → search "wan 2.2 5b"**.
2. Install:
   - `wan2.2_ti2v_5B_fp16.safetensors` (diffusion model, ~10 GB)
   - `umt5_xxl_fp8_e4m3fn_scaled.safetensors` (text encoder, ~5 GB)
   - `wan2.2_vae.safetensors` (VAE, ~500 MB)
3. Restart ComfyUI when downloads complete.

### Option B — direct HuggingFace download

Manually download from `Comfy-Org/Wan_2.2_ComfyUI_Repackaged` on HuggingFace and place:

| File | Save to |
|------|---------|
| `wan2.2_ti2v_5B_fp16.safetensors` | `D:\ComfyUI\ComfyUI\models\diffusion_models\` |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | `D:\ComfyUI\ComfyUI\models\text_encoders\` |
| `wan2.2_vae.safetensors` | `D:\ComfyUI\ComfyUI\models\vae\` |

Or use `huggingface-cli`:
```bash
pip install "huggingface_hub[cli]"
cd /d/ComfyUI/ComfyUI/models
huggingface-cli download Comfy-Org/Wan_2.2_ComfyUI_Repackaged \
  split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors \
  split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors \
  split_files/vae/wan2.2_vae.safetensors \
  --local-dir .
# Then move each file from split_files/ into the matching subfolder above.
```

---

## Step 4 — open the built-in Wan 2.2 workflow

1. Start ComfyUI: `run_nvidia_gpu.bat` → browser opens at 127.0.0.1:8188.
2. Top menu: **Workflow → Browse Templates → Video → Wan 2.2 5B TI2V**
   (menu names sometimes shift — look for anything with "Wan 2.2" and "5B" in the name).
3. The workflow appears on the canvas. Verify these node classes exist:
   - `UNETLoader` — loads the 5B model
   - `CLIPLoader` — loads umt5
   - `VAELoader` — loads the vae
   - `CLIPTextEncode` (×2 — positive and negative prompts)
   - `KSampler` or similar
   - `SaveAnimatedWEBP` or `VHS_VideoCombine`
4. **Manual smoke test:** in the positive prompt node, type `"a peaceful mountain sunrise, cinematic"` and click **Queue Prompt**.
5. First run downloads model shards (~30 sec extra). Then generation. On RTX 4060 8GB expect **3–7 minutes** for a 5-second clip.
6. When it completes, you'll get an MP4 or WEBP in `D:\ComfyUI\ComfyUI\output\`. Open it — should be a moving cinematic mountain sunrise.

If this manual test works, ComfyUI + Wan is fully set up. Continue to step 5.

### Troubleshooting step 4

| Symptom | Fix |
|---------|-----|
| Red error: "Missing model" | Model files not in the right folder — recheck step 3 paths |
| Red error: "Missing custom nodes" | Manager → "Install Missing Custom Nodes" → restart |
| CUDA OOM during generation | Edit `run_nvidia_gpu.bat`, add `--lowvram` to the launch args. Try again. |
| Still OOM with `--lowvram` | Reduce workflow's `EmptyLatentImage` frame count from 121 → 81 (5s → 3.3s clip) |
| Generation is very slow (>15 min) | Normal for 4060 8GB on FP16. Consider the community FP8 quantised variant of the 5B model |

---

## Step 5 — export the workflow as API JSON

1. In ComfyUI, with the working Wan workflow loaded:
2. Top menu: **Workflow → Export (API)** — this saves the workflow in the format our pipeline needs. (NOT the regular Save, which uses a different schema.)
3. Save location: **`C:\JAI\passive-automation\config\workflows\wan22_5b.json`**
4. Our code auto-detects the positive prompt node — no manual node ID configuration needed.

---

## Step 6 — smoke test from our pipeline

```bash
cd /c/JAI/passive-automation
source .venv/Scripts/activate
python test_wan.py
```

This runs a standalone 5-second AI clip generation via our code. Expected output:

```
[1/3] Checking ComfyUI health...
  ✓ ComfyUI is up: {"system": {"os": "nt", ...
[2/3] Loading workflow...
  ✓ Workflow loaded from config/workflows/wan22_5b.json
    Nodes: 12 — first few: ['3', '6', '7', '8', ...]
[3/3] Generating (this takes 3–7 min on RTX 4060 8GB)...
  [ai_video] Wan: using prompt node '6' (autodetected)
  [ai_video] Wan queued: prompt_id=abc123
  [ai_video] Wan: in-queue (10s)
  [ai_video] Wan: in-queue (20s)
  ...
  [ai_video] Wan output (videos): wan_test_20260701_150000.mp4 (2340KB)

✅ SUCCESS: C:\JAI\passive-automation\io_data\output\wan_test_20260701_150000.mp4
```

Open the file — should be a cinematic 5s clip matching the default prompt (silhouetted figure walking mountain sunrise). Iterate on prompts with:

```bash
python test_wan.py "Lord Murugan riding his peacock through cosmic clouds, sacred devotional art, warm temple lighting"
```

If `test_wan.py` works, the AI plumbing is fully verified.

---

## Step 7 — enable AI video in the full pipeline

Edit `config/niches.yaml`:

```yaml
positive_thinking:
  ai_video:
    enabled: true          # ← flip this
    providers: ["wan_local"]
    hero_slides: ["hook", "middle"]
```

Then run the full pipeline (keep ComfyUI running in the other terminal):

```bash
python run.py positive_thinking
```

You'll see:
- Slides 1 and 4 → `AI video (hero) — providers=['wan_local']` → Wan generation (~5 min each)
- Slides 2, 3, 5, 6, 7 → `Pexels video: ...` → stock footage
- Final MoviePy assembly → ~2 min

Expected total build time on 4060 8GB: **~15–20 min**.

Final output: `io_data/output/pt-001_<timestamp>.mp4` — hero slides now show AI-generated cinematic clips instead of stock footage.

---

## Troubleshooting the pipeline integration

Everything below runs in your Git Bash terminal, in the project directory:

```bash
# Verify Wan config picked up
python -c "from core.config import load_niche; import json; n=load_niche('positive_thinking'); print(json.dumps(n.get('ai_video'), indent=2))"

# Test just the provider health without generating
python -c "from services.ai_video import WanLocalProvider; p=WanLocalProvider(); ok,info=p._health(); print('OK:',ok,'|',info[:200])"

# Inspect the workflow after export — see the auto-detected prompt node
python -c "
import json
from services.ai_video import _autodetect_positive_prompt_node
wf = json.loads(open('config/workflows/wan22_5b.json').read())
print('Positive prompt node:', _autodetect_positive_prompt_node(wf))
print('Its inputs:', wf[_autodetect_positive_prompt_node(wf)].get('inputs'))
"
```

If any of these fail, paste the output — the error message is intentionally verbose so we can pinpoint the fix.
