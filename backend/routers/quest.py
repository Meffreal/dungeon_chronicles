"""
routers/quest.py — Start, status, collect quest
"""
import json
import random
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.character import Character, xp_to_next
from models.quest import Quest, QuestStatus, QUEST_DEFINITIONS
from models.item import InventoryItem
from game.combat import simulate_combat, quest_enemy_stats, CombatStats
from game.loot import get_random_item_for_quest
from game.achievements import check_and_award
from routers.auth import get_current_user
from routers.character import char_dict_with_equipment

router = APIRouter(prefix="/quest", tags=["quest"])

class StartQuestRequest(BaseModel):
    quest_id: int

async def _get_char_and_quest(user: User, db: AsyncSession):
    """Helper — vrátí (Character, Quest) nebo hodí 404."""
    c_result = await db.execute(select(Character).where(Character.user_id == user.id))
    char = c_result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Nejdřív si vytvoř postavu.")

    q_result = await db.execute(
        select(Quest)
        .options(selectinload(Quest.reward_item))
        .where(Quest.character_id == char.id)
    )
    quest = q_result.scalar_one_or_none()
    if not quest:
        # Quest slot chybí — vytvoříme
        quest = Quest(character_id=char.id, status=QuestStatus.IDLE)
        db.add(quest); await db.flush()

    return char, quest

@router.get("/list")
async def list_quests(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Vrátí všechny dostupné questy s info o win_chance."""
    char, _ = await _get_char_and_quest(user, db)
    from game.combat import calculate_win_chance

    quests = []
    for qdef in QUEST_DEFINITIONS:
        enemy = quest_enemy_stats(qdef, char.level)
        player = CombatStats(
            name=char.name, hp=char.hp_max, atk=char.atk,
            def_=char.def_, spd=char.spd, luck=char.luck, level=char.level,
        )
        win_chance = calculate_win_chance(player, enemy)
        unlocked = char.level >= qdef[8]  # min_level

        quests.append({
            "id":         qdef[0],
            "name":       qdef[1],
            "desc":       qdef[2],
            "difficulty": qdef[3],
            "duration":   qdef[4],
            "reward_xp":  qdef[5],
            "reward_gold_min": qdef[6],
            "reward_gold_max": qdef[7],
            "min_level":  qdef[8],
            "icon":       qdef[9],
            "win_chance": win_chance,
            "unlocked":   unlocked,
        })
    return quests

@router.post("/start")
async def start_quest(
    req: StartQuestRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    char, quest = await _get_char_and_quest(user, db)

    if quest.status == QuestStatus.ACTIVE:
        raise HTTPException(400, "Již probíhá quest. Počkej na dokončení.")
    if quest.status == QuestStatus.COLLECTING:
        raise HTTPException(400, "Máš quest k sebrání! Nejdřív ho seber.")

    # Najdi definici questu
    qdef = next((q for q in QUEST_DEFINITIONS if q[0] == req.quest_id), None)
    if not qdef:
        raise HTTPException(404, "Quest nenalezen.")
    if char.level < qdef[8]:
        raise HTTPException(400, f"Potřebuješ level {qdef[8]}. Ty jsi level {char.level}.")

    # Simuluj boj
    enemy = quest_enemy_stats(qdef, char.level)
    player_stats = CombatStats(
        name=char.name, hp=char.hp_max, atk=char.atk,
        def_=char.def_, spd=char.spd, luck=char.luck, level=char.level,
    )
    combat_result = simulate_combat(player_stats, enemy)

    # Vypočítej odměnu
    success = combat_result.winner == "player"
    reward_xp = qdef[5] if success else qdef[5] // 4  # prohra = 25% XP
    reward_gold = random.randint(qdef[6], qdef[7]) if success else 0
    drop_item = await get_random_item_for_quest(db, qdef[3], char.level) if success else None

    # Nastav quest
    now = datetime.utcnow()  # naive UTC — SQLite timezone=True nefunguje spolehlivě
    duration = timedelta(minutes=qdef[4])

    quest.quest_def_id   = req.quest_id
    quest.status         = QuestStatus.ACTIVE
    quest.started_at     = now
    quest.finish_at      = now + duration
    quest.reward_xp      = reward_xp
    quest.reward_gold    = reward_gold
    quest.reward_item_id = drop_item.id if drop_item else None
    quest.success        = success
    quest.battle_log     = json.dumps(combat_result.log, ensure_ascii=False)

    await db.commit()

    return {
        "message":  f"Quest '{qdef[1]}' zahájen!",
        "success":  success,
        "duration": qdef[4],
        "finish_at": quest.finish_at.isoformat(),
        "preview": {
            "xp":   reward_xp,
            "gold": reward_gold,
            "item": drop_item.name if drop_item else None,
        },
    }

@router.get("/status")
async def quest_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    char, quest = await _get_char_and_quest(user, db)

    # Auto-přechod ACTIVE → COLLECTING
    if quest.status == QuestStatus.ACTIVE and quest.is_finished:
        quest.status = QuestStatus.COLLECTING
        await db.commit()

    return quest.to_dict()

@router.post("/collect")
async def collect_quest(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    char, quest = await _get_char_and_quest(user, db)

    # Auto-check
    if quest.status == QuestStatus.ACTIVE and quest.is_finished:
        quest.status = QuestStatus.COLLECTING

    if quest.status != QuestStatus.COLLECTING:
        if quest.status == QuestStatus.ACTIVE:
            raise HTTPException(400, f"Quest ještě není hotov. Zbývá {quest.seconds_remaining}s.")
        raise HTTPException(400, "Žádný quest k sebrání.")

    # Připiš odměnu
    char.xp   += quest.reward_xp
    char.gold += quest.reward_gold
    char.quests_completed = (char.quests_completed or 0) + 1

    # Level up loop
    leveled_up = []
    while char.xp >= xp_to_next(char.level):
        char.xp    -= xp_to_next(char.level)
        char.level += 1
        char.stat_points = (char.stat_points or 0) + 1
        char.recalculate_stats()
        leveled_up.append(char.level)

    # Item drop → inventář
    gained_item = None
    if quest.reward_item_id:
        # Zkus zvýšit quantity stávajícího stacku
        inv_result = await db.execute(
            select(InventoryItem).where(
                InventoryItem.character_id == char.id,
                InventoryItem.item_id == quest.reward_item_id,
            )
        )
        inv_item = inv_result.scalar_one_or_none()
        if inv_item:
            inv_item.quantity += 1
        else:
            inv_item = InventoryItem(
                character_id=char.id,
                item_id=quest.reward_item_id,
                quantity=1,
            )
            db.add(inv_item)

        gained_item = quest.reward_item.to_dict() if quest.reward_item else None

    battle_log = json.loads(quest.battle_log) if quest.battle_log else []

    # Ulož odměny před resetem slotu
    earned_xp    = quest.reward_xp
    earned_gold  = quest.reward_gold
    was_success  = quest.success

    # Reset quest slotu
    quest.status         = QuestStatus.IDLE
    quest.quest_def_id   = None
    quest.started_at     = None
    quest.finish_at      = None
    quest.reward_xp      = 0
    quest.reward_gold    = 0
    quest.reward_item_id = None
    quest.success        = True
    quest.battle_log     = ""

    new_achievements = await check_and_award(char, db)
    await db.commit()

    return {
        "message":    "Odměna sebrána!",
        "success":    was_success,
        "xp_gained":  earned_xp,
        "gold_gained": earned_gold,
        "rewards": {
            "xp":   earned_xp,
            "gold": earned_gold,
            "item": gained_item,
        },
        "leveled_up":       leveled_up,
        "battle_log":       battle_log[:15],
        "character":        await char_dict_with_equipment(char, db),
        "new_achievements": new_achievements,
    }

@router.get("/battle-log")
async def get_battle_log(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí plný battle log posledního questu."""
    _, quest = await _get_char_and_quest(user, db)
    log = json.loads(quest.battle_log) if quest.battle_log else []
    return {"log": log}
