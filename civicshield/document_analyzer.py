import re

from . import config
from .llm import LLMClient, LLMUnavailable
from .prompts import document_prompt

HEADINGS = {
    "benefits": r"benefits?|what you get|assistance",
    "eligibility": r"eligibility|who can apply",
    "required_documents": r"documents? required|required documents?|documents? needed",
    "application_steps": r"how to apply|application (process|steps)|procedure",
    "deadlines": r"important dates?|deadlines?|last date",
}
DATE_RE = re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?[\s/-](?:[A-Za-z]{3,9}|\d{1,2})[\s/,-]*\d{2,4}\b")
LIST_KEYS = ("benefits", "eligibility", "required_documents", "deadlines", "application_steps", "official_links")


def _section(text: str, heading_rx: str) -> list[str]:
    lines, out, capture = text.splitlines(), [], False
    for ln in lines:
        s = ln.strip()
        if not capture:
            if re.fullmatch(rf"(?:{heading_rx})\s*:?", s, re.I):
                capture = True
            continue
        if not s:
            if out:
                break
            continue
        out.append(re.sub(r"^[-•*\d.)\s]+", "", s))
    return out


def _fallback(text: str) -> dict:
    res = {k: _section(text, HEADINGS[k]) for k in HEADINGS}
    if not res["deadlines"]:
        res["deadlines"] = DATE_RE.findall(text)[:5]
    first = [l.strip() for l in text.splitlines() if l.strip()]
    fee = [l for l in first if re.search(r"\b(fee|fees|charge|payment|free of cost)\b", l, re.I)]
    res.update(
        title=first[0] if first else "Untitled document",
        issuing_authority=next((l for l in first[:6] if re.search(r"ministry|department|government|board|commission", l, re.I)), "Not stated"),
        summary=" ".join(first[1:4])[:500] if len(first) > 1 else "",
        fees_or_payments=" ".join(fee[:2]) if fee else "No fee mentioned",
        official_links=re.findall(r"https?://[^\s,;)]+|\b[\w.-]+\.(?:gov|nic)\.in\b[^\s,;)]*", text),
        engine="rules")
    return res


def analyze_document(text: str, llm: LLMClient) -> dict:
    text = (text or "").strip()
    if not text:
        raise ValueError("No readable text found in the document.")
    clipped = text[: config.MAX_DOC_CHARS]
    try:
        data = llm.generate_json(document_prompt(clipped))
        if not isinstance(data, dict):
            raise ValueError("bad shape")
        for k in LIST_KEYS:
            v = data.get(k) or []
            data[k] = [str(x) for x in v] if isinstance(v, list) else [str(v)]
        data["engine"] = "gemma"
        return data
    except (LLMUnavailable, ValueError, TypeError):
        return _fallback(clipped)
