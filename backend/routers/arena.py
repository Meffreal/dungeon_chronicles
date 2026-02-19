"""
routers/arena.py — Aréna PvP systém
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta

from database import get_db
from models.user import User
from models.character import Character
from models.arena import ArenaMatch, Season, SeasonResult
from models.notification import Notification, NotifType
from game.arena_combat import pvp_fight, calc_elo_change, Fighter
from game.achievements import check_and_award
from game.season import process_expired_season, ensure_active_season
from routers.auth import get_current_user
from routers.character import char_dict_with_equipment

router = APIRouter(prefix="/arena", tags=["arena"])

ARENA_COOLDOWN_MINUTES = 5   # min. pauza mezi útoky na stejného hráče
ARENA_ATTACK_COOLDOWN_MINUTES = 5  # globální cooldown po každém útoku
GOLD_REWARD_WIN  = 50
GOLD_REWARD_LOSS = 10


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

    now = datetime.utcnow()
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
            }
            for o in opponents
        ],
        "my_rank":        char.arena_rank,
        "my_wins":        char.arena_wins,
        "my_losses":      char.arena_losses,
        "cooldown_until":  cd_until.isoformat() if cd_active else None,
        "cooldown_seconds": round(cd_seconds),
    }


@router.post("/attack/{defender_id}")
async def attack(
    defender_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Zaútočí na hráče. Simuluje PvP souboj a aktualizuje ELO."""
    # Auto-check expirace sezóny
    await process_expired_season(db)

    char = await _get_char(user, db)

    if char.id == defender_id:
        raise HTTPException(400, "Nemůžeš bojovat sám se sebou.")

    # Cooldown check
    now = datetime.utcnow()
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
    atk_fighter = Fighter(
        name=char.name, hp=char.hp_max, atk=char.atk,
        defense=char.def_, spd=char.spd, luck=char.luck, level=char.level,
    )
    def_fighter = Fighter(
        name=defender.name, hp=defender.hp_max, atk=defender.atk,
        defense=defender.def_, spd=defender.spd, luck=defender.luck, level=defender.level,
    )

    result = pvp_fight(atk_fighter, def_fighter)
    attacker_won = result["attacker_won"]

    # ELO změna
    elo_a, elo_d = calc_elo_change(char.arena_rank, defender.arena_rank, attacker_won)

    # Aktualizuj stats
    char.arena_rank   = max(100, char.arena_rank + elo_a)
    defender.arena_rank = max(100, defender.arena_rank + elo_d)

    if attacker_won:
        char.arena_wins     += 1
        defender.arena_losses += 1
        char.gold           += GOLD_REWARD_WIN
        defender.gold       += GOLD_REWARD_LOSS
    else:
        char.arena_losses   += 1
        defender.arena_wins += 1
        char.gold           += GOLD_REWARD_LOSS
        defender.gold       += GOLD_REWARD_WIN

    # Ulož zápas
    match = ArenaMatch(
        attacker_id=char.id,
        defender_id=defender.id,
        winner_id=char.id if attacker_won else defender.id,
        attacker_elo_change=elo_a,
        defender_elo_change=elo_d,
        battle_log="\n".join(result["battle_log"]),
        played_at=datetime.utcnow(),
    )
    db.add(match)

    # Nastav cooldown útočníkovi
    char.arena_cooldown_until = now + timedelta(minutes=ARENA_ATTACK_COOLDOWN_MINUTES)

    # Notifikace pro obránce
    notif_type = NotifType.ARENA_WIN if not attacker_won else NotifType.ARENA_LOSS
    defender_notif = Notification(
        character_id=defender.id,
        type=NotifType.ARENA_CHALLENGE,
        title=f"Byl jsi napaden v aréně!",
        body=f"{'🏆 Ubránil jsi se' if not attacker_won else '💀 Byl jsi poražen'} — {char.name} tě napadl. ELO: {elo_d:+d}",
    )
    db.add(defender_notif)

    new_achievements = await check_and_award(char, db)
    await db.commit()
    await db.refresh(char)

    return {
        "result":           "win" if attacker_won else "loss",
        "winner":       result["winner_name"],
        "attacker_won": attacker_won,
        "elo_change":   elo_a,
        "new_elo":      char.arena_rank,
        "gold_earned":  GOLD_REWARD_WIN if attacker_won else GOLD_REWARD_LOSS,
        "rounds":       result["rounds"],
        "battle_log":   result["battle_log"],
        "character":    await char_dict_with_equipment(char, db),
        "defender": {
            "name":        defender.name,
            "new_elo":     defender.arena_rank,
            "elo_change":  elo_d,
        },
        "new_achievements": new_achievements,
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
    """Top 20 hráčů podle ELO."""
    result = await db.execute(
        select(Character)
        .order_by(Character.arena_rank.desc())
        .limit(20)
    )
    chars = result.scalars().all()

    CLS_E = {"warrior": "⚔️", "mage": "🔮", "ranger": "🏹"}

    return [
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
        }
        for i, c in enumerate(chars)
    ]


# ── Season endpointy ──────────────────────────────────────────────────────────

@router.get("/season")
async def get_season(db: AsyncSession = Depends(get_db)):
    """Vrátí info o aktuální sezóně."""
    season = await ensure_active_season(db)
    return {"season": season.to_dict()}


@router.get("/season/leaderboard")
async def season_leaderboard(db: AsyncSession = Depends(get_db)):
    """Žebříček aktuální sezóny (= aktuální ELO pořadí)."""
    result = await db.execute(
        select(Character)
        .where(Character.arena_rank > 0)
        .order_by(Character.arena_rank.desc())
        .limit(25)
    )
    chars = result.scalars().all()
    CLS_E = {"warrior": "⚔️", "mage": "🔮", "ranger": "🏹"}

    return [
        {
            "rank":       i + 1,
            "name":       c.name,
            "cls_emoji":  CLS_E.get(c.cls, "⚔"),
            "level":      c.level,
            "arena_rank": c.arena_rank,
            "wins":       c.arena_wins,
            "losses":     c.arena_losses,
            "winrate":    round(c.arena_wins / max(1, c.arena_wins + c.arena_losses) * 100),
        }
        for i, c in enumerate(chars)
    ]


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

    return {
        "results":              [r.to_dict() for r in results],
        "unclaimed_count":      len(unclaimed),
        "total_unclaimed_gold": total_unclaimed_gold,
    }


@router.post("/season/claim")
async def claim_season_rewards(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vyzvedne všechny nevyzvednuté odměny za sezóny."""
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
    for r in unclaimed:
        r.reward_claimed = True

    char.gold += total_gold
    await db.commit()

    return {
        "message":    f"Vyzvednuty odměny za {len(unclaimed)} sezón(u): +{total_gold} G",
        "gold_gained": total_gold,
        "character":   await char_dict_with_equipment(char, db),
    }
