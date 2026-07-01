import json
from pathlib import Path
from core.config import ROOT
from core.logger import get_logger

log = get_logger("topic_picker")


def pick_next_topic(niche: dict) -> dict:
    plan_path = ROOT / niche["content_plan"]
    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)

    for item in plan["topics"]:
        if item.get("status", "pending") == "pending":
            log.info(f"Picked topic: {item['id']} — {item['title']}")
            return item

    raise RuntimeError(f"No pending topics left in {plan_path}. Add more or reset statuses.")


def mark_complete(niche: dict, topic_id: str) -> None:
    plan_path = ROOT / niche["content_plan"]
    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)
    for item in plan["topics"]:
        if item["id"] == topic_id:
            item["status"] = "complete"
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    log.info(f"Marked {topic_id} complete")
