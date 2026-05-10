from fastapi.testclient import TestClient
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_create_note():
    r = client.post("/notes", json={"title": "Test", "content": "Contenu"})
    assert r.status_code == 201
    assert r.json()["title"] == "Test"

def test_list_notes():
    r = client.get("/notes")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_delete_note_not_found():
    r = client.delete("/notes/9999")
    assert r.status_code == 404

def test_create_note_empty_title():
    r = client.post("/notes", json={"title": "", "content": "Contenu"})
    assert r.status_code == 422

def test_create_note_title_too_long():
    r = client.post("/notes", json={"title": "A" * 201, "content": "Contenu"})
    assert r.status_code == 422
