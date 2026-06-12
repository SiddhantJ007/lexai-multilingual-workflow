import fitz  # PyMuPDF

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    parts: list[str] = []
    has_low_text_page = False

    for page in doc:
        txt = page.get_text().strip()
        if len("".join(txt.split())) < 20:
            has_low_text_page = True
        parts.append(txt)

    full_text = "\n\n".join(parts).strip()
    if not full_text:
        raise ValueError(
            "This PDF appears to require OCR. OCR is not enabled in the Phase 1 Vercel deployment yet."
        )
    if has_low_text_page:
        raise ValueError(
            "This PDF contains scanned or image-based pages. Text-based PDFs are supported in Phase 1; OCR will require external vision/OCR integration later."
        )

    return full_text[:30_000]
