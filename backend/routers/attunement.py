"""
routers/attunement.py — Attunement systém (vstupenky do dungeonů)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.user import User
from models.character import Character
from models.quest import QUEST_DEFINITIONS
from models.attunement import ATTUNEMENT_CHAINS, QUEST_CHAIN_MAP
from routers.auth import get_current_user

router = APIRouter(prefix="/attunement", tags=["attunement"])

# Rychlý lookup quest definice
_QDEF = {q[0]: q for q in QUEST_DEFINITIONS}


@router.get("/progress")
async def get_progress(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí stav všech attunement chainů pro přihlášeného hráče."""
    result = await db.execute(select(Character).where(Character.user_id == user.id))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Nejdřív si vytvoř postavu.")

    attunements = char.get_attunements()
    progress    = char.get_attunement_progress()

    chains = []
    for chain in ATTUNEMENT_CHAINS:
        cid              = str(chain["id"])
        completed_ids    = progress.get(cid, [])
        completed_steps  = len(completed_ids)
        total_steps      = len(chain["quest_ids"])
        unlocked         = chain["id"] in attunements

        # Sestroj detail jednotlivých kroků
        steps = []
        for step_idx, qid in enumerate(chain["quest_ids"], 1):
            qdef = _QDEF.get(qid)
            steps.append({
                "step":       step_idx,
                "quest_id":   qid,
                "name":       qdef[1] if qdef else "?",
                "difficulty": qdef[3] if qdef else "normal",
                "duration":   qdef[4] if qdef else 0,
                "min_level":  qdef[8] if qdef else 1,
                "icon":       qdef[9] if qdef else "⚔️",
                "done":       qid in completed_ids,
            })

        # Zjisti ID dalšího dostupného kroku
        next_quest_id = None
        if not unlocked:
            for step in steps:
                if not step["done"]:
                    next_quest_id = step["quest_id"]
                    break

        # Dungeon quest detail
        dq_id  = chain["dungeon_quest_id"]
        dq_def = _QDEF.get(dq_id)

        chains.append({
            "id":               chain["id"],
            "name":             chain["name"],
            "badge":            chain["badge"],
            "color":            chain["color"],
            "desc":             chain["desc"],
            "dungeon_name":     chain["dungeon_name"],
            "dungeon_icon":     chain["dungeon_icon"],
            "dungeon_quest_id": dq_id,
            "dungeon_min_level": dq_def[8] if dq_def else 1,
            "dungeon_duration": dq_def[4] if dq_def else 0,
            "reward_title":     chain["reward_title"],
            "steps":            steps,
            "completed_steps":  completed_steps,
            "total_steps":      total_steps,
            "unlocked":         unlocked,
            "next_quest_id":    next_quest_id,
        })

    return {
        "chains":               chains,
        "unlocked_attunements": attunements,
    }
