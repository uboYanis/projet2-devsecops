import logging
import os
import uuid
from contextlib import contextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import Column, Integer, String, Text, create_engine, select
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, declarative_base, sessionmaker

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","trace_id":"%(trace_id)s","msg":"%(message)s"}',
)


class TraceFilter(logging.Filter):
    def filter(self, record):
        record.trace_id = getattr(record, "trace_id", "-")
        return True


logger = logging.getLogger(__name__)
logger.addFilter(TraceFilter())


def build_database_url():
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")
    if os.getenv("USE_SQLITE", "false").lower() == "true":
        return os.getenv("SQLITE_URL", "sqlite:///./notes.db")

    password = os.getenv("DB_PASSWORD")
    if not password:
        return "sqlite:///./notes.db"

    query = {}
    cloud_sql_instance = os.getenv("INSTANCE_CONNECTION_NAME")
    if cloud_sql_instance:
        query["host"] = f"/cloudsql/{cloud_sql_instance}"

    return URL.create(
        "postgresql+psycopg2",
        username=os.getenv("DB_USER", "notes-app"),
        password=password,
        host=os.getenv("DB_HOST") if not cloud_sql_instance else None,
        port=int(os.getenv("DB_PORT", "5432")) if os.getenv("DB_HOST") else None,
        database=os.getenv("DB_NAME", "notes"),
        query=query,
    )


engine = create_engine(build_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class NoteModel(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)


class NoteCreate(BaseModel):
    title: str
    content: str

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Le titre ne peut pas être vide")
        if len(value) > 200:
            raise ValueError("Titre trop long (max 200 caractères)")
        return value

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Le contenu ne peut pas être vide")
        if len(value) > 10000:
            raise ValueError("Contenu trop long (max 10 000 caractères)")
        return value


class NoteRead(BaseModel):
    id: int
    title: str
    content: str

    model_config = {"from_attributes": True}


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Notes API")
app.state.limiter = limiter
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


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


def init_db():
    Base.metadata.create_all(bind=engine)


@app.on_event("startup")
def startup():
    init_db()


@contextmanager
def session_scope():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db():
    with session_scope() as db:
        yield db


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok", "database": "ok"}


@app.post("/notes", response_model=NoteRead, status_code=201)
@limiter.limit("10/minute")
def create_note(note: NoteCreate, request: Request, db: Session = Depends(get_db)):
    created = NoteModel(title=note.title, content=note.content)
    db.add(created)
    db.flush()
    db.refresh(created)
    logger.info("Note créée", extra={"trace_id": request.state.trace_id})
    return created


@app.get("/notes", response_model=list[NoteRead])
@limiter.limit("30/minute")
def list_notes(request: Request, db: Session = Depends(get_db)):
    return db.scalars(select(NoteModel).order_by(NoteModel.id.desc())).all()


@app.get("/notes/search", response_model=list[NoteRead])
def search_notes(q: str, request: Request, db: Session = Depends(get_db)):
    if len(q) > 100:
        raise HTTPException(status_code=400, detail="Requête trop longue")
    return db.scalars(
        select(NoteModel)
        .where(NoteModel.title.ilike(f"%{q}%"))
        .order_by(NoteModel.id.desc())
    ).all()


@app.delete("/notes/{note_id}")
@limiter.limit("10/minute")
def delete_note(note_id: int, request: Request, db: Session = Depends(get_db)):
    note = db.get(NoteModel, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note non trouvée")
    db.delete(note)
    logger.info(f"Note supprimée id={note_id}", extra={"trace_id": request.state.trace_id})
    return {"message": "supprimée"}

def run_server():
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "127.0.0.1"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("API_RELOAD", "true").lower() == "true",
    )


if __name__ == "__main__":
    run_server()

