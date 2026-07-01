from core.schemas import VideoScript, QualityVerdict
from core.logger import get_logger

log = get_logger("quality")


def review(script: VideoScript, niche: dict) -> QualityVerdict:
    reasons = []
    banned = [b.lower() for b in niche.get("banned_topics", [])]

    combined = " ".join(
        [script.hook, script.cta] + [s.narration for s in script.slides] + [s.body for s in script.slides]
    ).lower()

    for term in banned:
        if term in combined:
            reasons.append(f"Contains banned topic: {term}")

    total_narration_words = sum(len(s.narration.split()) for s in script.slides)
    if total_narration_words < 80:
        reasons.append(f"Narration too short: {total_narration_words} words")
    if total_narration_words > 400:
        reasons.append(f"Narration too long: {total_narration_words} words")

    if len(script.hook.split()) > 20:
        reasons.append("Hook exceeds 20 words — will lose attention")

    verdict = QualityVerdict(approved=(len(reasons) == 0), reasons=reasons)
    log.info(f"Quality review: {'APPROVED' if verdict.approved else 'REJECTED'} ({len(reasons)} issues)")
    for r in reasons:
        log.warning(f"  - {r}")
    return verdict
