import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # dotenv is optional
    pass

LLM_BACKEND = os.getenv("LLM_BACKEND", "gemini_api").lower()   # gemini_api | ollama | offline
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma-3-27b-it")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:12b")
DB_PATH = os.getenv("DB_PATH", "civicshield.db")
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "")
MAX_DOC_CHARS = 12000          # text sent to the model
LANGUAGES = ["English", "Hindi", "Bengali"]

HELPLINE = "1930"
CYBER_PORTAL = "cybercrime.gov.in"
