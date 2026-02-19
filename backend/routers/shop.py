"""
routers/shop.py — NPC Obchod (rotující zásoby každé 3 hodiny)
"""
import math
import time
import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.character import Character
from models.item import Item, InventoryItem
from routers.auth import get_current_user

router = APIRouter(prefix="/shop", tags=["shop"])

ROTATION_HOURS = 3

NPCS = [
    {
        "id":          "weaponsmith",
        "name":        "Ozdobas Čepelník",
        "emoji":       "⚒️",
        "desc":        "Trpasličí mistr zbraňař. Kuje nejostřejší čepele v celém kraji.",
        "types":       ["weapon"],
        "stock_count": 5,
        "seed_offset": 1,
    },
    {
        "id":          "armorer",
        "name":        "Berta Železná",
        "emoji":       "🛡️",
        "desc":        "Legendární zbrojířka. Každý kus je ochranný artefakt.",
        "types":       ["armor", "helmet", "gloves", "boots"],
        "stock_count": 5,
        "seed_offset": 2,
    },
    {
        "id":          "alchemist",
        "name":        "Zilvanas Alchymista",
        "emoji":       "⚗️",
        "desc":        "Tajemný alchymista z Akademie. Prodává klenoty i vzácné lektvary.",
        "types":       ["ring", "amulet", "potion"],
        "stock_count": 5,
        "seed_offset": 3,
    },
]

PRICE_MULT = {
    "common":    3.5,
    "uncommon":  3.0,
    "rare":      2.5,
    "epic":      2.0,
    "legendary": 1.8,
}


def _current_slot() -> int:
    return math.floor(time.time() / (ROTATION_HOURS * 3600))


def _seconds_to_rotation() -> int:
    slot_secs = ROTATION_HOURS * 3600
    return int(slot_secs - (time.time() % slot_secs))


def _shop_price(item: Item) -> int:
    mult = PRICE_MULT.get(item.rarity, 2.5)
    return max(10, round(item.sell_price * mult))


async def _npc_stock(npc: dict, db: AsyncSession) -> list[Item]:
    result = await db.execute(
        select(Item).where(Item.item_type.in_(npc["types"]))
    )
    all_items = result.scalars().all()
    if not all_items:
        return []
    rng = random.Random(_current_slot() * 1000 + npc["seed_offset"])
    count = min(npc["stock_count"], len(all_items))
    return rng.sample(all_items, count)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/")
async def get_shop(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí aktuální zásoby všech NPC obchodníků."""
    char_res = await db.execute(select(Character).where(Character.user_id == user.id))
    char = char_res.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena.")

    npcs_out = []
    for npc in NPCS:
        items = await _npc_stock(npc, db)
        npcs_out.append({
            "id":    npc["id"],
            "name":  npc["name"],
            "emoji": npc["emoji"],
            "desc":  npc["desc"],
            "items": [
                {**item.to_dict(), "shop_price": _shop_price(item)}
                for item in items
            ],
        })

    return {
        "npcs":               npcs_out,
        "rotation_slot":      _current_slot(),
        "seconds_to_rotation": _seconds_to_rotation(),
    }


class BuyRequest(BaseModel):
    item_id: int


@router.post("/buy")
async def buy_from_shop(
    req: BuyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Koupí item od NPC obchodníka."""
    char_res = await db.execute(select(Character).where(Character.user_id == user.id))
    char = char_res.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena.")

    item_res = await db.execute(select(Item).where(Item.id == req.item_id))
    item = item_res.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item nenalezen.")

    # Ověř že item je v aktuálním slotu alespoň jednoho NPC
    in_stock = False
    for npc in NPCS:
        if item.item_type in npc["types"]:
            stock = await _npc_stock(npc, db)
            if any(s.id == req.item_id for s in stock):
                in_stock = True
                break
    if not in_stock:
        raise HTTPException(400, "Tento item není aktuálně v nabídce.")

    price = _shop_price(item)
    if char.gold < price:
        raise HTTPException(400, f"Nedostatek zlata. Potřebuješ {price} G, máš {char.gold} G.")

    char.gold -= price

    inv_res = await db.execute(
        select(InventoryItem).where(
            InventoryItem.character_id == char.id,
            InventoryItem.item_id == item.id,
        )
    )
    existing = inv_res.scalar_one_or_none()
    if existing:
        existing.quantity += 1
    else:
        db.add(InventoryItem(character_id=char.id, item_id=item.id, quantity=1))

    await db.commit()

    return {
        "message":        f"Zakoupeno '{item.name}' za {price} G.",
        "gold_spent":     price,
        "gold_remaining": char.gold,
        "item":           item.to_dict(),
    }
