import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from civicshield import scam_rules
from civicshield.database import Database
from civicshield.document_analyzer import analyze_document
from civicshield.json_utils import extract_json
from civicshield.llm import LLMClient
from civicshield.orchestrator import CivicShield
from civicshield.translator import translate_payload

OFFLINE = LLMClient(backend="offline")
DOC = open(os.path.join(os.path.dirname(__file__), "..", "sample_data", "official_scholarship_notice.txt"), encoding="utf-8").read()
SCAM = "Pay Rs 500 to activate your scholarship immediately at http://scholarship-india.xyz/pay or it will expire today."


def test_extract_json_variants():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! {"a": 2} hope that helps') == {"a": 2}
    assert extract_json('["x", "y"]') == ["x", "y"]


def test_scam_scores_high_and_safe_scores_low():
    assert scam_rules.scan(SCAM)["score"] >= 60
    safe = "Your application has been received. Track at https://scholarships.gov.in. No fee is required."
    assert scam_rules.scan(safe)["score"] < 30


def test_otp_kyc_message_is_high():
    s = scam_rules.scan("URGENT: SBI account will be blocked. Update KYC at bit.ly/x and share the OTP")
    assert s["score"] >= 60 and "otp_request" in s["matched_ids"]


def test_document_fallback_extracts_sections():
    d = analyze_document(DOC, OFFLINE)
    assert "Aadhaar card" in d["required_documents"]
    assert len(d["application_steps"]) == 4
    assert any("30 November 2026" in x for x in d["deadlines"])


def test_trustbridge_flags_fee_mismatch():
    with tempfile.TemporaryDirectory() as t:
        app = CivicShield(llm=OFFLINE, db=Database(os.path.join(t, "t.db")))
        r = app.trustbridge(SCAM, DOC)
        assert r["verdict"] == "Possible Claim Mismatch"
        assert any(m["severity"] == "High" for m in r["mismatches"])


def test_full_check_and_history():
    with tempfile.TemporaryDirectory() as t:
        app = CivicShield(llm=OFFLINE, db=Database(os.path.join(t, "t.db")))
        out = app.full_check(SCAM, DOC)
        assert out["scam"]["risk_level"] == "High"
        assert "Do NOT trust" in out["recommendation"]["headline"]
        assert len(app.db.recent()) == 1


def test_translation_degrades_gracefully_offline():
    payload = {"explanation": "Hello", "n": 3}
    out, ok = translate_payload(payload, "Hindi", OFFLINE)
    assert out == payload and ok is False
