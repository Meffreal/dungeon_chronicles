"""
routers/boss.py — World Boss endpoints.

World Boss je sdílený PvE obsah:
- GET  /boss/current     — info o aktivním bossovi
- POST /boss/attack      — útok na bosse (cooldown 6h)
- GET  /boss/leaderboard — top přispěvatelé
- POST /boss/claim       — vyzvednutí odměn po zabitení bosse
- POST /boss/spawn       — (admin) spawn nového bosse
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update as sa_update, case
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
import random

from database import get_db
from models.economy import log_gold, GoldReason
from models.user import User
from models.character import Character, xp_to_next
from models.world_boss import WorldBoss, BossParticipation, WORLD_BOSS_DEFINITIONS
from routers.auth import get_current_user
from routers.character import char_dict_with_equipment
from routers.world_event import add_world_event_contribution
from game.combat_engine import (
    CombatantConfig, BossPhase, simulate_unified_combat,
    events_to_dict_list,
)
from game.combatant_builder import build_combatant_config

router = APIRouter(prefix="/boss", tags=["boss"])


async def _get_char(user: User, db: AsyncSession) -> Character:
    result = await db.execute(select(Character).where(Character.user_id == user.id, Character.is_dead == False))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena.")
    return char


def _build_boss_config(boss: WorldBoss) -> CombatantConfig:
    """Sestaví CombatantConfig pro aktuálního world bosse."""
    bdef = WORLD_BOSS_DEFINITIONS[boss.boss_key]

    # Fáze bosse z definice
    phases = bdef.get("phases", [])

    return CombatantConfig(
        name=boss.name,
        hp=boss.hp_current,
        atk=bdef["atk"],
        def_=bdef["def_"],
        spd=bdef["spd"],
        luck=bdef["luck"],
        level=bdef["level"],
        cls="",
        mp=0,
        is_boss=True,
        phases=phases,
        special_abilities=bdef.get("special_abilities", []),
        hp_max_override=boss.hp_max,
    )


# ── GET /boss/current ─────────────────────────────────────────────────────────

@router.get("/current")
async def get_current_boss(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí info o aktuálně aktivním World Bossovi."""
    char = await _get_char(user, db)

    result = await db.execute(
        select(WorldBoss).where(WorldBoss.is_alive == True).order_by(WorldBoss.id.desc()).limit(1)
    )
    boss = result.scalar_one_or_none()

    if not boss:
        # Žádný boss — zkus auto-spawn prvního
        boss = await _auto_spawn_boss(db)
        if not boss:
            return {"boss": None, "message": "Žádný aktivní boss. Brzy se objeví nový."}

    # Najdi participaci hráče
    part_result = await db.execute(
        select(BossParticipation).where(
            BossParticipation.boss_id == boss.id,
            BossParticipation.character_id == char.id,
        )
    )
    participation = part_result.scalar_one_or_none()

    # Cooldown check
    bdef = WORLD_BOSS_DEFINITIONS.get(boss.boss_key, {})
    cooldown_hours = bdef.get("attack_cooldown_hours", 6)
    can_attack   = True
    cd_remaining = 0.0
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if participation and participation.last_attack_at:
        next_attack = participation.last_attack_at + timedelta(hours=cooldown_hours)
        if next_attack > now:
            can_attack   = False
            cd_remaining = (next_attack - now).total_seconds()

    # Top přispěvatelé
    top_result = await db.execute(
        select(BossParticipation, Character.name, Character.cls)
        .join(Character, BossParticipation.character_id == Character.id)
        .where(BossParticipation.boss_id == boss.id)
        .order_by(BossParticipation.total_damage.desc())
        .limit(10)
    )
    top_rows = top_result.all()
    total_dmg = sum(row[0].total_damage for row in top_rows) or 1
    today = datetime.now(timezone.utc).date()

    # Denní MVP
    mvp_char_id = None
    best_daily  = 0
    for row in top_rows:
        dd = row[0].daily_damage if row[0].daily_date == today else 0
        if dd > best_daily:
            best_daily  = dd
            mvp_char_id = row[0].character_id

    CLS_E = {"warrior": "⚔️", "mage": "🔮", "ranger": "🏹"}

    leaderboard = [
        {
            "rank":             i + 1,
            "name":             row[1],
            "cls_emoji":        CLS_E.get(row[2], "⚔"),
            "damage":           row[0].total_damage,
            "attacks":          row[0].attacks_count,
            "contribution_pct": round(row[0].total_damage / total_dmg * 100, 1),
            "daily_damage":     row[0].daily_damage if row[0].daily_date == today else 0,
            "is_daily_mvp":     row[0].character_id == mvp_char_id and best_daily > 0,
            "is_me":            row[0].character_id == char.id,
        }
        for i, row in enumerate(top_rows)
    ]

    return {
        "boss":        boss.to_dict(),
        "can_attack":  can_attack,
        "cd_remaining": round(cd_remaining),
        "my_damage":   participation.total_damage if participation else 0,
        "my_attacks":  participation.attacks_count if participation else 0,
        "leaderboard": leaderboard,
        "min_level":   bdef.get("min_level", 1),
        "char_level":  char.level,
    }


# ── POST /boss/attack ─────────────────────────────────────────────────────────

@router.post("/attack")
async def attack_boss(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Útok na aktuálního World Bosse. Cooldown 6h."""
    char = await _get_char(user, db)

    # with_for_update() = pessimistic lock — serializuje souběžné útoky
    # PostgreSQL: row-level lock; SQLite: serializable přes write lock
    result = await db.execute(
        select(WorldBoss)
        .where(WorldBoss.is_alive == True)
        .order_by(WorldBoss.id.desc())
        .limit(1)
        .with_for_update()
    )
    boss = result.scalar_one_or_none()

    if not boss:
        raise HTTPException(404, "Žádný aktivní boss.")

    bdef = WORLD_BOSS_DEFINITIONS.get(boss.boss_key, {})

    if char.level < bdef.get("min_level", 1):
        raise HTTPException(400, f"Potřebuješ level {bdef['min_level']} pro útok na tohoto bosse.")

    # Cooldown check
    cooldown_hours = bdef.get("attack_cooldown_hours", 6)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    part_result = await db.execute(
        select(BossParticipation).where(
            BossParticipation.boss_id == boss.id,
            BossParticipation.character_id == char.id,
        )
    )
    participation = part_result.scalar_one_or_none()

    if participation and participation.last_attack_at:
        next_attack = participation.last_attack_at + timedelta(hours=cooldown_hours)
        if next_attack > now:
            remaining_secs = int((next_attack - now).total_seconds())
            h, rem = divmod(remaining_secs, 3600)
            m, s   = divmod(rem, 60)
            raise HTTPException(400, f"Cooldown! Další útok za {h}h {m}m {s}s.")

    # Simuluj souboj hráče vs boss (jen aktuální HP bosse)
    boss_cfg = _build_boss_config(boss)
    player_cfg = await build_combatant_config(char, db)

    combat_result = simulate_unified_combat(player_cfg, boss_cfg, max_rounds=20)

    # Damage dealt = celkový damage útočníka
    damage_dealt = combat_result.total_damage_dealt

    # Atomický HP decrement — klíčový fix race condition.
    # ORM přiřazení (boss.hp_current -= dmg) by při souběžných requestech
    # použilo stale hodnotu z paměti. SQL UPDATE pracuje vždy s aktuální DB hodnotou.
    await db.execute(
        sa_update(WorldBoss)
        .where(WorldBoss.id == boss.id)
        .values(
            hp_current=case(
                (WorldBoss.hp_current <= damage_dealt, 0),
                else_=WorldBoss.hp_current - damage_dealt,
            )
        )
    )
    # Refresh — načte aktuální hp_current po atomickém updatu
    await db.refresh(boss)

    # Zkontroluj phase přechody (aktualizuj boss.current_phase)
    bdef_phases = bdef.get("phases", [])
    for phase in bdef_phases:
        if phase.phase_num not in boss.get_phases_triggered():
            if boss.hp_pct() <= phase.trigger_hp_pct:
                boss.add_phase_triggered(phase.phase_num)
                boss.current_phase = phase.phase_num

    # Aktualizuj nebo vytvoř participaci
    if not participation:
        participation = BossParticipation(
            boss_id=boss.id,
            character_id=char.id,
            total_damage=0,
            attacks_count=0,
        )
        db.add(participation)

    participation.total_damage  += damage_dealt
    participation.attacks_count += 1
    participation.last_attack_at = now

    # Denní tracking — reset při novém UTC dni
    today = now.date()
    if participation.daily_date != today:
        participation.daily_damage = 0
        participation.daily_date   = today
    participation.daily_damage += damage_dealt
    # World Event příspěvek — boss damage
    await add_world_event_contribution("boss_damage", char.id, damage_dealt, db)

    # Boss zabit? (kontrolujeme refreshnuté hp_current z DB)
    boss_killed = False
    if boss.hp_current <= 0:
        boss_killed = True
        boss.is_alive  = False
        boss.killed_at = now
        # Vypočítej odměny pro všechny participanty
        await _calculate_boss_rewards(boss, db)

    player_won = combat_result.attacker_won

    await db.commit()

    # Invalidace leaderboard cache po útoku
    from core.cache import cache as _cache
    await _cache.delete("boss:leaderboard")

    return {
        "result":        "win" if player_won else "loss",
        "player_won":    player_won,
        "damage_dealt":  damage_dealt,
        "boss_hp_now":   boss.hp_current,
        "boss_hp_max":   boss.hp_max,
        "boss_hp_pct":   round(boss.hp_pct() * 100, 1),
        "boss_killed":   boss_killed,
        "current_phase": boss.current_phase,
        "rounds":        combat_result.rounds,
        "battle_log":    combat_result.log,
        "events":        events_to_dict_list(combat_result.events),
        "player_hp_remaining": combat_result.attacker_hp_remaining,
        "player_hp_max": char.hp_max,
        "enemy_hp_max":  boss.hp_max,
    }


async def _calculate_boss_rewards(boss: WorldBoss, db: AsyncSession):
    """Vypočítá a uloží odměny pro všechny participanty zabitého bosse."""
    from datetime import date as _date_type
    bdef = WORLD_BOSS_DEFINITIONS.get(boss.boss_key, {})
    loot = bdef.get("loot_table", {})
    xp_base   = loot.get("xp_base", 500)
    gold_base = loot.get("gold_base", 300)
    bonus_pct = loot.get("bonus_gold_contribution_pct", 0.001)

    part_result = await db.execute(
        select(BossParticipation).where(BossParticipation.boss_id == boss.id)
    )
    all_parts = part_result.scalars().all()
    total_dmg = sum(p.total_damage for p in all_parts) or 1

    # Denní MVP — nejvyšší daily_damage dnes dostane +100 G bonus
    today = datetime.now(timezone.utc).date()
    mvp_part = max(
        (p for p in all_parts if p.daily_date == today and p.daily_damage > 0),
        key=lambda p: p.daily_damage,
        default=None,
    )
    mvp_char_id = mvp_part.character_id if mvp_part else None

    for part in all_parts:
        contrib_pct = part.total_damage / total_dmg  # 0.0–1.0
        # Odměna škáluje s příspěvkem — minimum 10%
        scale = max(0.10, contrib_pct)
        part.reward_xp   = int(xp_base   * scale)
        part.reward_gold = int(gold_base  * scale + gold_base * bonus_pct * contrib_pct * 100)
        if mvp_char_id and part.character_id == mvp_char_id:
            part.reward_gold += 100  # Daily MVP bonus


# ── POST /boss/claim ──────────────────────────────────────────────────────────

@router.post("/claim")
async def claim_boss_rewards(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vyzvednutí odměn po zabitém bossovi."""
    char = await _get_char(user, db)

    # Najdi nevyzvednuté odměny
    result = await db.execute(
        select(BossParticipation, WorldBoss)
        .join(WorldBoss, BossParticipation.boss_id == WorldBoss.id)
        .where(
            BossParticipation.character_id == char.id,
            BossParticipation.reward_claimed == False,
            WorldBoss.is_alive == False,
            BossParticipation.reward_gold > 0,
        )
        .order_by(WorldBoss.killed_at.desc())
        .limit(5)
    )
    rows = result.all()

    if not rows:
        raise HTTPException(400, "Žádné nevyzvednuté odměny za bossy.")

    total_xp   = 0
    total_gold = 0
    leveled_up = []

    for part, boss in rows:
        part.reward_claimed = True
        total_xp   += part.reward_xp
        total_gold += part.reward_gold

    char.xp   += total_xp
    char.gold += total_gold
    await log_gold(db, char, total_gold, GoldReason.BOSS_REWARD,
                   {"bosses_claimed": len(rows)})

    while char.xp >= xp_to_next(char.level):
        char.xp    -= xp_to_next(char.level)
        char.level += 1
        char.stat_points = (char.stat_points or 0) + 1
        leveled_up.append(char.level)
    if leveled_up:
        from routers.inventory import recalculate_with_gear
        await recalculate_with_gear(char, db)

    await db.commit()
    await db.refresh(char)

    return {
        "message":    f"Boss odměny vyzvednuty!",
        "xp_gained":  total_xp,
        "gold_gained": total_gold,
        "leveled_up":  leveled_up,
        "character":   await char_dict_with_equipment(char, db),
    }


# ── GET /boss/leaderboard ─────────────────────────────────────────────────────

@router.get("/leaderboard")
async def boss_leaderboard(db: AsyncSession = Depends(get_db)):
    """Top přispěvatelé na aktuálním aktivním bossovi. Cached 30s."""
    from core.cache import cache
    cached = await cache.get("boss:leaderboard")
    if cached is not None:
        return cached

    boss_result = await db.execute(
        select(WorldBoss).where(WorldBoss.is_alive == True).order_by(WorldBoss.id.desc()).limit(1)
    )
    boss = boss_result.scalar_one_or_none()

    if not boss:
        return {"leaderboard": [], "boss": None}

    rows_result = await db.execute(
        select(BossParticipation, Character.name, Character.cls)
        .join(Character, BossParticipation.character_id == Character.id)
        .where(BossParticipation.boss_id == boss.id)
        .order_by(BossParticipation.total_damage.desc())
        .limit(20)
    )
    rows = rows_result.all()
    total_dmg = sum(row[0].total_damage for row in rows) or 1

    CLS_E = {"warrior": "⚔️", "mage": "🔮", "ranger": "🏹"}
    today = datetime.now(timezone.utc).date()

    # Denní MVP
    mvp_char_id = None
    best_daily  = 0
    for row in rows:
        dd = row[0].daily_damage if row[0].daily_date == today else 0
        if dd > best_daily:
            best_daily  = dd
            mvp_char_id = row[0].character_id

    data = {
        "boss": boss.to_dict(),
        "leaderboard": [
            {
                "rank":             i + 1,
                "name":             row[1],
                "cls_emoji":        CLS_E.get(row[2], "⚔"),
                "damage":           row[0].total_damage,
                "attacks":          row[0].attacks_count,
                "contribution_pct": round(row[0].total_damage / total_dmg * 100, 1),
                "daily_damage":     row[0].daily_damage if row[0].daily_date == today else 0,
                "is_daily_mvp":     row[0].character_id == mvp_char_id and best_daily > 0,
            }
            for i, row in enumerate(rows)
        ],
    }
    await cache.set("boss:leaderboard", data, ttl=30)
    return data


# ── Admin: POST /boss/spawn ───────────────────────────────────────────────────

class SpawnBossRequest(BaseModel):
    boss_key:    str
    player_count: int = 10   # pro HP scaling


@router.post("/spawn")
async def spawn_boss(
    req: SpawnBossRequest,
    db: AsyncSession = Depends(get_db),
):
    """Admin endpoint: spawnuje nového world bosse."""
    if req.boss_key not in WORLD_BOSS_DEFINITIONS:
        raise HTTPException(404, f"Boss '{req.boss_key}' nenalezen.")

    # Zabij stávajícího bosse pokud existuje
    old_result = await db.execute(
        select(WorldBoss).where(WorldBoss.is_alive == True)
    )
    for old_boss in old_result.scalars().all():
        old_boss.is_alive = False

    bdef    = WORLD_BOSS_DEFINITIONS[req.boss_key]
    hp_max  = bdef["hp_base"] + bdef["hp_per_player"] * max(1, req.player_count)

    boss = WorldBoss(
        boss_key=req.boss_key,
        name=bdef["name"],
        emoji=bdef["emoji"],
        hp_current=hp_max,
        hp_max=hp_max,
        current_phase=0,
        is_alive=True,
        spawned_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(boss)
    await db.commit()
    await db.refresh(boss)

    return {"message": f"Boss '{bdef['name']}' spawnut!", "boss": boss.to_dict()}


async def _auto_spawn_boss(db: AsyncSession) -> WorldBoss | None:
    """Automaticky spawnuje prvního bosse pokud žádný není aktivní."""
    try:
        bdef   = WORLD_BOSS_DEFINITIONS["skeleton_king"]
        hp_max = bdef["hp_base"] + bdef["hp_per_player"] * 5

        boss = WorldBoss(
            boss_key="skeleton_king",
            name=bdef["name"],
            emoji=bdef["emoji"],
            hp_current=hp_max,
            hp_max=hp_max,
            current_phase=0,
            is_alive=True,
            spawned_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(boss)
        await db.commit()
        await db.refresh(boss)
        return boss
    except Exception:
        return None
