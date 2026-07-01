import json
from core.schemas import VideoScript, Slide
from core.logger import get_logger
from services.llm import generate_json

log = get_logger("script_writer")


PROMPT_TEMPLATE = """You are an expert YouTube scriptwriter for the channel "{channel}".
Niche: {niche_name}
Voice tone: {voice_tone}

Topic ID: {topic_id}
Topic title: {topic_title}
Topic context: {topic_context}

Write a {slides} slide video script. Return STRICT JSON matching this schema — no prose, no markdown fences:

{{
  "topic_id": "{topic_id}",
  "title_working": "short compelling working title (max 70 chars)",
  "hook": "first 3 seconds — a question or bold statement that stops the scroll",
  "slides": [
    {{
      "index": 1,
      "heading": "4-6 word heading shown on screen",
      "body": "1-2 sentence body text shown on screen",
      "narration": "20-40 word voiceover for this slide, natural spoken cadence",
      "stock_query": "2-4 word Pexels search query for this slide's background image"
    }}
  ],
  "cta": "closing 1-sentence call to action (subscribe, comment, etc.)"
}}

Rules:
- Total narration across slides ≈ 60-90 seconds spoken
- Every claim must be factual and citable — no fabricated quotes, dates, or events
- Avoid: medical/legal advice, defamation, unverified rumors
- Use everyday English, 8th-grade reading level
- Each slide should stand alone but connect to the next
"""


FALLBACK_SCRIPT = {
    "positive_thinking": {
        "title_working": "How She Turned Rejection Into a Global Movement",
        "hook": "She was rejected 30 times before one yes changed everything.",
        "slides": [
            {"index": 1, "heading": "Thirty Doors Slammed Shut", "body": "One dream. Thirty rejections. Zero backup plan.",
             "narration": "Before J.K. Rowling became a household name, twelve publishers rejected the first Harry Potter book. She was a single mother on welfare, writing in cafes.",
             "stock_query": "person writing cafe"},
            {"index": 2, "heading": "The Yes That Almost Wasn't", "body": "A publisher's 8-year-old daughter said yes for him.",
             "narration": "Bloomsbury only agreed to publish after the CEO's young daughter read the first chapter and demanded more.",
             "stock_query": "child reading book"},
            {"index": 3, "heading": "One Small Advance", "body": "£1,500. That was it.",
             "narration": "Rowling was told to get a day job — children's books don't make money.",
             "stock_query": "empty bookshelf"},
            {"index": 4, "heading": "The Turn", "body": "Word of mouth changed the trajectory.",
             "narration": "Kids passed the book to friends. Teachers read it aloud. Libraries couldn't keep it on shelves.",
             "stock_query": "children reading library"},
            {"index": 5, "heading": "500 Million Copies Later", "body": "The rejected manuscript became history.",
             "narration": "Every rejection letter was, in hindsight, one publisher missing the biggest story of the decade.",
             "stock_query": "stack of books"},
            {"index": 6, "heading": "What Rejection Really Means", "body": "It's data, not verdict.",
             "narration": "A no is not a judgment on your worth — it's information about that one door. Keep knocking.",
             "stock_query": "sunrise mountain"},
            {"index": 7, "heading": "Your Thirty-First Yes", "body": "It's already waiting.",
             "narration": "The only way to guarantee no is to stop asking. Somewhere out there, your yes is waiting.",
             "stock_query": "open door light"},
        ],
        "cta": "If this reminded you why you started — hit subscribe. Tomorrow: another real story."
    },
    "devotional": {
        "title_working": "Kanda Shashti Kavasam Verse 1 Meaning — Explained",
        "hook": "Do you know what the very first word of Kanda Shashti Kavasam actually invokes?",
        "slides": [
            {"index": 1, "heading": "The Opening Invocation", "body": "Thuthiporkku Val Vinaipom",
             "narration": "The Kavasam opens with a promise — for those who praise Lord Murugan, harmful karma dissolves.",
             "stock_query": "hindu temple sunrise"},
            {"index": 2, "heading": "Word by Word", "body": "Thuthiporkku = to those who praise",
             "narration": "Thuthi means devotional praise, and porkku means to those who offer it. The listener is placed inside the promise.",
             "stock_query": "temple lamp devotion"},
            {"index": 3, "heading": "Val Vinaipom", "body": "Val = strong, Vinai = karma, Pom = will go",
             "narration": "Val Vinaipom — even the most powerful negative karma departs. The verse doesn't say some — it says all.",
             "stock_query": "candle flame prayer"},
            {"index": 4, "heading": "Why This Order", "body": "Removal before request.",
             "narration": "Notice — Devaraya first removes obstacles before asking for anything. Cleanse, then invoke.",
             "stock_query": "flowing water river"},
            {"index": 5, "heading": "The Sage Behind It", "body": "Devaraya Swamigal, 19th century",
             "narration": "The Kavasam was composed by Devaraya Swamigal of Thiruvidaimaruthur, a devotee healed by Murugan himself.",
             "stock_query": "ancient manuscript"},
            {"index": 6, "heading": "How to Approach It", "body": "Understanding deepens devotion.",
             "narration": "Chanting with meaning is not lesser than chanting without — it is deeper. The words become alive.",
             "stock_query": "meditation posture"},
            {"index": 7, "heading": "Six Days, Six Verses", "body": "Kanda Shashti spans six days.",
             "narration": "The Kavasam is traditionally recited during Kanda Shashti — the six days before the full moon of Aippasi.",
             "stock_query": "temple bells"},
            {"index": 8, "heading": "Verse 2 Tomorrow", "body": "Sulori Ayilvel Sudarvel Vezhi",
             "narration": "In the next verse we meet the Vel — Murugan's divine spear. Its every syllable holds power.",
             "stock_query": "murugan vel spear"},
        ],
        "cta": "Subscribe to walk through every verse of the Kavasam — one lesson, one day."
    }
}


def write_script(topic: dict, niche: dict, channel: str = "OptimistMantra") -> VideoScript:
    prompt = PROMPT_TEMPLATE.format(
        channel=channel,
        niche_name=niche["display_name"],
        voice_tone=niche["voice_tone"],
        topic_id=topic["id"],
        topic_title=topic["title"],
        topic_context=topic.get("context", ""),
        slides=niche["slides_per_video"],
    )

    try:
        raw = generate_json(prompt)
        script = VideoScript(**raw)
        log.info(f"Script generated via LLM: {len(script.slides)} slides")
        return script
    except Exception as e:
        log.warning(f"LLM script generation failed ({e}); using fallback template")
        fb = FALLBACK_SCRIPT.get(niche["_key"], FALLBACK_SCRIPT["positive_thinking"])
        return VideoScript(
            topic_id=topic["id"],
            title_working=fb["title_working"],
            hook=fb["hook"],
            slides=[Slide(**s) for s in fb["slides"]],
            cta=fb["cta"],
        )
