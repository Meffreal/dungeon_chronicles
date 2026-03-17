# Combat Gear Stats Bug Fix — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Opravit `combatant_builder.py` tak, aby gear bonusy (`bonus_str/dex/int`) byly zahrnuty v combat stats — aktuálně jsou zcela ignorovány, způsobují výraznou slabost mága i ostatních tříd.

**Architecture:** Konsolidovat `_get_weapon_dmg` + `_get_armor_value` do jedné async funkce `_get_gear_stats` která načte všech 7 slotů jedním průchodem a vrátí weapon_dmg, armor_value, eq_str, eq_dex, eq_int, eq_luck. Odstranit `_primary_secondary` a inline stat mapping do `build_combatant_config`. Poznámka: `bonus_def` na weapon slotu je záměrně ignorován (armor value = pouze armor sloty).

**Tech Stack:** Python, SQLAlchemy async (`db.get`), pytest + pytest-asyncio, `unittest.mock.AsyncMock`

---

## Soubory

| Akce | Soubor |
|------|--------|
| Modify | `backend/game/combatant_builder.py` |
| Test (rozšíření) | `backend/tests/test_combatant_builder.py` |

---

## Bug — vysvětlení

`recalculate_with_gear` v `inventory.py` přidává gear stat bonusy k `char.intelligence` aj. **dočasně** (add → recalculate_stats → subtract). `recalculate_stats` počítá pouze `hp_max` přes `endurance`, INT nepoužívá. Po odečtení zůstane v DB pouze base INT (18 u mága). `build_combatant_config` čte `char.intelligence` z DB → gear `bonus_int` (+9, +15, +20 atd.) nemá na damage žádný efekt.

---

## Task 1: Přidat failing testy pro gear stat bonusy

**Files:**
- Modify: `backend/tests/test_combatant_builder.py`

- [ ] **Step 1: Přidat testy na konec `test_combatant_builder.py`**

```python
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

    db = AsyncMock()
    db.get = mock_get

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

    db = AsyncMock()
    db.get = AsyncMock(return_value=None)   # item nenalezen

    cfg = await build_combatant_config(char, db)
    assert cfg.weapon_dmg == 4     # fallback na CLASS_WEAPON_BASE["mage"]
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

    db = AsyncMock()
    db.get = mock_get

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

    db = AsyncMock()
    db.get = mock_get

    cfg = await build_combatant_config(char, db)
    assert cfg.primary_stat == 18 + 65   # 18 base + 65 total gear INT
    assert cfg.weapon_dmg == 40
    assert cfg.armor_value == 50   # 15+25+0+10+0+0 (weapon bonus_def ignorováno)
```

- [ ] **Step 2: Spustit testy a ověřit FAIL**

```bash
cd backend && pytest tests/test_combatant_builder.py -v
```

Očekávaný výsledek: 3 nové testy FAIL (stávající 2 musí stále PASS)

---

## Task 2: Implementovat opravu v `combatant_builder.py`

**Files:**
- Modify: `backend/game/combatant_builder.py`

- [ ] **Step 3: Přepsat `combatant_builder.py` celý soubor**

```python
"""
game/combatant_builder.py — Sestaví CombatantConfig z Character modelu.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from game.combat_engine import CombatantConfig
from game.combat_stats import CLASS_WEAPON_BASE


async def _get_gear_stats(
    char, db: AsyncSession
) -> tuple[int, int, int, int, int, int]:
    """Vrátí (weapon_dmg, armor_value, eq_str, eq_dex, eq_int, eq_luck) ze všech 7 slotů.

    Prochází weapon + 6 armor slotů jedním průchodem:
    - weapon_dmg: bonus_atk z weapon slotu (fallback na CLASS_WEAPON_BASE)
    - armor_value: součet bonus_def z armor slotů (weapon slot ignorován — záměrně)
    - eq_str/dex/int/luck: součet ze všech slotů
    """
    from models.item import Item

    weapon_dmg = CLASS_WEAPON_BASE.get(char.cls, 5)
    armor_val = eq_str = eq_dex = eq_int = eq_luck = 0

    slot_ids = [
        char.eq_weapon, char.eq_helmet, char.eq_armor,
        char.eq_gloves, char.eq_boots,  char.eq_ring, char.eq_amulet,
    ]

    for idx, item_id in enumerate(slot_ids):
        if item_id is None:
            continue
        item = await db.get(Item, item_id)
        if not item:
            continue
        if idx == 0:  # weapon slot — bonus_atk jako weapon_dmg
            weapon_dmg = item.bonus_atk or CLASS_WEAPON_BASE.get(char.cls, 5)
        else:         # armor sloty — bonus_def jako armor
            armor_val += item.bonus_def or 0
        eq_str  += item.bonus_str  or 0
        eq_dex  += item.bonus_dex  or 0
        eq_int  += item.bonus_int  or 0
        eq_luck += item.bonus_luck or 0

    return weapon_dmg, armor_val, eq_str, eq_dex, eq_int, eq_luck


async def build_combatant_config(char, db: AsyncSession) -> CombatantConfig:
    """Sestaví CombatantConfig z Character ORM objektu."""
    from game.set_bonuses import get_char_set_combat_effects  # lazy import

    weapon_dmg, armor_value, eq_str, eq_dex, eq_int, eq_luck = await _get_gear_stats(char, db)

    s = char.strength     + eq_str
    d = char.dexterity    + eq_dex
    i = char.intelligence + eq_int

    cls = char.cls
    if cls == "warrior":
        primary, sec_a, sec_b = s, d, i
    elif cls == "ranger":
        primary, sec_a, sec_b = d, s, i
    elif cls == "mage":
        primary, sec_a, sec_b = i, s, d
    else:
        primary, sec_a, sec_b = 0, 0, 0

    set_bonuses = await get_char_set_combat_effects(char, db)
    talents     = char.get_talents() if hasattr(char, 'get_talents') else []

    return CombatantConfig(
        name         = char.name,
        hp           = char.hp_max,
        weapon_dmg   = weapon_dmg,
        armor_value  = armor_value,
        primary_stat = primary,
        secondary_a  = sec_a,
        secondary_b  = sec_b,
        luck         = char.luck + eq_luck,
        level        = char.level,
        cls          = char.cls,
        talents      = talents,
        talent_t2    = char.talent_t2_key or "",
        subclass     = char.subclass or "",
        set_bonuses  = set_bonuses,
    )
```

- [ ] **Step 4: Spustit všechny testy a ověřit PASS**

```bash
cd backend && pytest tests/test_combatant_builder.py -v
```

Očekávaný výsledek: všech 5 testů PASS

- [ ] **Step 5: Spustit celou test suite**

```bash
cd backend && pytest tests/ -v
```

Očekávaný výsledek: žádné regresy — všechny testy PASS

- [ ] **Step 6: Commit**

```bash
git add backend/game/combatant_builder.py backend/tests/test_combatant_builder.py
git commit -m "fix: gear bonus_str/dex/int zahrnuty v combat stats

Dříve recalculate_with_gear přidávala gear stat bonusy jen dočasně
(add→recalculate_stats→subtract) a build_combatant_config četl pouze
base char.intelligence/strength/dexterity bez gear příspěvků.

Konsolidace _get_weapon_dmg + _get_armor_value do _get_gear_stats:
jeden průchod všemi 7 sloty, vrátí weapon_dmg + armor_value + eq_str/dex/int.
Inline stat mapping v build_combatant_config (odstraněno _primary_secondary).

Efekt: mág s legendárním gearem (+38 INT z itemů) jde z 98 na 168 DPS."
```

---

## Ověření balance po opravě

Pro manuální kontrolu spusť server a ověř combat dps v `/arena` nebo `/dungeon`:

| Setup | Před opravou | Po opravě |
|-------|-------------|-----------|
| Mage + Žezlo věčnosti (+20 INT) | `35×2.8 = 98` | `35×4.8 = 168` |
| Mage full Arkanní set (+65 INT) | ~98 | ~332 |
| Warrior + Excalibur (+10 STR) | `55×2.5 = 137` | `55×3.5 = 192` |
| Warrior full Titanovy Krve (+34 STR) | ~137 | ~354 |

Mág je po opravě na ~94 % warriora při full setu — vyváženě (kompenzuje vyšší luck + spelly).
