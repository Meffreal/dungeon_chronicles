"""
routers/fateweaver.py — Tkadlec Osudu: pouta, duchy, karma
"""
import json
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.character import Character
from models.fateweaver import (
    FateBond, BOND_TYPES, SPIRIT_TYPES,
    BOND_TARGET_COOLDOWN_HOURS, MAX_PLAYER_BONDS, MAX_SPIRIT_BONDS,
    KARMA_PER_CURSE, KARMA_PER_BLESS, FATEWEAVER_XP,
)
from models.profession import CharacterProfession, KARMA_HARD_CAP
from game.professions import get_char, require_active_profession, award_xp
from routers.auth import get_current_user

router = APIRouter(prefix="/fateweaver", tags=["fateweaver"])

# Efekty pout podle typu (base hodnoty, mohou být škálovány rankem)
BOND_EFFECTS = {
    "cooperation": {"bonus_xp_pct": 10},            # sdílené +10 % XP ze questů
    "war_pact":    {"bonus_atk_pct": 12},            # sdílený +12 % ATK v aréně
    "curse":       {"quest_success_penalty_pct": 8}, # -8 % quest success chance cíle
    "guild_bond":  {"bonus_xp_pct": 6, "bonus_atk_pct": 6},   # oslabené, ale pro 3 hráče
}


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreatePlayerBondRequest(BaseModel):
    target_a_char_id: int
    target_b_char_id: int
    bond_type:        str    # cooperation | war_pact | curse | guild_bond

class CreateSpiritBondRequest(BaseModel):
    target_char_id: int      # hráč, který získá pouto s duchem
    spirit_type:    str      # warrior | mage | ranger

class DissolveBondRequest(BaseModel):
    bond_id: int


# ── Helpery ───────────────────────────────────────────────────────────────────

async def _get_weaver_prof(char_id: int, db: AsyncSession) -> CharacterProfession:
    """Vrátí aktivní CharacterProfession pro Tkadlece."""
    return await require_active_profession(char_id, "oracle", db)


async def _check_target_cooldown(weaver_id: int, target_id: int, db: AsyncSession) -> None:
    """Zkontroluje zda uplynul cooldown pro nové pouto se stejným cílem."""
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=BOND_TARGET_COOLDOWN_HOURS)
    result = await db.execute(
        select(FateBond).where(
            FateBond.weaver_char_id == weaver_id,
            FateBond.target_a_char_id == target_id,
            FateBond.created_at >= cutoff,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(400,
            f"S tímto hráčem jsi nedávno vytvořil pouto. Cooldown: {BOND_TARGET_COOLDOWN_HOURS}h."
        )


async def _active_bond_counts(char_id: int, db: AsyncSession) -> tuple[int, int]:
    """Vrátí (počet aktivních hráčských pout, počet duchových pout)."""
    result = await db.execute(
        select(FateBond).where(
            FateBond.weaver_char_id == char_id,
            FateBond.is_active == True,
        )
    )
    bonds = result.scalars().all()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    active = [b for b in bonds if not b.is_expired]
    spirit = [b for b in active if b.spirit_type is not None]
    player = [b for b in active if b.spirit_type is None]
    return len(player), len(spirit)


# ── Endpointy ─────────────────────────────────────────────────────────────────

@router.get("/bonds")
async def my_bonds(
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Všechna aktivní pouta vytvořená tímto Tkadlecem."""
    char = await get_char(user, db)
    prof = await _get_weaver_prof(char.id, db)

    result = await db.execute(
        select(FateBond)
        .options(
            selectinload(FateBond.target_a),
            selectinload(FateBond.target_b),
        )
        .where(FateBond.weaver_char_id == char.id)
        .order_by(FateBond.created_at.desc())
    )
    bonds = result.scalars().all()
    active = [b for b in bonds if b.is_currently_active]

    player_count, spirit_count = await _active_bond_counts(char.id, db)

    return {
        "bonds":          [b.to_dict() for b in active],
        "expired_bonds":  [b.to_dict() for b in bonds if not b.is_currently_active],
        "karma":          prof.karma_points,
        "karma_soft_cap": KARMA_HARD_CAP - 5,
        "karma_hard_cap": KARMA_HARD_CAP,
        "limits": {
            "player_bonds": {"current": player_count, "max": MAX_PLAYER_BONDS},
            "spirit_bonds": {"current": spirit_count, "max": MAX_SPIRIT_BONDS},
        },
    }


@router.get("/spirits")
async def list_spirits(
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Dostupné typy duchů pro NPC pouta."""
    char = await get_char(user, db)
    await require_active_profession(char.id, "oracle", db)

    return {
        "spirits": [
            {"key": key, **data}
            for key, data in SPIRIT_TYPES.items()
        ]
    }


@router.post("/bond/player")
async def create_player_bond(
    req:  CreatePlayerBondRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """
    Vytvoří pouto mezi dvěma hráči. Tkadlec může být jedním z cílů.
    Curse generuje karmu (je-li karma >= KARMA_HARD_CAP, tvorba pout je blokována).
    """
    char = await get_char(user, db)
    prof = await _get_weaver_prof(char.id, db)

    if req.bond_type not in BOND_TYPES or req.bond_type == "ancestral":
        raise HTTPException(400, f"Neplatný typ pouta. Možnosti: {[t for t in BOND_TYPES if t != 'ancestral']}")

    # Karma blokace
    if prof.karma_blocked:
        raise HTTPException(403,
            f"Tvá karma ({prof.karma_points}) dosáhla maxima. "
            "Sebrání pout a prokletí jsou dočasně blokovány. Dokonči quest 'Smíření'."
        )

    # Ověř cíle
    for cid in (req.target_a_char_id, req.target_b_char_id):
        res = await db.execute(select(Character).where(Character.id == cid))
        if not res.scalar_one_or_none():
            raise HTTPException(404, f"Hráč ID {cid} nenalezen.")

    if req.target_a_char_id == req.target_b_char_id:
        raise HTTPException(400, "Cíle pouta musí být dva různí hráči.")

    # Cooldown check pro hlavní cíl
    await _check_target_cooldown(char.id, req.target_a_char_id, db)

    # Počet aktivních pout
    player_count, _ = await _active_bond_counts(char.id, db)
    if player_count >= MAX_PLAYER_BONDS:
        raise HTTPException(400, f"Maximálně {MAX_PLAYER_BONDS} aktivních hráčských pout.")

    # Vypočítej karma delta
    karma_delta = KARMA_PER_CURSE if req.bond_type == "curse" else KARMA_PER_BLESS
    effect = BOND_EFFECTS.get(req.bond_type, {})

    bond = FateBond.create_player_bond(
        weaver_id=char.id,
        target_a_id=req.target_a_char_id,
        target_b_id=req.target_b_char_id,
        bond_type=req.bond_type,
        effect=effect,
        karma_delta=karma_delta,
    )
    db.add(bond)

    # Aplikuj karmu na profesi Tkadlece
    prof.add_karma(karma_delta)

    # Curse dostane jiný XP klíč — oba by se jinak přičetly najednou (bug: double award)
    if req.bond_type == "curse":
        xp_result = await award_xp(char.id, "oracle", FATEWEAVER_XP["curse_delivered"], db)
    else:
        xp_result = await award_xp(char.id, "oracle", FATEWEAVER_XP["bond_created_player"], db)

    await db.commit()
    await db.refresh(bond)

    return {
        "message":    f"Pouto typu '{req.bond_type}' vytvořeno.",
        "bond":       bond.to_dict(),
        "karma":      prof.karma_points,
        "xp_result":  xp_result,
        "warning": (
            f"Karma: {prof.karma_points}/{KARMA_HARD_CAP}. "
            "Blíží se limit — prokletí se začnou obracet proti tobě."
        ) if prof.karma_penalty_active else None,
    }


@router.post("/bond/spirit")
async def create_spirit_bond(
    req:  CreateSpiritBondRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """
    Vytvoří pouto s NPC duchem. Slabší efekt, ale nevyžaduje souhlas druhého hráče.
    """
    char = await get_char(user, db)
    prof = await _get_weaver_prof(char.id, db)

    if req.spirit_type not in SPIRIT_TYPES:
        raise HTTPException(400, f"Neplatný typ ducha. Možnosti: {list(SPIRIT_TYPES.keys())}")

    # Ověř cíl
    target_res = await db.execute(select(Character).where(Character.id == req.target_char_id))
    if not target_res.scalar_one_or_none():
        raise HTTPException(404, "Cílový hráč nenalezen.")

    # Počet aktivních duchových pout
    _, spirit_count = await _active_bond_counts(char.id, db)
    if spirit_count >= MAX_SPIRIT_BONDS:
        raise HTTPException(400, f"Maximálně {MAX_SPIRIT_BONDS} aktivní duchová pouta.")

    bond = FateBond.create_spirit_bond(
        weaver_id=char.id,
        target_char_id=req.target_char_id,
        spirit_type=req.spirit_type,
    )
    db.add(bond)

    xp_result = await award_xp(char.id, "oracle", FATEWEAVER_XP["bond_created_spirit"], db)
    await db.commit()
    await db.refresh(bond)

    spirit_meta = SPIRIT_TYPES[req.spirit_type]
    return {
        "message":   f"Duch '{spirit_meta['name']}' přivolán.",
        "bond":      bond.to_dict(),
        "xp_result": xp_result,
    }


@router.delete("/bond/{bond_id}")
async def dissolve_bond(
    bond_id: int,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Rozvázání pouta na žádost (Tkadlec nebo jeden z účastníků)."""
    char = await get_char(user, db)
    await _get_weaver_prof(char.id, db)

    bond_res = await db.execute(
        select(FateBond).where(FateBond.id == bond_id)
    )
    bond = bond_res.scalar_one_or_none()
    if not bond:
        raise HTTPException(404, "Pouto nenalezeno.")

    can_dissolve = (
        bond.weaver_char_id == char.id or
        bond.target_a_char_id == char.id or
        bond.target_b_char_id == char.id
    )
    if not can_dissolve:
        raise HTTPException(403, "Toto pouto se tě netýká.")
    if not bond.is_currently_active:
        raise HTTPException(400, "Pouto již není aktivní.")

    bond.dissolve()

    xp_result = await award_xp(char.id, "oracle", FATEWEAVER_XP["bond_dissolved"], db)
    await db.commit()

    return {"message": "Pouto rozvázáno.", "xp_result": xp_result}


# ── Interní hook: kontrola pout po quest collect ─────────────────────────────

async def check_bonds_on_quest_complete(char_id: int, success: bool, db: AsyncSession) -> list[dict]:
    """
    Volá se z quest collect. Zkontroluje:
    1. Zda má cílový hráč aktivní curse od Tkadlece — penalizace již proběhla při simulation.
    2. Cooperation bond fire — když oba hráči uspějí ve stejný den.
    Vrátí list fired bonds pro notifikaci.
    """
    if not success:
        return []

    today = datetime.now(timezone.utc).replace(tzinfo=None).date()
    fired = []

    # Najdi cooperation / war_pact bonds kde je tento hráč cílem
    result = await db.execute(
        select(FateBond)
        .options(selectinload(FateBond.weaver))
        .where(
            FateBond.bond_type.in_(["cooperation", "war_pact"]),
            FateBond.is_active == True,
            (FateBond.target_a_char_id == char_id) | (FateBond.target_b_char_id == char_id),
        )
    )
    bonds = result.scalars().all()

    for bond in bonds:
        if bond.is_expired:
            continue
        # Zjednodušená fire logika: fire při každém úspěšném questu cíle
        # (plná logika by ověřovala i druhého cíle — pro MVP stačí tento přístup)
        last_fire = bond.xp_last_fire_at
        already_fired_today = last_fire and last_fire.date() == today

        if not already_fired_today:
            bond.register_fire()
            await award_xp(bond.weaver_char_id, "oracle", FATEWEAVER_XP["bond_fired"], db)
            fired.append({"bond_id": bond.id, "bond_type": bond.bond_type})

            # Milníkové XP za přežití 7/30 dní
            if bond.days_active >= 30 and not bond.xp_30d_awarded:
                await award_xp(bond.weaver_char_id, "oracle", FATEWEAVER_XP["bond_survived_30d"], db)
                bond.xp_30d_awarded = True
            elif bond.days_active >= 7 and not bond.xp_7d_awarded:
                await award_xp(bond.weaver_char_id, "oracle", FATEWEAVER_XP["bond_survived_7d"], db)
                bond.xp_7d_awarded = True

    return fired
