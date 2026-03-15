"""
routers/auth.py — Registrace, přihlášení, JWT
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sqlfunc
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel, EmailStr, field_validator
import re

from database import get_db
from models.user import User
from config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ── Pydantic schemas ──────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v):
        if not re.match(r"^[a-zA-Z0-9_]{3,32}$", v):
            raise ValueError("Uživatelské jméno musí být 3–32 znaků (a-z, 0-9, _)")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v):
        if len(v) < 6:
            raise ValueError("Heslo musí mít alespoň 6 znaků")
        return v

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    username: str
    has_character: bool

# ── Helpers ───────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt(rounds=12)).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    pw = plain.encode("utf-8")[:72]
    return bcrypt.checkpw(pw, hashed.encode("utf-8"))

def create_token(user_id: int, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {"sub": str(user_id), "username": username, "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Neplatný nebo expirovaný token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise credentials_exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exc
    return user

# ── Endpointy ─────────────────────────────────────────────────────────────────
@router.post("/register", status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Kontrola duplicit
    existing = await db.execute(
        select(User).where(
            (User.username == req.username) | (User.email == req.email)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Uživatelské jméno nebo email již existuje")

    user = User(
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_token(user.id, user.username)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        username=user.username,
        has_character=False,
    )

@router.post("/login")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == form.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Špatné jméno nebo heslo",
        )

    # Update last_login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    # Má charakter? + login streak tracking
    from models.character import Character
    from models.crystal import CrystalTransaction
    ch_result = await db.execute(
        select(Character).where(Character.user_id == user.id)
    )
    char = ch_result.scalar_one_or_none()
    has_char = char is not None

    if char:
        today = datetime.now(timezone.utc).date()
        today_str = today.isoformat()
        yesterday_str = (today - timedelta(days=1)).isoformat()
        last = char.last_login_date

        if last == today_str:
            pass  # Již přihlášen dnes — bez změny
        elif last == yesterday_str:
            char.login_streak = (char.login_streak or 0) + 1
            char.last_login_date = today_str
        else:
            char.login_streak = 1
            char.last_login_date = today_str

        # Crystal milestone odměny
        streak = char.login_streak or 0
        bonus = 0
        reason = ""
        if streak > 0 and streak % 30 == 0:
            bonus = 50
            reason = f"login_streak:{streak}"
        elif streak > 0 and streak % 7 == 0:
            bonus = 20
            reason = f"login_streak:{streak}"

        if bonus > 0:
            char.crystals = (char.crystals or 0) + bonus
            db.add(CrystalTransaction(
                character_id=char.id,
                amount=bonus,
                reason=reason,
                balance_after=char.crystals,
            ))

        await db.commit()

    token = create_token(user.id, user.username)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        username=user.username,
        has_character=has_char,
    )

@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username}

@router.post("/heartbeat")
async def heartbeat(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aktualizuje last_seen a vrátí počet online hráčů (aktivní za posledních 5 minut)."""
    now = datetime.now(timezone.utc)
    current_user.last_seen = now
    await db.commit()

    cutoff = now - timedelta(minutes=5)
    result = await db.execute(
        select(sqlfunc.count(User.id)).where(
            User.is_active == True,
            User.last_seen >= cutoff,
        )
    )
    online_count = result.scalar_one()
    return {"online": online_count}
