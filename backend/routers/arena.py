"""
routers/arena.py — Aréna PvP systém
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, timezone

from database import get_db
from models.user import User
from models.character import Character, xp_to_next
from models.arena import ArenaMatch, Season, SeasonResult
from models.economy import log_gold, GoldReason
from models.notification import Notification, NotifType
from game.combat_engine import CombatantConfig, simulate_unified_combat, events_to_dict_list
from game.experiments import get_experiment_overrides, apply_overrides_to_engine, apply_overrides_to_router
from game.achievements import check_and_award
from game.set_bonuses import get_char_set_combat_effects
from models.guild import Guild
from game.guild_xp import award_guild_xp
from game.season import process_expired_season, ensure_active_season
from game.professions import add_resonance_to_equipped_runes
from routers.auth import get_current_user
from routers.character import char_dict_with_equipment

router = APIRouter(prefix="/arena", tags=["arena"])


class ArenaAttackBody(BaseModel):
    strategy: str = "balanced"

_ELO_K = 32


def _calc_elo_change(attacker_elo: int, defender_elo: int,
                     attacker_won: bool) -> tuple[int, int]:
    """Vrátí (attacker_elo_change, defender_elo_change) dle ELO formule."""
    expected_a = 1 / (1 + 10 ** ((defender_elo - attacker_elo) / 400))
    actual_a   = 1.0 if attacker_won else 0.0

    change_a = int(_ELO_K * (actual_a - expected_a))
    change_d = int(_ELO_K * ((1.0 - actual_a) - (1.0 - expected_a)))

    # Minimální pohyb ±3
    change_a = max(3, change_a)  if attacker_won  else min(-3, change_a)
    change_d = max(3, change_d)  if not attacker_won else min(-3, change_d)

    return change_a, change_d


ARENA_COOLDOWN_MINUTES = 5   # min. pauza mezi útoky na stejného hráče
ARENA_ATTACK_COOLDOWN_MINUTES = 5  # globální cooldown po každém útoku
GOLD_REWARD_WIN  = 50
GOLD_REWARD_LOSS = 10
ARENA_DAILY_GOLD_CAP = 500  # max G z arény za den


def _reset_arena_gold_if_new_day(char: "Character") -> None:
    """Resetuje arena_gold_today pokud nastalo nové UTC datum."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if char.arena_gold_date != today:
        char.arena_gold_today = 0
        char.arena_gold_date  = today


async def _get_char(user: User, db: AsyncSession) -> Character:
    result = await db.execute(select(Character).where(Character.user_id == user.id))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena.")
    return char


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/opponents")
async def get_opponents(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí seznam hráčů vhodných pro PvP (podobné ELO ±300)."""
    char = await _get_char(user, db)
    _reset_arena_gold_if_new_day(char)

    result = await db.execute(
        select(Character).where(
            and_(
                Character.id != char.id,
                Character.arena_rank >= max(100, char.arena_rank - 300),
                Character.arena_rank <= char.arena_rank + 300,
            )
        ).order_by(Character.arena_rank.desc()).limit(10)
    )
    opponents = result.scalars().all()

    # Pokud není dost hráčů v rozsahu, vrať všechny kromě sebe
    if len(opponents) < 3:
        result2 = await db.execute(
            select(Character).where(Character.id != char.id)
            .order_by(Character.arena_rank.desc()).limit(10)
        )
        opponents = result2.scalars().all()

    CLS_N = {"warrior": "Válečník", "mage": "Mág", "ranger": "Lovec"}
    CLS_E = {"warrior": "⚔️", "mage": "🔮", "ranger": "🏹"}

    def win_chance(me: Character, opp: Character) -> float:
        """Odhad šance na výhru na základě stats."""
        my_power  = me.atk  + me.def_ + me.hp_max // 10 + me.spd
        opp_power = opp.atk + opp.def_ + opp.hp_max // 10 + opp.spd
        if my_power + opp_power == 0:
            return 0.5
        return round(my_power / (my_power + opp_power), 2)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cd_until = char.arena_cooldown_until
    cd_active = cd_until is not None and cd_until > now
    cd_seconds = max(0.0, (cd_until - now).total_seconds()) if cd_active else 0.0

    return {
        "opponents": [
            {
                "id":         o.id,
                "name":       o.name,
                "cls":        o.cls,
                "cls_name":   CLS_N.get(o.cls, o.cls),
                "cls_emoji":  CLS_E.get(o.cls, "⚔"),
                "level":      o.level,
                "arena_rank": o.arena_rank,
                "wins":       o.arena_wins,
                "losses":     o.arena_losses,
                "atk":        o.atk,
                "def":        o.def_,
                "hp":         o.hp_max,
                "spd":        o.spd,
                "win_chance": win_chance(char, o),
                "appearance": o.get_appearance(),
            }
            for o in opponents
        ],
        "my_rank":          char.arena_rank,
        "my_wins":          char.arena_wins,
        "my_losses":        char.arena_losses,
        "cooldown_until":   cd_until.isoformat() + "Z" if cd_active else None,
        "cooldown_seconds": round(cd_seconds),
        "arena_gold_today": char.arena_gold_today,
        "arena_daily_cap":  ARENA_DAILY_GOLD_CAP,
    }


@router.post("/attack/{defender_id}")
async def attack(
    defender_id: int,
    body: Optional[ArenaAttackBody] = Body(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Zaútočí na hráče. Simuluje PvP souboj a aktualizuje ELO."""
    # Auto-check expirace sezóny
    await process_expired_season(db)

    char = await _get_char(user, db)

    if char.id == defender_id:
        raise HTTPException(400, "Nemůžeš bojovat sám se sebou.")

    # Reset denního gold counteru pokud je nový den
    _reset_arena_gold_if_new_day(char)

    # Cooldown check
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if char.arena_cooldown_until and char.arena_cooldown_until > now:
        remaining = int((char.arena_cooldown_until - now).total_seconds())
        mins, secs = divmod(remaining, 60)
        raise HTTPException(400, f"Cooldown! Další útok za {mins}:{secs:02d}.")

    # Načti obránce
    def_res = await db.execute(select(Character).where(Character.id == defender_id))
    defender = def_res.scalar_one_or_none()
    if not defender:
        raise HTTPException(404, "Soupeř nenalezen.")

    # Simuluj souboj
    _strategy = (body.strategy if body else "balanced")
    _atk_set_fx = await get_char_set_combat_effects(char, db)
    _def_set_fx = await get_char_set_combat_effects(defender, db)
    # Načti experiment overrides pro útočícího hráče
    _exp_overrides = await get_experiment_overrides(char.experiment_group or 0, db)
    _engine_ov     = apply_overrides_to_engine(_exp_overrides)
    _router_ov     = apply_overrides_to_router(_exp_overrides)
    atk_cfg = CombatantConfig(
        name=char.name, hp=char.hp_max, atk=char.atk,
        def_=char.def_, spd=char.spd, luck=char.luck, level=char.level,
        cls=char.cls, mp=char.mp_max,
        strategy=_strategy,
        talents=char.get_talents(),
        subclass=char.subclass or "",
        talent_t2=char.talent_t2_key or "",
        set_bonuses=_atk_set_fx,
        experiment_overrides=_engine_ov,
    )
    def_cfg = CombatantConfig(
        name=defender.name, hp=defender.hp_max, atk=defender.atk,
        def_=defender.def_, spd=defender.spd, luck=defender.luck, level=defender.level,
        cls=defender.cls, mp=defender.mp_max,
        subclass=defender.subclass or "",
        talent_t2=defender.talent_t2_key or "",
        set_bonuses=_def_set_fx,
    )

    result = simulate_unified_combat(atk_cfg, def_cfg, max_rounds=20)
    attacker_won = result.attacker_won

    # ELO změna
    elo_a, elo_d = _calc_elo_change(char.arena_rank, defender.arena_rank, attacker_won)

    # Aktualizuj stats
    char.arena_rank   = max(100, char.arena_rank + elo_a)
    defender.arena_rank = max(100, defender.arena_rank + elo_d)

    # Výpočet gold odměny s respektem denního capu (+ A/B gold_reward_win multiplier)
    _gold_mult = float(_router_ov.get("gold_reward_win", 1.0))
    _effective_win_gold = max(1, int(GOLD_REWARD_WIN * _gold_mult))
    remaining_cap = max(0, ARENA_DAILY_GOLD_CAP - char.arena_gold_today)
    actual_win_gold  = min(_effective_win_gold, remaining_cap)
    actual_loss_gold = GOLD_REWARD_LOSS  # loss gold nemá cap

    if attacker_won:
        char.arena_wins       += 1
        defender.arena_losses += 1
        char.gold             += actual_win_gold
        char.arena_gold_today += actual_win_gold
        defender.gold         += actual_loss_gold
        if actual_win_gold > 0:
            await log_gold(db, char, actual_win_gold, GoldReason.ARENA_REWARD,
                           {"vs": defender.name, "result": "win", "capped": actual_win_gold < GOLD_REWARD_WIN})
        await log_gold(db, defender, actual_loss_gold, GoldReason.ARENA_REWARD, {"vs": char.name, "result": "loss"})
        if char.guild_id:
            g_res = await db.execute(select(Guild).where(Guild.id == char.guild_id))
            g = g_res.scalar_one_or_none()
            if g:
                award_guild_xp(g, 15)
    else:
        char.arena_losses   += 1
        defender.arena_wins += 1
        char.gold           += actual_loss_gold
        defender.gold       += GOLD_REWARD_WIN
        defender.arena_gold_today += GOLD_REWARD_WIN
        await log_gold(db, char,     actual_loss_gold,  GoldReason.ARENA_REWARD, {"vs": defender.name, "result": "loss"})
        await log_gold(db, defender, GOLD_REWARD_WIN,   GoldReason.ARENA_REWARD, {"vs": char.name,     "result": "win"})
        if defender.guild_id:
            g_res = await db.execute(select(Guild).where(Guild.id == defender.guild_id))
            g = g_res.scalar_one_or_none()
            if g:
                award_guild_xp(g, 15)

    # XP za arénu
    xp_gained = (20 + char.level * 3) if attacker_won else (8 + char.level)
    char.xp += xp_gained

    # Level-up loop
    leveled_up = []
    while char.xp >= xp_to_next(char.level):
        char.xp    -= xp_to_next(char.level)
        char.level += 1
        char.stat_points = (char.stat_points or 0) + 1
        char.recalculate_stats()
        leveled_up.append(char.level)

    # Ulož zápas
    match = ArenaMatch(
        attacker_id=char.id,
        defender_id=defender.id,
        winner_id=char.id if attacker_won else defender.id,
        attacker_elo_change=elo_a,
        defender_elo_change=elo_d,
        battle_log="\n".join(result.log),
        played_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(match)

    # Nastav cooldown útočníkovi
    char.arena_cooldown_until = now + timedelta(minutes=ARENA_ATTACK_COOLDOWN_MINUTES)

    # Notifikace pro obránce
    notif_type = NotifType.ARENA_WIN if not attacker_won else NotifType.ARENA_LOSS
    defender_notif = Notification(
        character_id=defender.id,
        type=notif_type,
        title=f"Byl jsi napaden v aréně!",
        body=f"{'🏆 Ubránil jsi se' if not attacker_won else '💀 Byl jsi poražen'} — {char.name} tě napadl. ELO: {elo_d:+d}",
    )
    db.add(defender_notif)

    new_achievements = await check_and_award(char, db)

    # ── Profesní hooky ────────────────────────────────────────────────────────

    # Runovník: rezonance za arénový boj (méně než za quest — boj je rychlý)
    rune_evolutions: list[dict] = []
    if attacker_won:
        rune_evolutions = await add_resonance_to_equipped_runes(char, 5, db)

    # Individuální Weekly Board hook — arena výhry
    _wq_arena_new: list[dict] = []
    if attacker_won:
        from routers.weekly_quest import increment_weekly_board
        _wq_arena_new = await increment_weekly_board(char.id, "arena", 1, db)

    # Season Pass XP
    if attacker_won:
        from routers.season_pass import add_season_xp
        await add_season_xp(char.id, "arena_win", db)

    # Durability loss — vždy pro útočníka (win i loss)
    from routers.inventory import _decrease_equipped_durability, DURABILITY_LOSS_ARENA
    await _decrease_equipped_durability(char, DURABILITY_LOSS_ARENA, db)

    await db.commit()
    await db.refresh(char)

    # Invalidace leaderboard cache po každém zápasu
    from core.cache import cache as _cache
    await _cache.delete("arena:leaderboard")
    await _cache.delete("arena:season_leaderboard")

    gold_earned = actual_win_gold if attacker_won else actual_loss_gold
    cap_reached = attacker_won and actual_win_gold < GOLD_REWARD_WIN

    return {
        "result":           "win" if attacker_won else "loss",
        "winner":       char.name if attacker_won else defender.name,
        "attacker_won": attacker_won,
        "elo_change":   elo_a,
        "new_elo":      char.arena_rank,
        "gold_earned":  gold_earned,
        "gold_cap_reached": cap_reached,
        "arena_gold_today": char.arena_gold_today,
        "arena_daily_cap":  ARENA_DAILY_GOLD_CAP,
        "xp_gained":    xp_gained,
        "leveled_up":   leveled_up,
        "rounds":       result.rounds,
        "battle_log":   result.log,
        "events":       events_to_dict_list(result.events),
        "enemy_hp_max": defender.hp_max,
        "character":    await char_dict_with_equipment(char, db),
        "defender": {
            "name":        defender.name,
            "new_elo":     defender.arena_rank,
            "elo_change":  elo_d,
            "appearance":  defender.get_appearance(),
        },
        "new_achievements":  new_achievements,
        "rune_evolutions":   rune_evolutions,
        "weekly_completed":  _wq_arena_new,
    }


@router.get("/history")
async def match_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Historie posledních 20 zápasů hráče."""
    char = await _get_char(user, db)

    result = await db.execute(
        select(ArenaMatch)
        .options(
            selectinload(ArenaMatch.attacker),
            selectinload(ArenaMatch.defender),
            selectinload(ArenaMatch.winner),
        )
        .where(
            or_(
                ArenaMatch.attacker_id == char.id,
                ArenaMatch.defender_id == char.id,
            )
        ).order_by(ArenaMatch.played_at.desc()).limit(20)
    )
    matches = result.scalars().all()

    return {
        "matches": [m.to_dict(pov_char_id=char.id) for m in matches],
        "total_played": len(matches),
    }


@router.get("/leaderboard")
async def arena_leaderboard(db: AsyncSession = Depends(get_db)):
    """Top 20 hráčů podle ELO. Cached 60s."""
    from core.cache import cache
    cached = await cache.get("arena:leaderboard")
    if cached is not None:
        return cached

    result = await db.execute(
        select(Character)
        .order_by(Character.arena_rank.desc())
        .limit(20)
    )
    chars = result.scalars().all()

    CLS_E = {"warrior": "⚔️", "mage": "🔮", "ranger": "🏹"}

    data = [
        {
            "rank":       i + 1,
            "name":       c.name,
            "cls":        c.cls,
            "cls_emoji":  CLS_E.get(c.cls, "⚔"),
            "level":      c.level,
            "arena_rank": c.arena_rank,
            "wins":       c.arena_wins,
            "losses":     c.arena_losses,
            "winrate":    round(c.arena_wins / max(1, c.arena_wins + c.arena_losses) * 100),
            "appearance": c.get_appearance(),
        }
        for i, c in enumerate(chars)
    ]
    await cache.set("arena:leaderboard", data, ttl=60)
    return data


# ── Season endpointy ──────────────────────────────────────────────────────────

@router.get("/season")
async def get_season(db: AsyncSession = Depends(get_db)):
    """Vrátí info o aktuální sezóně."""
    season = await ensure_active_season(db)
    return {"season": season.to_dict()}


@router.get("/season/leaderboard")
async def season_leaderboard(db: AsyncSession = Depends(get_db)):
    """Žebříček aktuální sezóny (= aktuální ELO pořadí). Cached 60s."""
    from core.cache import cache
    cached = await cache.get("arena:season_leaderboard")
    if cached is not None:
        return cached

    result = await db.execute(
        select(Character)
        .where(Character.arena_rank > 0)
        .order_by(Character.arena_rank.desc())
        .limit(25)
    )
    chars = result.scalars().all()
    CLS_E = {"warrior": "⚔️", "mage": "🔮", "ranger": "🏹"}

    data = [
        {
            "rank":       i + 1,
            "name":       c.name,
            "cls_emoji":  CLS_E.get(c.cls, "⚔"),
            "level":      c.level,
            "arena_rank": c.arena_rank,
            "wins":       c.arena_wins,
            "losses":     c.arena_losses,
            "winrate":    round(c.arena_wins / max(1, c.arena_wins + c.arena_losses) * 100),
            "appearance": c.get_appearance(),
        }
        for i, c in enumerate(chars)
    ]
    await cache.set("arena:season_leaderboard", data, ttl=60)
    return data


@router.get("/season/history")
async def season_history(db: AsyncSession = Depends(get_db)):
    """Přehled posledních 5 ukončených sezón."""
    result = await db.execute(
        select(Season)
        .where(Season.is_active == False)
        .order_by(Season.number.desc())
        .limit(5)
    )
    seasons = result.scalars().all()
    return {"seasons": [s.to_dict() for s in seasons]}


@router.get("/season/my-result")
async def my_season_result(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Výsledky aktuálního hráče v minulých sezónách + nevyzvednuté odměny."""
    char = await _get_char(user, db)

    result = await db.execute(
        select(SeasonResult)
        .options(selectinload(SeasonResult.character))
        .where(SeasonResult.character_id == char.id)
        .order_by(SeasonResult.season_id.desc())
        .limit(10)
    )
    results = result.scalars().all()

    unclaimed = [r for r in results if not r.reward_claimed and r.reward_gold > 0]
    total_unclaimed_gold = sum(r.reward_gold for r in unclaimed)

    # Shrnutí nevyzvednutých kosmetik pro UI preview
    unclaimed_cosmetics = [
        {"title": r.reward_title, "frame": r.reward_frame, "rank": r.final_rank}
        for r in unclaimed if r.reward_title or r.reward_frame
    ]

    return {
        "results":              [r.to_dict() for r in results],
        "unclaimed_count":      len(unclaimed),
        "total_unclaimed_gold": total_unclaimed_gold,
        "unclaimed_cosmetics":  unclaimed_cosmetics,
        "current_season_frame": char.season_portrait_frame,
    }


@router.post("/season/claim")
async def claim_season_rewards(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vyzvedne všechny nevyzvednuté odměny za sezóny (gold + kosmetika)."""
    char = await _get_char(user, db)

    result = await db.execute(
        select(SeasonResult).where(
            SeasonResult.character_id == char.id,
            SeasonResult.reward_claimed == False,
            SeasonResult.reward_gold > 0,
        )
    )
    unclaimed = result.scalars().all()

    if not unclaimed:
        raise HTTPException(400, "Žádné nevyzvednuté odměny.")

    total_gold = sum(r.reward_gold for r in unclaimed)

    # Prioritizace frame: champion > challenger > veteran > (žádný)
    _FRAME_PRIORITY = ["season-champion", "season-challenger", "season-veteran"]
    best_frame: str | None = None
    for frame_key in _FRAME_PRIORITY:
        if any(r.reward_frame == frame_key for r in unclaimed):
            best_frame = frame_key
            break

    # Titul: z výsledku s nejlepším rankem
    best_title: str | None = None
    best_rank_result = min(unclaimed, key=lambda r: r.final_rank)
    if best_rank_result.reward_title:
        best_title = best_rank_result.reward_title

    for r in unclaimed:
        r.reward_claimed = True

    char.gold += total_gold
    await log_gold(db, char, total_gold, GoldReason.ARENA_SEASON_REWARD,
                   {"seasons": len(unclaimed)})

    # Aplikuj nejlepší frame (pokud hráč dostal lepší než má)
    frame_applied: str | None = None
    if best_frame:
        current_priority = _FRAME_PRIORITY.index(char.season_portrait_frame) \
            if char.season_portrait_frame in _FRAME_PRIORITY else len(_FRAME_PRIORITY)
        new_priority = _FRAME_PRIORITY.index(best_frame)
        if new_priority < current_priority:
            char.season_portrait_frame = best_frame
            frame_applied = best_frame

    # Aplikuj titul pokud hráč žádný nemá
    title_applied: str | None = None
    if best_title and not char.current_title:
        char.current_title = best_title
        title_applied = best_title

    await db.commit()

    parts = [f"+{total_gold} G"]
    if frame_applied:
        parts.append(f"portrait frame \"{frame_applied}\"")
    if title_applied:
        parts.append(f"titul \"{title_applied}\"")

    return {
        "message":       f"Vyzvednuty odměny za {len(unclaimed)} sezón(u): {', '.join(parts)}",
        "gold_gained":   total_gold,
        "frame_applied": frame_applied,
        "title_applied": title_applied,
        "character":     await char_dict_with_equipment(char, db),
    }


@router.get("/season/recap")
async def season_recap(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Vrátí sezónní recap pro nejnovější ukončenou sezónu, kde hráč ještě neviděl recap.
    Obsahuje: rank, ELO vývoj, W/L, top soupeř, kosmetiky.
    Pokud žádný unshown recap neexistuje, vrátí {"recap": null}.
    """
    char = await _get_char(user, db)

    # Najdi nejnovější SeasonResult kde recap_shown=False (sezóna musí být ukončená)
    sr_res = await db.execute(
        select(SeasonResult)
        .options(selectinload(SeasonResult.season))
        .where(
            SeasonResult.character_id == char.id,
            SeasonResult.recap_shown == False,
        )
        .order_by(SeasonResult.season_id.desc())
        .limit(1)
    )
    sr = sr_res.scalar_one_or_none()

    # Musí existovat a sezóna musí být neaktivní (ukončená)
    if sr is None or sr.season is None or sr.season.is_active:
        return {"recap": None}

    season = sr.season

    # W/L statistika za tuto sezónu (z ArenaMatch v datu sezóny)
    matches_res = await db.execute(
        select(ArenaMatch)
        .options(
            selectinload(ArenaMatch.attacker),
            selectinload(ArenaMatch.defender),
        )
        .where(
            or_(
                ArenaMatch.attacker_id == char.id,
                ArenaMatch.defender_id == char.id,
            ),
            ArenaMatch.played_at >= season.start_at,
            ArenaMatch.played_at <= season.end_at,
        )
        .order_by(ArenaMatch.played_at.asc())
    )
    matches = matches_res.scalars().all()

    wins = sum(1 for m in matches if m.winner_id == char.id)
    losses = len(matches) - wins

    # ELO vývoj — rekonstrukce zpětně od final_elo
    elo_changes: list[int] = []
    for m in matches:
        if m.attacker_id == char.id:
            elo_changes.append(m.attacker_elo_change)
        else:
            elo_changes.append(m.defender_elo_change)

    # Začáteční ELO = final_elo minus součet všech změn
    start_elo = sr.final_elo - sum(elo_changes)
    elo_points: list[int] = [start_elo]
    running = start_elo
    for chg in elo_changes:
        running += chg
        elo_points.append(running)

    # Top soupeř — kdo se mi objevil nejčastěji
    opp_count: dict[str, int] = {}
    for m in matches:
        opp_name = m.defender.name if m.attacker_id == char.id else m.attacker.name
        opp_count[opp_name] = opp_count.get(opp_name, 0) + 1
    top_opponent = max(opp_count, key=opp_count.get) if opp_count else None
    top_opponent_count = opp_count.get(top_opponent, 0) if top_opponent else 0

    return {
        "recap": {
            "season_id":          season.id,
            "season_number":      season.number,
            "season_theme":       season.theme_name,
            "final_rank":         sr.final_rank,
            "final_elo":          sr.final_elo,
            "start_elo":          start_elo,
            "elo_points":         elo_points,
            "wins":               wins,
            "losses":             losses,
            "total_matches":      len(matches),
            "top_opponent":       top_opponent,
            "top_opponent_count": top_opponent_count,
            "reward_gold":        sr.reward_gold,
            "reward_title":       sr.reward_title,
            "reward_frame":       sr.reward_frame,
        }
    }


@router.post("/season/recap/dismiss")
async def dismiss_season_recap(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Označí všechny unshown season recaps jako zobrazené."""
    char = await _get_char(user, db)

    sr_res = await db.execute(
        select(SeasonResult).where(
            SeasonResult.character_id == char.id,
            SeasonResult.recap_shown == False,
        )
    )
    rows = sr_res.scalars().all()
    for row in rows:
        row.recap_shown = True

    await db.commit()
    return {"ok": True}
