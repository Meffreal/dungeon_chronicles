"""
game/professions.py — Sdílené helpery pro profesní systém.

Používají ho jednotlivé routery: award_xp, get_active_profession,
add_resonance_to_equipped_runes (volá se z quest/arena collect).
"""
import random
import string
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from models.profession import (
    CharacterProfession, PROFESSION_KEYS,
    PROFESSION_LEARN_COSTS, ACTIVE_SLOTS,
)
from models.character import Character
from models.runosmith import ItemRune, RUNE_COMBINATIONS, RUNE_COMBINATION_LOOKUP
from models.soulforger import FORGE_NAME_PREFIXES, FORGE_NAME_SUFFIXES


# ── Základní helpery ──────────────────────────────────────────────────────────

async def get_char(user, db: AsyncSession) -> Character:
    result = await db.execute(select(Character).where(Character.user_id == user.id))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Nejdřív si vytvoř postavu.")
    return char


async def get_profession(char_id: int, profession_key: str,
                         db: AsyncSession) -> CharacterProfession:
    """Vrátí CharacterProfession nebo 404."""
    result = await db.execute(
        select(CharacterProfession).where(
            CharacterProfession.character_id == char_id,
            CharacterProfession.profession_key == profession_key,
        )
    )
    prof = result.scalar_one_or_none()
    if not prof:
        raise HTTPException(404, f"Profese '{profession_key}' není naučena.")
    return prof


async def require_active_profession(char_id: int, profession_key: str,
                                    db: AsyncSession) -> CharacterProfession:
    """Vrátí profesi pouze pokud je aktivní. Jinak 403."""
    prof = await get_profession(char_id, profession_key, db)
    if not prof.is_active:
        raise HTTPException(403, f"Profese '{profession_key}' není aktivní. Aktivuj ji v menu profesí.")
    return prof


async def require_active_profession_rank(char_id: int, profession_key: str,
                                         min_rank: int, db: AsyncSession) -> CharacterProfession:
    """Vrátí aktivní profesi s alespoň min_rank. Jinak 403."""
    prof = await require_active_profession(char_id, profession_key, db)
    if prof.rank < min_rank:
        raise HTTPException(403, f"Potřebuješ Rank {min_rank} v '{profession_key}'. Aktuálně Rank {prof.rank}.")
    return prof


# ── XP award ─────────────────────────────────────────────────────────────────

async def award_xp(char_id: int, profession_key: str,
                   amount: int, db: AsyncSession) -> dict:
    """
    Přidá XP aktivní profesi. Vrátí dict s info o rank-up.
    Pokud profese není aktivní, nedělá nic a vrátí {"awarded": False}.
    """
    result = await db.execute(
        select(CharacterProfession).where(
            CharacterProfession.character_id == char_id,
            CharacterProfession.profession_key == profession_key,
            CharacterProfession.is_active == True,
        )
    )
    prof = result.scalar_one_or_none()
    if not prof or amount <= 0:
        return {"awarded": False}

    old_rank = prof.rank
    ranked_up = prof.add_xp(amount)
    return {
        "awarded":   True,
        "xp_gained": amount,
        "ranked_up": ranked_up,
        "old_rank":  old_rank,
        "new_rank":  prof.rank,
    }


# ── Profese: learn / activate logic ──────────────────────────────────────────

async def learn_cost_for_char(char_id: int, db: AsyncSession) -> int:
    """Vrátí cenu (v zlatě) za naučení další profese."""
    result = await db.execute(
        select(CharacterProfession).where(CharacterProfession.character_id == char_id)
    )
    count = len(result.scalars().all())
    if count >= len(PROFESSION_LEARN_COSTS):
        return -1   # už má všechny
    return PROFESSION_LEARN_COSTS[count]


async def get_free_slot(char_id: int, db: AsyncSession) -> int | None:
    """Vrátí číslo prvního volného aktivního slotu (1 nebo 2). None pokud jsou oba plné."""
    result = await db.execute(
        select(CharacterProfession).where(
            CharacterProfession.character_id == char_id,
            CharacterProfession.is_active == True,
        )
    )
    active = result.scalars().all()
    used_slots = {p.slot for p in active}
    for slot in range(1, ACTIVE_SLOTS + 1):
        if slot not in used_slots:
            return slot
    return None


# ── Runovník: resonance hook ──────────────────────────────────────────────────

async def add_resonance_to_equipped_runes(char: Character, amount: int,
                                           db: AsyncSession) -> list[dict]:
    """
    Volá se z quest/arena collect po každém úspěšném boji.
    Přidá rezonanci ke všem runám na nasazených předmětech hráče.
    Pokud runa dosáhne evolve prahu, přidá ji do returned listu.
    Vrátí list {rune_name, evolved_to} pro notifikace.
    """
    # Controlovat zda je Runovník aktivní
    prof_result = await db.execute(
        select(CharacterProfession).where(
            CharacterProfession.character_id == char.id,
            CharacterProfession.profession_key == "runist",
            CharacterProfession.is_active == True,
        )
    )
    if not prof_result.scalar_one_or_none():
        return []

    # Najdi inventory IDs nasazených předmětů
    equipped_item_ids = [
        x for x in [
            char.eq_weapon, char.eq_helmet, char.eq_armor,
            char.eq_gloves, char.eq_boots,  char.eq_ring, char.eq_amulet,
        ] if x is not None
    ]
    if not equipped_item_ids:
        return []

    from models.item import InventoryItem
    inv_res = await db.execute(
        select(InventoryItem).where(
            InventoryItem.character_id == char.id,
            InventoryItem.item_id.in_(equipped_item_ids),
        )
    )
    inv_items = inv_res.scalars().all()
    inv_ids = [i.id for i in inv_items]
    if not inv_ids:
        return []

    rune_res = await db.execute(
        select(ItemRune)
        .options(selectinload(ItemRune.rune))
        .where(ItemRune.inventory_item_id.in_(inv_ids))
    )
    runes = rune_res.scalars().all()

    evolved = []
    for ir in runes:
        ready = ir.add_resonance(amount)
        if ready and ir.rune and ir.rune.evolves_to:
            evolved.append({
                "rune_name":  ir.rune.name,
                "evolved_to": ir.rune.evolves_to,
            })

    return evolved


# ── Oracle: Prozření — pasivní XP bonus z questů ────────────────────────────

async def get_oracle_xp_bonus(char_id: int, base_xp: int, db: AsyncSession) -> int:
    """
    Pasivní: Oracle Rank N → +2 % base_xp za každý rank (max +10 % na rank 5).
    Vrátí bonus XP (int). 0 pokud Oracle není aktivní.
    """
    result = await db.execute(
        select(CharacterProfession).where(
            CharacterProfession.character_id == char_id,
            CharacterProfession.profession_key == "oracle",
            CharacterProfession.is_active == True,
        )
    )
    prof = result.scalar_one_or_none()
    if not prof or prof.rank <= 0:
        return 0
    bonus_pct = min(prof.rank * 2, 10)   # 2 % za rank, max 10 %
    return int(base_xp * bonus_pct / 100)


# ── Broker: Riziková prémie — pasivní gold bonus z questů ────────────────────

async def get_broker_gold_bonus(char_id: int, base_gold: int, db: AsyncSession) -> int:
    """
    Pasivní: Broker Rank N → +5 % base_gold za každý rank (max +25 % na rank 5).
    Vrátí bonus gold (int). 0 pokud Broker není aktivní.
    """
    result = await db.execute(
        select(CharacterProfession).where(
            CharacterProfession.character_id == char_id,
            CharacterProfession.profession_key == "broker",
            CharacterProfession.is_active == True,
        )
    )
    prof = result.scalar_one_or_none()
    if not prof or prof.rank <= 0:
        return 0
    bonus_pct = min(prof.rank * 5, 25)   # 5 % za rank, max 25 %
    return int(base_gold * bonus_pct / 100)


# ── Dušekoval: procedurální jméno forge výstupu ───────────────────────────────

def generate_forge_name(item_type: str, output_rarity: str) -> tuple[str, str]:
    """
    Vrátí (name, flavor_text) procedurálně vygenerované pro forged předmět.
    """
    prefix = random.choice(FORGE_NAME_PREFIXES)
    suffix = random.choice(FORGE_NAME_SUFFIXES)

    type_map = {
        "weapon": "Čepel",
        "helmet": "Přilba",
        "armor":  "Zbroj",
        "gloves": "Rukavice",
        "boots":  "Boty",
        "ring":   "Prsten",
        "amulet": "Amulet",
    }
    base = type_map.get(item_type, "Artefakt")
    name = f"{prefix} {base} {suffix}"

    flavors = [
        f"Zkován z trosek a vzpomínek. Ani stvořitel neví, co přesně v tom kovu dřímá.",
        f"Materiály se odpíraly, ale vůle Dušekovale zlomila jejich odpor.",
        f"Každá jizva na povrchu vypráví příběh svého předchozího majitele.",
        f"Cítíš cizí přítomnost kdykoli se ho dotkneš.",
        f"Výsledek zoufalství a mistrovství zároveň.",
    ]
    flavor = random.choice(flavors)
    return name, flavor


# ── Agent: generátor pseudonymů ───────────────────────────────────────────────

def generate_pseudonym() -> str:
    """Generuje unikátní pseudonym pro Agenta ve formátu 'Adjektivum Jméno'."""
    adjectives = [
        "Tichý", "Stínový", "Mlžný", "Skrytý", "Bledý",
        "Ocelový", "Temný", "Bezejmenný", "Ledový", "Zakuklený",
    ]
    names = [
        "Vrán", "Dýka", "Háv", "Stín", "Vítr",
        "Prach", "Mlha", "Ozvěna", "Číhání", "Prázdnota",
    ]
    suffix = "".join(random.choices(string.digits, k=3))
    return f"{random.choice(adjectives)} {random.choice(names)}-{suffix}"
