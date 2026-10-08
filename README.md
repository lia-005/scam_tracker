# 🛡️ CivicShield AI — HTML / CSS / JavaScript + Python API

Simple architecture: a plain **HTML/CSS/JS frontend** (no build step) talking to a **Flask REST API**, which uses **Google Gemma** for the AI.

```
Browser (index.html + style.css + script.js)
        │  fetch() JSON
        ▼
Flask API (app.py)  ──►  CivicShield Orchestrator ──► Message Analyzer / Document Analyzer ──► Gemma ──► TrustBridge ──► Safe Recommendation
```

## Run it (3 steps)
```bash
pip install -r requirements.txt
copy .env.example .env        # Mac/Linux: cp .env.example .env   -> then put your GOOGLE_API_KEY inside
python app.py
```
Open **http://localhost:5000**

No API key? Set `LLM_BACKEND=offline` in `.env` — scam rules and TrustBridge fee/link checks still work.
Free key: https://aistudio.google.com/apikey

## Project structure
```
app.py                    Flask backend + REST API (serves the frontend too)
frontend/
  index.html              page structure
  style.css               styling
  script.js               UI logic, calls the API, renders results, Hindi/Bengali labels
civicshield/              AI engine (Python)
  orchestrator.py  message_analyzer.py  document_analyzer.py  trustbridge.py
  scam_rules.py  document_processor.py (PDF + OCR)  translator.py  llm.py  prompts.py  database.py
sample_data/              demo notice + scam messages
tests/                    16 tests (run offline)
```

## REST API
| Method | Endpoint | Body | Returns |
|---|---|---|---|
| GET | `/api/status` | – | engine info, languages, helpline |
| POST | `/api/analyze-message` | `{message, language}` | risk score, level, red flags, explanation, safe actions |
| POST | `/api/extract-text` | multipart `file` (pdf/png/jpg/txt) | `{filename, text}` |
| POST | `/api/explain-document` | `{text, language}` | summary, benefits, eligibility, documents, deadlines, steps, fees |
| POST | `/api/trustbridge` | `{message, doc_text, language}` | `{scam, document, trustbridge, recommendation}` |
| GET / DELETE | `/api/history` | – | recent analyses / clear them |

`language` is `English`, `Hindi` or `Bengali`.

Quick test with curl:
```bash
curl -X POST http://localhost:5000/api/analyze-message -H "Content-Type: application/json" \
     -d "{\"message\": \"Pay Rs 500 to activate your scholarship at http://abc.xyz\"}"
```

## OCR (scanned PDFs / photos)
Install Tesseract: Windows installer https://github.com/UB-Mannheim/tesseract/wiki (then set `TESSERACT_CMD` in `.env`), Mac `brew install tesseract tesseract-lang`, Ubuntu `sudo apt install tesseract-ocr tesseract-ocr-hin tesseract-ocr-ben`.

## Demo (TrustBridge)
1. Open **TrustBridge** → click **Try an example** → **Verify with TrustBridge**.
2. Result: **Possible Claim Mismatch** (the official notice says no fee, and never names that website).

## Tests
```bash
python -m pytest tests
```

## Deploy
Render / Railway / Cloud Run: use the included `Dockerfile` (gunicorn), set `GOOGLE_API_KEY` as an environment variable.
Change `app.run(... debug=True)` is only used locally; in production gunicorn runs `app:app`.

## Notes
- Decision support only. Always verify on official `.gov.in` / `.nic.in` sites.
- All user/AI text is HTML-escaped in the frontend (no XSS).
- Set `GEMMA_MODEL` in `.env` if your key uses a different Gemma model.
