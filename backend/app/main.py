from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

import csv
import io
import os
import re
from typing import Final, Literal

import requests
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, Response
from openai import OpenAI
from pydantic import BaseModel, Field

from app.api_emails import router as emails_router
from app import db as feedback_db
from app.utils import critique_allowed
from app.utils_pdf import extract_text_from_pdf

MAX_UPLOAD_SIZE: Final = 4_000_000

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

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
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


def translate_with_deepl(text: str, target_language: str) -> str | None:
    if not DEEPL_API_KEY:
        return None
    response = requests.post(
        DEEPL_API_URL,
        data={
            "auth_key": DEEPL_API_KEY,
            "text": text,
            "target_lang": target_language.upper(),
            "formality": "prefer_less",
        },
        timeout=20,
    )
    if not response.ok:
        raise HTTPException(502, f"DeepL request failed: {response.status_code}")
    payload = response.json()
    translations = payload.get("translations") or []
    if not translations:
        raise HTTPException(502, "DeepL returned no translations")
    return translations[0]["text"]


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
    deepl_result = translate_with_deepl(text, target_language)
    if deepl_result:
        return deepl_result.strip()
    return translate_with_openai(text, target_language, model)


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


@app.on_event("startup")
def startup() -> None:
    if feedback_db.is_configured():
        feedback_db.ensure_schema()


@app.get("/")
def home() -> dict[str, str]:
    return {"message": "LexAi portfolio backend running"}


@app.get("/ping")
def ping() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/healthz")
def healthz() -> dict[str, bool]:
    try:
        db_ok = feedback_db.ping() if feedback_db.is_configured() else False
    except Exception:
        db_ok = False
    return {"ok": True, "database_configured": feedback_db.is_configured(), "database_ok": db_ok}


@app.get("/health")
def health() -> dict[str, bool]:
    return healthz()


@app.post("/full-process/")
def full_process(req: FullProcessRequest) -> dict[str, str]:
    model = chosen_model(req.model)
    improved = improve_prompt(req.prompt.strip(), model)
    translated = translate_text(improved, req.target_language, model)
    return {"translated_text": translated}


@app.post("/rephrase/")
def rephrase(req: RephraseRequest) -> dict[str, str]:
    model = chosen_model(req.model)
    rewritten = improve_prompt(req.prompt.strip(), model)
    return {"rephrased": rewritten}


@app.post("/copy-variants/")
def copy_variants(req: VariantsRequest) -> dict[str, list[str]]:
    model = chosen_model(req.model)
    return {"variants": generate_variants(req.prompt.strip(), req.target_language, model)}


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
def feedbacks(session_id: str = Header(..., alias="X-Lex-Session")) -> list[dict[str, str]]:
    try:
        rows = feedback_db.list_feedbacks(session_id)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    return [
        {
            "original_prompt": row["original_prompt"],
            "translated_text": row["translated_text"],
            "target_language": language_name(row["target_language"]),
            "feedback": row["feedback"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


@app.delete("/feedbacks/clear")
def clear_feedbacks(session_id: str = Header(..., alias="X-Lex-Session")) -> dict[str, int]:
    try:
        deleted = feedback_db.clear_feedbacks(session_id)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    return {"deleted": deleted}


@app.get("/feedbacks/download")
def download_feedbacks(session_id: str = Header(..., alias="X-Lex-Session")) -> Response:
    try:
        rows = feedback_db.list_feedbacks(session_id)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    if not rows:
        raise HTTPException(404, "No feedback rows available")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Prompt", "Output", "Language", "Feedback", "Created At"])
    for index, row in enumerate(rows, start=1):
        writer.writerow(
            [
                index,
                row["original_prompt"],
                row["translated_text"],
                language_name(row["target_language"]),
                row["feedback"],
                row["created_at"],
            ]
        )
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="lexai_feedbacks.csv"'},
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
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "Improve the English source based on the critique while preserving its factual intent. "
                    "Return only the improved English text."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Original source:\n{req.original_prompt}\n\n"
                    f"Current output:\n{req.translated_text}\n\n"
                    f"Critique:\n{req.reason}"
                ),
            },
        ],
    )
    improved_prompt = response.output_text.strip()
    new_translation = translate_text(improved_prompt, req.target_language, model)

    save_feedback_row(
        session_id,
        req.original_prompt.strip(),
        req.translated_text.strip(),
        req.target_language,
        f"Bad - {req.reason[:100]}",
    )
    return {"improved_prompt": improved_prompt, "new_translation": new_translation}


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots() -> str:
    return "User-agent: *\nDisallow: /\n"
