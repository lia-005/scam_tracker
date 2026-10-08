import json
import re


def extract_json(text: str):
    """Parse JSON from an LLM reply that may contain code fences or extra prose."""
    if not text:
        raise ValueError("Empty model response")
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    for open_c, close_c in (("{", "}"), ("[", "]")):
        start, end = cleaned.find(open_c), cleaned.rfind(close_c)
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("Could not parse JSON from model response")
