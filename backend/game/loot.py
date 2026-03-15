"""
game/loot.py — Drop systém pro questy
"""
import random
from models.item import Rarity

# Šance na drop podle obtížnosti questu
DROP_CHANCE = {
    "easy":   0.20,
    "normal": 0.35,
    "hard":   0.55,
    "boss":   0.90,
}

# Šance na raritu (při dropu) podle obtížnosti
RARITY_WEIGHTS = {
    "easy":   [60, 30, 8,  2,  0],   # common, uncommon, rare, epic, legendary
    "normal": [40, 35, 18, 6,  1],
    "hard":   [20, 30, 30, 16, 4],
    "boss":   [5,  15, 30, 35, 15],
}

RARITIES = [Rarity.COMMON, Rarity.UNCOMMON, Rarity.RARE, Rarity.EPIC, Rarity.LEGENDARY]

def roll_drop(difficulty: str) -> bool:
    """Vrátí True pokud quest dá item drop."""
    return random.random() < DROP_CHANCE.get(difficulty, 0.25)

def roll_rarity(difficulty: str) -> Rarity:
    """Vrátí raritu dropu."""
    weights = RARITY_WEIGHTS.get(difficulty, RARITY_WEIGHTS["normal"])
    return random.choices(RARITIES, weights=weights, k=1)[0]

async def get_dungeon_set_item(db, char_cls: str):
    """
    Vrátí náhodný setový item odpovídající třídě postavy.
    Volá se při dokončení dungeon questu — garantovaný drop setového kusu.
    """
    from sqlalchemy import select
    from models.item import Item
    from models.sets import CLS_TO_SET_ID

    set_id = CLS_TO_SET_ID.get(char_cls)
    if set_id is None:
        return None

    result = await db.execute(
        select(Item).where(Item.set_id == set_id)
    )
    items = result.scalars().all()
    return random.choice(items) if items else None


async def get_random_item_for_quest(db, difficulty: str, character_level: int):
    """
    Vybere náhodný item z databáze odpovídající obtížnosti a levelu.
    Vrátí Item nebo None.
    """
    from sqlalchemy import select
    from models.item import Item

    if not roll_drop(difficulty):
        return None

    rarity = roll_rarity(difficulty)

    # Vyber item dané rarity který hráč může nosit
    result = await db.execute(
        select(Item).where(
            Item.rarity == rarity.value,
            Item.min_level <= character_level + 2,
        )
    )
    items = result.scalars().all()

    if not items:
        # Fallback — libovolný common item
        result = await db.execute(
            select(Item).where(Item.rarity == Rarity.COMMON.value).limit(10)
        )
        items = result.scalars().all()

    return random.choice(items) if items else None
