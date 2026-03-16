"""
routers/dungeon.py — Dungeon multi-stage combat systém.

Dungeon = sekvence 5 stagů se škálujícím nepřítelem.
HP hráče se přenáší mezi stagy — žádná obnova.

Endpoints:
- GET  /dungeon/list         — seznam dostupných dungeonů
- POST /dungeon/enter        — vstup do dungeonu (stage 1)
- POST /dungeon/next-stage   — pokračování na další stage
- GET  /dungeon/status       — aktuální stav dungeonu
- POST /dungeon/collect      — vyzvednutí odměn po dokončení
- POST /dungeon/abandon      — opuštění dungeonu (ztráta progress)
"""
import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, model_validator

from database import get_db
from models.user import User
from models.character import Character, xp_to_next
from models.dungeon_run import DungeonRun, DUNGEON_DEFINITIONS
from models.economy import log_gold, GoldReason
from routers.auth import get_current_user
from routers.character import char_dict_with_equipment
from game.combat_engine import (
    CombatantConfig, BossPhase, simulate_unified_combat,
    events_to_dict_list,
)
from game.loot import get_random_item_for_quest
from models.item import InventoryItem
from routers.world_event import add_world_event_contribution
from game.dungeon_modifiers import (
    apply_modifier_to_enemy,
    apply_modifier_to_player,
    get_modifier_start_statuses,
    scale_rewards,
    DUNGEON_MODIFIERS,
)
from game.set_bonuses import get_char_set_combat_effects
from models.hall_of_fallen import HallOfFallen
from game.bloodline import award_death_bloodline_xp

router = APIRouter(prefix="/dungeon", tags=["dungeon"])


# ── Permadeath helper ─────────────────────────────────────────────────────────

async def _trigger_permadeath(
    char: Character,
    enemy_name: str,
    dungeon_key: str,
    now: datetime,
    db: AsyncSession,
) -> dict:
    """
    Spustí permadeath sekvenci pro HC postavu:
    - Označí postavu jako mrtvou
    - Vytvoří HallOfFallen snapshot
    - Přidá Bloodline XP

    Volat PŘED db.commit() — caller commituje.
    Vrátí dict s výsledkem permadeath pro API response.
    """
    char.is_dead       = True
    char.died_at       = now
    char.killed_by     = enemy_name
    char.death_dungeon = dungeon_key

    # Počet dokončených dungeonů (pro Bloodline XP a HoF snapshot)
    runs_result = await db.execute(
        select(DungeonRun).where(
            DungeonRun.character_id == char.id,
            DungeonRun.status == "completed",
        )
    )
    dungeons_cleared = len(runs_result.scalars().all())

    # Délka přežití v dnech
    created_at = char.created_at if isinstance(char.created_at, datetime) else now
    days_survived = max(0, (now - created_at).days)

    # Hall of the Fallen snapshot
    hall_entry = HallOfFallen(
        user_id=char.user_id,
        character_id=char.id,
        hero_name=char.name,
        hero_cls=char.cls,
        hero_level=char.level,
        hero_faction=char.faction,
        killed_by=enemy_name,
        death_dungeon=dungeon_key,
        died_at=now,
        days_survived=days_survived,
        dungeons_cleared=dungeons_cleared,
        build_snapshot={
            "talents":   char.get_talents(),
            "subclass":  char.subclass,
            "prestige":  char.prestige_level,
            "talent_t2": char.talent_t2_key,
            "atk":       char.atk,
            "def":       char.def_,
            "hp_max":    char.hp_max,
            "spd":       char.spd,
        },
    )
    db.add(hall_entry)

    # Bloodline XP
    bloodline_result = await award_death_bloodline_xp(
        user_id=char.user_id,
        char_level=char.level,
        days_survived=days_survived,
        dungeons_cleared=dungeons_cleared,
        db=db,
    )

    return {
        "permadeath":       True,
        "hero_name":        char.name,
        "hero_level":       char.level,
        "hero_cls":         char.cls,
        "killed_by":        enemy_name,
        "death_dungeon":    dungeon_key,
        "days_survived":    days_survived,
        "dungeons_cleared": dungeons_cleared,
        "bloodline_xp_gained": bloodline_result["xp_gained"],
        "bloodline_level_up":  bloodline_result["level_ups"] > 0,
        "bloodline_new_level": bloodline_result["new_level"],
    }


# ── GET /dungeon/config ───────────────────────────────────────────────────────

@router.get("/config")
async def dungeon_config():
    """Vrátí display konfiguraci dungeonů z JSON (bez auth — statická data pro frontend)."""
    from game.config_loader import load_dungeon_config
    return load_dungeon_config()


async def _get_active_modifier(db: AsyncSession) -> dict | None:
    """Načte aktuální týdenní modifikátor. Vrátí dict efektů nebo None při chybě."""
    try:
        from routers.dungeon_modifier import ensure_active_modifier
        mod = await ensure_active_modifier(db)
        return DUNGEON_MODIFIERS.get(mod.modifier_key)
    except Exception:
        return None


async def _get_char(user: User, db: AsyncSession) -> Character:
    result = await db.execute(select(Character).where(Character.user_id == user.id))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena.")
    if char.is_dead:
        raise HTTPException(403, f"Tato postava zemřela. Zabit: {char.killed_by or 'Neznámý nepřítel'}")
    return char


_DIFFICULTY_CAP = 3.5   # absolutní strop — stage 18+ nedostane vyšší mult
_DIFFICULTY_STEP = 0.15  # přírůstek na stage (lineární část)


def _stage_difficulty_mult(stage_num: int) -> float:
    """
    Bezpečná capped-linear křivka pro dungeony bez explicitního enemy_mult.

    Vzorec: min(cap, 1 + (stage - 1) * step)
      stage  1 → 1.00  (baseline)
      stage  5 → 1.60
      stage 10 → 2.35
      stage 18 → 3.50  (dosažen cap)
      stage 100 → 3.50  (cap drží — žádná exploze)
    """
    return min(_DIFFICULTY_CAP, 1.0 + (stage_num - 1) * _DIFFICULTY_STEP)


def _build_stage_enemy(
    dungeon_key: str, stage_def: dict, char_level: int,
    modifier: dict | None = None,
    secret_mult: float = 1.0,
) -> CombatantConfig:
    """Sestaví CombatantConfig pro nepřítele v daném stage s aplikovaným modifikátorem."""
    # Explicitní enemy_mult z definice má přednost; fallback = bezpečná auto-křivka
    explicit_mult = stage_def.get("enemy_mult")
    stage_num     = stage_def.get("stage_num", 1)
    mult          = (explicit_mult if explicit_mult is not None else _stage_difficulty_mult(stage_num)) * secret_mult
    base_lvl  = max(char_level, DUNGEON_DEFINITIONS[dungeon_key].get("min_level", 1))
    is_boss   = stage_def.get("type") in ("boss", "miniboss")
    phases    = stage_def.get("phases", [])
    specials  = stage_def.get("special_abilities", [])

    hp  = int(60  * base_lvl * mult)
    atk = int(9   * base_lvl * mult)
    def_= int(5   * base_lvl * mult)
    spd = int(7   * base_lvl * mult * 0.8)

    # Aplikuj týdenní modifikátor na stats nepřítele
    hp, atk, def_, spd = apply_modifier_to_enemy(modifier, hp, atk, def_, spd, is_boss=is_boss)

    # Start status nepřítele z modifikátoru
    enemy_statuses = []
    if modifier:
        start_statuses = get_modifier_start_statuses(modifier)
        if start_statuses["enemy"]:
            enemy_statuses = [start_statuses["enemy"]]

    return CombatantConfig(
        name=stage_def["enemy_name"],
        hp=hp,
        atk=atk,
        def_=def_,
        spd=spd,
        luck=int(3 * mult),
        level=base_lvl,
        cls="",
        mp=0,
        is_boss=is_boss,
        phases=phases,
        special_abilities=specials,
        modifier_statuses=enemy_statuses,
    )


# ── GET /dungeon/list ─────────────────────────────────────────────────────────

@router.get("/list")
async def list_dungeons(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Seznam dostupných dungeonů s cooldown info."""
    char = await _get_char(user, db)
    now  = datetime.now(timezone.utc).replace(tzinfo=None)

    # Načti posledního aktivního/dokončeného runu pro každý dungeon
    runs_result = await db.execute(
        select(DungeonRun)
        .where(
            DungeonRun.character_id == char.id,
            DungeonRun.status.in_(["active", "completed", "collecting"]),
        )
        .order_by(DungeonRun.id.desc())
    )
    recent_runs = {r.dungeon_key: r for r in runs_result.scalars().all()}

    # Načti aktivní modifikátor pro zobrazení v listu
    modifier_data = await _get_active_modifier(db)
    modifier_info = None
    if modifier_data:
        from routers.dungeon_modifier import ensure_active_modifier
        try:
            mod_obj = await ensure_active_modifier(db)
            modifier_info = mod_obj.to_dict()
            modifier_info["seconds_remaining"] = max(
                0, int((mod_obj.week_end - now).total_seconds())
            )
        except Exception:
            pass

    dungeons = []
    for key, ddef in DUNGEON_DEFINITIONS.items():
        run = recent_runs.get(key)

        # Cooldown check
        cooldown_until = None
        cd_remaining   = 0
        can_enter      = True
        if run and run.cooldown_until and run.cooldown_until > now:
            cooldown_until = run.cooldown_until
            cd_remaining   = int((cooldown_until - now).total_seconds())
            can_enter      = False

        # Active run check
        active_run = run if (run and run.status == "active") else None

        # Scaled reward preview (s modifikátorem)
        comp_xp, comp_gold = scale_rewards(
            modifier_data,
            ddef["rewards"]["completion_xp"],
            ddef["rewards"]["completion_gold"],
        )

        dungeons.append({
            "key":              key,
            "name":             ddef["name"],
            "emoji":            ddef["emoji"],
            "description":      ddef["description"],
            "min_level":        ddef["min_level"],
            "stages":           len(ddef["stages"]),
            "cooldown_hours":   ddef["cooldown_hours"],
            "can_enter":        can_enter and char.level >= ddef["min_level"],
            "level_required":   char.level < ddef["min_level"],
            "cooldown_until":   cooldown_until.isoformat() if cooldown_until else None,
            "cd_remaining":     cd_remaining,
            "has_active_run":   active_run is not None,
            "active_run_stage": active_run.current_stage if active_run else None,
            "rewards_preview":  {
                "completion_xp":   comp_xp,
                "completion_gold": comp_gold,
            },
        })

    return {
        "dungeons":   dungeons,
        "char_level": char.level,
        "modifier":   modifier_info,
    }


# ── POST /dungeon/enter ───────────────────────────────────────────────────────

class EnterDungeonRequest(BaseModel):
    dungeon_id: str | None = None   # preferovaný způsob výběru dungeonu
    dungeon_key: str | None = None  # deprecated — zpětná kompatibilita
    strategy: str = "balanced"

    @model_validator(mode="after")
    def resolve_dungeon_id(self) -> "EnterDungeonRequest":
        """dungeon_id má přednost; dungeon_key slouží jako fallback pro staré klienty."""
        if not self.dungeon_id:
            if not self.dungeon_key:
                raise ValueError("dungeon_id (nebo dungeon_key) je povinný.")
            self.dungeon_id = self.dungeon_key
        return self


@router.post("/enter")
async def enter_dungeon(
    req: EnterDungeonRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vstup do dungeonu — začne stage 1."""
    char = await _get_char(user, db)

    if req.dungeon_id not in DUNGEON_DEFINITIONS:
        raise HTTPException(404, "Dungeon nenalezen.")

    ddef = DUNGEON_DEFINITIONS[req.dungeon_id]
    now  = datetime.now(timezone.utc).replace(tzinfo=None)

    if char.level < ddef["min_level"]:
        raise HTTPException(400, f"Potřebuješ level {ddef['min_level']}.")

    # Kontrola cooldownu
    runs_result = await db.execute(
        select(DungeonRun)
        .where(
            DungeonRun.character_id == char.id,
            DungeonRun.dungeon_key  == req.dungeon_id,
        )
        .order_by(DungeonRun.id.desc())
        .limit(1)
    )
    last_run = runs_result.scalar_one_or_none()

    if last_run:
        if last_run.status == "active":
            raise HTTPException(400, "Dungeon již probíhá. Dokončte nebo opusťte ho.")
        if last_run.status == "completed" and not last_run.reward_claimed:
            raise HTTPException(400, "Nejdřív vyzvedni odměny za předchozí dokončený dungeon.")
        if last_run.cooldown_until and last_run.cooldown_until > now:
            remaining = int((last_run.cooldown_until - now).total_seconds())
            h, rem = divmod(remaining, 3600)
            m, s   = divmod(rem, 60)
            raise HTTPException(400, f"Cooldown! Dungeon dostupný za {h}h {m}m {s}s.")

    # Načti týdenní modifikátor
    modifier = await _get_active_modifier(db)
    mod_statuses = get_modifier_start_statuses(modifier)

    # Simuluj stage 1
    stage_def   = ddef["stages"][0]
    enemy_cfg   = _build_stage_enemy(req.dungeon_id, stage_def, char.level, modifier=modifier)

    # Aplikuj modifikátor na hráčské stats
    _p_hp, _p_atk, _p_def, _p_spd, _p_mp = apply_modifier_to_player(
        modifier, char.hp_max, char.atk, char.def_, char.spd, char.mp_max
    )
    _set_fx = await get_char_set_combat_effects(char, db)
    player_cfg  = CombatantConfig(
        name=char.name, hp=_p_hp, atk=_p_atk, def_=_p_def,
        spd=_p_spd, luck=char.luck, level=char.level, cls=char.cls, mp=_p_mp,
        hp_max_override=_p_hp,
        strategy=req.strategy,
        talents=char.get_talents(),
        subclass=char.subclass or "",
        modifier_statuses=[mod_statuses["player"]] if mod_statuses["player"] else [],
        talent_t2=char.talent_t2_key or "",
        set_bonuses=_set_fx,
    )

    combat = simulate_unified_combat(player_cfg, enemy_cfg, max_rounds=20)

    # Vytvoř nový run
    stage1_won = combat.attacker_won and combat.attacker_hp_remaining > 0
    run = DungeonRun(
        character_id=char.id,
        dungeon_key=req.dungeon_id,
        current_stage=1,
        total_stages=len(ddef["stages"]),
        player_hp_current=combat.attacker_hp_remaining,
        player_hp_max=char.hp_max,
        status="active" if stage1_won else "failed",
        started_at=now,
        last_stage_at=now,
        cooldown_until=None if stage1_won else now + timedelta(hours=ddef["cooldown_hours"] // 2),
    )

    stage_rewards = ddef["rewards"]
    base_xp   = stage_rewards["xp_per_stage"][0]
    base_gold = stage_rewards["gold_per_stage"][0]
    if combat.attacker_won:
        scaled_xp, scaled_gold = scale_rewards(modifier, base_xp, base_gold)
        run.reward_xp   = scaled_xp
        run.reward_gold = scaled_gold
    else:
        scaled_xp, _ = scale_rewards(modifier, base_xp // 4, 0)
        run.reward_xp   = scaled_xp
        run.reward_gold = 0

    run.append_stage_log(1, combat.log, events_to_dict_list(combat.events))
    db.add(run)

    # Weekly hooky — kills za vítězství v stage 1
    if combat.attacker_won:
        if char.guild_id:
            from routers.guild import increment_guild_weekly
            await increment_guild_weekly(char.guild_id, "kills", 1, char.id, db)
        from routers.weekly_quest import increment_weekly_board
        await increment_weekly_board(char.id, "kills", 1, db)
        from routers.season_pass import add_season_xp
        await add_season_xp(char.id, "dungeon_stage", db)
        # Durability loss
        from routers.inventory import _decrease_equipped_durability, DURABILITY_LOSS_DUNGEON
        await _decrease_equipped_durability(char, DURABILITY_LOSS_DUNGEON, db)

    # HC permadeath — postava zemřela na stage 1
    permadeath_data = None
    if not stage1_won and char.is_hardcore and combat.attacker_hp_remaining <= 0:
        permadeath_data = await _trigger_permadeath(
            char, stage_def["enemy_name"], req.dungeon_id, now, db
        )

    try:
        await db.commit()
        await db.refresh(run)
    except Exception:
        await db.rollback()
        raise HTTPException(500, "Chyba při vytváření dungeon runu — zkus znovu.")

    return {
        "run":           run.to_dict(),
        "stage_num":     1,
        "stage_name":    stage_def["name"],
        "enemy_name":    stage_def["enemy_name"],
        "enemy_hp_max":  enemy_cfg.hp,
        "result":        "win" if combat.attacker_won else "loss",
        "player_won":    combat.attacker_won,
        "player_hp_remaining": combat.attacker_hp_remaining,
        "rounds":        combat.rounds,
        "battle_log":    combat.log,
        "events":        events_to_dict_list(combat.events),
        "can_continue":  stage1_won,
        "next_stage":    2 if (stage1_won and len(ddef["stages"]) > 1) else None,
        "stage_xp":      run.reward_xp,
        "stage_gold":    run.reward_gold if combat.attacker_won else 0,
        **(permadeath_data or {}),
    }


# ── POST /dungeon/next-stage ──────────────────────────────────────────────────

# Multiplikátory pro tajný průchod
_SECRET_ENEMY_MULT   = 1.6   # nepřítel je o 60% silnější
_SECRET_REWARD_MULT  = 2.0   # double odměna


class NextStageRequest(BaseModel):
    run_id: int
    accept_secret: bool | None = None   # None = automatický postup, True/False = volba hráče


@router.post("/next-stage")
async def next_stage(
    req: NextStageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pokračuje na další stage. HP hráče se přenáší."""
    char = await _get_char(user, db)

    run_result = await db.execute(
        select(DungeonRun).where(
            DungeonRun.id == req.run_id,
            DungeonRun.character_id == char.id,
        ).with_for_update()  # pessimistic lock — serializuje souběžné requesty na stejný run
    )
    run = run_result.scalar_one_or_none()

    if not run:
        raise HTTPException(404, "Dungeon run nenalezen.")
    if run.status != "active":
        raise HTTPException(400, f"Dungeon run není aktivní (status: {run.status}).")
    if run.player_hp_current <= 0:
        raise HTTPException(400, "Hráč nemá HP — dungeon selhal.")

    ddef = DUNGEON_DEFINITIONS.get(run.dungeon_key)
    if not ddef:
        raise HTTPException(400, f"Neznámý dungeon '{run.dungeon_key}' — data mohla být aktualizována. Opusťte dungeon.")
    next_stage_num = run.current_stage + 1

    if next_stage_num > run.total_stages:
        raise HTTPException(400, "Dungeon je již dokončen — vyzvedni odměny.")

    stage_def  = ddef["stages"][next_stage_num - 1]  # 0-indexed

    # ── Tajný průchod — stage 3 ──────────────────────────────────────────────
    # Fáze A: roll (první volání na stage 3, ještě není rozhodnutí)
    if next_stage_num == 3 and not run.secret_path_offered and req.accept_secret is None:
        modifier_for_roll = await _get_active_modifier(db)
        chance = modifier_for_roll.get("secret_path_chance", 0.40) if modifier_for_roll else 0.40
        if random.random() < chance:
            run.secret_path_offered = True
            try:
                await db.commit()
                await db.refresh(run)
            except Exception:
                await db.rollback()
                raise HTTPException(500, "Chyba při uložení tajného průchodu.")
            return {
                "run":               run.to_dict(),
                "requires_choice":   True,
                "secret_path_chance": chance,
                "stage_num":         next_stage_num,
                "stage_name":        stage_def["name"],
            }
        # Roll selhal — pokračujeme normálně (secret_path_offered zůstane False)

    # Fáze B: hráč se rozhodl (nebo roll selhal)
    is_secret = run.secret_path_offered and req.accept_secret is True

    # Načti týdenní modifikátor
    modifier = await _get_active_modifier(db)
    mod_statuses = get_modifier_start_statuses(modifier)

    enemy_cfg  = _build_stage_enemy(run.dungeon_key, stage_def, char.level, modifier=modifier,
                                    secret_mult=_SECRET_ENEMY_MULT if is_secret else 1.0)

    # Aplikuj modifikátor na hráčské stats (HP přenos zůstává, ale ostatní stats se škálují)
    _p_hp, _p_atk, _p_def, _p_spd, _p_mp = apply_modifier_to_player(
        modifier, char.hp_max, char.atk, char.def_, char.spd, char.mp_max
    )
    # HP se přenáší z předchozího stage — škálujeme poměrem
    _hp_ratio = run.player_hp_current / max(1, run.player_hp_max)
    _carried_hp = max(1, int(_p_hp * _hp_ratio))

    # Hráč vstupuje s přeneseným HP (přenos z předchozího stage)
    _set_fx = await get_char_set_combat_effects(char, db)
    player_cfg = CombatantConfig(
        name=char.name,
        hp=_carried_hp,              # přenesené HP (škálované)!
        atk=_p_atk, def_=_p_def,
        spd=_p_spd, luck=char.luck, level=char.level, cls=char.cls, mp=_p_mp,
        hp_max_override=_p_hp,       # max HP pro HP bar (škálované)
        talents=char.get_talents(),
        subclass=char.subclass or "",
        modifier_statuses=[mod_statuses["player"]] if mod_statuses["player"] else [],
        talent_t2=char.talent_t2_key or "",
        set_bonuses=_set_fx,
    )

    combat = simulate_unified_combat(player_cfg, enemy_cfg, max_rounds=20)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    run.current_stage     = next_stage_num
    run.last_stage_at     = now
    # Zpět škálujeme HP na původní hp_max základ (pro konzistentní ukládání)
    if _p_hp > 0:
        run.player_hp_current = max(0, int(combat.attacker_hp_remaining * run.player_hp_max / _p_hp))
    else:
        run.player_hp_current = combat.attacker_hp_remaining

    # Nastav secret_path_taken pokud hráč přijal tajný průchod
    if is_secret and combat.attacker_won:
        run.secret_path_taken = True

    stage_rewards = ddef["rewards"]
    base_stage_xp   = stage_rewards["xp_per_stage"][next_stage_num - 1]
    base_stage_gold = stage_rewards["gold_per_stage"][next_stage_num - 1]

    # Secret path: double odměna za úspěch
    if is_secret and combat.attacker_won:
        base_stage_xp   = int(base_stage_xp   * _SECRET_REWARD_MULT)
        base_stage_gold = int(base_stage_gold  * _SECRET_REWARD_MULT)

    if combat.attacker_won:
        stage_xp_reward, stage_gold_reward = scale_rewards(modifier, base_stage_xp, base_stage_gold)
    else:
        stage_xp_reward, _ = scale_rewards(modifier, base_stage_xp // 4, 0)
        stage_gold_reward = 0

    run.reward_xp   += stage_xp_reward
    run.reward_gold += stage_gold_reward

    run.append_stage_log(next_stage_num, combat.log, events_to_dict_list(combat.events))

    # Dungeon dokončen?
    dungeon_completed = False
    if next_stage_num == run.total_stages and combat.attacker_won:
        dungeon_completed = True
        run.status       = "completed"
        run.completed_at = now
        comp_xp, comp_gold = scale_rewards(modifier, stage_rewards["completion_xp"], stage_rewards["completion_gold"])
        run.reward_xp    += comp_xp
        run.reward_gold  += comp_gold
        run.cooldown_until = now + timedelta(hours=ddef["cooldown_hours"])
    elif not combat.attacker_won or combat.attacker_hp_remaining <= 0:
        run.status = "failed"
        run.cooldown_until = now + timedelta(hours=ddef["cooldown_hours"] // 2)

    # Weekly hooky — kills a dungeons
    if combat.attacker_won:
        try:
            if char.guild_id:
                from routers.guild import increment_guild_weekly
                await increment_guild_weekly(char.guild_id, "kills", 1, char.id, db)
                if dungeon_completed:
                    await increment_guild_weekly(char.guild_id, "dungeons", 1, char.id, db)
            from routers.weekly_quest import increment_weekly_board
            await increment_weekly_board(char.id, "kills", 1, db)
            if dungeon_completed:
                await increment_weekly_board(char.id, "dungeons", 1, db)
            from routers.season_pass import add_season_xp
            await add_season_xp(char.id, "dungeon_stage", db)
            if dungeon_completed:
                await add_season_xp(char.id, "dungeon_complete", db)
            # Durability loss
            from routers.inventory import _decrease_equipped_durability, DURABILITY_LOSS_DUNGEON
            await _decrease_equipped_durability(char, DURABILITY_LOSS_DUNGEON, db)
        except Exception as _hook_err:
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "Dungeon next_stage weekly hook failed (non-critical, stage %s): %s",
                next_stage_num, _hook_err
            )

    # HC permadeath — postava zemřela na tomto stage
    permadeath_data = None
    if run.status == "failed" and char.is_hardcore and combat.attacker_hp_remaining <= 0:
        permadeath_data = await _trigger_permadeath(
            char, stage_def["enemy_name"], run.dungeon_key, now, db
        )

    try:
        await db.commit()
        await db.refresh(run)
    except Exception:
        await db.rollback()
        raise HTTPException(500, "Chyba při ukládání postupu dungeonu — zkus znovu.")

    return {
        "run":           run.to_dict(),
        "stage_num":     next_stage_num,
        "stage_name":    stage_def["name"],
        "enemy_name":    stage_def["enemy_name"],
        "enemy_hp_max":  enemy_cfg.hp,
        "result":        "win" if combat.attacker_won else "loss",
        "player_won":    combat.attacker_won,
        "player_hp_remaining": combat.attacker_hp_remaining,
        "rounds":        combat.rounds,
        "battle_log":    combat.log,
        "events":        events_to_dict_list(combat.events),
        "dungeon_completed": dungeon_completed,
        "can_continue":  (combat.attacker_won
                          and combat.attacker_hp_remaining > 0
                          and next_stage_num < run.total_stages),
        "next_stage":    (next_stage_num + 1
                          if (combat.attacker_won and next_stage_num < run.total_stages)
                          else None),
        "stage_xp":      stage_xp_reward,
        "stage_gold":    stage_gold_reward,
        "was_secret":    is_secret,
        "requires_choice": False,
        **(permadeath_data or {}),
    }


# ── GET /dungeon/status ───────────────────────────────────────────────────────

@router.get("/status")
async def dungeon_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aktuální stav dungeon runu hráče."""
    char = await _get_char(user, db)

    result = await db.execute(
        select(DungeonRun)
        .where(DungeonRun.character_id == char.id)
        .order_by(DungeonRun.id.desc())
        .limit(1)
    )
    run = result.scalar_one_or_none()

    if not run:
        return {"run": None, "has_active": False}

    return {
        "run":        run.to_dict(),
        "has_active": run.status == "active",
        "can_claim":  run.status == "completed" and not run.reward_claimed,
    }


# ── POST /dungeon/collect ─────────────────────────────────────────────────────

class CollectDungeonRequest(BaseModel):
    run_id: int


@router.post("/collect")
async def collect_dungeon(
    req: CollectDungeonRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vyzvednutí odměn za dokončený dungeon."""
    char = await _get_char(user, db)

    run_result = await db.execute(
        select(DungeonRun).where(
            DungeonRun.id == req.run_id,
            DungeonRun.character_id == char.id,
        ).with_for_update()  # serializuje souběžné collect requesty — zabrání double-claim
    )
    run = run_result.scalar_one_or_none()

    if not run:
        raise HTTPException(404, "Dungeon run nenalezen.")
    if run.status not in ("completed", "failed"):
        raise HTTPException(400, "Dungeon ještě probíhá.")
    if run.reward_claimed:
        raise HTTPException(400, "Odměny již byly vyzvednuty.")

    # Snapshot hodnot před jakoukoliv mutací — zabrání stale read po db.refresh
    xp_gained   = run.reward_xp
    gold_gained = run.reward_gold

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    ddef_collect = DUNGEON_DEFINITIONS.get(run.dungeon_key, {})
    cd_hours = ddef_collect.get("cooldown_hours", 24)
    if not run.cooldown_until:
        run.cooldown_until = (
            now + timedelta(hours=cd_hours)
            if run.status == "completed"
            else now + timedelta(hours=cd_hours // 2)
        )

    run.reward_claimed = True
    char.xp   += xp_gained
    char.gold += gold_gained
    await log_gold(db, char, gold_gained, GoldReason.DUNGEON_REWARD,
                   {"dungeon_run_id": run.id, "dungeon_key": run.dungeon_key})

    leveled_up = []
    while char.xp >= xp_to_next(char.level):
        char.xp    -= xp_to_next(char.level)
        char.level += 1
        char.stat_points = (char.stat_points or 0) + 1
        char.recalculate_stats()
        leveled_up.append(char.level)

    # World Event příspěvek — dungeon clear
    if run.status == "completed":
        await add_world_event_contribution("dungeon_clears", char.id, 1, db)

    # Bonus item drop za plné dokončení
    gained_item = None
    if run.status == "completed":
        ddef = DUNGEON_DEFINITIONS.get(run.dungeon_key, {})
        drop_item = await get_random_item_for_quest(db, "boss", char.level)
        if drop_item:
            inv_result = await db.execute(
                select(InventoryItem).where(
                    InventoryItem.character_id == char.id,
                    InventoryItem.item_id == drop_item.id,
                )
            )
            inv_item = inv_result.scalar_one_or_none()
            if inv_item:
                inv_item.quantity += 1
            else:
                inv_item = InventoryItem(
                    character_id=char.id,
                    item_id=drop_item.id,
                    quantity=1,
                )
                db.add(inv_item)
            gained_item = drop_item.to_dict()

    try:
        await db.commit()
        await db.refresh(char)
        await db.refresh(run)
    except Exception:
        await db.rollback()
        raise HTTPException(500, "Chyba při vyzvednutí odměn — zkus znovu.")

    return {
        "message":     "Dungeon odměny vyzvednuty!",
        "completed":   run.status == "completed",
        "xp_gained":   xp_gained,
        "gold_gained": gold_gained,
        "item":        gained_item,
        "leveled_up":  leveled_up,
        "character":   await char_dict_with_equipment(char, db),
    }


# ── POST /dungeon/abandon ─────────────────────────────────────────────────────

class AbandonDungeonRequest(BaseModel):
    run_id: int


@router.post("/abandon")
async def abandon_dungeon(
    req: AbandonDungeonRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Opustí aktivní dungeon. Krátký cooldown, žádné odměny."""
    char = await _get_char(user, db)

    run_result = await db.execute(
        select(DungeonRun).where(
            DungeonRun.id == req.run_id,
            DungeonRun.character_id == char.id,
        )
    )
    run = run_result.scalar_one_or_none()

    if not run or run.status != "active":
        raise HTTPException(400, "Žádný aktivní dungeon k opuštění.")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    ddef = DUNGEON_DEFINITIONS.get(run.dungeon_key, {})

    run.status = "failed"

    # Vyplať nashromážděné stage odměny (stages 1 až N-1) místo jejich smazání
    char_result = await db.execute(select(Character).where(Character.user_id == user.id))
    char = char_result.scalar_one_or_none()
    partial_xp   = run.reward_xp
    partial_gold = run.reward_gold
    if char and (partial_xp > 0 or partial_gold > 0):
        char.xp   += partial_xp
        char.gold += partial_gold
        if partial_gold > 0:
            await log_gold(db, char, partial_gold, GoldReason.DUNGEON_REWARD,
                           {"dungeon_run_id": run.id, "dungeon_key": run.dungeon_key, "partial": True})
        while char.xp >= xp_to_next(char.level):
            char.xp    -= xp_to_next(char.level)
            char.level += 1
            char.stat_points = (char.stat_points or 0) + 1
            char.recalculate_stats()

    run.reward_xp      = 0
    run.reward_gold    = 0
    run.reward_claimed = True  # prevent collect
    run.cooldown_until = now + timedelta(hours=ddef.get("cooldown_hours", 24) // 4)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(500, "Chyba při opouštění dungeonu — zkus znovu.")
    return {"message": "Dungeon opuštěn.", "partial_xp": partial_xp, "partial_gold": partial_gold}
