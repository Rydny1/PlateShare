import logging
import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


load_dotenv()

logger = logging.getLogger(__name__)
database_url = os.getenv("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)


class Base(DeclarativeBase):
    pass


engine = create_engine(database_url, pool_pre_ping=True) if database_url else None
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False) if engine else None


def create_tables() -> None:
    if engine is None:
        logger.warning("DATABASE_URL is not set; database tables were not created")
        return

    import models

    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        columns = {column["name"] for column in inspect(connection).get_columns("offers")}
        if "image_data" not in columns:
            connection.execute(text("ALTER TABLE offers ADD COLUMN image_data TEXT"))
        if "image_content_type" not in columns:
            connection.execute(
                text("ALTER TABLE offers ADD COLUMN image_content_type VARCHAR(100)")
            )
    logger.info("Database tables are ready")


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()