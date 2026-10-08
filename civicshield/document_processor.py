"""Text extraction from PDFs / images / txt, with Tesseract OCR fallback."""
import io

from . import config

OCR_LANGS = "eng+hin+ben"


def _ocr_image(img) -> str:
    import pytesseract
    if config.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
    try:
        return pytesseract.image_to_string(img, lang=OCR_LANGS)
    except pytesseract.TesseractError:      # language packs missing -> English only
        return pytesseract.image_to_string(img, lang="eng")


def extract_text(data: bytes, filename: str) -> str:
    name = (filename or "").lower()
    if name.endswith((".txt", ".md")):
        return data.decode("utf-8", errors="ignore")
    if name.endswith(".pdf"):
        return _pdf_text(data)
    if name.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff")):
        from PIL import Image
        return _ocr_image(Image.open(io.BytesIO(data)))
    raise ValueError(f"Unsupported file type: {filename}")


def _pdf_text(data: bytes) -> str:
    import fitz  # PyMuPDF
    from PIL import Image
    parts = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            text = page.get_text().strip()
            if len(text) < 40:               # scanned page -> OCR
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                try:
                    text = _ocr_image(img).strip()
                except Exception:
                    pass
            parts.append(text)
    return "\n\n".join(p for p in parts if p).strip()
