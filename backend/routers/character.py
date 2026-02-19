"""
routers/character.py — Tvorba a správa postavy
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import re

from database import get_db
from models.user import User
from models.character import Character, CharacterClass, CLASS_BASE_STATS
from models.item import Item
from models.quest import Quest, QuestStatus
from routers.auth import get_current_user

router = APIRouter(prefix="/character", tags=["character"])

EQUIPMENT_SLOTS = {
    "weapon": "eq_weapon",
    "helmet": "eq_helmet",
    "armor":  "eq_armor",
    "gloves": "eq_gloves",
    "boots":  "eq_boots",
    "ring":   "eq_ring",
    "amulet": "eq_amulet",
}

async def char_dict_with_equipment(char: Character, db: AsyncSession) -> dict:
    """Vrátí char.to_dict() s plnými daty nasazených itemů místo jen ID."""
    data = char.to_dict()
    equipped = {}
    for slot, attr in EQUIPMENT_SLOTS.items():
        item_id = getattr(char, attr)
        if item_id is not None:
            res = await db.execute(select(Item).where(Item.id == item_id))
            item = res.scalar_one_or_none()
            equipped[slot] = item.to_dict() if item else None
        else:
            equipped[slot] = None
    data["equipment"] = equipped
    return data

VALID_STATS = {"strength", "dexterity", "intelligence", "endurance", "luck"}

STAT_CZ = {
    "strength": "Síla", "dexterity": "Obratnost",
    "intelligence": "Inteligence", "endurance": "Výdrž", "luck": "Štěstí",
}

async def _get_char(user: User, db: AsyncSession) -> Character:
    result = await db.execute(select(Character).where(Character.user_id == user.id))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena.")
    return char

# ── Schemas ───────────────────────────────────────────────────────────────────
class CreateCharacterRequest(BaseModel):
    name: str
    cls: str  # warrior / mage / ranger

class AllocateStatRequest(BaseModel):
    stat: str  # strength / dexterity / intelligence / endurance / luck

# ── Endpointy ─────────────────────────────────────────────────────────────────
@router.post("/create", status_code=201)
async def create_character(
    req: CreateCharacterRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validace jména
    if not re.match(r"^[a-zA-ZáčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-zA-ZáčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ0-9_ ]{1,30}$", req.name):
        raise HTTPException(400, "Jméno musí být 2–32 znaků")

    # Validace třídy
    try:
        cls = CharacterClass(req.cls.lower())
    except ValueError:
        raise HTTPException(400, f"Neplatná třída. Možnosti: {[c.value for c in CharacterClass]}")

    # Jeden hráč = jedna postava
    existing = await db.execute(select(Character).where(Character.user_id == user.id))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Již máš postavu. Jeden účet = jedna postava.")

    # Unikátní jméno
    name_taken = await db.execute(select(Character).where(Character.name == req.name))
    if name_taken.scalar_one_or_none():
        raise HTTPException(400, "Toto jméno je již obsazeno, zvol jiné.")

    base = CLASS_BASE_STATS[cls]
    char = Character(
        user_id=user.id,
        name=req.name,
        cls=cls.value,
        level=1, xp=0, gold=150,
        strength=base["strength"],
        dexterity=base["dexterity"],
        intelligence=base["intelligence"],
        endurance=base["endurance"],
        luck=base["luck"],
    )
    char.recalculate_stats()
    db.add(char)
    await db.flush()  # získáme char.id

    # Vytvoř quest slot
    quest = Quest(character_id=char.id, status=QuestStatus.IDLE)
    db.add(quest)

    await db.commit()
    await db.refresh(char)

    return {"message": "Postava vytvořena!", "character": await char_dict_with_equipment(char, db)}

@router.get("/me")
async def get_my_character(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Character).where(Character.user_id == user.id))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena — nejprve si vytvoř postavu.")
    return await char_dict_with_equipment(char, db)

@router.get("/classes")
async def get_classes():
    """Vrátí info o všech třídách pro výběr při tvorbě postavy."""
    return {
        cls.value: {
            **data,
            "class": cls.value,
        }
        for cls, data in CLASS_BASE_STATS.items()
    }

@router.post("/allocate-stat")
async def allocate_stat(
    req: AllocateStatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Utratí 1 stat bod za zvýšení vybraného primárního atributu."""
    char = await _get_char(user, db)

    if req.stat not in VALID_STATS:
        raise HTTPException(400, f"Neplatný atribut. Povolené: {', '.join(sorted(VALID_STATS))}")

    if (char.stat_points or 0) <= 0:
        raise HTTPException(400, "Nemáš žádné volné stat body.")

    setattr(char, req.stat, getattr(char, req.stat) + 1)
    char.stat_points = (char.stat_points or 0) - 1

    # Přepočítej stats včetně equipu
    from routers.inventory import recalculate_with_gear
    await recalculate_with_gear(char, db)
    await db.commit()

    stat_name = STAT_CZ.get(req.stat, req.stat)
    return {
        "message": f"+1 {stat_name}! Zbývá {char.stat_points} bodů.",
        "stat_points_remaining": char.stat_points,
        "character": await char_dict_with_equipment(char, db),
    }


@router.get("/leaderboard")
async def leaderboard(db: AsyncSession = Depends(get_db)):
    """Top 20 hráčů podle levelu a XP."""
    result = await db.execute(
        select(Character)
        .order_by(Character.level.desc(), Character.xp.desc())
        .limit(20)
    )
    chars = result.scalars().all()
    return [
        {
            "rank": i + 1,
            "name": c.name,
            "cls": c.cls,
            "level": c.level,
            "arena_rank": c.arena_rank,
        }
        for i, c in enumerate(chars)
    ]
