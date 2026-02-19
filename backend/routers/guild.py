"""
routers/guild.py — Guild (cech) systém
"""
import random
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.character import Character
from models.guild import Guild, GuildMessage, GuildDungeon, GuildDungeonContrib, GUILD_BOSSES
from models.notification import Notification, NotifType
from game.achievements import check_and_award
from routers.auth import get_current_user
from routers.character import char_dict_with_equipment

router = APIRouter(prefix="/guild", tags=["guild"])

GUILD_CREATE_COST      = 500   # gold na vytvoření cechu
GUILD_MAX_MEMBERS      = 20
CHAT_MAX_LEN           = 300
CHAT_HISTORY           = 50
DUNGEON_COOLDOWN_MIN   = 30    # minut mezi útoky na bosse


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_char(user: User, db: AsyncSession) -> Character:
    result = await db.execute(select(Character).where(Character.user_id == user.id))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena.")
    return char


async def _member_count(guild_id: int, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count()).where(Character.guild_id == guild_id)
    )
    return result.scalar_one()


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateGuildRequest(BaseModel):
    name:        str
    description: str = ""
    emblem:      str = "🛡️"


class ChatRequest(BaseModel):
    text: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/list")
async def list_guilds(db: AsyncSession = Depends(get_db)):
    """Vrátí seznam všech cechů seřazený podle levelu."""
    result = await db.execute(select(Guild).order_by(Guild.level.desc(), Guild.xp.desc()))
    guilds = result.scalars().all()

    out = []
    for g in guilds:
        cnt = await _member_count(g.id, db)
        out.append({**g.to_dict(member_count=cnt)})
    return {"guilds": out}


@router.post("/create", status_code=201)
async def create_guild(
    req: CreateGuildRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vytvoří nový cech. Stojí 500 gold. Hráč nesmí být v jiném cechu."""
    char = await _get_char(user, db)

    if char.guild_id is not None:
        raise HTTPException(400, "Už jsi v cechu. Nejdřív ho opusť.")

    name = req.name.strip()
    if not name or len(name) < 3 or len(name) > 48:
        raise HTTPException(400, "Jméno cechu musí mít 3–48 znaků.")

    if char.gold < GUILD_CREATE_COST:
        raise HTTPException(400, f"Nemáš dostatek zlata. Cech stojí {GUILD_CREATE_COST} G.")

    # Kontrola duplicitního jména
    existing = await db.execute(select(Guild).where(Guild.name == name))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Cech s tímto jménem již existuje.")

    guild = Guild(
        name=name,
        description=req.description[:256],
        emblem=req.emblem or "🛡️",
        leader_id=char.id,
    )
    db.add(guild)
    await db.flush()   # získáme guild.id

    char.guild_id = guild.id
    char.gold    -= GUILD_CREATE_COST

    new_achievements = await check_and_award(char, db)
    await db.commit()
    await db.refresh(guild)

    return {"guild": guild.to_dict(member_count=1), "message": "Cech byl úspěšně vytvořen!", "new_achievements": new_achievements}


@router.post("/join/{guild_id}")
async def join_guild(
    guild_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vstoupí do cechu."""
    char = await _get_char(user, db)

    if char.guild_id is not None:
        raise HTTPException(400, "Už jsi v cechu. Nejdřív ho opusť.")

    guild_res = await db.execute(select(Guild).where(Guild.id == guild_id))
    guild = guild_res.scalar_one_or_none()
    if not guild:
        raise HTTPException(404, "Cech nenalezen.")

    cnt = await _member_count(guild_id, db)
    if cnt >= GUILD_MAX_MEMBERS:
        raise HTTPException(400, f"Cech je plný (max {GUILD_MAX_MEMBERS} členů).")

    char.guild_id = guild.id
    new_achievements = await check_and_award(char, db)
    await db.commit()

    return {"guild": guild.to_dict(member_count=cnt + 1), "message": f"Vstoupil jsi do cechu {guild.emblem} {guild.name}!", "new_achievements": new_achievements}


@router.post("/leave")
async def leave_guild(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Opustí cech. Leader musí nejdřív předat vedení nebo cech rozpustit."""
    char = await _get_char(user, db)

    if char.guild_id is None:
        raise HTTPException(400, "Nejsi v žádném cechu.")

    guild_res = await db.execute(select(Guild).where(Guild.id == char.guild_id))
    guild = guild_res.scalar_one_or_none()

    if guild and guild.leader_id == char.id:
        cnt = await _member_count(guild.id, db)
        if cnt > 1:
            raise HTTPException(400, "Jsi leader cechu. Nejdřív předej vedení nebo cech rozpusť.")

    char.guild_id = None
    await db.commit()

    return {"message": "Opustil jsi cech."}


@router.get("/my")
async def my_guild(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí detail cechu hráče včetně členů."""
    char = await _get_char(user, db)

    if char.guild_id is None:
        return {"guild": None}

    guild_res = await db.execute(select(Guild).where(Guild.id == char.guild_id))
    guild = guild_res.scalar_one_or_none()
    if not guild:
        char.guild_id = None
        await db.commit()
        return {"guild": None}

    members_res = await db.execute(
        select(Character).where(Character.guild_id == guild.id).order_by(Character.level.desc())
    )
    members = members_res.scalars().all()

    CLS_E = {"warrior": "⚔️", "mage": "🔮", "ranger": "🏹"}
    CLS_N = {"warrior": "Válečník", "mage": "Mág", "ranger": "Lovec"}

    return {
        "guild": guild.to_dict(member_count=len(members)),
        "is_leader": guild.leader_id == char.id,
        "members": [
            {
                "id":       m.id,
                "name":     m.name,
                "cls":      m.cls,
                "cls_name": CLS_N.get(m.cls, m.cls),
                "cls_emoji": CLS_E.get(m.cls, "⚔"),
                "level":    m.level,
                "is_leader": guild.leader_id == m.id,
            }
            for m in members
        ],
    }


@router.post("/promote/{char_id}")
async def promote_member(
    char_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Předá vedení cechu jinému členovi (jen leader)."""
    char = await _get_char(user, db)

    if char.guild_id is None:
        raise HTTPException(400, "Nejsi v žádném cechu.")

    guild_res = await db.execute(select(Guild).where(Guild.id == char.guild_id))
    guild = guild_res.scalar_one_or_none()
    if not guild or guild.leader_id != char.id:
        raise HTTPException(403, "Nejsi leader tohoto cechu.")

    target_res = await db.execute(
        select(Character).where(Character.id == char_id, Character.guild_id == guild.id)
    )
    target = target_res.scalar_one_or_none()
    if not target:
        raise HTTPException(404, "Člen nenalezen v cechu.")

    guild.leader_id = target.id
    await db.commit()

    return {"message": f"{target.name} je nyní leader cechu."}


@router.delete("/kick/{char_id}")
async def kick_member(
    char_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vyhodí člena z cechu (jen leader)."""
    char = await _get_char(user, db)

    if char.guild_id is None:
        raise HTTPException(400, "Nejsi v žádném cechu.")

    guild_res = await db.execute(select(Guild).where(Guild.id == char.guild_id))
    guild = guild_res.scalar_one_or_none()
    if not guild or guild.leader_id != char.id:
        raise HTTPException(403, "Nejsi leader tohoto cechu.")

    if char_id == char.id:
        raise HTTPException(400, "Nemůžeš vyhodit sám sebe.")

    target_res = await db.execute(
        select(Character).where(Character.id == char_id, Character.guild_id == guild.id)
    )
    target = target_res.scalar_one_or_none()
    if not target:
        raise HTTPException(404, "Člen nenalezen v cechu.")

    target.guild_id = None
    await db.commit()

    return {"message": f"{target.name} byl vyhozen z cechu."}


@router.delete("/disband")
async def disband_guild(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rozpustí cech (jen leader)."""
    char = await _get_char(user, db)

    if char.guild_id is None:
        raise HTTPException(400, "Nejsi v žádném cechu.")

    guild_res = await db.execute(select(Guild).where(Guild.id == char.guild_id))
    guild = guild_res.scalar_one_or_none()
    if not guild or guild.leader_id != char.id:
        raise HTTPException(403, "Nejsi leader tohoto cechu.")

    # Odeber všem členům guild_id
    members_res = await db.execute(
        select(Character).where(Character.guild_id == guild.id)
    )
    for m in members_res.scalars().all():
        m.guild_id = None

    # Smaž zprávy chatu
    msgs_res = await db.execute(
        select(GuildMessage).where(GuildMessage.guild_id == guild.id)
    )
    for msg in msgs_res.scalars().all():
        await db.delete(msg)

    await db.delete(guild)
    await db.commit()

    return {"message": "Cech byl rozpuštěn."}


# ── Guild Dungeon ──────────────────────────────────────────────────────────────

async def _get_active_dungeon(guild: Guild, db: AsyncSession) -> GuildDungeon:
    """Vrátí aktivního bosse nebo vytvoří nového."""
    result = await db.execute(
        select(GuildDungeon)
        .where(GuildDungeon.guild_id == guild.id, GuildDungeon.is_defeated == False)
        .order_by(GuildDungeon.id.desc())
    )
    dungeon = result.scalar_one_or_none()

    if dungeon is None:
        # Zvol bosse podle guild levelu (cyklicky)
        idx = (guild.level - 1) % len(GUILD_BOSSES)
        boss = GUILD_BOSSES[idx]
        hp = boss["hp_base"] * max(1, guild.level)
        dungeon = GuildDungeon(
            guild_id=guild.id,
            boss_index=idx,
            boss_name=boss["name"],
            boss_emoji=boss["emoji"],
            boss_hp_max=hp,
            boss_hp_current=hp,
        )
        db.add(dungeon)
        await db.flush()

    return dungeon


@router.get("/dungeon")
async def get_dungeon(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí stav guild dungeonu — aktuálního bosse a příspěvky členů."""
    char = await _get_char(user, db)
    if char.guild_id is None:
        raise HTTPException(400, "Nejsi v žádném cechu.")

    guild_res = await db.execute(select(Guild).where(Guild.id == char.guild_id))
    guild = guild_res.scalar_one_or_none()
    if not guild:
        raise HTTPException(404, "Cech nenalezen.")

    dungeon = await _get_active_dungeon(guild, db)
    await db.commit()

    contribs_res = await db.execute(
        select(GuildDungeonContrib)
        .options(selectinload(GuildDungeonContrib.character))
        .where(GuildDungeonContrib.dungeon_id == dungeon.id)
        .order_by(GuildDungeonContrib.damage_dealt.desc())
    )
    contribs = contribs_res.scalars().all()

    my_contrib = next((c for c in contribs if c.character_id == char.id), None)

    cooldown_remaining = 0.0
    if my_contrib and my_contrib.last_attack_at:
        elapsed = (datetime.utcnow() - my_contrib.last_attack_at).total_seconds() / 60
        cooldown_remaining = max(0.0, DUNGEON_COOLDOWN_MIN - elapsed)

    return {
        "dungeon":        dungeon.to_dict(),
        "contributions":  [c.to_dict() for c in contribs],
        "my_damage":      my_contrib.damage_dealt if my_contrib else 0,
        "cooldown_minutes": round(cooldown_remaining, 1),
        "can_attack":     cooldown_remaining == 0 and not dungeon.is_defeated,
    }


@router.post("/dungeon/attack")
async def dungeon_attack(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Útočí na guild bosse. Cooldown 30 minut."""
    char = await _get_char(user, db)
    if char.guild_id is None:
        raise HTTPException(400, "Nejsi v žádném cechu.")

    guild_res = await db.execute(select(Guild).where(Guild.id == char.guild_id))
    guild = guild_res.scalar_one_or_none()
    if not guild:
        raise HTTPException(404, "Cech nenalezen.")

    dungeon = await _get_active_dungeon(guild, db)

    if dungeon.is_defeated:
        raise HTTPException(400, "Tento boss je již poražen.")

    # Cooldown check
    contrib_res = await db.execute(
        select(GuildDungeonContrib).where(
            GuildDungeonContrib.dungeon_id == dungeon.id,
            GuildDungeonContrib.character_id == char.id,
        )
    )
    contrib = contrib_res.scalar_one_or_none()

    now = datetime.utcnow()
    if contrib and contrib.last_attack_at:
        elapsed = (now - contrib.last_attack_at).total_seconds() / 60
        if elapsed < DUNGEON_COOLDOWN_MIN:
            remaining = DUNGEON_COOLDOWN_MIN - elapsed
            raise HTTPException(400, f"Cooldown! Další útok za {remaining:.1f} minut.")

    # Výpočet damage
    base = char.atk * 3 + char.level * 5
    damage = random.randint(int(base * 0.8), int(base * 1.4))

    if contrib is None:
        contrib = GuildDungeonContrib(
            dungeon_id=dungeon.id,
            character_id=char.id,
            damage_dealt=0,
        )
        db.add(contrib)
    contrib.damage_dealt  += damage
    contrib.last_attack_at = now
    dungeon.boss_hp_current -= damage

    reward_gold = 0
    reward_xp   = 0
    boss_defeated = dungeon.boss_hp_current <= 0

    if boss_defeated:
        dungeon.is_defeated  = True
        dungeon.defeated_at  = now

        all_res = await db.execute(
            select(GuildDungeonContrib).where(GuildDungeonContrib.dungeon_id == dungeon.id)
        )
        all_contribs = all_res.scalars().all()
        total_dmg = sum(c.damage_dealt for c in all_contribs)

        boss = GUILD_BOSSES[dungeon.boss_index % len(GUILD_BOSSES)]

        for c in all_contribs:
            ratio = c.damage_dealt / max(1, total_dmg)
            cr = await db.execute(select(Character).where(Character.id == c.character_id))
            c_char = cr.scalar_one_or_none()
            if not c_char:
                continue
            gold = int(boss["gold_reward"] * ratio * guild.level)
            xp   = int(boss["xp_reward"]   * ratio * guild.level)
            c_char.gold += gold
            c_char.xp   += xp
            db.add(Notification(
                character_id=c_char.id,
                type=NotifType.SYSTEM,
                title=f"Boss {dungeon.boss_name} porazen!",
                body=f"Tvuj podil: +{gold} G, +{xp} XP ({round(ratio*100)}% damage)",
            ))
            if c_char.id == char.id:
                reward_gold, reward_xp = gold, xp

        # Guild dostane XP a může level up
        guild.xp += 100
        if guild.xp >= guild.level * 500:
            guild.xp    = 0
            guild.level += 1

    await db.commit()
    await db.refresh(char)

    return {
        "damage":            damage,
        "boss_hp_remaining": max(0, dungeon.boss_hp_current),
        "boss_hp_max":       dungeon.boss_hp_max,
        "boss_defeated":     boss_defeated,
        "reward_gold":       reward_gold,
        "reward_xp":         reward_xp,
        "character":         await char_dict_with_equipment(char, db),
    }


# ── Guild Chat ─────────────────────────────────────────────────────────────────

@router.get("/chat")
async def get_chat(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí posledních 50 zpráv v guild chatu."""
    char = await _get_char(user, db)

    if char.guild_id is None:
        raise HTTPException(400, "Nejsi v žádném cechu.")

    result = await db.execute(
        select(GuildMessage)
        .options(selectinload(GuildMessage.character))
        .where(GuildMessage.guild_id == char.guild_id)
        .order_by(GuildMessage.created_at.desc())
        .limit(CHAT_HISTORY)
    )
    messages = result.scalars().all()

    return {"messages": [m.to_dict() for m in reversed(messages)]}


@router.post("/chat")
async def send_chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pošle zprávu do guild chatu."""
    char = await _get_char(user, db)

    if char.guild_id is None:
        raise HTTPException(400, "Nejsi v žádném cechu.")

    text = req.text.strip()
    if not text:
        raise HTTPException(400, "Zpráva nesmí být prázdná.")
    if len(text) > CHAT_MAX_LEN:
        raise HTTPException(400, f"Zpráva je příliš dlouhá (max {CHAT_MAX_LEN} znaků).")

    msg = GuildMessage(
        guild_id=char.guild_id,
        character_id=char.id,
        text=text,
    )
    msg.character = char
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    return {"message": msg.to_dict()}
