"""CivicShield Orchestrator: routes inputs to analyzers, TrustBridge, and builds the safe recommendation."""
from . import config, scam_rules
from .database import Database
from .document_analyzer import analyze_document
from .document_processor import extract_text
from .llm import LLMClient
from .message_analyzer import analyze_message
from .trustbridge import verify_claim


class CivicShield:
    def __init__(self, llm: LLMClient | None = None, db: Database | None = None):
        self.llm = llm or LLMClient()
        self.db = db or Database()

    # --- individual features -------------------------------------------
    def check_message(self, message: str, save: bool = True) -> dict:
        if not message.strip():
            raise ValueError("Please paste a message to analyze.")
        res = analyze_message(message, self.llm)
        if save:
            self.db.save("scam_check", message, res, risk_score=res["risk_score"])
        return res

    def read_file(self, data: bytes, filename: str) -> str:
        return extract_text(data, filename)

    def explain_document(self, text: str, save: bool = True) -> dict:
        res = analyze_document(text, self.llm)
        if save:
            self.db.save("document", res.get("title", "document"), res)
        return res

    def trustbridge(self, message: str, doc_text: str, save: bool = True) -> dict:
        res = verify_claim(message, doc_text, self.llm)
        if save:
            self.db.save("trustbridge", message, res, verdict=res["verdict"])
        return res

    # --- full pipeline ---------------------------------------------------
    def full_check(self, message: str, doc_text: str | None = None) -> dict:
        scam = self.check_message(message, save=False)
        out = {"scam": scam}
        if doc_text and doc_text.strip():
            out["document"] = self.explain_document(doc_text, save=False)
            out["trustbridge"] = self.trustbridge(message, doc_text, save=False)
            if out["trustbridge"]["verdict"] == "Possible Claim Mismatch":
                bump = 20 if any(m.get("severity") == "High" for m in out["trustbridge"]["mismatches"]) else 10
                scam["risk_score"] = min(100, scam["risk_score"] + bump)
                scam["risk_level"] = scam_rules.risk_level(scam["risk_score"])
        out["recommendation"] = self.recommendation(out)
        self.db.save("full_check", message, out, risk_score=scam["risk_score"],
                     verdict=out.get("trustbridge", {}).get("verdict"))
        return out

    @staticmethod
    def recommendation(out: dict) -> dict:
        scam, tb = out["scam"], out.get("trustbridge")
        level = scam["risk_level"]
        mismatch = bool(tb and tb["verdict"] == "Possible Claim Mismatch")
        if level == "High" or mismatch:
            headline = "Do NOT trust this message. Do not pay, click or reply."
        elif level == "Medium":
            headline = "Be careful. Verify through an official channel before acting."
        else:
            headline = "Looks low-risk, but still verify before sharing personal details."
        steps = list(scam["safe_actions"])
        if tb:
            steps.insert(0, tb["recommendation"])
        return {"headline": headline, "steps": list(dict.fromkeys(steps)),
                "report_to": f"Cyber crime helpline {config.HELPLINE} | {config.CYBER_PORTAL}"}
