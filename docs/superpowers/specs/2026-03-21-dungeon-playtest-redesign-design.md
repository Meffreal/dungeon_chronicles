# Dungeon Playtest Redesign — Design Spec

**Datum:** 2026-03-21
**Status:** Approved
**Scope:** Nový roguelite dungeon systém pod Playtest tabem — izolovaný od stávajícího dungeon systému

---

## Kontext & Problém

Stávající dungeon systém je lineární: vstup → 5× "další stage" → odměny. Hráče nebaví kvůli:
- **Žádnému rozhodování** — jediná volba je "pokračovat" nebo "opustit"
- **Nulové variabilitě** — každý run je identický
- **Pasivnímu combatu** — výsledek závisí pouze na stats postavy, hráč nic neovlivní

## Cíl

Přidat **Playtest tab** s roguelite dungeon systémem. Starý dungeon systém zůstává beze změny jako záloha. Po úspěšném playtestingu Playtest tab nahradí starý systém.

---

## Architektura & Izolace

### Princip izolace

Vše nové žije pod prefixem `/playtest/`. Žádný existující soubor se nemění.

```
backend/
  routers/playtest_dungeon.py     # 7 nových endpointů
  game/playtest_dungeon.py        # generátor map, herní logika
  models/playtest_run.py          # nový ORM model PlaytestRun

frontend/
  js/playtest.js                  # kompletní frontend logika
  css/components.css              # rozšíření o .pt-* třídy

game.html                         # +<div id="page-playtest">
                                  # +navigační tlačítko "Playtest"
```

Nedotčené soubory: `dungeon.py`, `dungeon_run.py`, `dungeons.js`, `dungeon.js` a vše ostatní.

### Nový ORM model `PlaytestRun`

```python
class PlaytestRun(Base):
    __tablename__ = "playtest_runs"

    id              : int (PK)
    char_id         : int (FK → characters.id)
    dungeon_key     : str           # "tomb" | "fiery" | "citadel"
    status          : str           # "active" | "completed" | "failed"
    map_data        : JSON          # celý strom uzlů (generován při vstupu)
    current_node_id : str | None    # ID uzlu čekajícího na akci
    visited_nodes   : JSON          # list navštívených node ID
    relics          : JSON          # [{id, name, effect_key, value}]
    hp_current      : int
    reward_xp       : int (default 0)
    reward_gold     : int (default 0)
    cooldown_until  : datetime | None
    created_at      : datetime
```

### Struktura `map_data` JSON

```json
{
  "nodes": {
    "n1": {
      "type": "combat",
      "enemy_name": "Skeleton Guard",
      "enemy_mult": 0.8,
      "status": "completed",
      "reward_xp": 120,
      "reward_gold": 60
    },
    "n2": {
      "type": "rest",
      "status": "available"
    },
    "n3": {
      "type": "elite",
      "enemy_name": "Tomb Warden",
      "enemy_mult": 1.4,
      "status": "locked"
    },
    "n_boss": {
      "type": "boss",
      "enemy_name": "Guardian of Eternity",
      "enemy_mult": 2.0,
      "status": "locked"
    }
  },
  "edges": [["start","n1"], ["n1","n2"], ["n1","n3"], ["n2","n_boss"], ["n3","n_boss"]],
  "layout": {
    "start": [0, 0],
    "n1":    [1, 0],
    "n2":    [2, -1],
    "n3":    [2, 1],
    "n_boss":[3, 0]
  }
}
```

---

## Dungeony

Tři dungeony, zachovány jako oddělené konfigurace. Fiery Depths = hard mode Tomb (stejná struktura, silnější nepřátelé, jiné eventy).

| Dungeon | Klíč | Min. level | Cooldown | Boss mult | Téma eventů |
|---------|------|-----------|----------|-----------|-------------|
| Tomb of Forgotten | `tomb` | 8 | 6h | 2.0× | Hrobky, prokletí, nemrtví |
| Fiery Depths | `fiery` | 15 | 8h | 2.4× | Oheň, láva, démonická past |
| Citadel of Chaos | `citadel` | 24 | 12h | 2.8× | Chaos, magie, korupce |

---

## Generování mapy

Mapa se generuje **procedurálně** při `enter`. Struktura:

```
[Start] → Vrstva 1 (2 uzly) → Vrstva 2 (2 uzly) → Vrstva 3 (2 uzly) → [Boss]
```

Celkem: 7–9 uzlů (Start + 6 uzlů ve vrstvách + Boss).

### Pravidla generování

- Každá vrstva má přesně 2 uzly — hráč volí jeden, druhý přeskočí
- Vrstva 1: vždy `combat` + (`rest` nebo `event`)
- Vrstva 2: vždy `combat` nebo `elite` + (`event` nebo `shop`)
- Vrstva 3: vždy `elite` + (`rest` nebo `combat`)
- Boss: vždy poslední, jediný uzel bez volby
- Celá mapa musí mít: aspoň 1 `rest`, aspoň 1 `elite`, 1–2 `event`

### Typy uzlů

| Typ | Ikona | Popis |
|-----|-------|-------|
| `combat` | ⚔️ | Normální nepřítel, po výhře výběr 1 ze 3 relics |
| `elite` | 💀 | Silnější nepřítel (1.4× mult), garantovaně lepší relic pool |
| `event` | ❓ | Náhodná událost s rozhodnutím, žádný combat |
| `rest` | 🛖 | Obnova 25% max HP, žádný combat |
| `shop` | 💰 | Nákup za run-gold (ne z banku postavy) |
| `boss` | 👑 | Finální boss, konec runu |

---

## Herní mechaniky

### HP přenos

- Hráč vstupuje s `char.hp_max` HP
- HP se přenáší mezi uzly — bez automatické obnovy
- Rest uzel: `hp = min(hp_current + hp_max * 0.25, hp_max)`
- Smrt v uzlu → `status = "failed"`, partial odměny (50% nashromážděného XP, 0 gold)

### Relic systém

Po výhře v `combat` nebo `elite` uzlu backend nabídne **3 náhodné relics** z poolu daného dungeonu. Hráč vybere 1. Relic platí do konce runu.

**Pool relics (sdílený, ~12 kusů):**

| ID | Název | Efekt |
|----|-------|-------|
| `blood_stone` | Krvavý kámen | +20% ATK |
| `stone_shield` | Kamenný štít | +15% DEF |
| `healing_herb` | Léčivá bylina | Obnov 15% HP ihned |
| `gold_coin` | Zlatá mince | +50% gold z uzlů |
| `swift_boots` | Rychlé nohy | +15% SPD |
| `war_cry` | Válečný pokřik | +10% ATK, +10% SPD |
| `iron_will` | Železná vůle | +20% HP max (pro zbytek runu) |
| `cursed_blade` | Prokletý meč | +35% ATK, -10% DEF |
| `lucky_charm` | Šťastný amulet | +15% LUCK |
| `mana_crystal` | Mana krystal | +20% DMG z abilities |
| `vampiric_edge` | Vampýrická čepel | 10% šance léčit se za 15% způsobeného DMG |
| `ancient_tome` | Starobylý svazek | +25% XP z uzlů |

### Shop uzel

Ceny jsou v **run-gold** (gold nashromážděný v aktuálním runu, ne inventář postavy):

| Položka | Cena | Efekt |
|---------|------|-------|
| Léčení | 50g | Obnov 40% max HP |
| Stat boost | 80g | +10% ATK na zbytek runu |
| Relic refresh | 120g | Dostaneš nový výběr 1 ze 3 relics |

### Event uzly

Každý dungeon má **6 tematických eventů**. Každý event má 2 volby s jasně popsaným rizikem.

**Příklady pro Tomb:**
1. "Nalezl jsi zlatou truhlu." → A) Otevři (70% +200g / 30% past -15% HP) / B) Ignoruj
2. "Duch tě prosí o pomoc." → A) Pomoz (ztráť 10% HP, získej relic) / B) Odmítni (nic)
3. "Tajná chodba." → A) Projdi (event v dalším uzlu se změní na combat s 1.6× mult ale 2× odměna) / B) Ignoruj

### Abandon

- Kdykoli během aktivního runu
- Hráč dostane 50% nashromážděného XP a 0 gold
- Cooldown: `cooldown / 4`

---

## Backend endpointy

Všechny pod `/playtest/dungeon/`:

| Metoda | Path | Popis |
|--------|------|-------|
| `GET` | `/list` | Dostupné dungeony s cooldown info |
| `GET` | `/status` | Aktuální run + celá mapa |
| `POST` | `/enter` | Vstup do dungeonu, generace mapy |
| `POST` | `/choose-node` | Výběr uzlu na mapě |
| `POST` | `/choose-relic` | Výběr relicu po combatu |
| `POST` | `/shop-buy` | Nákup v shop uzlu |
| `POST` | `/collect` | Vyzvednutí odměn (completed/failed) |
| `POST` | `/abandon` | Opuštění runu |

### Tok `choose-node`

```
POST /playtest/dungeon/choose-node { run_id, node_id }

1. Validace: node musí být v available_nodes
2. Dle node.type:
   - combat/elite: spustit combat, vrátit battle_log + výsledek
     - výhra → nastavit current_node_id, generovat 3 relic nabídky
     - prohra → status = "failed"
   - rest: obnovit HP, posunout mapu
   - event: vrátit event data (text + volby) → čekat na choose-event
   - shop: vrátit shop položky → čekat na shop-buy
   - boss: combat → výhra = status "completed", nastavit cooldown
3. Aktualizovat visited_nodes, reward_xp/gold
4. Vrátit nový stav runu + dostupné uzly
```

### Integrace s existujícími systémy

Zachovat stávající hooks při dokončení runu:
- `increment_guild_weekly("dungeons", ...)`
- `increment_weekly_board(char_id, "dungeons", ...)`
- `add_season_xp(char_id, "dungeon_complete", ...)`
- `_decrease_equipped_durability(...)`
- HC permadeath při selhání (pokud `char.is_hardcore`)

---

## Frontend

### Navigace

Nové tlačítko v topbaru: **"⚗️ Playtest"** s fialovou barvou a `BETA` badge. CSS třída `.nav-playtest`.

### Stránka `page-playtest`

Tři sekce, přepínané dle stavu:

**1. List view** (žádný aktivní run):
- 3 dungeon karty s názvem, min. level, cooldown timerem, tlačítkem "Vstoupit"
- Zamčené dungeony jsou zašedlé

**2. Active run view** (aktivní run):
- **Sidebar:** HP bar, seznam relics, nashromážděné XP/gold
- **Mapa:** SVG nebo CSS-positioned uzly s hranami, klikatelné dostupné uzly
- Tlačítko "Opustit run" (s potvrzovacím modálem)

**3. Node action modal** (po kliknutí na uzel):
- Combat: jméno nepřítele, tlačítko "Vstoupit do boje"
- Rest: "Obnovit X HP?" s tlačítkem
- Event: popis + 2 tlačítka volby
- Shop: 3 karty s cenami

**4. Relic výběr modal** (po výhře v combatu):
- 3 karty relics vedle sebe
- Každá: název, ikona, popis efektu
- Klik = výběr, modal se zavře

**5. Collect view** (run dokončen/selhal):
- Shrnutí: XP, gold, navštívené uzly, použité relics
- Tlačítko "Vyzvednout odměny"

### Combat replay

Používá stávající `showCombatReplay()` beze změny.

### CSS třídy

Prefix `.pt-` pro všechny nové třídy. Žádné změny existujících CSS.

---

## Migrace

Nová Alembic migrace `0049_playtest_runs.py`:
- Přidá tabulku `playtest_runs`
- Idempotentní guard (inspect)
- Žádné změny existujících tabulek

---

## Co je mimo scope

- Týdenní modifikátory pro Playtest (přidají se až po schválení systému)
- Multiplayer / guild dungeon runy
- Dungeon-specifické relic pooly (sdílený pool pro teď)
- Statistiky / history runů
- Achievements pro nový systém

---

## Kritéria úspěchu

1. Hráč může vstoupit do Playtest dungeonu aniž by ovlivnil stávající dungeon systém
2. Mapa se generuje procedurálně a je různá při každém runu
3. Hráč má smysluplné rozhodnutí v každé vrstvě (volba uzlu)
4. Relics mění průběh combatu měřitelně
5. Run se ukládá a lze v něm pokračovat po reloadu stránky
6. HC permadeath správně triggeruje při selhání v Playtest dungeonu
