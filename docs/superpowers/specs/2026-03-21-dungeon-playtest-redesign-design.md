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
  routers/playtest_dungeon.py     # 9 nových endpointů
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
    dungeon_key     : str           # "pt_tomb" | "pt_fiery" | "pt_citadel"
                                    # Prefix "pt_" odlišuje od starého systému ("tomb_of_forgotten" atd.)
    status          : str           # "active" | "completed" | "failed"
    map_data        : JSON          # celý strom uzlů (generován při vstupu)
    current_node_id : str | None    # ID uzlu čekajícího na akci
    visited_nodes   : JSON          # list navštívených node ID
    relics          : JSON          # [{id, name, effect_key, value}]
    hp_current      : int
    hp_max          : int           # efektivní max HP v runu (char.hp_max + iron_will bonus)
                                    # ukládá se aby rest a cap výpočty byly konzistentní
    run_gold        : int (default 0)  # gold dostupný pro shop UVNITŘ runu — oddělený od reward_gold
    reward_xp       : int (default 0)
    reward_gold     : int (default 0)  # gold vyplacený hráči při collect (po odečtení shop výdajů)
    reward_claimed  : bool (default False)  # guard proti double-spend při collect
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
| Tomb of Forgotten | `pt_tomb` | 8 | 6h | 2.0× | Hrobky, prokletí, nemrtví |
| Fiery Depths | `pt_fiery` | 15 | 8h | 2.4× | Oheň, láva, démonická past |
| Citadel of Chaos | `pt_citadel` | 24 | 12h | 2.8× | Chaos, magie, korupce |

> **Poznámka k prefix `pt_`:** Starý systém používá klíče `tomb_of_forgotten`, `fiery_depths`, `citadel_of_chaos`. Nové klíče mají prefix `pt_` aby nemohlo dojít ke kolizi v DB ani v podmínkách. Nikde nesdílejí namespace.

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

**Constraint validace po generování:** Generátor po sestavení mapy ověří constraints. Pokud nejsou splněny (např. žádný `rest`), provede force-substituci:
- Chybí `rest` → Vrstva 3 pravý uzel se změní na `rest` (přepíše `combat`)
- Chybí `elite` → Vrstva 2 levý uzel se změní na `elite` (přepíše `combat`)
- Žádný `event` → Vrstva 1 pravý uzel se změní na `event` (přepíše `rest`)
Substituce probíhá v tomto pořadí, po max. 1 iteraci (bez nekonečné smyčky).

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

- Hráč vstupuje s `char.hp_max` HP; tato hodnota se uloží jako `run.hp_max` při vytvoření runu
- `run.hp_max` se aktualizuje okamžitě při výběru relicu `iron_will` (+20%): `run.hp_max = int(run.hp_max * 1.2)`
- HP se přenáší mezi uzly — bez automatické obnovy
- Rest uzel: `run.hp_current = min(run.hp_current + run.hp_max * 0.25, run.hp_max)`
- Smrt v uzlu → `status = "failed"`, partial odměny (50% nashromážděného XP, 0 gold)

> **Proč `hp_max` na modelu:** `iron_will` relic mění max HP uvnitř runu. Kdyby se `hp_max` vždy derivovalo z `char.hp_max`, změna by se ztratila mezi requesty. Uložením `run.hp_max` je cap konzistentní po celý run bez přepočítávání.

### Relic systém

Po výhře v `combat` nebo `elite` uzlu backend nabídne **3 náhodné relics** z poolu daného dungeonu. Hráč vybere 1. Relic platí do konce runu.

#### Relic aplikace do CombatantConfig

Před každým `run_combat()` se sestaví `CombatantConfig` pro hráče s aplikovanými efekty aktivních relics. Funkce `build_playtest_combatant(char, run) -> CombatantConfig` v `game/playtest_dungeon.py`:

```python
def build_playtest_combatant(char, run: PlaytestRun) -> CombatantConfig:
    # Základ — stejné hodnoty jako běžný dungeon
    atk = char.atk; def_ = char.def_; hp = run.hp_current
    spd = char.spd; luck = char.luck

    for relic in run.relics:
        if relic.get("consumed"):
            continue  # healing_herb a podobné — pouze one-time efekt
        key = relic["effect_key"]
        val = relic["value"]          # procento jako float, např. 0.20
        if key == "atk_pct":      atk  = int(atk  * (1 + val))
        elif key == "def_pct":    def_ = int(def_ * (1 + val))
        elif key == "spd_pct":    spd  = int(spd  * (1 + val))
        elif key == "luck_pct":   luck = int(luck * (1 + val))
        elif key == "hp_max_pct": pass  # hp_max uložen na run, hp_current se nemění zpětně
        # vampiric_edge a gold_coin nemají stat efekt na CombatantConfig
        # vampiric_edge → předat jako set_bonuses (viz níže)

    # vampiric_edge: mapuje na set_bonuses strukturu aby combat engine mohl aplikovat lifesteal
    set_bonuses = get_set_bonuses(char, db)  # existující set bonusy
    if any(r["id"] == "vampiric_edge" and not r.get("consumed") for r in run.relics):
        set_bonuses = {**set_bonuses, "vampiric_lifesteal": 0.15, "vampiric_chance": 0.10}

    return CombatantConfig(
        atk=atk, def_=def_, hp=hp, mp=char.mp, spd=spd, luck=luck,
        class_name=char.char_class, level=char.level,
        talents=char.talent_key or "", talent_t2=char.talent_t2_key or "",
        subclass=char.subclass_key or "", set_bonuses=set_bonuses, strategy="balanced"
    )
```

> `vampiric_edge` vyžaduje support v combat engine — implementace přidá `vampiric_lifesteal` a `vampiric_chance` do zpracování set_bonuses v `combat_engine.py` (nový effect handler).

#### One-time relics

`healing_herb` — efekt se aplikuje okamžitě při `choose-relic`:
```python
# V endpointu choose-relic, po uložení relicu:
if relic["effect_key"] == "hp_restore_pct":
    run.hp_current = min(run.hp_current + int(run.hp_max * relic["value"]), run.hp_max)
    relic["consumed"] = True  # zabrání opakované aplikaci v build_playtest_combatant
```
Consumed relics zůstávají v `run.relics` pro historii — frontend nezobrazuje consumed relics v aktivním seznamu.

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

Ceny jsou v **run-gold** (`run.run_gold` — gold nashromážděný v aktuálním runu, ne inventář postavy). `run_gold` se inkrementuje při každém combat/elite/boss výhře. Shop nákup odečítá z `run_gold`. `reward_gold` vyplacený hráči při `collect` = `run_gold` v době dokončení (shop výdaje byly již odečteny z `run_gold`).

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
| `POST` | `/choose-node` | Výběr uzlu na mapě (combat/rest/boss) |
| `POST` | `/choose-event` | Odeslání volby hráče pro event uzel |
| `POST` | `/choose-relic` | Výběr relicu po combatu |
| `POST` | `/shop-buy` | Nákup v shop uzlu |
| `POST` | `/collect` | Vyzvednutí odměn (completed/failed) |
| `POST` | `/abandon` | Opuštění runu |

### Tok `choose-node`

```
POST /playtest/dungeon/choose-node { run_id, node_id, skip_shop: bool = False }

1. Validace: run.status == "active", node.status == "available"
2. Dle node.type:
   - combat/elite:
     - sestavit CombatantConfig pro hráče s aplikovanými relics (viz Relic aplikace níže)
     - spustit run_combat()
     - výhra → přidat reward_xp/run_gold
              → node.status = "completed", DO NOT odemknout sousedy zatím
              → current_node_id = node_id, generovat 3 relic nabídky
              → vrátit { result: "win", pending_relics: [...], battle_log }
              → ČEKAT na choose-relic — sousední uzly se odemknou až po výběru relicu
     - prohra → node.status = "completed", status = "failed", hp_current = 0
              → vrátit { result: "loss", battle_log }
   - rest:
     - hp_current = min(hp_current + hp_max * 0.25, hp_max)
     - node.status = "completed", odemknout sousední uzly
     - vrátit { hp_restored, new_hp }
   - event:
     - node.status = "pending_event" (nová hodnota — uzel aktivní, ale nedokončený)
     - current_node_id = node_id
     - vrátit { event_data: { id, text, choices: [{index, label, hint}] } }
     - ČEKAT na choose-event
   - shop:
     - pokud skip_shop == True: node.status = "completed", odemknout sousedy, vrátit {}
     - jinak: vrátit { shop_items: [{id, label, cost, effect}], run_gold }
              → hráč buď zavolá shop-buy nebo znovu choose-node s skip_shop=True
   - boss:
     - sestavit CombatantConfig s relics
     - spustit run_combat()
     - výhra → node.status = "completed", status = "completed"
              → nastavit cooldown_until, spustit completion hooks
     - prohra → status = "failed"
3. Vrátit nový run stav
```

### Tok `choose-event`

```
POST /playtest/dungeon/choose-event { run_id, choice_index }

1. Validace: run.status == "active", current_node_id je event uzel
2. Aplikovat efekt dle choice_index a výsledku (deterministický nebo random seeded):
   - gold bonus: run_gold += amount
   - HP ztráta: hp_current -= int(hp_max * percent)
   - relic bonus: generovat 1 relic výběr (vrátit jako pending_relics)
   - next_node_override: upravit typ/mult sousedního uzlu v map_data
3. Posunout mapu: uzel dokončen, odemknout sousedy
4. Vrátit efekt { outcome_text, hp_delta, gold_delta } + nový run stav
```

### Tok `collect`

```
POST /playtest/dungeon/collect { run_id }

1. Validace: run.status in ("completed", "failed"), reward ještě nebyl vyplacen
2. char.xp += run.reward_xp
3. char.gold += run.run_gold  # run_gold = reward_gold (shop výdaje již odečteny)
4. log_gold(db, char, run.run_gold, GoldReason.DUNGEON_REWARD,
           {"dungeon_run_id": run.id, "dungeon_key": run.dungeon_key})
   # VŽDY log_gold — nikdy přímá editace char.gold
   # Signatura: log_gold(db, char, amount, reason: GoldReason, detail: dict | None)
5. Level-up check (smyčka)
6. Boss loot drop pokud status == "completed"
7. Vrátit { xp_gained, gold_gained, item, leveled_up, character }
```

### Integrace s existujícími systémy

#### Per-combat-node (každá výhra v combat/elite/boss uzlu)
Správné signatury — musí odpovídat existujícím funkcím:
```python
await increment_guild_weekly(char.guild_id, "kills", 1, char.id, db)
await increment_weekly_board(char.id, "kills", 1, db)
await add_season_xp(char.id, "dungeon_stage", db)
await _decrease_equipped_durability(char, DURABILITY_LOSS_DUNGEON, db)
```

#### Při dokončení runu (boss výhra, status → "completed")
```python
await increment_guild_weekly(char.guild_id, "dungeons", 1, char.id, db)
await increment_weekly_board(char.id, "dungeons", 1, db)
await add_season_xp(char.id, "dungeon_complete", db)
await add_world_event_contribution("dungeon_clears", char.id, 1, db)
```

#### Při selhání runu (status → "failed")
```python
now = datetime.now(timezone.utc).replace(tzinfo=None)
if char.is_hardcore:
    await _trigger_permadeath(char, killed_by_enemy_name, dungeon_key, now, db)
```
Žádné guild/season hooks při selhání (stejné chování jako starý systém).

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
