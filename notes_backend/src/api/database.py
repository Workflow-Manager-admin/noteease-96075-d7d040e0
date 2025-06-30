"""
Database configuration and SQLAlchemy base for NoteSaver FastAPI application.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os


# PUBLIC_INTERFACE
def get_database_url():
    """Constructs the database URL from environment variables.

    Supports SQLite by default for development.
    """
    # In production, swap in PostgreSQL/MySQL as needed.
    return os.getenv("DATABASE_URL", "sqlite:///./notes.db")


SQLALCHEMY_DATABASE_URL = get_database_url()

# SQLite: connect_args required to allow multiple threads
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    connect_args = {}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
