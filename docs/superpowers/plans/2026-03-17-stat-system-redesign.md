# Stat System Redesign — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Přepracovat stat systém postav na Shakes & Fidget model — každá třída má jeden primární damage atribut (STR/DEX/INT), odstranit atk/def_/spd/mp_max z DB, smazat COMBAT_STRATEGIES.

**Architecture:** Damage se počítá runtime v combat enginu z `weapon_dmg × (1 + primary/10) + sec_a/2 + sec_b/2`. HP = `END × class_mult × (level+1)`. Armor% = `min(cap, armor_value / enemy_level)`. Crit = `min(50%, LCK×5 / (enemy_level×2))`.

**Tech Stack:** Python/FastAPI, SQLAlchemy async, Alembic, pytest, Vanilla JS

**Spec:** `docs/superpowers/specs/2026-03-17-stat-system-redesign.md`

---

## Chunk 1: DB Migrace + Modely

### Task 1: Alembic migrace 0047

**Files:**
- Create: `backend/alembic/versions/0047_stat_system_redesign.py`

- [ ] **Krok 1: Vytvoř soubor migrace**

```python
"""0047_stat_system_redesign — odstraní staré combat staty z characters a items, přidá bonus_xp"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '0047'
down_revision = '0046'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    # -- characters: odstraň atk, def_, spd, mp_max
    char_cols = [c['name'] for c in insp.get_columns('characters')]
    for col in ('atk', 'def_', 'spd', 'mp_max'):
        if col in char_cols:
            op.drop_column('characters', col)

    # -- items: odstraň bonus_spd, bonus_mp; přidej bonus_xp
    item_cols = [c['name'] for c in insp.get_columns('items')]
    for col in ('bonus_spd', 'bonus_mp'):
        if col in item_cols:
            op.drop_column('items', col)
    if 'bonus_xp' not in item_cols:
        op.add_column('items', sa.Column('bonus_xp', sa.Integer(),
                                         nullable=False, server_default='0'))

def downgrade():
    # Opačné operace pro rollback
    op.add_column('characters', sa.Column('atk',    sa.Integer(), server_default='10'))
    op.add_column('characters', sa.Column('def_',   sa.Integer(), server_default='5'))
    op.add_column('characters', sa.Column('spd',    sa.Integer(), server_default='8'))
    op.add_column('characters', sa.Column('mp_max', sa.Integer(), server_default='50'))
    op.add_column('items', sa.Column('bonus_spd', sa.Integer(), server_default='0'))
    op.add_column('items', sa.Column('bonus_mp',  sa.Integer(), server_default='0'))
    op.drop_column('items', 'bonus_xp')
```

- [ ] **Krok 2: Spusť migraci a ověř**

```bash
cd backend && alembic upgrade head
```

Očekáváno: `Running upgrade 0046 -> 0047`

- [ ] **Krok 3: Commit**

```bash
git add backend/alembic/versions/0047_stat_system_redesign.py
git commit -m "feat: alembic 0047 — odstraň staré combat staty, přidej bonus_xp"
```

---

### Task 2: Item model — remove bonus_spd/mp, add bonus_xp

**Files:**
- Modify: `backend/models/item.py`

- [ ] **Krok 1: Napiš failing test**

```python
# backend/tests/test_item_model.py  (nový soubor)
from models.item import Item

def test_item_has_no_bonus_spd():
    assert not hasattr(Item, 'bonus_spd') or Item.bonus_spd is None

def test_item_has_no_bonus_mp():
    assert not hasattr(Item, 'bonus_mp') or Item.bonus_mp is None

def test_item_has_bonus_xp():
    item = Item.__new__(Item)
    item.bonus_xp = 0
    assert item.bonus_xp == 0
```

```bash
cd backend && pytest tests/test_item_model.py -v
```

Očekáváno: FAIL

- [ ] **Krok 2: Uprav Item model**

V `backend/models/item.py`:
- Smaž řádky s `bonus_spd` a `bonus_mp` (mapped_column definice)
- Přidej: `bonus_xp: Mapped[int] = mapped_column(Integer, default=0)`

- [ ] **Krok 3: Uprav `Item.to_dict()` v item.py**

V sekci `bonuses` dict:
- Odstraň klíče `"spd"` a `"mp"`
- Přidej: `"xp": self.bonus_xp`

- [ ] **Krok 4: Uprav `InventoryItem._upgraded_item_dict()`**

Odstraň klíče `"spd"` a `"mp"` z upgrade škálování.

- [ ] **Krok 5: Ověř testy**

```bash
cd backend && pytest tests/test_item_model.py -v
```

Očekáváno: PASS

- [ ] **Krok 6: Commit**

```bash
git add backend/models/item.py backend/tests/test_item_model.py
git commit -m "feat: item model — odstraň bonus_spd/mp, přidej bonus_xp"
```

---

### Task 3: Character model — recalculate_stats rewrite

**Files:**
- Modify: `backend/models/character.py`

- [ ] **Krok 1: Napiš failing testy**

```python
# backend/tests/test_character_stats.py  (nový soubor)
from models.character import Character, CLASS_BASE_STATS, CharacterClass

def _make_char(cls, end=10, level=1, **kwargs):
    c = Character.__new__(Character)
    c.cls = cls
    c.level = level
    c.strength     = kwargs.get('strength', 10)
    c.dexterity    = kwargs.get('dexterity', 10)
    c.intelligence = kwargs.get('intelligence', 10)
    c.endurance    = end
    c.luck         = kwargs.get('luck', 5)
    c.prestige_level = 0
    c.subclass = ""
    c.talents_json = "[]"   # správný atribut — get_talents() čte z talents_json
    return c

def test_warrior_hp_formula():
    c = _make_char("warrior", end=15, level=10)
    c.recalculate_stats()
    assert c.hp_max == 15 * 5 * (10 + 1)  # 825

def test_mage_hp_formula():
    c = _make_char("mage", end=8, level=10)
    c.recalculate_stats()
    assert c.hp_max == 8 * 2 * (10 + 1)  # 176

def test_ranger_hp_formula():
    c = _make_char("ranger", end=12, level=10)
    c.recalculate_stats()
    assert c.hp_max == 12 * 4 * (10 + 1)  # 528

def test_hp_floor():
    c = _make_char("mage", end=0, level=1)
    c.recalculate_stats()
    assert c.hp_max >= 10

def test_no_atk_attribute():
    c = _make_char("warrior", end=10, level=1)
    c.recalculate_stats()
    assert not hasattr(c, 'atk') or c.atk is None

def test_no_mp_max_attribute():
    c = _make_char("mage", end=10, level=1)
    c.recalculate_stats()
    assert not hasattr(c, 'mp_max') or c.mp_max is None
```

```bash
cd backend && pytest tests/test_character_stats.py -v
```

Očekáváno: FAIL

- [ ] **Krok 2: Uprav `CLASS_BASE_STATS` v character.py**

Odstraň z každé třídy klíče: `"atk_base"`, `"def_base"`, `"spd_base"`, `"mp_base"`, `"hp_base"`.

Přidej HP multiplikátor:
```python
CLASS_HP_MULT = {
    CharacterClass.WARRIOR: 5,
    CharacterClass.MAGE:    2,
    CharacterClass.RANGER:  4,
}
```

- [ ] **Krok 3: Přepiš `recalculate_stats()`**

```python
def recalculate_stats(self):
    """Přepočítá hp_max z primary stats + level."""
    bt  = self.buff_totals()
    lvl = self.level
    cls = CharacterClass(self.cls)

    eff_end = self.endurance + bt["endurance"]

    # HP: END × class_mult × (level + 1), min 10
    hp_mult = CLASS_HP_MULT[cls]
    self.hp_max = max(10, eff_end * hp_mult * (lvl + 1))

    # Talent fortitude: +15% HP
    _talents = self.get_talents()
    if "fortitude" in _talents:
        self.hp_max = int(self.hp_max * 1.15)

    # Bonus HP z itemů (bonus_hp ze všech vybavených předmětů)
    self.hp_max += self._equipped_hp_bonus()

    # Prestige: pouze HP bonus
    _pl = self.prestige_level or 0
    if _pl > 0:
        from models.prestige import prestige_bonus_mult
        _pmult = prestige_bonus_mult(_pl)
        self.hp_max = max(10, int(self.hp_max * _pmult["hp"]))

    # Subclass hp_mult
    if self.subclass:
        from models.subclass import SUBCLASS_DEFINITIONS
        _mults = SUBCLASS_DEFINITIONS.get(self.subclass, {}).get("stat_mults", {})
        if "hp_mult" in _mults:
            self.hp_max = max(10, int(self.hp_max * _mults["hp_mult"]))
```

- [ ] **Krok 4: Odstraň properties hp_base, mp_base, atk_base, def_base, spd_base**

Smaž tyto `@property` metody z Character modelu (řádky ~278–295).

- [ ] **Krok 5: Přidej helper `_equipped_hp_bonus()`**

```python
def _equipped_hp_bonus(self) -> int:
    """Součet bonus_hp ze všech vybavených předmětů (bez DB — používá cached data)."""
    # bonus_hp se aplikuje v recalculate_with_gear; zde jen fallback
    return 0
```

Poznámka: Plný bonus_hp z itemů se aplikuje v `inventory.py::recalculate_with_gear()` — tam se volá `recalculate_stats()` a pak přičítá item bonusy.

- [ ] **Krok 6: Uprav `to_dict()` v character.py**

- Odstraň import `_dodge_chance` (dodge odstraněn); zachovej `_crit_chance` nebo nahraď importem `calc_crit_chance` z `game.combat_stats` — oba fungují, ale `calc_crit_chance` vyžaduje `enemy_level` (použij `self.level` jako odhad)
- Odstraň `avg_enemy_spd` a dodge výpočet
- V `"combat"` dict: odstraň `"mp_max"`, `"atk"`, `"def"`, `"spd"` a jejich soft-cap varianty
- Přidej `"hp_max": self.hp_max`
- Zachovej zobrazení crit šance: `"crit_pct": round(_crit_chance(eff_lck) * 100, 1)` nebo `round(calc_crit_chance(eff_lck, self.level) * 100, 1)` — obojí je přijatelné pro UI

**Poznámka k `bonus_hp` z itemů:** `_equipped_hp_bonus()` vrací 0 protože `bonus_hp` se přičítá v `inventory.py::recalculate_with_gear()` PO volání `recalculate_stats()`. Toto chování se nemění — plan Task 11 zachovává tuto logiku.

- [ ] **Krok 7: Ověř testy**

```bash
cd backend && pytest tests/test_character_stats.py -v
```

Očekáváno: PASS

- [ ] **Krok 8: Commit**

```bash
git add backend/models/character.py backend/tests/test_character_stats.py
git commit -m "feat: character model — nová HP formule, odstraň atk/def_/spd/mp_max"
```

---

## Chunk 2: Combat Engine přepis

### Task 4: Nový CombatantConfig + helper get_combat_stats()

**Files:**
- Modify: `backend/game/combat_engine.py`
- Create: `backend/game/combat_stats.py`

- [ ] **Krok 1: Napiš failing test pro get_combat_stats**

```python
# backend/tests/test_combat_stats_helper.py
import pytest
from game.combat_stats import calc_damage_components, CLASS_WEAPON_BASE, CLASS_ARMOR_CAPS

def test_warrior_damage_components():
    dmg, sec_a, sec_b = calc_damage_components("warrior", str_=30, dex=10, int_=5, weapon_dmg=20)
    # base = 20*(1+30/10) + 10/2 + 5/2 = 80 + 5 + 2 = 87
    assert dmg == pytest.approx(87, abs=1)

def test_mage_damage_components():
    dmg, sec_a, sec_b = calc_damage_components("mage", str_=5, dex=8, int_=30, weapon_dmg=20)
    # base = 20*(1+30/10) + 5/2 + 8/2 = 80 + 2 + 4 = 86
    assert dmg == pytest.approx(86, abs=1)

def test_ranger_damage_components():
    dmg, sec_a, sec_b = calc_damage_components("ranger", str_=9, dex=30, int_=8, weapon_dmg=20)
    # base = 20*(1+30/10) + 9/2 + 8/2 = 80 + 4 + 4 = 88
    assert dmg == pytest.approx(88, abs=1)

def test_warrior_base_weapon_if_unarmed():
    base = CLASS_WEAPON_BASE["warrior"]
    assert base == 8

def test_armor_cap_warrior():
    assert CLASS_ARMOR_CAPS["warrior"] == 0.45

def test_armor_cap_mage():
    assert CLASS_ARMOR_CAPS["mage"] == 0.15

def test_armor_pct_divides_by_enemy_level():
    from game.combat_stats import calc_armor_pct
    pct = calc_armor_pct("warrior", armor_value=90, enemy_level=10)
    assert pct == pytest.approx(0.09)

def test_armor_pct_capped():
    pct = calc_armor_pct("warrior", armor_value=9000, enemy_level=1)
    assert pct == pytest.approx(0.45)

def test_armor_pct_no_division_by_zero():
    pct = calc_armor_pct("mage", armor_value=50, enemy_level=0)
    assert pct <= 0.15

def test_crit_chance_new():
    from game.combat_stats import calc_crit_chance
    # LCK=10, enemy_level=10 → 10*5/(10*2) = 0.25
    assert calc_crit_chance(luck=10, enemy_level=10) == pytest.approx(0.25)

def test_crit_chance_capped():
    from game.combat_stats import calc_crit_chance
    assert calc_crit_chance(luck=1000, enemy_level=1) == pytest.approx(0.50)

def test_hp_for_class():
    from game.combat_stats import calc_hp
    assert calc_hp("warrior", endurance=15, level=10) == 825
    assert calc_hp("mage",    endurance=8,  level=10) == 176
    assert calc_hp("ranger",  endurance=12, level=10) == 528
```

```bash
cd backend && pytest tests/test_combat_stats_helper.py -v
```

Očekáváno: FAIL (modul neexistuje)

- [ ] **Krok 2: Vytvoř `backend/game/combat_stats.py`**

```python
"""
game/combat_stats.py — Pomocné funkce pro výpočet combat statistik.

Odděleno od combat_engine.py aby bylo testovatelné a importovatelné
z routerů bez tažení celého enginu.
"""

# Třídně-specifické konstanty
CLASS_WEAPON_BASE: dict[str, int] = {
    "warrior": 8,
    "ranger":  6,
    "mage":    4,
}

CLASS_ARMOR_CAPS: dict[str, float] = {
    "warrior": 0.45,
    "ranger":  0.25,
    "mage":    0.15,
}

CLASS_HP_MULT: dict[str, int] = {
    "warrior": 5,
    "ranger":  4,
    "mage":    2,
}


def soft_cap_stat(value: int) -> float:
    """Aplikuje soft cap na primární stat před damage výpočtem.
    0-50: 100% | 51-150: 70% | 151+: 30%
    """
    if value <= 50:
        return float(value)
    elif value <= 150:
        return 50.0 + (value - 50) * 0.70
    else:
        return 50.0 + 70.0 + (value - 150) * 0.30


def calc_damage_components(
    cls: str,
    str_: int, dex: int, int_: int,
    weapon_dmg: int,
) -> tuple[float, float, float]:
    """Vypočítá (total_base_damage, sec_a_contrib, sec_b_contrib) pro třídu.

    Warrior:  weapon × (1 + STR/10) + DEX/2 + INT/2
    Ranger:   weapon × (1 + DEX/10) + STR/2 + INT/2
    Mage:     weapon × (1 + INT/10) + STR/2 + DEX/2
    """
    if cls == "warrior":
        primary = soft_cap_stat(str_)
        sec_a   = soft_cap_stat(dex) / 2
        sec_b   = soft_cap_stat(int_) / 2
    elif cls == "ranger":
        primary = soft_cap_stat(dex)
        sec_a   = soft_cap_stat(str_) / 2
        sec_b   = soft_cap_stat(int_) / 2
    elif cls == "mage":
        primary = soft_cap_stat(int_)
        sec_a   = soft_cap_stat(str_) / 2
        sec_b   = soft_cap_stat(dex) / 2
    else:
        # AI/boss — používá weapon_dmg jako flat damage, žádný primary stat bonus
        primary = 0.0
        sec_a   = 0.0
        sec_b   = 0.0

    base = weapon_dmg * (1 + primary / 10) + sec_a + sec_b
    return base, sec_a, sec_b


def calc_armor_pct(cls: str, armor_value: int, enemy_level: int) -> float:
    """Vrátí damage reduction % pro dané brnění a level nepřítele."""
    eff_level = max(1, enemy_level)
    cap = CLASS_ARMOR_CAPS.get(cls, 0.25)
    return min(cap, armor_value / eff_level)


def calc_crit_chance(luck: int, enemy_level: int) -> float:
    """Šance na krit: LCK×5 / (enemy_level×2), max 50%."""
    eff_level = max(1, enemy_level)
    return min(0.50, luck * 5 / (eff_level * 2))


def calc_hp(cls: str, endurance: int, level: int) -> int:
    """HP: END × class_mult × (level + 1), min 10."""
    mult = CLASS_HP_MULT.get(cls, 4)
    return max(10, endurance * mult * (level + 1))
```

- [ ] **Krok 3: Spusť testy**

```bash
cd backend && pytest tests/test_combat_stats_helper.py -v
```

Očekáváno: PASS

- [ ] **Krok 4: Commit**

```bash
git add backend/game/combat_stats.py backend/tests/test_combat_stats_helper.py
git commit -m "feat: přidej game/combat_stats.py — nové damage/armor/crit formule"
```

---

### Task 5: Přepiš CombatantConfig + _FighterState

**Files:**
- Modify: `backend/game/combat_engine.py`

- [ ] **Krok 1: Napiš failing test pro nový CombatantConfig**

```python
# backend/tests/test_combat_new.py
import pytest
from game.combat_engine import CombatantConfig, simulate_unified_combat

def _warrior(hp=825, weapon_dmg=20, armor_value=90,
             str_=30, dex=10, int_=5, luck=5, level=10):
    return CombatantConfig(
        name="Warrior", hp=hp,
        weapon_dmg=weapon_dmg, armor_value=armor_value,
        primary_stat=str_, secondary_a=dex, secondary_b=int_,
        luck=luck, level=level, cls="warrior",
    )

def _mage(hp=176, weapon_dmg=20, armor_value=20,
          str_=5, dex=8, int_=30, luck=8, level=10):
    return CombatantConfig(
        name="Mage", hp=hp,
        weapon_dmg=weapon_dmg, armor_value=armor_value,
        primary_stat=int_, secondary_a=str_, secondary_b=dex,
        luck=luck, level=level, cls="mage",
    )

def test_combatant_config_no_atk_field():
    w = _warrior()
    assert not hasattr(w, 'atk')

def test_combatant_config_no_strategy_field():
    w = _warrior()
    assert not hasattr(w, 'strategy')

def test_combat_runs_warrior_vs_mage():
    result = simulate_unified_combat(_warrior(), _mage())
    assert result.winner in ("attacker", "defender")
    assert result.rounds >= 1

def test_ranger_always_first_strike():
    """Ranger útočí první v kole 1 bez ohledu na soupeře."""
    from game.combat_engine import _FighterState
    ranger_cfg = CombatantConfig(
        name="Ranger", hp=528, weapon_dmg=20, armor_value=50,
        primary_stat=30, secondary_a=9, secondary_b=8,
        luck=13, level=10, cls="ranger",
    )
    warrior_cfg = CombatantConfig(
        name="Warrior", hp=825, weapon_dmg=20, armor_value=90,
        primary_stat=30, secondary_a=10, secondary_b=5,
        luck=5, level=10, cls="warrior",
    )
    result = simulate_unified_combat(ranger_cfg, warrior_cfg)
    # V prvním eventu útočníkem musí být Ranger když je attacker
    first_attack = next(e for e in result.events if e.type in ("attack", "crit"))
    assert first_attack.actor == "Ranger"
```

```bash
cd backend && pytest tests/test_combat_new.py -v
```

Očekáváno: FAIL

- [ ] **Krok 2: Uprav `CombatantConfig` dataclass**

Nahraď stávající fieldy:

```python
@dataclass
class CombatantConfig:
    """Vstupní konfigurace bojovníka pro combat engine."""
    name:       str
    hp:         int
    weapon_dmg: int          # bonus_atk vybavené zbraně (nebo class base)
    armor_value: int         # součet bonus_def ze všech equipů
    primary_stat: int        # STR pro warrior / DEX pro ranger / INT pro mage
    secondary_a: int         # DEX pro warrior / STR pro ranger / STR pro mage
    secondary_b: int         # INT pro warrior / INT pro ranger / DEX pro mage
    luck:       int  = 5
    level:      int  = 1
    cls:        str  = ""
    # Boss-specific
    is_boss:    bool = False
    phases:     list = field(default_factory=list)
    special_abilities: list = field(default_factory=list)
    hp_max_override: int = 0
    talents:    list = field(default_factory=list)
    subclass:   str  = ""
    modifier_statuses: list = field(default_factory=list)
    talent_t2:  str  = ""
    set_bonuses: dict = field(default_factory=dict)
    experiment_overrides: dict = field(default_factory=dict)
```

- [ ] **Krok 3: Uprav `ActiveStatus` dataclass**

Odstraň `spd_debuff_pct` field (slow status odstraněn).

- [ ] **Krok 4: Chirurgicky uprav `_FighterState.__init__()` — NENAHRADZUJ CELÝ INIT**

Existující `__init__` obsahuje ~100 řádků kritické logiky (talenty, set bonusy, A/B override, rage, spell cycle). Místo přepisu proveď tyto cílené změny:

**4a) Na začátku init — nahraď blok soft_cap + COMBAT_STRATEGIES:**

Smaž tyto řádky (řádky ~394–405):
```python
_atk_capped  = soft_cap_stat(cfg.atk)
_def_capped  = soft_cap_stat(cfg.def_)
_spd_capped  = soft_cap_stat(cfg.spd)
self.luck    = soft_cap_stat(cfg.luck)
_strat       = COMBAT_STRATEGIES.get(cfg.strategy or "balanced", ...)
self.atk     = max(1, int(_atk_capped * _strat["atk_mult"]))
self.def_    = max(0, int(_def_capped * _strat["def_mult"]))
self.spd     = max(1, int(_spd_capped * _strat["spd_mult"]))
_mp_val      = max(0, int(cfg.mp   * _strat["mp_mult"]))
self.mp      = _mp_val
self.mp_max  = _mp_val
```

Nahraď tímto blokem:
```python
from game.combat_stats import calc_damage_components
self.luck    = int(soft_cap_stat(cfg.luck))
self.level   = cfg.level
# Vypočítej base damage z nové formule
_base_dmg, _, _ = calc_damage_components(
    cfg.cls or "",
    str_=cfg.secondary_a if cfg.cls in ("ranger", "mage") else cfg.primary_stat,
    dex=(cfg.primary_stat if cfg.cls == "ranger"
         else cfg.secondary_b if cfg.cls == "mage"
         else cfg.secondary_a),
    int_=(cfg.secondary_b if cfg.cls == "warrior"
          else cfg.secondary_b if cfg.cls == "ranger"
          else cfg.primary_stat),
    weapon_dmg=cfg.weapon_dmg,
)
self.base_dmg    = _base_dmg
self.armor_value = cfg.armor_value
# Subclass dmg_mult a armor_mult
self.dmg_mult   = 1.0
self.armor_mult = 1.0
if cfg.subclass:
    from models.subclass import SUBCLASS_DEFINITIONS
    _mults = SUBCLASS_DEFINITIONS.get(cfg.subclass, {}).get("stat_mults", {})
    self.dmg_mult   = _mults.get("dmg_mult",   1.0)
    self.armor_mult = _mults.get("armor_mult",  1.0)
# Ranger: first strike flag (útočí první v kole 1)
# Nastavujeme has_first_strike a necháme existující first_strike logiku být
self.has_class_first_strike = (cfg.cls == "ranger")
```

**4b) Talent `mana_surge` — nahraď v bloku talentů:**

Najdi a smaž řádky:
```python
if "mana_surge" in _talents:
    self.mp     = int(self.mp     * 1.25)
    self.mp_max = int(self.mp_max * 1.25)
```

Nahraď:
```python
if "mana_surge" in _talents:
    self.dmg_mult *= 1.15   # nový efekt: +15% damage
```

**4c) Talent `evasion` — nahraď `dodge_bonus_pct`:**

Najdi:
```python
self.dodge_bonus_pct = 0.10 if "evasion" in _talents else 0.0
```

Nahraď:
```python
self.crit_bonus_pct = 0.10 if "evasion" in _talents else 0.0
```

**4d) Odstraň start status ze strategie (defensive shield):**

Najdi a smaž:
```python
if _start_status := _strat.get("start_status"):
    self.add_status(_start_status, hp_max=self.hp_max, atk=self.atk)
```

**4e) Uprav start statusy z dungeon modifikátoru — odstraň `atk=self.atk`:**

```python
# Před:
self.add_status(_mod_status, hp_max=self.hp_max, atk=self.atk)
# Po:
self.add_status(_mod_status, hp_max=self.hp_max)
```

**4f) Smaž `dodge_chance_cap` z A/B overrides:**

```python
# Smaž tento řádek:
self.dodge_chance_cap = float(_ov.get("dodge_chance_cap", MAX_DODGE_CHANCE))
```

- [ ] **Krok 5: Přidej `effective_dmg()` helper na `_FighterState` a odstraň `effective_atk()`**

```python
def effective_dmg(self) -> float:
    """Celkový base damage po aplikaci dmg_mult."""
    return self.base_dmg * self.dmg_mult
```

Smaž nebo zakomentuj `effective_atk()` a `effective_spd()` metody.
Nahraď všechna volání `attacker.effective_atk()` za `attacker.effective_dmg()` v celém `combat_engine.py` (grep: `effective_atk`).

- [ ] **Krok 5b: Uprav `_check_boss_phases()` — boss stat multipliers**

V `_check_boss_phases()` fáze aplikují `stat_multipliers` jako `boss.atk = int(boss.atk * mult)`.
Po přepsání `_FighterState` neexistuje `boss.atk`. Uprav mapování:

```python
# V _check_boss_phases() nahraď:
# Před:
if "atk" in phase_mults:
    boss.atk = max(1, int(boss.atk * phase_mults["atk"]))
if "def" in phase_mults:
    boss.def_ = max(0, int(boss.def_ * phase_mults["def"]))
if "spd" in phase_mults:
    boss.spd = max(1, int(boss.spd * phase_mults["spd"]))

# Po:
if "atk" in phase_mults:
    boss.dmg_mult *= phase_mults["atk"]
if "def" in phase_mults:
    boss.armor_mult *= phase_mults["def"]
# spd mult se ignoruje (SPD odstraněn)
```

Zkontroluj `backend/game/seed.py` nebo boss definice — klíče `stat_multipliers` v boss fázích musí být `"atk"` a `"def"` (nebo aktualizuj je na `"dmg"` a `"armor"` konzistentně).

- [ ] **Krok 5c: Přepiš `_calc_damage()` v combat enginu**

```python
def _calc_damage(
    attacker: "_FighterState",
    defender: "_FighterState",
    is_crit: bool = False,
    dmg_override: float = 0.0,   # pro schopnosti s vlastním dmg (ability)
    ignore_armor: bool = False,
) -> int:
    from game.combat_stats import calc_armor_pct
    base = dmg_override if dmg_override > 0 else attacker.effective_dmg()
    if not ignore_armor:
        armor_pct = calc_armor_pct(
            defender.cfg.cls or "",
            int(defender.armor_value * defender.armor_mult),
            attacker.level,
        )
        base *= (1.0 - armor_pct)
    if is_crit:
        base *= 2.0
    return max(1, int(base))
```

- [ ] **Krok 6: Ověř testy**

```bash
cd backend && pytest tests/test_combat_new.py -v
```

Očekáváno: PASS

- [ ] **Krok 7: Commit**

```bash
git add backend/game/combat_engine.py backend/tests/test_combat_new.py
git commit -m "feat: combat engine — nový CombatantConfig, _FighterState, _calc_damage"
```

---

### Task 6: Odstraň COMBAT_STRATEGIES, dodge, MP, slow

**Files:**
- Modify: `backend/game/combat_engine.py`

- [ ] **Krok 1: Odstraň `COMBAT_STRATEGIES` dict**

Smaž celou definici `COMBAT_STRATEGIES` (řádky ~93–115).

- [ ] **Krok 2: Odstraň `_dodge_chance()` funkci**

Smaž funkci `_dodge_chance()`. Odstraň `EVENT_DODGE` z event type konstant.

- [ ] **Krok 3: Odstraň `slow` status handling**

V `_apply_status_tick()` a `_process_statuses()` odstraň větve pro `"slow"` status.

- [ ] **Krok 4: Odstraň MP tracking v `_execute_attack()`**

Odstraň veškerou logiku kontroly `mp_cost_pct` a odečítání `self.mp`. Schopnosti se nyní spouštějí každé N kol bez MP podmínky.

- [ ] **Krok 5: Uprav crit šanci aby používala novou formuli**

```python
# V _execute_attack() nahraď starý _crit_chance() volání:
from game.combat_stats import calc_crit_chance
_is_crit = random.random() < calc_crit_chance(attacker.luck, defender.level)
```

Starý `_crit_chance(luck)` lze smazat nebo zachovat jako alias pro backward compat v testech.

- [ ] **Krok 6: Oprav `test_combat.py` — uprav existující testy**

Nejprve oprav import v hlavičce souboru — odstraň `_dodge_chance` z importu (file se jinak odmítne načíst):
```python
# Před:
from game.combat_engine import (
    CombatantConfig, CombatResult, simulate_unified_combat,
    calculate_win_chance, _crit_chance, _dodge_chance, _calc_damage,
)
# Po:
from game.combat_engine import (
    CombatantConfig, CombatResult, simulate_unified_combat,
    calculate_win_chance, _crit_chance, _calc_damage,
)
```

Přepiš helper funkce v test_combat.py:
```python
def _player(hp=825, weapon_dmg=20, armor_value=50, luck=5, level=5):
    return CombatantConfig(
        name="Hrdina", hp=hp, weapon_dmg=weapon_dmg,
        armor_value=armor_value, primary_stat=20,
        secondary_a=10, secondary_b=5,
        luck=luck, level=level, cls="warrior",
    )

def _enemy(hp=80, weapon_dmg=12, armor_value=10, luck=3, level=3):
    return CombatantConfig(
        name="Skřet", hp=hp, weapon_dmg=weapon_dmg,
        armor_value=armor_value, primary_stat=10,
        secondary_a=5, secondary_b=3,
        luck=luck, level=level, cls="",
    )
```

Odstraň testy pro `_dodge_chance` (funkce neexistuje) a uprav `_calc_damage` testy.

- [ ] **Krok 7: Smaž `test_strategies_talents.py`**

```bash
git rm backend/tests/test_strategies_talents.py
```

- [ ] **Krok 8: Spusť celou test suite**

```bash
cd backend && pytest tests/ -v --tb=short
```

Očekáváno: všechny testy PASS (nebo jen testy nesouvisející se strategiemi)

- [ ] **Krok 9: Commit**

```bash
git add -A
git commit -m "feat: odstraň COMBAT_STRATEGIES, dodge, slow, MP tracking z combat enginu"
```

---

## Chunk 3: Herní logika cleanup

### Task 7: Talenty + subclassy

**Files:**
- Modify: `backend/game/talents.py`
- Modify: `backend/models/subclass.py`

- [ ] **Krok 1: Uprav 4 talenty v `talents.py`**

```python
# mana_surge: mp_pct → dmg_bonus_pct
"mana_surge": {
    "class": "mage", "level_req": 20,
    "name": "Příval Energie", "emoji": "💧",
    "desc": "+15 % poškození.",
    "effect": {"dmg_bonus_pct": 0.15},
},

# evasion: dodge_bonus_pct → crit_bonus_pct
"evasion": {
    "class": "ranger", "level_req": 20,
    "name": "Úskok", "emoji": "💨",
    "desc": "+10 % šance na kritický zásah.",
    "effect": {"crit_bonus_pct": 0.10},
},

# mana_void (T2): drain_pct → apply_status weaken
{
    "key": "mana_void",
    "name": "Prázdnota Síly",
    "emoji": "🕳",
    "level_req": 25,
    "desc": "Každé 4. kolo: aplikuje Oslabení na nepřítele (2 kola).",
    "effect": {"apply_status": "weaken", "rounds": 2},
},

# shadow_step (T2): dodge_chance → guaranteed counter
{
    "key": "shadow_step",
    "name": "Stínový Krok",
    "emoji": "👤",
    "level_req": 25,
    "desc": "Každé 4. kolo: garantovaný protiútok za 1.5× poškození + krvácení.",
    "effect": {"counter_dmg_mult": 1.5, "apply_bleed": True},
},
```

- [ ] **Krok 2: Uprav subclassy v `subclass.py`**

```python
# elementalist: atk_mult → dmg_mult, smaž mp_mult
"elementalist": {
    ...
    "stat_mults": {
        "dmg_mult": 1.25,   # +25% damage (bylo atk_mult)
        "def_mult": 0.90,   # odstraní se v combat enginu (armor_mult)
    },
},

# necromancer: smaž mp_mult a spd_mult, přidej dmg_mult
"necromancer": {
    ...
    "stat_mults": {
        "dmg_mult": 0.85,   # -15% damage (zachovává původní ATK penalizaci)
    },
},

# shadowblade: smaž spd_mult, přidej crit_mult
"shadowblade": {
    ...
    "stat_mults": {
        "crit_mult": 1.35,  # +35% crit damage (náhrada za +35% SPD)
        "def_mult":  0.90,
        "atk_mult":  0.95,  # → dmg_mult: 0.95
    },
},
```

Přejmenuj všechny `atk_mult` → `dmg_mult` a `def_mult` → `armor_mult` ve všech subclassech.

- [ ] **Krok 3: Uprav `shadow_step` handling v combat enginu**

V části kde se zpracovávají T2 talent ability (každé 4. kolo), najdi `shadow_step` a nahraď dodge logiku:

```python
# shadow_step: garantovaný protiútok 1.5× + bleed
if t2 == "shadow_step":
    counter_dmg = _calc_damage(
        fighter, opponent,
        is_crit=False,
        dmg_override=fighter.base_dmg * 1.5,
    )
    # aplikuj bleed na nepřítele
    _apply_bleed(opponent, source=fighter)
```

- [ ] **Krok 4: Uprav `mark_for_death` v combat enginu**

Najdi handling `mark_for_death` a změň z `def_reduction_pct` na `armor_reduction_pct` aplikaci na `opponent.armor_value`.

- [ ] **Krok 5: Ověř testy**

```bash
cd backend && pytest tests/test_combat_new.py tests/test_character_stats.py -v
```

- [ ] **Krok 6: Commit**

```bash
git add backend/game/talents.py backend/models/subclass.py backend/game/combat_engine.py
git commit -m "feat: talenty — přepiš 4 talenty, subclassy — atk/def/spd/mp_mult → dmg/armor_mult"
```

---

### Task 8: Cleanup herních souborů

**Files:**
- Modify: `backend/game/class_mechanics.py`
- Modify: `backend/game/dungeon_modifiers.py`
- Modify: `backend/game/seed.py`
- Modify: `backend/models/runosmith.py`
- Modify: `backend/models/fateweaver.py`

- [ ] **Krok 1: `class_mechanics.py` — odstraň `check_mage_opening_crit`**

Najdi a smaž funkci `check_mage_opening_crit(mage_spd, enemy_spd)`.
Odstraň její volání z `combat_engine.py`.

- [ ] **Krok 2: `dungeon_modifiers.py` — odstraň SPD/MP modifikátory**

Odstraň z definic modifikátorů klíče `enemy_spd_mult` a `player_mp_mult`.
Odstraň jejich aplikaci v apply funkci (kde se modifikátory aplikují na CombatantConfig).

- [ ] **Krok 3: Uprav `test_dungeon_modifiers.py`**

Odstraň testy testující `enemy_spd_mult` a `player_mp_mult` — tyto testy selžou po odstranění.

- [ ] **Krok 4: `seed.py` — odstraň bonus_spd a bonus_mp parametry**

V řádcích ~210–233 odstraň `bonus_spd=...` a `bonus_mp=...` z volání item konstruktorů.

- [ ] **Krok 5: `runosmith.py` — nahraď bonus_spd a bonus_mp efekty**

Pro každý efekt s `bonus_spd`:
- Nahraď: `"bonus_spd": N` → `"bonus_dex": N`

Pro každý efekt s `bonus_mp`:
- Nahraď: `"bonus_mp": N` → `"bonus_luck": N`

- [ ] **Krok 6: `fateweaver.py` — odstraň mp efekt**

Smaž efekt `{"bonus_mp_flat": 40, "bonus_spell_pct": 10}` celý (oba klíče jsou nefunkční).

- [ ] **Krok 7: Spusť celou test suite**

```bash
cd backend && pytest tests/ -v --tb=short
```

Očekáváno: PASS (případně skip pro testy co závisí na DB)

- [ ] **Krok 8: Commit**

```bash
git add backend/game/class_mechanics.py backend/game/dungeon_modifiers.py \
        backend/game/seed.py backend/models/runosmith.py backend/models/fateweaver.py \
        backend/tests/test_dungeon_modifiers.py
git commit -m "feat: cleanup herní logiky — odstraň SPD/MP ze seed/modifiers/runosmith/fateweaver"
```

---

## Chunk 4: Routery + Inventory

### Task 9: Helper pro sestavení CombatantConfig v routerech

**Files:**
- Create: `backend/game/combatant_builder.py`

- [ ] **Krok 1: Napiš failing test**

```python
# backend/tests/test_combatant_builder.py
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
    char.talent_keys = "[]"
    char.talent_t2_key = ""
    char.subclass = ""
    char.prestige_level = 0

    db = AsyncMock()
    db.get = AsyncMock(return_value=None)

    cfg = await build_combatant_config(char, db)
    assert cfg.cls == "warrior"
    assert cfg.primary_stat == 30   # STR
    assert cfg.secondary_a == 10   # DEX
    assert cfg.secondary_b == 5    # INT
    assert cfg.weapon_dmg == 8     # unarmed warrior base
```

```bash
cd backend && pytest tests/test_combatant_builder.py -v
```

Očekáváno: FAIL

- [ ] **Krok 2: Vytvoř `backend/game/combatant_builder.py`**

```python
"""
game/combatant_builder.py — Sestaví CombatantConfig z Character modelu.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from game.combat_engine import CombatantConfig
from game.combat_stats import CLASS_WEAPON_BASE
from models.loot import get_set_bonuses  # existující helper


async def _get_weapon_dmg(char, db: AsyncSession) -> int:
    """Vrátí weapon_dmg z vybavené zbraně nebo class base."""
    if char.eq_weapon:
        from models.item import Item
        weapon = await db.get(Item, char.eq_weapon)
        if weapon:
            return weapon.bonus_atk or CLASS_WEAPON_BASE.get(char.cls, 5)
    return CLASS_WEAPON_BASE.get(char.cls, 5)


async def _get_armor_value(char, db: AsyncSession) -> int:
    """Součet bonus_def ze všech vybavených předmětů."""
    total = 0
    slot_ids = [
        char.eq_helmet, char.eq_armor, char.eq_gloves,
        char.eq_boots, char.eq_ring, char.eq_amulet,
    ]
    from models.item import Item
    for item_id in slot_ids:
        if item_id:
            item = await db.get(Item, item_id)
            if item:
                total += item.bonus_def or 0
    return total


def _primary_secondary(char) -> tuple[int, int, int]:
    """Vrátí (primary_stat, secondary_a, secondary_b) dle třídy."""
    cls = char.cls
    s, d, i = char.strength, char.dexterity, char.intelligence
    if cls == "warrior":
        return s, d, i
    elif cls == "ranger":
        return d, s, i
    elif cls == "mage":
        return i, s, d
    else:
        return 0, 0, 0


async def build_combatant_config(char, db: AsyncSession) -> CombatantConfig:
    """Sestaví CombatantConfig z Character ORM objektu."""
    weapon_dmg   = await _get_weapon_dmg(char, db)
    armor_value  = await _get_armor_value(char, db)
    primary, sec_a, sec_b = _primary_secondary(char)
    set_bonuses  = await get_set_bonuses(char, db)
    talents      = char.get_talents() if hasattr(char, 'get_talents') else []

    return CombatantConfig(
        name         = char.name,
        hp           = char.hp_max,
        weapon_dmg   = weapon_dmg,
        armor_value  = armor_value,
        primary_stat = primary,
        secondary_a  = sec_a,
        secondary_b  = sec_b,
        luck         = char.luck,
        level        = char.level,
        cls          = char.cls,
        talents      = talents,
        talent_t2    = char.talent_t2_key or "",
        subclass     = char.subclass or "",
        set_bonuses  = set_bonuses,
    )
```

- [ ] **Krok 3: Spusť testy**

```bash
cd backend && pytest tests/test_combatant_builder.py -v
```

Očekáváno: PASS

- [ ] **Krok 4: Commit**

```bash
git add backend/game/combatant_builder.py backend/tests/test_combatant_builder.py
git commit -m "feat: combatant_builder — helper pro sestavení CombatantConfig z Character"
```

---

### Task 10: Uprav combat routery — odstraň strategy

**Files:**
- Modify: `backend/routers/arena.py`
- Modify: `backend/routers/quest.py`
- Modify: `backend/routers/dungeon.py`
- Modify: `backend/routers/guild_war.py`

Pro každý soubor:

- [ ] **`arena.py`**:
  - Odstraň `strategy: str = "balanced"` z `ArenaAttackBody`
  - Nahraď ruční sestavení CombatantConfig za `await build_combatant_config(char, db)`
  - Importuj `from game.combatant_builder import build_combatant_config`

- [ ] **`quest.py`**:
  - Odstraň `strategy: str = "balanced"` z `StartQuestRequest`
  - Nahraď sestavení CombatantConfig za `await build_combatant_config(char, db)`

- [ ] **`dungeon.py`**:
  - Odstraň `strategy: str = "balanced"` z `EnterDungeonRequest`
  - Nahraď sestavení CombatantConfig za `await build_combatant_config(char, db)`

- [ ] **`guild_war.py`**:
  - Odstraň `strategy` z `WarAttackReq`
  - Nahraď sestavení CombatantConfig za `await build_combatant_config(char, db)`

- [ ] **Spusť testy arény**

```bash
cd backend && pytest tests/test_arena.py -v --tb=short
```

- [ ] **Commit**

```bash
git add backend/routers/arena.py backend/routers/quest.py \
        backend/routers/dungeon.py backend/routers/guild_war.py
git commit -m "feat: routery — odstraň strategy, použij build_combatant_config()"
```

---

### Task 11: Inventory router — odstraň MP, oprav scroll XP

**Files:**
- Modify: `backend/routers/inventory.py`

- [ ] **Krok 1: Odstraň `char.mp_max += item.bonus_mp` z `apply_item_bonus()`**

Najdi řádek ~97 kde se přičítá `bonus_mp` k `mp_max` — smaž.

- [ ] **Krok 2: Oprav scroll XP logiku**

Najdi řádek ~426: `gained_xp = item.bonus_mp or 0`
Nahraď: `gained_xp = item.bonus_xp or 0`

- [ ] **Krok 3: Spusť testy**

```bash
cd backend && pytest tests/ -v --tb=short -x
```

Očekáváno: celá suite PASS

- [ ] **Krok 4: Commit**

```bash
git add backend/routers/inventory.py
git commit -m "feat: inventory — odstraň mp_max bonus, oprav scroll XP na bonus_xp"
```

---

## Chunk 5: Frontend

### Task 12: Odstraň strategy picker z JS souborů

**Files:**
- Modify: `frontend/js/ui.js`
- Modify: `frontend/js/arena.js`
- Modify: `frontend/js/quest.js`
- Modify: `frontend/js/dungeons.js`
- Modify: `frontend/js/guild.js`
- Modify: `frontend/js/build.js`

- [ ] **`ui.js`**: Smaž `_STRAT_DEFS`, `getStrategy()`, `strategyPickerHtml()` a volání `localStorage.setItem('combat_strategy', ...)`.

- [ ] **`arena.js`**: Odstraň `strategy: getStrategy()` z body API volání.

- [ ] **`quest.js`**: Odstraň `strategy: getStrategy()` z body API volání.

- [ ] **`dungeons.js`**: Odstraň `strategy: getStrategy()` z body API volání.

- [ ] **`guild.js`**: Odstraň `strategy: localStorage.getItem('combatStrategy')` a strategy pole z API volání.

- [ ] **`build.js`**: Odstraň volání `getStrategy()` (řádek ~63).

- [ ] **Commit**

```bash
git add frontend/js/ui.js frontend/js/arena.js frontend/js/quest.js \
        frontend/js/dungeons.js frontend/js/guild.js frontend/js/build.js
git commit -m "feat: frontend — odstraň strategy picker ze všech JS souborů"
```

---

### Task 13: Uprav stat display v game.html + character JS

**Files:**
- Modify: `frontend/game.html`
- Modify: `frontend/js/character.js` (nebo soubor co renderuje stat panel)

- [ ] **`game.html`**:
  - Odstraň MP bar element (hledej `id="mp-bar"` nebo obdobné)
  - Odstraň ATK, DEF, SPD stat řádky z character sheetu
  - Zachovej: STR, DEX, INT, END, LCK, HP

- [ ] **Character JS soubor**:
  - V `updateUI(char)` nebo `renderCharacterStats()` odstraň reference na `char.combat.mp_max`, `char.combat.atk`, `char.combat.def`, `char.combat.spd`
  - Přidej zobrazení `HP: char.combat.hp_max`
  - Přidej tooltip u každého statu (např. title atribut):
    - STR: `"Síla — hlavní útočný stat Warriora"`
    - DEX: `"Obratnost — hlavní útočný stat Rangera, first strike"`
    - INT: `"Inteligence — hlavní útočný stat Mága"`
    - END: `"Výdrž — určuje maximální HP"`
    - LCK: `"Štěstí — šance na kritický zásah"`

- [ ] **Spusť backend smoke test**

```bash
cd backend && uvicorn main:app --port 8001 &
curl -s http://localhost:8001/health | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if d.get('status')=='ok' else 'FAIL')"
kill %1
```

- [ ] **Commit**

```bash
git add frontend/game.html frontend/js/character.js
git commit -m "feat: frontend — odstraň MP bar/ATK/DEF/SPD, přidej stat tooltips"
```

---

## Finální ověření

- [ ] **Spusť celou test suite**

```bash
cd backend && pytest tests/ -v
```

Očekáváno: PASS (žádné failures)

- [ ] **Ověř migraci na čisté DB**

```bash
cd backend && rm -f dungeon.db && alembic upgrade head && python -c "from database import Base; print('OK')"
```

- [ ] **Závěrečný commit**

```bash
git add -A
git commit -m "feat: stat system redesign kompletní — Shakes & Fidget model"
```
