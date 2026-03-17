# Class Balance Patch 2 — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dokončit zbývající Warrior class mechaniky (rage stacks, berserk mode, stun imunita) a vyřešit potenciální přetrvávající nerovnováhy (Guardian subclass, Spell Burn cap).

**Architecture:** Všechny změny v `backend/game/combat_engine.py` — integrace funkcí z `class_mechanics.py` do `_FighterState` a `_execute_attack`. Žádné DB migrace.

**Tech Stack:** Python, pytest, `backend/game/combat_engine.py`, `backend/game/class_mechanics.py`

**Předpoklad:** Patch 1 (Tasks 1–4) je nasazen. Testy: 258 passing.

---

## Kontext — co už existuje v `class_mechanics.py`

Všechny funkce jsou připraveny, jen nejsou volány:

```python
# Warrior Rage
apply_rage_on_hit_received(rage_stacks, base_atk) -> (new_stacks, new_atk)
check_berserk_mode(current_hp, hp_max) -> {"is_berserk": bool, "atk_mult": float, "def_mult": float}
warrior_is_stun_immune() -> True

# Konstanty
RAGE_ATK_PER_HIT_RECEIVED = 0.03   # +3% base ATK za stack
RAGE_MAX_STACKS = 10                # max +30% ATK
RAGE_BERSERK_HP_THRESHOLD = 0.30   # aktivuje se při HP < 30%
RAGE_BERSERK_ATK_BONUS = 0.50      # +50% ATK v berserk módu
RAGE_BERSERK_DEF_PENALTY = -0.20   # -20% DEF v berserk módu
```

---

## Soubory

| Soubor | Akce | Co se mění |
|--------|------|------------|
| `backend/game/combat_engine.py` | Modify | `_FighterState.__init__` (rage_stacks, base_atk), `_execute_attack` (rage stacks + stun imunita), `effective_atk`/`effective_def` (berserk), add_status (stun guard) |
| `backend/tests/test_class_balance.py` | Modify | Přidat testy pro rage stacks, berserk, stun imunitu |

---

## Task 1: Warrior Rage Stacks per hit

**Proč:** Aktuálně Warrior dostává rage jen flat +15 za útok / +25 za přijatý hit (starý systém). Nový systém přidává +3% base ATK za každý přijatý hit (max 10 stacků = +30% ATK). Oba systémy musí koexistovat — flat rage pro Berserker Burst (100 rage → 2× DMG), rage stacks pro per-hit ATK bonus.

### Změny v `_FighterState.__init__`

Za existující `self.rage: int = 0` přidej:
```python
# F.1 Warrior: Rage Stacks systém (per-hit ATK bonus)
self.rage_stacks: int = 0          # 0–10; každý přijatý hit +1 stack (+3% ATK)
self.base_atk: float = self.effective_atk()  # ATK bez rage bonus (pro výpočet)
```

### Změny v `_execute_attack`

Za existující rage gain block (~řádek 1494):
```python
# F.1 Warrior: Rage gain (flat — pro Berserker Burst)
if a_cls == "warrior":
    attacker.rage = min(100, attacker.rage + 15)
if defender.cfg.cls == "warrior":
    defender.rage = min(100, defender.rage + 25)
```

Přidej za tento blok:
```python
# F.1 Warrior: Rage Stacks per hit (+3% base ATK za stack, max 10)
if defender.cfg.cls == "warrior":
    new_stacks, new_atk = apply_rage_on_hit_received(
        defender.rage_stacks, int(defender.base_atk)
    )
    defender.rage_stacks = new_stacks
    defender.base_atk = float(new_atk)
```

### Jak `rage_stacks` ovlivní damage

`effective_atk()` v `_FighterState` musí číst `base_atk` pokud je Warrior a rage_stacks > 0. Uprav `effective_atk()`:

```python
def effective_atk(self) -> float:
    # Warrior rage stacks: base_atk je aktualizován v apply_rage_on_hit_received
    # a zahrnuje stack bonus — použij ho pokud existuje
    base = self.base_atk if (self.cfg.cls == "warrior" and self.rage_stacks > 0) else self.base_dmg
    # ... zbytek existující logiky (dmg_mult, berserk atd.)
```

### Testy

```python
def test_warrior_rage_stacks_increase_on_hit():
    """Warrior musí získat rage stack při přijatém hitu a ATK musí růst."""
    from game.combat_engine import _FighterState, CombatantConfig
    warrior = _FighterState(CombatantConfig(
        name="W", cls="warrior", level=10,
        hp=500, weapon_dmg=20, armor_value=30,
        primary_stat=15, secondary_a=8, secondary_b=5, luck=5,
    ))
    initial_atk = warrior.base_atk
    # Simuluj přijatý hit
    from game.class_mechanics import apply_rage_on_hit_received
    warrior.rage_stacks, warrior.base_atk = apply_rage_on_hit_received(
        warrior.rage_stacks, int(initial_atk)
    )
    assert warrior.rage_stacks == 1
    assert warrior.base_atk > initial_atk

def test_warrior_rage_stacks_capped_at_10():
    """Rage stacks nesmí překročit 10."""
    from game.combat_engine import _FighterState, CombatantConfig
    from game.class_mechanics import apply_rage_on_hit_received
    warrior = _FighterState(CombatantConfig(
        name="W", cls="warrior", level=10,
        hp=500, weapon_dmg=20, armor_value=30,
        primary_stat=15, secondary_a=8, secondary_b=5, luck=5,
    ))
    for _ in range(15):  # 15 hitů → max 10 stacků
        warrior.rage_stacks, warrior.base_atk = apply_rage_on_hit_received(
            warrior.rage_stacks, int(warrior.base_atk)
        )
    assert warrior.rage_stacks == 10
```

- [ ] Přidat `rage_stacks` a `base_atk` do `_FighterState.__init__`
- [ ] Přidat rage stacks update do `_execute_attack` za rage gain blok
- [ ] Upravit `effective_atk()` aby použilo `base_atk` pro Warriora s rage stacks
- [ ] Napsat testy a ověřit: `cd backend && pytest tests/test_class_balance.py -v`
- [ ] Commit: `git commit -m "feat: implementovat warrior rage stacks per-hit ATK bonus"`

---

## Task 2: Warrior Berserk Mode (HP < 30%)

**Proč:** Při HP pod 30% má Warrior vstoupit do Berserk Mode (+50% ATK, -20% DEF). Tato mechanika je navržena ale nikdy nebyla volána.

**Jak implementovat:** `check_berserk_mode` je pure function — volat při každém výpočtu `effective_atk()` a `effective_def()` pro Warriora.

### Změny v `effective_atk()`

```python
def effective_atk(self) -> float:
    base = self.base_atk if (self.cfg.cls == "warrior" and self.rage_stacks > 0) else self.base_dmg
    mult = self.dmg_mult
    # Berserk Mode
    if self.cfg.cls == "warrior":
        berserk = check_berserk_mode(self.hp, self.hp_max)
        if berserk["is_berserk"]:
            mult *= berserk["atk_mult"]
    # ... enrage bonus atd.
    return base * mult * (1.0 + self.dmg_bonus_pct)
```

### Změny v `effective_def()`

```python
def effective_def(self) -> float:
    base_armor = self.armor_value * self.armor_mult
    # Berserk Mode: -20% DEF
    if self.cfg.cls == "warrior":
        berserk = check_berserk_mode(self.hp, self.hp_max)
        if berserk["is_berserk"]:
            base_armor *= (1.0 + berserk["def_mult"])  # def_mult je -0.20
    return base_armor
```

### Testy

```python
def test_warrior_berserk_mode_activates_below_30pct_hp():
    """Warrior v berserk mode musí mít vyšší ATK a nižší DEF."""
    from game.combat_engine import _FighterState, CombatantConfig
    warrior = _FighterState(CombatantConfig(
        name="W", cls="warrior", level=10,
        hp=500, weapon_dmg=20, armor_value=30,
        primary_stat=15, secondary_a=8, secondary_b=5, luck=5,
    ))
    normal_atk = warrior.effective_atk()
    normal_def = warrior.effective_def()
    # Sníž HP pod 30%
    warrior.hp = int(warrior.hp_max * 0.25)
    berserk_atk = warrior.effective_atk()
    berserk_def = warrior.effective_def()
    assert berserk_atk > normal_atk, "Berserk ATK musí být vyšší"
    assert berserk_def < normal_def, "Berserk DEF musí být nižší"

def test_warrior_berserk_mode_not_active_above_30pct():
    """Berserk mode nesmí být aktivní při HP >= 30%."""
    from game.combat_engine import _FighterState, CombatantConfig
    warrior = _FighterState(CombatantConfig(
        name="W", cls="warrior", level=10,
        hp=500, weapon_dmg=20, armor_value=30,
        primary_stat=15, secondary_a=8, secondary_b=5, luck=5,
    ))
    warrior.hp = int(warrior.hp_max * 0.50)  # 50% HP
    normal_atk = warrior.effective_atk()
    warrior.hp = int(warrior.hp_max * 0.90)  # 90% HP
    full_atk = warrior.effective_atk()
    assert normal_atk == pytest.approx(full_atk, rel=0.01), "Bez berserk musí být ATK stejné"
```

- [ ] Upravit `effective_atk()` pro berserk ATK bonus
- [ ] Upravit `effective_def()` pro berserk DEF penalty
- [ ] Napsat testy a ověřit
- [ ] Commit: `git commit -m "feat: implementovat warrior berserk mode pri HP < 30%"`

---

## Task 3: Warrior Stun Imunita

**Proč:** Warrior má být imunní na stun — `warrior_is_stun_immune()` vrací `True` ale nikdy se nevolá. Stun se Warriorovi normálně aplikuje.

**Kde v kódu:** Stun se aplikuje přes `add_status("stun", ...)` nebo `attacker.statuses.append(ActiveStatus(name="stun", ...))`. Warrior guard musí blokovat stun při aplikaci.

### Kde hledat stun aplikaci

```bash
grep -n "stun" backend/game/combat_engine.py
```

Najdi všechna místa kde se stun přidává — typicky `add_status("stun")` nebo `ActiveStatus(name="stun")`.

### Změna v `add_status` nebo přímo v místě aplikace

Pokud existuje centrální `add_status` metoda na `_FighterState`, přidej guard:
```python
def add_status(self, name: str, **kwargs):
    # Warrior je imunní na stun
    if name == "stun" and self.cfg.cls == "warrior":
        return
    # ... zbytek
```

Pokud stun se přidává přímo přes `statuses.append`, přidej guard na každém místě:
```python
if not (attacker.cfg.cls == "warrior" and status_name == "stun"):
    defender.statuses.append(ActiveStatus(name="stun", ...))
```

### Test

```python
def test_warrior_is_immune_to_stun():
    """Warrior nesmí dostat stun status."""
    from game.combat_engine import _FighterState, CombatantConfig
    warrior = _FighterState(CombatantConfig(
        name="W", cls="warrior", level=10,
        hp=500, weapon_dmg=20, armor_value=30,
        primary_stat=15, secondary_a=8, secondary_b=5, luck=5,
    ))
    # Pokus o přidání stun
    from game.combat_engine import ActiveStatus
    warrior.add_status("stun", remaining_rounds=2)  # nebo odpovídající API
    stun = next((s for s in warrior.statuses if s.name == "stun"), None)
    assert stun is None, "Warrior nesmí mít stun status"
```

- [ ] Najít všechna místa aplikace stun v `combat_engine.py`
- [ ] Přidat warrior stun guard
- [ ] Napsat test a ověřit
- [ ] Commit: `git commit -m "feat: implementovat warrior stun imunita"`

---

## Task 4: Guardian Subclass — analýza a případný nerf

**Proč:** Guardian (+35% armor mult, +20% HP) v kombinaci s armor cap 0.35 (po patch 1) a Iron Skin (-20% DR) je stále velmi silný. Potřebujeme zjistit, zda je to problém v praxi.

**Toto není implementační task** — je to analýza + rozhodnutí.

### Co prověřit

1. Spusť testovací souboj `Guardian Warrior (level 30) vs Mage (level 30)` a spočítej průměrný počet kol
2. Pokud souboj trvá 25+ kol → Guardian je stále OP
3. Pokud 15–20 kol → přijatelné

### Potenciální úprava (jen pokud analýza potvrdí problém)

```python
# models/subclass.py — Guardian stat_mults
"guardian": {
    "stat_mults": {
        "dmg_mult":   0.90,   # -10% DMG (beze změny)
        "armor_mult": 1.25,   # bylo 1.35 → 1.25
        "hp_mult":    1.15,   # bylo 1.20 → 1.15
    }
}
```

- [ ] Spustit analytický souboj (lze přes pytest nebo manuálně)
- [ ] Rozhodnout zda nerf je nutný
- [ ] Pokud ano: upravit `models/subclass.py` a commitovat

---

## Task 5: Spell Burn Stack Cap — monitoring

**Proč:** Mage Spell Burn se refreshuje při každém útoku (3 kola). V soubojích 20+ kol Mage permanentně udržuje burn na nepříteli. Je potřeba sledovat zda DoT damage v dlouhých soubojích není příliš silný.

**Toto je monitoring task**, ne implementace.

### Co sledovat po nasazení Patch 1

- Průměrná délka PvP souboje (počet kol)
- Procento soubojů kde Mage vyhraje přes DoT (ne přímý damage)
- Průměrný DoT damage vs. direct damage Mage per souboj

### Potenciální úprava (jen pokud data potvrdí problém)

Omezit burn na max 1 refresh za souboj, nebo snížit duration:
```python
# combat_engine.py — v Spell Burn bloku
existing_burn.remaining_rounds = min(
    existing_burn.remaining_rounds + 3,
    6   # max 6 kol celkem (2 refreshe)
)
```

Nebo snížit `MAGE_SPELL_BURN_PCT` z 0.03 na 0.02 v `class_mechanics.py`.

- [ ] Sledovat PvP statistiky 1–2 týdny po Patch 1
- [ ] Pokud Mage win rate > 45% v arene → zvažit cap
- [ ] Rozhodnutí a implementace dle dat

---

## Priorita

| Task | Priorita | Důvod |
|------|----------|-------|
| Task 3 — Stun imunita | **Vysoká** | Jednoduchá změna, jasný design intent |
| Task 1 — Rage Stacks | **Střední** | Zesiluje Warriora ale je to design, ne bug |
| Task 2 — Berserk Mode | **Střední** | Závisí na Task 1 (sdílí `base_atk`) |
| Task 4 — Guardian analýza | **Nízká** | Čekat na playtest data z Patch 1 |
| Task 5 — Spell Burn monitoring | **Nízká** | Čekat na PvP statistiky |

> **Poznámka:** Tasks 1+2 zesilují Warriora, který byl právě patch 1 oslaben. Implementovat až po několika dnech playtestů — pokud Warrior bude slabý, přidáme rage stacks jako buff. Pokud bude stále silný, počkáme déle.
