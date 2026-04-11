import json
import re
from typing import Any, Dict


def parse_llm_json_object(content: str) -> Dict[str, Any]:
    """Parse a JSON object from LLM output; strips optional markdown fences."""
    text = (content or "").strip()
    if not text:
        raise ValueError("empty LLM content")
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
        text = text.strip()
    return json.loads(text)
