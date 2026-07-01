# BGM library setup — one-time (~15 min)

Public music APIs (Pixabay, Freesound) have become unreliable for programmatic music access
in 2026. Simpler approach: seed a local library once, code random-picks per video.

## Where to get royalty-free tracks

Free sources (no attribution needed, YouTube-safe):

1. **YouTube Audio Library** (best for our use case)
   URL: https://www.youtube.com/audiolibrary
   - Sign in to your YouTube Studio → Audio Library
   - Filter by mood: **Inspirational / Calm / Cinematic** for positive_thinking
   - Filter by mood: **Peaceful / Meditation / Ambient** for devotional
   - Filter by attribution: "Attribution not required"
   - Download 10–15 tracks per niche

2. **Pixabay Music** (browser download, no API needed)
   URL: https://pixabay.com/music/
   Search: "uplifting cinematic", "meditation", "sacred ambient"
   License: royalty-free, YouTube-safe

3. **Freesound.org** (register free → download)
   URL: https://freesound.org/
   Search + filter by CC0 license

4. **Chosic** (free instrumental)
   URL: https://www.chosic.com/free-music/all/

5. **Bensound** (some free, some paid)
   URL: https://www.bensound.com/

## What to download

**Positive thinking niche** (`io_data/bgm/positive_thinking/`)
- Genre: cinematic, inspirational, uplifting, warm piano, orchestral pop
- Tempo: 90–110 BPM, slow build
- Length: 60–120 sec each (matches our 45–60 sec videos with fade room)
- Mood: hopeful, warm, resolved
- Aim for 10–15 tracks so the algorithm doesn't hear the same track daily

**Devotional niche** (`io_data/bgm/devotional/`)
- Genre: sacred ambient, meditation, indian classical instrumental, tanpura drone
- Tempo: slow (60–80 BPM) or no measurable tempo (ambient)
- Length: 60–120 sec
- Mood: reverent, peaceful, meditative
- Search terms: "meditation", "temple", "sacred", "spiritual ambient", "sitar meditation"
- Aim for 10–15 tracks

## File format

- MP3 (recommended, small file size) or WAV/M4A/OGG (also supported)
- Any file name — code picks by extension, not name
- Bitrate: 128–192 kbps is fine (BGM is played at −18 dB anyway)

## Structure

After seeding:

```
io_data/bgm/
├── positive_thinking/
│   ├── uplifting_moment.mp3
│   ├── new_beginnings.mp3
│   ├── hope_rising.mp3
│   ├── ...
│   └── warm_piano_reflection.mp3
└── devotional/
    ├── temple_meditation.mp3
    ├── sacred_flute.mp3
    ├── mantra_ambient.mp3
    ├── ...
    └── divine_silence.mp3
```

## Verify

```bash
python -c "
from pathlib import Path
from services.music import BGM_LIBRARY
for niche in ['positive_thinking', 'devotional']:
    tracks = list((BGM_LIBRARY / niche).glob('*'))
    tracks = [t for t in tracks if t.suffix.lower() in {'.mp3', '.wav', '.m4a', '.ogg'}]
    print(f'{niche}: {len(tracks)} tracks')
"
```

Expected:
```
positive_thinking: 12 tracks
devotional: 10 tracks
```

## Do NOT commit BGM files

They're already in `.gitignore` under `io_data/bgm/**/*.mp3` etc — see `.gitignore`.
Keep them local only (large files, licensing edge cases).

## After seeding

Just run the pipeline as normal:
```bash
python run.py positive_thinking
```

Each run picks a random track from the matching niche folder. Log will say:
```
[INFO] music: BGM (local): 'uplifting_moment.mp3' (2340KB) → bgm.mp3
```
