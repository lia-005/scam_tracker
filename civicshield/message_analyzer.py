from . import config, scam_rules
from .llm import LLMClient, LLMUnavailable
from .prompts import message_prompt


def _safe_actions(level: str) -> list[str]:
    base = ["Do not click any link or call any number in the message.",
            "Never share OTP, UPI PIN, card details or passwords with anyone - real officials never ask.",
            "Verify on the official website (.gov.in / .nic.in) that you typed yourself, or visit the office."]
    if level in ("High", "Medium"):
        base += [f"Report it: call {config.HELPLINE} or visit {config.CYBER_PORTAL}.",
                 "If you already paid or shared details, call your bank immediately and report within hours."]
    else:
        base += ["If anything still feels wrong, confirm through the official helpline before acting."]
    return base


def _to_list(v):
    if v is None:
        return []
    return [str(x) for x in v] if isinstance(v, list) else [str(v)]


def analyze_message(message: str, llm: LLMClient) -> dict:
    scan = scam_rules.scan(message)
    result = {
        "risk_score": scan["score"],
        "risk_level": scam_rules.risk_level(scan["score"]),
        "scam_type": "Suspicious message" if scan["score"] >= 30 else "No strong scam pattern",
        "red_flags": scan["signals"],
        "explanation": ("Detected by rule-based checks only. " if not llm.available else "") +
                       (f"This message shows {len(scan['signals'])} warning sign(s) commonly seen in scams."
                        if scan["signals"] else "No common scam warning signs were found."),
        "safe_actions": [],
        "engine": "rules",
        "rule_score": scan["score"],
    }
    try:
        data = llm.generate_json(message_prompt(message, scan["signals"]))
        llm_score = max(0, min(100, int(float(data.get("risk_score", scan["score"])))))
        # Blend the model with deterministic rules; never let a loud rule signal get diluted below itself by much.
        score = round(0.6 * llm_score + 0.4 * scan["score"])
        if scan["score"] >= 60:
            score = max(score, 60)
        flags = list(dict.fromkeys(_to_list(data.get("red_flags")) + scan["signals"]))
        result.update(
            risk_score=score, risk_level=scam_rules.risk_level(score),
            scam_type=str(data.get("scam_type") or result["scam_type"]),
            red_flags=flags, explanation=str(data.get("explanation") or result["explanation"]),
            safe_actions=_to_list(data.get("safe_actions")), engine="gemma", llm_score=llm_score)
    except (LLMUnavailable, ValueError, TypeError):
        pass
    if not result["safe_actions"]:
        result["safe_actions"] = _safe_actions(result["risk_level"])
    return result
