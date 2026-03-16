"""
routers/quest.py — Start, status, collect quest
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
from models.character import Character, xp_to_next
from models.economy import log_gold, GoldReason
from models.quest import Quest, QuestStatus, QUEST_DEFINITIONS, DailyQuestRotation, _DISABLED_QUESTS
from models.quest_slot import QuestSlot, slot_count_for_level
from models.item import InventoryItem
from models.attunement import QUEST_CHAIN_MAP, DUNGEON_QUEST_ATTUNEMENT, ATTUNEMENT_CHAINS
from routers.world_event import add_world_event_contribution
from game.combat_engine import (
    CombatantConfig, simulate_unified_combat, calculate_win_chance, events_to_dict_list,
)
from game.experiments import get_experiment_overrides, apply_overrides_to_engine, apply_overrides_to_router
from game.loot import get_random_item_for_quest, get_dungeon_set_item
from game.achievements import check_and_award
from game.set_bonuses import get_char_set_combat_effects
from game.factions import REP_FROM_QUEST
from game.professions import (
    add_resonance_to_equipped_runes,
    get_oracle_xp_bonus,
    get_broker_gold_bonus,
)
from models.faction import FactionReputation
from routers.auth import get_current_user
from routers.character import char_dict_with_equipment
from routers.diviner import verify_prophecies_for_quest
from routers.gambler import resolve_quest_bets
from routers.fateweaver import check_bonds_on_quest_complete

router = APIRouter(prefix="/quest", tags=["quest"])


def _quest_enemy_config(qdef: tuple, character_level: int) -> CombatantConfig:
    """Sestaví CombatantConfig nepřítele pro daný quest a level hráče."""
    difficulty = qdef[3]
    base_level = max(qdef[8], character_level)
    mult = {"easy": 0.75, "normal": 1.0, "hard": 1.35, "boss": 2.0}.get(difficulty, 1.0)
    return CombatantConfig(
        name=f"[{qdef[1]}] Nepřítel",
        hp=int(50 * base_level * mult),
        atk=int(8 * base_level * mult),
        def_=int(4 * base_level * mult),
        spd=int(6 * base_level * mult * 0.8),
        luck=int(3 * mult),
        level=base_level,
        cls="",
        mp=0,
    )

def _build_eligible_pool(char, disabled_ids: set) -> list:
    """Vrátí questy vhodné pro slot generování (bez boss, chain, dungeon, pod min_level)."""
    eligible = []
    for qdef in QUEST_DEFINITIONS:
        qid = qdef[0]
        if qid in DUNGEON_QUEST_ATTUNEMENT:
            continue
        if qid in QUEST_CHAIN_MAP:
            continue
        if qdef[3] == "boss":
            continue
        if char.level < qdef[8]:
            continue
        if qid in disabled_ids:
            continue
        eligible.append(qdef)
    return eligible


async def _ensure_slots(char, db: AsyncSession, disabled_ids: set) -> list:
    """Vrátí sloty postavy seřazené podle slot_index; chybějící dogeneruje."""
    count = slot_count_for_level(char.level)
    result = await db.execute(
        select(QuestSlot)
        .where(QuestSlot.character_id == char.id)
        .order_by(QuestSlot.slot_index)
    )
    slots = list(result.scalars().all())

    pool = _build_eligible_pool(char, disabled_ids)
    used_ids = {s.quest_def_id for s in slots}

    # Smaž přebytečné sloty (edge case: downgrade levelu)
    for s in list(slots):
        if s.slot_index >= count:
            await db.delete(s)
    slots = [s for s in slots if s.slot_index < count]

    # Dogeneruj chybějící sloty
    existing_indices = {s.slot_index for s in slots}
    for idx in range(count):
        if idx in existing_indices:
            continue
        available = [q for q in pool if q[0] not in used_ids]
        if not available:
            available = pool  # fallback — duplicity ok
        if not available:
            continue
        chosen = random.choice(available)
        slot = QuestSlot(
            character_id=char.id,
            slot_index=idx,
            quest_def_id=chosen[0],
        )
        db.add(slot)
        slots.append(slot)
        used_ids.add(chosen[0])

    await db.flush()
    return sorted(slots, key=lambda s: s.slot_index)


def _slot_to_quest_dict(slot: QuestSlot, char, disabled_ids: set) -> dict | None:
    """Převede QuestSlot na quest dict pro frontend. Vrátí None pokud qdef nenalezen."""
    qdef = next((q for q in QUEST_DEFINITIONS if q[0] == slot.quest_def_id), None)
    if qdef is None:
        return None
    enemy = _quest_enemy_config(qdef, char.level)
    player = CombatantConfig(
        name=char.name, hp=char.hp_max, atk=char.atk,
        def_=char.def_, spd=char.spd, luck=char.luck, level=char.level,
        cls="", mp=0,
    )
    gold_scale = 1.0 + char.level * 0.1
    return {
        "id":              qdef[0],
        "name":            qdef[1],
        "desc":            qdef[2],
        "difficulty":      qdef[3],
        "duration":        qdef[4],
        "reward_xp":       qdef[5],
        "reward_gold_min": int(qdef[6] * gold_scale),
        "reward_gold_max": int(qdef[7] * gold_scale),
        "min_level":       qdef[8],
        "icon":            qdef[9],
        "win_chance":      calculate_win_chance(player, enemy),
        "chain_info":      None,
        "slot_index":      slot.slot_index,
        "free_skip":       slot.free_skip_available(),
    }


class StartQuestRequest(BaseModel):
    quest_id: int
    strategy: str = "balanced"
    is_daily: bool = False

async def _get_char_and_quest(user: User, db: AsyncSession):
    """Helper — vrátí (Character, Quest) nebo hodí 404."""
    c_result = await db.execute(select(Character).where(Character.user_id == user.id))
    char = c_result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Nejdřív si vytvoř postavu.")
    if char.is_dead:
        raise HTTPException(403, f"Tato postava zemřela. Zabit: {char.killed_by or 'Neznámý nepřítel'}")

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
    """Vrátí slot questy (max 4) + chain questy s chain info a win_chance."""
    char, _ = await _get_char_and_quest(user, db)

    attunements = char.get_attunements()
    progress    = char.get_attunement_progress()

    # Určí, který quest je dalším dostupným krokem v každém chainu
    next_chain_steps: dict[int, dict] = {}   # quest_id → chain info
    for chain in ATTUNEMENT_CHAINS:
        if chain["id"] in attunements:
            continue  # Chain dokončen — žádné další kroky
        cid       = str(chain["id"])
        completed = progress.get(cid, [])
        for qid in chain["quest_ids"]:
            if qid not in completed:
                next_chain_steps[qid] = chain
                break

    # DB-backed disabled quests (multi-instance safe, 10s cache)
    from models.disabled_quest import get_disabled_quest_ids
    disabled_ids = await get_disabled_quest_ids(db)

    # ── Chain questy (zachováno z původní logiky) ──────────────────────────────
    chain_quests = []
    for qdef in QUEST_DEFINITIONS:
        qid = qdef[0]
        if qid not in next_chain_steps:
            continue
        if qid in disabled_ids or char.level < qdef[8]:
            continue
        enemy = _quest_enemy_config(qdef, char.level)
        player = CombatantConfig(
            name=char.name, hp=char.hp_max, atk=char.atk,
            def_=char.def_, spd=char.spd, luck=char.luck, level=char.level,
            cls="", mp=0,
        )
        ci    = QUEST_CHAIN_MAP[qid]
        chain = ci["chain"]
        cid   = str(chain["id"])
        done  = len(progress.get(cid, []))
        gold_scale = 1.0 + char.level * 0.1
        chain_quests.append({
            "id":              qdef[0],
            "name":            qdef[1],
            "desc":            qdef[2],
            "difficulty":      qdef[3],
            "duration":        qdef[4],
            "reward_xp":       qdef[5],
            "reward_gold_min": int(qdef[6] * gold_scale),
            "reward_gold_max": int(qdef[7] * gold_scale),
            "min_level":       qdef[8],
            "icon":            qdef[9],
            "win_chance":      calculate_win_chance(player, enemy),
            "chain_info": {
                "chain_id":   chain["id"],
                "chain_name": chain["name"],
                "badge":      chain["badge"],
                "color":      chain["color"],
                "step":       ci["step"],
                "total":      len(chain["quest_ids"]),
                "completed":  done,
            },
            "slot_index": None,
            "free_skip":  False,
        })

    # ── Slot questy (normální — max 3 nebo 4 sloty) ───────────────────────────
    slots = await _ensure_slots(char, db, disabled_ids)
    slot_quests = []
    for slot in slots:
        q = _slot_to_quest_dict(slot, char, disabled_ids)
        if q:
            slot_quests.append(q)

    # Recommended: top 2 ze slot_quests podle score (win_chance >= 0.40)
    def _rec_score(q: dict) -> float:
        dur = q["duration"] or 1
        return (q["reward_xp"] + (q["reward_gold_min"] + q["reward_gold_max"]) / 2) * q["win_chance"] / dur

    recommended = sorted(
        [q for q in slot_quests if q["win_chance"] >= 0.40],
        key=_rec_score, reverse=True,
    )[:2]

    return {"quests": slot_quests, "chain_quests": chain_quests, "recommended": recommended}

@router.post("/slot/skip/{slot_index}")
async def skip_quest_slot(
    slot_index: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    char, quest = await _get_char_and_quest(user, db)

    # Nelze skipovat když probíhá quest
    if quest and quest.status != QuestStatus.IDLE:
        raise HTTPException(400, "Nejdřív dokonči aktuální quest.")

    result = await db.execute(
        select(QuestSlot).where(
            QuestSlot.character_id == char.id,
            QuestSlot.slot_index == slot_index,
        )
    )
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(404, "Slot nenalezen.")

    from models.disabled_quest import get_disabled_quest_ids
    disabled_ids = await get_disabled_quest_ids(db)

    free = slot.free_skip_available()
    SKIP_COST = 10  # gold

    if not free:
        if char.gold < SKIP_COST:
            raise HTTPException(400, f"Nedostatek goldu. Potřebuješ {SKIP_COST} G.")
        char.gold -= SKIP_COST
        await log_gold(db, char, -SKIP_COST, GoldReason.OTHER, {"reason": "quest_skip"})

    # Nový quest pro tento slot (jiný než ostatní sloty)
    all_slots_res = await db.execute(
        select(QuestSlot).where(QuestSlot.character_id == char.id)
    )
    used_ids = {s.quest_def_id for s in all_slots_res.scalars().all() if s.slot_index != slot_index}

    pool = _build_eligible_pool(char, disabled_ids)
    available = [q for q in pool if q[0] not in used_ids and q[0] != slot.quest_def_id]
    if not available:
        available = [q for q in pool if q[0] != slot.quest_def_id]
    if not available:
        available = pool

    chosen = random.choice(available)
    slot.quest_def_id = chosen[0]
    slot.mark_skipped(paid=not free)
    slot.generated_at = datetime.now(timezone.utc)

    await db.commit()

    return {
        "ok": True,
        "paid": not free,
        "cost": 0 if free else SKIP_COST,
        "new_quest": _slot_to_quest_dict(slot, char, disabled_ids),
        "gold": char.gold,
    }


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

    # Dungeon quest — vyžaduje attunement
    if req.quest_id in DUNGEON_QUEST_ATTUNEMENT:
        required_chain_id = DUNGEON_QUEST_ATTUNEMENT[req.quest_id]
        if required_chain_id not in char.get_attunements():
            chain = next(c for c in ATTUNEMENT_CHAINS if c["id"] == required_chain_id)
            raise HTTPException(403, f"Nemáš attunement '{chain['name']}'. Dokonči sérii questů '{chain['name']}'.")

    # Chain quest — musí to být aktuální krok (ne přeskočený nebo hotový)
    if req.quest_id in QUEST_CHAIN_MAP:
        ci        = QUEST_CHAIN_MAP[req.quest_id]
        cid       = str(ci["chain_id"])
        chain     = ci["chain"]
        completed = char.get_attunement_progress().get(cid, [])
        if req.quest_id in completed:
            raise HTTPException(400, "Tento krok série jsi již dokončil.")
        # Zkontroluj, že předchozí krok je hotový
        if ci["step"] > 1:
            prev_qid = chain["quest_ids"][ci["step"] - 2]
            if prev_qid not in completed:
                raise HTTPException(400, f"Nejdříve dokonči předchozí krok série '{chain['name']}'.")

    # Načti experiment overrides pro skupinu hráče
    _exp_overrides = await get_experiment_overrides(char.experiment_group or 0, db)
    _engine_ov     = apply_overrides_to_engine(_exp_overrides)
    _router_ov     = apply_overrides_to_router(_exp_overrides)

    # Simuluj boj
    enemy = _quest_enemy_config(qdef, char.level)
    _set_fx = await get_char_set_combat_effects(char, db)
    player_cfg = CombatantConfig(
        name=char.name, hp=char.hp_max, atk=char.atk,
        def_=char.def_, spd=char.spd, luck=char.luck, level=char.level,
        cls=char.cls, mp=char.mp_max,
        strategy=req.strategy,
        talents=char.get_talents(),
        subclass=char.subclass or "",
        talent_t2=char.talent_t2_key or "",
        set_bonuses=_set_fx,
        experiment_overrides=_engine_ov,
    )
    combat_result = simulate_unified_combat(player_cfg, enemy)

    # Vypočítej odměnu — gold škáluje s levelem hráče (+ A/B xp_reward_mult)
    success = combat_result.attacker_won
    _xp_mult = float(_router_ov.get("xp_reward_mult", 1.0))
    reward_xp = int((qdef[5] if success else qdef[5] // 4) * _xp_mult)
    if success:
        base_gold = random.randint(qdef[6], qdef[7])
        reward_gold = int(base_gold * (1.0 + char.level * 0.1))
    else:
        reward_gold = 0
    # Dungeon questy garantují drop setového itemu (pro třídu hráče)
    if req.quest_id in DUNGEON_QUEST_ATTUNEMENT and success:
        drop_item = await get_dungeon_set_item(db, char.cls)
        if drop_item is None:  # fallback pokud set itemy ještě nejsou v DB
            drop_item = await get_random_item_for_quest(db, qdef[3], char.level)
    else:
        drop_item = await get_random_item_for_quest(db, qdef[3], char.level) if success else None

    # Nastav quest
    now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC — SQLite timezone=True nefunguje spolehlivě
    duration = timedelta(minutes=qdef[4])

    quest.quest_def_id   = req.quest_id
    quest.status         = QuestStatus.ACTIVE
    quest.started_at     = now
    quest.finish_at      = now + duration
    quest.reward_xp      = reward_xp
    quest.reward_gold    = reward_gold
    quest.reward_item_id = drop_item.id if drop_item else None
    quest.success        = success
    quest.is_daily       = req.is_daily
    # Ukládáme jak text log, tak structured events pro animovaný replay
    quest.battle_log     = json.dumps({
        "log":    combat_result.log,
        "events": events_to_dict_list(combat_result.events),
    }, ensure_ascii=False)

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

    # Daily bonus: +25 % XP a gold pokud byl quest spuštěn jako daily
    _is_daily_quest = quest.is_daily
    if _is_daily_quest:
        quest.reward_xp   = int(quest.reward_xp   * 1.25)
        quest.reward_gold = int(quest.reward_gold  * 1.25)

    # Připiš odměnu — s Crystal XP boost (+25% pokud aktivní)
    from datetime import datetime as _dt, timezone as _tz
    _now = _dt.now(_tz.utc).replace(tzinfo=None)
    _boost = (
        char.crystal_xp_boost_until is not None
        and char.crystal_xp_boost_until > _now
    )
    _base_xp = quest.reward_xp
    _bonus_xp = int(_base_xp * 0.25) if _boost else 0
    char.xp   += _base_xp + _bonus_xp
    char.gold += quest.reward_gold
    char.quests_completed = (char.quests_completed or 0) + 1
    # World Event příspěvek — quest
    await add_world_event_contribution("quests", char.id, 1, db)
    _qdef_log = next((q for q in QUEST_DEFINITIONS if q[0] == quest.quest_def_id), None)
    await log_gold(db, char, quest.reward_gold, GoldReason.QUEST_REWARD,
                   {"quest_id": quest.id, "quest_name": _qdef_log[1] if _qdef_log else ""})

    # Level up loop
    leveled_up = []
    while char.xp >= xp_to_next(char.level):
        char.xp    -= xp_to_next(char.level)
        char.level += 1
        char.stat_points = (char.stat_points or 0) + 1
        leveled_up.append(char.level)
    if leveled_up:
        from routers.inventory import recalculate_with_gear
        await recalculate_with_gear(char, db)
    # Auto-unlock talentů (Tier 1) při dosažení level 10/20/30
    from game.talents import TALENT_TREE as _TALENT_TREE
    _newly_talents = char.check_and_unlock_talents() if leveled_up else []
    newly_unlocked_talents = [{"key": k, **_TALENT_TREE[k]} for k in _newly_talents]

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

    # Zpětná kompatibilita: starý formát = list, nový = dict s "log" a "events"
    raw_log = json.loads(quest.battle_log) if quest.battle_log else []
    if isinstance(raw_log, dict):
        battle_log    = raw_log.get("log", [])
        battle_events = raw_log.get("events", [])
    else:
        battle_log    = raw_log
        battle_events = []

    # Ulož odměny před resetem slotu
    earned_xp          = quest.reward_xp
    earned_gold        = quest.reward_gold
    was_success        = quest.success
    saved_quest_def    = quest.quest_def_id  # nutné pro frakční rep (před resetem!)
    actual_drop_rarity = quest.reward_item.rarity if quest.reward_item else None

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
    quest.is_daily       = False

    # ── Frakční reputace za quest ──────────────────────────────────────────────
    faction_rep_gained = 0
    if char.faction and was_success:
        # Zjisti obtížnost dokončeného questu (používáme saved_quest_def, ne quest.quest_def_id který je již None)
        quest_difficulty = None
        if saved_quest_def:
            qdef = next((q for q in QUEST_DEFINITIONS if q[0] == saved_quest_def), None)
            if qdef:
                quest_difficulty = qdef[3]
        if quest_difficulty:
            faction_rep_gained = REP_FROM_QUEST.get(quest_difficulty, 5)
            # Přidej reputaci do faction_reputation záznamu
            fr_result = await db.execute(
                select(FactionReputation).where(FactionReputation.character_id == char.id)
            )
            faction_rep = fr_result.scalar_one_or_none()
            if faction_rep:
                faction_rep.reputation += faction_rep_gained

    # ── Attunement chain progress ──────────────────────────────────────────────
    chain_step_done   = False
    chain_completed   = False
    chain_info_result = None
    if was_success and saved_quest_def and saved_quest_def in QUEST_CHAIN_MAP:
        chain_step_done = True
        ci              = QUEST_CHAIN_MAP[saved_quest_def]
        chain_completed = char.add_attunement_quest_progress(saved_quest_def)
        chain_info_result = {
            "chain_id":   ci["chain_id"],
            "chain_name": ci["chain"]["name"],
            "badge":      ci["chain"]["badge"],
            "step":       ci["step"],
            "total":      len(ci["chain"]["quest_ids"]),
            "dungeon_name": ci["chain"]["dungeon_name"],
            "dungeon_icon": ci["chain"]["dungeon_icon"],
        }

    new_achievements = await check_and_award(char, db)

    # ── Profesní hooky ────────────────────────────────────────────────────────

    # Runovník: rezonance do run na nasazených předmětech po každém boji
    rune_evolutions: list[dict] = []
    if was_success and saved_quest_def:
        qdef_full = next((q for q in QUEST_DEFINITIONS if q[0] == saved_quest_def), None)
        resonance_amount = {"easy": 3, "normal": 7, "hard": 15, "boss": 25}.get(
            qdef_full[3] if qdef_full else "normal", 7
        )
        rune_evolutions = await add_resonance_to_equipped_runes(char, resonance_amount, db)

    # Věštec: verifikace svitků proroctví pro tento quest
    if saved_quest_def:
        await verify_prophecies_for_quest(saved_quest_def, was_success, actual_drop_rarity, db)

    # Šarlatán: uzavření sázek navázaných na tento quest
    if saved_quest_def:
        await resolve_quest_bets(char.id, saved_quest_def, was_success, actual_drop_rarity, db)

    # Tkadlec: fire cooperation pout
    bond_fires = await check_bonds_on_quest_complete(char.id, was_success, db)

    # Oracle pasivní: Prozření — +2 % XP za rank při sebrání úspěšného questu
    oracle_bonus_xp = 0
    if was_success and earned_xp > 0:
        oracle_bonus_xp = await get_oracle_xp_bonus(char.id, earned_xp, db)
        if oracle_bonus_xp > 0:
            char.xp += oracle_bonus_xp

    # Broker pasivní: Riziková prémie — +5 % gold za rank při sebrání úspěšného questu
    broker_bonus_gold = 0
    if was_success and earned_gold > 0:
        broker_bonus_gold = await get_broker_gold_bonus(char.id, earned_gold, db)
        if broker_bonus_gold > 0:
            char.gold += broker_bonus_gold

    # Guild Weekly Quest hooky
    if was_success and char.guild_id:
        from routers.guild import increment_guild_weekly
        await increment_guild_weekly(char.guild_id, "quests", 1, char.id, db)
        await increment_guild_weekly(char.guild_id, "kills",  1, char.id, db)

    # Individuální Weekly Board hooky
    if was_success:
        from routers.weekly_quest import increment_weekly_board
        _wq_new = await increment_weekly_board(char.id, "quests", 1, db)
        _wq_new += await increment_weekly_board(char.id, "kills",  1, db)
    else:
        _wq_new = []

    # Season Pass XP
    if was_success:
        from routers.season_pass import add_season_xp
        await add_season_xp(char.id, "quest", db)

    # Auto-refresh slotu, který měl dokončený quest
    from models.disabled_quest import get_disabled_quest_ids as _get_disabled
    _disabled_refresh = await _get_disabled(db)
    _all_slots_res = await db.execute(
        select(QuestSlot).where(QuestSlot.character_id == char.id)
    )
    _all_slots = list(_all_slots_res.scalars().all())
    _completed_slot = next(
        (s for s in _all_slots if s.quest_def_id == saved_quest_def), None
    )
    if _completed_slot:
        _pool = _build_eligible_pool(char, _disabled_refresh)
        _used = {s.quest_def_id for s in _all_slots if s.slot_index != _completed_slot.slot_index}
        _avail = [q for q in _pool if q[0] not in _used]
        if not _avail:
            _avail = _pool
        if _avail:
            _completed_slot.quest_def_id = random.choice(_avail)[0]
            _completed_slot.generated_at = datetime.now(timezone.utc)

    await db.commit()

    return {
        "message":    "Odměna sebrána!",
        "success":    was_success,
        "xp_gained":  earned_xp + _bonus_xp + oracle_bonus_xp,
        "xp_boost_bonus": _bonus_xp,
        "oracle_bonus_xp": oracle_bonus_xp,
        "gold_gained": earned_gold + broker_bonus_gold,
        "broker_bonus_gold": broker_bonus_gold,
        "daily_bonus_applied":     _is_daily_quest,
        "daily_bonus_multiplier":  1.25 if _is_daily_quest else 1.0,
        "rewards": {
            "xp":   earned_xp + _bonus_xp + oracle_bonus_xp,
            "gold": earned_gold + broker_bonus_gold,
            "item": gained_item,
        },
        "faction_rep_gained": faction_rep_gained,
        "leveled_up":            leveled_up,
        "newly_unlocked_talents": newly_unlocked_talents,
        "battle_log":            battle_log[:15],
        "battle_events":    battle_events,   # structured events pro animovaný replay
        "character":        await char_dict_with_equipment(char, db),
        "new_achievements": new_achievements,
        "chain_step_done":  chain_step_done,
        "chain_completed":  chain_completed,
        "chain_info":       chain_info_result,
        "rune_evolutions":  rune_evolutions,
        "bond_fires":       bond_fires,
        "weekly_completed": _wq_new,
    }

@router.post("/abandon")
async def abandon_quest(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Přeruší aktivní quest bez jakékoli penalizace."""
    char, quest = await _get_char_and_quest(user, db)

    if quest.status != QuestStatus.ACTIVE:
        raise HTTPException(400, "Žádný aktivní quest k přerušení.")

    quest.status         = QuestStatus.IDLE
    quest.quest_def_id   = None
    quest.started_at     = None
    quest.finish_at      = None
    quest.reward_xp      = 0
    quest.reward_gold    = 0
    quest.reward_item_id = None
    quest.success        = True
    quest.battle_log     = ""

    await db.commit()
    return {"message": "Quest přerušen."}


@router.get("/daily")
async def get_daily_quests(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí dnešní 3 denní questy. Generuje nové pokud ještě neexistují (reset 00:00 UTC)."""
    char, _ = await _get_char_and_quest(user, db)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Zkontroluj existující rotaci
    rot_result = await db.execute(
        select(DailyQuestRotation).where(
            DailyQuestRotation.character_id == char.id,
            DailyQuestRotation.date == today,
        )
    )
    rotation = rot_result.scalar_one_or_none()

    if rotation is None:
        # Vyber pool eligibilních questů: non-boss, non-chain, non-dungeon, min_level splněn
        pool = [
            qdef for qdef in QUEST_DEFINITIONS
            if qdef[3] != "boss"
            and qdef[0] not in QUEST_CHAIN_MAP
            and qdef[0] not in DUNGEON_QUEST_ATTUNEMENT
            and char.level >= qdef[8]
        ]
        selected = random.sample(pool, min(3, len(pool)))
        rotation = DailyQuestRotation(
            character_id=char.id,
            date=today,
            quest_ids=json.dumps([q[0] for q in selected]),
        )
        db.add(rotation)
        await db.commit()

    quest_ids = json.loads(rotation.quest_ids)
    quests_out = []
    for qid in quest_ids:
        qdef = next((q for q in QUEST_DEFINITIONS if q[0] == qid), None)
        if not qdef:
            continue
        enemy = _quest_enemy_config(qdef, char.level)
        player = CombatantConfig(
            name=char.name, hp=char.hp_max, atk=char.atk,
            def_=char.def_, spd=char.spd, luck=char.luck, level=char.level,
            cls="", mp=0,
        )
        win_chance = calculate_win_chance(player, enemy)
        gold_scale = 1.0 + char.level * 0.1
        quests_out.append({
            "id":               qdef[0],
            "name":             qdef[1],
            "desc":             qdef[2],
            "difficulty":       qdef[3],
            "duration":         qdef[4],
            "reward_xp":        qdef[5],
            "reward_gold_min":  int(qdef[6] * gold_scale),
            "reward_gold_max":  int(qdef[7] * gold_scale),
            "min_level":        qdef[8],
            "icon":             qdef[9],
            "win_chance":       win_chance,
            "is_daily":         True,
            "bonus_multiplier": 1.25,
            "is_daily_bonus":   True,
        })

    # Čas do resetu: příští půlnoc UTC
    now_utc = datetime.now(timezone.utc)
    next_reset = (now_utc + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_to_reset = int((next_reset - now_utc).total_seconds())

    return {
        "quests":          quests_out,
        "date":            today,
        "reset_at":        next_reset.isoformat(),
        "seconds_to_reset": seconds_to_reset,
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
