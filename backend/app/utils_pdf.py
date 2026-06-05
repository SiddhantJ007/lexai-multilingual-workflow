import io
import fitz                # PyMuPDF
from PIL import Image
import pytesseract

def _ocr_page(page) -> str:
    pix = page.get_pixmap(dpi=300)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    return pytesseract.image_to_string(img, lang="eng")

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    parts: list[str] = []

    for page in doc:
        txt = page.get_text().strip()

        # if < 20 printable chars we assume it's a scanned page
        if len(''.join(txt.split())) < 20:
            txt = _ocr_page(page)

        parts.append(txt)

    # join pages with two newlines to keep separation
    full_text = "\n\n".join(parts).strip()

    # optional hard cap (DeepL free tier ≈ 30 k chars)
    return full_text[:30_000]
