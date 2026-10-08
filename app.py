"""CivicShield AI - Flask backend. Serves the HTML/CSS/JS frontend and a JSON REST API.

Run:  python app.py   ->  http://localhost:5000
"""
import os

from flask import Flask, jsonify, request, send_from_directory

from civicshield import config
from civicshield.llm import LLMClient
from civicshield.orchestrator import CivicShield
from civicshield.translator import translate_payload

FRONTEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")

app = Flask(__name__, static_folder=FRONTEND, static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024  # 15 MB uploads

engine = CivicShield(llm=LLMClient())


# ---------------------------------------------------------------- helpers
def body() -> dict:
    return request.get_json(silent=True) or {}


def localized(result: dict, language: str) -> dict:
    """Translate a result dict if a non-English language was requested."""
    if language and language != "English":
        result, ok = translate_payload(result, language, engine.llm)
        result["_translated"] = ok
    return result


def fail(message: str, code: int = 400):
    return jsonify({"error": message}), code


# ---------------------------------------------------------------- pages
@app.get("/")
def index():
    return send_from_directory(FRONTEND, "index.html")


# ---------------------------------------------------------------- API
@app.get("/api/status")
def status():
    return jsonify({"engine": engine.llm.label, "ai_enabled": engine.llm.available,
                    "languages": config.LANGUAGES, "helpline": config.HELPLINE,
                    "portal": config.CYBER_PORTAL})


@app.post("/api/analyze-message")
def analyze_message():
    data = body()
    try:
        res = engine.check_message(data.get("message", ""))
    except ValueError as e:
        return fail(str(e))
    return jsonify(localized(res, data.get("language", "English")))


@app.post("/api/extract-text")
def extract_text():
    f = request.files.get("file")
    if not f or not f.filename:
        return fail("Please choose a file.")
    try:
        text = engine.read_file(f.read(), f.filename)
    except ValueError as e:
        return fail(str(e))
    except Exception as e:  # corrupt file, tesseract missing ...
        return fail(f"Could not read the file: {e}", 422)
    if not text.strip():
        return fail("No readable text found. If this is a scan, install Tesseract OCR.", 422)
    return jsonify({"filename": f.filename, "text": text, "chars": len(text)})


@app.post("/api/explain-document")
def explain_document():
    data = body()
    try:
        res = engine.explain_document(data.get("text", ""))
    except ValueError as e:
        return fail(str(e))
    return jsonify(localized(res, data.get("language", "English")))


@app.post("/api/trustbridge")
def trustbridge():
    data = body()
    message, doc_text = data.get("message", ""), data.get("doc_text", "")
    if not message.strip() or not doc_text.strip():
        return fail("Both a message and an official document are required.")
    out = engine.full_check(message, doc_text)
    return jsonify(localized(out, data.get("language", "English")))


@app.get("/api/history")
def history():
    return jsonify(engine.db.recent())


@app.delete("/api/history")
def clear_history():
    engine.db.clear()
    return jsonify({"ok": True})


@app.errorhandler(413)
def too_large(_):
    return fail("File is too large (max 15 MB).", 413)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", 5000)), debug=True)
