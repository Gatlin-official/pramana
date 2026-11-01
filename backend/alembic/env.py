from alembic import context
from sqlalchemy import create_engine

from app.core.config import DATABASE_URL
from app.db.models import Base

target_metadata = Base.metadata

with create_engine(DATABASE_URL).connect() as conn:
    context.configure(connection=conn, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
