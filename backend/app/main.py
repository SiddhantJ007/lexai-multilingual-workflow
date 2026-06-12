from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

import io
import os
import re
from datetime import datetime
from typing import Final, Literal
from zoneinfo import ZoneInfo

import requests
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, Response
from openai import OpenAI
from openpyxl import Workbook
from pydantic import BaseModel, Field

from .api_emails import router as emails_router
from . import db as feedback_db
from .utils import critique_allowed
from .utils_pdf import extract_text_from_pdf

MAX_UPLOAD_SIZE: Final = 4_000_000
ANON_QUOTA_DAY: Final = int(os.getenv("ANON_QUOTA_DAY", "10000"))
ET_ZONE: Final = ZoneInfo("America/New_York")

LANGUAGE_NAMES = {
    "AR": "Arabic",
    "BG": "Bulgarian",
    "ZH": "Chinese",
    "CS": "Czech",
    "DA": "Danish",
    "NL": "Dutch",
    "EN": "English",
    "ET": "Estonian",
    "FI": "Finnish",
    "FR": "French",
    "DE": "German",
    "EL": "Greek",
    "HU": "Hungarian",
    "ID": "Indonesian",
    "IT": "Italian",
    "JA": "Japanese",
    "KO": "Korean",
    "LV": "Latvian",
    "LT": "Lithuanian",
    "NB": "Norwegian (Bokmal)",
    "PL": "Polish",
    "PT": "Portuguese",
    "RO": "Romanian",
    "RU": "Russian",
    "SK": "Slovak",
    "SL": "Slovenian",
    "ES": "Spanish",
    "SV": "Swedish",
    "TR": "Turkish",
    "UK": "Ukrainian",
}

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
ALLOWED_MODELS = {
    model.strip()
    for model in os.getenv("ALLOWED_MODELS", "gpt-4.1-mini,gpt-4o-mini,gpt-4o").split(",")
    if model.strip()
}

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "test-key"))
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "").strip()
DEEPL_API_URL = os.getenv("DEEPL_API_URL", "https://api-free.deepl.com/v2/translate").strip()

app = FastAPI(title="LexAi Portfolio API")


def allowed_origins() -> list[str]:
    origins = {
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    }

    single = os.getenv("FRONTEND_ORIGIN", "").strip()
    if single:
        origins.add(single)

    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    for item in raw.split(","):
        value = item.strip()
        if value:
            origins.add(value)
    return sorted(origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(emails_router)


class FullProcessRequest(BaseModel):
    prompt: str = Field(min_length=1)
    target_language: str = Field(min_length=2, max_length=5)
    model: str | None = None


class RephraseRequest(BaseModel):
    prompt: str = Field(min_length=1)
    keep_length: bool = True
    model: str | None = None


class FeedbackRequest(BaseModel):
    original_prompt: str = Field(min_length=1)
    translated_text: str = Field(min_length=1)
    target_language: str = Field(min_length=2, max_length=32)
    feedback: str = Field(min_length=2, max_length=64)


class VariantsRequest(BaseModel):
    prompt: str = Field(min_length=1)
    target_language: str = Field(min_length=2, max_length=5)
    model: str | None = None


class VariantFeedbackRequest(BaseModel):
    original_prompt: str = Field(min_length=1)
    target_language: str = Field(min_length=2, max_length=32)
    variant_text: str = Field(min_length=1)
    rating: Literal["Good", "Bad"]


class RegenRequest(BaseModel):
    original_prompt: str = Field(min_length=1)
    translated_text: str = Field(min_length=1)
    target_language: str = Field(min_length=2, max_length=5)
    reason: str = Field(min_length=5, max_length=250)
    model: str | None = None


def chosen_model(value: str | None) -> str:
    model = (value or DEFAULT_MODEL).strip()
    if model not in ALLOWED_MODELS:
        raise HTTPException(400, f"Model not allowed: {model}")
    return model


def language_name(code: str) -> str:
    return LANGUAGE_NAMES.get(code.upper(), code.upper())


def today_et():
    return datetime.now(ET_ZONE).date()


def deepl_candidate_urls() -> list[str]:
    configured = DEEPL_API_URL or "https://api-free.deepl.com/v2/translate"
    free_url = "https://api-free.deepl.com/v2/translate"
    paid_url = "https://api.deepl.com/v2/translate"

    candidates: list[str] = []
    for url in [configured]:
        if url and url not in candidates:
            candidates.append(url)

    prefers_free = ":fx" in DEEPL_API_KEY
    fallback_order = [free_url, paid_url] if prefers_free else [paid_url, free_url]
    for url in fallback_order:
        if url not in candidates:
            candidates.append(url)
    return candidates


def short_http_error(response: requests.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            message = payload.get("message") or payload.get("detail")
            if message:
                return str(message)[:160]
    except ValueError:
        pass
    return f"HTTP {response.status_code}"


def translate_with_deepl(text: str, target_language: str) -> str:
    if not DEEPL_API_KEY:
        raise HTTPException(503, "DeepL is not configured on the backend.")

    errors: list[str] = []
    for url in deepl_candidate_urls():
        try:
            response = requests.post(
                url,
                headers={"Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}"},
                data={
                    "text": text,
                    "target_lang": target_language.upper(),
                    "formality": "prefer_less",
                },
                timeout=20,
            )
        except requests.RequestException as exc:
            errors.append(f"{url}: {exc.__class__.__name__}")
            continue

        if not response.ok:
            errors.append(f"{url}: {short_http_error(response)}")
            continue

        try:
            payload = response.json()
        except ValueError:
            errors.append(f"{url}: invalid JSON")
            continue

        translations = payload.get("translations") or []
        if translations and translations[0].get("text"):
            return str(translations[0]["text"]).strip()
        errors.append(f"{url}: no translations returned")

    detail = errors[0] if errors else "translation service unavailable"
    if any("HTTP 403" in item or "Authorization failed" in item for item in errors):
        detail = (
            "DeepL rejected the request. Check whether the deployed key matches "
            "the correct DeepL API endpoint (Free vs Pro) in Vercel env vars."
        )
    raise HTTPException(502, f"DeepL request failed: {detail}")


def translate_with_openai(text: str, target_language: str, model: str) -> str:
    target_name = language_name(target_language)
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "You translate short-form content accurately and naturally. "
                    "Preserve meaning, numbers, brand tokens, and line breaks."
                ),
            },
            {
                "role": "user",
                "content": f"Translate this into {target_name}:\n\n{text}",
            },
        ],
    )
    return response.output_text.strip()


def improve_prompt(prompt: str, model: str) -> str:
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "Rewrite short marketing or product copy to read cleaner and more deliberate. "
                    "Preserve factual meaning. Return only the improved English text."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )
    return response.output_text.strip()


def improve_for_translation(prompt: str, model: str) -> str:
    source_length = len(prompt)
    tolerance = max(5, int(source_length * 0.05))
    matches = re.findall(
        r"\$?\d[\d,]*(?:\.\d+)?%?|[A-Z][A-Za-z0-9&@\-\']*(?:\s+[A-Z][A-Za-z0-9&@\-\']*)*",
        prompt,
    )
    locks = ", ".join(sorted(set(matches))[:15])
    system = (
        "You refine short marketing or product copy before translation. "
        "Keep meaning identical. Preserve names, numerals, dates, prices, promo codes, and claims."
    )
    user = (
        f"ORIGINAL ({source_length} chars):\n{prompt}\n\n"
        f"DO NOT CHANGE verbatim: {locks or 'none'}\n\n"
        f"Constraints:\n"
        f"- Final length within plus or minus {tolerance} characters.\n"
        "- No new claims, no deletions.\n"
        "- Return exactly one improved English paragraph."
    )
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    improved = response.output_text.strip()
    if abs(len(improved) - source_length) > tolerance:
        return prompt
    return improved


def qa_translation(source_english: str, translated_text: str, target_language: str, model: str) -> str:
    target_name = language_name(target_language)
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "You are a bilingual QA checker. Compare the English source and target text. "
                    "Reply exactly OK if the target is faithful, otherwise reply exactly: FIX: <short reason>."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"SOURCE (English):\n{source_english}\n\n"
                    f"TARGET ({target_name}):\n{translated_text}"
                ),
            },
        ],
    )
    verdict = response.output_text.strip()
    if not verdict.startswith("FIX:"):
        return translated_text

    fix_response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "Correct the translation so it faithfully matches the English source. "
                    "Return only the corrected translation."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Reason:\n{verdict}\n\n"
                    f"English source:\n{source_english}\n\n"
                    f"Current target text:\n{translated_text}\n\n"
                    f"Target language: {target_name}"
                ),
            },
        ],
    )
    return fix_response.output_text.strip()


def normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def rewrite_from_critique(
    original_prompt: str,
    translated_text: str,
    reason: str,
    model: str,
    *,
    force_distinct: bool = False,
) -> str:
    distinct_clause = (
        "The revised English must be materially different in wording and sentence structure from the original. "
        "Avoid reusing the same opening phrase or the same key adjective-verb pair. "
        if force_distinct
        else ""
    )
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "You improve the English source based on critique while preserving the original meaning exactly. "
                    "The critique is guidance about tone, local resonance, clarity, or persuasion. "
                    "It is not new source material and must not replace the original concept, image, promise, or call to action. "
                    "Do not swap the core noun, core verb, or central metaphor unless the critique explicitly asks for that exact change. "
                    "Keep the revised line back-translatable to the same meaning as the original. "
                    f"{distinct_clause}"
                    "Apply the critique concretely, but with minimal semantic drift. "
                    "Prefer a focused edit over a full reinterpretation. Return only the improved English text."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Original source:\n{original_prompt}\n\n"
                    f"Current output:\n{translated_text}\n\n"
                    f"Critique:\n{reason}\n\n"
                    "Rules:\n"
                    "- Preserve the same meaning as the original source.\n"
                    "- Treat the critique as optimization guidance only.\n"
                    "- Do not translate or paraphrase the critique itself into the output.\n"
                    "- If the critique is vague, make one small but concrete improvement without changing the concept.\n"
                    "- Keep the output concise and suitable for the same target translation task."
                ),
            },
        ],
    )
    return response.output_text.strip()


def generate_variants(prompt: str, target_language: str, model: str) -> list[str]:
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "Generate five distinct short-form alternatives that keep the same core meaning. "
                    "Return a JSON array of strings only."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )
    raw = response.output_text.strip()
    clean = re.sub(r"^```json|```$", "", raw, flags=re.M).strip()
    try:
        import json

        variants_en = json.loads(clean)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(502, f"Could not parse variant output: {exc}") from exc

    if not isinstance(variants_en, list) or not variants_en:
        raise HTTPException(502, "No variants returned")

    translated = []
    for item in variants_en[:5]:
        line = str(item).strip()
        if not line:
            continue
        translated.append(translate_text(line, target_language, model))
    return translated


def translate_text(text: str, target_language: str, model: str) -> str:
    if target_language.upper() == "EN":
        return text
    return translate_with_deepl(text, target_language).strip()


def update_usage(session_id: str, chars: int) -> None:
    try:
        current = feedback_db.get_session_usage(session_id, today_et())
        if current + chars > ANON_QUOTA_DAY:
            raise HTTPException(429, f"Daily quota exceeded ({ANON_QUOTA_DAY:,} characters)")
        feedback_db.increment_session_usage(session_id, today_et(), chars)
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, f"Feedback storage is unavailable: {feedback_db.safe_error_message(exc)}") from exc


def save_feedback_row(session_id: str, original_prompt: str, translated_text: str, target_language: str, feedback: str) -> None:
    try:
        feedback_db.insert_feedback(
            session_id,
            original_prompt,
            translated_text,
            target_language.upper(),
            feedback,
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, f"Feedback storage is unavailable: {feedback_db.safe_error_message(exc)}") from exc


@app.on_event("startup")
def startup() -> None:
    if feedback_db.is_configured():
        try:
            feedback_db.ensure_schema()
        except Exception as exc:
            print(f"Warning: feedback schema initialization skipped: {feedback_db.safe_error_message(exc)}")


@app.get("/")
def home() -> dict[str, str]:
    return {"message": "LexAi portfolio backend running"}


@app.get("/ping")
def ping() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/healthz")
def healthz() -> dict[str, bool | str | None]:
    db_configured = feedback_db.is_configured()
    db_ok, db_error = feedback_db.check()
    payload: dict[str, bool | str | None] = {
        "ok": True,
        "database_configured": db_configured,
        "database_ok": db_ok,
    }
    if db_error:
        payload["database_error"] = db_error
    return payload


@app.get("/health")
def health() -> dict[str, bool | str | None]:
    return healthz()


@app.get("/quota")
def quota(session_id: str = Header(..., alias="X-Lex-Session")) -> dict[str, int | str]:
    try:
        used = feedback_db.get_session_usage(session_id, today_et())
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, f"Feedback storage is unavailable: {feedback_db.safe_error_message(exc)}") from exc
    return {"limit": ANON_QUOTA_DAY, "used": used, "day": today_et().isoformat()}


@app.post("/full-process/")
def full_process(req: FullProcessRequest, session_id: str = Header(..., alias="X-Lex-Session")) -> dict[str, str]:
    model = chosen_model(req.model)
    improved = improve_for_translation(req.prompt.strip(), model)
    translated = translate_text(improved, req.target_language, model)
    translated = qa_translation(improved, translated, req.target_language, model)
    update_usage(session_id, len(improved) + len(translated))
    return {"translated_text": translated}


@app.post("/rephrase/")
def rephrase(req: RephraseRequest) -> dict[str, str]:
    model = chosen_model(req.model)
    rewritten = improve_prompt(req.prompt.strip(), model)
    return {"rephrased": rewritten}


@app.post("/copy-variants/")
def copy_variants(req: VariantsRequest, session_id: str = Header(..., alias="X-Lex-Session")) -> dict[str, list[str]]:
    model = chosen_model(req.model)
    variants = generate_variants(req.prompt.strip(), req.target_language, model)
    update_usage(session_id, sum(len(item) for item in variants))
    return {"variants": variants}


@app.post("/feedback/")
def feedback(req: FeedbackRequest, session_id: str = Header(..., alias="X-Lex-Session")) -> dict[str, str]:
    save_feedback_row(
        session_id,
        req.original_prompt.strip(),
        req.translated_text.strip(),
        req.target_language,
        req.feedback.strip(),
    )
    return {"message": "Feedback stored"}


@app.post("/variant-feedback/")
def variant_feedback(req: VariantFeedbackRequest, session_id: str = Header(..., alias="X-Lex-Session")) -> dict[str, str]:
    save_feedback_row(
        session_id,
        req.original_prompt.strip(),
        req.variant_text.strip(),
        req.target_language,
        f"{req.rating} (alt)",
    )
    return {"message": "Variant feedback stored"}


@app.get("/feedbacks/")
def feedbacks(
    include_variants: bool = False,
    session_id: str = Header(..., alias="X-Lex-Session"),
) -> list[dict[str, str]]:
    try:
        rows = feedback_db.list_feedbacks(session_id, include_variants=include_variants)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, f"Feedback storage is unavailable: {feedback_db.safe_error_message(exc)}") from exc
    return [
        {
            "original_prompt": row["original_prompt"],
            "translated_text": row["translated_text"],
            "target_language": language_name(row["target_language"]),
            "feedback": row["feedback"],
            "created_at": str(row["created_at"]),
        }
        for row in rows
    ]


@app.delete("/feedbacks/clear")
def clear_feedbacks(session_id: str = Header(..., alias="X-Lex-Session")) -> dict[str, int]:
    try:
        deleted = feedback_db.clear_feedbacks(session_id)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, f"Feedback storage is unavailable: {feedback_db.safe_error_message(exc)}") from exc
    return {"deleted": deleted}


@app.get("/feedbacks/download")
def download_feedbacks(
    type: Literal["Good", "Bad"] | None = None,
    include_variants: bool = False,
    session_id: str = Header(..., alias="X-Lex-Session"),
) -> Response:
    try:
        rows = feedback_db.list_feedbacks(
            session_id,
            include_variants=include_variants,
            feedback_prefix=type,
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, f"Feedback storage is unavailable: {feedback_db.safe_error_message(exc)}") from exc
    if not rows:
        raise HTTPException(404, "No feedback rows available")

    book = Workbook()
    sheet = book.active
    sheet.title = "LexAi Feedback"
    sheet.append(["ID", "Prompt", "Output", "Language", "Feedback", "Created At"])
    for index, row in enumerate(rows, start=1):
        sheet.append(
            [
                index,
                row["original_prompt"],
                row["translated_text"],
                language_name(row["target_language"]),
                row["feedback"],
                str(row["created_at"]),
            ]
        )
    output = io.BytesIO()
    book.save(output)
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="lexai_feedbacks.xlsx"'},
    )


@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)) -> dict[str, str]:
    pdf_bytes = await file.read()
    if len(pdf_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(413, "PDF exceeds the Phase 1 Vercel upload limit of 4 MB.")
    try:
        return {"extracted_text": extract_text_from_pdf(pdf_bytes)}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/upload-image/")
async def upload_image(file: UploadFile = File(...)) -> dict[str, str]:
    raise HTTPException(
        501,
        "Image OCR is not available in the Phase 1 Vercel deployment. Add external OCR or vision integration to support this route."
    )


@app.post("/feedback/regenerate")
def regenerate(req: RegenRequest, session_id: str = Header(..., alias="X-Lex-Session")) -> dict[str, str]:
    if not critique_allowed(req.reason):
        raise HTTPException(400, "Critique was flagged as unsafe")

    model = chosen_model(req.model)
    save_feedback_row(
        session_id,
        req.original_prompt.strip(),
        req.translated_text.strip(),
        req.target_language,
        f"Bad - {req.reason[:100]}",
    )

    improved_prompt = rewrite_from_critique(
        req.original_prompt.strip(),
        req.translated_text.strip(),
        req.reason.strip(),
        model,
    )
    if normalized_text(improved_prompt) == normalized_text(req.original_prompt):
        improved_prompt = rewrite_from_critique(
            req.original_prompt.strip(),
            req.translated_text.strip(),
            req.reason.strip(),
            model,
            force_distinct=True,
        )

    new_translation = translate_text(improved_prompt, req.target_language, model)
    new_translation = qa_translation(improved_prompt, new_translation, req.target_language, model)
    if normalized_text(new_translation) == normalized_text(req.translated_text):
        improved_prompt = rewrite_from_critique(
            req.original_prompt.strip(),
            req.translated_text.strip(),
            req.reason.strip(),
            model,
            force_distinct=True,
        )
        new_translation = translate_text(improved_prompt, req.target_language, model)
        new_translation = qa_translation(improved_prompt, new_translation, req.target_language, model)
    update_usage(session_id, len(improved_prompt) + len(new_translation))
    return {"improved_prompt": improved_prompt, "new_translation": new_translation}


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots() -> str:
    return "User-agent: *\nDisallow: /\n"
