# Full automation setup — 500–1000 INR/month, hands-off daily videos

End-to-end setup for the "human-quality automated" pipeline:
- Script: Gemini 2.5 Flash (free API)
- Voice: ElevenLabs Turbo v2.5 (free 10k chars/mo)
- Video hero clips: Fal.ai Kling 2.0 Master ($0.40/clip × ~24/month ≈ ₹805)
- Music: Pixabay (free)
- B-roll fill: Pexels (free)
- Upload: YouTube Data API v3 (free)
- Scheduler: GitHub Actions cron (free)

Total: ~₹805/month for 12 videos/month (3/week).

---

## Part 1 — Sign up for the 5 accounts (15 min)

### 1. Gemini API key
- URL: https://aistudio.google.com/apikey
- Sign in with Google, click "Create API key"
- Copy key → save as `GEMINI_API_KEY`

### 2. Fal.ai account (video generation)
- URL: https://fal.ai/
- Sign up → Dashboard → API Keys → Create
- Copy → save as `FAL_API_KEY`
- $10 free credit on signup = ~25 clips before spend starts

### 3. ElevenLabs account (voice)
- URL: https://elevenlabs.io/
- Sign up (free tier: 10k chars/mo, commercial use OK)
- Profile icon → API Keys → Create
- Copy → save as `ELEVENLABS_API_KEY`
- Default voice ID (Rachel) is preloaded; change with `ELEVENLABS_VOICE_ID` if desired

### 4. Pixabay API key (music + fallback images)
- URL: https://pixabay.com/api/docs/
- Sign up → your API key is at the top of the docs page
- Copy → save as `PIXABAY_API_KEY`

### 5. Pexels API key (stock video)
- URL: https://www.pexels.com/api/
- Sign up → generate key
- Copy → save as `PEXELS_API_KEY`

---

## Part 2 — YouTube OAuth (one-time, ~10 min)

### 2a. Enable YouTube Data API v3

1. Go to https://console.cloud.google.com/
2. Create project "PassiveAutomation" (or reuse existing)
3. APIs & Services → Library → search "YouTube Data API v3" → **Enable**

### 2b. Create OAuth credentials

4. APIs & Services → OAuth consent screen
   - User Type: **External**
   - App name: `PassiveAutomation`
   - Support email: your Google account
   - Scopes: (skip, we set programmatically)
   - Test users: **Add** the Google account that owns `@OptimistMantra`
   - Save

5. APIs & Services → Credentials → Create Credentials → **OAuth client ID**
   - Application type: **Desktop app**
   - Name: `PassiveAutomation Desktop`
   - Create → **Download JSON**
   - Save the downloaded file to: `config/youtube_client_secret.json`

### 2c. Run the OAuth flow (one-time)

```bash
cd /c/JAI/passive-automation
source .venv/Scripts/activate
pip install -r requirements.txt  # picks up google-api-python-client and google-auth-oauthlib
python scripts/setup_youtube_oauth.py
```

- Browser opens → sign in with the `@OptimistMantra` Google account
- Grant YouTube upload permission
- Script saves `config/youtube_token.json` (refresh token) — do NOT commit this

### 2d. Verify

```bash
python -c "from services.youtube import _load_credentials; _load_credentials(); print('YouTube auth OK')"
```

Should print `YouTube auth OK`.

---

## Part 3 — Populate .env

Create `.env` at the project root:

```env
GEMINI_API_KEY=your_gemini_key_here
PEXELS_API_KEY=your_pexels_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
FAL_API_KEY=your_fal_key_here
FAL_MODEL=fal-ai/kling-video/v2/master/text-to-video
PIXABAY_API_KEY=your_pixabay_key_here
CHANNEL_NAME=OptimistMantra
DEFAULT_NICHE=positive_thinking
```

**Model options for `FAL_MODEL`** (change to trade cost for quality):

| Model | Cost/5s | Quality |
|---|---|---|
| `fal-ai/ltx-video` | ~$0.02 | Low (2023-era) |
| `fal-ai/wan-t2v-14b` | ~$0.20 | Good (Kling 1.5) |
| `fal-ai/hailuo-02/standard/text-to-video` | ~$0.30 | Very good |
| `fal-ai/kling-video/v2/master/text-to-video` | ~$0.40 | Excellent (recommended) |
| `fal-ai/veo3-fast` | ~$0.75 | Near-SOTA |
| `fal-ai/kling-video/v2-5/pro/text-to-video` | ~$1.50 | SOTA |

Default is Kling 2.0 Master — the sweet spot for ₹1000/month budget.

---

## Part 4 — First local test

Test each service, then the full pipeline.

### 4a. Test individual services

```bash
# LLM (Gemini)
python -c "from services.llm import generate_json; print(generate_json('Return {\"ok\": true} as JSON'))"

# ElevenLabs voice
python -c "
from services.tts import synthesize
from pathlib import Path
synthesize('Hello, this is a test.', Path('io_data/output/tts_test.mp3'))
print('Voice ready — play io_data/output/tts_test.mp3')
"

# Fal.ai video (~30 sec)
python -c "
from services.ai_video import FalAiProvider
from pathlib import Path
p = FalAiProvider()
p.generate('a peaceful sunrise over mountains, cinematic slow drone pullback', Path('io_data/output/fal_test.mp4'))
print('AI clip ready — play io_data/output/fal_test.mp4')
"

# Pixabay music
python -c "
from services.music import fetch_bgm
from pathlib import Path
fetch_bgm('positive_thinking', Path('io_data/output/bgm_test.mp3'))
"

# YouTube (dry auth check only)
python -c "from services.youtube import _load_credentials; _load_credentials(); print('YouTube auth OK')"
```

### 4b. Full pipeline (local)

```bash
python run.py positive_thinking            # generates locally, no upload
python run.py positive_thinking --upload   # uploads unlisted for review
```

Expected output: `io_data/output/pt-001_<timestamp>.mp4` — ~50 sec, hero shots via Kling 2.0, ElevenLabs voice, BGM mixed underneath.

---

## Part 5 — GitHub Actions cron (fully hands-off)

### 5a. Push all API keys to GitHub secrets

- Repo → Settings → Secrets and variables → Actions → New repository secret

Add each:
- `GEMINI_API_KEY`
- `PEXELS_API_KEY`
- `ELEVENLABS_API_KEY`
- `ELEVENLABS_VOICE_ID`
- `FAL_API_KEY`
- `FAL_MODEL` (optional, defaults to Kling 2.0 Master)
- `PIXABAY_API_KEY`
- `CHANNEL_NAME`
- `YOUTUBE_CLIENT_SECRET` — paste the entire contents of `config/youtube_client_secret.json` as a single-line string
- `YOUTUBE_TOKEN` — paste the entire contents of `config/youtube_token.json`

### 5b. Verify cron schedule

`.github/workflows/daily.yml` is already configured:
- Mon/Wed/Fri at 8:30 IST → positive_thinking
- Tue/Thu/Sat at 8:30 IST → devotional

### 5c. Test manually via GitHub UI

- Repo → Actions → "Daily video generation" → Run workflow
- Select niche, choose upload true, privacy unlisted
- Wait ~30 min → check YouTube for the video

---

## Part 6 — Cost tracking

Fal.ai dashboard shows real-time credit usage: https://fal.ai/dashboard

**Expected monthly spend:**
- 12 videos × 2 hero clips × $0.40 = **$9.60/month (~₹805)**
- Small buffer: signup credit ($10) covers first month entirely

If usage runs high:
- Downgrade to Hailuo 02 Standard: `FAL_MODEL=fal-ai/hailuo-02/standard/text-to-video` → $0.30/clip = $7.20/month
- Or drop to 1 hero clip per video: **$4.80/month**

---

## Part 7 — What happens each morning

1. GitHub Actions cron fires at 8:30 IST
2. Runs `python run.py <niche> --mark-done --upload --public`
3. Pipeline:
   - Picks next pending topic from content plan
   - Generates script via Gemini (~5 sec)
   - Renders TTS via ElevenLabs (~10 sec)
   - Generates 2 hero clips via Fal.ai Kling 2.0 Master (~2 min)
   - Fetches 5 Pexels stock clips (~30 sec)
   - Fetches mood-matched BGM from Pixabay (~5 sec)
   - Assembles video in MoviePy (~2 min)
   - Uploads to YouTube (~2 min)
4. You get an email from YouTube: "Your video is now live"
5. Total wall time: ~7–10 min per video, hands-off

---

## Troubleshooting

### Fal.ai returns 401
- `FAL_API_KEY` wrong or expired — check dashboard

### ElevenLabs quota exhausted
- Free tier ran out (10k chars/mo) — pipeline auto-falls back to gTTS
- Or upgrade to Starter ($5/mo = 30k chars = 30 videos)

### Fal.ai returns "insufficient credit"
- Free $10 credit exhausted — add card at fal.ai/billing

### YouTube upload fails with 403
- Content flagged — check YouTube Studio → Uploads for the reason
- Common: monetization dispute (fine for unlisted/private), copyright claim on BGM (change Pixabay track)

### Wrong voice sound
- ElevenLabs has many voices — swap `ELEVENLABS_VOICE_ID` in .env
- Voice IDs: https://elevenlabs.io/app/voice-library
- Default `21m00Tcm4TlvDq8ikWAM` is "Rachel" (warm, calm female)
- For devotional consider: `29vD33N1CtxCmqQRPOHJ` "Drew" (deep, meditative male)

---

## Downgrade / stop

- To pause automation: Repo → Actions → daily.yml → Disable workflow
- To stop spend: revoke `FAL_API_KEY` at fal.ai dashboard
- To un-upload: manual delete in YouTube Studio (each video ID printed in Actions logs)
