from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

app = FastAPI(title="Pramana")


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("select 1"))
    return {"status": "ok"}
