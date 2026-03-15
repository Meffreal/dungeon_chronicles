"""
routers/agent.py — Stínový Agent: operace, identita, counter-intel
"""
import json
import random
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.character import Character
from models.guild import Guild
from models.agent import (
    AgentOperation, AgentIdentity, SabotageEffect,
    OPERATION_TYPES, OPERATION_DURATIONS, DETECTION_CHANCE,
    AGENT_XP, IDENTITY_REVEAL_HOURS,
)
from models.profession import CharacterProfession
from game.professions import get_char, require_active_profession, award_xp, generate_pseudonym
from routers.auth import get_current_user

router = APIRouter(prefix="/agent", tags=["agent"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class StartOperationRequest(BaseModel):
    operation_type: str          # reconnaissance | infiltration | sabotage | counter_intel
    difficulty:     str = "normal"
    target_char_id: int | None = None
    target_guild_id: int | None = None
    is_phantom:     bool = False  # NPC cíl


class ToggleHardTargetRequest(BaseModel):
    enabled: bool


# ── Helpery ───────────────────────────────────────────────────────────────────

async def _get_or_create_identity(char_id: int, db: AsyncSession) -> AgentIdentity:
    result = await db.execute(
        select(AgentIdentity).where(AgentIdentity.character_id == char_id)
    )
    identity = result.scalar_one_or_none()
    if not identity:
        pseudonym = generate_pseudonym()
        # Zajisti unikátnost
        while True:
            exists = await db.execute(
                select(AgentIdentity).where(AgentIdentity.pseudonym == pseudonym)
            )
            if not exists.scalar_one_or_none():
                break
            pseudonym = generate_pseudonym()

        identity = AgentIdentity(character_id=char_id, pseudonym=pseudonym)
        db.add(identity)
        await db.flush()
    return identity


def _generate_phantom_intel(operation_type: str) -> dict:
    """Generuje fiktivní NPC intel pro Phantom Contracts."""
    if operation_type == "reconnaissance":
        return {
            "guild_name":       random.choice(["Gobliní Pakt", "Železná Pěst", "Řád Temnoty"]),
            "boss_hp_pct":      random.randint(20, 95),
            "peak_activity":    random.choice(["ráno", "odpoledne", "večer", "v noci"]),
            "member_count":     random.randint(3, 15),
            "next_attack_in_h": random.randint(2, 48),
        }
    elif operation_type == "infiltration":
        items = ["Ohnivý meč", "Stínová dýka", "Prokletý štít", "Runový krystal"]
        return {
            "hot_item":        random.choice(items),
            "avg_sell_price":  random.randint(200, 2000),
            "market_trend":    random.choice(["roste", "klesá", "stabilní"]),
            "top_seller":      f"Agent-{random.randint(100, 999)}",
        }
    elif operation_type == "sabotage":
        return {
            "target":         "NPC Questor",
            "penalty_pct":    random.randint(5, 15),
            "duration_hours": random.randint(6, 24),
        }
    return {}


def _generate_real_intel(operation_type: str, target_char: Character | None,
                          target_guild: Guild | None) -> dict:
    """Generuje skutečný intel o reálném cíli."""
    if operation_type == "reconnaissance" and target_guild:
        return {
            "guild_name":   target_guild.name,
            "member_count": len(target_guild.members) if target_guild.members else 0,
            "guild_level":  target_guild.level,
        }
    elif operation_type == "infiltration":
        return {
            "note": "Získal jsi přístup k tržním datům cíle. Zkontroluj tržiště.",
        }
    elif operation_type == "sabotage" and target_char:
        return {
            "target":         target_char.name,
            "penalty_pct":    10,
            "duration_hours": 12,
        }
    return {}


# ── Endpointy ─────────────────────────────────────────────────────────────────

@router.get("/identity")
async def my_identity(
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Vrátí pseudonym a stav krytu agenta."""
    char = await get_char(user, db)
    await require_active_profession(char.id, "broker", db)

    identity = await _get_or_create_identity(char.id, db)
    await db.commit()

    prof_res = await db.execute(
        select(CharacterProfession).where(
            CharacterProfession.character_id == char.id,
            CharacterProfession.profession_key == "broker",
        )
    )
    prof = prof_res.scalar_one_or_none()

    return {
        "identity":    identity.to_dict(),
        "cover_xp_milestones": {
            "7d_awarded":  identity.cover_7d_xp_awarded,
            "30d_awarded": identity.cover_30d_xp_awarded,
            "7d_xp":       AGENT_XP["cover_7_days"],
            "30d_xp":      AGENT_XP["cover_30_days"],
        },
    }


@router.post("/identity/toggle-hard-target")
async def toggle_hard_target(
    req:  ToggleHardTargetRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Přepne opt-in jako 'tvrdý cíl' — ostatní Agenti tě mohou napadnout za odměny."""
    char = await get_char(user, db)
    identity = await _get_or_create_identity(char.id, db)
    identity.is_hard_target = req.enabled
    await db.commit()

    status = "aktivní" if req.enabled else "neaktivní"
    return {"message": f"Hard target: {status}.", "is_hard_target": req.enabled}


@router.get("/operations")
async def my_operations(
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Aktivní a nedávné dokončené operace."""
    char = await get_char(user, db)
    await require_active_profession(char.id, "broker", db)

    result = await db.execute(
        select(AgentOperation)
        .where(AgentOperation.agent_char_id == char.id)
        .order_by(AgentOperation.started_at.desc())
        .limit(20)
    )
    ops = result.scalars().all()
    return {"operations": [o.to_dict() for o in ops]}


@router.get("/targets")
async def available_targets(
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """
    Vrátí dostupné cíle: hráči kteří jsou 'hard targets' + phantom targets.
    """
    char = await get_char(user, db)
    await require_active_profession(char.id, "broker", db)

    # Reální hard-target hráči
    ht_res = await db.execute(
        select(AgentIdentity)
        .options(selectinload(AgentIdentity.character))
        .where(
            AgentIdentity.is_hard_target == True,
            AgentIdentity.character_id != char.id,
        )
    )
    hard_targets = ht_res.scalars().all()

    # Phantom targets (NPC)
    phantom_names = ["Gobliní Pakt", "Železná Pěst", "Řád Temnoty", "Stínový Kruh"]
    phantoms = [
        {"name": name, "type": "phantom", "difficulty_options": ["easy", "normal", "hard"]}
        for name in phantom_names
    ]

    return {
        "real_targets": [
            {
                "char_id":   ht.character_id,
                "char_name": ht.character.name if ht.character else "?",
                "pseudonym": ht.pseudonym if not ht.is_currently_revealed else "ODHALENO",
            }
            for ht in hard_targets
        ],
        "phantom_targets": phantoms,
    }


@router.post("/operations/start")
async def start_operation(
    req:  StartOperationRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """
    Spustí novou operaci. Max 1 aktivní operace najednou.
    Čas do dokončení závisí na obtížnosti.
    """
    char = await get_char(user, db)
    prof = await require_active_profession(char.id, "broker", db)

    if req.operation_type not in OPERATION_TYPES:
        raise HTTPException(400, f"Neplatný typ operace. Možnosti: {OPERATION_TYPES}")
    if req.difficulty not in ("easy", "normal", "hard"):
        raise HTTPException(400, "Obtížnost musí být easy | normal | hard.")

    # Max 1 aktivní operace
    active_res = await db.execute(
        select(AgentOperation).where(
            AgentOperation.agent_char_id == char.id,
            AgentOperation.status == "active",
        )
    )
    if active_res.scalar_one_or_none():
        raise HTTPException(400, "Máš již probíhající operaci. Dokončit nebo seberou výsledky.")

    # Ověř cíl
    target_char = None
    target_guild = None

    if not req.is_phantom:
        if req.target_char_id:
            tc_res = await db.execute(select(Character).where(Character.id == req.target_char_id))
            target_char = tc_res.scalar_one_or_none()
            if not target_char:
                raise HTTPException(404, "Cílový hráč nenalezen.")
        if req.target_guild_id:
            tg_res = await db.execute(select(Guild).where(Guild.id == req.target_guild_id))
            target_guild = tg_res.scalar_one_or_none()
            if not target_guild:
                raise HTTPException(404, "Cílový cech nenalezen.")

    # Ensure identity exists
    await _get_or_create_identity(char.id, db)

    # Časování
    dur = OPERATION_DURATIONS[req.difficulty]
    minutes = random.randint(dur["min"], dur["max"])
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    finish_at = now + timedelta(minutes=minutes)

    op = AgentOperation(
        agent_char_id=char.id,
        operation_type=req.operation_type,
        difficulty=req.difficulty,
        target_char_id=req.target_char_id if not req.is_phantom else None,
        target_guild_id=req.target_guild_id if not req.is_phantom else None,
        is_phantom=req.is_phantom,
        started_at=now,
        finish_at=finish_at,
        status="active",
    )
    db.add(op)
    await db.commit()
    await db.refresh(op)

    return {
        "message":   f"Operace '{req.operation_type}' zahájena.",
        "operation": op.to_dict(),
    }


@router.post("/operations/{op_id}/collect")
async def collect_operation(
    op_id: int,
    user:  User = Depends(get_current_user),
    db:    AsyncSession = Depends(get_db),
):
    """
    Sebrání výsledků dokončené operace.
    Systém rozhodne o detekci a vygeneruje intel.
    """
    char = await get_char(user, db)
    prof = await require_active_profession(char.id, "broker", db)

    op_res = await db.execute(
        select(AgentOperation)
        .options(selectinload(AgentOperation.target_char))
        .where(AgentOperation.id == op_id, AgentOperation.agent_char_id == char.id)
    )
    op = op_res.scalar_one_or_none()
    if not op:
        raise HTTPException(404, "Operace nenalezena.")
    if op.status != "active":
        raise HTTPException(400, "Operace již byla sebrána nebo selhala.")
    if not op.is_finished:
        raise HTTPException(400, f"Operace ještě není hotova. Zbývá {op.seconds_remaining}s.")

    # Rozhodnutí o detekci
    detect_chances = DETECTION_CHANCE[op.difficulty]
    detect_chance  = detect_chances[min(prof.rank, len(detect_chances) - 1)]
    was_detected   = random.random() < detect_chance

    # Generuj intel
    if op.is_phantom:
        intel = _generate_phantom_intel(op.operation_type)
    else:
        target_guild_res = None
        if op.target_guild_id:
            tg_res = await db.execute(
                select(Guild)
                .options(selectinload(Guild.members))
                .where(Guild.id == op.target_guild_id)
            )
            target_guild_res = tg_res.scalar_one_or_none()
        intel = _generate_real_intel(op.operation_type, op.target_char, target_guild_res)

    # Sabotáž: aplikuj efekt na cíl (pokud nedetekován)
    if op.operation_type == "sabotage" and not was_detected and op.target_char_id:
        sabotage = SabotageEffect(
            target_char_id=op.target_char_id,
            agent_char_id=char.id,
            operation_id=op.id,
            fail_penalty_pct=intel.get("penalty_pct", 10),
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=intel.get("duration_hours", 12)),
        )
        db.add(sabotage)

    op.status       = "detected" if was_detected else "completed"
    op.was_detected = was_detected
    op.intel_result_json = json.dumps(intel, ensure_ascii=False)
    op.collected_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # XP
    xp_result = {"awarded": False}
    if not op.xp_awarded:
        if was_detected:
            xp_key = "operation_detected"
            xp_amt = AGENT_XP[xp_key]
        else:
            xp_key = f"operation_success_{op.difficulty}"
            if op.is_phantom:
                xp_key = f"phantom_{op.difficulty}"
            xp_amt = AGENT_XP.get(xp_key, AGENT_XP["operation_success_normal"])
        xp_result = await award_xp(char.id, "broker", xp_amt, db)
        op.xp_awarded = True

    # Odhalení identity (při detekci)
    if was_detected:
        identity = await _get_or_create_identity(char.id, db)
        identity.reveal()

    # Cover milníkové XP
    identity = await _get_or_create_identity(char.id, db)
    cover_xp = {"awarded": False}
    if not was_detected:
        if identity.cover_days >= 30 and not identity.cover_30d_xp_awarded:
            cover_xp = await award_xp(char.id, "broker", AGENT_XP["cover_30_days"], db)
            identity.cover_30d_xp_awarded = True
        elif identity.cover_days >= 7 and not identity.cover_7d_xp_awarded:
            cover_xp = await award_xp(char.id, "broker", AGENT_XP["cover_7_days"], db)
            identity.cover_7d_xp_awarded = True

    await db.commit()

    return {
        "success":      not was_detected,
        "was_detected": was_detected,
        "intel":        intel,
        "operation":    op.to_dict(),
        "xp_result":    xp_result,
        "cover_xp":     cover_xp,
        "message": (
            "Operace úspěšná. Intel sebrán."
            if not was_detected else
            "Byl jsi odhalen! Tvá identita je kompromitována na 72 hodin."
        ),
    }
