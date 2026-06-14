import os
import sys

os.environ["USE_SQLITE"] = "true"
os.environ["SQLITE_URL"] = "sqlite:///./test-notes.db"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from main import Base, app, engine, init_db

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    init_db()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_create_note():
    response = client.post("/notes", json={"title": "Test", "content": "Contenu"})
    assert response.status_code == 201
    assert response.json()["title"] == "Test"


def test_list_notes():
    client.post("/notes", json={"title": "Liste", "content": "Contenu"})
    response = client.get("/notes")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert response.json()[0]["title"] == "Liste"


def test_search_notes():
    client.post("/notes", json={"title": "DevSecOps", "content": "Pipeline"})
    response = client.get("/notes/search", params={"q": "devsec"})
    assert response.status_code == 200
    assert response.json()[0]["title"] == "DevSecOps"


def test_delete_note():
    created = client.post("/notes", json={"title": "Delete", "content": "Me"}).json()
    response = client.delete(f"/notes/{created['id']}")
    assert response.status_code == 200
    assert response.json() == {"message": "supprimée"}


def test_delete_note_not_found():
    response = client.delete("/notes/9999")
    assert response.status_code == 404


def test_create_note_empty_title():
    response = client.post("/notes", json={"title": "", "content": "Contenu"})
    assert response.status_code == 422


def test_create_note_title_too_long():
    response = client.post("/notes", json={"title": "A" * 201, "content": "Contenu"})
    assert response.status_code == 422


def test_search_query_too_long():
    response = client.get("/notes/search", params={"q": "A" * 101})
    assert response.status_code == 400
