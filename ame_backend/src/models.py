"""
Capa de memoria de estado para el Núcleo Evolutivo de AURA.

Usa SQLAlchemy 2.x sobre la variable de entorno ``DATABASE_URL``:
- Si ``DATABASE_URL`` apunta a PostgreSQL (Render), se conecta ahí.
- Si no está presente (o falla), cae de forma segura a SQLite local
  (``aura_core.db``) para desarrollo y fallback.

Tablas:
- ``chat_history``: mensajes reales del chat (usuario / asistente).
- ``neural_state``: pesos, bias y tasa de aprendizaje de la neurona.
- ``semantic_memory``: memoria subconsciente vectorial (RAG) con
  embeddings de Gemini y similitud de coseno.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import (
    Session,
    declarative_base,
    sessionmaker,
)

Base = declarative_base()


def _resolve_url() -> str:
    """Devuelve DATABASE_URL si existe; si no, SQLite local seguro."""
    raw = (os.environ.get("DATABASE_URL") or "").strip()
    if raw:
        # SQLAlchemy espera el driver postgresql+psycopg2:// en vez de postgres://
        if raw.startswith("postgres://"):
            raw = "postgresql+psycopg2://" + raw[len("postgres://") :]
        elif raw.startswith("postgresql://"):
            raw = "postgresql+psycopg2://" + raw[len("postgresql://") :]
        return raw
    db_path = Path(__file__).resolve().parent.parent / "aura_core.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # Forma correcta Windows: sqlite:///C:/ruta/db.sqlite (3 barras).
    posix = db_path.as_posix()
    return f"sqlite:///{posix}"


ENGINE_URL = _resolve_url()
IS_EXTERNAL = ENGINE_URL.startswith("postgresql")
ECHO = False

engine = create_engine(ENGINE_URL, echo=ECHO, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class ChatMessage(Base):
    """Un mensaje real intercambiado con la IA."""

    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String(16))  # 'user' | 'assistant' | 'system'
    content = Column(Text)
    provider = Column(String(64))
    session_id = Column(String(64))
    context = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "provider": self.provider,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class NeuralState(Base):
    """Estado persistido de la neurona evolutiva (una sola fila)."""

    __tablename__ = "neural_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    weights = Column(Text)  # JSON list[float]
    bias = Column(Float)
    learning_rate = Column(Float)
    iterations = Column(Integer, default=0)
    last_stability = Column(Float)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class SemanticMemory(Base):
    """Memoria subconsciente vectorial (RAG).

    Cada registro guarda un fragmento de conocimiento (mensaje clave,
    código importante, nota) junto con su embedding de Gemini como JSON.
    """

    __tablename__ = "semantic_memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text)
    kind = Column(String(32), default="chat")  # 'chat' | 'code' | 'note'
    vector_json = Column(Text)  # JSON list[float]
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


def init_db() -> None:
    """Crea las tablas si no existen."""
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    return SessionLocal()


# --------------------------------------------------------------------------- #
# API de alto nivel
# --------------------------------------------------------------------------- #
def save_message(
    role: str,
    content: str,
    provider: Optional[str] = None,
    session_id: Optional[str] = None,
    context: Optional[str] = None,
) -> ChatMessage:
    with get_session() as s:
        msg = ChatMessage(
            role=role,
            content=content,
            provider=provider,
            session_id=session_id,
            context=context,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        s.add(msg)
        s.commit()
        s.refresh(msg)
        return msg


def recent_messages(limit: int = 50) -> List[Dict[str, Any]]:
    with get_session() as s:
        rows = (
            s.query(ChatMessage)
            .order_by(ChatMessage.id.desc())
            .limit(limit)
            .all()
        )
        return [r.to_dict() for r in reversed(rows)]


def count_messages() -> int:
    with get_session() as s:
        return s.query(ChatMessage).count()


def load_neural_state() -> Optional[Dict[str, Any]]:
    with get_session() as s:
        row = s.query(NeuralState).order_by(NeuralState.id).first()
        if not row:
            return None
        return {
            "weights": json.loads(row.weights),
            "bias": row.bias,
            "learning_rate": row.learning_rate,
            "iterations": row.iterations,
            "last_stability": row.last_stability,
        }


def save_neural_state(
    weights: List[float],
    bias: float,
    learning_rate: float,
    iterations: int,
    last_stability: Optional[float] = None,
) -> None:
    with get_session() as s:
        row = s.query(NeuralState).order_by(NeuralState.id).first()
        if row is None:
            row = NeuralState()
            s.add(row)
        row.weights = json.dumps(weights)
        row.bias = bias
        row.learning_rate = learning_rate
        row.iterations = iterations
        row.last_stability = last_stability
        row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        s.commit()


# --------------------------------------------------------------------------- #
# Memoria semántica (RAG)
# --------------------------------------------------------------------------- #
def save_memory(
    content: str,
    vector: Optional[List[float]] = None,
    kind: str = "chat",
) -> SemanticMemory:
    with get_session() as s:
        row = SemanticMemory(
            content=content,
            kind=kind,
            vector_json=json.dumps(vector) if vector is not None else None,
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        s.add(row)
        s.commit()
        s.refresh(row)
        return row


def memory_rows() -> List[Dict[str, Any]]:
    """Devuelve todos los recuerdos con su vector (para retrieval)."""
    with get_session() as s:
        rows = s.query(SemanticMemory).order_by(SemanticMemory.id.desc()).all()
        return [
            {
                "id": r.id,
                "content": r.content,
                "kind": r.kind,
                "vector": json.loads(r.vector_json) if r.vector_json else None,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            }
            for r in rows
        ]


def count_memories() -> int:
    with get_session() as s:
        return s.query(SemanticMemory).count()


def recent_memories(limit: int = 20) -> List[Dict[str, Any]]:
    with get_session() as s:
        rows = (
            s.query(SemanticMemory)
            .order_by(SemanticMemory.id.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "content": r.content,
                "kind": r.kind,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            }
            for r in reversed(rows)
        ]
