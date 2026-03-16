"""
routers/faction.py — Frakce: info, výběr, změna, reputace, odměny
"""
import json
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from database import get_db
from models.economy import log_gold, GoldReason
from models.user import User
from models.character import Character
from models.faction import FactionReputation
from game.factions import FACTIONS, FACTION_REWARDS, RENOWN_TIERS
from routers.auth import get_current_user
from routers.character import char_dict_with_equipment

router = APIRouter(prefix="/faction", tags=["faction"])


class ChooseFactionRequest(BaseModel):
    faction:        str
    confirm_reset:  bool = False  # True = hráč potvrdil ztrátu starého progressu


async def _get_char(user: User, db: AsyncSession) -> Character:
    result = await db.execute(select(Character).where(Character.user_id == user.id, Character.is_dead == False))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena.")
    return char


async def _get_rep(char_id: int, db: AsyncSession) -> FactionReputation | None:
    result = await db.execute(
        select(FactionReputation).where(FactionReputation.character_id == char_id)
    )
    return result.scalar_one_or_none()


# ── Endpointy ─────────────────────────────────────────────────────────────────

@router.get("/info")
async def faction_info():
    """Vrátí statické informace o všech třech frakcích."""
    return {"factions": list(FACTIONS.values())}


@router.get("/my")
async def my_faction(
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Vrátí aktuální frakci a reputaci přihlášeného hráče."""
    char = await _get_char(user, db)

    if not char.faction:
        return {"faction": None, "reputation": None}

    rep = await _get_rep(char.id, db)
    if not rep:
        return {"faction": char.faction, "reputation": None}

    return rep.to_dict(FACTIONS[char.faction])


@router.post("/choose")
async def choose_faction(
    req:  ChooseFactionRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """
    Vybere nebo změní frakci hráče.
    Pokud hráč mění frakci (ne poprvé), musí odeslat confirm_reset=True.
    Starý progress je nenávratně ztracen.
    """
    if req.faction not in FACTIONS:
        raise HTTPException(400, f"Neplatná frakce. Možnosti: {list(FACTIONS.keys())}")

    char = await _get_char(user, db)

    # Hráč mění frakci (ne výběr poprvé)
    if char.faction and char.faction != req.faction:
        if not req.confirm_reset:
            old_name = FACTIONS[char.faction]["name"]
            raise HTTPException(
                400,
                {
                    "code":                 "CONFIRM_RESET",
                    "message":              f"Změnou frakce ztratíš veškerý progress s '{old_name}'.",
                    "current_faction":      char.faction,
                    "current_faction_name": old_name,
                },
            )
        # Smaž starý reputation record
        old_rep = await _get_rep(char.id, db)
        if old_rep:
            await db.delete(old_rep)
        await db.flush()

    # Nastav novou frakci na postavě
    char.faction = req.faction

    # Vytvoř nový reputation record pokud ještě neexistuje
    rep = await _get_rep(char.id, db)
    if not rep:
        rep = FactionReputation(
            character_id=char.id,
            faction=req.faction,
            reputation=0,
        )
        db.add(rep)

    await db.commit()
    await db.refresh(char)
    await db.refresh(rep)

    faction_data = FACTIONS[req.faction]
    return {
        "message":   f"Přidal ses k frakci '{faction_data['name']}'!",
        "faction":   rep.to_dict(faction_data),
        "character": await char_dict_with_equipment(char, db),
    }


@router.post("/claim/{tier_id}")
async def claim_reward(
    tier_id: int,
    user:    User = Depends(get_current_user),
    db:      AsyncSession = Depends(get_db),
):
    """Nárokuje odměnu za dosažení daného renown tieru."""
    char = await _get_char(user, db)

    if not char.faction:
        raise HTTPException(400, "Nemáš zvolenou frakci.")

    rep = await _get_rep(char.id, db)
    if not rep:
        raise HTTPException(400, "Chybí frakční data — zvol frakci znovu.")

    # Validace tieru
    tier_data = next((t for t in RENOWN_TIERS if t[0] == tier_id), None)
    if not tier_data or tier_id == 1:
        raise HTTPException(404, "Tier nenalezen nebo nemá odměnu.")

    if rep.reputation < tier_data[1]:
        raise HTTPException(
            400,
            f"Nemáš dostatek reputace. Potřebuješ {tier_data[1]}, máš {rep.reputation}."
        )

    claimed = rep.get_claimed_tiers()
    if tier_id in claimed:
        raise HTTPException(400, "Tuto odměnu jsi již převzal.")

    # Zjisti odměnu pro tuto frakci a tier
    reward = FACTION_REWARDS.get(char.faction, {}).get(tier_id)
    if not reward:
        raise HTTPException(404, "Odměna pro tento tier nenalezena.")

    # ── Udělej odměnu ──────────────────────────────────────────────────────────
    reward_msg = ""

    if reward["type"] == "gold":
        char.gold += reward["amount"]
        await log_gold(db, char, reward["amount"], GoldReason.FACTION_REWARD,
                       {"tier_id": tier_id})
        reward_msg = f"+{reward['amount']} Zlatých"

    elif reward["type"] == "title":
        rep.add_unlocked_title(reward["title"])
        reward_msg = f"Titul: [{reward['title']}]"

    elif reward["type"] == "elixir":
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=reward["duration_days"])
        bonuses = reward["bonuses"]
        char.add_buff(
            name=reward["name"],
            expires_at=expires_at,
            bonus_str=bonuses.get("bonus_str", 0),
            bonus_dex=bonuses.get("bonus_dex", 0),
            bonus_int=bonuses.get("bonus_int", 0),
            bonus_end=bonuses.get("bonus_end", 0),
            bonus_luck=bonuses.get("bonus_luck", 0),
        )
        char.recalculate_stats()
        reward_msg = reward["label"]

    elif reward["type"] == "title_gold":
        rep.add_unlocked_title(reward["title"])
        char.gold += reward["bonus_gold"]
        await log_gold(db, char, reward["bonus_gold"], GoldReason.FACTION_REWARD,
                       {"tier_id": tier_id, "title": reward["title"]})
        reward_msg = f"Titul: [{reward['title']}] + {reward['bonus_gold']} Zlatých"

    # Označ tier jako collected
    claimed.append(tier_id)
    rep.set_claimed_tiers(claimed)

    await db.commit()

    faction_data = FACTIONS[char.faction]
    return {
        "message":   f"Odměna za stupeň '{tier_data[2]}' převzata: {reward_msg}",
        "reward":    reward,
        "reward_msg": reward_msg,
        "faction":   rep.to_dict(faction_data),
        "character": await char_dict_with_equipment(char, db),
    }
