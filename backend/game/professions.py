"""
game/professions.py — Profese v3 game logic: Enchanter, Alchymista, Blacksmith
"""
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from models.profession import CharacterProfession, RANK_XP_THRESHOLDS, MAX_RANK
from models.character import Character
from models.item import InventoryItem, Item


# ── Základní helpery ──────────────────────────────────────────────────────────

async def get_char(user, db: AsyncSession) -> Character:
    result = await db.execute(select(Character).where(Character.user_id == user.id))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Nejdřív si vytvoř postavu.")
    return char


async def get_profession(char_id: int, db: AsyncSession) -> Optional[CharacterProfession]:
    result = await db.execute(
        select(CharacterProfession).where(CharacterProfession.character_id == char_id)
    )
    return result.scalar_one_or_none()


async def require_profession(char_id: int, profession_key: str, db: AsyncSession) -> CharacterProfession:
    prof = await get_profession(char_id, db)
    if not prof:
        raise HTTPException(403, "Nemáš zvolenou profesi.")
    if prof.profession_key != profession_key:
        raise HTTPException(403, f"Tato akce vyžaduje profesi '{profession_key}'.")
    return prof


async def require_profession_rank(char_id: int, profession_key: str, min_rank: int,
                                   db: AsyncSession) -> CharacterProfession:
    prof = await require_profession(char_id, profession_key, db)
    if prof.rank < min_rank:
        raise HTTPException(403, f"Potřebuješ Rank {min_rank} v '{profession_key}'. Aktuálně Rank {prof.rank}.")
    return prof


async def award_xp(char_id: int, profession_key: str, amount: int, db: AsyncSession) -> dict:
    """Přidá XP aktivní profesi. Vrátí dict s info o rank-up."""
    result = await db.execute(
        select(CharacterProfession).where(
            CharacterProfession.character_id == char_id,
            CharacterProfession.profession_key == profession_key,
        )
    )
    prof = result.scalar_one_or_none()
    if not prof or amount <= 0:
        return {"awarded": False}
    old_rank = prof.rank
    ranked_up = prof.add_xp(amount)
    return {"awarded": True, "xp_gained": amount, "ranked_up": ranked_up,
            "old_rank": old_rank, "new_rank": prof.rank}


# ── Inventory helpery ─────────────────────────────────────────────────────────

async def get_item_by_name(name: str, db: AsyncSession) -> Optional[Item]:
    result = await db.execute(select(Item).where(Item.name == name))
    return result.scalar_one_or_none()


async def get_inventory_count(char_id: int, item_name: str, db: AsyncSession) -> int:
    """Vrátí celkové množství daného itemu v inventáři postavy."""
    item = await get_item_by_name(item_name, db)
    if not item:
        return 0
    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.character_id == char_id,
            InventoryItem.item_id == item.id,
        )
    )
    rows = result.scalars().all()
    return sum(r.quantity for r in rows)


async def give_item(char_id: int, item_name: str, amount: int, db: AsyncSession) -> None:
    """Přidá item do inventáře (stack nebo nový řádek)."""
    if amount <= 0:
        return
    item = await get_item_by_name(item_name, db)
    if not item:
        raise HTTPException(500, f"Item '{item_name}' nebyl nalezen v databázi.")
    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.character_id == char_id,
            InventoryItem.item_id == item.id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.quantity += amount
    else:
        db.add(InventoryItem(character_id=char_id, item_id=item.id, quantity=amount))


async def consume_item(char_id: int, item_name: str, amount: int, db: AsyncSession) -> None:
    """Spotřebuje item z inventáře. Vyhodí 400 pokud nestačí."""
    if amount <= 0:
        return
    item = await get_item_by_name(item_name, db)
    if not item:
        raise HTTPException(400, f"Nemáš žádný '{item_name}'.")
    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.character_id == char_id,
            InventoryItem.item_id == item.id,
        )
    )
    rows = result.scalars().all()
    total = sum(r.quantity for r in rows)
    if total < amount:
        raise HTTPException(400, f"Nedostatek '{item_name}': potřebuješ {amount}, máš {total}.")
    remaining = amount
    for row in sorted(rows, key=lambda r: r.quantity):
        if remaining <= 0:
            break
        if row.quantity <= remaining:
            remaining -= row.quantity
            await db.delete(row)
        else:
            row.quantity -= remaining
            remaining = 0


async def consume_costs(char_id: int, costs: dict, db: AsyncSession) -> None:
    """Spotřebuje více itemů najednou dle dict {item_name: amount}."""
    for item_name, amount in costs.items():
        await consume_item(char_id, item_name, amount, db)


async def give_items(char_id: int, outputs: dict, db: AsyncSession) -> list[dict]:
    """Dá více itemů najednou. Vrátí list {name, amount}."""
    results = []
    for item_name, amount in outputs.items():
        await give_item(char_id, item_name, amount, db)
        results.append({"name": item_name, "amount": amount})
    return results


# ── Recipes ───────────────────────────────────────────────────────────────────

# Enchanter - disenchant outputs by rarity
DISENCHANT_OUTPUTS = {
    "common":      {"min_rank": 0, "outputs": {"Arcane Dust": 2}},
    "uncommon":    {"min_rank": 2, "outputs": {"Enchanted Shard": 2}},
    "rare":        {"min_rank": 2, "outputs": {"Enchanted Shard": 3}},
    "epic":        {"min_rank": 4, "outputs": {"Void Crystal": 1}},
    "legendary":   {"min_rank": 4, "outputs": {"Void Crystal": 2}},
    "soul_crafted":{"min_rank": 4, "outputs": {"Void Crystal": 3}},
}

# Enchanter - enchant costs by rarity
ENCHANT_COSTS = {
    "common":      {"min_rank": 0, "cost": {"Metal Scraps": 2, "Alchemic Residue": 1}},
    "uncommon":    {"min_rank": 0, "cost": {"Metal Scraps": 2, "Alchemic Residue": 1}},
    "rare":        {"min_rank": 2, "cost": {"Metal Scraps": 3, "Alchemic Residue": 2}},
    "epic":        {"min_rank": 3, "cost": {"Metal Scraps": 4, "Potent Extract": 1}},
    "legendary":   {"min_rank": 4, "cost": {"Metal Scraps": 5, "Potent Extract": 2}},
    "soul_crafted":{"min_rank": 4, "cost": {"Metal Scraps": 6, "Potent Extract": 2}},
}

SIGNATURE_EXTRA_COST = {"Essence Concentrate": 1}  # rank 5 enchants

BASIC_ENCHANT_EFFECTS  = ["atk", "def", "hp"]
SIGNATURE_ENCHANT_EFFECTS = ["lifesteal", "reflect", "crit_bonus"]

ENCHANT_STAT_VALUES = {
    "common":      {"atk": 3,  "def": 3,  "hp": 15},
    "uncommon":    {"atk": 5,  "def": 5,  "hp": 25},
    "rare":        {"atk": 8,  "def": 8,  "hp": 40},
    "epic":        {"atk": 12, "def": 12, "hp": 60},
    "legendary":   {"atk": 18, "def": 18, "hp": 90},
    "soul_crafted":{"atk": 24, "def": 24, "hp": 120},
}
ENCHANT_SIGNATURE_VALUES = {"lifesteal": 0.05, "reflect": 0.05, "crit_bonus": 0.05}

CRAFT_SCROLL_COST = {"Void Crystal": 3, "Essence Concentrate": 2}

# Alchymista - brew recipes
BREW_RECIPES = {
    "HP Potion":                    {"min_rank": 0, "cost": {"Metal Scraps": 2}},
    "MP Potion":                    {"min_rank": 0, "cost": {"Metal Scraps": 2}},
    "Combat Elixir: Attack":        {"min_rank": 2, "cost": {"Metal Scraps": 3, "Arcane Dust": 2}},
    "Combat Elixir: Defense":       {"min_rank": 2, "cost": {"Metal Scraps": 3, "Arcane Dust": 2}},
    "XP Elixir":                    {"min_rank": 3, "cost": {"Metal Scraps": 4, "Arcane Dust": 3}},
    "Gold Elixir":                  {"min_rank": 3, "cost": {"Metal Scraps": 4, "Arcane Dust": 3}},
    "Crit Boost Elixir":            {"min_rank": 4, "cost": {"Metal Scraps": 5, "Arcane Dust": 2, "Potent Extract": 2}},
    "Shield Elixir":                {"min_rank": 4, "cost": {"Metal Scraps": 5, "Arcane Dust": 2, "Potent Extract": 2}},
    "Legendary Elixir: Berserk":    {"min_rank": 5, "cost": {"Essence Concentrate": 3, "Arcane Dust": 2}},
    "Legendary Elixir: Arcane Surge":{"min_rank": 5, "cost": {"Essence Concentrate": 3, "Arcane Dust": 2}},
}

# Alchymista - dissolve outputs by item name
DISSOLVE_OUTPUTS = {
    "HP Potion":                    {"min_rank": 0, "outputs": {"Alchemic Residue": 1}},
    "MP Potion":                    {"min_rank": 0, "outputs": {"Alchemic Residue": 1}},
    "Combat Elixir: Attack":        {"min_rank": 3, "outputs": {"Potent Extract": 1}},
    "Combat Elixir: Defense":       {"min_rank": 3, "outputs": {"Potent Extract": 1}},
    "XP Elixir":                    {"min_rank": 3, "outputs": {"Potent Extract": 1}},
    "Gold Elixir":                  {"min_rank": 3, "outputs": {"Potent Extract": 1}},
    "Crit Boost Elixir":            {"min_rank": 4, "outputs": {"Potent Extract": 2}},
    "Shield Elixir":                {"min_rank": 4, "outputs": {"Potent Extract": 2}},
    "Legendary Elixir: Berserk":    {"min_rank": 5, "outputs": {"Essence Concentrate": 1}},
    "Legendary Elixir: Arcane Surge":{"min_rank": 5, "outputs": {"Essence Concentrate": 1}},
}

# Blacksmith - destroy outputs by rarity
DESTROY_OUTPUTS = {
    "common":      {"min_rank": 0, "outputs": {"Metal Scraps": 2}},
    "uncommon":    {"min_rank": 0, "outputs": {"Metal Scraps": 3}},
    "rare":        {"min_rank": 3, "outputs": {"Refined Ore": 1}},
    "epic":        {"min_rank": 3, "outputs": {"Refined Ore": 2}},
    "legendary":   {"min_rank": 5, "outputs": {"Soulsteel Fragment": 1}},
    "soul_crafted":{"min_rank": 5, "outputs": {"Soulsteel Fragment": 2}},
}

# Blacksmith - upgrade recipes by input rarity
UPGRADE_RECIPES = {
    "common":    {"min_rank": 1, "output": "uncommon",     "cost": {"Void Crystal": 2, "Essence Concentrate": 2}},
    "uncommon":  {"min_rank": 2, "output": "rare",         "cost": {"Void Crystal": 3, "Essence Concentrate": 2}},
    "rare":      {"min_rank": 3, "output": "epic",         "cost": {"Void Crystal": 4, "Essence Concentrate": 3}},
    "epic":      {"min_rank": 4, "output": "legendary",    "cost": {"Void Crystal": 5, "Essence Concentrate": 4}},
    "legendary": {"min_rank": 5, "output": "soul_crafted", "cost": {"Void Crystal": 4, "Soulsteel Fragment": 2, "Essence Concentrate": 3}},
}

XP_PER_ACTION = {
    "disenchant":  15,
    "enchant":     20,
    "craft_scroll":25,
    "brew":        15,
    "dissolve":    10,
    "destroy":     15,
    "upgrade":     25,
}


# ── Enchanter akce ────────────────────────────────────────────────────────────

async def do_disenchant(char_id: int, inv_item_id: int, db: AsyncSession) -> dict:
    prof = await require_profession(char_id, "enchanter", db)

    inv_res = await db.execute(
        select(InventoryItem).where(
            InventoryItem.id == inv_item_id,
            InventoryItem.character_id == char_id,
        )
    )
    inv = inv_res.scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Item nenalezen v inventáři.")

    item_res = await db.execute(select(Item).where(Item.id == inv.item_id))
    item = item_res.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item data nenalezena.")

    effective_rarity = inv.override_rarity or item.rarity
    recipe = DISENCHANT_OUTPUTS.get(effective_rarity)
    if not recipe:
        raise HTTPException(400, f"Nelze disenchantovat item s raritou '{effective_rarity}'.")
    if prof.rank < recipe["min_rank"]:
        raise HTTPException(403, f"Potřebuješ Rank {recipe['min_rank']} pro disenchant '{effective_rarity}'.")

    # Spotřebuj item
    if inv.quantity > 1:
        inv.quantity -= 1
    else:
        await db.delete(inv)

    # Dej reagenty
    received = await give_items(char_id, recipe["outputs"], db)

    xp_info = await award_xp(char_id, "enchanter", XP_PER_ACTION["disenchant"], db)
    return {"received": received, "xp": xp_info}


async def do_enchant(char_id: int, inv_item_id: int, effect: str, db: AsyncSession) -> dict:
    """effect: atk | def | hp | lifesteal | reflect | crit_bonus"""
    is_signature = effect in SIGNATURE_ENCHANT_EFFECTS
    min_rank = 5 if is_signature else 1

    prof = await require_profession_rank(char_id, "enchanter", min_rank, db)

    inv_res = await db.execute(
        select(InventoryItem).where(
            InventoryItem.id == inv_item_id,
            InventoryItem.character_id == char_id,
        )
    )
    inv = inv_res.scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Item nenalezen v inventáři.")

    item_res = await db.execute(select(Item).where(Item.id == inv.item_id))
    item = item_res.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item data nenalezena.")

    # Potions/reagents nelze enchantovat
    if item.item_type in ("potion", "elixir", "reagent", "scroll"):
        raise HTTPException(400, "Tento typ itemu nelze enchantovat.")

    effective_rarity = inv.override_rarity or item.rarity
    enchant_rule = ENCHANT_COSTS.get(effective_rarity)
    if not enchant_rule:
        raise HTTPException(400, f"Nelze enchantovat item s raritou '{effective_rarity}'.")
    if prof.rank < enchant_rule["min_rank"]:
        raise HTTPException(403, f"Potřebuješ Rank {enchant_rule['min_rank']} pro enchant '{effective_rarity}'.")

    # Zkontroluj dual enchant (max 2 enchants, rank 3+ pro 2. enchant)
    existing_enchants = json.loads(inv.enchants_json) if inv.enchants_json else []
    if len(existing_enchants) >= 1 and prof.rank < 3:
        raise HTTPException(403, "Dual enchant vyžaduje Rank 3.")
    if len(existing_enchants) >= 2:
        raise HTTPException(400, "Item již má maximální počet enchantů (2).")

    # Zkontroluj duplicitní efekt
    if any(e["effect"] == effect for e in existing_enchants):
        raise HTTPException(400, f"Item již má enchant '{effect}'.")

    # Validuj efekt
    all_effects = BASIC_ENCHANT_EFFECTS + SIGNATURE_ENCHANT_EFFECTS
    if effect not in all_effects:
        raise HTTPException(400, f"Neznámý enchant efekt '{effect}'. Dostupné: {all_effects}")

    # Cost
    cost = dict(enchant_rule["cost"])
    if is_signature:
        for k, v in SIGNATURE_EXTRA_COST.items():
            cost[k] = cost.get(k, 0) + v
    if len(existing_enchants) >= 1:  # dual enchant — double cost
        cost = {k: v * 2 for k, v in cost.items()}

    await consume_costs(char_id, cost, db)

    # Aplikuj enchant
    if is_signature:
        value = ENCHANT_SIGNATURE_VALUES[effect]
    else:
        stats = ENCHANT_STAT_VALUES.get(effective_rarity, ENCHANT_STAT_VALUES["common"])
        value = stats[effect]

    existing_enchants.append({"effect": effect, "value": value})
    inv.enchants_json = json.dumps(existing_enchants)

    xp_info = await award_xp(char_id, "enchanter", XP_PER_ACTION["enchant"], db)
    return {"enchants": existing_enchants, "cost_paid": cost, "xp": xp_info}


async def do_craft_scroll(char_id: int, db: AsyncSession) -> dict:
    await require_profession_rank(char_id, "enchanter", 5, db)
    await consume_costs(char_id, CRAFT_SCROLL_COST, db)
    await give_item(char_id, "Enchant Scroll", 1, db)
    xp_info = await award_xp(char_id, "enchanter", XP_PER_ACTION["craft_scroll"], db)
    return {"received": [{"name": "Enchant Scroll", "amount": 1}], "xp": xp_info}


# ── Alchymista akce ───────────────────────────────────────────────────────────

async def do_brew(char_id: int, recipe_name: str, db: AsyncSession) -> dict:
    recipe = BREW_RECIPES.get(recipe_name)
    if not recipe:
        raise HTTPException(400, f"Neznámý recept '{recipe_name}'.")

    await require_profession_rank(char_id, "alchymista", recipe["min_rank"], db)
    await consume_costs(char_id, recipe["cost"], db)
    await give_item(char_id, recipe_name, 1, db)

    xp_info = await award_xp(char_id, "alchymista", XP_PER_ACTION["brew"], db)
    return {"brewed": recipe_name, "cost_paid": recipe["cost"], "xp": xp_info}


async def do_dissolve(char_id: int, inv_item_id: int, db: AsyncSession) -> dict:
    prof = await require_profession(char_id, "alchymista", db)

    inv_res = await db.execute(
        select(InventoryItem).where(
            InventoryItem.id == inv_item_id,
            InventoryItem.character_id == char_id,
        )
    )
    inv = inv_res.scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Item nenalezen v inventáři.")

    item_res = await db.execute(select(Item).where(Item.id == inv.item_id))
    item = item_res.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item data nenalezena.")

    recipe = DISSOLVE_OUTPUTS.get(item.name)
    if not recipe:
        raise HTTPException(400, f"Item '{item.name}' nelze dissolveovat.")
    if prof.rank < recipe["min_rank"]:
        raise HTTPException(403, f"Potřebuješ Rank {recipe['min_rank']} pro dissolve '{item.name}'.")

    # Spotřebuj item
    if inv.quantity > 1:
        inv.quantity -= 1
    else:
        await db.delete(inv)

    received = await give_items(char_id, recipe["outputs"], db)
    xp_info = await award_xp(char_id, "alchymista", XP_PER_ACTION["dissolve"], db)
    return {"received": received, "xp": xp_info}


# ── Blacksmith akce ───────────────────────────────────────────────────────────

async def do_destroy(char_id: int, inv_item_id: int, db: AsyncSession) -> dict:
    prof = await require_profession(char_id, "blacksmith", db)

    inv_res = await db.execute(
        select(InventoryItem).where(
            InventoryItem.id == inv_item_id,
            InventoryItem.character_id == char_id,
        )
    )
    inv = inv_res.scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Item nenalezen v inventáři.")

    item_res = await db.execute(select(Item).where(Item.id == inv.item_id))
    item = item_res.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item data nenalezena.")

    # Potions/reagents/scrolls nelze zničit
    if item.item_type in ("potion", "elixir", "reagent", "scroll"):
        raise HTTPException(400, "Tento typ itemu nelze zničit.")

    effective_rarity = inv.override_rarity or item.rarity
    recipe = DESTROY_OUTPUTS.get(effective_rarity)
    if not recipe:
        raise HTTPException(400, f"Nelze zničit item s raritou '{effective_rarity}'.")
    if prof.rank < recipe["min_rank"]:
        raise HTTPException(403, f"Potřebuješ Rank {recipe['min_rank']} pro zničení '{effective_rarity}'.")

    # Spotřebuj item
    if inv.quantity > 1:
        inv.quantity -= 1
    else:
        await db.delete(inv)

    received = await give_items(char_id, recipe["outputs"], db)
    xp_info = await award_xp(char_id, "blacksmith", XP_PER_ACTION["destroy"], db)
    return {"received": received, "xp": xp_info}


async def do_upgrade(char_id: int, inv_item_id: int, db: AsyncSession) -> dict:
    prof = await require_profession(char_id, "blacksmith", db)

    inv_res = await db.execute(
        select(InventoryItem).where(
            InventoryItem.id == inv_item_id,
            InventoryItem.character_id == char_id,
        )
    )
    inv = inv_res.scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Item nenalezen v inventáři.")

    item_res = await db.execute(select(Item).where(Item.id == inv.item_id))
    item = item_res.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item data nenalezena.")

    if item.item_type in ("potion", "elixir", "reagent", "scroll"):
        raise HTTPException(400, "Tento typ itemu nelze upgradovat.")

    effective_rarity = inv.override_rarity or item.rarity
    recipe = UPGRADE_RECIPES.get(effective_rarity)
    if not recipe:
        raise HTTPException(400, f"Rarity '{effective_rarity}' nelze upgradovat (max: legendary → soul_crafted).")
    if prof.rank < recipe["min_rank"]:
        raise HTTPException(403, f"Potřebuješ Rank {recipe['min_rank']} pro upgrade '{effective_rarity}' → '{recipe['output']}'.")

    await consume_costs(char_id, recipe["cost"], db)

    inv.override_rarity = recipe["output"]

    xp_info = await award_xp(char_id, "blacksmith", XP_PER_ACTION["upgrade"], db)
    return {
        "old_rarity": effective_rarity,
        "new_rarity": recipe["output"],
        "cost_paid":  recipe["cost"],
        "xp":         xp_info,
    }


# ── Backward compat stubs (volá quest.py a arena.py) ─────────────────────────

async def add_resonance_to_equipped_runes(char, amount: int, db: AsyncSession) -> list:
    """Legacy stub — runy neexistují v v3. Vrátí prázdný list."""
    return []


async def get_oracle_xp_bonus(char_id: int, base_xp: int, db: AsyncSession) -> int:
    """Legacy stub — oracle profese neexistuje v v3. Vrátí 0."""
    return 0


async def get_broker_gold_bonus(char_id: int, base_gold: int, db: AsyncSession) -> int:
    """Legacy stub — broker profese neexistuje v v3. Vrátí 0."""
    return 0
