from fastapi.testclient import TestClient
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from main import app

client = TestClient(app)

# ─── Tests nominaux ───────────────────────────────────────────────────────────

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

# ─── Tests injection SQL ──────────────────────────────────────────────────────
# Ces tests vérifient que l'endpoint /notes/search résiste aux tentatives
# d'injection SQL classiques. La recherche est faite en mémoire (pas de SQL),
# donc les payloads malveillants sont traités comme du texte brut.

def test_sqli_tautologie():
    """
    Payload : ' OR '1'='1
    En SQL vulnérable : WHERE title LIKE '%' OR '1'='1%'  → retourne tout
    Ici : cherche littéralement ce texte → liste vide (aucune note ne contient ce titre)
    """
    client.post("/notes", json={"title": "Note normale", "content": "Contenu"})
    r = client.get("/notes/search", params={"q": "' OR '1'='1"})
    assert r.status_code == 200
    for note in r.json():
        assert "' OR '1'='1" not in note["title"]

def test_sqli_drop_table():
    """
    Payload : '; DROP TABLE notes; --
    En SQL vulnérable : exécuterait la suppression de la table
    Ici : traité comme texte → résultat vide, pas d'erreur serveur
    """
    r = client.get("/notes/search", params={"q": "'; DROP TABLE notes; --"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_sqli_union():
    """
    Payload : ' UNION SELECT username, password FROM users --
    En SQL vulnérable : exfiltrerait d'autres tables
    Ici : aucune donnée sensible retournée, juste une liste vide
    """
    r = client.get("/notes/search", params={"q": "' UNION SELECT username, password FROM users --"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_sqli_requete_trop_longue():
    """
    Un payload d'injection SQL dépasse souvent 100 caractères.
    La validation bloque la requête avant même de la traiter.
    """
    payload = "' OR '1'='1' UNION SELECT table_name FROM information_schema.tables --"
    assert len(payload) > 100
    r = client.get("/notes/search", params={"q": payload})
    assert r.status_code == 400
    assert "trop longue" in r.json()["detail"]