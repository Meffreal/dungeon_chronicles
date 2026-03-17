import pytest
from unittest.mock import AsyncMock, MagicMock
from game.combatant_builder import build_combatant_config

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

    db = AsyncMock()
    db.get = AsyncMock(return_value=None)

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

    db = AsyncMock()
    db.get = AsyncMock(return_value=None)

    cfg = await build_combatant_config(char, db)
    assert cfg.cls == "mage"
    assert cfg.primary_stat == 30   # INT
    assert cfg.secondary_a == 5    # STR
    assert cfg.secondary_b == 8    # DEX
    assert cfg.weapon_dmg == 4     # unarmed mage base
