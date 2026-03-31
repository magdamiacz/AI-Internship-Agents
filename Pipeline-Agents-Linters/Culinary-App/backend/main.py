import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from agent import run_agent
from database import (
    create_user,
    get_all_recipes,
    get_recipe_by_id,
    get_user_by_email,
    get_user_by_id,
    init_db,
    update_user_hashed_password,
)
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from security import hash_password, verify_password

logger = logging.getLogger(__name__)

JWT_SECRET = os.getenv("JWT_SECRET", "myjwtsecret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440
JWT_ISSUER = "culinary-app"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=32000)
    thread_id: str = Field(..., max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str


class RegisterBody(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=72)
    confirm_password: str = Field(..., min_length=6, max_length=72)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v):
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class User(BaseModel):
    id: int
    email: str


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=15)
    to_encode["exp"] = int(expire.timestamp())
    to_encode["iat"] = int(now.timestamp())
    to_encode["iss"] = JWT_ISSUER
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[ALGORITHM],
        )
        token_iss = payload.get("iss")
        if token_iss is not None and token_iss != JWT_ISSUER:
            raise credentials_exception
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception
        user_id = int(sub)
    except (JWTError, ValueError, TypeError):
        raise credentials_exception
    user = get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user


def _validate_jwt_secret_at_startup() -> None:
    env = (os.getenv("ENV") or "").lower()
    if JWT_SECRET == "myjwtsecret" or len(JWT_SECRET) < 16:
        msg = (
            "JWT_SECRET is default or too short — set a long random secret in production "
            "(e.g. openssl rand -hex 32)."
        )
        if env == "production":
            raise RuntimeError(msg)
        logger.warning(msg)


@app.on_event("startup")
async def startup_event():
    _validate_jwt_secret_at_startup()
    pepper = (os.getenv("PASSWORD_PEPPER") or "").strip()
    if not pepper:
        logger.warning(
            "PASSWORD_PEPPER is not set — passwords use legacy bcrypt(plain) only. "
            "Set PASSWORD_PEPPER for HMAC+pepper hashing on new registrations and upgrades on login."
        )
    os.makedirs("./images", exist_ok=True)
    init_db()


@app.post("/register", response_model=Token)
async def register(body: RegisterBody):
    email = str(body.email)
    user = get_user_by_email(email)
    if user:
        raise HTTPException(status_code=400, detail="Ten adres e-mail jest już zarejestrowany")
    user = create_user(email, body.password)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_by_email(form_data.username.strip().lower())
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    ok, needs_rehash = verify_password(form_data.password, user.hashed_password)
    if not ok:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if needs_rehash:
        update_user_hashed_password(user.id, hash_password(form_data.password))
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/chat")
async def chat_endpoint(request: ChatRequest, current_user: User = Depends(get_current_user)):
    try:
        result = run_agent(request.message, request.thread_id, current_user.id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/images/{filename}")
async def get_image(filename: str):
    file_path = f"./images/{filename}"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Image not found")


@app.get("/recipes")
async def list_recipes(current_user: User = Depends(get_current_user)):
    try:
        return get_all_recipes(current_user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recipes/{recipe_id}")
async def get_recipe(recipe_id: int, current_user: User = Depends(get_current_user)):
    try:
        recipe = get_recipe_by_id(current_user.id, recipe_id)
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        return recipe
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
