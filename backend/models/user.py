"""
models/user.py — User účet
"""
from datetime import datetime
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
    last_seen:    Mapped[str]  = mapped_column(DateTime(timezone=True), nullable=True)

    # GDPR account management
    is_deleted:   Mapped[bool]           = mapped_column(Boolean, default=False, server_default="0")
    deleted_at:   Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    anonymized:   Mapped[bool]           = mapped_column(Boolean, default=False, server_default="0")

    # Vztahy
    character = relationship("Character", back_populates="user", uselist=False)
