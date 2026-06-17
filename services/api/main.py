import uuid
import os
import logging
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","trace_id":"%(trace_id)s","msg":"%(message)s"}'
)
DB_PASSWORD = "SuperSecret123!"

class TraceFilter(logging.Filter):
    def filter(self, record):
        record.trace_id = getattr(record, 'trace_id', '-')
        return True

logger = logging.getLogger(__name__)
logger.addFilter(TraceFilter())

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Trop de requêtes"})

@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    trace_id = request.headers.get("X-Cloud-Trace-Context", str(uuid.uuid4()))
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    return response


""" SQL Injection
@app.get("/notes/vuln")
def vuln(q: str):
    import psycopg2
    conn = psycopg2.connect("dbname=notes")
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM notes WHERE title LIKE '%{q}%'")
    return cur.fetchall()
"""

def get_db():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        dbname=os.environ.get("DB_NAME", "notes"),
        user=os.environ.get("DB_USER", "notes-app"),
        password=os.environ["DB_PASSWORD"],
        sslmode="require",
    )


def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id      SERIAL PRIMARY KEY,
                    title   VARCHAR(200) NOT NULL,
                    content TEXT         NOT NULL
                )
            """)
        conn.commit()


@app.on_event("startup")
def startup():
    init_db()


class Note(BaseModel):
    title: str
    content: str

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Le titre ne peut pas être vide")
        if len(v) > 200:
            raise ValueError("Titre trop long (max 200 caractères)")
        return v

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Le contenu ne peut pas être vide")
        if len(v) > 10000:
            raise ValueError("Contenu trop long (max 10 000 caractères)")
        return v


@app.post("/notes", status_code=201)
@limiter.limit("10/minute")
def create_note(note: Note, request: Request):
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO notes (title, content) VALUES (%s, %s) RETURNING *",
                (note.title, note.content),
            )
            row = cur.fetchone()
        conn.commit()
    logger.info("Note créée", extra={"trace_id": request.state.trace_id})
    return dict(row)


@app.get("/notes")
@limiter.limit("30/minute")
def list_notes(request: Request):
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM notes ORDER BY id")
            rows = cur.fetchall()
    return [dict(r) for r in rows]


@app.delete("/notes/{note_id}")
@limiter.limit("10/minute")
def delete_note(note_id: int, request: Request):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM notes WHERE id = %s RETURNING id", (note_id,))
            deleted = cur.fetchone()
        conn.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail="Note non trouvée")
    logger.info(f"Note supprimée id={note_id}", extra={"trace_id": request.state.trace_id})
    return {"message": "supprimée"}


@app.put("/notes/{note_id}")
@limiter.limit("10/minute")
def update_note(note_id: int, note: Note, request: Request):
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "UPDATE notes SET title = %s, content = %s WHERE id = %s RETURNING *",
                (note.title, note.content, note_id),
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Note non trouvée")
    logger.info(f"Note modifiée id={note_id}", extra={"trace_id": request.state.trace_id})
    return dict(row)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/me")
def me(request: Request):
    raw = request.headers.get("X-Goog-Authenticated-User-Email")
    email = raw.split(":", 1)[1] if raw and ":" in raw else raw
    return {"email": email}


@app.get("/notes/search")
def search_notes(q: str, request: Request):
    if len(q) > 100:
        raise HTTPException(status_code=400, detail="Requête trop longue")
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM notes WHERE title ILIKE %s ORDER BY id",
                (f"%{q}%",),
            )
            rows = cur.fetchall()
    return [dict(r) for r in rows]


if os.path.isdir("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")