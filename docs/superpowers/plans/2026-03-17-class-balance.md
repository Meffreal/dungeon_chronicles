# Class Balance Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Opravit nerovnováhu tříd — Warrior je OP, Mage/Ranger mají neimplementované mechaniky.

**Architecture:** Změny ve třech vrstvách: (1) konstanty v `combat_stats.py` a `talents.py`, (2) hardcoded hodnoty v `combat_engine.py`, (3) integrace chybějících tříd mechanik z `class_mechanics.py` do hlavní smyčky v `combat_engine.py`.

**Tech Stack:** Python, pytest, `backend/game/combat_stats.py`, `backend/game/combat_engine.py`, `backend/game/talents.py`, `backend/game/class_mechanics.py`

---

## Kontext a aktuální stav

**Již opraveno:** `CLASS_HP_MULT` je warrior=4, ranger=3, mage=2 ✅

**Zbývá opravit:**

| Problém | Soubor | Aktuálně | Cíl |
|---------|--------|----------|-----|
| Warrior armor cap příliš vysoký | `combat_stats.py:16` | 0.45 | **0.35** |
| Mage armor cap příliš nízký | `combat_stats.py:18` | 0.15 | **0.20** |
| Mage base weapon damage příliš nízký | `combat_stats.py:12` | 4 | **5** |
| Hunter's Mark první úder OP | `talents.py:68` | 0.75 | **0.50** |
| Rallying Cry heal příliš silný | `combat_engine.py:939` | 0.15 | **0.10** |
| Rallying Cry štít příliš silný | `combat_engine.py:946/950` | 0.20 | **0.15** |
| Dračí Šupiny 5pc regen příliš dlouhý | `combat_engine.py:450` | 30 kol | **10 kol** |
| Ranger chain_hit není integrován | `combat_engine.py` | TODO | implementovat |
| Ranger multi_hit není integrován | `combat_engine.py` | TODO | implementovat |
| Mage spell_burn není integrován | `combat_engine.py` | TODO | implementovat |
| Mage spirit_revenge není integrováno | `combat_engine.py` | TODO | implementovat |

---

## Kritické API poznámky (nutné pro všechny testy)

### `CombatantConfig` pole (dataclass, `combat_engine.py:256-278`)

```python
# Povinné poziční fieldy:
name: str
hp: int
weapon_dmg: int       # bonus_atk vybavené zbraně
armor_value: int      # součet bonus_def ze všech equipů
primary_stat: int     # STR pro warrior / DEX pro ranger / INT pro mage
secondary_a: int      # DEX pro warrior / STR pro ranger / STR pro mage
secondary_b: int      # INT pro warrior / INT pro ranger / DEX pro mage
# Volitelné:
luck: int = 5
level: int = 1
cls: str = ""
talents: list = []
talent_t2: str = ""
set_bonuses: dict = {}
# ... (boss/subclass polia)
```

**Neexistující pole:** `mp`, `atk`, `def_`, `spd` — engine je odvozuje interně.

### `ActiveStatus` pole (`combat_engine.py:282-289`)

```python
name: str
remaining_rounds: int
tick_value: float = 0.0    # damage/heal hodnota za tick — používá _process_status_ticks
absorb_pct: float = 0.0    # pro shield
atk_debuff_pct: float = 0.0
spd_debuff_pct: float = 0.0
```

### Burn status interně

`burn` existuje v `STATUS_DEFS` s `tick_dmg_pct=0.04` (4%). `_process_status_ticks` ale při zpracování tiku čte `status.tick_value` z instance (`combat_engine.py:744`), ne `tick_dmg_pct`. Správná cesta pro Spell Burn: appendovat `ActiveStatus(name="burn", remaining_rounds=3, tick_value=burn_dmg)` přímo — `tick_value` bude použito.

---

## Soubory

| Soubor | Akce | Co se mění |
|--------|------|------------|
| `backend/game/combat_stats.py` | Modify:15-18,9-13 | warrior armor cap, mage armor cap + weapon base |
| `backend/game/talents.py` | Modify:68,103-104 | Hunter's Mark bonus, Rallying Cry desc/effect |
| `backend/game/combat_engine.py` | Modify:446-451,939-951,1620-1649 | Dračí Šupiny, Rallying Cry, Ranger chain/multi, Mage burn/revenge |
| `backend/tests/test_combat_stats_helper.py` | Modify | aktualizovat assert pro nové hodnoty |
| `backend/tests/test_class_balance.py` | Create | nové testy pro balance + class mechaniky |

---

## Task 1: Numerické úpravy konstant (low-risk)

**Files:**
- Modify: `backend/game/combat_stats.py:9-19`
- Modify: `backend/game/talents.py:68`
- Modify: `backend/tests/test_combat_stats_helper.py:29,41`
- Create: `backend/tests/test_class_balance.py`

### Hodnoty

| Konstanta | Stará | Nová | Důvod |
|-----------|-------|------|-------|
| `CLASS_WEAPON_BASE["mage"]` | 4 | **5** | Mage base damage příliš penalizovaný bez equip |
| `CLASS_ARMOR_CAPS["warrior"]` | 0.45 | **0.35** | Iron Skin + 0.45 = 55% DR je OP |
| `CLASS_ARMOR_CAPS["mage"]` | 0.15 | **0.20** | Mage potřebuje aspoň drobnou odolnost |
| `hunters_mark first_strike_bonus_pct` | 0.75 | **0.50** | First Strike + Hunter's Mark = 2.45× → snížit na 2.10× |

- [ ] **Krok 1: Napiš selhávající test**

```python
# backend/tests/test_class_balance.py
import pytest
from game.combat_stats import CLASS_WEAPON_BASE, CLASS_ARMOR_CAPS
from game.talents import TALENT_TREE


def test_warrior_armor_cap_reduced():
    assert CLASS_ARMOR_CAPS["warrior"] == 0.35


def test_mage_armor_cap_raised():
    assert CLASS_ARMOR_CAPS["mage"] == 0.20


def test_mage_weapon_base_raised():
    assert CLASS_WEAPON_BASE["mage"] == 5


def test_hunters_mark_reduced():
    assert TALENT_TREE["hunters_mark"]["effect"]["first_strike_bonus_pct"] == 0.50
```

- [ ] **Krok 2: Spusť test a ověř, že selže**

```
cd backend && pytest tests/test_class_balance.py -v
```
Očekáváno: 4× FAIL

- [ ] **Krok 3: Uprav `combat_stats.py`**

```python
# combat_stats.py řádky 9-19
CLASS_WEAPON_BASE: dict[str, int] = {
    "warrior": 8,
    "ranger":  6,
    "mage":    5,   # bylo 4
}

CLASS_ARMOR_CAPS: dict[str, float] = {
    "warrior": 0.35,  # bylo 0.45
    "ranger":  0.25,
    "mage":    0.20,  # bylo 0.15
}
```

- [ ] **Krok 4: Uprav `talents.py` — Hunter's Mark**

```python
# talents.py řádek 68 — jen hodnota v effect
"hunters_mark": {
    "class": "ranger", "level_req": 30,
    "name": "Lovecká Značka", "emoji": "🎯",
    "desc": "První útok v souboji způsobí +50 % poškození.",
    "effect": {"first_strike_bonus_pct": 0.50},   # bylo 0.75
},
```

- [ ] **Krok 5: Aktualizuj existující testy v `test_combat_stats_helper.py`**

Existující testy assertují staré hodnoty — aktualizuj:

```python
# test_combat_stats_helper.py

def test_armor_cap_warrior():
    assert CLASS_ARMOR_CAPS["warrior"] == 0.35   # bylo 0.45

def test_armor_cap_mage():
    assert CLASS_ARMOR_CAPS["mage"] == 0.20      # bylo 0.15

def test_armor_pct_capped():
    pct = calc_armor_pct("warrior", armor_value=9000, enemy_level=1)
    assert pct == pytest.approx(0.35)            # bylo 0.45

def test_armor_pct_no_division_by_zero():
    pct = calc_armor_pct("mage", armor_value=50, enemy_level=0)
    assert pct <= 0.20   # bylo 0.15
```

- [ ] **Krok 6: Spusť testy a ověř, že projdou**

```
cd backend && pytest tests/test_class_balance.py tests/test_combat_stats_helper.py -v
```
Očekáváno: všechny PASS

- [ ] **Krok 7: Commit**

```bash
git add backend/game/combat_stats.py backend/game/talents.py \
        backend/tests/test_class_balance.py backend/tests/test_combat_stats_helper.py
git commit -m "balance: snížit warrior armor cap, zvýšit mage armor+weapon, snížit hunters_mark"
```

---

## Task 2: Rallying Cry a Dračí Šupiny (low-risk)

**Files:**
- Modify: `backend/game/combat_engine.py:446-451` (Dračí Šupiny regen duration)
- Modify: `backend/game/combat_engine.py:939-951` (Rallying Cry heal/shield hodnoty)
- Modify: `backend/game/talents.py:103-104` (Rallying Cry effect dict pro soulad s kódem)
- Modify: `backend/tests/test_class_balance.py` (přidat testy)

### Hodnoty

| Efekt | Stará | Nová | Důvod |
|-------|-------|------|-------|
| Rallying Cry `heal_pct` | 0.15 | **0.10** | Heal každé 4 kolo bez MP je OP |
| Rallying Cry `shield_pct` | 0.20 | **0.15** | Heal+shield kombinace je příliš silná |
| Dračí Šupiny `remaining_rounds` | 30 | **10** | 30 kol = 150% extra HP; 10 kol = 50% extra HP |

- [ ] **Krok 1: Napiš selhávající testy**

```python
# přidej do backend/tests/test_class_balance.py

from game.combat_engine import _FighterState, CombatantConfig
from dataclasses import field


def _make_warrior_with_regen() -> CombatantConfig:
    return CombatantConfig(
        name="TestWarrior", cls="warrior", level=30,
        hp=1000, weapon_dmg=20, armor_value=50,
        primary_stat=15, secondary_a=8, secondary_b=5,  # STR=15, DEX=8, INT=5
        luck=5,
        set_bonuses={"regen_every_round": True},
    )


def test_dragon_scales_regen_limited():
    """Dračí Šupiny 5pc regen musí trvat 10 kol, ne 30."""
    state = _FighterState(_make_warrior_with_regen())
    regen_status = next((s for s in state.statuses if s.name == "regen"), None)
    assert regen_status is not None, "Regen status musí existovat"
    assert regen_status.remaining_rounds == 10   # bylo 30


def test_rallying_cry_values_reduced():
    """Rallying Cry musí léčit 10% a mít štít 15%, ne 15%/20%."""
    from game.talents import TALENT_T2_TREE
    rc = next(t for t in TALENT_T2_TREE["warrior"] if t["key"] == "rallying_cry")
    assert rc["effect"]["heal_pct"] == 0.10
    assert rc["effect"]["shield_pct"] == 0.15
```

- [ ] **Krok 2: Spusť testy a ověř, že selžou**

```
cd backend && pytest tests/test_class_balance.py::test_dragon_scales_regen_limited tests/test_class_balance.py::test_rallying_cry_values_reduced -v
```
Očekáváno: 2× FAIL

- [ ] **Krok 3: Uprav `combat_engine.py` — Dračí Šupiny**

Na řádku ~447–451:
```python
if _sb.get("regen_every_round", False):
    # Dračí Šupiny 5pc: regen prvních 10 kol souboje (~50 % extra HP)
    self.statuses.append(ActiveStatus(
        name="regen",
        remaining_rounds=10,        # bylo 30
        tick_value=self.hp_max * STATUS_DEFS["regen"]["heal_pct"],
    ))
```

- [ ] **Krok 4: Uprav `combat_engine.py` — Rallying Cry**

Na řádku ~938–951:
```python
elif key == "rallying_cry":
    heal = max(1, int(attacker.hp_max * 0.10))   # bylo 0.15
    attacker.hp = min(attacker.hp_max, attacker.hp + heal)
    if attacker.has_status("shield"):
        s = attacker.get_status("shield")
        if s:
            s.remaining_rounds = 2
            s.absorb_pct = max(s.absorb_pct, 0.15)   # bylo 0.20
    else:
        attacker.statuses.append(ActiveStatus(
            name="shield", remaining_rounds=2,
            absorb_pct=0.15,                           # bylo 0.20
        ))
    txt = (f"  📯 {aname}: Bojový Pokřik! +{heal} HP léčení + štít 2 kola  "
           f"[{aname} HP: {attacker.hp}]")
```

- [ ] **Krok 5: Uprav `talents.py` — Rallying Cry effect dict (soulad s kódem)**

```python
# talents.py řádek ~103-104
{
    "key": "rallying_cry",
    "name": "Bojový Pokřik",
    "emoji": "📯",
    "level_req": 25,
    "desc": "Každé 4. kolo: obnova 10% max HP + aktivuje štít (blokuje 15% dmg 2 kola).",
    "effect": {"heal_pct": 0.10, "shield_pct": 0.15, "shield_rounds": 2},
},
```

- [ ] **Krok 6: Spusť testy**

```
cd backend && pytest tests/test_class_balance.py -v
```
Očekáváno: všechny PASS

- [ ] **Krok 7: Commit**

```bash
git add backend/game/combat_engine.py backend/game/talents.py \
        backend/tests/test_class_balance.py
git commit -m "balance: snížit rallying cry heal/shield, omezit dracj šupiny regen na 10 kol"
```

---

## Task 3: Ranger Chain Mechanics (medium risk)

**Files:**
- Modify: `backend/game/combat_engine.py` — přidat `_ranger_chain_or_multi_attack` + 4 místa v hlavní smyčce
- Modify: `backend/tests/test_class_balance.py`

### Co implementovat

Importy jsou již přítomny (`combat_engine.py:35-36`):
- `check_chain_hit` — 25% šance bonus hitu po každém primárním hitu
- `check_multi_hit_round` — každé 3. kolo: zaručený druhý útok (nahrazuje chain v daném kole)

### Strategie opačného útočníka

Chain/multi se aplikuje **pouze pro bojovníka jehož kolo to je** (útočník v daném tahu). Ne pro obou najednou.

- [ ] **Krok 1: Napiš selhávající testy**

```python
# přidej do backend/tests/test_class_balance.py

from game.combat_engine import simulate_unified_combat, CombatantConfig


def _ranger_vs_tank() -> tuple:
    """Ranger vs. tuhý tank — Ranger přežije 10+ kol."""
    ranger = CombatantConfig(
        name="Ranger", cls="ranger", level=20,
        hp=500, weapon_dmg=30, armor_value=20,
        primary_stat=16, secondary_a=9, secondary_b=8,  # DEX=16, STR=9, INT=8
        luck=5,
    )
    tank = CombatantConfig(
        name="Tank", cls="warrior", level=20,
        hp=5000, weapon_dmg=5, armor_value=60,
        primary_stat=15, secondary_a=8, secondary_b=5,
        luck=5,
    )
    return ranger, tank


def test_ranger_multi_hit_round_3():
    """Ranger musí útočit 2× v kole 3 (multi-hit kolo)."""
    ranger, tank = _ranger_vs_tank()
    result = simulate_unified_combat(ranger, tank, seed=99)
    attack_events_round3 = [
        e for e in result.events
        if e.round == 3
        and e.type in ("attack", "crit", "multi_hit")
        and e.actor == "Ranger"
    ]
    assert len(attack_events_round3) >= 2, (
        f"Ranger musí útočit 2× v kole 3 (multi-hit), "
        f"ale měl jen {len(attack_events_round3)} útokový event"
    )


def test_ranger_chain_hit_or_multi_fires_over_10_rounds():
    """Za 10 kol musí existovat aspoň jeden chain_hit nebo multi_hit event od Rangera."""
    ranger, tank = _ranger_vs_tank()
    result = simulate_unified_combat(ranger, tank, seed=42)
    chain_events = [
        e for e in result.events
        if e.type in ("chain_hit", "multi_hit") and e.actor == "Ranger"
    ]
    assert len(chain_events) > 0, (
        "Za 10+ kol musí Ranger mít aspoň jeden chain/multi-hit event"
    )
```

- [ ] **Krok 2: Spusť testy a ověř, že selžou**

```
cd backend && pytest tests/test_class_balance.py::test_ranger_multi_hit_round_3 tests/test_class_balance.py::test_ranger_chain_hit_or_multi_fires_over_10_rounds -v
```
Očekáváno: 2× FAIL

- [ ] **Krok 3: Přidej helper funkci do `combat_engine.py`**

Přidej těsně před funkci `simulate_unified_combat` (cca řádek 1532):

```python
def _ranger_chain_or_multi_attack(
    attacker: "_FighterState",
    defender: "_FighterState",
    round_num: int,
    events: list,
    log: list,
) -> int:
    """
    Ranger class mechanic: chain hit nebo multi-hit kolo.
    - Multi-hit: každé 3. kolo → zaručený druhý útok (priorita)
    - Chain hit: 25% šance po primárním hitu
    Vrací způsobený damage (0 pokud se neaktivoval).
    Voláno ihned po primárním _execute_attack pokud útočník je Ranger a přežívá.
    """
    if attacker.cfg.cls != "ranger":
        return 0
    if check_multi_hit_round(round_num):
        txt = f"  🏹 {attacker.cfg.name}: Multi-hit kolo! (kolo {round_num})"
        log.append(txt)
        events.append(CombatEvent(
            type="multi_hit", round=round_num,
            actor=attacker.cfg.name, target=defender.cfg.name,
            actor_hp=attacker.hp, target_hp=defender.hp,
            actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
            text=txt,
        ))
        return _execute_attack(attacker, defender, round_num, events, log)
    elif check_chain_hit(random.random()):
        txt = f"  🔗 {attacker.cfg.name}: Chain hit!"
        log.append(txt)
        events.append(CombatEvent(
            type="chain_hit", round=round_num,
            actor=attacker.cfg.name, target=defender.cfg.name,
            actor_hp=attacker.hp, target_hp=defender.hp,
            actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
            text=txt,
        ))
        return _execute_attack(attacker, defender, round_num, events, log)
    return 0
```

- [ ] **Krok 4: Integruj do hlavní smyčky v `simulate_unified_combat`**

Ve smyčce jsou 4 místa kde se volá `_execute_attack`. Po každém z nich přidej chain/multi check + break guard. Přesné umístění níže (čísla řádků jsou přibližná — hledej podle okolního kódu):

**Místo A** (`a_goes_first`, `attacker` útočí první, řádek ~1620):
```python
dmg = _execute_attack(attacker, defender, round_num, events, log)
total_dmg_by_attacker += dmg
if defender.hp <= 0:
    break
# ← PŘIDEJ:
total_dmg_by_attacker += _ranger_chain_or_multi_attack(attacker, defender, round_num, events, log)
if defender.hp <= 0:
    break
```

**Místo B** (`a_goes_first`, `defender` útočí druhý, řádek ~1629):
```python
_execute_attack(defender, attacker, round_num, events, log)
if attacker.hp <= 0:
    break
# ← PŘIDEJ:
_ranger_chain_or_multi_attack(defender, attacker, round_num, events, log)
if attacker.hp <= 0:
    break
```

**Místo C** (`else` větev, `defender` útočí první, řádek ~1638):
```python
_execute_attack(defender, attacker, round_num, events, log)
if attacker.hp <= 0:
    break
# ← PŘIDEJ:
_ranger_chain_or_multi_attack(defender, attacker, round_num, events, log)
if attacker.hp <= 0:
    break
```

**Místo D** (`else` větev, `attacker` útočí druhý, řádek ~1646):
```python
dmg = _execute_attack(attacker, defender, round_num, events, log)
total_dmg_by_attacker += dmg
if defender.hp <= 0:
    break
# ← PŘIDEJ:
total_dmg_by_attacker += _ranger_chain_or_multi_attack(attacker, defender, round_num, events, log)
if defender.hp <= 0:
    break
```

- [ ] **Krok 5: Spusť testy**

```
cd backend && pytest tests/test_class_balance.py -v
```
Očekáváno: všechny PASS

- [ ] **Krok 6: Spusť celou test suite**

```
cd backend && pytest tests/ -v --tb=short 2>&1 | tail -40
```
Očekáváno: žádné nové selhání

- [ ] **Krok 7: Commit**

```bash
git add backend/game/combat_engine.py backend/tests/test_class_balance.py
git commit -m "feat: implementovat ranger chain hit a multi-hit class mechanic"
```

---

## Task 4: Mage Spell Burn a Spirit Revenge (medium risk)

**Files:**
- Modify: `backend/game/combat_engine.py` — `_execute_attack` (spell burn) + `simulate_unified_combat` death handling (spirit revenge)
- Modify: `backend/tests/test_class_balance.py`

### Burn status — jak funguje interně

`burn` existuje v `STATUS_DEFS` s `tick_dmg_pct=0.04`. `_process_status_ticks` na řádku ~743–744 dělá:
```python
if "tick_dmg_pct" in sdef or "tick_dmg_flat" in sdef:
    dmg = max(1, int(status.tick_value))   # čte z instance, ne ze STATUS_DEFS
```
Takže `tick_value` na instanci `ActiveStatus` je autoritativní. Spell Burn nastaví `tick_value = calculate_spell_burn_damage(enemy_hp_max)` = 3% max HP (funkce z `class_mechanics.py`).

### Spirit Revenge — 4 break sites

V `simulate_unified_combat` existují 4 místa kde může bojovník zemřít. Správné mapování `dead_fighter` → `killer`:

| Místo | Větev | Kdo zemřel | Kdo zabil |
|-------|-------|-----------|----------|
| A | `a_goes_first`, attacker útočí → `defender.hp <= 0` | `defender` | `attacker` |
| B | `a_goes_first`, defender útočí → `attacker.hp <= 0` | `attacker` | `defender` |
| C | `else`, defender útočí → `attacker.hp <= 0` | `attacker` | `defender` |
| D | `else`, attacker útočí → `defender.hp <= 0` | `defender` | `attacker` |

- [ ] **Krok 1: Napiš selhávající testy**

```python
# přidej do backend/tests/test_class_balance.py


def _mage_vs_enemy(mage_hp: int = 400) -> tuple:
    mage = CombatantConfig(
        name="Mage", cls="mage", level=20,
        hp=mage_hp, weapon_dmg=25, armor_value=10,
        primary_stat=18, secondary_a=5, secondary_b=8,  # INT=18, STR=5, DEX=8
        luck=10,
    )
    enemy = CombatantConfig(
        name="Warrior", cls="warrior", level=20,
        hp=5000, weapon_dmg=5, armor_value=60,
        primary_stat=15, secondary_a=8, secondary_b=5,
        luck=5,
    )
    return mage, enemy


def test_mage_applies_spell_burn_after_attack():
    """Mage musí aplikovat burn DoT na nepřítele po každém útoku."""
    mage, enemy = _mage_vs_enemy()
    result = simulate_unified_combat(mage, enemy, seed=1)
    burn_events = [e for e in result.events if e.type == "burn"]
    assert len(burn_events) > 0, "Mage musí způsobit burn DoT (type='burn')"


def test_mage_spirit_revenge_on_round1_death():
    """Mage zabitý v kole 1 musí způsobit Spirit Revenge damage útočníkovi."""
    # Mage s 1 HP — umře určitě v kole 1
    mage_1hp = CombatantConfig(
        name="Mage", cls="mage", level=1,
        hp=1, weapon_dmg=5, armor_value=1,
        primary_stat=5, secondary_a=3, secondary_b=3,
        luck=5,
    )
    killer = CombatantConfig(
        name="Warrior", cls="warrior", level=20,
        hp=1000, weapon_dmg=50, armor_value=80,
        primary_stat=15, secondary_a=8, secondary_b=5,
        luck=5,
    )
    # Warrior jde první (vyšší SPD z DEX)
    result = simulate_unified_combat(killer, mage_1hp, seed=1)
    spirit_events = [e for e in result.events if e.type == "spirit_revenge"]
    assert len(spirit_events) > 0, (
        "Spirit Revenge event musí existovat pokud Mage zemře v kole 1"
    )
    # Spirit Revenge = 20% max HP útočníka = 200 HP z 1000
    sr = spirit_events[0]
    assert sr.damage == pytest.approx(200, abs=5), (
        f"Spirit Revenge musí způsobit 20% max HP = 200 dmg, ale byl {sr.damage}"
    )
```

- [ ] **Krok 2: Spusť testy a ověř, že selžou**

```
cd backend && pytest tests/test_class_balance.py::test_mage_applies_spell_burn_after_attack tests/test_class_balance.py::test_mage_spirit_revenge_on_round1_death -v
```
Očekáváno: 2× FAIL

- [ ] **Krok 3: Implementuj Spell Burn v `_execute_attack`**

Import `calculate_spell_burn_damage` je přítomen na řádku 38. V `_execute_attack`, za sekcí rage gain (~řádek 1495), přidej:

```python
# ── F.3 Mage: Spell Burn DoT ─────────────────────────────────────────────
if a_cls == "mage":
    burn_dmg = calculate_spell_burn_damage(defender.hp_max)
    existing_burn = defender.get_status("burn")
    if existing_burn:
        # Obnov délku a hodnotu (nepiluj nový stack)
        existing_burn.remaining_rounds = max(existing_burn.remaining_rounds, 3)
        existing_burn.tick_value = max(existing_burn.tick_value, float(burn_dmg))
    else:
        defender.statuses.append(ActiveStatus(
            name="burn",
            remaining_rounds=3,
            tick_value=float(burn_dmg),
        ))
    txt = f"  🔥 {a_name}: Kouzlo zapaluje {d_name}! ({burn_dmg} dmg/kolo po 3 kola)"
    events.append(CombatEvent(
        type="burn", round=round_num,
        actor=a_name, target=d_name,
        damage=burn_dmg,
        actor_hp=attacker.hp, target_hp=defender.hp,
        actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
        text=txt,
    ))
    log.append(txt)
```

- [ ] **Krok 4: Implementuj Spirit Revenge — přidej helper funkci**

Přidej těsně před `simulate_unified_combat` (vedle `_ranger_chain_or_multi_attack`):

```python
def _maybe_spirit_revenge(
    dead_fighter: "_FighterState",
    killer: "_FighterState",
    round_num: int,
    events: list,
    log: list,
) -> None:
    """
    Spirit Revenge: Mage zabitý v kole 1 způsobí 20% max HP damage killerovi.
    Args:
        dead_fighter: bojovník který právě zemřel
        killer: bojovník který zabil dead_fighter
        round_num: aktuální kolo (1-based)
    """
    if dead_fighter.cfg.cls != "mage":
        return
    if not check_spirit_revenge_trigger(round_num):
        return
    revenge_dmg = calculate_spirit_revenge_damage(killer.hp_max)
    killer.hp = max(0, killer.hp - revenge_dmg)
    txt = (
        f"  👻 {dead_fighter.cfg.name}: Spirit Revenge! "
        f"{killer.cfg.name} utrpí {revenge_dmg} dmg!  "
        f"[{killer.cfg.name} HP: {killer.hp}]"
    )
    events.append(CombatEvent(
        type="spirit_revenge", round=round_num,
        actor=dead_fighter.cfg.name, target=killer.cfg.name,
        damage=revenge_dmg,
        actor_hp=dead_fighter.hp, target_hp=killer.hp,
        actor_hp_max=dead_fighter.hp_max, target_hp_max=killer.hp_max,
        text=txt,
    ))
    log.append(txt)
```

- [ ] **Krok 5: Integruj Spirit Revenge do všech 4 break sites**

Pozor: mapování dead/killer se liší podle větve. Nahraď každý `if xxx.hp <= 0: break` tímto vzorem.

**Místo A** (větev `a_goes_first`, po útoku `attacker`, `defender` zemřel):
```python
if defender.hp <= 0:
    _maybe_spirit_revenge(defender, attacker, round_num, events, log)
    break
```

**Místo B** (větev `a_goes_first`, po útoku `defender`, `attacker` zemřel):
```python
if attacker.hp <= 0:
    _maybe_spirit_revenge(attacker, defender, round_num, events, log)
    break
```

**Místo C** (větev `else`, po útoku `defender`, `attacker` zemřel):
```python
if attacker.hp <= 0:
    _maybe_spirit_revenge(attacker, defender, round_num, events, log)
    break
```

**Místo D** (větev `else`, po útoku `attacker`, `defender` zemřel):
```python
if defender.hp <= 0:
    _maybe_spirit_revenge(defender, attacker, round_num, events, log)
    break
```

> **Poznámka k Berserker Burst:** Na řádcích 1618, 1627, 1636, 1644 jsou break conditions pro Berserker Burst. Spirit Revenge se tam **nepřidává** — burst není direct hit, spirit revenge se váže na normální attack hit. Přidávej pouze na 4 místech popsaných výše.

- [ ] **Krok 6: Spusť testy**

```
cd backend && pytest tests/test_class_balance.py -v
```
Očekáváno: všechny PASS

- [ ] **Krok 7: Spusť celou test suite**

```
cd backend && pytest tests/ -v --tb=short 2>&1 | tail -40
```
Očekáváno: žádné nové selhání

- [ ] **Krok 8: Commit**

```bash
git add backend/game/combat_engine.py backend/tests/test_class_balance.py
git commit -m "feat: implementovat mage spell burn a spirit revenge class mechanics"
```

---

## Shrnutí změn

Po dokončení všech 4 tasků budou tyto balance problémy vyřešeny:

| Problém | Stav |
|---------|------|
| Warrior armor cap 0.45 → 0.35 | ✅ Task 1 |
| Mage armor cap 0.15 → 0.20 | ✅ Task 1 |
| Mage base weapon 4 → 5 | ✅ Task 1 |
| Hunter's Mark 0.75 → 0.50 | ✅ Task 1 |
| Rallying Cry heal 0.15 → 0.10, štít 0.20 → 0.15 | ✅ Task 2 |
| Dračí Šupiny regen 30 kol → 10 kol | ✅ Task 2 |
| Ranger chain hit implementován | ✅ Task 3 |
| Ranger multi-hit kolo implementováno | ✅ Task 3 |
| Mage spell burn implementován | ✅ Task 4 |
| Mage spirit revenge implementováno | ✅ Task 4 |

**HP multiplikátory jsou již správné** (warrior=4, ranger=3, mage=2) — žádná změna.
