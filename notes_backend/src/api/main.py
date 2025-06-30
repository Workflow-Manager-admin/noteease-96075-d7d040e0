from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import database
from . import routes

openapi_tags = [
    {"name": "Auth", "description": "User authentication and management"},
    {"name": "Notes", "description": "CRUD operations for Notes"},
]

app = FastAPI(
    title="NoteSaver API",
    description=(
        "FastAPI backend for NoteSaver App. "
        "Handles authentication and notes CRUD operations."
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)


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


# Register all API routes
app.include_router(routes.router)


@app.get("/", tags=["Other"])
def health_check():
    """Health check endpoint - confirms that the API is live."""
    return {"message": "Healthy"}
