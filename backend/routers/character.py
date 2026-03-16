"""
routers/character.py — Tvorba a správa postavy
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from pydantic import BaseModel
import re
import json
import httpx
from datetime import datetime, timezone, timedelta

from database import get_db
from core.logging import get_logger
from models.user import User

log = get_logger(__name__)
from models.character import Character, CharacterClass, CLASS_BASE_STATS
from models.item import Item, InventoryItem, UPGRADE_STAT_MULT, MAX_UPGRADE_LEVEL
from models.quest import Quest, QuestStatus
from models.achievement import PlayerAchievement, ACHIEVEMENT_DEFINITIONS
from models.faction import FactionReputation
from game.factions import FACTIONS
from routers.auth import get_current_user

router = APIRouter(prefix="/character", tags=["character"])

EQUIPMENT_SLOTS = {
    "weapon": "eq_weapon",
    "helmet": "eq_helmet",
    "armor":  "eq_armor",
    "gloves": "eq_gloves",
    "boots":  "eq_boots",
    "ring":   "eq_ring",
    "amulet": "eq_amulet",
}

async def char_dict_with_equipment(char: Character, db: AsyncSession) -> dict:
    """Vrátí char.to_dict() s plnými daty nasazených itemů (incl. upgrade bonusy) + set bonus info."""
    from sqlalchemy.orm import selectinload
    data = char.to_dict()
    equipped = {}
    equipped_items = []        # plain Item objects (pro set bonus calcs)
    equipped_inv_items = []    # InventoryItem objects (pro upgrade stats)
    for slot, attr in EQUIPMENT_SLOTS.items():
        item_id = getattr(char, attr)
        if item_id is not None:
            # Zkus načíst InventoryItem (obsahuje upgrade_level)
            inv_res = await db.execute(
                select(InventoryItem)
                .options(selectinload(InventoryItem.item))
                .where(InventoryItem.character_id == char.id,
                       InventoryItem.item_id == item_id)
            )
            inv_item = inv_res.scalar_one_or_none()
            if inv_item and inv_item.item:
                equipped[slot] = inv_item.to_dict()["item"]  # upgraded stats
                equipped_items.append(inv_item.item)
                equipped_inv_items.append(inv_item)
            else:
                # Fallback: plain Item (edge case — item bez inv záznamu)
                res = await db.execute(select(Item).where(Item.id == item_id))
                item = res.scalar_one_or_none()
                equipped[slot] = item.to_dict() if item else None
                if item:
                    equipped_items.append(item)
        else:
            equipped[slot] = None
    data["equipment"] = equipped

    # Přidej info o aktivních set bonusech
    from models.sets import get_active_set_bonuses
    data["set_bonuses"] = get_active_set_bonuses(equipped_items, char.cls)

    # Breakdown: přímé bonusy ze všech nasazených itemů (s upgrade mult)
    def _eff_bonus(inv_or_item, bk: str) -> int:
        if hasattr(inv_or_item, 'item') and inv_or_item.item:
            item = inv_or_item.item
            ul   = getattr(inv_or_item, 'upgrade_level', 0) or 0
            raw  = getattr(item, f"bonus_{bk}", 0) or 0
            if raw == 0 or bk in ("str", "dex", "int", "end", "luck"):
                return raw
            mult = UPGRADE_STAT_MULT[min(ul, MAX_UPGRADE_LEVEL)]
            return max(raw, int(raw * mult))
        return getattr(inv_or_item, f"bonus_{bk}", 0) or 0

    src = equipped_inv_items if equipped_inv_items else equipped_items
    data["stats_breakdown"] = {
        "eq_bonus": {k: sum(_eff_bonus(i, k) for i in src)
                     for k in ("atk","def","spd","hp","mp","str","dex","int","end","luck")}
    }

    # Transmog — kosmetický vzhled slotů
    try:
        from routers.transmog import get_transmog_dict
        data["equipment_transmog"] = await get_transmog_dict(char.id, db)
    except Exception:
        data["equipment_transmog"] = {}

    return data

VALID_STATS = {"strength", "dexterity", "intelligence", "endurance", "luck"}

STAT_CZ = {
    "strength": "Síla", "dexterity": "Obratnost",
    "intelligence": "Inteligence", "endurance": "Výdrž", "luck": "Štěstí",
}

async def _get_char(user: User, db: AsyncSession) -> Character:
    result = await db.execute(select(Character).where(Character.user_id == user.id))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena.")
    if char.is_dead:
        raise HTTPException(403, f"Tato postava zemřela. Zabit: {char.killed_by or 'Neznámý nepřítel'}")
    return char

# ── Schemas ───────────────────────────────────────────────────────────────────
class CreateCharacterRequest(BaseModel):
    name:      str
    cls:       str            # warrior / mage / ranger
    faction:   str | None = None  # rad_popele / pakt_stinu / kongregace_prazdna
    is_hardcore: bool = False     # opt-in permadeath mode

class AllocateStatRequest(BaseModel):
    stat: str  # strength / dexterity / intelligence / endurance / luck

class SetTitleIn(BaseModel):
    title: str | None

class SelectLegacyRequest(BaseModel):
    item_id: int

# ── Endpointy ─────────────────────────────────────────────────────────────────
@router.post("/create", status_code=201)
async def create_character(
    req: CreateCharacterRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validace jména
    if not re.match(r"^[a-zA-ZáčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-zA-ZáčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ0-9_ ]{1,30}$", req.name):
        raise HTTPException(400, "Jméno musí být 2–32 znaků")

    # Validace třídy
    try:
        cls = CharacterClass(req.cls.lower())
    except ValueError:
        raise HTTPException(400, f"Neplatná třída. Možnosti: {[c.value for c in CharacterClass]}")

    # Jeden hráč = jedna živá postava (mrtvá HC postava umožní nový run)
    existing_res = await db.execute(select(Character).where(Character.user_id == user.id))
    existing_char = existing_res.scalar_one_or_none()
    if existing_char and not existing_char.is_dead:
        raise HTTPException(400, "Již máš živou postavu. Jeden účet = jedna živá postava.")

    # Unikátní jméno
    name_taken = await db.execute(select(Character).where(Character.name == req.name))
    if name_taken.scalar_one_or_none():
        raise HTTPException(400, "Toto jméno je již obsazeno, zvol jiné.")

    # Validace frakce (volitelná při tvorbě)
    if req.faction is not None and req.faction not in FACTIONS:
        raise HTTPException(400, f"Neplatná frakce. Možnosti: {list(FACTIONS.keys())}")

    import random as _random
    base = CLASS_BASE_STATS[cls]
    char = Character(
        user_id=user.id,
        name=req.name,
        cls=cls.value,
        level=1, xp=0, gold=150,
        strength=base["strength"],
        dexterity=base["dexterity"],
        intelligence=base["intelligence"],
        endurance=base["endurance"],
        luck=base["luck"],
        faction=req.faction,
        experiment_group=_random.randint(0, 9),
        is_hardcore=req.is_hardcore,
    )
    char.recalculate_stats()
    db.add(char)
    await db.flush()  # získáme char.id

    # Přiřaď pending legacy item (pokud existuje)
    try:
        legacy_res = await db.execute(
            select(InventoryItem).where(
                InventoryItem.is_legacy_pending == True,
                InventoryItem.legacy_owner_user_id == user.id,
            )
        )
        legacy_item = legacy_res.scalar_one_or_none()
        if legacy_item:
            legacy_item.character_id = char.id
            legacy_item.is_legacy_pending = False
            legacy_item.legacy_owner_user_id = None
            await db.flush()
    except Exception:
        pass  # Legacy item přiřazení není kritické

    # Vytvoř quest slot
    quest = Quest(character_id=char.id, status=QuestStatus.IDLE)
    db.add(quest)

    # Vytvoř faction reputation slot pokud hráč zvolil frakci
    if req.faction:
        faction_rep = FactionReputation(
            character_id=char.id,
            faction=req.faction,
            reputation=0,
        )
        db.add(faction_rep)

    await db.commit()
    await db.refresh(char)

    return {"message": "Postava vytvořena!", "character": await char_dict_with_equipment(char, db)}

@router.get("/me")
async def get_my_character(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Character).where(Character.user_id == user.id))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena — nejprve si vytvoř postavu.")
    return await char_dict_with_equipment(char, db)

@router.get("/hub-summary")
async def hub_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Agregovaný přehled stavu pro hlavní stránku (Hub). Jeden request místo 6."""
    char = await _get_char(user, db)
    now  = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    result: dict = {}

    # ── 1. AKTIVNÍ QUEST ─────────────────────────────────────────────────────
    quest_res = await db.execute(select(Quest).where(Quest.character_id == char.id))
    quest = quest_res.scalar_one_or_none()
    if quest and quest.status != QuestStatus.IDLE:
        from models.quest import QUEST_DEFINITIONS
        q_def = QUEST_DEFINITIONS.get(quest.quest_def_id, {}) if quest.quest_def_id else {}
        finish = quest.finish_at
        if finish and finish.tzinfo is None:
            finish = finish.replace(tzinfo=timezone.utc)
        secs = max(0, int((finish - now).total_seconds())) if finish and finish > now else 0
        result["quest"] = {
            "status":            quest.status.value if hasattr(quest.status, "value") else str(quest.status),
            "quest_name":        q_def.get("name", "Quest"),
            "seconds_remaining": secs,
            "finish_at":         finish.isoformat() if finish else None,
        }
    else:
        result["quest"] = {"status": "idle", "quest_name": None, "seconds_remaining": 0, "finish_at": None}

    # ── 2. DENNÍ QUESTY ──────────────────────────────────────────────────────
    from models.quest import DailyQuestRotation
    rot_res = await db.execute(
        select(DailyQuestRotation)
        .where(DailyQuestRotation.character_id == char.id,
               DailyQuestRotation.date == today_str)
    )
    rotation = rot_res.scalar_one_or_none()
    daily_ids = json.loads(rotation.quest_ids) if rotation else []
    result["daily_quests"] = {"available": len(daily_ids), "total": 3}

    # ── 3. ARÉNA ─────────────────────────────────────────────────────────────
    cd = char.arena_cooldown_until
    if cd and cd.tzinfo is None:
        cd = cd.replace(tzinfo=timezone.utc)
    on_cd = bool(cd and cd > now)
    result["arena"] = {
        "rank":           char.arena_rank,
        "wins":           char.arena_wins,
        "losses":         char.arena_losses,
        "on_cooldown":    on_cd,
        "cooldown_until": cd.isoformat() if on_cd else None,
    }

    # ── 4. DUNGEON ────────────────────────────────────────────────────────────
    from models.dungeon_run import DungeonRun
    dng_res = await db.execute(select(DungeonRun).where(DungeonRun.character_id == char.id))
    dng = dng_res.scalar_one_or_none()
    if dng:
        dcd = dng.cooldown_until
        if dcd and dcd.tzinfo is None:
            dcd = dcd.replace(tzinfo=timezone.utc)
        on_dcd = bool(dcd and dcd > now)
        result["dungeon"] = {
            "status":         dng.status,
            "current_stage":  dng.current_stage,
            "total_stages":   dng.total_stages,
            "dungeon_key":    dng.dungeon_key,
            "on_cooldown":    on_dcd,
            "cooldown_until": dcd.isoformat() if on_dcd else None,
            "reward_claimed": dng.reward_claimed,
        }
    else:
        result["dungeon"] = {"status": "idle", "on_cooldown": False}

    # ── 5. SEZÓNNÍ PASS ───────────────────────────────────────────────────────
    from models.season_pass import SeasonPass, SeasonPassProgress, SEASON_TIERS
    sp_res = await db.execute(select(SeasonPass).where(SeasonPass.is_active == True))
    season = sp_res.scalar_one_or_none()
    if season:
        prog_res = await db.execute(
            select(SeasonPassProgress)
            .where(SeasonPassProgress.character_id == char.id,
                   SeasonPassProgress.season_id == season.id)
        )
        prog = prog_res.scalar_one_or_none()
        season_xp    = prog.season_xp if prog else 0
        claimed      = json.loads(prog.claimed_tiers) if prog and prog.claimed_tiers else []
        current_tier = max(claimed) if claimed else 0
        next_tier    = next((t for t in SEASON_TIERS if t["tier"] == current_tier + 1), None)
        result["season_pass"] = {
            "season_name":   season.name,
            "current_tier":  current_tier,
            "max_tier":      len(SEASON_TIERS),
            "season_xp":     season_xp,
            "next_tier_xp":  next_tier["xp_req"] if next_tier else None,
            "next_tier_num": current_tier + 1 if next_tier else None,
        }
    else:
        result["season_pass"] = None

    # ── 6. GUILD WEEKLY QUEST ────────────────────────────────────────────────
    from models.guild import GuildWeeklyQuest, GuildWeeklyContrib
    if char.guild_id:
        week_start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        gwq_res = await db.execute(
            select(GuildWeeklyQuest)
            .where(GuildWeeklyQuest.guild_id == char.guild_id,
                   GuildWeeklyQuest.week_start >= week_start)
        )
        gwq = gwq_res.scalar_one_or_none()
        if gwq:
            ctr_res = await db.execute(
                select(GuildWeeklyContrib)
                .where(GuildWeeklyContrib.quest_id == gwq.id,
                       GuildWeeklyContrib.character_id == char.id)
            )
            ctr = ctr_res.scalar_one_or_none()
            result["guild_weekly"] = {
                "goal_type":      gwq.goal_type,
                "progress":       gwq.progress,
                "goal_target":    gwq.goal_target,
                "is_completed":   gwq.is_completed,
                "my_contribution": ctr.contribution if ctr else 0,
            }
        else:
            result["guild_weekly"] = None
    else:
        result["guild_weekly"] = None

    # ── 7. WORLD EVENT ────────────────────────────────────────────────────────
    from models.world_event import WorldEvent, WorldEventContrib
    we_res = await db.execute(select(WorldEvent).where(WorldEvent.is_active == True))
    we = we_res.scalar_one_or_none()
    if we:
        wec_res = await db.execute(
            select(WorldEventContrib)
            .where(WorldEventContrib.event_id == we.id,
                   WorldEventContrib.character_id == char.id)
        )
        wec = wec_res.scalar_one_or_none()
        ends = we.ends_at
        if ends and ends.tzinfo is None:
            ends = ends.replace(tzinfo=timezone.utc)
        result["world_event"] = {
            "name":             we.name,
            "event_type":       we.event_type,
            "goal":             we.goal,
            "current_progress": we.current_progress,
            "my_contribution":  wec.contribution if wec else 0,
            "ends_at":          ends.isoformat() if ends else None,
            "is_completed":     we.is_completed,
        }
    else:
        result["world_event"] = None

    # ── 8. NEXT ACTION (doporučení) ───────────────────────────────────────────
    actions = []
    q_status = result["quest"]["status"]
    if q_status == "collecting":
        actions.append({"priority": 1, "icon": "🎁", "text": "Máš nevyzvednutou odměnu za quest!", "page": "quests"})
    if dng and dng.status == "completed" and not dng.reward_claimed:
        actions.append({"priority": 1, "icon": "🏆", "text": "Dungeon dokončen — seber odměnu!", "page": "dungeons"})
    if char.stat_points and char.stat_points > 0:
        pts = char.stat_points
        actions.append({"priority": 1, "icon": "⬆", "text": f"Máš {pts} bod{'y' if 1 < pts < 5 else 'ů'} k přidělení!", "page": "equipment"})
    if q_status == "idle":
        actions.append({"priority": 2, "icon": "⚔", "text": "Žádný aktivní quest — přijmi nový úkol.", "page": "quests"})
    if not result["arena"]["on_cooldown"]:
        actions.append({"priority": 3, "icon": "🏟", "text": "Aréna je dostupná — vyzvi soupeře.", "page": "arena"})
    if result["dungeon"]["status"] == "idle" and not result["dungeon"]["on_cooldown"]:
        actions.append({"priority": 4, "icon": "🏰", "text": "Dungeon čeká na dobrodruha.", "page": "dungeons"})
    actions.sort(key=lambda x: x["priority"])
    result["next_action"] = actions[0] if actions else None

    return result


@router.get("/classes")
async def get_classes():
    """Vrátí info o všech třídách pro výběr při tvorbě postavy."""
    return {
        cls.value: {
            **data,
            "class": cls.value,
        }
        for cls, data in CLASS_BASE_STATS.items()
    }

@router.get("/class-mechanics")
async def get_class_mechanics_endpoint():
    """Vrátí asymetrické třídní mechaniky pro zobrazení v UI."""
    try:
        from game.class_mechanics import CLASS_MECHANICS
        return CLASS_MECHANICS
    except ImportError:
        return {
            "warrior": {
                "name": "Rage",
                "description": "Každý přijatý úder zvyšuje ATK. Při HP < 30%: Berserker Mode (+50% ATK, -20% DEF). Imunita na stun.",
                "passives": ["rage_stacks", "berserk_mode", "stun_immune"],
            },
            "ranger": {
                "name": "Chain",
                "description": "25% šance na bonus hit. Každé 3. kolo: dvojitý útok. Vždy útočí první v kole 1.",
                "passives": ["chain_hit", "multi_hit", "first_round_first_strike"],
            },
            "mage": {
                "name": "First Strike",
                "description": "Při vyšší SPD: guaranteed crit v kole 1. Burn DoT 3% HP/kolo. Spirit Revenge při smrti v kole 1.",
                "passives": ["opening_crit", "spell_burn", "spirit_revenge"],
            },
        }

@router.post("/allocate-stat")
async def allocate_stat(
    req: AllocateStatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Utratí 1 stat bod za zvýšení vybraného primárního atributu."""
    char = await _get_char(user, db)

    if req.stat not in VALID_STATS:
        raise HTTPException(400, f"Neplatný atribut. Povolené: {', '.join(sorted(VALID_STATS))}")

    if (char.stat_points or 0) <= 0:
        raise HTTPException(400, "Nemáš žádné volné stat body.")

    setattr(char, req.stat, getattr(char, req.stat) + 1)
    char.stat_points = (char.stat_points or 0) - 1

    # Přepočítej stats včetně equipu
    from routers.inventory import recalculate_with_gear
    await recalculate_with_gear(char, db)
    await db.commit()

    stat_name = STAT_CZ.get(req.stat, req.stat)
    return {
        "message": f"+1 {stat_name}! Zbývá {char.stat_points} bodů.",
        "stat_points_remaining": char.stat_points,
        "character": await char_dict_with_equipment(char, db),
    }


@router.post("/set-title")
async def set_title(
    body: SetTitleIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Nastaví aktivní titul postavy (musí být odemčen přes achievement)."""
    char = await _get_char(user, db)

    if body.title is not None:
        # Načti odemčené achievement IDs
        res = await db.execute(
            select(PlayerAchievement.achievement_id)
            .where(PlayerAchievement.character_id == char.id)
        )
        unlocked_ids = {row[0] for row in res.all()}

        # Dostupné tituly z odemčených achievementů
        available = {
            defn[6] for defn in ACHIEVEMENT_DEFINITIONS
            if defn[0] in unlocked_ids and defn[6] is not None
        }

        # Dostupné tituly z frakce
        faction_rep_res = await db.execute(
            select(FactionReputation).where(FactionReputation.character_id == char.id)
        )
        faction_rep = faction_rep_res.scalar_one_or_none()
        if faction_rep:
            available.update(faction_rep.get_unlocked_titles())

        if body.title not in available:
            raise HTTPException(400, "Titul není odemčen.")

    char.current_title = body.title
    await db.commit()
    return await char_dict_with_equipment(char, db)


@router.get("/search")
async def search_characters(q: str = "", db: AsyncSession = Depends(get_db)):
    """Hledání postav podle jména (substring, min 2 znaky, max 8 výsledků)."""
    if len(q) < 2:
        return []
    result = await db.execute(
        select(Character)
        .where(Character.name.ilike(f"%{q}%"))
        .order_by(Character.level.desc())
        .limit(8)
    )
    chars = result.scalars().all()
    CLS_E = {"warrior": "⚔", "mage": "🔮", "ranger": "🏹"}
    return [
        {
            "id":        c.id,
            "name":      c.name,
            "cls_emoji": CLS_E.get(c.cls, "⚔"),
            "level":     c.level,
        }
        for c in chars
    ]


@router.get("/leaderboard")
async def leaderboard(db: AsyncSession = Depends(get_db)):
    """Top 20 hráčů podle levelu a XP. Cached 60s."""
    from core.cache import cache
    cached = await cache.get("character:leaderboard")
    if cached is not None:
        return cached

    result = await db.execute(
        select(Character)
        .order_by(Character.level.desc(), Character.xp.desc())
        .limit(20)
    )
    chars = result.scalars().all()
    data = [
        {
            "rank": i + 1,
            "name": c.name,
            "cls": c.cls,
            "level": c.level,
            "arena_rank": c.arena_rank,
        }
        for i, c in enumerate(chars)
    ]
    await cache.set("character:leaderboard", data, ttl=60)
    return data


# ── APPEARANCE ENDPOINTS (DiceBear Adventurer) ──────────────────────────────

class DiceBearAppearanceRequest(BaseModel):
    """Update request with DiceBear Adventurer options (deterministic)."""
    seed: str | None = None
    base: list[str] | None = None
    size: int | None = None
    flip: bool | None = None
    rotate: int | None = None
    scale: int | None = None
    translateX: int | None = None
    translateY: int | None = None
    clip: bool | None = None
    randomizeIds: bool | None = None
    radius: int | None = None
    earrings: list[str] | None = None
    eyebrows: list[str] | None = None
    eyes: list[str] | None = None
    features: list[str] | None = None
    glasses: list[str] | None = None
    hair: list[str] | None = None
    hairColor: list[str] | None = None
    mouth: list[str] | None = None
    skinColor: list[str] | None = None


class DiceBearAppearanceResponse(BaseModel):
    """Response with appearance and avatar URL."""
    appearance: dict
    avatar_url: str


@router.get("/appearance/options")
async def get_appearance_options():
    """Get all available DiceBear Adventurer appearance options."""
    from game.appearance import get_appearance_options
    options = get_appearance_options()
    
    # Format for frontend consumption: provide nice descriptions
    return {
        "options": options,
        "api_url_base": "https://api.dicebear.com/9.x/adventurer/svg",
        "api_version": "9.x"
    }


@router.get("/appearance")
async def get_appearance(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current character appearance and generated avatar URL."""
    from game.appearance import build_avatar_url
    
    char = await _get_char(user, db)
    appearance = char.get_appearance()
    avatar_url = build_avatar_url(appearance, char.id)
    
    return {
        "appearance": appearance,
        "avatar_url": avatar_url,
    }


@router.post("/appearance")
async def update_appearance(
    req: DiceBearAppearanceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update character appearance with DiceBear Adventurer options.
    Only provided fields are updated (partial updates allowed).
    All fields are validated against DiceBear specification.
    Returns full updated character object for global state sync.
    """
    from game.appearance import (
        validate_appearance_field,
        sanitize_appearance,
        build_avatar_url,
        DEFAULT_APPEARANCE,
    )
    
    char = await _get_char(user, db)
    current = char.get_appearance()

    # Build update dict from request (only non-None fields)
    updates = {field: value for field, value in req.model_dump(exclude_none=True).items()}

    # Validate each field
    for field, value in updates.items():
        is_valid, error_msg = validate_appearance_field(field, value)
        if not is_valid:
            raise HTTPException(400, error_msg)

    # Merge + sanitize
    current.update(updates)
    current = sanitize_appearance(current)

    # Save to database
    char.set_appearance(current)
    await db.commit()
    await db.refresh(char)

    avatar_url = build_avatar_url(current, char.id)
    log.debug("Appearance updated", extra={"data": {"char_id": char.id, "updates": updates}})

    # Return full updated character object (including appearance) for state sync
    updated_char_dict = await char_dict_with_equipment(char, db)
    return {
        "character": updated_char_dict,
        "appearance": current,
        "avatar_url": avatar_url,
        "message": "✨ Vzhled aktualizován!",
    }


@router.get("/avatar-proxy")
async def get_avatar_proxy(
    seed: str = "default",
    hair: str = "short01",
    eyes: str = "variant01",
    skin: str = "9e5622",
    hairColor: str = "0e0e0e",
    t: str = "",  # timestamp for cache busting
):
    """
    Proxy endpoint to fetch DiceBear avatar and serve it directly.
    
    Uses DiceBear 9.x Adventurer style with proper parameter values:
    - hair: short01-short19, long01-long26
    - eyes: variant01-variant26 (each variant provides a different eye appearance)
    - skin: hex color code (unused by Adventurer but kept for compatibility)
    - hairColor: hex color code for hair color (unused by Adventurer but kept for compatibility)
    - t: timestamp for cache busting
    
    Note: The Adventurer style uses variant-based customization for eyes and hair,
    rather than direct color customization like other styles.
    """
    import urllib.parse
    
    # Build DiceBear URL with proper URL encoding and 9.x API version
    params = urllib.parse.urlencode({
        "seed": seed,
        "hair": hair,
        "eyes": eyes,
        # Note: skinColor and hairColor are not supported by Adventurer style
        # but we keep the parameters for API compatibility
    })
    url = f"https://api.dicebear.com/9.x/adventurer/svg?{params}"
    
    log.debug("Avatar proxy fetch", extra={"data": {"seed": seed, "hair": hair, "eyes": eyes}})

    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(url)
            if response.status_code == 200:
                # Return SVG directly with proper headers - no caching to ensure updates are visible
                return Response(
                    content=response.content,
                    media_type="image/svg+xml",
                    headers={
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "Pragma": "no-cache",
                        "Expires": "0"
                    }
                )
            else:
                log.warning("DiceBear error", extra={"data": {"status": response.status_code}})
    except Exception as e:
        log.error("Avatar proxy failed", extra={"data": {"error": str(e)}}, exc_info=True)


# ── Subclass ───────────────────────────────────────────────────────────────────

class ChooseSubclassReq(BaseModel):
    subclass: str


@router.get("/subclasses")
async def list_subclasses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí definice všech subclassů dostupných pro třídu hráče."""
    char = await _get_char(current_user, db)
    from models.subclass import SUBCLASS_DEFINITIONS, SUBCLASSES_BY_CLASS
    available_keys = SUBCLASSES_BY_CLASS.get(char.cls, [])
    return {
        "current_subclass": char.subclass,
        "cls": char.cls,
        "level": char.level,
        "can_choose": char.subclass is None and char.level >= 10,
        "subclasses": {
            key: {
                "key":         key,
                "name":        sdef["name"],
                "emoji":       sdef["emoji"],
                "description": sdef["description"],
                "flavor":      sdef.get("flavor", ""),
                "stat_mults":  sdef.get("stat_mults", {}),
                "unlock_level": sdef["unlock_level"],
            }
            for key in available_keys
            if (sdef := SUBCLASS_DEFINITIONS[key])
        },
    }


@router.post("/choose-subclass")
async def choose_subclass(
    req: ChooseSubclassReq,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Zvolí specializaci postavy. Vyžaduje level 10. Nelze změnit."""
    char = await _get_char(current_user, db)

    if char.subclass:
        raise HTTPException(400, "Specializaci nelze změnit po jejím výběru.")
    if char.level < 10:
        raise HTTPException(400, "Pro výběr specializace musíš dosáhnout úrovně 10.")

    from models.subclass import SUBCLASS_DEFINITIONS
    sdef = SUBCLASS_DEFINITIONS.get(req.subclass)
    if not sdef:
        raise HTTPException(404, "Neznámá specializace.")
    if sdef["cls"] != char.cls:
        raise HTTPException(400, "Tato specializace není dostupná pro tvou třídu.")

    char.subclass = req.subclass
    char.recalculate_stats()
    await db.commit()
    await db.refresh(char)
    log.info("Subclass chosen", extra={"data": {"char": char.name, "subclass": req.subclass}})
    return await char_dict_with_equipment(char, db)

    raise HTTPException(status_code=500, detail="Failed to fetch avatar")


# ── Talent Tier 2 ──────────────────────────────────────────────────────────────

class ChooseT2Req(BaseModel):
    t2_key: str


@router.get("/t2-talents")
async def get_t2_talents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí dostupné T2 opce pro třídu hráče + aktuální volbu."""
    char = await _get_char(current_user, db)
    from game.talents import get_t2_options
    return {
        "options":       get_t2_options(char.cls),
        "current":       char.talent_t2_key,
        "can_choose":    char.level >= 25 and not char.talent_t2_key,
        "level":         char.level,
        "level_required": 25,
    }


@router.post("/choose-t2")
async def choose_t2_talent(
    req: ChooseT2Req,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Zvolí T2 aktivní schopnost. Vyžaduje level 25. Nelze změnit."""
    char = await _get_char(current_user, db)

    if char.talent_t2_key:
        raise HTTPException(400, "T2 talent nelze změnit po výběru.")
    if char.level < 25:
        raise HTTPException(400, "T2 talent odemkne na levelu 25.")

    from game.talents import get_t2_options
    options = get_t2_options(char.cls)
    if not any(o["key"] == req.t2_key for o in options):
        raise HTTPException(400, "Neplatná volba T2 talentu.")

    char.talent_t2_key = req.t2_key
    await db.commit()
    await db.refresh(char)
    log.info("T2 talent chosen", extra={"data": {"char": char.name, "t2_key": req.t2_key}})
    return await char_dict_with_equipment(char, db)


@router.post("/legacy/select")
async def select_legacy_item(
    req: SelectLegacyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Při permadeath: hráč vybere jeden item jako legacy pro příštího hrdinu."""
    # Najdi mrtvou postavu
    char_result = await db.execute(
        select(Character).where(Character.user_id == user.id, Character.is_dead == True)
    )
    char = char_result.scalar_one_or_none()
    if not char:
        raise HTTPException(400, "Žádná mrtvá postava nenalezena.")

    # Ověř, že hráč ještě nemá pending legacy item
    existing_res = await db.execute(
        select(InventoryItem).where(
            InventoryItem.is_legacy_pending == True,
            InventoryItem.legacy_owner_user_id == user.id,
        )
    )
    if existing_res.scalar_one_or_none():
        raise HTTPException(400, "Již máš legacy item čekající na příštího hrdinu.")

    # Najdi item v inventáři mrtvé postavy
    item_result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.id == req.item_id,
            InventoryItem.character_id == char.id,
        )
    )
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item nenalezen v inventáři mrtvé postavy.")

    # Přidej záznam do legacy_chain_json
    chain = item.legacy_chain_json or []
    chain.append({
        "hero_name":  char.name,
        "hero_cls":   char.cls,
        "hero_level": char.level,
        "died_at":    char.died_at.isoformat() if getattr(char, "died_at", None) else None,
        "dungeon":    getattr(char, "death_dungeon", None),
    })
    item.legacy_chain_json = chain

    # Odpoj item od mrtvé postavy — označíme jako pending
    item.character_id = char.id  # zachováme původní pro FK, ale pending flag ho "skryje"
    item.is_legacy_pending = True
    item.legacy_owner_user_id = user.id

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        log.error("select_legacy_item commit failed", extra={"data": {"error": str(e)}})
        raise HTTPException(500, "Nepodařilo se uložit legacy item.")

    return {"ok": True, "item_id": item.id, "chain_length": len(chain)}


@router.get("/legacy/pending")
async def get_pending_legacy(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí legacy item čekající na příštího hrdinu."""
    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.is_legacy_pending == True,
            InventoryItem.legacy_owner_user_id == user.id,
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        return {"has_legacy": False, "item": None}

    # Načti item data přes relationship (lazy-safe)
    from sqlalchemy.orm import selectinload
    item_res = await db.execute(
        select(InventoryItem)
        .options(selectinload(InventoryItem.item))
        .where(InventoryItem.id == item.id)
    )
    item_full = item_res.scalar_one_or_none()

    return {
        "has_legacy": True,
        "item": {
            "id":           item_full.id,
            "name":         item_full.item.name if item_full.item else None,
            "type":         item_full.item.item_type if item_full.item else None,
            "rarity":       item_full.item.rarity if item_full.item else None,
            "upgrade_level": item_full.upgrade_level or 0,
            "legacy_chain": item_full.legacy_chain_json or [],
        },
    }


@router.post("/complete-onboarding")
async def complete_onboarding(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Označí onboarding jako dokončený — voláno z frontendu po posledním kroku."""
    char = await _get_char(current_user, db)
    if not char.onboarding_completed:
        char.onboarding_completed = True
        await db.commit()
    return {"ok": True}


@router.get("/profile/{name}")
async def get_public_profile(name: str, db: AsyncSession = Depends(get_db)):
    """Veřejný profil hráče. Nevrací gold ani inventář."""
    from models.arena import ArenaMatch

    result = await db.execute(select(Character).where(Character.name == name))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Hráč nenalezen.")

    # Počet achievementů
    ach_res = await db.execute(
        select(func.count(PlayerAchievement.id))
        .where(PlayerAchievement.character_id == char.id)
    )
    achievement_count = ach_res.scalar() or 0

    # Posledních 5 arenových zápasů (selectinload nutný pro async — lazy load v async nefunguje)
    from sqlalchemy.orm import selectinload
    matches_res = await db.execute(
        select(ArenaMatch)
        .options(
            selectinload(ArenaMatch.attacker),
            selectinload(ArenaMatch.defender),
            selectinload(ArenaMatch.winner),
        )
        .where(or_(ArenaMatch.attacker_id == char.id, ArenaMatch.defender_id == char.id))
        .order_by(ArenaMatch.played_at.desc())
        .limit(5)
    )
    matches = matches_res.scalars().all()
    matches_data = [m.to_dict(pov_char_id=char.id) for m in matches]

    # Subclass info
    subclass_info = None
    if char.subclass:
        from models.subclass import SUBCLASS_DEFINITIONS
        sdef = SUBCLASS_DEFINITIONS.get(char.subclass)
        if sdef:
            subclass_info = {
                "key":   char.subclass,
                "name":  sdef["name"],
                "emoji": sdef.get("emoji", ""),
            }

    # T2 talent info
    talent_t2_info = None
    if char.talent_t2_key:
        from game.talents import TALENT_T2_TREE
        for talents_list in TALENT_T2_TREE.values():
            for t in talents_list:
                if t["key"] == char.talent_t2_key:
                    talent_t2_info = {"key": t["key"], "name": t["name"], "emoji": t.get("emoji", "⚡")}
                    break
            if talent_t2_info:
                break

    # Aktivní portrait frame (season > prestige > crystal)
    active_frame = (
        char.season_portrait_frame
        or getattr(char, "prestige_portrait_frame", None)
        or char.crystal_portrait_frame
    )

    # Effective combat stats
    char_dict = char.to_dict()
    combat = char_dict.get("combat", {})

    total_games = char.arena_wins + char.arena_losses
    win_rate = round(char.arena_wins / total_games * 100) if total_games > 0 else 0

    return {
        "name":              char.name,
        "cls":               char.cls,
        "level":             char.level,
        "faction":           char.faction,
        "current_title":     char.current_title,
        "portrait_frame":    active_frame,
        "prestige_level":    char.prestige_level or 0,
        "subclass":          subclass_info,
        "talent_t2":         talent_t2_info,
        "appearance":        char.get_appearance(),
        "arena": {
            "rank":     char.arena_rank,
            "wins":     char.arena_wins,
            "losses":   char.arena_losses,
            "win_rate": win_rate,
        },
        "last_matches":      matches_data,
        "achievement_count": achievement_count,
        "combat": {
            "atk": combat.get("eff_atk", char.atk),
            "def": combat.get("eff_def", char.def_),
            "spd": combat.get("eff_spd", char.spd),
            "hp":  combat.get("hp_max",  char.hp_max),
            "mp":  combat.get("mp_max",  char.mp_max),
        },
    }