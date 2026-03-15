"""
models/crystal.py — Crystal currency (earned premium), Crystal Shop definitions
"""
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


# ── Crystal Shop katalog ──────────────────────────────────────────────────────
CRYSTAL_SHOP: dict[str, dict] = {
    "xp_boost_24h": {
        "name":        "Posílení XP (24h)",
        "emoji":       "⚡",
        "description": "+25 % XP z questů na 24 hodin. Lze skládat — každý nákup přidá dalších 24h.",
        "cost":        300,
        "type":        "consumable",    # lze kupovat opakovaně
    },
    "name_color_gold": {
        "name":        "Zlatá barva jména",
        "emoji":       "✨",
        "description": "Tvoje jméno svítí zlatě v celé hře.",
        "cost":        250,
        "color":       "#ffd700",
        "type":        "name_color",    # přepíše předchozí barvu
    },
    "name_color_crimson": {
        "name":        "Krvavá barva jména",
        "emoji":       "🔴",
        "description": "Tvoje jméno svítí krvavě červeně.",
        "cost":        250,
        "color":       "#dc143c",
        "type":        "name_color",
    },
    "name_color_azure": {
        "name":        "Azurová barva jména",
        "emoji":       "💎",
        "description": "Tvoje jméno svítí azurově modře.",
        "cost":        250,
        "color":       "#00bfff",
        "type":        "name_color",
    },
    "portrait_frame_bronze": {
        "name":        "Bronzový rám portrétu",
        "emoji":       "🟫",
        "description": "Solidní bronzový rám — základ každého hrdiny.",
        "cost":        100,
        "frame":       "bronze",
        "type":        "portrait_frame",
    },
    "portrait_frame_silver": {
        "name":        "Stříbrný rám portrétu",
        "emoji":       "🖼",
        "description": "Elegantní stříbrný rám okolo tvého portrétu.",
        "cost":        150,
        "frame":       "silver",
        "type":        "portrait_frame",  # přepíše předchozí rám
    },
    "portrait_frame_gold": {
        "name":        "Zlatý rám portrétu",
        "emoji":       "👑",
        "description": "Impozantní zlatý rám okolo tvého portrétu.",
        "cost":        250,
        "frame":       "gold",
        "type":        "portrait_frame",
    },
    "portrait_frame_arcane": {
        "name":        "Arkánný rám portrétu",
        "emoji":       "🔮",
        "description": "Mystický rám pulzující arkánnou energií. Záře nikdy neuhasne.",
        "cost":        350,
        "frame":       "arcane",
        "type":        "portrait_frame",
    },
    "portrait_frame_ruby": {
        "name":        "Rubínový rám portrétu",
        "emoji":       "🔴",
        "description": "Planoucí rubínový rám pro nejodvážnější válečníky.",
        "cost":        400,
        "frame":       "ruby",
        "type":        "portrait_frame",
    },
    "portrait_frame_legendary": {
        "name":        "Legendární rám portrétu",
        "emoji":       "⭐",
        "description": "Duhová záře legendy. Pouze pro ty nejlepší hrdiny.",
        "cost":        500,
        "frame":       "legendary",
        "type":        "portrait_frame",
    },
}

# Zdroje krystalů (informativní popis pro UI)
CRYSTAL_EARN_SOURCES = {
    "season_tier":  ("Sezónní odměna", "💎"),
    "achievement":  ("Achievement",    "🏆"),
    "event":        ("Událost",        "🎉"),
    "admin":        ("Admin dar",      "⚙"),
}


# ── Crystal transakční log ────────────────────────────────────────────────────
class CrystalTransaction(Base):
    __tablename__ = "crystal_transactions"

    id:            Mapped[int]      = mapped_column(Integer, primary_key=True)
    character_id:  Mapped[int]      = mapped_column(
        Integer, __import__('sqlalchemy').ForeignKey("characters.id")
    )
    amount:        Mapped[int]      = mapped_column(Integer)         # + = earned, - = spent
    reason:        Mapped[str]      = mapped_column(String(64))
    timestamp:     Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    balance_after: Mapped[int]      = mapped_column(Integer)
