"""
routers/crystals.py — Crystal shop (earned premium currency)

Endpointy:
- GET  /crystals/shop           — shop + stav hráče (balance, aktivní efekty)
- POST /crystals/buy/{item_key} — nákup položky z Crystal shopu
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.user import User
from models.character import Character
from models.crystal import CRYSTAL_SHOP, CrystalTransaction
from models.scheduled_crystal_sale import ScheduledCrystalSale
from routers.auth import get_current_user
from routers.character import char_dict_with_equipment

router = APIRouter(prefix="/crystals", tags=["crystals"])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_char(user: User, db: AsyncSession) -> Character:
    result = await db.execute(select(Character).where(Character.user_id == user.id))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena.")
    return char


async def add_crystals(
    character_id: int,
    amount: int,
    reason: str,
    db: AsyncSession,
) -> None:
    """Přidá crystaly hráči a zaznamená transakci. Bez commit — volající commit provede sám."""
    res = await db.execute(select(Character).where(Character.id == character_id))
    char = res.scalar_one_or_none()
    if not char:
        return
    char.crystals = (char.crystals or 0) + amount
    txn = CrystalTransaction(
        character_id=character_id,
        amount=amount,
        reason=reason,
        balance_after=char.crystals,
    )
    db.add(txn)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/reset-frame")
async def reset_portrait_frame(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Odstraní aktivní rám portrétu (vrátí výchozí styl)."""
    char = await _get_char(user, db)
    if not char.crystal_portrait_frame:
        raise HTTPException(400, "Žádný rám portrétu není aktivní.")
    char.crystal_portrait_frame = None
    await db.commit()
    await db.refresh(char)
    return {
        "message": "Rám portrétu byl odstraněn.",
        "character": await char_dict_with_equipment(char, db),
    }


@router.post("/reset-name-color")
async def reset_name_color(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Odstraní aktivní barvu jména (vrátí výchozí barvu)."""
    char = await _get_char(user, db)
    if not char.crystal_name_color:
        raise HTTPException(400, "Žádná barva jména není aktivní.")
    char.crystal_name_color = None
    await db.commit()
    await db.refresh(char)
    return {
        "message": "Barva jména byla odstraněna.",
        "character": await char_dict_with_equipment(char, db),
    }


@router.get("/shop")
async def get_shop(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí Crystal shop katalog a aktuální stav hráče."""
    char = await _get_char(user, db)
    now  = datetime.now(timezone.utc).replace(tzinfo=None)

    xp_boost_active = bool(
        char.crystal_xp_boost_until and char.crystal_xp_boost_until > now
    )
    xp_boost_until_str = (
        char.crystal_xp_boost_until.isoformat()
        if (char.crystal_xp_boost_until and char.crystal_xp_boost_until > now)
        else None
    )

    # Aktivní slevy
    sales_res = await db.execute(
        select(ScheduledCrystalSale).where(
            ScheduledCrystalSale.starts_at <= now,
            ScheduledCrystalSale.ends_at   >= now,
        )
    )
    active_sales: dict[str, ScheduledCrystalSale] = {
        s.item_key: s for s in sales_res.scalars().all()
    }

    items = []
    for key, item in CRYSTAL_SHOP.items():
        entry = {**item, "key": key}
        if item["type"] == "consumable":
            entry["active"] = xp_boost_active
        elif item["type"] == "name_color":
            entry["owned"] = char.crystal_name_color == item.get("color")
        elif item["type"] == "portrait_frame":
            entry["owned"] = char.crystal_portrait_frame == item.get("frame")
        # Aplikuj slevu pokud existuje
        sale = active_sales.get(key)
        if sale:
            entry["sale_cost"]     = sale.sale_cost
            entry["sale_label"]    = sale.label
            entry["sale_ends_at"]  = sale.ends_at.isoformat()
            entry["discount_pct"]  = round((1 - sale.sale_cost / item["cost"]) * 100)
        items.append(entry)

    # Login streak info
    streak = char.login_streak or 0
    days_to_weekly  = 7  - (streak % 7)  if (streak % 7)  != 0 else 7
    days_to_monthly = 30 - (streak % 30) if (streak % 30) != 0 else 30
    if days_to_monthly <= days_to_weekly:
        streak_next = {"days": days_to_monthly, "amount": 50, "type": "monthly"}
    else:
        streak_next = {"days": days_to_weekly, "amount": 20, "type": "weekly"}

    return {
        "crystals":        char.crystals or 0,
        "name_color":      char.crystal_name_color,
        "portrait_frame":  char.crystal_portrait_frame,
        "xp_boost_until":  xp_boost_until_str,
        "xp_boost_active": xp_boost_active,
        "login_streak":    streak,
        "streak_next":     streak_next,
        "items":           items,
    }


@router.post("/buy/{item_key}")
async def buy_item(
    item_key: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Koupí položku z Crystal shopu."""
    char     = await _get_char(user, db)
    item_def = CRYSTAL_SHOP.get(item_key)
    if not item_def:
        raise HTTPException(404, f"Položka '{item_key}' v Crystal shopu neexistuje.")

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Zkontroluj aktivní slevu
    sale_res = await db.execute(
        select(ScheduledCrystalSale).where(
            ScheduledCrystalSale.item_key == item_key,
            ScheduledCrystalSale.starts_at <= now,
            ScheduledCrystalSale.ends_at   >= now,
        ).limit(1)
    )
    active_sale = sale_res.scalar_one_or_none()
    cost    = active_sale.sale_cost if active_sale else item_def["cost"]
    balance = char.crystals or 0
    if balance < cost:
        raise HTTPException(
            400,
            f"Nedostatek krystalů. Potřebuješ {cost} 💎, máš {balance} 💎.",
        )

    char.crystals = balance - cost

    item_type = item_def["type"]
    msg_parts = []

    if item_type == "consumable":
        current = char.crystal_xp_boost_until
        if current and current > now:
            char.crystal_xp_boost_until = current + timedelta(hours=24)
            msg_parts.append("XP Posílení prodlouženo o 24 hodin")
        else:
            char.crystal_xp_boost_until = now + timedelta(hours=24)
            msg_parts.append("XP Posílení aktivní na 24 hodin (+25 % XP)")

    elif item_type == "name_color":
        char.crystal_name_color = item_def["color"]
        msg_parts.append(f"Barva jména změněna: {item_def['name']}")

    elif item_type == "portrait_frame":
        char.crystal_portrait_frame = item_def["frame"]
        msg_parts.append(f"Rám portrétu nastaven: {item_def['name']}")

    # Zaznamenej výdaj (s poznámkou o slevě pokud platí)
    reason_suffix = f":sale{active_sale.id}" if active_sale else ""
    txn = CrystalTransaction(
        character_id=char.id,
        amount=-cost,
        reason=f"shop:{item_key}{reason_suffix}",
        balance_after=char.crystals,
    )
    db.add(txn)

    await db.commit()
    await db.refresh(char)

    return {
        "message":   f"✅ {item_def['emoji']} {item_def['name']} zakoupeno! {' · '.join(msg_parts)}",
        "crystals":  char.crystals,
        "character": await char_dict_with_equipment(char, db),
    }


@router.get("/transparency")
async def get_transparency():
    """
    Veřejný endpoint — transparentní mechaniky hry.
    Vrátí drop rates, crystal earning sources a design commitments.
    Nevyžaduje autentizaci.
    """
    from game.loot import DROP_CHANCE, RARITY_WEIGHTS

    drop_rates = []
    rarity_labels = ["Běžný", "Neobvyklý", "Vzácný", "Epický", "Legendární"]
    for diff, chance in DROP_CHANCE.items():
        weights = RARITY_WEIGHTS[diff]
        total = sum(weights)
        rarities = [
            {"label": rarity_labels[i], "pct": round(w / total * 100, 1)}
            for i, w in enumerate(weights)
        ]
        drop_rates.append({
            "difficulty":    diff,
            "label":         {"easy": "Snadný", "normal": "Normální", "hard": "Těžký", "boss": "Boss"}[diff],
            "drop_chance":   int(chance * 100),
            "rarities":      rarities,
        })

    crystal_sources = [
        {"icon": "🏅", "source": "Sezónní pass (tiery 2, 4, 6, 8, 10)",  "amount": "až 405 💎 za sezónu"},
        {"icon": "⚔️", "source": "Achievement chainy (5 chainů)",          "amount": "až 90 💎 celkem"},
        {"icon": "🌍", "source": "World Events (komunální cíle)",           "amount": "50–100 💎 za event"},
        {"icon": "⚜️", "source": "Guild War výhry (+25 💎 každému členovi)","amount": "neomezeno"},
        {"icon": "🔥", "source": "Login Streak (7 dní +20, 30 dní +50)",   "amount": "~50 💎 / měsíc"},
        {"icon": "✦",  "source": "Prestige levely (1–10)",                  "amount": "až 150 💎 celkem"},
    ]

    shop_items = [
        {"name": it["name"], "cost": it["cost"], "type": it["type"], "emoji": it["emoji"]}
        for it in CRYSTAL_SHOP.values()
    ]

    commitments = [
        {
            "icon":  "🚫",
            "title": "Žádná výhoda za peníze",
            "desc":  "Žádný předmět v Crystal shopu nedává bojovou výhodu. Crystaly jsou pouze pro kosmetiku a QoL.",
        },
        {
            "icon":  "🎁",
            "title": "Crystaly lze získat zcela zdarma",
            "desc":  "Všechny crystal položky lze dosáhnout aktivní hrou bez jakékoliv platby. Aktivní hráč vydělá stovky crystalů měsíčně.",
        },
        {
            "icon":  "📊",
            "title": "Transparentní pravděpodobnosti",
            "desc":  "Šance na drop předmětu a raritu jsou zde zveřejněny přesně tak, jak jsou implementovány v kódu. Žádné skryté algoritmy.",
        },
        {
            "icon":  "🚷",
            "title": "Žádné lootboxy ani gambling",
            "desc":  "V Crystal shopu nejsou žádné náhodné balíčky ani hazardní mechaniky. Každý nákup je přesně to, co vidíš.",
        },
        {
            "icon":  "♾️",
            "title": "Žádné uměle vytvořené scarcity",
            "desc":  "Kosmetické předměty nejsou dočasně skryté za účelem vyvolání FOMO. Pokud je položka dostupná, zůstane dostupná.",
        },
        {
            "icon":  "🔓",
            "title": "Otevřená herní matematika",
            "desc":  "Soft capy statistik, XP křivka, T2 cooldown, arena ELO — vše je dokumentováno a přístupné. Žádné black-boxy.",
        },
    ]

    return {
        "drop_rates":      drop_rates,
        "crystal_sources": crystal_sources,
        "shop_items":      shop_items,
        "commitments":     commitments,
        "ability_trigger_prob": 40,
        "t2_cooldown_rounds":   4,
        "arena_daily_gold_cap": 500,
        "elo_win":  20,
        "elo_loss": 15,
    }
