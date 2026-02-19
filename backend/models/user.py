"""
models/user.py — User účet
"""
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id:           Mapped[int]  = mapped_column(primary_key=True)
    username:     Mapped[str]  = mapped_column(String(32), unique=True, index=True)
    email:        Mapped[str]  = mapped_column(String(128), unique=True, index=True)
    password_hash:Mapped[str]  = mapped_column(String(256))
    is_active:    Mapped[bool] = mapped_column(Boolean, default=True)
    created_at:   Mapped[str]  = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login:   Mapped[str]  = mapped_column(DateTime(timezone=True), nullable=True)

    # Vztahy
    character = relationship("Character", back_populates="user", uselist=False)
