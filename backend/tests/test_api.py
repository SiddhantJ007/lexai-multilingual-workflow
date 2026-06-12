from fastapi.testclient import TestClient

from backend.app import main as main_module
from backend.app.main import app


client = TestClient(app)


def test_healthz_smoke():
    response = client.get("/healthz")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "database_ok" in payload


def test_full_process_success(monkeypatch):
    monkeypatch.setattr(main_module, "improve_for_translation", lambda prompt, model: prompt)
    monkeypatch.setattr(main_module, "translate_text", lambda text, target_language, model: "Ciao mondo")
    monkeypatch.setattr(main_module, "qa_translation", lambda source, translated, target_language, model: translated)
    monkeypatch.setattr(main_module, "update_usage", lambda session_id, chars: None)

    response = client.post(
        "/full-process/",
        headers={"X-Lex-Session": "test-session"},
        json={"prompt": "Hello world", "target_language": "IT", "model": "gpt-4.1-mini"},
    )

    assert response.status_code == 200
    assert response.json() == {"translated_text": "Ciao mondo"}


def test_input_validation_error():
    response = client.post(
        "/full-process/",
        headers={"X-Lex-Session": "test-session"},
        json={"prompt": "", "target_language": "IT", "model": "gpt-4.1-mini"},
    )
    assert response.status_code == 422


def test_feedback_route_error_handling(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("Feedback storage is not configured. Set DATABASE_URL or SUPABASE_DB_URL.")

    monkeypatch.setattr(main_module.feedback_db, "list_feedbacks", boom)

    response = client.get("/feedbacks/", headers={"X-Lex-Session": "test-session"})

    assert response.status_code == 503
    assert "Feedback storage is not configured" in response.json()["detail"]


def test_upload_image_unavailable_message():
    response = client.post(
        "/upload-image/",
        headers={"X-Lex-Session": "test-session"},
        files={"file": ("sample.png", b"fake", "image/png")},
    )
    assert response.status_code == 501
    assert "Image OCR is not available" in response.json()["detail"]
