"""
FastAPI routes for user authentication (register/login/logout) and notes CRUD operations,
using JWT for authentication. Secure and organized for frontend integration.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List, Optional
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field
import os

from . import models, database

# Router
router = APIRouter()


# --- JWT and Password Config ---
SECRET_KEY = os.getenv("SECRET_KEY", "insecure_dev_key_change_me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# --- Pydantic Schemas ---
class UserCreate(BaseModel):
    username: str = Field(
        ...,
        max_length=64,
        description="Unique username"
    )
    email: EmailStr = Field(
        ...,
        max_length=128
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=128
    )


class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str


class NoteCreate(BaseModel):
    title: str = Field(
        ...,
        max_length=256
    )
    content: Optional[str] = Field(
        None,
        description="Text content of the note"
    )


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(
        None,
        max_length=256
    )
    content: Optional[str] = None


class NoteOut(BaseModel):
    id: int
    title: str
    content: Optional[str]
    created_at: datetime
    updated_at: datetime
    owner_id: int

    class Config:
        orm_mode = True


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


# --- Dependency for getting current user ---
# PUBLIC_INTERFACE
def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> models.User:
    """Get current user from JWT access token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or token expired",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_username(db, username)
    if user is None:
        raise credentials_exception
    return user


# --- Auth Routes ---

# PUBLIC_INTERFACE
@router.post(
    "/auth/register",
    response_model=UserOut,
    tags=["Auth"],
    summary="Register new user"
)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user with username, email, and password."""
    if get_user_by_username(db, user.username):
        raise HTTPException(
            status_code=400,
            detail="Username already registered."
        )
    if get_user_by_email(db, user.email):
        raise HTTPException(
            status_code=400,
            detail="Email already registered."
        )
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# PUBLIC_INTERFACE
@router.post(
    "/auth/login",
    response_model=Token,
    tags=["Auth"],
    summary="User login and token generation"
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Authenticate user and return JWT access token."""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


# PUBLIC_INTERFACE
@router.post(
    "/auth/logout",
    tags=["Auth"],
    summary="Logout (client-side JWT discard)"
)
def logout():
    """
    [Stateless] 'Logout' is handled by discarding the token on the client.
    This endpoint exists for API symmetry and frontend handling.
    """
    return {"message": "Successfully logged out"}


# --- Notes CRUD Routes ---

# PUBLIC_INTERFACE
@router.post(
    "/notes/",
    response_model=NoteOut,
    tags=["Notes"],
    summary="Create Note"
)
def create_note(
    note: NoteCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new note for the current user."""
    db_note = models.Note(
        title=note.title,
        content=note.content,
        owner_id=current_user.id
    )
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note


# PUBLIC_INTERFACE
@router.get(
    "/notes/",
    response_model=List[NoteOut],
    tags=["Notes"],
    summary="List all notes"
)
def list_notes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all notes belonging to the current user."""
    notes = (
        db.query(models.Note)
        .filter(models.Note.owner_id == current_user.id)
        .order_by(models.Note.updated_at.desc())
        .all()
    )
    return notes


# PUBLIC_INTERFACE
@router.get(
    "/notes/{note_id}",
    response_model=NoteOut,
    tags=["Notes"],
    summary="Get note by ID"
)
def get_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Retrieve a single note by its ID, only if it belongs to the user."""
    note = (
        db.query(models.Note)
        .filter(
            models.Note.id == note_id,
            models.Note.owner_id == current_user.id
        )
        .first()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


# PUBLIC_INTERFACE
@router.put(
    "/notes/{note_id}",
    response_model=NoteOut,
    tags=["Notes"],
    summary="Update note"
)
def update_note(
    note_id: int,
    note_update: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update the title/content of a note."""
    note = (
        db.query(models.Note)
        .filter(
            models.Note.id == note_id,
            models.Note.owner_id == current_user.id
        )
        .first()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note_update.title is not None:
        note.title = note_update.title
    if note_update.content is not None:
        note.content = note_update.content
    db.commit()
    db.refresh(note)
    return note


# PUBLIC_INTERFACE
@router.delete(
    "/notes/{note_id}",
    response_model=dict,
    tags=["Notes"],
    summary="Delete note"
)
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete a note; only allowed if owned by current user."""
    note = (
        db.query(models.Note)
        .filter(
            models.Note.id == note_id,
            models.Note.owner_id == current_user.id
        )
        .first()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
    return {"message": "Note deleted"}
