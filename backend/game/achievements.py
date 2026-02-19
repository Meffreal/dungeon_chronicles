"""
game/achievements.py — Kontrola a udělování achievementů
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models.character import Character
from models.achievement import PlayerAchievement, ACHIEVEMENT_DEFINITIONS
from models.notification import Notification, NotifType
from models.item import InventoryItem, Item
from models.market import MarketListing
from models.guild import Guild


async def check_and_award(char: Character, db: AsyncSession) -> list[dict]:
    """
    Zkontroluje všechny achievementy pro danou postavu.
    Nově odemčené uloží do DB a vrátí jejich seznam.
    """
    # Načti již odemčené IDs
    res = await db.execute(
        select(PlayerAchievement.achievement_id)
        .where(PlayerAchievement.character_id == char.id)
    )
    unlocked_ids = {row[0] for row in res.all()}

    # Lazy-load hodnot potřebných pro podmínky (načteme jen pokud je třeba)
    _market_buys = None
    _has_legendary = None
    _is_guild_leader = None

    async def market_buys() -> int:
        nonlocal _market_buys
        if _market_buys is None:
            r = await db.execute(
                select(func.count())
                .select_from(MarketListing)
                .where(
                    MarketListing.buyer_id == char.id,
                    MarketListing.is_sold == True,
                )
            )
            _market_buys = r.scalar_one()
        return _market_buys

    async def has_legendary() -> bool:
        nonlocal _has_legendary
        if _has_legendary is None:
            r = await db.execute(
                select(func.count())
                .select_from(InventoryItem)
                .join(Item, InventoryItem.item_id == Item.id)
                .where(
                    InventoryItem.character_id == char.id,
                    Item.rarity == "legendary",
                )
            )
            _has_legendary = r.scalar_one() > 0
        return _has_legendary

    async def is_guild_leader() -> bool:
        nonlocal _is_guild_leader
        if _is_guild_leader is None:
            r = await db.execute(
                select(func.count())
                .select_from(Guild)
                .where(Guild.leader_id == char.id)
            )
            _is_guild_leader = r.scalar_one() > 0
        return _is_guild_leader

    newly_awarded = []

    for defn in ACHIEVEMENT_DEFINITIONS:
        ach_id, name, desc, icon, category, points, ctype, cvalue = defn

        if ach_id in unlocked_ids:
            continue  # již odemčeno

        # Zkontroluj podmínku
        met = False
        if ctype == "level":
            met = char.level >= cvalue
        elif ctype == "quests":
            met = (char.quests_completed or 0) >= cvalue
        elif ctype == "arena_wins":
            met = char.arena_wins >= cvalue
        elif ctype == "arena_fights":
            met = (char.arena_wins + char.arena_losses) >= cvalue
        elif ctype == "arena_rank":
            met = char.arena_rank >= cvalue
        elif ctype == "gold":
            met = char.gold >= cvalue
        elif ctype == "market_buys":
            met = await market_buys() >= cvalue
        elif ctype == "guild":
            met = char.guild_id is not None
        elif ctype == "guild_leader":
            met = await is_guild_leader()
        elif ctype == "legendary_item":
            met = await has_legendary()

        if met:
            pa = PlayerAchievement(character_id=char.id, achievement_id=ach_id)
            db.add(pa)

            # Notifikace
            notif = Notification(
                character_id=char.id,
                type=NotifType.SYSTEM,
                title=f"Achievement odemčen: {name}",
                body=f"{icon} {desc} (+{points} bodů)",
            )
            db.add(notif)

            newly_awarded.append({
                "id": ach_id, "name": name, "desc": desc,
                "icon": icon, "category": category, "points": points,
            })

    if newly_awarded:
        await db.flush()  # ulož bez commitu — volající provede commit

    return newly_awarded
