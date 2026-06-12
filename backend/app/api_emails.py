from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Literal, Dict
from openai import OpenAI
import os, json, re

# ---------- Router ----------
router = APIRouter(prefix="/api", tags=["emails"])

# ---------- OpenAI client ----------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
ALLOWED_MODELS = {
    model.strip()
    for model in os.getenv("ALLOWED_MODELS", "gpt-4.1-mini,gpt-4o-mini,gpt-4o").split(",")
    if model.strip()
}

# ---------- Types & Models ----------
MethodName = Literal["AIDA", "PAS", "4U", "STAR", "IDCA"]

class GenerateRequest(BaseModel):
    industry: str
    persona: str
    offer: str
    value_prop: str
    market_state: str
    cta_type: Literal["buy","book"]
    cta_target: str  # allow http(s), tel:, mailto:
    tone: Optional[Literal["neutral","friendly","formal","bold"]] = "neutral"
    differentiators: Optional[List[str]] = []
    competitors: Optional[List[str]] = []
    only_method: Optional[MethodName] = None  # for per-method regenerate

class Email(BaseModel):
    method: MethodName
    title: Optional[str] = None
    body: str
    cta_label: Optional[str] = None
    cta_target: str

class GenerateResponse(BaseModel):
    emails: List[Email]
    meta: Dict[str, Dict[str, int]]  # {"word_counts": {...}}

# ---------- Prompting ----------
SYSTEM = (
    "You are a seasoned B2B email copywriter. Output strictly JSON (no prose). "
    "Produce skim-friendly emails that follow the named framework precisely. "
    "Each email must be 50–125 words and end with a clear CTA matching the desired action and using the provided target. "
    "Write in American English. Use concise line breaks to improve scan-ability. Avoid clichéd fluff."
)

def _user_prompt(payload: GenerateRequest, restrict: Optional[MethodName]) -> str:
    spec = {
        "inputs": payload.model_dump(),
        "requirements": {
            "length_words": [50, 125],
            "methods": [restrict] if restrict else ["AIDA","PAS","4U","STAR","IDCA"],
            "cta_rule": f"Use '{payload.cta_type}' and target '{payload.cta_target}'.",
            "tone": payload.tone,
            "skim_friendly": True
        },
        "output_schema": {
            "emails": [
                {
                    "method": "AIDA|PAS|4U|STAR|IDCA",
                    "title": "short subject-like title",
                    "body": "50–125 words, with line breaks",
                    "cta_label": "Specific label matching action",
                    "cta_target": payload.cta_target
                }
            ]
        }
    }
    return json.dumps(spec, ensure_ascii=False)


def selected_model() -> str:
    return DEFAULT_MODEL if DEFAULT_MODEL in ALLOWED_MODELS else sorted(ALLOWED_MODELS)[0]

def _call_llm(payload: GenerateRequest, restrict: Optional[MethodName]) -> Dict:
    resp = client.chat.completions.create(
        model=selected_model(),
        temperature=0.7,
        response_format={"type": "json_object"},
        messages=[
            {"role":"system", "content": SYSTEM},
            {"role":"user",   "content": _user_prompt(payload, restrict)}
        ]
    )
    text = resp.choices[0].message.content
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"LLM did not return JSON: {e}")

# ---------- Validation helpers ----------
def _word_count(s: str) -> int:
    return len(re.findall(r"\b\w[\w'-]*\b", s))

def _ensure_linebreaks(s: str) -> str:
    if s.count("\n") >= 2:
        return s
    words = s.split()
    lines, chunk, cap = [], [], 20
    for w in words:
        chunk.append(w)
        if len(chunk) >= cap:
            lines.append(" ".join(chunk)); chunk = []
    if chunk: lines.append(" ".join(chunk))
    return "\n".join(lines)

def _normalize_cta_label(cta_type: str) -> str:
    return "Buy now" if cta_type == "buy" else "Book a 20-min call"

def _validate_and_fix(payload: GenerateRequest, data: Dict, restrict: Optional[MethodName]) -> GenerateResponse:
    expect = [restrict] if restrict else ["AIDA","PAS","4U","STAR","IDCA"]
    got = data.get("emails", [])
    if not isinstance(got, list) or not got:
        raise HTTPException(status_code=502, detail="Missing 'emails' array from model.")

    if restrict:
        got = [e for e in got if e.get("method") == restrict]
        if not got:
            raise HTTPException(status_code=502, detail=f"Model omitted required method {restrict}.")

    methods = [e.get("method") for e in got]
    missing = [m for m in expect if m not in methods]
    if missing:
        raise HTTPException(status_code=502, detail=f"Missing methods: {missing}")

    out_emails: List[Email] = []
    wc: Dict[str, int] = {}

    for e in got:
        method: MethodName = e.get("method")
        body = (e.get("body") or "").strip()
        title = (e.get("title") or f"{method}: A concise outreach").strip()
        cta_label = (e.get("cta_label") or _normalize_cta_label(payload.cta_type)).strip()
        cta_target = payload.cta_target

        # enforce CTA at end
        if not body.lower().rstrip().endswith(cta_label.lower()):
            suffix = f" → {cta_target}"
            body = body.rstrip() + f"\n{cta_label}{suffix}"

        # enforce skim-friendly layout
        body = _ensure_linebreaks(body)

        # length guard (single corrective pass)
        count = _word_count(body)
        if count < 50 or count > 125:
            fix = client.chat.completions.create(
                model=selected_model(),
                temperature=0.3,
                messages=[
                    {"role":"system","content":"Rewrite to 50–125 words, keep meaning & CTA intact, add concise line breaks. Return only the email body text."},
                    {"role":"user","content": body}
                ]
            )
            try:
                body = _ensure_linebreaks(fix.choices[0].message.content.strip())
            except Exception:
                pass

        wc[method] = _word_count(body)

        out_emails.append(Email(
            method=method, title=title, body=body,
            cta_label=cta_label, cta_target=cta_target
        ))

    return GenerateResponse(emails=out_emails, meta={"word_counts": wc})

# ---------- Route ----------
@router.post("/generate-emails", response_model=GenerateResponse)
def generate_emails(req: GenerateRequest):
    if not re.match(r"^(https?:|tel:|mailto:)", req.cta_target):
        raise HTTPException(status_code=400, detail="cta_target must start with http(s):, tel:, or mailto:")
    raw = _call_llm(req, req.only_method)
    final = _validate_and_fix(req, raw, req.only_method)
    return final
