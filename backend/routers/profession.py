"""
routers/profession.py — Profese v3 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.profession import CharacterProfession, PROFESSION_KEYS, PROFESSION_META
from game.professions import (
    get_char, get_profession,
    do_disenchant, do_enchant, do_craft_scroll,
    do_brew, do_dissolve,
    do_destroy, do_upgrade,
    BREW_RECIPES, DISENCHANT_OUTPUTS, ENCHANT_COSTS, DISSOLVE_OUTPUTS,
    DESTROY_OUTPUTS, UPGRADE_RECIPES, CRAFT_SCROLL_COST,
    BASIC_ENCHANT_EFFECTS, SIGNATURE_ENCHANT_EFFECTS,
)
from routers.auth import get_current_user

router = APIRouter(prefix="/professions", tags=["professions"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class ChooseRequest(BaseModel):
    profession_key: str

class EnchantRequest(BaseModel):
    inventory_item_id: int
    effect: str  # atk | def | hp | lifesteal | reflect | crit_bonus

class DisenchantRequest(BaseModel):
    inventory_item_id: int

class BrewRequest(BaseModel):
    recipe: str

class DissolveRequest(BaseModel):
    inventory_item_id: int

class DestroyRequest(BaseModel):
    inventory_item_id: int

class UpgradeRequest(BaseModel):
    inventory_item_id: int


# ── Endpointy ─────────────────────────────────────────────────────────────────

@router.get("/")
async def list_professions(
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Přehled všech 3 profesí + aktuální volba hráče."""
    char = await get_char(user, db)
    current = await get_profession(char.id, db)

    professions = []
    for key in PROFESSION_KEYS:
        meta = PROFESSION_META[key]
        if current and current.profession_key == key:
            professions.append({**current.to_dict(), "status": "chosen"})
        else:
            professions.append({
                "profession_key": key,
                "name":          meta["name"],
                "icon":          meta["icon"],
                "description":   meta["description"],
                "rank":          0,
                "rank_name":     "Novic",
                "xp":            0,
                "xp_to_next":    100,
                "chosen_at":     None,
                "status":        "locked" if current else "available",
            })
    return {
        "professions":    professions,
        "has_profession": current is not None,
        "current":        current.to_dict() if current else None,
    }


@router.post("/choose")
async def choose_profession(
    req: ChooseRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Zvol profesi (jednou navždy)."""
    char = await get_char(user, db)
    existing = await get_profession(char.id, db)
    if existing:
        raise HTTPException(400, f"Profesi nelze změnit. Máš: '{existing.profession_key}'.")
    if req.profession_key not in PROFESSION_KEYS:
        raise HTTPException(400, f"Neznámá profese '{req.profession_key}'.")

    prof = CharacterProfession(
        character_id=char.id,
        profession_key=req.profession_key,
    )
    db.add(prof)
    await db.commit()
    await db.refresh(prof)

    meta = PROFESSION_META[req.profession_key]
    return {
        "message":    f"Zvolil sis profesi '{meta['name']}'!",
        "profession": prof.to_dict(),
    }


@router.post("/enchant")
async def enchant_item(
    req: EnchantRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    char = await get_char(user, db)
    result = await do_enchant(char.id, req.inventory_item_id, req.effect, db)
    await db.commit()
    return result


@router.post("/disenchant")
async def disenchant_item(
    req: DisenchantRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    char = await get_char(user, db)
    result = await do_disenchant(char.id, req.inventory_item_id, db)
    await db.commit()
    return result


@router.post("/craft-scroll")
async def craft_enchant_scroll(
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    char = await get_char(user, db)
    result = await do_craft_scroll(char.id, db)
    await db.commit()
    return result


@router.post("/brew")
async def brew_potion(
    req: BrewRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    char = await get_char(user, db)
    result = await do_brew(char.id, req.recipe, db)
    await db.commit()
    return result


@router.post("/dissolve")
async def dissolve_potion(
    req: DissolveRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    char = await get_char(user, db)
    result = await do_dissolve(char.id, req.inventory_item_id, db)
    await db.commit()
    return result


@router.post("/destroy")
async def destroy_item(
    req: DestroyRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    char = await get_char(user, db)
    result = await do_destroy(char.id, req.inventory_item_id, db)
    await db.commit()
    return result


@router.post("/upgrade")
async def upgrade_item(
    req: UpgradeRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    char = await get_char(user, db)
    result = await do_upgrade(char.id, req.inventory_item_id, db)
    await db.commit()
    return result


@router.get("/recipes")
async def get_recipes(
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Recepty pro aktuální profesi hráče."""
    char = await get_char(user, db)
    from game.professions import get_profession as _gp
    prof = await _gp(char.id, db)
    if not prof:
        return {"recipes": [], "profession": None}

    key = prof.profession_key
    recipes = {}

    if key == "enchanter":
        recipes = {
            "disenchant": DISENCHANT_OUTPUTS,
            "enchant":    {
                "costs_by_rarity": ENCHANT_COSTS,
                "basic_effects":   BASIC_ENCHANT_EFFECTS,
                "signature_effects": SIGNATURE_ENCHANT_EFFECTS,
                "craft_scroll_cost": CRAFT_SCROLL_COST,
            },
        }
    elif key == "alchymista":
        recipes = {
            "brew":    BREW_RECIPES,
            "dissolve": DISSOLVE_OUTPUTS,
        }
    elif key == "blacksmith":
        recipes = {
            "destroy": DESTROY_OUTPUTS,
            "upgrade": UPGRADE_RECIPES,
        }

    return {"recipes": recipes, "profession": prof.to_dict()}
