"""Deterministic scam signals. Used to ground the LLM and as an offline fallback."""
import re
from urllib.parse import urlparse

# (id, label, regex, weight)
RULES = [
    ("otp_request", "Asks you to share OTP / PIN / CVV / password",
     r"(share|send|tell|give|enter|provide|forward).{0,40}(otp|pin|cvv|password|passcode)", 30),
    ("otp_mention", "Mentions OTP / verification code",
     r"\b(otp|one[- ]time password|verification code)\b", 5),
    ("payment_demand", "Demands a payment / fee",
     r"(pay|deposit|transfer|send|remit)\b.{0,40}(₹|rs\.?|inr|rupees?|fee|charge)"
     r"|(₹|rs\.?\s?|inr\s?)\d[\d,]*.{0,40}(fee|charge|activate|activation|processing|registration|release|claim|verification)", 25),
    ("urgency", "Creates urgency / time pressure",
     r"\b(urgent|immediately|within \d+ ?(hours?|hrs?|minutes?|mins?)|last chance|expires? (today|soon)|"
     r"final notice|act now|today only|blocked|suspended|deactivated)\b", 15),
    ("threat", "Threatens arrest / legal action / account closure",
     r"(arrest|legal action|police|court|\bfir\b|penalty|case (has been )?registered|account will be (blocked|closed))", 15),
    ("impersonation", "Claims to be a government body / bank / official scheme",
     r"\b(government of india|govt\.? of india|ministry|rbi|income tax|uidai|aadhaar|pan card|epfo|"
     r"pm[- ]?kisan|scholarship|npci|trai|cbi|customs|sbi|ration card)\b", 10),
    ("kyc_update", "Asks for KYC / Aadhaar / PAN update",
     r"\b(kyc|update (your )?(pan|aadhaar|kyc)|link (your )?aadhaar)\b", 15),
    ("prize", "Offers a prize, refund, cashback or lottery",
     r"(lottery|you (have )?won|prize|reward points|cashback|free gift|refund (is )?(pending|approved))", 20),
    ("credentials", "Asks for banking credentials",
     r"(upi pin|net ?banking|card number|expiry date|login details|bank details)", 20),
    ("remote_app", "Asks you to install an app / remote-access tool",
     r"(download|install).{0,30}(apk|app|anydesk|teamviewer|quicksupport)", 30),
    ("click_prompt", "Pushes you to click a link",
     r"(click|tap|open|visit).{0,20}(link|below|here)", 10),
]
_COMPILED = [(i, l, re.compile(p, re.I | re.S), w) for i, l, p, w in RULES]

URL_RE = re.compile(
    r"(?:https?://|www\.)[^\s<>\"']+"
    r"|\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:xyz|top|club|info|online|site|link|live|cc|icu|vip|shop|click)\b[^\s]*"
    r"|\b(?:bit\.ly|tinyurl\.com|t\.co|goo\.gl|cutt\.ly|rb\.gy|is\.gd)/[^\s]*", re.I)
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "cutt.ly", "rb.gy", "is.gd", "shorturl.at"}
SUSPICIOUS_TLDS = (".xyz", ".top", ".club", ".info", ".online", ".site", ".link", ".live", ".cc", ".icu", ".vip", ".shop", ".click")
OFFICIAL_SUFFIXES = (".gov.in", ".nic.in", ".gov", ".edu.in", ".ac.in")
BRAND_WORDS = ("gov", "india", "sbi", "scholar", "uidai", "aadhaar", "epfo", "kisan", "incometax", "rbi", "npci")
AMOUNT_RE = re.compile(r"(?:₹|rs\.?\s?|inr\s?)\s?(\d[\d,]*(?:\.\d+)?)", re.I)


def extract_urls(text: str) -> list[str]:
    return [u.rstrip(".,);]") for u in URL_RE.findall(text or "")]


def domain_of(url: str) -> str:
    u = url if "://" in url else "http://" + url
    return (urlparse(u).hostname or "").lower().removeprefix("www.")


def extract_amounts(text: str) -> list[str]:
    return [a.replace(",", "") for a in AMOUNT_RE.findall(text or "")]


def analyze_url(url: str) -> list[tuple[str, int]]:
    out, dom = [], domain_of(url)
    if dom in SHORTENERS:
        out.append((f"Shortened link hides the real destination ({dom})", 20))
    if dom.endswith(SUSPICIOUS_TLDS):
        out.append((f"Unusual domain extension: {dom}", 20))
    if url.lower().startswith("http://"):
        out.append((f"Link is not secure (http): {dom}", 10))
    if any(b in dom for b in BRAND_WORDS) and not dom.endswith(OFFICIAL_SUFFIXES):
        out.append((f"Looks like an official site but is not a .gov.in / .nic.in domain: {dom}", 25))
    return out


def risk_level(score: int) -> str:
    return "High" if score >= 60 else "Medium" if score >= 30 else "Low"


def scan(text: str) -> dict:
    """Return {'score': 0-100, 'signals': [labels], 'urls': [...], 'matched_ids': [...]}"""
    text = text or ""
    signals, ids, score = [], [], 0
    for rid, label, rx, weight in _COMPILED:
        if rx.search(text):
            signals.append(label)
            ids.append(rid)
            score += weight
    urls = extract_urls(text)
    for url in urls:
        for label, weight in analyze_url(url):
            signals.append(label)
            score += weight
    if "otp_request" in ids:  # avoid double counting the plain mention
        score -= 5
    return {"score": max(0, min(100, score)), "signals": signals, "urls": urls, "matched_ids": ids}
