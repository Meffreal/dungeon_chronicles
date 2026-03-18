# Class-Focused Items Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Přidat 30 nových class-focused itemů (10 warrior / 10 ranger / 10 mage), označit je přes nullable `hint_class` sloupec, zvýšit jejich šanci v shopu pro správnou třídu, a zobrazit badge v UI.

**Architecture:** Nový nullable sloupec `hint_class` na `items` tabulce. Seed data jsou v separátním `SEED_CLASS_ITEMS` listu aby stávající formát zůstal čistý. Shop `_npc_stock` dostane `char_cls` parametr a použije váhované samplingování (matching class 3×, cizí třída 0.5×, generic 1×).

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, Vanilla JS, pytest-asyncio

---

## Soubory

| Akce | Soubor | Co se mění |
|------|--------|-----------|
| Create | `backend/alembic/versions/0049_item_hint_class.py` | přidá `hint_class` sloupec |
| Modify | `backend/models/item.py` | přidá `hint_class` field + `to_dict()` |
| Modify | `backend/game/seed.py` | přidá `SEED_CLASS_ITEMS`, rozšíří `seed()` |
| Modify | `backend/routers/shop.py` | váhované sampling v `_npc_stock` |
| Modify | `frontend/js/inventory.js` | badge rendering pro `hint_class` |
| Modify | `frontend/js/shop.js` | badge rendering pro `hint_class` |
| Create | `backend/tests/test_hint_class.py` | testy |

---

## Task 1: DB migrace + Item model

**Files:**
- Create: `backend/alembic/versions/0049_item_hint_class.py`
- Modify: `backend/models/item.py`
- Test: `backend/tests/test_hint_class.py`

- [ ] **Step 1: Napiš failing test**

```python
# backend/tests/test_hint_class.py
import pytest
from models.item import Item

def test_item_hint_class_in_to_dict():
    item = Item(
        name="Test meč", item_type="weapon", rarity="common",
        description="Test", icon="⚔️",
        bonus_atk=5, sell_price=10, min_level=1,
        hint_class="warrior",
    )
    d = item.to_dict()
    assert d["hint_class"] == "warrior"

def test_item_hint_class_none_by_default():
    item = Item(
        name="Generický meč", item_type="weapon", rarity="common",
        description="Test", icon="⚔️",
        bonus_atk=5, sell_price=10, min_level=1,
    )
    d = item.to_dict()
    assert d["hint_class"] is None
```

- [ ] **Step 2: Spusť test, ověř že failuje**

```
pytest backend/tests/test_hint_class.py -v
```
Očekáváno: AttributeError — `hint_class` neexistuje

- [ ] **Step 3: Přidej `hint_class` do Item modelu (`backend/models/item.py`)**

Za `set_name` přidej:
```python
hint_class: Mapped[str | None] = mapped_column(String(16), nullable=True)
```

Do `to_dict()` přidej:
```python
"hint_class": self.hint_class,
```

- [ ] **Step 4: Vytvoř migraci `backend/alembic/versions/0049_item_hint_class.py`**

```python
"""items: přidej hint_class

Revision ID: 0049
Revises: 0048
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '0049'
down_revision = '0048'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    cols = [c['name'] for c in insp.get_columns('items')]
    if 'hint_class' not in cols:
        op.add_column(
            'items',
            sa.Column('hint_class', sa.String(16), nullable=True),
        )


def downgrade():
    op.drop_column('items', 'hint_class')
```

- [ ] **Step 5: Spusť test, ověř že prochází**

```
pytest backend/tests/test_hint_class.py -v
```
Očekáváno: 2 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/models/item.py backend/alembic/versions/0049_item_hint_class.py backend/tests/test_hint_class.py
git commit -m "feat: přidat hint_class pole na Item model"
```

---

## Task 2: Seed data — 30 nových itemů

**Files:**
- Modify: `backend/game/seed.py`
- Test: `backend/tests/test_hint_class.py` (rozšíř)

- [ ] **Step 1: Napiš failing test**

Přidej do `backend/tests/test_hint_class.py`:
```python
from game.seed import SEED_CLASS_ITEMS

def test_seed_class_items_count():
    assert len(SEED_CLASS_ITEMS) == 30

def test_seed_class_items_per_class():
    warriors = [i for i in SEED_CLASS_ITEMS if i[-1] == "warrior"]
    rangers  = [i for i in SEED_CLASS_ITEMS if i[-1] == "ranger"]
    mages    = [i for i in SEED_CLASS_ITEMS if i[-1] == "mage"]
    assert len(warriors) == 10
    assert len(rangers)  == 10
    assert len(mages)    == 10

def test_seed_class_items_hint_class_values():
    valid = {"warrior", "ranger", "mage"}
    for item in SEED_CLASS_ITEMS:
        assert item[-1] in valid, f"Neplatný hint_class: {item[-1]}"
```

- [ ] **Step 2: Spusť test, ověř že failuje**

```
pytest backend/tests/test_hint_class.py::test_seed_class_items_count -v
```
Očekáváno: ImportError nebo AssertionError

- [ ] **Step 3: Přidej `SEED_CLASS_ITEMS` do `backend/game/seed.py`**

Za stávající `SEED_SET_ITEMS` list přidej nový list. Formát:
`(name, type, rarity, desc, icon, atk, def_, spd, hp, xp, s_str, s_dex, s_int, s_end, s_luck, min_level, sell_price, hint_class)`

```python
SEED_CLASS_ITEMS = [
    # Formát: (name, type, rarity, desc, icon, atk, def_, spd, hp, xp, s_str, s_dex, s_int, s_end, s_luck, min_level, sell, hint_class)
    # POZNÁMKA: `spd` (pole 8) je v Item modelu ignorováno — vždy 0

    # ── WARRIOR ──────────────────────────────────────────────────────────────
    # Common
    ("Těžký sekáč",              "weapon",  "common",   "Masivní sekáč pro silné ruce.",              "🪓",  6,  0, 0,  0, 0,  2,0,0,0,0,  1,  10, "warrior"),
    ("Zbroj bojovníka",          "armor",   "common",   "Jednoduchá ale odolná zbroj.",               "🛡️",  0,  5, 0,  0, 0,  0,0,0,1,0,  1,  12, "warrior"),
    # Uncommon
    ("Válečnická sekera",        "weapon",  "uncommon", "Sekera tesaná pro boj z blízka.",            "🪓", 16,  0, 0,  0, 0,  5,0,0,1,0,  3,  38, "warrior"),
    ("Ocelová helma",            "helmet",  "uncommon", "Ochrana hlavy zkušeného bojovníka.",         "⛑️",  0,  9, 0,  8, 0,  0,0,0,2,0,  3,  35, "warrior"),
    ("Válečné rukavice",         "gloves",  "uncommon", "Těžké rukavice pro boj z blízka.",           "🥊",  0,  5, 0,  0, 0,  3,0,0,1,0,  3,  32, "warrior"),
    # Rare
    ("Ocelový bastard",          "weapon",  "rare",     "Dvouruční meč z nejtvrdší oceli.",           "⚔️", 28,  0, 0,  8, 0,  7,0,0,0,0,  6, 130, "warrior"),
    ("Plátová zbroj válečníka",  "armor",   "rare",     "Těžká plátová ochrana pro frontový boj.",    "🛡️",  0, 24, 0, 12, 0,  0,0,0,4,0,  6, 125, "warrior"),
    ("Bojové boty válečníka",    "boots",   "rare",     "Pevné boty pro frontový boj.",               "👢",  0,  7, 0,  8, 0,  3,0,0,1,0,  6, 115, "warrior"),
    # Epic
    ("Hněv titana",              "weapon",  "epic",     "Zbraň hodná pravého válečníka.",             "🪓", 50,  0, 0, 15, 0, 12,0,0,5,0, 12, 450, "warrior"),
    ("Prsten silákův",           "ring",    "epic",     "Magický prsten zesilující fyzickou sílu.",   "💍",  0,  6, 0, 12, 0,  8,0,0,5,0, 10, 420, "warrior"),

    # ── RANGER ───────────────────────────────────────────────────────────────
    # Common
    ("Průzkumnický luk",         "weapon",  "common",   "Lehký luk pro rychlé střelce.",              "🏹",  4,  0, 0,  0, 0,  0,2,0,0,1,  1,   9, "ranger"),
    ("Lehké boty lovce",         "boots",   "common",   "Boty pro pohyb v terénu.",                   "👟",  0,  3, 0,  0, 0,  0,2,0,0,0,  1,  10, "ranger"),
    # Uncommon
    ("Ostrostřelecký luk",       "weapon",  "uncommon", "Přesný luk z jasanového dřeva.",             "🏹", 13,  0, 0,  0, 0,  0,6,0,0,2,  3,  34, "ranger"),
    ("Kůže lovce",               "armor",   "uncommon", "Ohebná zbroj z dračí kůže.",                 "🥋",  0,  8, 0,  0, 0,  0,3,0,0,1,  3,  33, "ranger"),
    ("Rukavice střelce",         "gloves",  "uncommon", "Lehké rukavice pro přesnou střelbu.",        "🧤",  0,  4, 0,  0, 0,  0,4,0,0,1,  3,  30, "ranger"),
    # Rare
    ("Stříbrný luk",             "weapon",  "rare",     "Luk zdobený stříbrnými runy přesnosti.",     "🏹", 23,  0, 0,  6, 0,  0,9,0,0,4,  6, 118, "ranger"),
    ("Průzkumnická kukla",       "helmet",  "rare",     "Lehká kukla pro přesné střelce.",            "🪖",  0, 11, 0,  6, 0,  0,5,0,0,2,  6, 112, "ranger"),
    ("Přívěsek lovce",           "amulet",  "rare",     "Talisman ostrých smyslů.",                   "🌿",  0,  4, 0,  8, 0,  0,6,0,0,5,  7, 120, "ranger"),
    # Epic
    ("Stín a vítr",              "weapon",  "epic",     "Luk tak rychlý, že zní jako vítr.",          "🏹", 44,  0, 0, 10, 0,  0,14,0,0,6, 12, 430, "ranger"),
    ("Zbroj stínového lovce",    "armor",   "epic",     "Zbroj splývající se stínem.",                "🥷",  0, 21, 0, 15, 0,  0,10,0,0,4, 10, 410, "ranger"),

    # ── MAGE ─────────────────────────────────────────────────────────────────
    # Common
    ("Větvičková hůlka",         "weapon",  "common",   "Malá hůlka pro začínající mága.",            "🪄",  3,  0, 0,  0, 0,  0,0,3,0,0,  1,   8, "mage"),
    ("Mystické roucho",          "armor",   "common",   "Jednoduché roucho s magickými vzory.",       "👘",  0,  3, 0,  0, 0,  0,0,2,0,0,  1,   9, "mage"),
    # Uncommon
    ("Arkanická tyč",            "weapon",  "uncommon", "Tyč kanalizující arkanickou energii.",       "🔮", 10,  0, 0,  0, 0,  0,0,8,0,0,  3,  33, "mage"),
    ("Čepice zaříkávače",        "helmet",  "uncommon", "Čepice zvyšující soustředění mága.",         "🎓",  0,  6, 0,  0, 0,  0,0,5,0,0,  3,  31, "mage"),
    ("Prsten moudra",            "ring",    "uncommon", "Prsten zesilující arkanickou sílu.",         "💍",  0,  0, 0,  5, 0,  0,0,6,0,0,  3,  30, "mage"),
    # Rare
    ("Runová hůlka",             "weapon",  "rare",     "Hůlka vyřezaná z runového kamene.",          "🔮", 19,  0, 0, 12, 0,  0,0,14,0,0,  6, 122, "mage"),
    ("Arkanické roucho",         "armor",   "rare",     "Roucho tkané z magických vláken.",           "👘",  0, 13, 0, 15, 0,  0,0, 8,0,0,  6, 118, "mage"),
    ("Boty učence",              "boots",   "rare",     "Komfortní boty pro dlouhé studium kouzel.",  "👡",  0,  5, 0, 10, 0,  0,0, 6,0,0,  6, 110, "mage"),
    # Epic
    ("Arcimágova hůl",           "weapon",  "epic",     "Hůl napájená arkanickým krystalem.",         "🔮", 38,  0, 0, 20, 0,  0,0,16,0,0, 12, 440, "mage"),
    ("Amulet arkanisty",         "amulet",  "epic",     "Amulet posilující magické schopnosti.",      "📿",  0,  5, 0, 18, 0,  0,0,12,0,0, 10, 415, "mage"),
]
```

- [ ] **Step 4: Rozšíř `seed()` v `backend/game/seed.py` o zpracování `SEED_CLASS_ITEMS`**

Za blok zpracovávající `SEED_SET_ITEMS` přidej:

```python
        # ── Class-focused itemy ───────────────────────────────────────────────
        for row in SEED_CLASS_ITEMS:
            (name, itype, rarity, desc, icon,
             atk, def_, spd, hp, xp,
             s_str, s_dex, s_int, s_end, s_luck,
             min_lv, sell, hint_cls) = row

            if name in existing_names:
                from sqlalchemy import update as sql_update  # stejný pattern jako stávající bloky
                await db.execute(
                    sql_update(Item).where(Item.name == name).values(
                        bonus_atk=atk,  bonus_def=def_,
                        bonus_hp=hp,    bonus_xp=xp,
                        bonus_str=s_str, bonus_dex=s_dex, bonus_int=s_int,
                        bonus_end=s_end, bonus_luck=s_luck,
                        hint_class=hint_cls,
                    )
                )
                count += 1
                continue

            item = Item(
                name=name, item_type=itype, rarity=rarity,
                description=desc, icon=icon,
                bonus_atk=atk,  bonus_def=def_,
                bonus_hp=hp,    bonus_xp=xp,
                bonus_str=s_str, bonus_dex=s_dex, bonus_int=s_int,
                bonus_end=s_end, bonus_luck=s_luck,
                min_level=min_lv, sell_price=sell,
                hint_class=hint_cls,
            )
            db.add(item)
            count += 1
```

- [ ] **Step 5: Spusť testy, ověř že prochází**

```
pytest backend/tests/test_hint_class.py -v
```
Očekáváno: 5 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/game/seed.py backend/tests/test_hint_class.py
git commit -m "feat: přidat 30 class-focused itemů do seed dat"
```

---

## Task 3: Shop váhované samplingování

**Files:**
- Modify: `backend/routers/shop.py`
- Test: `backend/tests/test_hint_class.py` (rozšíř)

- [ ] **Step 1: Napiš failing test**

Přidej do `backend/tests/test_hint_class.py`:
```python
from routers.shop import _weighted_pool

def test_weighted_pool_favors_matching_class():
    """Matching class items se musí konzistentně dominovat poolu."""
    from unittest.mock import MagicMock
    import random

    def make_item(id_, hint):
        m = MagicMock()
        m.id = id_
        m.hint_class = hint
        return m

    items = (
        [make_item(i, "warrior") for i in range(10)] +
        [make_item(i + 10, "ranger") for i in range(10)] +
        [make_item(i + 20, None) for i in range(10)]
    )

    # Otestuj přes více seedů pro statistickou spolehlivost
    warrior_wins = 0
    for seed in range(20):
        rng = random.Random(seed)
        pool = _weighted_pool(items, k=10, char_cls="warrior", rng=rng)
        warrior_count = sum(1 for i in pool if i.hint_class == "warrior")
        ranger_count  = sum(1 for i in pool if i.hint_class == "ranger")
        if warrior_count > ranger_count * 2:
            warrior_wins += 1

    # Warrior musí dominovat v alespoň 80% seedů
    assert warrior_wins >= 16, f"Váhování nefunguje spolehlivě: warrior dominoval jen {warrior_wins}/20 seedů"

def test_weighted_pool_no_duplicates():
    """Pool nesmí obsahovat duplicitní itemy."""
    from unittest.mock import MagicMock
    import random

    def make_item(id_, hint):
        m = MagicMock()
        m.id = id_
        m.hint_class = hint
        return m

    items = [make_item(i, "warrior" if i < 5 else None) for i in range(15)]
    rng = random.Random(99)
    pool = _weighted_pool(items, k=8, char_cls="warrior", rng=rng)

    ids = [i.id for i in pool]
    assert len(ids) == len(set(ids)), "Pool obsahuje duplicitní itemy"
```

- [ ] **Step 2: Spusť test, ověř že failuje**

```
pytest backend/tests/test_hint_class.py::test_weighted_pool_favors_matching_class -v
```
Očekáváno: ImportError — `_weighted_pool` neexistuje

- [ ] **Step 3: Implementuj `_weighted_pool` a aktualizuj `_npc_stock` v `backend/routers/shop.py`**

Za funkci `_shop_price` přidej:

```python
def _weighted_pool(items: list, k: int, char_cls: str, rng: random.Random) -> list:
    """Vrátí k unikátních itemů s váhami podle hint_class.

    hint_class == char_cls → 3.0, hint_class == jiná třída → 0.5, None → 1.0
    Implementace: weighted sampling bez náhrady přes postupné odebrání.
    """
    available = list(items)
    weights = []
    for item in available:
        hint = getattr(item, 'hint_class', None)
        if hint == char_cls:
            weights.append(3.0)
        elif hint is None:
            weights.append(1.0)
        else:
            weights.append(0.5)

    selected: list = []
    for _ in range(min(k, len(available))):
        if not available:
            break
        chosen = rng.choices(available, weights=weights, k=1)[0]
        idx = available.index(chosen)
        selected.append(chosen)
        available.pop(idx)
        weights.pop(idx)

    return selected
```

Aktualizuj `_npc_stock` — nahraď řádek `pool = rng.sample(all_items, pool_size)`:

```python
    char_cls_res = None
    if char_id is not None:
        cls_res = await db.execute(
            select(Character.cls).where(Character.id == char_id)
        )
        row = cls_res.first()
        char_cls_res = row[0] if row else None

    pool_size = min(npc["stock_count"] * 2, len(all_items))
    if char_cls_res:
        pool = _weighted_pool(all_items, pool_size, char_cls_res, rng)
    else:
        pool = rng.sample(all_items, pool_size)
```

Přidej import `Character` na začátek souboru (pokud chybí):
```python
from models.character import Character
```

- [ ] **Step 4: Spusť testy**

```
pytest backend/tests/test_hint_class.py -v
```
Očekáváno: všechny PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/routers/shop.py backend/tests/test_hint_class.py
git commit -m "feat: váhované samplingování v shopu podle hint_class třídy hráče"
```

---

## Task 4: Frontend badge

**Files:**
- Modify: `frontend/js/shop.js`
- Modify: `frontend/js/inventory.js`

- [ ] **Step 1: Najdi kde se renderují itemy v shopu**

Přečti `frontend/js/shop.js` a najdi funkci která generuje HTML pro item kartu (hledej `hint_class`, `item.type`, `rarity`, nebo funkce jako `_renderItem`, `shopItemHtml`).

- [ ] **Step 2: Přidej badge helper funkci do `frontend/js/shop.js`**

Funkci přidej na **top-level scope** souboru (ne uvnitř jiné funkce) — musí být globálně dostupná pro `inventory.js` který se načítá po `shop.js`.

Těsně před/za existující helper funkce přidej:

```javascript
function _hintClassBadge(hintClass) {
    if (!hintClass) return '';
    const badges = { warrior: '⚔️', ranger: '🏹', mage: '🔮' };
    const label  = { warrior: 'Válečník', ranger: 'Lovec', mage: 'Mág' };
    const emoji = badges[hintClass] || '';
    const name  = label[hintClass]  || hintClass;
    return `<span class="hint-class-badge hint-class-${hintClass}" title="Doporučeno pro: ${name}">${emoji}</span>`;
}
```

- [ ] **Step 3: Vlož badge do shop item render funkce**

V místě kde se generuje HTML pro item v shopu (obvykle název nebo ikona itemu), přidej:
```javascript
${_hintClassBadge(item.hint_class)}
```

- [ ] **Step 4: Přidej CSS do `frontend/css/components.css`**

```css
.hint-class-badge {
    display: inline-block;
    font-size: 0.75em;
    margin-left: 4px;
    opacity: 0.85;
    vertical-align: middle;
}
```

- [ ] **Step 5: Stejný badge přidej do `frontend/js/inventory.js`**

Najdi item render funkci v inventory.js a přidej `_hintClassBadge` — buď sdílej funkci přes globální scope nebo zduplikuj (inventory.js se načítá za shop.js, takže funkce bude dostupná).

- [ ] **Step 6: Manuálně ověř v prohlížeči**

Spusť backend, otevři shop — warrior item by měl zobrazovat ⚔️ badge.

- [ ] **Step 7: Commit**

```bash
git add frontend/js/shop.js frontend/js/inventory.js frontend/css/components.css
git commit -m "feat: zobrazit hint_class badge na itemech v shopu a inventáři"
```

---

## Task 5: Finální integrace a push

- [ ] **Step 1: Spusť všechny testy**

```
pytest backend/tests/ -v
```
Očekáváno: všechny PASSED, žádné regresy

- [ ] **Step 2: Push**

```bash
git push
```

- [ ] **Step 3: Ověř deploy**

Zkontroluj deploy dashboard — migrace `0049` by měla proběhnout automaticky při startu.
