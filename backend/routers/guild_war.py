"""
routers/guild_war.py — Guild Wars (asynchronní formát)
"""
import json
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from pydantic import BaseModel

from database import get_db
from core.logging import get_logger
from models.user import User
from models.character import Character
from models.guild import Guild
from game.guild_xp import award_guild_xp
from models.guild_war import (
    GuildWar, GuildWarAttack,
    WAR_DURATION_HOURS, MAX_ATTACKS_PER_WAR,
    POINTS_WIN, POINTS_LOSS, REWARD_XP_WIN, REWARD_XP_LOSS,
)
from game.combat_engine import CombatantConfig, simulate_unified_combat, events_to_dict_list
from routers.auth import get_current_user

log = get_logger(__name__)
router = APIRouter(prefix="/guild/war", tags=["guild_war"])

_UTC = timezone.utc

# ── Pomocné funkce ─────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(_UTC).replace(tzinfo=None)


async def _get_char(user: User, db: AsyncSession) -> Character:
    res = await db.execute(select(Character).where(Character.user_id == user.id, Character.is_dead == False))
    char = res.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena.")
    return char


async def _get_active_war(guild_id: int, db: AsyncSession) -> GuildWar | None:
    """Vrátí aktivní válku cechu nebo None."""
    res = await db.execute(
        select(GuildWar).where(
            and_(
                or_(
                    GuildWar.attacker_guild_id == guild_id,
                    GuildWar.defender_guild_id == guild_id,
                ),
                GuildWar.status == "active",
            )
        )
    )
    return res.scalar_one_or_none()


async def _resolve_war(war: GuildWar, db: AsyncSession) -> None:
    """Uzavře expirovanou válku, určí vítěze a odměny guild XP."""
    if war.status != "active":
        return

    war.status = "completed"

    if war.attacker_points > war.defender_points:
        war.winner_guild_id = war.attacker_guild_id
        win_guild_id = war.attacker_guild_id
        lose_guild_id = war.defender_guild_id
    elif war.defender_points > war.attacker_points:
        war.winner_guild_id = war.defender_guild_id
        win_guild_id = war.defender_guild_id
        lose_guild_id = war.attacker_guild_id
    else:
        # Remíza — oba dostanou průměrnou XP odměnu
        war.winner_guild_id = None
        mid_xp = (REWARD_XP_WIN + REWARD_XP_LOSS) // 2
        for gid in (war.attacker_guild_id, war.defender_guild_id):
            gr = await db.execute(select(Guild).where(Guild.id == gid))
            g = gr.scalar_one_or_none()
            if g:
                award_guild_xp(g, mid_xp)
        await db.commit()
        log.info("Guild war resolved: draw", extra={"data": {"war_id": war.id}})
        return

    # XP odměny
    for gid, xp in ((win_guild_id, REWARD_XP_WIN), (lose_guild_id, REWARD_XP_LOSS)):
        gr = await db.execute(select(Guild).where(Guild.id == gid))
        g = gr.scalar_one_or_none()
        if g:
            award_guild_xp(g, xp)

    # Crystal odměny pro členy vítězného cechu (+25 💎 každému)
    from models.crystal import CrystalTransaction
    members_res = await db.execute(
        select(Character).where(Character.guild_id == win_guild_id)
    )
    for member in members_res.scalars().all():
        member.crystals = (member.crystals or 0) + 25
        db.add(CrystalTransaction(
            character_id=member.id,
            amount=25,
            reason=f"guild_war:{war.id}:win",
            balance_after=member.crystals,
        ))

    await db.commit()
    log.info("Guild war resolved", extra={"data": {
        "war_id": war.id, "winner": win_guild_id,
        "atk_pts": war.attacker_points, "def_pts": war.defender_points,
    }})


async def _guild_war_state(war: GuildWar, my_guild_id: int, char_id: int, db: AsyncSession) -> dict:
    """Sestaví kompletní state dict pro frontend."""
    # Načti oba cechy
    atk_res = await db.execute(select(Guild).where(Guild.id == war.attacker_guild_id))
    def_res = await db.execute(select(Guild).where(Guild.id == war.defender_guild_id))
    atk_guild = atk_res.scalar_one_or_none()
    def_guild = def_res.scalar_one_or_none()

    # Načti moje útoky
    my_atks_res = await db.execute(
        select(func.count()).where(
            and_(GuildWarAttack.war_id == war.id, GuildWarAttack.attacker_char_id == char_id)
        )
    )
    my_attacks_used = my_atks_res.scalar_one() or 0

    # Počet útoků per člen (souhrn pro zobrazení)
    atk_total_res = await db.execute(
        select(func.count(), func.sum(GuildWarAttack.points_earned))
        .where(GuildWarAttack.war_id == war.id)
    )
    total_row = atk_total_res.one()
    total_attacks = total_row[0] or 0

    # Načti posledních 10 útoků
    recent_res = await db.execute(
        select(GuildWarAttack)
        .where(GuildWarAttack.war_id == war.id)
        .order_by(GuildWarAttack.attacked_at.desc())
        .limit(10)
    )
    recent_attacks = recent_res.scalars().all()

    # Jména útočníků a obránců
    char_ids = set()
    for a in recent_attacks:
        char_ids.add(a.attacker_char_id)
        char_ids.add(a.defender_char_id)
    names: dict[int, str] = {}
    if char_ids:
        cn_res = await db.execute(select(Character.id, Character.name).where(Character.id.in_(char_ids)))
        for cid, cname in cn_res.all():
            names[cid] = cname

    return {
        "war": war.to_dict(),
        "attacker_guild": {
            "id": atk_guild.id, "name": atk_guild.name, "emblem": atk_guild.emblem
        } if atk_guild else None,
        "defender_guild": {
            "id": def_guild.id, "name": def_guild.name, "emblem": def_guild.emblem
        } if def_guild else None,
        "my_guild_id": my_guild_id,
        "my_attacks_used": my_attacks_used,
        "attacks_remaining": max(0, MAX_ATTACKS_PER_WAR - my_attacks_used),
        "total_attacks": total_attacks,
        "recent_attacks": [
            {
                "attacker": names.get(a.attacker_char_id, "?"),
                "defender": names.get(a.defender_char_id, "?"),
                "attacker_won": a.attacker_won,
                "points": a.points_earned,
                "at": a.attacked_at.isoformat(),
            }
            for a in recent_attacks
        ],
    }


# ── Endpointy ──────────────────────────────────────────────────────────────────

class DeclareWarReq(BaseModel):
    target_guild_id: int


@router.post("/declare")
async def declare_war(
    req: DeclareWarReq,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vyhlásí válku jinému cechu. Pouze leader cechu."""
    char = await _get_char(current_user, db)
    if not char.guild_id:
        raise HTTPException(400, "Nejsi v cechu.")

    # Ověř, že je leader
    guild_res = await db.execute(select(Guild).where(Guild.id == char.guild_id))
    guild = guild_res.scalar_one_or_none()
    if not guild or guild.leader_id != char.id:
        raise HTTPException(403, "Válku může vyhlásit pouze leader cechu.")

    if req.target_guild_id == char.guild_id:
        raise HTTPException(400, "Nelze vyhlásit válku vlastnímu cechu.")

    # Cílový cech
    tgt_res = await db.execute(select(Guild).where(Guild.id == req.target_guild_id))
    target = tgt_res.scalar_one_or_none()
    if not target:
        raise HTTPException(404, "Cílový cech nenalezen.")

    # Zkontroluj, zda není některý cech již ve válce
    my_war = await _get_active_war(char.guild_id, db)
    if my_war:
        raise HTTPException(400, "Tvůj cech je již v aktivní válce.")
    tgt_war = await _get_active_war(req.target_guild_id, db)
    if tgt_war:
        raise HTTPException(400, "Cílový cech je již v aktivní válce.")

    now = _now()
    war = GuildWar(
        attacker_guild_id=char.guild_id,
        defender_guild_id=req.target_guild_id,
        started_at=now,
        ends_at=now + timedelta(hours=WAR_DURATION_HOURS),
        status="active",
        attacker_points=0,
        defender_points=0,
    )
    db.add(war)
    await db.commit()
    await db.refresh(war)

    log.info("Guild war declared", extra={"data": {
        "attacker": guild.name, "defender": target.name, "war_id": war.id,
    }})
    return {
        "message": f"Válka vyhlášena cechu {target.emblem} {target.name}! Trvá {WAR_DURATION_HOURS} hodin.",
        "war": war.to_dict(),
    }


@router.get("/current")
async def get_current_war(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí aktuální aktivní válku pro cech hráče (nebo None)."""
    char = await _get_char(current_user, db)
    if not char.guild_id:
        return {"war": None}

    war = await _get_active_war(char.guild_id, db)
    if not war:
        return {"war": None}

    # Lazy resolve — pokud válka expirovala
    now = _now()
    if war.ends_at <= now:
        await _resolve_war(war, db)
        await db.refresh(war)

    state = await _guild_war_state(war, char.guild_id, char.id, db)
    return state


@router.get("/opponents")
async def get_opponents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Seznam útočitelných soupeřů (členové nepřátelského cechu)."""
    char = await _get_char(current_user, db)
    if not char.guild_id:
        raise HTTPException(400, "Nejsi v cechu.")

    war = await _get_active_war(char.guild_id, db)
    if not war or war.ends_at <= _now():
        raise HTTPException(400, "Žádná aktivní válka.")

    # Zjisti ID nepřátelského cechu
    enemy_guild_id = (
        war.defender_guild_id if war.attacker_guild_id == char.guild_id
        else war.attacker_guild_id
    )

    # Načti soupeře
    opp_res = await db.execute(
        select(Character).where(Character.guild_id == enemy_guild_id)
    )
    opponents = opp_res.scalars().all()

    # Počet mých útoků na každého obránce
    atk_count_res = await db.execute(
        select(GuildWarAttack.defender_char_id, func.count())
        .where(
            and_(
                GuildWarAttack.war_id == war.id,
                GuildWarAttack.attacker_char_id == char.id,
            )
        )
        .group_by(GuildWarAttack.defender_char_id)
    )
    atk_counts: dict[int, int] = {row[0]: row[1] for row in atk_count_res.all()}

    # Počet mých celkových útoků v této válce
    total_atks_res = await db.execute(
        select(func.count()).where(
            and_(GuildWarAttack.war_id == war.id, GuildWarAttack.attacker_char_id == char.id)
        )
    )
    total_used = total_atks_res.scalar_one() or 0

    cls_emoji = {"warrior": "⚔️", "mage": "🔮", "ranger": "🏹"}

    return {
        "attacks_remaining": max(0, MAX_ATTACKS_PER_WAR - total_used),
        "opponents": [
            {
                "id":       o.id,
                "name":     o.name,
                "cls":      o.cls,
                "cls_emoji": cls_emoji.get(o.cls, "⚔️"),
                "level":    o.level,
                "hp_max":   o.hp_max,
                "atk":      o.atk,
                "def":      o.def_,
                "spd":      o.spd,
                "subclass": o.subclass,
                "attacks_on_this": atk_counts.get(o.id, 0),
            }
            for o in opponents
        ],
    }


class WarAttackReq(BaseModel):
    defender_id: int
    strategy: str = "balanced"


@router.post("/attack")
async def war_attack(
    req: WarAttackReq,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Zaútočí na člena nepřátelského cechu v rámci aktivní války."""
    char = await _get_char(current_user, db)
    if not char.guild_id:
        raise HTTPException(400, "Nejsi v cechu.")

    war = await _get_active_war(char.guild_id, db)
    if not war:
        raise HTTPException(400, "Žádná aktivní válka.")
    if war.ends_at <= _now():
        await _resolve_war(war, db)
        raise HTTPException(400, "Válka skončila. Výsledky jsou k dispozici v historii.")

    # Zkontroluj počet útoků
    used_res = await db.execute(
        select(func.count()).where(
            and_(GuildWarAttack.war_id == war.id, GuildWarAttack.attacker_char_id == char.id)
        )
    )
    used = used_res.scalar_one() or 0
    if used >= MAX_ATTACKS_PER_WAR:
        raise HTTPException(400, f"Vyčerpal jsi všechny {MAX_ATTACKS_PER_WAR} útoky pro tuto válku.")

    # Ověř, že obránce je v nepřátelském cechu
    enemy_guild_id = (
        war.defender_guild_id if war.attacker_guild_id == char.guild_id
        else war.attacker_guild_id
    )
    def_res = await db.execute(select(Character).where(Character.id == req.defender_id))
    defender = def_res.scalar_one_or_none()
    if not defender or defender.guild_id != enemy_guild_id:
        raise HTTPException(400, "Tento hráč není v nepřátelském cechu.")
    if defender.id == char.id:
        raise HTTPException(400, "Nemůžeš útočit sám na sebe.")

    # Simuluj souboj
    atk_cfg = CombatantConfig(
        name=char.name, hp=char.hp_max, atk=char.atk, def_=char.def_,
        spd=char.spd, luck=char.luck, level=char.level,
        cls=char.cls, mp=char.mp_max,
        strategy=req.strategy,
        talents=char.get_talents(),
        subclass=char.subclass or "",
    )
    def_cfg = CombatantConfig(
        name=defender.name, hp=defender.hp_max, atk=defender.atk, def_=defender.def_,
        spd=defender.spd, luck=defender.luck, level=defender.level,
        cls=defender.cls, mp=defender.mp_max,
        subclass=defender.subclass or "",
    )
    result = simulate_unified_combat(atk_cfg, def_cfg, max_rounds=20)
    won = result.attacker_won
    pts = POINTS_WIN if won else POINTS_LOSS

    # Ulož útok
    short_events = events_to_dict_list(result.events[:15])  # max 15 events
    attack = GuildWarAttack(
        war_id=war.id,
        attacker_char_id=char.id,
        defender_char_id=defender.id,
        attacker_won=won,
        points_earned=pts,
        attacked_at=_now(),
        events_json=json.dumps(short_events),
    )
    db.add(attack)

    # Připiš body správné straně
    is_attacker_side = war.attacker_guild_id == char.guild_id
    if is_attacker_side:
        war.attacker_points += pts
    else:
        war.defender_points += pts

    await db.commit()

    log.info("War attack", extra={"data": {
        "war": war.id, "atk": char.name, "def": defender.name, "won": won, "pts": pts,
    }})

    return {
        "won": won,
        "points_earned": pts,
        "attacks_remaining": max(0, MAX_ATTACKS_PER_WAR - used - 1),
        "war_score": {
            "attacker_guild_id": war.attacker_guild_id,
            "attacker_points": war.attacker_points,
            "defender_guild_id": war.defender_guild_id,
            "defender_points": war.defender_points,
        },
        "battle_events": short_events,
        "battle_log": result.log,
    }


@router.get("/history")
async def war_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Posledních 10 dokončených válek cechu hráče."""
    char = await _get_char(current_user, db)
    if not char.guild_id:
        return {"wars": []}

    gid = char.guild_id
    hist_res = await db.execute(
        select(GuildWar).where(
            and_(
                or_(GuildWar.attacker_guild_id == gid, GuildWar.defender_guild_id == gid),
                GuildWar.status == "completed",
            )
        )
        .order_by(GuildWar.ends_at.desc())
        .limit(10)
    )
    wars = hist_res.scalars().all()

    # Jména cechů
    guild_ids = set()
    for w in wars:
        guild_ids.add(w.attacker_guild_id)
        guild_ids.add(w.defender_guild_id)
    gname: dict[int, str] = {}
    gemblem: dict[int, str] = {}
    if guild_ids:
        gres = await db.execute(select(Guild.id, Guild.name, Guild.emblem).where(Guild.id.in_(guild_ids)))
        for gid2, gn, ge in gres.all():
            gname[gid2] = gn
            gemblem[gid2] = ge

    return {
        "wars": [
            {
                **w.to_dict(),
                "attacker_name":  gname.get(w.attacker_guild_id, "?"),
                "attacker_emblem": gemblem.get(w.attacker_guild_id, "🛡️"),
                "defender_name":  gname.get(w.defender_guild_id, "?"),
                "defender_emblem": gemblem.get(w.defender_guild_id, "🛡️"),
                "my_result": (
                    "win" if w.winner_guild_id == char.guild_id
                    else "draw" if w.winner_guild_id is None
                    else "loss"
                ),
            }
            for w in wars
        ]
    }
