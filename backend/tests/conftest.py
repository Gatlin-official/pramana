import pytest
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document
from app.db.session import engine

TOY = [
    "Path parameters are declared with Python format string syntax in the route path.",
    "Use Depends to declare dependencies; FastAPI resolves and injects them per request.",
    "CORS middleware lets browsers call your API from another origin.",
]


def onehot(i: int) -> list[float]:
    v = [0.0] * 768
    v[i] = 1.0
    return v


@pytest.fixture
def db():
    """Session inside a transaction that is rolled back, so tests never touch real data."""
    conn = engine.connect()
    tx = conn.begin()
    s = Session(conn, join_transaction_mode="create_savepoint")
    yield s
    s.close()
    tx.rollback()
    conn.close()


@pytest.fixture
def toy(db):
    doc = Document(source="toy.md", title="toy", kind="md", text="\n".join(TOY))
    db.add(doc)
    db.flush()
    pos, ids = 0, []
    for i, t in enumerate(TOY):
        c = Chunk(
            doc_id=doc.id,
            config="toy",
            ordinal=i,
            text=t,
            token_count=len(t.split()),
            char_start=pos,
            char_end=pos + len(t),
            embedding=onehot(i),
        )
        db.add(c)
        db.flush()
        ids.append(c.id)
        pos += len(t) + 1
    return ids
