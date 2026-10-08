"""Thin wrapper around Google Gemma (Google AI Studio API, or local Ollama)."""
import requests

from . import config
from .json_utils import extract_json


class LLMUnavailable(Exception):
    """Raised when no LLM backend is configured/reachable. Callers fall back to rules."""


class LLMClient:
    def __init__(self, backend: str | None = None):
        self.backend = (backend or config.LLM_BACKEND).lower()
        self._client = None

    # ---- status -------------------------------------------------------
    @property
    def available(self) -> bool:
        if self.backend == "gemini_api":
            return bool(config.GOOGLE_API_KEY)
        return self.backend == "ollama"

    @property
    def label(self) -> str:
        if self.backend == "gemini_api" and config.GOOGLE_API_KEY:
            return f"Gemma via Google AI ({config.GEMMA_MODEL})"
        if self.backend == "ollama":
            return f"Gemma via Ollama ({config.OLLAMA_MODEL})"
        return "Offline rules engine (no LLM)"

    # ---- generation ---------------------------------------------------
    def generate(self, prompt: str) -> str:
        if self.backend == "gemini_api":
            return self._gemini(prompt)
        if self.backend == "ollama":
            return self._ollama(prompt)
        raise LLMUnavailable("LLM backend is offline")

    def generate_json(self, prompt: str):
        return extract_json(self.generate(prompt))

    def _gemini(self, prompt: str) -> str:
        if not config.GOOGLE_API_KEY:
            raise LLMUnavailable("GOOGLE_API_KEY not set")
        try:
            from google import genai
        except ImportError as e:
            raise LLMUnavailable("google-genai not installed") from e
        if self._client is None:
            self._client = genai.Client(api_key=config.GOOGLE_API_KEY)
        try:
            # Gemma models don't accept system instructions, so everything is in the prompt.
            resp = self._client.models.generate_content(model=config.GEMMA_MODEL, contents=prompt)
            return resp.text or ""
        except Exception as e:  # network, quota, auth ...
            raise LLMUnavailable(f"Gemma API error: {e}") from e

    def _ollama(self, prompt: str) -> str:
        try:
            r = requests.post(
                f"{config.OLLAMA_URL}/api/generate",
                json={"model": config.OLLAMA_MODEL, "prompt": prompt, "stream": False,
                      "options": {"temperature": 0.2}},
                timeout=180,
            )
            r.raise_for_status()
            return r.json().get("response", "")
        except Exception as e:
            raise LLMUnavailable(f"Ollama error: {e}") from e
