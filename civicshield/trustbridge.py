"""TrustBridge: compare a suspicious claim/message with an official document."""
import re

from . import config, scam_rules
from .llm import LLMClient, LLMUnavailable
from .prompts import trustbridge_prompt

NO_FEE_RX = re.compile(r"(no (fee|fees|charge|charges|payment)|free of (cost|charge)|without (any )?(fee|payment|charge)|"
                       r"not (charge|ask)|never (ask|charge|demand))", re.I)
FEE_RX = re.compile(r"\b(fee|fees|charge|charges|payable|deposit)\b", re.I)


def _rule_check(message: str, doc: str) -> dict:
    mismatches, confirmed = [], []
    scan = scam_rules.scan(message)
    doc_l = doc.lower()
    msg_pays = "payment_demand" in scan["matched_ids"] or bool(scam_rules.extract_amounts(message))
    doc_no_fee = bool(NO_FEE_RX.search(doc))
    doc_has_fee = bool(FEE_RX.search(doc)) and not doc_no_fee

    if msg_pays:
        amts = ", ".join("₹" + a for a in scam_rules.extract_amounts(message)) or "a payment"
        if doc_no_fee:
            mismatches.append({"claim": f"Message demands {amts}", "official_says": "The document states no fee/payment is required.", "severity": "High"})
        elif not doc_has_fee:
            mismatches.append({"claim": f"Message demands {amts}", "official_says": "Not mentioned - the document does not ask for any payment.", "severity": "High"})
        else:
            for a in scam_rules.extract_amounts(message):
                (confirmed if a in doc.replace(",", "") else mismatches).append(
                    f"Amount ₹{a} appears in the document" if a in doc.replace(",", "") else
                    {"claim": f"Fee of ₹{a}", "official_says": "This amount is not in the document.", "severity": "Medium"})

    doc_domains = {scam_rules.domain_of(u) for u in scam_rules.extract_urls(doc)}
    for url in scan["urls"]:
        dom = scam_rules.domain_of(url)
        if dom and dom not in doc_l and dom not in doc_domains:
            mismatches.append({"claim": f"Message links to {dom}", "official_says": "This website is not named in the official document.", "severity": "High" if scam_rules.analyze_url(url) else "Medium"})

    if "otp_request" in scan["matched_ids"]:
        mismatches.append({"claim": "Message asks you to share an OTP/PIN/password", "official_says": "Official documents never require sharing OTPs or PINs.", "severity": "High"})

    if not msg_pays and not scan["urls"] and not mismatches:
        verdict = "Cannot Verify"
    else:
        verdict = "Possible Claim Mismatch" if mismatches else "Consistent"
    return {
        "verdict": verdict, "mismatches": mismatches, "confirmed_claims": [c for c in confirmed if isinstance(c, str)],
        "explanation": ("The message makes claims that the official document does not support." if mismatches else
                        "No contradictions were found, but the document may not cover everything in the message." if verdict == "Consistent" else
                        "The message has no checkable claims (amounts, links) to compare against the document."),
        "recommendation": ("Do not pay or click. Check the official portal named in the document or contact the issuing office." if mismatches
                           else "Proceed carefully and confirm through the official website."),
        "engine": "rules",
    }


def verify_claim(message: str, doc_text: str, llm: LLMClient) -> dict:
    if not (message or "").strip() or not (doc_text or "").strip():
        raise ValueError("Both a message and an official document are required.")
    doc_text = doc_text[: config.MAX_DOC_CHARS]
    baseline = _rule_check(message, doc_text)
    try:
        data = llm.generate_json(trustbridge_prompt(message, doc_text))
        mism = [m for m in data.get("mismatches", []) if isinstance(m, dict)]
        # merge: deterministic mismatches are kept so a weak model can't hide a fee/link contradiction
        seen = {m.get("claim", "").lower() for m in mism}
        mism += [m for m in baseline["mismatches"] if m["claim"].lower() not in seen]
        verdict = str(data.get("verdict", baseline["verdict"]))
        if mism and verdict != "Possible Claim Mismatch":
            verdict = "Possible Claim Mismatch"
        return {"verdict": verdict, "mismatches": mism,
                "confirmed_claims": [str(c) for c in data.get("confirmed_claims", [])],
                "explanation": str(data.get("explanation", baseline["explanation"])),
                "recommendation": str(data.get("recommendation", baseline["recommendation"])), "engine": "gemma"}
    except (LLMUnavailable, ValueError, TypeError, AttributeError):
        return baseline
