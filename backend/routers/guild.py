"""
routers/guild.py — Guild (cech) systém
"""
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from jose import JWTError, jwt

from database import get_db, AsyncSessionLocal
from config import settings
from models.user import User
from models.character import Character
from models.guild import (
    Guild, GuildMessage, GuildDungeon, GuildDungeonContrib, GUILD_BOSSES,
    GuildWeeklyQuest, GuildWeeklyContrib, WEEKLY_QUEST_POOL, _week_start_for,
)
from models.economy import log_gold, GoldReason
from models.notification import Notification, NotifType
from game.achievements import check_and_award
from game.guild_xp import award_guild_xp, get_perks, GUILD_LV10_TITLE
from routers.auth import get_current_user
from routers.character import char_dict_with_equipment


# ── WebSocket Connection Manager ──────────────────────────────────────────────

class GuildConnectionManager:
    """Sleduje aktivní WS spojení per guild_id."""

    def __init__(self):
        self._connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, guild_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.setdefault(guild_id, []).append(ws)

    def disconnect(self, guild_id: int, ws: WebSocket) -> None:
        if guild_id in self._connections:
            try:
                self._connections[guild_id].remove(ws)
            except ValueError:
                pass

    async def broadcast(self, guild_id: int, data: dict) -> None:
        dead: List[WebSocket] = []
        for ws in list(self._connections.get(guild_id, [])):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(guild_id, ws)


guild_manager = GuildConnectionManager()

router = APIRouter(prefix="/guild", tags=["guild"])

GUILD_CREATE_COST      = 500   # gold na vytvoření cechu
GUILD_MAX_MEMBERS      = 20
CHAT_MAX_LEN           = 300
CHAT_HISTORY           = 50
DUNGEON_COOLDOWN_MIN   = 30    # minut mezi útoky na bosse


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_char(user: User, db: AsyncSession) -> Character:
    result = await db.execute(select(Character).where(Character.user_id == user.id, Character.is_dead == False))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena.")
    return char


async def _member_count(guild_id: int, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(Character.id)).select_from(Character).where(
            Character.guild_id == guild_id,
            Character.is_dead == False,
        )
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
    await log_gold(db, char, -GUILD_CREATE_COST, GoldReason.GUILD_CREATE,
                   {"guild_name": guild.name})

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
    member_cap = get_perks(guild.level)["member_cap"]
    if cnt >= member_cap:
        raise HTTPException(400, f"Cech je plný (max {member_cap} členů).")

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
        select(Character).where(
            Character.guild_id == guild.id,
            Character.is_dead == False,
        ).order_by(Character.level.desc())
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
        elapsed = (datetime.now(timezone.utc).replace(tzinfo=None) - my_contrib.last_attack_at).total_seconds() / 60
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

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if contrib and contrib.last_attack_at:
        elapsed = (now - contrib.last_attack_at).total_seconds() / 60
        if elapsed < DUNGEON_COOLDOWN_MIN:
            remaining = DUNGEON_COOLDOWN_MIN - elapsed
            raise HTTPException(400, f"Cooldown! Další útok za {remaining:.1f} minut.")

    # Výpočet damage
    base = (char.strength * 2 + char.level) * 3 + char.level * 5
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
            await log_gold(db, c_char, gold, GoldReason.GUILD_BOSS_REWARD,
                           {"boss": dungeon.boss_name, "contribution_pct": round(ratio * 100)})
            db.add(Notification(
                character_id=c_char.id,
                type=NotifType.SYSTEM,
                title=f"Boss {dungeon.boss_name} porazen!",
                body=f"Tvuj podil: +{gold} G, +{xp} XP ({round(ratio*100)}% damage)",
            ))
            if c_char.id == char.id:
                reward_gold, reward_xp = gold, xp

        # Guild dostane XP a může level up
        guild_leveled_up = award_guild_xp(guild, 100)
        if guild_leveled_up:
            perks = get_perks(guild.level)
            for c in all_contribs:
                cr2 = await db.execute(select(Character).where(Character.id == c.character_id))
                c2 = cr2.scalar_one_or_none()
                if not c2:
                    continue
                title_note = f' Titul: „{GUILD_LV10_TITLE}"' if guild.level == 10 else ""
                db.add(Notification(
                    character_id=c2.id,
                    type=NotifType.SYSTEM,
                    title=f"⚜ Cech postoupil na Level {guild.level}!",
                    body=f"{perks['emoji']} Cech je nyní {perks['name']}. Odemčeno: {perks['unlock']}{title_note}",
                ))

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

    g_res = await db.execute(select(Guild).where(Guild.id == char.guild_id))
    g = g_res.scalar_one_or_none()
    chat_limit = get_perks(g.level)["chat_history"] if g else CHAT_HISTORY

    result = await db.execute(
        select(GuildMessage)
        .options(selectinload(GuildMessage.character))
        .where(GuildMessage.guild_id == char.guild_id)
        .order_by(GuildMessage.created_at.desc())
        .limit(chat_limit)
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

    # Broadcastuj přes WS všem připojeným členům guildy
    await guild_manager.broadcast(char.guild_id, {
        "type": "message",
        "message": msg.to_dict(),
    })

    return {"message": msg.to_dict()}


# ── WebSocket: Guild Chat ──────────────────────────────────────────────────────

@router.websocket("/ws/{guild_id}")
async def guild_websocket(
    guild_id: int,
    ws: WebSocket,
    token: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint pro guild chat.
    Připojení: ws://host/guild/ws/{guild_id}?token=JWT
    Zprávy: {"type": "message", "text": "..."}
    Server broadcastuje: {"type": "message", "message": {...}} | {"type": "history", "messages": [...]}
    """
    # 1. Autentizace přes token v query parametru
    if not token:
        await ws.close(code=4001, reason="Missing token")
        return
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        await ws.close(code=4001, reason="Invalid token")
        return

    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user or not user.is_active:
        await ws.close(code=4001, reason="User not found")
        return

    char_res = await db.execute(
        select(Character).where(Character.user_id == user_id, Character.is_dead == False)
    )
    char = char_res.scalar_one_or_none()
    if not char or char.guild_id != guild_id:
        await ws.close(code=4003, reason="Not in this guild")
        return

    # 2. Přijmout spojení a poslat historii
    await guild_manager.connect(guild_id, ws)

    hist_res = await db.execute(
        select(GuildMessage)
        .options(selectinload(GuildMessage.character))
        .where(GuildMessage.guild_id == guild_id)
        .order_by(GuildMessage.created_at.desc())
        .limit(CHAT_HISTORY)
    )
    messages = hist_res.scalars().all()
    await ws.send_json({
        "type": "history",
        "messages": [m.to_dict() for m in reversed(messages)],
    })

    # 3. Smyčka příjmu zpráv
    try:
        while True:
            data = await ws.receive_json()
            if data.get("type") != "message":
                continue
            text = str(data.get("text", "")).strip()
            if not text or len(text) > CHAT_MAX_LEN:
                continue

            # Ulož zprávu (nová session pro každou zprávu)
            async with AsyncSessionLocal() as msg_db:
                # Refresh character v nové session
                char_r = await msg_db.execute(select(Character).where(Character.id == char.id))
                char_fresh = char_r.scalar_one_or_none()
                if not char_fresh:
                    continue
                new_msg = GuildMessage(
                    guild_id=guild_id,
                    character_id=char.id,
                    text=text,
                )
                new_msg.character = char_fresh
                msg_db.add(new_msg)
                await msg_db.commit()
                await msg_db.refresh(new_msg)
                msg_dict = new_msg.to_dict()

            await guild_manager.broadcast(guild_id, {
                "type": "message",
                "message": msg_dict,
            })

    except WebSocketDisconnect:
        guild_manager.disconnect(guild_id, ws)
    except Exception:
        guild_manager.disconnect(guild_id, ws)


# ── Guild Weekly Quest ─────────────────────────────────────────────────────────

async def _get_or_create_weekly(guild_id: int, db: AsyncSession) -> GuildWeeklyQuest:
    """Vrátí weekly quest pro aktuální týden; pokud neexistuje, vytvoří náhodný."""
    now        = datetime.now(timezone.utc).replace(tzinfo=None)
    week_start = _week_start_for(now)

    res = await db.execute(
        select(GuildWeeklyQuest).where(
            GuildWeeklyQuest.guild_id   == guild_id,
            GuildWeeklyQuest.week_start == week_start,
        )
    )
    wq = res.scalar_one_or_none()
    if wq is None:
        pool_entry = random.choice(WEEKLY_QUEST_POOL)
        wq = GuildWeeklyQuest(
            guild_id=guild_id,
            week_start=week_start,
            goal_type=pool_entry["goal_type"],
            goal_target=pool_entry["goal_target"],
            reward_gold=pool_entry["reward_gold"],
            progress=0,
            is_completed=False,
        )
        db.add(wq)
        await db.flush()
    return wq


async def increment_guild_weekly(
    guild_id: int | None,
    goal_type: str,
    amount: int,
    char_id: int,
    db: AsyncSession,
) -> bool:
    """
    Inkrementuje progress guild weekly questu.
    Voláno z quest.py, dungeon.py po každém relevantním úspěchu.
    Vrací True pokud byl quest v tomto volání dokončen.
    """
    if not guild_id or amount <= 0:
        return False

    wq = await _get_or_create_weekly(guild_id, db)

    if wq.is_completed or wq.goal_type != goal_type:
        return False

    # Přidej příspěvek hráče
    contrib_res = await db.execute(
        select(GuildWeeklyContrib).where(
            GuildWeeklyContrib.quest_id     == wq.id,
            GuildWeeklyContrib.character_id == char_id,
        )
    )
    contrib = contrib_res.scalar_one_or_none()
    if contrib is None:
        contrib = GuildWeeklyContrib(
            quest_id=wq.id,
            character_id=char_id,
            contribution=0,
        )
        db.add(contrib)
    contrib.contribution += amount
    wq.progress          += amount

    just_completed = False

    if wq.progress >= wq.goal_target:
        wq.is_completed = True
        wq.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        just_completed  = True

        # Odměna: flat gold všem přispívajícím členům (s bonusem ze guild perku)
        await db.flush()
        all_contribs_res = await db.execute(
            select(GuildWeeklyContrib).where(GuildWeeklyContrib.quest_id == wq.id)
        )
        all_contribs = all_contribs_res.scalars().all()

        from models.character import Character
        from models.notification import Notification, NotifType
        from models.economy import log_gold, GoldReason

        # Načti guild pro gold bonus perk + guild XP
        g_res = await db.execute(select(Guild).where(Guild.id == guild_id))
        g = g_res.scalar_one_or_none()
        gold_pct = get_perks(g.level)["weekly_gold_pct"] if g else 0
        actual_gold = int(wq.reward_gold * (1 + gold_pct / 100))

        # Guild dostane XP za splnění týdenního questu
        if g:
            guild_leveled_up = award_guild_xp(g, 75)
            if guild_leveled_up:
                perks = get_perks(g.level)
                for c in all_contribs:
                    cr2 = await db.execute(select(Character).where(Character.id == c.character_id))
                    c2 = cr2.scalar_one_or_none()
                    if c2:
                        title_note = f' Titul: „{GUILD_LV10_TITLE}"' if g.level == 10 else ""
                        db.add(Notification(
                            character_id=c2.id,
                            type=NotifType.SYSTEM,
                            title=f"⚜ Cech postoupil na Level {g.level}!",
                            body=f"{perks['emoji']} Cech je nyní {perks['name']}. Odemčeno: {perks['unlock']}{title_note}",
                        ))

        bonus_note = f" (+{gold_pct}% guild bonus)" if gold_pct > 0 else ""
        for c in all_contribs:
            char_res = await db.execute(select(Character).where(Character.id == c.character_id))
            c_char   = char_res.scalar_one_or_none()
            if not c_char:
                continue
            c_char.gold += actual_gold
            await log_gold(db, c_char, actual_gold, GoldReason.GUILD_BOSS_REWARD,
                           {"source": "weekly_quest", "goal_type": goal_type})
            db.add(Notification(
                character_id=c_char.id,
                type=NotifType.SYSTEM,
                title="⚜ Guild Weekly Quest splněn!",
                body=f"Cech splnil týdenní quest! Odměna: +{actual_gold} G{bonus_note}",
            ))

    return just_completed


@router.get("/weekly")
async def get_weekly_quest(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí stav guild weekly questu pro aktuální týden."""
    char = await _get_char(user, db)
    if char.guild_id is None:
        raise HTTPException(400, "Nejsi v žádném cechu.")

    wq = await _get_or_create_weekly(char.guild_id, db)
    await db.commit()
    await db.refresh(wq)

    # Příspěvky členů
    contribs_res = await db.execute(
        select(GuildWeeklyContrib)
        .options(selectinload(GuildWeeklyContrib.character))
        .where(GuildWeeklyContrib.quest_id == wq.id)
        .order_by(GuildWeeklyContrib.contribution.desc())
    )
    contribs = contribs_res.scalars().all()

    my_contrib = next((c for c in contribs if c.character_id == char.id), None)

    return {
        "weekly":       wq.to_dict(),
        "contributions": [c.to_dict() for c in contribs],
        "my_contribution": my_contrib.contribution if my_contrib else 0,
    }
