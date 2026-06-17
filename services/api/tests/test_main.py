# ─── Tests nominaux ───────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_me_anonymous(client):
    r = client.get("/me")
    assert r.status_code == 200
    assert r.json() == {"email": None}


def test_me_authenticated(client):
    r = client.get("/me", headers={"X-Goog-Authenticated-User-Email": "accounts.google.com:demo@example.com"})
    assert r.status_code == 200
    assert r.json() == {"email": "demo@example.com"}


def test_create_note(client, reset_cursor):
    reset_cursor.fetchone.return_value = {"id": 1, "title": "Test", "content": "Contenu"}
    r = client.post("/notes", json={"title": "Test", "content": "Contenu"})
    assert r.status_code == 201
    assert r.json()["title"] == "Test"


def test_list_notes(client, reset_cursor):
    reset_cursor.fetchall.return_value = [{"id": 1, "title": "Test", "content": "Contenu"}]
    r = client.get("/notes")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_delete_note_not_found(client, reset_cursor):
    reset_cursor.fetchone.return_value = None
    r = client.delete("/notes/9999")
    assert r.status_code == 404


def test_update_note(client, reset_cursor):
    reset_cursor.fetchone.return_value = {"id": 1, "title": "Modifié", "content": "Nouveau contenu"}
    r = client.put("/notes/1", json={"title": "Modifié", "content": "Nouveau contenu"})
    assert r.status_code == 200
    assert r.json()["title"] == "Modifié"


def test_update_note_not_found(client, reset_cursor):
    reset_cursor.fetchone.return_value = None
    r = client.put("/notes/9999", json={"title": "Test", "content": "Contenu"})
    assert r.status_code == 404


def test_create_note_empty_title(client):
    r = client.post("/notes", json={"title": "", "content": "Contenu"})
    assert r.status_code == 422


def test_create_note_title_too_long(client):
    r = client.post("/notes", json={"title": "A" * 201, "content": "Contenu"})
    assert r.status_code == 422


# ─── Tests injection SQL ──────────────────────────────────────────────────────

def test_sqli_tautologie(client, reset_cursor):
    """
    Payload : ' OR '1'='1
    Avec requêtes paramétrées (%s), le payload est traité comme du texte brut.
    """
    reset_cursor.fetchall.return_value = []
    r = client.get("/notes/search", params={"q": "' OR '1'='1"})
    assert r.status_code == 200
    assert r.json() == []


def test_sqli_drop_table(client, reset_cursor):
    """
    Payload : '; DROP TABLE notes; --
    Avec requêtes paramétrées, impossible d'exécuter une seconde instruction.
    """
    reset_cursor.fetchall.return_value = []
    r = client.get("/notes/search", params={"q": "'; DROP TABLE notes; --"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_sqli_union(client, reset_cursor):
    """
    Payload : ' UNION SELECT username, password FROM users --
    Aucune donnée sensible retournée grâce aux requêtes paramétrées.
    """
    reset_cursor.fetchall.return_value = []
    r = client.get("/notes/search", params={"q": "' UNION SELECT username, password FROM users --"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_sqli_requete_trop_longue(client):
    """
    Un payload d'injection SQL long est bloqué par la validation (max 100 chars).
    """
    payload = "' OR '1'='1' UNION SELECT table_name, column_name FROM information_schema.columns WHERE table_schema='public' --"
    assert len(payload) > 100
    r = client.get("/notes/search", params={"q": payload})
    assert r.status_code == 400
    assert "trop longue" in r.json()["detail"]