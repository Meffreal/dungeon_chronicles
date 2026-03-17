import pytest
from unittest.mock import AsyncMock, MagicMock
from game.combatant_builder import build_combatant_config


def _make_db(get_side_effect=None, get_return=None):
    """Vytvoří AsyncMock db s nastaveným get() a execute() vracejícím None."""
    db = AsyncMock()
    if get_side_effect is not None:
        db.get = get_side_effect
    else:
        db.get = AsyncMock(return_value=get_return)
    # set_bonuses.py volá db.execute(); vrátíme mock result kde scalar_one_or_none() = None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    db.execute = AsyncMock(return_value=mock_result)
    return db


@pytest.mark.asyncio
async def test_warrior_uses_strength_as_primary():
    char = MagicMock()
    char.cls = "warrior"
    char.strength = 30
    char.dexterity = 10
    char.intelligence = 5
    char.endurance = 15
    char.luck = 5
    char.level = 10
    char.hp_max = 825
    char.eq_weapon = None
    char.eq_helmet = char.eq_armor = char.eq_gloves = None
    char.eq_boots = char.eq_ring = char.eq_amulet = None
    char.talents_json = "[]"
    char.get_talents = MagicMock(return_value=[])
    char.talent_t2_key = ""
    char.subclass = ""
    char.prestige_level = 0
    char.name = "TestWarrior"

    db = _make_db()

    cfg = await build_combatant_config(char, db)
    assert cfg.cls == "warrior"
    assert cfg.primary_stat == 30   # STR
    assert cfg.secondary_a == 10   # DEX
    assert cfg.secondary_b == 5    # INT
    assert cfg.weapon_dmg == 8     # unarmed warrior base

@pytest.mark.asyncio
async def test_mage_uses_intelligence_as_primary():
    char = MagicMock()
    char.cls = "mage"
    char.strength = 5
    char.dexterity = 8
    char.intelligence = 30
    char.luck = 8
    char.level = 10
    char.hp_max = 176
    char.eq_weapon = None
    char.eq_helmet = char.eq_armor = char.eq_gloves = None
    char.eq_boots = char.eq_ring = char.eq_amulet = None
    char.get_talents = MagicMock(return_value=[])
    char.talent_t2_key = ""
    char.subclass = ""
    char.name = "TestMage"

    db = _make_db()

    cfg = await build_combatant_config(char, db)
    assert cfg.cls == "mage"
    assert cfg.primary_stat == 30   # INT
    assert cfg.secondary_a == 5    # STR
    assert cfg.secondary_b == 8    # DEX
    assert cfg.weapon_dmg == 5     # unarmed mage base (CLASS_WEAPON_BASE["mage"] = 5)


@pytest.mark.asyncio
async def test_mage_gear_int_included_in_primary_stat():
    """bonus_int na weapon a amulet musí být přičten k primary_stat mága."""
    char = MagicMock()
    char.cls = "mage"
    char.strength = 5
    char.dexterity = 8
    char.intelligence = 18   # base
    char.luck = 8
    char.level = 10
    char.hp_max = 176
    char.eq_weapon = 1
    char.eq_helmet = char.eq_armor = char.eq_gloves = None
    char.eq_boots = char.eq_ring = None
    char.eq_amulet = 2
    char.get_talents = MagicMock(return_value=[])
    char.talent_t2_key = ""
    char.subclass = ""
    char.name = "TestMage"

    weapon_item = MagicMock()
    weapon_item.bonus_atk = 35
    weapon_item.bonus_def = 0
    weapon_item.bonus_str = 0
    weapon_item.bonus_dex = 0
    weapon_item.bonus_int = 20   # Žezlo věčnosti
    weapon_item.bonus_end = 0
    weapon_item.bonus_luck = 0
    weapon_item.bonus_hp = 0

    amulet_item = MagicMock()
    amulet_item.bonus_atk = 0
    amulet_item.bonus_def = 0
    amulet_item.bonus_str = 0
    amulet_item.bonus_dex = 0
    amulet_item.bonus_int = 10   # Amulet Arkanního Mistra
    amulet_item.bonus_end = 0
    amulet_item.bonus_luck = 0
    amulet_item.bonus_hp = 0

    async def mock_get(model, item_id):
        if item_id == 1: return weapon_item
        if item_id == 2: return amulet_item
        return None

    db = _make_db(get_side_effect=mock_get)

    cfg = await build_combatant_config(char, db)
    assert cfg.primary_stat == 48   # 18 base + 20 weapon + 10 amulet
    assert cfg.weapon_dmg == 35


@pytest.mark.asyncio
async def test_missing_item_falls_back_to_class_base():
    """Pokud item_id odkazuje na neexistující item, weapon_dmg = class base."""
    char = MagicMock()
    char.cls = "mage"
    char.strength = 5
    char.dexterity = 8
    char.intelligence = 18
    char.luck = 8
    char.level = 1
    char.hp_max = 100
    char.eq_weapon = 999   # neexistující item
    char.eq_helmet = char.eq_armor = char.eq_gloves = None
    char.eq_boots = char.eq_ring = char.eq_amulet = None
    char.get_talents = MagicMock(return_value=[])
    char.talent_t2_key = ""
    char.subclass = ""
    char.name = "TestMageNoItem"

    db = _make_db(get_return=None)   # item nenalezen

    cfg = await build_combatant_config(char, db)
    assert cfg.weapon_dmg == 5     # fallback na CLASS_WEAPON_BASE["mage"] = 5
    assert cfg.primary_stat == 18  # base INT, žádný gear bonus


@pytest.mark.asyncio
async def test_warrior_gear_str_included_in_primary_stat():
    """bonus_str na vybavených itemech musí být přičten k primary_stat warriora."""
    char = MagicMock()
    char.cls = "warrior"
    char.strength = 15   # base
    char.dexterity = 8
    char.intelligence = 5
    char.luck = 5
    char.level = 10
    char.hp_max = 825
    char.eq_weapon = 1
    char.eq_helmet = None
    char.eq_armor = char.eq_gloves = None
    char.eq_boots = char.eq_ring = char.eq_amulet = None
    char.get_talents = MagicMock(return_value=[])
    char.talent_t2_key = ""
    char.subclass = ""
    char.name = "TestWarrior"

    weapon_item = MagicMock()
    weapon_item.bonus_atk = 55
    weapon_item.bonus_def = 0
    weapon_item.bonus_str = 10   # Excalibur
    weapon_item.bonus_dex = 5
    weapon_item.bonus_int = 0
    weapon_item.bonus_end = 0
    weapon_item.bonus_luck = 0
    weapon_item.bonus_hp = 0

    async def mock_get(model, item_id):
        if item_id == 1: return weapon_item
        return None

    db = _make_db(get_side_effect=mock_get)

    cfg = await build_combatant_config(char, db)
    assert cfg.primary_stat == 25   # 15 base + 10 weapon str
    assert cfg.secondary_a == 13   # 8 base + 5 weapon dex
    assert cfg.weapon_dmg == 55


@pytest.mark.asyncio
async def test_gear_bonuses_from_all_slots():
    """bonus_int ze všech 7 slotů musí být sečteny."""
    char = MagicMock()
    char.cls = "mage"
    char.strength = 5
    char.dexterity = 8
    char.intelligence = 18
    char.luck = 8
    char.level = 10
    char.hp_max = 176
    char.eq_weapon = 1
    char.eq_helmet = 2
    char.eq_armor = 3
    char.eq_gloves = 4
    char.eq_boots = 5
    char.eq_ring = 6
    char.eq_amulet = 7
    char.get_talents = MagicMock(return_value=[])
    char.talent_t2_key = ""
    char.subclass = ""
    char.name = "TestMageFull"

    def make_item(bonus_int_val, bonus_atk_val=0, bonus_def_val=0):
        m = MagicMock()
        m.bonus_atk = bonus_atk_val
        m.bonus_def = bonus_def_val
        m.bonus_str = 0
        m.bonus_dex = 0
        m.bonus_int = bonus_int_val
        m.bonus_end = 0
        m.bonus_luck = 0
        m.bonus_hp = 0
        return m

    items = {
        1: make_item(12, bonus_atk_val=40),  # weapon
        2: make_item(10, bonus_def_val=15),  # helmet
        3: make_item(12, bonus_def_val=25),  # armor
        4: make_item(8,  bonus_def_val=0),   # gloves
        5: make_item(5,  bonus_def_val=10),  # boots
        6: make_item(8,  bonus_def_val=0),   # ring
        7: make_item(10, bonus_def_val=0),   # amulet
    }

    async def mock_get(model, item_id):
        return items.get(item_id)

    db = _make_db(get_side_effect=mock_get)

    cfg = await build_combatant_config(char, db)
    assert cfg.primary_stat == 18 + 65   # 18 base + 65 total gear INT
    assert cfg.weapon_dmg == 40
    assert cfg.armor_value == 50   # 15+25+0+10+0+0 (weapon bonus_def ignorováno)
