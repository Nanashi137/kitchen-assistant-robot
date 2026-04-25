from typing import Any, Dict, List


def normalize_viable_objects(
    viable_raw: Any,
    entity_action: Dict[str, str],
) -> List[dict]:
    """Map LLM viable_objects (strings or dicts) to list[dict] for downstream prompts."""
    if viable_raw is None:
        return []
    if not isinstance(viable_raw, list):
        return []

    out: List[dict] = []
    for item in viable_raw:
        if isinstance(item, dict) and item:
            out.append(item)
            continue
        name = str(item).strip()
        if not name:
            continue
        role = "alternative for this request"
        matched = False
        for ent, r in entity_action.items():
            if name.lower() == ent.lower():
                role = r
                matched = True
                break
        if not matched:
            for ent, r in entity_action.items():
                el, nl = ent.lower(), name.lower()
                if el in nl or nl in el:
                    role = r
                    break
        out.append({name: role})
    return out


def normalize_knowno_ambiguity_type_label(raw: str) -> str:
    """Align type prompt output with internal labels (e.g. Common sense)."""
    t = (raw or "").strip().lower()
    if t == "safety":
        return "Safety"
    if t == "preference":
        return "Preference"
    if "common" in t and "sense" in t:
        return "Common sense"
    return "Common sense"
