import copy

from .llm import LLMClient, LLMUnavailable
from .prompts import translate_prompt

# enum-like values the UI depends on must stay in English; the UI localizes their labels itself
SKIP_KEYS = {"engine", "risk_level", "verdict", "severity"}


def _walk(obj, out: list, key=None):
    if isinstance(obj, dict):
        for k, v in obj.items():
            _walk(v, out, k)
    elif isinstance(obj, list):
        for v in obj:
            _walk(v, out, key)
    elif isinstance(obj, str) and key not in SKIP_KEYS and any(c.isalpha() for c in obj):
        out.append(obj)


def _rebuild(obj, it, key=None):
    if isinstance(obj, dict):
        return {k: _rebuild(v, it, k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_rebuild(v, it, key) for v in obj]
    if isinstance(obj, str) and key not in SKIP_KEYS and any(c.isalpha() for c in obj):
        return next(it)
    return obj


def translate_payload(payload: dict, language: str, llm: LLMClient) -> tuple[dict, bool]:
    """Translate every string value of a result dict. Returns (payload, translated_ok)."""
    if language == "English":
        return payload, True
    strings: list[str] = []
    _walk(payload, strings)
    if not strings:
        return payload, True
    try:
        out = llm.generate_json(translate_prompt(strings, language))
        if not isinstance(out, list) or len(out) != len(strings):
            raise ValueError("length mismatch")
        return _rebuild(copy.deepcopy(payload), iter(str(x) for x in out)), True
    except (LLMUnavailable, ValueError):
        return payload, False
