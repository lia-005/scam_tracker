import json

_CONTEXT = ("You are CivicShield AI, a citizen-safety assistant focused on India. "
            "Be accurate, calm and use simple language a non-technical citizen can follow. "
            "Reply with ONLY one valid JSON object. No markdown, no commentary.")


def message_prompt(message: str, rule_signals: list[str]) -> str:
    schema = {
        "risk_score": "integer 0-100 (0 = clearly safe, 100 = certainly a scam)",
        "scam_type": "short label e.g. 'Fake scholarship fee', 'Phishing', 'OTP fraud', 'KYC fraud', 'Legitimate/None'",
        "red_flags": ["each suspicious element found, plain language"],
        "explanation": "2-4 sentences: WHY this is or is not risky",
        "safe_actions": ["3-5 concrete things the citizen should do next"],
    }
    return (f"{_CONTEXT}\n\nTASK: Assess whether the message below is a scam, phishing or impersonation attempt. "
            "Look for: phishing, fake government messages, OTP/PIN requests, payment requests, suspicious links, "
            "urgency/threats, impersonation.\n"
            f"Automated pre-scan signals (may be incomplete): {json.dumps(rule_signals, ensure_ascii=False)}\n\n"
            f"JSON schema:\n{json.dumps(schema, indent=2)}\n\nMESSAGE:\n\"\"\"\n{message}\n\"\"\"")


def document_prompt(text: str) -> str:
    schema = {
        "title": "name of the scheme/notice",
        "issuing_authority": "department/ministry or 'Not stated'",
        "summary": "3-5 simple sentences",
        "benefits": ["..."],
        "eligibility": ["..."],
        "required_documents": ["..."],
        "deadlines": ["date + what it is for"],
        "application_steps": ["ordered steps"],
        "fees_or_payments": "what the document says about fees/payments; say 'No fee mentioned' if absent",
        "official_links": ["URLs/portals named in the document"],
    }
    return (f"{_CONTEXT}\n\nTASK: Read this government document and extract structured information. "
            "Use ONLY facts in the document; use an empty list or 'Not stated' when missing. Never invent.\n\n"
            f"JSON schema:\n{json.dumps(schema, indent=2)}\n\nDOCUMENT:\n\"\"\"\n{text}\n\"\"\"")


def trustbridge_prompt(message: str, doc_text: str) -> str:
    schema = {
        "verdict": "one of: 'Consistent', 'Possible Claim Mismatch', 'Cannot Verify'",
        "mismatches": [{"claim": "what the message claims", "official_says": "what the document says (or 'Not mentioned')",
                        "severity": "High | Medium | Low"}],
        "confirmed_claims": ["claims in the message that the document supports"],
        "explanation": "2-4 simple sentences",
        "recommendation": "the single most important safe next step",
    }
    return (f"{_CONTEXT}\n\nTASK (TrustBridge): Compare the MESSAGE a citizen received with the OFFICIAL DOCUMENT. "
            "Check amounts/fees, payment requests, deadlines, eligibility, links/portals and procedures. "
            "A message demanding payment when the document says the service is free, or a link that is not in the "
            "document, is a High severity mismatch. Only use facts from the document.\n\n"
            f"JSON schema:\n{json.dumps(schema, indent=2)}\n\nMESSAGE:\n\"\"\"\n{message}\n\"\"\"\n\n"
            f"OFFICIAL DOCUMENT:\n\"\"\"\n{doc_text}\n\"\"\"")


def translate_prompt(strings: list[str], language: str) -> str:
    return (f"Translate each string in the JSON array below into {language}. Keep the same order and the same number "
            "of items. Keep numbers, URLs, phone numbers and names of portals unchanged. Use simple, everyday words. "
            f"Reply with ONLY a JSON array of strings.\n\n{json.dumps(strings, ensure_ascii=False)}")
