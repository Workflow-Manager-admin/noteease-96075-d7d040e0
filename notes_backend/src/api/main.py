from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import database

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure models are imported so Alembic and SQLAlchemy are aware of them
# In deployment, consider running migrations via Alembic tool

@app.on_event("startup")
def on_startup():
    # Optionally create tables on first run for dev/SQLite use.
    database.Base.metadata.create_all(bind=database.engine)


@app.get("/")
def health_check():
    return {"message": "Healthy"}
