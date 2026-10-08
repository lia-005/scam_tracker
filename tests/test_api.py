import io, os, sys, tempfile
os.environ["LLM_BACKEND"] = "offline"
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import app as backend  # noqa: E402

client = backend.app.test_client()
ROOT = os.path.dirname(os.path.dirname(__file__))
DOC = open(os.path.join(ROOT, "sample_data", "official_scholarship_notice.txt"), encoding="utf-8").read()
SCAM = "Pay Rs 500 to activate your scholarship immediately at http://scholarship-india.xyz/pay or it will expire today."


def test_frontend_is_served():
    r = client.get("/")
    assert r.status_code == 200 and b"CivicShield AI" in r.data
    assert client.get("/script.js").status_code == 200
    assert client.get("/style.css").status_code == 200


def test_status():
    d = client.get("/api/status").get_json()
    assert d["ai_enabled"] is False and "Hindi" in d["languages"]


def test_analyze_message_high_risk():
    d = client.post("/api/analyze-message", json={"message": SCAM}).get_json()
    assert d["risk_level"] == "High" and d["risk_score"] >= 60 and d["safe_actions"]


def test_analyze_message_validation():
    r = client.post("/api/analyze-message", json={"message": "  "})
    assert r.status_code == 400 and "error" in r.get_json()


def test_extract_and_explain_document():
    r = client.post("/api/extract-text", data={"file": (io.BytesIO(DOC.encode()), "notice.txt")}, content_type="multipart/form-data")
    assert r.status_code == 200
    text = r.get_json()["text"]
    d = client.post("/api/explain-document", json={"text": text}).get_json()
    assert "Aadhaar card" in d["required_documents"]


def test_unsupported_file_type():
    r = client.post("/api/extract-text", data={"file": (io.BytesIO(b"x"), "a.exe")}, content_type="multipart/form-data")
    assert r.status_code == 400


def test_trustbridge_mismatch_and_history():
    d = client.post("/api/trustbridge", json={"message": SCAM, "doc_text": DOC}).get_json()
    assert d["trustbridge"]["verdict"] == "Possible Claim Mismatch"
    assert "Do NOT trust" in d["recommendation"]["headline"]
    assert len(client.get("/api/history").get_json()) >= 1
    assert client.delete("/api/history").get_json()["ok"] is True
    assert client.get("/api/history").get_json() == []


def test_trustbridge_requires_both_inputs():
    assert client.post("/api/trustbridge", json={"message": SCAM}).status_code == 400


def test_language_offline_keeps_english_and_flags_it():
    d = client.post("/api/analyze-message", json={"message": SCAM, "language": "Hindi"}).get_json()
    assert d["_translated"] is False and d["risk_level"] == "High"
