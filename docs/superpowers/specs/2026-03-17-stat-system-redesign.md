# Spec: Přepracování stat systému postav

**Datum:** 2026-03-17
**Status:** Schváleno uživatelem
**Inspirace:** Shakes & Fidget — jednoduchý, čitelný RPG systém

---

## Problém

Aktuální systém má 5 primárních statů + 5 odvozených combat statů (`atk`, `def_`, `spd`, `hp_max`, `mp_max`). Žádný z nich nemá popis. Mage čerpá damage z `atk`, který vychází z STR/DEX — inteligence do damage vůbec nevstupuje. Systém je neintuitní a těžko balancovatelný.

---

## Cíl

Každá třída má jeden jasný primární damage atribut. Formule jsou jednoduché a čitelné. Zbytečné odvozené staty zmizí z DB i UI.

---

## Nový systém

### Primární staty (zachovány — všech 5)

> Poznámka: Ranger v kódu = `CharacterClass.RANGER = "ranger"` — název třídy se nemění.

| Stat | Warrior | Ranger | Mage |
|------|---------|--------|------|
| Síla (STR) | ⭐ hlavní damage | sekundární obrana | sekundární obrana |
| Obratnost (DEX) | sekundární obrana | ⭐ hlavní damage | sekundární obrana |
| Inteligence (INT) | sekundární obrana | sekundární obrana | ⭐ hlavní damage |
| Výdrž (END) | HP | HP | HP |
| Štěstí (LCK) | crit šance | crit šance | crit šance |

### Damage formule

```
Warrior:  weapon_dmg × (1 + STR/10) + DEX/2 + INT/2
Ranger:   weapon_dmg × (1 + DEX/10) + STR/2 + INT/2
Mage:     weapon_dmg × (1 + INT/10) + STR/2 + DEX/2
```

- `weapon_dmg` = `bonus_atk` vybavené zbraně (stávající pole v Item modelu)
- Pokud není zbraň vybavena: `weapon_dmg` = class base (Warrior 8, Ranger 6, Mage 4)
- Sekundární staty přidávají flat bonus k celkovému damage

### HP

```
Warrior:  END × 5 × (level + 1)
Ranger:   END × 4 × (level + 1)
Mage:     END × 2 × (level + 1)
```

Minimální HP floor: 10 (ochrana před edge cases při velmi nízkém END).

### Armor (damage reduction %)

```
effective_level = max(1, enemy_level)   ← ochrana před dělením nulou
Armor% = min(class_armor_cap, armor_value / effective_level)
```

| Třída | Max Armor% |
|-------|-----------|
| Warrior | 45% |
| Ranger | 25% |
| Mage | 15% |

- `armor_value` = součet `bonus_def` ze všech vybavených předmětů (stávající pole v Item modelu)
- Příklad: Warrior s armor_value=90 vs enemy_level=10 → 9% redukce

### Crit

```
effective_level = max(1, enemy_level)   ← ochrana před dělením nulou
Crit šance = min(0.50, LCK × 5 / (effective_level × 2))
Crit damage = +100% (2× celkový damage)
```

### Pořadí tahů a dodge

- **Ranger** má vždy first strike (pasivní class bonus) — jde první bez ohledu na ostatní
- SPD stat je odstraněn
- Dodge systém je odstraněn — `_dodge_chance()` se odstraní z combat enginu
- Status efekt `slow` se odstraní (závislý na SPD)
- Talent `evasion` (Ranger, +10% dodge) se nahradí jiným bonusem — viz sekce Talenty

---

## Odstraněno z DB

| Odstraněno | Důvod |
|-----------|-------|
| `atk` | Nahrazeno třídně-specifickou damage formulí (runtime výpočet) |
| `def_` | Nahrazeno Armor% systémem z `bonus_def` na itemech |
| `spd` | Odstraněno, nahrazeno Ranger first-strike pasivem |
| `mp_max` | Mana odstraněna — Mage vždy castuje automaticky |
| `atk_base`, `def_base`, `spd_base`, `mp_base` (v CLASS_BASE_STATS) | Nepotřebné |

`hp_max` zůstává v DB — přepočítává se při level-upu a equipu z nové formule.

---

## Dopad na Items

### Zachovaná pole (stále relevantní)

| Pole | Účel |
|------|------|
| `bonus_atk` | weapon_dmg zdroj (zbraně, prsteny, amulety) |
| `bonus_def` | armor_value zdroj (zbroje, helmy, boty, prsteny) |
| `bonus_str`, `bonus_dex`, `bonus_int`, `bonus_end`, `bonus_luck` | Primární stat bonusy — zachovány |
| `bonus_hp` | Flat HP bonus — zachován (přidává se k vypočítanému HP) |

### Odstraněná pole z Item modelu (DB migrace)

| Pole | Důvod |
|------|-------|
| `bonus_spd` | SPD stat odstraněn — žádné využití |
| `bonus_mp` | MP odstraněno — **výjimka: scrolly** (viz níže) |

### Výjimka: bonus_mp na scrollech

`bonus_mp` na scrollech aktuálně funguje jako **okamžitý XP bonus** (ne mana). Tato logika se přesune na `bonus_xp` field — nový sloupec v Item modelu, nebo se logika přepíše aby používala `bonus_hp` jako náhradní carrier. Rozhodnutí: přidat `bonus_xp: int = 0` do Item modelu.

### Runosmith a Fateweaver

- `runosmith.py` — odstraní se efekty s `bonus_spd` a `bonus_mp`; konkrétní náhrada:
  - `bonus_spd` efekty → nahradit `bonus_dex` (tematicky nejbližší — rychlost = obratnost)
  - `bonus_mp` efekty → nahradit `bonus_luck` (mana byla caster resource, luck je univerzální bonus)
- `fateweaver.py` — odstraní se efekt `{"bonus_mp_flat": 40, "bonus_spell_pct": 10}` celý; `bonus_spell_pct` je mrtvý kód (nikde se nečte v combat enginu)
- `game/seed.py` — odstraní se parametry `bonus_spd=` a `bonus_mp=` z volání item konstruktorů (řádky 210–233)
- `game/dungeon_modifiers.py` — odstraní se `enemy_spd_mult` a `player_mp_mult` modifikátory a jejich aplikace

### Item upgrade systém

`InventoryItem._upgraded_item_dict()` škáluje klíče `atk`, `def`, `spd`, `mp` — klíče `spd` a `mp` se odstraní, `atk` a `def` zůstávají.

---

## Dopad na Combat Engine

### CombatantConfig (nové fieldy)

```python
# Stará pole která MIZÍ:
# atk, def_, spd, mp, strategy

# Nová pole:
weapon_dmg: int        # bonus_atk z vybavené zbraně (nebo class base)
armor_value: int       # součet bonus_def ze všech vybavených předmětů
primary_stat: int      # hodnota primárního statu (STR/DEX/INT dle třídy)
secondary_a: int       # první sekundární stat (DEX pro Warriora, STR pro Rangera, STR pro Mage)
secondary_b: int       # druhý sekundární stat (INT pro Warriora, INT pro Rangera, DEX pro Mage)

# Zachována pole:
hp, luck, class_name, level, talents, talent_t2, subclass, set_bonuses
```

### Damage výpočet za runtime

```python
def _calc_damage(weapon_dmg, primary_stat, sec_a, sec_b,
                 armor_value, enemy_level, is_crit, class_name):
    base = weapon_dmg * (1 + primary_stat / 10) + sec_a / 2 + sec_b / 2
    eff_level = max(1, enemy_level)
    armor_cap = CLASS_ARMOR_CAPS[class_name]  # 0.45 / 0.25 / 0.15
    armor_pct = min(armor_cap, armor_value / eff_level)
    dmg = base * (1.0 - armor_pct)
    if is_crit:
        dmg *= 2.0
    return max(1, int(dmg))
```

### Odstraněno z combat enginu

- `_dodge_chance()` funkce
- `slow` status efekt
- `COMBAT_STRATEGIES` dict — **kompletně odstraněn**
- `strategy` field z `CombatantConfig`
- MP tracking (`self.mp`, `self.mp_max`, `mp_cost_pct` logika)
- `check_mage_opening_crit(mage_spd, enemy_spd)` v `game/class_mechanics.py` — závislá na SPD, odstraní se

### Combat strategies — kompletní odstranění

`COMBAT_STRATEGIES` se odstraní úplně. Dopad:

| Místo | Akce |
|-------|------|
| `combat_engine.py` | Smazat `COMBAT_STRATEGIES` dict a veškerou `_strat[...]` logiku |
| `CombatantConfig` | Odstraní se field `strategy: str = "balanced"` |
| `_FighterState.__init__()` | Odstraní se aplikace multiplikátorů z strategie |
| `routers/arena.py` | Odstraní se `strategy` z `ArenaAttackBody` |
| `routers/quest.py` | Odstraní se `strategy` z `StartQuestRequest` |
| `routers/dungeon.py` | Odstraní se `strategy` z `EnterDungeonRequest` |
| `routers/guild_war.py` | Odstraní se `strategy` z `WarAttackReq` |
| `frontend/js/ui.js` | Smazat `_STRAT_DEFS`, `getStrategy()`, `strategyPickerHtml()` |
| `frontend/js/arena.js` | Odstraní se `strategy: getStrategy()` z API volání |
| `frontend/js/quest.js` | Odstraní se `strategy: getStrategy()` z API volání |
| `frontend/js/dungeons.js` | Odstraní se `strategy: getStrategy()` z API volání |
| `frontend/js/guild.js` | Odstraní se `strategy` z API volání (`localStorage.getItem('combatStrategy')`) |
| `frontend/js/build.js` | Odstraní se volání `getStrategy()` (řádek 63) |
| `localStorage` | Klíče `combat_strategy` i `combatStrategy` se přestanou ukládat (obě varianty) |
| `backend/tests/test_strategies_talents.py` | Smazat celý soubor — testuje pouze odstraněné COMBAT_STRATEGIES |

Poznámka: `defensive` strategie měla `start_status: "shield"` — tento efekt zaniká spolu se strategiemi.

---

## Dopad na Talenty

### Talenty závislé na MP (musí být přepsány)

| Talent | Aktuální efekt | Nový efekt |
|--------|---------------|-----------|
| `mana_surge` | +25% MP | +15% damage (flat damage bonus) |
| `mana_void` (T2) | vysaje 30% many protivníka | aplikuje `weaken` status na 2 kola |

### Talent závislý na dodge

| Talent | Aktuální efekt | Nový efekt |
|--------|---------------|-----------|
| `evasion` (Ranger) | +10% dodge šance | +10% crit šance |

### Ostatní talenty

Talenty odkazující na `atk_mult`/`def_mult` v subclass systému se mapují takto:
- `atk_mult` → multiplikátor výsledného damage (stejná logika, jiný název)
- `def_mult` → multiplikátor `armor_value`

---

## Dopad na Subclassy

Subclass `stat_mults` se přemapují:

| Starý klíč | Nový klíč | Aplikace |
|-----------|----------|---------|
| `atk_mult` | `dmg_mult` | násobí výsledný damage |
| `def_mult` | `armor_mult` | násobí `armor_value` |
| `hp_mult` | `hp_mult` | beze změny |
| `spd_mult` | odstraněn | — |
| `mp_mult` | odstraněn | — |

Subclassy `elementalist` a `necromancer` ztratí `mp_mult` — nahradí je `dmg_mult: 1.10` resp. `dmg_mult: 1.05`.

---

## DB Migrace

**Soubor:** `backend/alembic/versions/0047_stat_system_redesign.py`

Operace (vše s idempotentním guard):

**Tabulka `characters` — odstraněné sloupce:**
- `atk`, `def_`, `spd`, `mp_max`
- `hp_max` zůstává — přepočítán při startu přes `recalculate_stats()`

**Tabulka `items` — odstraněné sloupce:**
- `bonus_spd`, `bonus_mp`

**Tabulka `items` — nový sloupec:**
- `bonus_xp: int = 0` (náhrada za scroll logiku z `bonus_mp`)

```python
# Idempotentní guard vzor:
cols = [c['name'] for c in inspect(bind).get_columns('characters')]
if 'atk' in cols:
    op.drop_column('characters', 'atk')

item_cols = [c['name'] for c in inspect(bind).get_columns('items')]
if 'bonus_spd' in item_cols:
    op.drop_column('items', 'bonus_spd')
if 'bonus_mp' in item_cols:
    op.drop_column('items', 'bonus_mp')
if 'bonus_xp' not in item_cols:
    op.add_column('items', sa.Column('bonus_xp', sa.Integer(), nullable=False, server_default='0'))
```

---

## Dopad na UI

- Stat panel zobrazuje: STR / DEX / INT / END / LCK + HP + Armor%
- Odstraněno z UI: ATK číslo, DEF číslo, SPD číslo, MP bar
- Přidáno: tooltip u každého statu s popisem
- Mage nemá MP bar

---

## Soft Caps

Soft caps se aplikují na primární staty před výpočtem damage:

```
0–50:   100% hodnoty
51–150:  70% hodnoty
151+:    30% hodnoty
```

`armor_value` a `weapon_dmg` soft cap nemají — jsou omezeny jinak (Armor% cap, weapon itemizace).

---

## Příklad — Level 10 postava

**Warrior** (STR=30, DEX=10, INT=5, END=15, weapon_dmg=20, armor_value=90, enemy_level=10):
- Damage: `20 × (1 + 30/10) + 10/2 + 5/2` = `20×4 + 5 + 2` = **87**
- HP: `15 × 5 × 11` = **825**
- Armor%: `90/10 = 9%` → enemy hit 87 → po armor: 87×0.91 = **79**

**Mage** (INT=30, STR=5, DEX=8, END=8, weapon_dmg=20, armor_value=20, enemy_level=10):
- Damage: `20 × (1 + 30/10) + 5/2 + 8/2` = `20×4 + 2 + 4` = **86**
- HP: `8 × 2 × 11` = **176**
- Armor%: `20/10 = 2%`
- *Záměrně křehký — vysoký damage, nízké přežití*

**Ranger** (DEX=30, STR=9, INT=8, END=12, weapon_dmg=20, armor_value=50, enemy_level=10):
- Damage: `20 × (1 + 30/10) + 9/2 + 8/2` = `20×4 + 4 + 4` = **88**
- HP: `12 × 4 × 11` = **528**
- Armor%: `50/10 = 5%`
- First strike: vždy útočí první

---

## Co se nemění

- Arena ELO systém
- Guild systém
- Loot / item drop systém
- Quest systém
- Prestige systém
- Rage systém Warriora (závisí na HP thresholdech, ne na SPD/MP)
- Ranger first-strike systém (existuje, jen se posílí na garantovaný první tah)
- Mage spell cycle + burn DoT (zůstávají, jen bez MP gatingu)
- Bleed, poison, stun, shield, burn, weaken, regen status efekty (slow se odstraní)
