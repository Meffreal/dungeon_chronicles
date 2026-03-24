"""
routers/market.py — Hráčský trh (tržiště)
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.character import Character
from models.item import Item, InventoryItem
from models.market import MarketListing, MARKET_FEE, LISTING_FEE_PCT, LISTING_FEE_MIN, LISTING_HOURS
from models.economy import log_gold, GoldReason
from game.achievements import check_and_award
from routers.auth import get_current_user

router = APIRouter(prefix="/market", tags=["market"])

# ── Schemas ───────────────────────────────────────────────────────────────────
class ListItemRequest(BaseModel):
    inv_item_id: int   # ID v tabulce inventory
    quantity: int = 1
    price: int         # cena za 1 kus

class BuyRequest(BaseModel):
    listing_id: int
    quantity: int = 1  # zatím vždy vše najednou — quantity pro budoucnost

# ── Helper ────────────────────────────────────────────────────────────────────
async def _get_char(user: User, db: AsyncSession) -> Character:
    result = await db.execute(select(Character).where(Character.user_id == user.id, Character.is_dead == False))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena.")
    return char

def _fix_dt(dt: datetime) -> datetime:
    """Vrátí naive UTC datetime (SQLite kompatibilita)."""
    if dt is None:
        return None
    return dt.replace(tzinfo=None) if dt.tzinfo else dt

def _is_expired(listing: MarketListing) -> bool:
    return datetime.now(timezone.utc).replace(tzinfo=None) > _fix_dt(listing.expires_at)

# ── Endpointy ─────────────────────────────────────────────────────────────────

@router.get("/")
async def browse_market(
    item_type: str | None = Query(None, description="weapon/armor/helmet/..."),
    rarity:    str | None = Query(None, description="common/uncommon/rare/epic/legendary"),
    search:    str | None = Query(None, description="hledej v názvu itemu"),
    sort:      str        = Query("price_asc", description="price_asc/price_desc/newest"),
    page:      int        = Query(1, ge=1),
    page_size: int        = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Zobrazí aktivní nabídky na trhu."""
    query = (
        select(MarketListing)
        .options(selectinload(MarketListing.item), selectinload(MarketListing.seller))
        .where(MarketListing.is_sold == False)
        .join(MarketListing.item)
    )

    # Filtry
    if item_type:
        query = query.where(Item.item_type == item_type)
    if rarity:
        query = query.where(Item.rarity == rarity)
    if search:
        query = query.where(Item.name.ilike(f"%{search}%"))

    # Řazení
    if sort == "price_desc":
        query = query.order_by(MarketListing.price.desc())
    elif sort == "newest":
        query = query.order_by(MarketListing.listed_at.desc())
    else:  # price_asc (default)
        query = query.order_by(MarketListing.price.asc())

    result = await db.execute(query)
    all_listings = result.scalars().all()

    # Filtruj expirované (SQLite nemá dobrou podporu pro datetime porovnání v query)
    active = [l for l in all_listings if not _is_expired(l)]

    # Stránkování
    total = len(active)
    start = (page - 1) * page_size
    page_listings = active[start:start + page_size]

    return {
        "listings": [l.to_dict() for l in page_listings],
        "total": total,
        "page": page,
        "pages": max(1, (total + page_size - 1) // page_size),
    }


@router.get("/my-listings")
async def my_listings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Nabídky aktuálního hráče."""
    char = await _get_char(user, db)

    result = await db.execute(
        select(MarketListing)
        .options(selectinload(MarketListing.item), selectinload(MarketListing.seller))
        .where(
            MarketListing.seller_id == char.id,
            MarketListing.is_sold == False,
        ).order_by(MarketListing.listed_at.desc())
    )
    listings = result.scalars().all()
    return {"listings": [l.to_dict() for l in listings]}


@router.post("/list")
async def list_item(
    req: ListItemRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vystaví item z inventáře na trhu."""
    char = await _get_char(user, db)

    if req.price < 1:
        raise HTTPException(400, "Cena musí být alespoň 1 G.")
    if req.quantity < 1:
        raise HTTPException(400, "Množství musí být alespoň 1.")

    # Najdi item v inventáři
    inv_res = await db.execute(
        select(InventoryItem)
        .options(selectinload(InventoryItem.item))
        .where(
            InventoryItem.id == req.inv_item_id,
            InventoryItem.character_id == char.id,
        )
    )
    inv_item = inv_res.scalar_one_or_none()
    if not inv_item:
        raise HTTPException(404, "Item nenalezen v inventáři.")
    if req.quantity > inv_item.quantity:
        raise HTTPException(400, f"Nemáš dostatek. Máš {inv_item.quantity} ks.")

    # Zkontroluj že není nasazen
    equipped_ids = {
        char.eq_weapon, char.eq_helmet, char.eq_armor,
        char.eq_gloves, char.eq_boots,  char.eq_ring, char.eq_amulet,
    }
    if inv_item.item_id in equipped_ids:
        raise HTTPException(400, "Nelze prodat nasazený item. Nejdřív ho sundej.")

    # Limit: max 5 aktivních nabídek na hráče
    active_count_res = await db.execute(
        select(MarketListing).where(
            MarketListing.seller_id == char.id,
            MarketListing.is_sold == False,
        )
    )
    active_count = len([l for l in active_count_res.scalars().all() if not _is_expired(l)])
    if active_count >= 5:
        raise HTTPException(400, "Maximálně 5 aktivních nabídek najednou.")

    # Listing fee — odečte se ihned při listování (i pokud se neprodá)
    listing_fee = max(LISTING_FEE_MIN, int(req.price * LISTING_FEE_PCT))
    if char.gold < listing_fee:
        raise HTTPException(
            400,
            f"Nedostatek goldu na poplatek za listování ({listing_fee} G). Máš {char.gold} G.",
        )
    char.gold -= listing_fee
    await log_gold(db, char, -listing_fee, GoldReason.MARKET_BUY,
                   {"listing_fee": True, "item_id": inv_item.item_id, "price": req.price})

    # Odeber z inventáře
    if inv_item.quantity <= req.quantity:
        await db.delete(inv_item)
    else:
        inv_item.quantity -= req.quantity

    # Vytvoř listing (naive UTC pro SQLite)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    listing = MarketListing(
        seller_id=char.id,
        item_id=inv_item.item_id,
        quantity=req.quantity,
        price=req.price,
        listed_at=now,
        expires_at=now + timedelta(hours=LISTING_HOURS),
        is_sold=False,
        upgrade_level=inv_item.upgrade_level or 0,
    )
    db.add(listing)
    await db.commit()
    await db.refresh(listing)

    return {
        "message": (
            f"'{inv_item.item.name}' vystaveno za {req.price} G/ks na {LISTING_HOURS}h. "
            f"Poplatek za listování: {listing_fee} G."
        ),
        "listing":      listing.to_dict(),
        "listing_fee":  listing_fee,
    }


@router.post("/buy/{listing_id}")
async def buy_item(
    listing_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Koupí nabídku na trhu."""
    char = await _get_char(user, db)

    listing_res = await db.execute(
        select(MarketListing)
        .options(selectinload(MarketListing.item))
        .where(MarketListing.id == listing_id)
    )
    listing = listing_res.scalar_one_or_none()
    if not listing:
        raise HTTPException(404, "Nabídka nenalezena.")
    if listing.is_sold:
        raise HTTPException(400, "Tato nabídka je již prodána.")
    if _is_expired(listing):
        raise HTTPException(400, "Tato nabídka expirovala.")
    if listing.seller_id == char.id:
        raise HTTPException(400, "Nemůžeš koupit vlastní nabídku.")

    total_price = listing.price * listing.quantity
    if char.gold < total_price:
        raise HTTPException(400, f"Nedostatek goldu. Potřebuješ {total_price} G, máš {char.gold} G.")

    # Transakce
    char.gold -= total_price
    await log_gold(db, char, -total_price, GoldReason.MARKET_BUY,
                   {"listing_id": listing.id, "item_id": listing.item_id, "price": total_price})

    # Prodávajícímu připsat gold minus poplatek
    fee = int(total_price * MARKET_FEE)
    seller_gold = total_price - fee

    seller_res = await db.execute(
        select(Character).where(Character.id == listing.seller_id)
    )
    seller = seller_res.scalar_one_or_none()
    if seller:
        seller.gold += seller_gold
        await log_gold(db, seller, seller_gold, GoldReason.MARKET_SELL,
                       {"listing_id": listing.id, "item_id": listing.item_id,
                        "gross": total_price, "fee": fee})

    # Přidej item kupujícímu do inventáře — stackuj pouze pokud se shoduje i upgrade_level
    existing_res = await db.execute(
        select(InventoryItem).where(
            InventoryItem.character_id == char.id,
            InventoryItem.item_id == listing.item_id,
            InventoryItem.upgrade_level == (listing.upgrade_level or 0),
        )
    )
    existing = existing_res.scalar_one_or_none()
    if existing:
        existing.quantity += listing.quantity
    else:
        new_inv = InventoryItem(
            character_id=char.id,
            item_id=listing.item_id,
            quantity=listing.quantity,
            upgrade_level=listing.upgrade_level or 0,
        )
        db.add(new_inv)

    # Označ jako prodáno
    listing.is_sold = True
    listing.buyer_id = char.id

    await check_and_award(char, db)

    await db.commit()

    item_name = listing.item.name if listing.item else "?"
    return {
        "message": f"Koupeno '{item_name}' za {total_price} G (poplatek {fee} G).",
        "gold_spent": total_price,
        "gold_remaining": char.gold,
        "item": listing.item.to_dict() if listing.item else None,
    }


@router.delete("/cancel/{listing_id}")
async def cancel_listing(
    listing_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Zruší vlastní nabídku — item se vrátí do inventáře."""
    char = await _get_char(user, db)

    listing_res = await db.execute(
        select(MarketListing).where(MarketListing.id == listing_id)
    )
    listing = listing_res.scalar_one_or_none()
    if not listing:
        raise HTTPException(404, "Nabídka nenalezena.")
    if listing.seller_id != char.id:
        raise HTTPException(403, "Toto není tvoje nabídka.")
    if listing.is_sold:
        raise HTTPException(400, "Nabídka je již prodána, nelze zrušit.")

    # Vrať item do inventáře — stackuj pouze pokud se shoduje i upgrade_level
    existing_res = await db.execute(
        select(InventoryItem).where(
            InventoryItem.character_id == char.id,
            InventoryItem.item_id == listing.item_id,
            InventoryItem.upgrade_level == (listing.upgrade_level or 0),
        )
    )
    existing = existing_res.scalar_one_or_none()
    if existing:
        existing.quantity += listing.quantity
    else:
        db.add(InventoryItem(
            character_id=char.id,
            item_id=listing.item_id,
            quantity=listing.quantity,
            upgrade_level=listing.upgrade_level or 0,
        ))

    await db.delete(listing)
    await db.commit()

    return {"message": "Nabídka zrušena, item vrácen do inventáře."}


@router.get("/history")
async def purchase_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Historie nákupů a prodejů hráče."""
    char = await _get_char(user, db)

    result = await db.execute(
        select(MarketListing)
        .options(selectinload(MarketListing.item), selectinload(MarketListing.seller))
        .where(
            and_(
                MarketListing.is_sold == True,
                or_(
                    MarketListing.seller_id == char.id,
                    MarketListing.buyer_id == char.id,
                )
            )
        ).order_by(MarketListing.listed_at.desc()).limit(30)
    )
    listings = result.scalars().all()

    history = []
    for l in listings:
        d = l.to_dict()
        d["role"] = "seller" if l.seller_id == char.id else "buyer"
        d["fee"] = int(l.price * l.quantity * MARKET_FEE) if l.seller_id == char.id else 0
        history.append(d)

    return {"history": history}
