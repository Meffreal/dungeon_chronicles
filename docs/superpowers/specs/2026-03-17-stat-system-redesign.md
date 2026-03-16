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

| Stat | Warrior | Hunter | Mage |
|------|---------|--------|------|
| Síla (STR) | ⭐ hlavní damage | sekundární obrana | sekundární obrana |
| Obratnost (DEX) | sekundární obrana | ⭐ hlavní damage | sekundární obrana |
| Inteligence (INT) | sekundární obrana | sekundární obrana | ⭐ hlavní damage |
| Výdrž (END) | HP | HP | HP |
| Štěstí (LCK) | crit šance | crit šance | crit šance |

### Damage formule

```
Warrior:  weapon_dmg × (1 + STR/10) + DEX/2 + INT/2
Hunter:   weapon_dmg × (1 + DEX/10) + STR/2 + INT/2
Mage:     weapon_dmg × (1 + INT/10) + STR/2 + DEX/2
```

- `weapon_dmg` = hodnota vybavené zbraně (item atribut)
- Pokud není zbraň vybavena: `weapon_dmg` = class base (Warrior 8, Hunter 6, Mage 4)
- Sekundární staty přidávají flat bonus k celkovému damage

### HP

```
Warrior:  END × 5 × (level + 1)
Hunter:   END × 4 × (level + 1)
Mage:     END × 2 × (level + 1)
```

### Armor (damage reduction %)

```
Armor% = armor_value / enemy_level
```

| Třída | Max Armor% |
|-------|-----------|
| Warrior | 45% |
| Hunter | 25% |
| Mage | 15% |

- `armor_value` = součet armor bonusů ze všech vybavených předmětů
- Příklad: Warrior s armor_value=90 vs enemy level 10 → 9% redukce (cap 45%)

### Crit

```
Crit šance = LCK × 5 / (enemy_level × 2),  max 50%
Crit damage = +100% (2× celkový damage)
```

### Pořadí tahů

- **Hunter** má vždy first strike (pasivní class bonus) — jde první bez ohledu na ostatní
- SPD stat je odstraněn, žádný dodge systém

---

## Odstraněno z DB a UI

| Odstraněno | Důvod |
|-----------|-------|
| `atk` | Nahrazeno třídně-specifickou damage formulí |
| `def_` | Nahrazeno Armor% systémem |
| `spd` | Odstraněno, nahrazeno Hunter first-strike pasivem |
| `mp_max` | Mage mana odstraněna — Mage vždy castuje automaticky |
| `atk_base`, `def_base`, `spd_base` (v CLASS_BASE_STATS) | Nepotřebné |

---

## Dopad na items

- Zbraně: atribut `atk_bonus` se přejmenuje/přeinterpretuje jako `weapon_dmg`
- Zbroje/helmy/boty: atribut `def_bonus` se přejmenuje jako `armor_value`
- Logika je univerzální — třída rozhoduje jak se stat použije (ne item sám)

---

## Dopad na combat engine

- `CombatantConfig` ztratí `atk`, `def_`, `spd`, `mp` fieldy
- Přidá `weapon_dmg`, `armor_value`, `primary_stat_value`, `class_name` (již existuje)
- `run_combat()` počítá damage per-turn z nové formule
- Mage spell systém (spell cycle, burn DoT) zůstává — jen MP resource mizí
- Warrior rage systém a Hunter first-strike zůstávají

---

## Dopad na DB

Odstraněné sloupce z tabulky `characters`:
- `atk`, `def_`, `spd`, `mp_max`

Ponechané sloupce:
- `hp_max` (přepočítán z nové formule při každém level-upu / equip změně)
- Všech 5 primárních statů

Nová Alembic migrace: `0046_stat_system_redesign.py`

---

## Dopad na UI

- Stat panel zobrazuje: STR / DEX / INT / END / LCK + HP + Armor%
- Odstraněno z UI: ATK číslo, DEF číslo, SPD číslo, MP bar
- Přidáno: tooltip u každého statu s popisem ("Obratnost ovlivňuje damage Lovce a rychlost útoku")
- Mage nemá MP bar

---

## Příklad — Level 10 postava

**Warrior** (STR=30, DEX=10, INT=5, END=15, weapon_dmg=20, armor_value=90, enemy_level=10):
- Damage: `20 × (1 + 30/10) + 10/2 + 5/2` = `20×4 + 5 + 2` = **87**
- HP: `15 × 5 × 11` = **825**
- Armor%: `90/10` = 9% (well below 45% cap)

**Mage** (INT=30, STR=5, DEX=8, END=8, weapon_dmg=20, armor_value=20, enemy_level=10):
- Damage: `20 × (1 + 30/10) + 5/2 + 8/2` = `20×4 + 2 + 4` = **86**
- HP: `8 × 2 × 11` = **176**
- Armor%: `20/10` = 2% (well below 15% cap)

**Hunter** (DEX=30, STR=9, INT=8, END=12, weapon_dmg=20, armor_value=50, enemy_level=10):
- Damage: `20 × (1 + 30/10) + 9/2 + 8/2` = `20×4 + 4 + 4` = **88**
- HP: `12 × 4 × 11` = **528**
- Armor%: `50/10` = 5% (below 25% cap)
- First strike: vždy útočí první

---

## Co se nemění

- Talent systém (talent_t2, subclass bonusy)
- Arena ELO systém
- Guild systém
- Loot / item drop systém
- Quest systém
- Prestige systém
