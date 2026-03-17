"""
game/combat_engine.py — Unifikovaný combat engine pro PvP, PvE, Bossy i Dungeony.

Architektura:
- Jeden engine pro VŠECHNY typy soubojů
- Server-autoritativní deterministický výpočet
- Žádná náhoda na frontendu
- Strukturovaný JSON event log (CombatEvent)
- Zpětně kompatibilní text log (pro stávající systémy)
- Status efekty: bleed, poison, stun, shield, burn, weaken, slow
- Multi-phase boss podpora (fáze při % HP)
- Přesné formule bez arbitrárních oprav

Proč unified engine:
- DRY — žádná duplikace damage formul
- Konzistentní feel (PvP i PvE se hrají stejně)
- Snadná extensibilita (raid, guild war, spectator mode)
- Testovatelnost — jeden celek místo dvou různých implementací
"""

import random
import math
from dataclasses import dataclass, field
from typing import Optional

# ── HC Gauntlet: asymetrické třídní mechaniky ──────────────────────────────────
# F.1 Rage (Warrior), F.2 Chain (Ranger), F.3 First Strike (Mage)
# Logika je čistě izolována v game/class_mechanics.py.
# _FighterState používá objektový pattern (ne dict) — plná integrace proběhne
# při dalším combat refactoru. Viz CLASS_MECHANICS_TODO níže.
from game.class_mechanics import (
    apply_rage_on_hit_received,
    check_berserk_mode,
    warrior_is_stun_immune,
    check_chain_hit,
    check_multi_hit_round,
    ranger_first_round_first_strike,
    calculate_spell_burn_damage,
    check_spirit_revenge_trigger,
    calculate_spirit_revenge_damage,
    get_class_mechanics,
)
# CLASS_MECHANICS_TODO: integrace do _FighterState a _execute_attack:
#   Warrior: přidat rage_stacks + base_atk atributy; volat apply_rage_on_hit_received()
#            po každém přijatém hitu; check_berserk_mode() v effective_atk/effective_def;
#            warrior_is_stun_immune() v add_status("stun").
#   Ranger:  check_chain_hit(random.random()) po primárním hitu → bonus _execute_attack;
#            check_multi_hit_round(round_num) → druhý útok bez chain;
#            ranger_first_round_first_strike() → přeskočit SPD sort v kole 1.
#   Mage:    calculate_spell_burn_damage(enemy.hp_max) → add_status("burn") po každém útoku;
#            check_spirit_revenge_trigger(round) → calculate_spirit_revenge_damage() při smrti.

# ── Konstanty ──────────────────────────────────────────────────────────────────
MAX_ROUNDS_DEFAULT    = 30
CRIT_DAMAGE_MULT      = 1.75   # damage × 1.75 při critu
DAMAGE_VARIANCE       = 0.15   # ±15% rozptyl
BASE_CRIT_CHANCE      = 0.05   # 5% baseline
CRIT_PER_LUCK         = 0.01   # +1% za bod luck
MAX_CRIT_CHANCE       = 0.40   # max 40%
ABILITY_TRIGGER_PROB  = 0.40   # 40% šance triggernout specialní ability


# ── Combat strategie ───────────────────────────────────────────────────────────
# Hráč volí strategii před bojem — ovlivní ATK/DEF/SPD/MP multiplikátory.
# ── Attribute soft caps ────────────────────────────────────────────────────────
# Zóna 1 (0–50): 100% return | Zóna 2 (51–150): 70% | Zóna 3 (151+): 30%
# Aplikuje se na ATK, DEF, SPD, LUCK v _FighterState (raw hodnoty v DB zůstávají).
SOFT_CAP_ZONE1_END   = 50
SOFT_CAP_ZONE2_END   = 150
SOFT_CAP_ZONE1_RATE  = 1.00
SOFT_CAP_ZONE2_RATE  = 0.70
SOFT_CAP_ZONE3_RATE  = 0.30

def soft_cap_stat(value: int) -> int:
    """Aplikuje diminishing returns na herní stat."""
    if value <= SOFT_CAP_ZONE1_END:
        return value
    elif value <= SOFT_CAP_ZONE2_END:
        zone1 = SOFT_CAP_ZONE1_END
        return zone1 + int((value - zone1) * SOFT_CAP_ZONE2_RATE)
    else:
        zone1  = SOFT_CAP_ZONE1_END
        zone12 = int((SOFT_CAP_ZONE2_END - zone1) * SOFT_CAP_ZONE2_RATE)  # = 70
        return zone1 + zone12 + int((value - SOFT_CAP_ZONE2_END) * SOFT_CAP_ZONE3_RATE)



# ── Status efekty ──────────────────────────────────────────────────────────────
STATUS_DEFS = {
    "bleed": {
        "name": "Krvácení", "emoji": "🩸",
        "rounds": 3, "tick_dmg_pct": 0.06,   # 6% max HP za kolo
        "description": "Způsobuje krvácení — ztráta HP každé kolo.",
    },
    "poison": {
        "name": "Jed", "emoji": "☠️",
        "rounds": 4, "tick_dmg_flat": 1.0,   # multiplier na ATK útočníka
        "description": "Jedovatá rána — postupné otravování.",
    },
    "stun": {
        "name": "Omráčení", "emoji": "⭐",
        "rounds": 1, "skip_turn": True,
        "description": "Omráčen — přeskočí příští tah.",
    },
    "shield": {
        "name": "Štít", "emoji": "🛡️",
        "rounds": 3, "absorb_pct": 0.30,     # absorbuje 30% každého útoku
        "description": "Magický štít — absorbuje část poškození.",
    },
    "burn": {
        "name": "Hoření", "emoji": "🔥",
        "rounds": 3, "tick_dmg_pct": 0.04,   # 4% max HP za kolo
        "description": "Plameny spalují — hoří každé kolo.",
    },
    "weaken": {
        "name": "Oslabení", "emoji": "💔",
        "rounds": 2, "atk_debuff_pct": 0.30, # -30% ATK
        "description": "Oslaben — snížené poškození.",
    },
    "regen": {
        "name": "Regenerace", "emoji": "💚",
        "rounds": 3, "heal_pct": 0.05,       # léčí 5% max HP za kolo
        "description": "Regenerace — léčí HP každé kolo.",
    },
}


# ── Schopnosti tříd ────────────────────────────────────────────────────────────
CLASS_ABILITIES = {
    "warrior": {
        "name": "Otřes Zemí", "emoji": "🪨", "mp_cost_pct": 0.15,  # 15 % MP
        "desc": "Mocný úder, který probíjí brnění.",
        "type": "armor_pierce",
        "dmg_mult": 1.7, "def_ignore_pct": 0.7,  # ignoruje 70% DEF
        "apply_status": None,
    },
    "mage": {
        "name": "Ohnivá Koule", "emoji": "🔥", "mp_cost_pct": 0.30,  # 30 % MP
        "desc": "Ohnivé kouzlo s přidaným efektem hoření.",
        "type": "magic",
        "dmg_mult": 2.0, "def_ignore_pct": 1.0,  # ignoruje DEF úplně
        "apply_status": "burn",                     # aplikuje hoření
    },
    "ranger": {
        "name": "Přesný Zásah", "emoji": "🎯", "mp_cost_pct": 0.17,  # 17 % MP
        "desc": "Precizní výstřel — vždy kritický zásah.",
        "type": "guaranteed_crit",
        "dmg_mult": 1.3, "def_ignore_pct": 0.0,
        "apply_status": None,
    },
}

# ── Schopnosti subclassů (nahrazují class ability) ────────────────────────────
SUBCLASS_ABILITIES: dict[str, dict] = {
    "berserker": {
        "name": "Zuřivý Náraz", "emoji": "🔴", "mp_cost_pct": 0.20,
        "desc": "Drtivý úder probíjející brnění — útočník však přijme část způsobeného poškození.",
        "type": "armor_pierce",
        "dmg_mult": 2.2, "def_ignore_pct": 0.80,
        "apply_status": None,
        "self_dmg_pct": 0.08,   # berserk recoil: 8 % způsobeného dmg
    },
    "guardian": {
        "name": "Železná Pevnost", "emoji": "🛡️", "mp_cost_pct": 0.15,
        "desc": "Zaujme pevnou pozici a obklopí se štítem. Útok oslabený, obrana posílena.",
        "type": "armor_pierce",
        "dmg_mult": 0.8, "def_ignore_pct": 0.0,
        "apply_status": None,
        "apply_status_self": "shield",  # štít na sebe
    },
    "elementalist": {
        "name": "Armageddon", "emoji": "☄️", "mp_cost_pct": 0.40,
        "desc": "Kombinace živlů decimuje nepřítele. Způsobuje hoření.",
        "type": "magic",
        "dmg_mult": 2.5, "def_ignore_pct": 1.0,
        "apply_status": "burn",
        "extra_statuses": [],
    },
    "necromancer": {
        "name": "Mor Nemrtvých", "emoji": "☠️", "mp_cost_pct": 0.25,
        "desc": "Obklopí nepřítele temnou magií — jed, krvácení a oslabení najednou.",
        "type": "magic",
        "dmg_mult": 0.9, "def_ignore_pct": 1.0,
        "apply_status": "poison",
        "extra_statuses": ["bleed", "weaken"],
    },
    "sharpshooter": {
        "name": "Smrtící Zásah", "emoji": "💥", "mp_cost_pct": 0.22,
        "desc": "Přesný výstřel na životně důležité místo. Vždy kritický zásah.",
        "type": "guaranteed_crit",
        "dmg_mult": 1.8, "def_ignore_pct": 0.0,
        "apply_status": None,
    },
    "shadowblade": {
        "name": "Stínový Skok", "emoji": "🌑", "mp_cost_pct": 0.18,
        "desc": "Teleportuje se a útočí ze stínu dvěma rychlými ranami. Zanechává krvácení.",
        "type": "multi_hit",
        "dmg_mult": 0.85, "def_ignore_pct": 0.20,
        "hit_count": 2,
        "apply_status": "bleed",
    },
}

# Boss speciální schopnosti (triggery při určitém % HP nebo každé N kolo)
BOSS_SPECIAL_ABILITIES = {
    "bone_shatter": {
        "name": "Lom Kostí", "emoji": "💀",
        "apply_status": "bleed",
        "trigger": "on_hit",  # triggerne při normálním útoku s šancí
        "trigger_chance": 0.35,
    },
    "venomous_bite": {
        "name": "Jedovatý Kous", "emoji": "🐍",
        "apply_status": "poison",
        "trigger": "on_hit",
        "trigger_chance": 0.40,
    },
    "soul_drain": {
        "name": "Drénování Duše", "emoji": "💜",
        "apply_status": "weaken",
        "trigger": "every_n_rounds", "trigger_rounds": 3,
    },
    "fire_breath": {
        "name": "Dech Ohně", "emoji": "🔥",
        "apply_status": "burn",
        "trigger": "every_n_rounds", "trigger_rounds": 4,
    },
    "chaos_bolt": {
        "name": "Bolt Chaosu", "emoji": "⚡",
        "apply_status": "stun",
        "trigger": "on_hit",
        "trigger_chance": 0.20,
    },
    "enrage": {
        "name": "Zuřivost", "emoji": "😡",
        "dmg_bonus": 0.50,   # +50% DMG
        "trigger": "phase_change",
    },
}


# ── Datové třídy ────────────────────────────────────────────────────────────────
@dataclass
class BossPhase:
    """Definice fáze bosse. Triggerne se při určitém % HP."""
    phase_num:        int
    trigger_hp_pct:   float       # triggeruje při hp <= X% max HP
    message:          str
    stat_multipliers: dict = field(default_factory=dict)   # {"atk": 1.5, "spd": 1.2}
    apply_status_to_player: Optional[str] = None           # stav aplikovaný na hráče
    new_ability:      Optional[str] = None                 # přidá boss specialní ability
    heal_pct:         float = 0.0                          # boss se léčí o X% max HP


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


@dataclass
class ActiveStatus:
    """Aktivní status efekt na bojovníkovi."""
    name:             str
    remaining_rounds: int
    tick_value:       float = 0.0   # damage/heal hodnota za tick
    absorb_pct:       float = 0.0   # % absorpce (pro shield)
    atk_debuff_pct:   float = 0.0   # % debuff na ATK
    spd_debuff_pct:   float = 0.0   # % debuff na SPD


@dataclass
class CombatEvent:
    """
    Jeden event v combat logu. Frontendová animace je řízena těmito eventy.
    Každý event odpovídá jedné vizuální akci.
    """
    type:          str          # viz EVENT_TYPES
    round:         int
    actor:         str          # jméno útočníka
    target:        str          # jméno obránce
    damage:        int    = 0
    heal:          int    = 0
    actor_hp:      int    = 0   # HP útočníka PO eventu
    target_hp:     int    = 0   # HP cíle PO eventu
    actor_hp_max:  int    = 0
    target_hp_max: int    = 0
    is_crit:       bool   = False
    ability_name:  str    = ""  # název použité schopnosti
    ability_emoji: str    = ""
    status_name:   str    = ""  # název aplikovaného/expirovaného statusu
    status_emoji:  str    = ""
    phase_num:     int    = 0   # číslo boss fáze
    phase_msg:     str    = ""  # zpráva při změně fáze
    text:          str    = ""  # human-readable popis pro text log

# Typy eventů:
EVENT_ATTACK        = "attack"          # normální útok
EVENT_CRIT          = "crit"            # kritický útok
EVENT_ABILITY       = "ability"         # class ability
EVENT_STATUS_APPLY  = "status_apply"    # aplikace status efektu
EVENT_STATUS_TICK   = "status_tick"     # tick status efektu
EVENT_STATUS_EXPIRE = "status_expire"   # expirování status efektu
EVENT_PHASE_CHANGE  = "phase_change"    # změna fáze bosse
EVENT_HEAL          = "heal"            # léčení
EVENT_ROUND_START   = "round_start"     # začátek kola
EVENT_COMBAT_END    = "combat_end"      # konec souboje
EVENT_INTERACTION   = "interaction"     # status synergy interakce


@dataclass
class CombatResult:
    """Výsledek combat simulace."""
    winner:               str          # "attacker" nebo "defender"
    rounds:               int
    events:               list         # list[CombatEvent] — strukturovaný JSON log
    log:                  list         # list[str] — text log (backward compat)
    attacker_hp_remaining: int
    defender_hp_remaining: int
    attacker_hp_max:      int
    defender_hp_max:      int
    # Výsledky pro reward kalkulaci
    attacker_won:         bool = True
    total_damage_dealt:   int  = 0    # celkový damage útočníka (pro boss contribution)


# ── Interní stav bojovníka ─────────────────────────────────────────────────────
class _FighterState:
    """Mutable stav bojovníka během souboje."""

    def __init__(self, cfg: CombatantConfig):
        self.cfg     = cfg
        self.hp      = cfg.hp
        self.hp_max  = cfg.hp_max_override if cfg.hp_max_override else cfg.hp
        from game.combat_stats import calc_damage_components
        self.luck    = int(soft_cap_stat(cfg.luck))
        self.level   = cfg.level
        # Vypocitej base damage z nove formule
        # primary_stat odpovida primarnimu statu tridy (STR/DEX/INT)
        # secondary_a = DEX(warrior)/STR(ranger)/STR(mage)
        # secondary_b = INT(warrior)/INT(ranger)/DEX(mage)
        if cfg.cls == "warrior":
            _str, _dex, _int = cfg.primary_stat, cfg.secondary_a, cfg.secondary_b
        elif cfg.cls == "ranger":
            _dex, _str, _int = cfg.primary_stat, cfg.secondary_a, cfg.secondary_b
        elif cfg.cls == "mage":
            _int, _str, _dex = cfg.primary_stat, cfg.secondary_a, cfg.secondary_b
        else:
            _str, _dex, _int = cfg.primary_stat, cfg.secondary_a, cfg.secondary_b
        _base_dmg, _, _ = calc_damage_components(
            cfg.cls or "",
            str_=_str, dex=_dex, int_=_int,
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
        # SPD derived from DEX (for dodge/initiative calculations)
        self.spd = int(soft_cap_stat(_dex))
        # Ranger: first strike flag
        self.has_class_first_strike = (cfg.cls == "ranger")
        self.statuses: list[ActiveStatus] = []
        # Boss specifické
        self.current_phase    = 0
        self.triggered_phases: set = set()
        self.active_specials:  list = list(cfg.special_abilities)
        self.dmg_bonus_pct    = 0.0   # extra % dmg bonus (enrage atd.)

        # ── Talent pasivní efekty ──────────────────────────────────────────────
        _talents = set(cfg.talents or [])
        # Eagle Eye: +8 LUCK (přepočítej po soft_cap)
        if "eagle_eye" in _talents:
            self.luck = soft_cap_stat(cfg.luck + 8)
        # Fortitude: +15 % HP (aplikuje se na combat HP, character sheet HP
        #            je již přepočítán v recalculate_stats)
        if "fortitude" in _talents:
            self.hp     = int(self.hp     * 1.15)
            self.hp_max = int(self.hp_max * 1.15)
        # Mana Surge: +15 % dmg_mult
        if "mana_surge" in _talents:
            self.dmg_mult *= 1.15
        # Combat modifikátory — uloženy pro _execute_attack
        self.crit_dmg_bonus_pct    = 0.25 if "battle_rage"   in _talents else 0.0
        self.dmg_reduction_pct     = 0.20 if "iron_skin"      in _talents else 0.0
        self.ability_dmg_bonus_pct = 0.20 if "arcane_focus"   in _talents else 0.0
        self.spell_echo_chance     = 0.25 if "spell_echo"     in _talents else 0.0
        self.crit_bonus_pct        = 0.10 if "evasion"        in _talents else 0.0
        self.hunters_mark_active   = "hunters_mark" in _talents

        # ── Talent T2 (aktivní schopnost) ─────────────────────────────────────
        self.talent_t2 = cfg.talent_t2 or ""
        self.t2_def_reduction = 0.0   # Mark for Death: akumulovaná redukce DEF nepřítele

        # ── F.1 Warrior: Rage systém ───────────────────────────────────────────
        # rage: 0–100; při 100 aktivuje Berserker Burst (double dmg + stun) a resetuje se
        self.rage: int = 0

        # ── F.2 Mage: Spell Chain systém ──────────────────────────────────────
        # Sleduje typ posledního kouzla pro chain combo/penalty (+20%/-10% dmg)
        self.last_spell_type: Optional[str] = None
        # Cyklus typů kouzel pro AI mage (vždy střídá → vždy combo bonus)
        _SPELL_CYCLE = ["Fire", "Ice", "Arcane", "Void"]
        self._spell_cycle_index: int = 0
        self._spell_cycle: list = _SPELL_CYCLE

        # ── Set bonusy (combat efekty) ────────────────────────────────────────
        # Stat bonusy (HP, LUCK) jsou již zapečeny v CombatantConfig hodnotách.
        # Zde aplikujeme pouze efekty ovlivňující průběh souboje.
        self.first_strike = False   # Přízračný Chodec 5pc: zaručený první útok
        _sb = cfg.set_bonuses or {}
        if _sb.get("ability_dmg_pct", 0):
            self.ability_dmg_bonus_pct += _sb["ability_dmg_pct"] / 100.0
        if _sb.get("spell_echo_pct", 0):
            self.spell_echo_chance = max(
                self.spell_echo_chance, _sb["spell_echo_pct"] / 100.0
            )
        if _sb.get("first_strike", False):
            self.first_strike = True
        if _sb.get("regen_every_round", False):
            # Dračí Šupiny 5pc: přidej permanentní regen (30 kol = celý souboj)
            self.statuses.append(ActiveStatus(
                name="regen",
                remaining_rounds=30,
                tick_value=self.hp_max * STATUS_DEFS["regen"]["heal_pct"],
            ))

        # ── Subclass: luck_mult (combat-only, primární stat se nemění) ────────
        if cfg.subclass:
            from models.subclass import SUBCLASS_DEFINITIONS as _SUBCLASS_DEFS
            _sd = _SUBCLASS_DEFS.get(cfg.subclass, {})
            _lm = _sd.get("stat_mults", {}).get("luck_mult", 0.0)
            if _lm:
                self.luck = max(0, int(self.luck * _lm))

        # ── A/B experiment overrides ──────────────────────────────────────────
        _ov = cfg.experiment_overrides or {}
        self.crit_damage_mult  = float(_ov.get("crit_damage_mult",  CRIT_DAMAGE_MULT))
        self.ability_damage_mult = float(_ov.get("ability_damage_mult", 1.0))

        # Start statusy z dungeon modifikátoru (např. poison z cursed_grounds)
        for _mod_status in (cfg.modifier_statuses or []):
            if _mod_status and _mod_status in STATUS_DEFS:
                self.add_status(_mod_status, hp_max=self.hp_max)

    # ── Status helpers ───────────────────────────────────────────────────────

    def has_status(self, name: str) -> bool:
        return any(s.name == name for s in self.statuses)

    def get_status(self, name: str) -> Optional[ActiveStatus]:
        return next((s for s in self.statuses if s.name == name), None)

    def add_status(self, name: str, hp_max: int = 0, atk: int = 0):
        """Aplikuje nebo obnoví status efekt."""
        if self.has_status(name):
            # Obnov trvání
            s = self.get_status(name)
            if s:
                s.remaining_rounds = STATUS_DEFS[name]["rounds"]
            return

        sdef = STATUS_DEFS.get(name, {})
        tick_val = 0.0
        absorb   = 0.0
        atk_deb  = 0.0
        spd_deb  = 0.0

        if "tick_dmg_pct" in sdef:
            tick_val = hp_max * sdef["tick_dmg_pct"]
        elif "tick_dmg_flat" in sdef:
            tick_val = atk * sdef["tick_dmg_flat"]  # skáluje na ATK aplikátora
        elif "heal_pct" in sdef:
            tick_val = hp_max * sdef["heal_pct"]
        if "absorb_pct" in sdef:
            absorb = sdef["absorb_pct"]
        if "atk_debuff_pct" in sdef:
            atk_deb = sdef["atk_debuff_pct"]
        if "spd_debuff_pct" in sdef:
            spd_deb = sdef["spd_debuff_pct"]

        self.statuses.append(ActiveStatus(
            name=name,
            remaining_rounds=sdef.get("rounds", 1),
            tick_value=tick_val,
            absorb_pct=absorb,
            atk_debuff_pct=atk_deb,
            spd_debuff_pct=spd_deb,
        ))

    def remove_status(self, name: str):
        self.statuses = [s for s in self.statuses if s.name != name]

    # ── Efektivní stats (s debuffs) ─────────────────────────────────────────

    def effective_dmg(self) -> float:
        """Celkovy base damage po aplikaci dmg_mult a debuffu."""
        dmg = self.base_dmg * self.dmg_mult
        for s in self.statuses:
            if s.atk_debuff_pct > 0:
                dmg *= (1.0 - s.atk_debuff_pct)
        # Boss enrage bonus
        if self.dmg_bonus_pct > 0:
            dmg *= (1.0 + self.dmg_bonus_pct)
        return max(1.0, dmg)

    # Backward compat alias
    def effective_atk(self) -> int:
        return max(1, int(self.effective_dmg()))

    def effective_spd(self) -> int:
        spd = self.spd
        for s in self.statuses:
            if s.spd_debuff_pct > 0:
                spd = int(spd * (1.0 - s.spd_debuff_pct))
        return max(1, spd)

    def is_stunned(self) -> bool:
        return self.has_status("stun")

    def shield_absorb(self) -> float:
        """Vrátí aktuální absorpci štítu (0.0–1.0)."""
        s = self.get_status("shield")
        return s.absorb_pct if s else 0.0


# ── Pomocné funkce ─────────────────────────────────────────────────────────────




# ── Status interaction matrix ──────────────────────────────────────────────────
# Dvojice statusů a jejich synergie — implementace inline v _process_status_ticks
STATUS_INTERACTIONS: dict = {
    ("bleed", "weaken"): {
        "name": "Zranitelnost", "emoji": "🩸💔",
        "desc": "Krvácení × Oslabení — bleed tick způsobí 50 % více škody.",
    },
    ("poison", "regen"): {
        "name": "Neutralizace", "emoji": "☠️💚",
        "desc": "Jed × Regenerace — efekty se vzájemně ruší (čistý výsledek).",
    },
    ("burn", "shield"): {
        "name": "Tavení Štítu", "emoji": "🔥🛡️",
        "desc": "Hoření × Štít — každý burn tick sníží absorpci štítu o 10 %.",
    },
}


def _calc_damage(
    attacker: "_FighterState",
    defender: "_FighterState",
    is_crit: bool = False,
    dmg_override: float = 0.0,
    ignore_armor: bool = False,
    crit_mult: float = CRIT_DAMAGE_MULT,
) -> int:
    """Vypocita poskozeni pomoci armor reduction formule s rozptylem +-15%."""
    from game.combat_stats import calc_armor_pct
    base = dmg_override if dmg_override > 0 else attacker.effective_dmg()
    if not ignore_armor:
        armor_pct = calc_armor_pct(
            defender.cfg.cls or "",
            int(defender.armor_value * defender.armor_mult),
            attacker.level,
        )
        base *= (1.0 - armor_pct)
    variance = random.uniform(1.0 - DAMAGE_VARIANCE, 1.0 + DAMAGE_VARIANCE)
    dmg = int(base * variance)
    if is_crit:
        dmg = int(dmg * crit_mult)
    return max(1, dmg)


def _apply_shield_absorb(fighter: _FighterState, raw_dmg: int) -> int:
    """Aplikuje štít absorpci — sníží damage."""
    absorb = fighter.shield_absorb()
    if absorb > 0:
        absorbed = int(raw_dmg * absorb)
        return max(1, raw_dmg - absorbed)
    return raw_dmg


def _check_boss_phases(boss: _FighterState, target: _FighterState,
                        round_num: int, events: list, log: list):
    """Zkontroluje, zda boss přešel do nové fáze a aplikuje efekty."""
    if not boss.cfg.is_boss or not boss.cfg.phases:
        return

    hp_pct = boss.hp / boss.hp_max
    for phase in boss.cfg.phases:
        phase_num = phase.phase_num
        if phase_num in boss.triggered_phases:
            continue  # Fáze již byla triggernuta

        if hp_pct <= phase.trigger_hp_pct:
            boss.triggered_phases.add(phase_num)
            boss.current_phase = phase_num

            # Stat buff
            for stat, mult in phase.stat_multipliers.items():
                if stat == "atk":
                    boss.dmg_mult *= mult
                elif stat == "def":
                    boss.armor_mult *= mult
                elif stat == "dmg_bonus":
                    boss.dmg_bonus_pct += (mult - 1.0)
                # spd ignoruj

            # Boss se léčí
            if phase.heal_pct > 0:
                heal_amount = int(boss.hp_max * phase.heal_pct)
                boss.hp = min(boss.hp_max, boss.hp + heal_amount)

            # Aplikuj status na hráče
            if phase.apply_status_to_player:
                target.add_status(phase.apply_status_to_player,
                                   hp_max=target.hp_max, atk=boss.effective_atk())

            # Přidej novou ability
            if phase.new_ability and phase.new_ability not in boss.active_specials:
                boss.active_specials.append(phase.new_ability)

            sdef_apply = STATUS_DEFS.get(phase.apply_status_to_player or "", {})

            evt = CombatEvent(
                type=EVENT_PHASE_CHANGE,
                round=round_num,
                actor=boss.cfg.name,
                target=target.cfg.name,
                actor_hp=boss.hp,
                target_hp=target.hp,
                actor_hp_max=boss.hp_max,
                target_hp_max=target.hp_max,
                phase_num=phase_num,
                phase_msg=phase.message,
                status_name=phase.apply_status_to_player or "",
                status_emoji=sdef_apply.get("emoji", ""),
                text=f"⚡ PHASE CHANGE! {phase.message}",
            )
            events.append(evt)
            log.append(f"\n⚡ {phase.message}")


def _process_status_ticks(fighter: _FighterState, other: _FighterState,
                            round_num: int, events: list, log: list):
    """Aplikuje tickové efekty a odebere expirované statusy.

    Interaction matrix (STATUS_INTERACTIONS):
      bleed  + weaken  → Zranitelnost: bleed tick způsobí 50 % více škody
      poison + regen   → Neutralizace: efekty se ruší, tick silnějšího probíhá
      burn   + shield  → Tavení Štítu: každý burn tick -10 % absorpce štítu
    """
    # ── Pre-check: poison + regen neutralizace ──────────────────────────────
    # Pokud jsou oba aktivní, vzájemně se ruší — tickneme jen čistý výsledek.
    _has_poison = fighter.has_status("poison")
    _has_regen  = fighter.has_status("regen")
    _poison_skip = False
    _regen_skip  = False
    if _has_poison and _has_regen:
        _ps = fighter.get_status("poison")
        _rs = fighter.get_status("regen")
        _net_dmg  = int(_ps.tick_value) if _ps else 0
        _net_heal = int(_rs.tick_value) if _rs else 0
        _net = _net_heal - _net_dmg     # kladné = léčí, záporné = škodí
        if _net < 0:
            fighter.hp = max(0, fighter.hp + _net)
        elif _net > 0:
            fighter.hp = min(fighter.hp_max, fighter.hp + _net)
        _idef = STATUS_INTERACTIONS[("poison", "regen")]
        if _net < 0:
            _itext = (f"  {_idef['emoji']} {fighter.cfg.name}: {_idef['name']}! "
                      f"Jed převládl — čistá škoda: -{abs(_net)} HP  [{fighter.cfg.name} HP: {fighter.hp}]")
        elif _net > 0:
            _itext = (f"  {_idef['emoji']} {fighter.cfg.name}: {_idef['name']}! "
                      f"Regenerace převládla — čisté léčení: +{_net} HP  [{fighter.cfg.name} HP: {fighter.hp}]")
        else:
            _itext = (f"  {_idef['emoji']} {fighter.cfg.name}: {_idef['name']}! "
                      f"Jed a regenerace se dokonale ruší.")
        evt_i = CombatEvent(
            type=EVENT_INTERACTION,
            round=round_num,
            actor=fighter.cfg.name,
            target=fighter.cfg.name,
            damage=abs(_net) if _net < 0 else 0,
            heal=_net if _net > 0 else 0,
            actor_hp=fighter.hp,
            target_hp=fighter.hp,
            actor_hp_max=fighter.hp_max,
            target_hp_max=fighter.hp_max,
            status_name="poison+regen",
            status_emoji=_idef["emoji"],
            text=_itext,
        )
        events.append(evt_i)
        log.append(_itext)
        _poison_skip = True
        _regen_skip  = True

    expired = []
    for status in list(fighter.statuses):
        sdef = STATUS_DEFS.get(status.name, {})

        # Přeskočit poison/regen tický — byly zpracovány v neutralizaci výše
        if status.name == "poison" and _poison_skip:
            status.remaining_rounds -= 1
            if status.remaining_rounds <= 0:
                expired.append(status.name)
            continue
        if status.name == "regen" and _regen_skip:
            status.remaining_rounds -= 1
            if status.remaining_rounds <= 0:
                expired.append(status.name)
            continue

        # Tick damage/heal (ne stun, shield, weaken, slow — ty ticknout ne)
        if "tick_dmg_pct" in sdef or "tick_dmg_flat" in sdef:
            dmg = max(1, int(status.tick_value))
            emoji = sdef.get("emoji", "⚡")

            # Interakce: bleed + weaken → Zranitelnost (+50 % škody)
            if status.name == "bleed" and fighter.has_status("weaken"):
                _amplified = int(dmg * 1.50)
                _idef = STATUS_INTERACTIONS[("bleed", "weaken")]
                _itext = (f"  {_idef['emoji']} {fighter.cfg.name}: {_idef['name']}! "
                          f"Krvácení zesíleno oslabením: {dmg} → {_amplified} HP")
                evt_i = CombatEvent(
                    type=EVENT_INTERACTION,
                    round=round_num,
                    actor=fighter.cfg.name,
                    target=fighter.cfg.name,
                    actor_hp=fighter.hp,
                    target_hp=fighter.hp,
                    actor_hp_max=fighter.hp_max,
                    target_hp_max=fighter.hp_max,
                    status_name="bleed+weaken",
                    status_emoji=_idef["emoji"],
                    text=_itext,
                )
                events.append(evt_i)
                log.append(_itext)
                dmg = _amplified

            fighter.hp = max(0, fighter.hp - dmg)

            # Interakce: burn + shield → Tavení Štítu (-10 % absorpce)
            if status.name == "burn":
                _sh = fighter.get_status("shield")
                if _sh is not None:
                    _old_absorb = _sh.absorb_pct
                    _sh.absorb_pct = max(0.05, _sh.absorb_pct - 0.10)
                    _idef = STATUS_INTERACTIONS[("burn", "shield")]
                    _itext = (f"  {_idef['emoji']} {fighter.cfg.name}: {_idef['name']}! "
                              f"Absorpce štítu: {int(_old_absorb*100)} % → {int(_sh.absorb_pct*100)} %")
                    evt_i = CombatEvent(
                        type=EVENT_INTERACTION,
                        round=round_num,
                        actor=fighter.cfg.name,
                        target=fighter.cfg.name,
                        actor_hp=fighter.hp,
                        target_hp=fighter.hp,
                        actor_hp_max=fighter.hp_max,
                        target_hp_max=fighter.hp_max,
                        status_name="burn+shield",
                        status_emoji=_idef["emoji"],
                        text=_itext,
                    )
                    events.append(evt_i)
                    log.append(_itext)

            evt = CombatEvent(
                type=EVENT_STATUS_TICK,
                round=round_num,
                actor=fighter.cfg.name,
                target=fighter.cfg.name,
                damage=dmg,
                actor_hp=fighter.hp,
                target_hp=fighter.hp,
                actor_hp_max=fighter.hp_max,
                target_hp_max=fighter.hp_max,
                status_name=status.name,
                status_emoji=emoji,
                text=f"  {emoji} {fighter.cfg.name} trpí {sdef.get('name', status.name)}! -{dmg} HP  [{fighter.cfg.name} HP: {fighter.hp}]",
            )
            events.append(evt)
            log.append(evt.text)

        elif "heal_pct" in sdef:
            heal = max(1, int(status.tick_value))
            fighter.hp = min(fighter.hp_max, fighter.hp + heal)
            emoji = sdef.get("emoji", "💚")
            evt = CombatEvent(
                type=EVENT_HEAL,
                round=round_num,
                actor=fighter.cfg.name,
                target=fighter.cfg.name,
                heal=heal,
                actor_hp=fighter.hp,
                target_hp=fighter.hp,
                actor_hp_max=fighter.hp_max,
                target_hp_max=fighter.hp_max,
                status_name=status.name,
                status_emoji=emoji,
                text=f"  {emoji} {fighter.cfg.name} se léčí z {sdef.get('name', status.name)}! +{heal} HP  [{fighter.cfg.name} HP: {fighter.hp}]",
            )
            events.append(evt)
            log.append(evt.text)

        # Odeber stun po 1 kole (skip_turn se vyhodnocuje jinde)
        status.remaining_rounds -= 1
        if status.remaining_rounds <= 0:
            expired.append(status.name)

    for name in expired:
        fighter.remove_status(name)
        sdef = STATUS_DEFS.get(name, {})
        emoji = sdef.get("emoji", "")
        evt = CombatEvent(
            type=EVENT_STATUS_EXPIRE,
            round=round_num,
            actor=fighter.cfg.name,
            target=fighter.cfg.name,
            actor_hp=fighter.hp,
            target_hp=fighter.hp,
            actor_hp_max=fighter.hp_max,
            target_hp_max=fighter.hp_max,
            status_name=name,
            status_emoji=emoji,
            text=f"  {emoji} {sdef.get('name', name)} na {fighter.cfg.name} expiroval.",
        )
        events.append(evt)


def _try_boss_special(boss: _FighterState, target: _FighterState,
                       round_num: int, events: list, log: list, trigger: str = "on_hit"):
    """Zkusí aktivovat boss speciální ability při daném triggeru."""
    for ability_key in boss.active_specials:
        adef = BOSS_SPECIAL_ABILITIES.get(ability_key, {})
        if adef.get("trigger") != trigger:
            continue

        if trigger == "on_hit":
            if random.random() > adef.get("trigger_chance", 0.0):
                continue
        elif trigger == "every_n_rounds":
            n = adef.get("trigger_rounds", 3)
            if round_num % n != 0:
                continue

        # Aplikuj efekt
        status_name = adef.get("apply_status")
        if status_name and not target.has_status(status_name):
            target.add_status(status_name, hp_max=target.hp_max, atk=boss.effective_atk())
            sdef = STATUS_DEFS.get(status_name, {})
            emoji = sdef.get("emoji", "⚡")
            txt = f"  {adef.get('emoji', '⚡')} {boss.cfg.name} použil {adef['name']}! {target.cfg.name} trpí {sdef.get('name', status_name)}!"
            evt = CombatEvent(
                type=EVENT_STATUS_APPLY,
                round=round_num,
                actor=boss.cfg.name,
                target=target.cfg.name,
                actor_hp=boss.hp,
                target_hp=target.hp,
                actor_hp_max=boss.hp_max,
                target_hp_max=target.hp_max,
                status_name=status_name,
                status_emoji=emoji,
                ability_name=adef["name"],
                ability_emoji=adef.get("emoji", "⚡"),
                text=txt,
            )
            events.append(evt)
            log.append(txt)


def _execute_t2_ability(
    attacker: _FighterState,
    defender: _FighterState,
    events: list,
    log: list,
    round_num: int,
) -> None:
    """
    Provede T2 aktivní schopnost útočníka.
    Spouští se každé 4. kolo (round_num % 4 == 0).
    """
    key   = attacker.talent_t2
    aname = attacker.cfg.name
    dname = defender.cfg.name

    # ── warrior: Cyklónový Úder — 3 údery × 50% ATK ──────────────────────────
    if key == "cyclone_strike":
        total = 0
        for _ in range(3):
            h = max(1, int(attacker.effective_atk() * 0.50))
            h = _apply_shield_absorb(defender, h)
            if defender.dmg_reduction_pct > 0:
                h = max(1, int(h * (1.0 - defender.dmg_reduction_pct)))
            defender.hp = max(0, defender.hp - h)
            total += h
        txt = f"  🌪 {aname}: Cyklónový Úder! 3 údery → {total} dmg  [{dname} HP: {defender.hp}]"
        events.append(CombatEvent(
            type="t2_attack", round=round_num,
            actor=aname, target=dname, damage=total,
            actor_hp=attacker.hp, target_hp=defender.hp,
            actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
            ability_name="Cyklónový Úder", ability_emoji="🌪", text=txt,
        ))
        log.append(txt)

    # ── warrior: Bojový Pokřik — heal 15% HP + štít 2 kola ──────────────────
    elif key == "rallying_cry":
        heal = max(1, int(attacker.hp_max * 0.15))
        attacker.hp = min(attacker.hp_max, attacker.hp + heal)
        # Přidej štít (vlastní absorpce 20%, 2 kola)
        if attacker.has_status("shield"):
            s = attacker.get_status("shield")
            if s:
                s.remaining_rounds = 2
                s.absorb_pct = max(s.absorb_pct, 0.20)
        else:
            attacker.statuses.append(ActiveStatus(
                name="shield", remaining_rounds=2,
                absorb_pct=0.20,
            ))
        txt = (f"  📯 {aname}: Bojový Pokřik! +{heal} HP léčení + štít 2 kola  "
               f"[{aname} HP: {attacker.hp}]")
        events.append(CombatEvent(
            type="t2_heal", round=round_num,
            actor=aname, target=aname, heal=heal,
            actor_hp=attacker.hp, target_hp=defender.hp,
            actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
            ability_name="Bojový Pokřik", ability_emoji="📯", text=txt,
        ))
        log.append(txt)

    # ── warrior: Poprava — 3× ATK pod 25% HP, jinak 1× ATK ─────────────────
    elif key == "execute":
        hp_pct = defender.hp / defender.hp_max if defender.hp_max > 0 else 1.0
        mult = 3.0 if hp_pct < 0.25 else 1.0
        dmg = _calc_damage(attacker, defender, dmg_override=attacker.effective_dmg() * mult)
        dmg = _apply_shield_absorb(defender, dmg)
        if defender.dmg_reduction_pct > 0:
            dmg = max(1, int(dmg * (1.0 - defender.dmg_reduction_pct)))
        defender.hp = max(0, defender.hp - dmg)
        note = " ☠ POPRAVA!" if mult == 3.0 else ""
        txt = (f"  ⚰ {aname}: Poprava!{note} → {dmg} dmg  [{dname} HP: {defender.hp}]")
        events.append(CombatEvent(
            type="t2_attack", round=round_num,
            actor=aname, target=dname, damage=dmg,
            actor_hp=attacker.hp, target_hp=defender.hp,
            actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
            ability_name="Poprava", ability_emoji="⚰", text=txt,
        ))
        log.append(txt)

    # ── mage: Arkánná Bouře — 3 kouzla × 60% ATK, ignorují brnění ───────────
    elif key == "arcane_storm":
        total = 0
        for _ in range(3):
            h = _calc_damage(attacker, defender,
                             dmg_override=attacker.effective_dmg() * 0.60,
                             ignore_armor=True)
            if attacker.ability_dmg_bonus_pct > 0:
                h = max(1, int(h * (1.0 + attacker.ability_dmg_bonus_pct)))
            defender.hp = max(0, defender.hp - h)
            total += h
        txt = f"  ⚡ {aname}: Arkánná Bouře! 3 kouzla → {total} dmg (pierce)  [{dname} HP: {defender.hp}]"
        events.append(CombatEvent(
            type="t2_attack", round=round_num,
            actor=aname, target=dname, damage=total,
            actor_hp=attacker.hp, target_hp=defender.hp,
            actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
            ability_name="Arkánná Bouře", ability_emoji="⚡", text=txt,
        ))
        log.append(txt)

    # ── mage: Prázdnota Many — aplikuje weaken na nepřítele ─────────────────
    elif key == "mana_void":
        defender.add_status("weaken", hp_max=defender.hp_max, atk=attacker.effective_atk())
        txt = (f"  🕳 {aname}: Prázdnota Many! {dname} je oslaben!")
        events.append(CombatEvent(
            type="t2_status", round=round_num,
            actor=aname, target=dname,
            actor_hp=attacker.hp, target_hp=defender.hp,
            actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
            ability_name="Prázdnota Many", ability_emoji="🕳",
            status_name="weaken", status_emoji=STATUS_DEFS["weaken"]["emoji"],
            text=txt,
        ))
        log.append(txt)

    # ── mage: Časový Zlom — druhý útok za 80% ability dmg ───────────────────
    elif key == "time_warp":
        ability = CLASS_ABILITIES.get(attacker.cfg.cls)
        if ability:
            base_dmg = _calc_damage(
                attacker, defender,
                dmg_override=attacker.effective_dmg() * ability["dmg_mult"] * 0.80,
                ignore_armor=(ability.get("def_ignore_pct", 0.0) >= 1.0),
            )
            if attacker.ability_dmg_bonus_pct > 0:
                base_dmg = max(1, int(base_dmg * (1.0 + attacker.ability_dmg_bonus_pct)))
            base_dmg = _apply_shield_absorb(defender, base_dmg)
            if defender.dmg_reduction_pct > 0:
                base_dmg = max(1, int(base_dmg * (1.0 - defender.dmg_reduction_pct)))
            defender.hp = max(0, defender.hp - base_dmg)
            txt = (f"  ⏳ {aname}: Časový Zlom! Extra útok → {base_dmg} dmg  "
                   f"[{dname} HP: {defender.hp}]")
        else:
            base_dmg = 0
            txt = f"  ⏳ {aname}: Časový Zlom! (žádná ability)"
        events.append(CombatEvent(
            type="t2_attack", round=round_num,
            actor=aname, target=dname, damage=base_dmg,
            actor_hp=attacker.hp, target_hp=defender.hp,
            actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
            ability_name="Časový Zlom", ability_emoji="⏳", text=txt,
        ))
        log.append(txt)

    # ── ranger: Déšť Šípů — 4 šípy × 40% ATK + bleed ───────────────────────
    elif key == "rain_of_arrows":
        total = 0
        for _ in range(4):
            h = max(1, int(attacker.effective_atk() * 0.40))
            h = _apply_shield_absorb(defender, h)
            if defender.dmg_reduction_pct > 0:
                h = max(1, int(h * (1.0 - defender.dmg_reduction_pct)))
            defender.hp = max(0, defender.hp - h)
            total += h
        defender.add_status("bleed", hp_max=defender.hp_max, atk=attacker.effective_atk())
        txt = (f"  🏹 {aname}: Déšť Šípů! 4 šípy → {total} dmg + krvácení  "
               f"[{dname} HP: {defender.hp}]")
        events.append(CombatEvent(
            type="t2_attack", round=round_num,
            actor=aname, target=dname, damage=total,
            actor_hp=attacker.hp, target_hp=defender.hp,
            actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
            ability_name="Déšť Šípů", ability_emoji="🏹",
            status_name="bleed", status_emoji="🩸", text=txt,
        ))
        log.append(txt)

    # ── ranger: Stínový Krok — garantovaný protiútok 1.5× + krvácení ────────
    elif key == "shadow_step":
        # shadow_step: garantovaný protiútok 1.5× + bleed
        counter_dmg = int(attacker.base_dmg * attacker.dmg_mult * 1.5)
        counter_dmg = _apply_shield_absorb(defender, counter_dmg)
        if defender.dmg_reduction_pct > 0:
            counter_dmg = max(1, int(counter_dmg * (1.0 - defender.dmg_reduction_pct)))
        defender.hp = max(0, defender.hp - counter_dmg)
        defender.add_status("bleed", hp_max=defender.hp_max)
        txt = (f"  👤 {aname}: Stínový Krok! Protiútok → {counter_dmg} dmg + krvácení  "
               f"[{dname} HP: {defender.hp}]")
        events.append(CombatEvent(
            type="counter", round=round_num,
            actor=aname, target=dname, damage=counter_dmg,
            actor_hp=attacker.hp, target_hp=defender.hp,
            actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
            ability_name="Stínový Krok", ability_emoji="👤",
            status_name="bleed", status_emoji="🩸", text=txt,
        ))
        log.append(txt)

    # ── ranger: Označení Smrtí — trvale -25% DEF nepřítele (kumulativní) ────
    elif key == "mark_for_death":
        old_armor = defender.armor_value
        defender.armor_mult *= 0.75
        attacker.t2_def_reduction += 0.25
        _new_eff_armor = int(defender.armor_value * defender.armor_mult)
        txt = (f"  🎯 {aname}: Označení Smrtí! Armor {dname}: {old_armor} → {_new_eff_armor}  "
               f"(celková redukce: {int(attacker.t2_def_reduction * 100)}%)")
        events.append(CombatEvent(
            type="t2_status", round=round_num,
            actor=aname, target=dname,
            actor_hp=attacker.hp, target_hp=defender.hp,
            actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
            ability_name="Označení Smrtí", ability_emoji="🎯", text=txt,
        ))
        log.append(txt)


T2_COOLDOWN = 4  # T2 schopnost se spouští každé 4. kolo


# ── F.1/F.2/F.3: Pomocné funkce class-specific mechanik ───────────────────────

def _warrior_berserker_burst(
    attacker: "_FighterState",
    defender: "_FighterState",
    round_num: int,
    events: list,
    log: list,
) -> None:
    """F.1 — Warrior Berserker Burst: double damage na příštím útoku + stun na nepřítele.
    Volá se když rage >= 100 na začátku útočníkova kola. Resetuje rage na 0.
    Implementováno jako přímý double-damage útok (bez dodge check — burst probíjí)."""
    attacker.rage = 0
    # Double damage útok (ignoruje dodge, neprobíhá ability check)
    dmg = _calc_damage(attacker, defender, dmg_override=attacker.effective_dmg() * 2)
    dmg = _apply_shield_absorb(defender, dmg)
    if defender.dmg_reduction_pct > 0:
        dmg = max(1, int(dmg * (1.0 - defender.dmg_reduction_pct)))
    defender.hp = max(0, defender.hp - dmg)
    # Aplikuj stun na nepřítele
    defender.add_status("stun", hp_max=defender.hp_max, atk=attacker.effective_atk())
    txt = (f"  ⚔ {attacker.cfg.name} BERSERKER BURST! (rage 100) "
           f"→ {dmg} dmg + omráčení!  [{defender.cfg.name} HP: {defender.hp}]")
    events.append(CombatEvent(
        type=EVENT_ABILITY,
        round=round_num,
        actor=attacker.cfg.name,
        target=defender.cfg.name,
        damage=dmg,
        actor_hp=attacker.hp,
        target_hp=defender.hp,
        actor_hp_max=attacker.hp_max,
        target_hp_max=defender.hp_max,
        ability_name="Berserker Burst",
        ability_emoji="⚔",
        status_name="stun",
        status_emoji=STATUS_DEFS["stun"]["emoji"],
        text=txt,
    ))
    log.append(txt)


def _mage_next_spell_type(mage: "_FighterState") -> str:
    """F.2 — Vrátí typ příštího kouzla. AI mage cyklí, player mage je pseudo-náhodný."""
    idx = mage._spell_cycle_index % len(mage._spell_cycle)
    spell_type = mage._spell_cycle[idx]
    mage._spell_cycle_index += 1
    return spell_type


def _ranger_first_strike_bonus(round_num: int) -> tuple[float, float]:
    """F.3 — Vrátí (dmg_bonus_pct, crit_bonus_pct) pro Rangera v daném kole.
    Kolo 1: +40% dmg, +15% crit. Každé další kolo klesá o 8%/3%. Kolo 6+: (0, 0)."""
    if round_num >= 6:
        return 0.0, 0.0
    decay = round_num - 1          # kolo 1 → decay=0, kolo 5 → decay=4
    dmg_bonus  = max(0.0, 0.40 - decay * 0.08)
    crit_bonus = max(0.0, 0.15 - decay * 0.03)
    return dmg_bonus, crit_bonus


def _execute_attack(
    attacker: _FighterState,
    defender: _FighterState,
    round_num: int,
    events: list,
    log: list,
) -> int:
    """
    Provede jeden útok včetně ability checku, dodge, critu a status aplikací.
    Vrátí počet způsobeného poškození (pro contribution tracking).
    """
    total_dmg = 0
    a_name = attacker.cfg.name
    d_name = defender.cfg.name
    a_cls  = attacker.cfg.cls
    a_sub  = attacker.cfg.subclass

    # ── 1. Omráčení — přeskočí tah ──────────────────────────────────────────
    if attacker.is_stunned():
        txt = f"  ⭐ {a_name} je omráčen a přeskočí tah!"
        evt = CombatEvent(
            type=EVENT_STATUS_TICK,
            round=round_num,
            actor=a_name, target=a_name,
            actor_hp=attacker.hp, target_hp=defender.hp,
            actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
            status_name="stun", status_emoji="⭐",
            text=txt,
        )
        events.append(evt)
        log.append(txt)
        # Odeber stun
        attacker.remove_status("stun")
        return 0

    # ── 2. Subclass/Class ability ─────────────────────────────────────────────
    # Subclass ability má přednost před základní class ability
    ability = SUBCLASS_ABILITIES.get(a_sub or "") or (CLASS_ABILITIES.get(a_cls) if a_cls else None)
    if ability:
        ignore_pct = ability.get("def_ignore_pct", 0.0)

        # ── Multi-hit (Stínová Čepel) — speciální branch, vrátí early ────────
        if ability["type"] == "multi_hit":
            hit_count = ability.get("hit_count", 2)
            total_mh_dmg = 0
            for _ in range(hit_count):
                h = _calc_damage(
                    attacker, defender,
                    dmg_override=attacker.effective_dmg() * ability["dmg_mult"],
                    ignore_armor=(ignore_pct >= 1.0),
                )
                h = _apply_shield_absorb(defender, h)
                if defender.dmg_reduction_pct > 0:
                    h = max(1, int(h * (1.0 - defender.dmg_reduction_pct)))
                defender.hp = max(0, defender.hp - h)
                total_mh_dmg += h
            if attacker.ability_dmg_bonus_pct > 0:
                total_mh_dmg = max(1, int(total_mh_dmg * (1.0 + attacker.ability_dmg_bonus_pct)))
            if attacker.ability_damage_mult != 1.0:
                total_mh_dmg = max(1, int(total_mh_dmg * attacker.ability_damage_mult))
            mh_status = ability.get("apply_status")
            if mh_status:
                defender.add_status(mh_status, hp_max=defender.hp_max, atk=attacker.effective_atk())
            mh_txt = (f"  {ability['emoji']} {a_name} použil {ability['name']}! "
                      f"({hit_count}× zásah) → {total_mh_dmg} dmg  [{d_name} HP: {defender.hp}]")
            if mh_status:
                _ms = STATUS_DEFS.get(mh_status, {})
                mh_txt += f" [{_ms.get('emoji', '')} {_ms.get('name', mh_status)}!]"
            mh_sdef = STATUS_DEFS.get(mh_status or "", {})
            events.append(CombatEvent(
                type=EVENT_ABILITY, round=round_num,
                actor=a_name, target=d_name, damage=total_mh_dmg,
                actor_hp=attacker.hp, target_hp=defender.hp,
                actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
                ability_name=ability["name"], ability_emoji=ability["emoji"],
                status_name=mh_status or "", status_emoji=mh_sdef.get("emoji", ""),
                text=mh_txt,
            ))
            log.append(mh_txt)
            if mh_status:
                events.append(CombatEvent(
                    type=EVENT_STATUS_APPLY, round=round_num,
                    actor=a_name, target=d_name,
                    actor_hp=attacker.hp, target_hp=defender.hp,
                    actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
                    status_name=mh_status, status_emoji=mh_sdef.get("emoji", ""),
                    ability_name=ability["name"], text="",
                ))
            return total_mh_dmg

        # ── Normal ability ────────────────────────────────────────────────────
        if ability["type"] == "guaranteed_crit":
            dmg = _calc_damage(attacker, defender,
                                is_crit=True, ignore_armor=(ignore_pct >= 1.0))
        else:
            dmg = _calc_damage(attacker, defender,
                                dmg_override=attacker.effective_dmg() * ability["dmg_mult"],
                                ignore_armor=(ignore_pct >= 1.0))

        # Talent: Arcane Focus — +20 % dmg schopností
        if attacker.ability_dmg_bonus_pct > 0:
            dmg = max(1, int(dmg * (1.0 + attacker.ability_dmg_bonus_pct)))
        # A/B experiment: ability_damage_mult
        if attacker.ability_damage_mult != 1.0:
            dmg = max(1, int(dmg * attacker.ability_damage_mult))

        # Talent: Hunter's Mark — první útok +75 % dmg
        if attacker.hunters_mark_active:
            dmg = max(1, int(dmg * 1.75))
            attacker.hunters_mark_active = False

        # Štít absorpce
        dmg = _apply_shield_absorb(defender, dmg)

        # Talent: Iron Skin — -20 % přijatého dmg
        if defender.dmg_reduction_pct > 0:
            dmg = max(1, int(dmg * (1.0 - defender.dmg_reduction_pct)))

        defender.hp = max(0, defender.hp - dmg)
        total_dmg = dmg

        # Subclass: Berserkr recoil — útočník přijme 8 % způsobeného dmg
        _recoil_pct = ability.get("self_dmg_pct", 0.0)
        if _recoil_pct > 0:
            _recoil = max(1, int(total_dmg * _recoil_pct))
            attacker.hp = max(0, attacker.hp - _recoil)
            _rc_txt = (f"  🔴 {a_name} přijímá {_recoil} zpětného poškození!")
            events.append(CombatEvent(
                type=EVENT_STATUS_TICK, round=round_num,
                actor=a_name, target=a_name,
                damage=_recoil, actor_hp=attacker.hp, target_hp=attacker.hp,
                actor_hp_max=attacker.hp_max, target_hp_max=attacker.hp_max,
                text=_rc_txt,
            ))
            log.append(_rc_txt)

        # Aplikuj status k obránci
        status_applied = ability.get("apply_status")
        if status_applied:
            defender.add_status(status_applied, hp_max=defender.hp_max,
                                  atk=attacker.effective_atk())
        # Subclass: extra_statuses k obránci (Nekromancer, Elementalista)
        _extra_statuses: list[str] = ability.get("extra_statuses", [])
        for _ext_s in _extra_statuses:
            defender.add_status(_ext_s, hp_max=defender.hp_max, atk=attacker.effective_atk())

        # Subclass: apply_status_self (Strážce — štít na sebe)
        _status_self = ability.get("apply_status_self")
        if _status_self:
            attacker.add_status(_status_self, hp_max=attacker.hp_max, atk=attacker.effective_atk())

        txt = (f"  {ability['emoji']} {a_name} použil {ability['name']}! "
               f"→ {dmg} dmg  [{d_name} HP: {defender.hp}]")
        if status_applied:
            sdef = STATUS_DEFS.get(status_applied, {})
            txt += f" [{sdef.get('emoji', '')} {sdef.get('name', status_applied)}!]"
        for _ext_s in _extra_statuses:
            _edef = STATUS_DEFS.get(_ext_s, {})
            txt += f" [{_edef.get('emoji', '')} {_edef.get('name', _ext_s)}!]"
        if _status_self:
            txt += f" [🛡️ {STATUS_DEFS.get(_status_self, {}).get('name', _status_self)} na sebe!]"

        sdef_s = STATUS_DEFS.get(status_applied or "", {})
        evt = CombatEvent(
            type=EVENT_ABILITY,
            round=round_num,
            actor=a_name, target=d_name,
            damage=dmg,
            actor_hp=attacker.hp, target_hp=defender.hp,
            actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
            ability_name=ability["name"], ability_emoji=ability["emoji"],
            status_name=status_applied or "",
            status_emoji=sdef_s.get("emoji", ""),
            text=txt,
        )
        events.append(evt)
        log.append(txt)

        if status_applied:
            events.append(CombatEvent(
                type=EVENT_STATUS_APPLY, round=round_num,
                actor=a_name, target=d_name,
                actor_hp=attacker.hp, target_hp=defender.hp,
                actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
                status_name=status_applied, status_emoji=sdef_s.get("emoji", ""),
                ability_name=ability["name"], text="",
            ))

        # Extra status eventy (Nekromancer / Elementalista)
        for _ext_s in _extra_statuses:
            _edef_s = STATUS_DEFS.get(_ext_s, {})
            events.append(CombatEvent(
                type=EVENT_STATUS_APPLY, round=round_num,
                actor=a_name, target=d_name,
                actor_hp=attacker.hp, target_hp=defender.hp,
                actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
                status_name=_ext_s, status_emoji=_edef_s.get("emoji", ""),
                ability_name=ability["name"], text="",
            ))

        # Status-self event (Strážce)
        if _status_self:
            _ssdef = STATUS_DEFS.get(_status_self, {})
            events.append(CombatEvent(
                type=EVENT_STATUS_APPLY, round=round_num,
                actor=a_name, target=a_name,
                actor_hp=attacker.hp, target_hp=attacker.hp,
                actor_hp_max=attacker.hp_max, target_hp_max=attacker.hp_max,
                status_name=_status_self, status_emoji=_ssdef.get("emoji", ""),
                ability_name=ability["name"], text="",
            ))

        # Talent: Spell Echo — 25 % šance zopakovat za 60 % dmg
        if attacker.spell_echo_chance > 0 and random.random() < attacker.spell_echo_chance:
            echo_dmg = max(1, int(total_dmg * 0.60))
            defender.hp = max(0, defender.hp - echo_dmg)
            total_dmg += echo_dmg
            echo_txt = (f"  ✨ {a_name}: Ozvěna Kouzla! "
                        f"→ {echo_dmg} dmg  [{d_name} HP: {defender.hp}]")
            events.append(CombatEvent(
                type=EVENT_ABILITY, round=round_num,
                actor=a_name, target=d_name, damage=echo_dmg,
                actor_hp=attacker.hp, target_hp=defender.hp,
                actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
                ability_name="Ozvěna Kouzla", ability_emoji="✨",
                text=echo_txt,
            ))
            log.append(echo_txt)

        return total_dmg

    # ── 3. Crit check ─────────────────────────────────────────────────────────
    # Talent: Hunter's Mark — první útok +75 % dmg
    _hunters_mult = 1.0
    if attacker.hunters_mark_active:
        _hunters_mult = 1.75
        attacker.hunters_mark_active = False
    # Talent: Battle Rage — +25 % crit dmg | experiment override: crit_damage_mult
    _crit_m = attacker.crit_damage_mult * (1.0 + attacker.crit_dmg_bonus_pct)

    # ── F.3 Ranger: First Strike Advantage (Diminishing Returns) ─────────────
    _fs_dmg_bonus = 0.0
    _fs_crit_bonus = 0.0
    if a_cls == "ranger":
        _fs_dmg_bonus, _fs_crit_bonus = _ranger_first_strike_bonus(round_num)
        if _fs_dmg_bonus > 0 and round_num == 1:
            _fs_txt = (f"  🏹 {a_name}: First Strike! +{int(_fs_dmg_bonus * 100)}% damage "
                       f"+{int(_fs_crit_bonus * 100)}% crit")
            events.append(CombatEvent(
                type=EVENT_ABILITY,
                round=round_num,
                actor=a_name, target=d_name,
                actor_hp=attacker.hp, target_hp=defender.hp,
                actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
                ability_name="First Strike", ability_emoji="🏹",
                text=_fs_txt,
            ))
            log.append(_fs_txt)

    from game.combat_stats import calc_crit_chance as _calc_crit_chance
    _effective_crit_chance = min(MAX_CRIT_CHANCE,
        _calc_crit_chance(attacker.luck, defender.level) + attacker.crit_bonus_pct + _fs_crit_bonus)
    is_crit = random.random() < _effective_crit_chance
    dmg     = _calc_damage(attacker, defender, is_crit,
                           crit_mult=_crit_m)
    dmg = max(1, int(dmg * _hunters_mult))

    # F.3 Ranger: aplikuj first strike damage bonus
    if _fs_dmg_bonus > 0:
        dmg = max(1, int(dmg * (1.0 + _fs_dmg_bonus)))

    # ── F.2 Mage: Spell Chain systém ─────────────────────────────────────────
    if a_cls == "mage":
        _current_spell = _mage_next_spell_type(attacker)
        if attacker.last_spell_type is not None:
            if _current_spell != attacker.last_spell_type:
                # Combo! +20% damage
                dmg = max(1, int(dmg * 1.20))
                _sc_txt = f"  🔥 Spell chain combo! +20% ({attacker.last_spell_type}→{_current_spell})"
                events.append(CombatEvent(
                    type=EVENT_ABILITY,
                    round=round_num,
                    actor=a_name, target=d_name,
                    actor_hp=attacker.hp, target_hp=defender.hp,
                    actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
                    ability_name="Spell Chain Combo", ability_emoji="🔥",
                    text=_sc_txt,
                ))
                log.append(_sc_txt)
            else:
                # Penalty: -10% damage
                dmg = max(1, int(dmg * 0.90))
                _sc_txt = f"  ❄ Repeated spell. -10% ({_current_spell})"
                events.append(CombatEvent(
                    type=EVENT_ABILITY,
                    round=round_num,
                    actor=a_name, target=d_name,
                    actor_hp=attacker.hp, target_hp=defender.hp,
                    actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
                    ability_name="Repeated Spell", ability_emoji="❄",
                    text=_sc_txt,
                ))
                log.append(_sc_txt)
        attacker.last_spell_type = _current_spell

    # Štít absorpce
    dmg = _apply_shield_absorb(defender, dmg)

    # Talent: Iron Skin — -20 % přijatého dmg
    if defender.dmg_reduction_pct > 0:
        dmg = max(1, int(dmg * (1.0 - defender.dmg_reduction_pct)))

    defender.hp = max(0, defender.hp - dmg)
    total_dmg = dmg

    # ── F.1 Warrior: Rage gain při zasažení nepřítele (+15) ──────────────────
    if a_cls == "warrior":
        attacker.rage = min(100, attacker.rage + 15)

    # ── F.1 Warrior: Rage gain pro obránce při přijatém zásahu (+25) ─────────
    if defender.cfg.cls == "warrior":
        defender.rage = min(100, defender.rage + 25)

    # ── 5. Crit efekt — aplikuj status pokud máš bonus ───────────────────────
    if is_crit:
        txt = f"  💥 KRITICKÝ ZÁSAH! {a_name} zasahuje za {dmg} dmg!  [{d_name} HP: {defender.hp}]"
        evt = CombatEvent(
            type=EVENT_CRIT,
            round=round_num,
            actor=a_name, target=d_name,
            damage=dmg, is_crit=True,
            actor_hp=attacker.hp, target_hp=defender.hp,
            actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
            text=txt,
        )
        events.append(evt)
        log.append(txt)
    else:
        txt = f"  ⚔️  {a_name} útočí → {dmg} dmg  [{d_name} HP: {defender.hp}]"
        evt = CombatEvent(
            type=EVENT_ATTACK,
            round=round_num,
            actor=a_name, target=d_name,
            damage=dmg,
            actor_hp=attacker.hp, target_hp=defender.hp,
            actor_hp_max=attacker.hp_max, target_hp_max=defender.hp_max,
            text=txt,
        )
        events.append(evt)
        log.append(txt)

    # ── 6. Boss speciální ability trigger (on_hit) ────────────────────────────
    if attacker.cfg.is_boss:
        _try_boss_special(attacker, defender, round_num, events, log, "on_hit")

    return total_dmg


# ── Hlavní funkce ──────────────────────────────────────────────────────────────

def simulate_unified_combat(
    attacker_cfg: CombatantConfig,
    defender_cfg: CombatantConfig,
    max_rounds: int = MAX_ROUNDS_DEFAULT,
    seed: Optional[int] = None,
) -> CombatResult:
    """
    Unifikovaný combat engine pro PvP, PvE, Bossy i Dungeony.

    Vstupy jsou CombatantConfig objekty — stejné pro hráče i AI.
    Vrací CombatResult s events (strukturovaný JSON) i log (text, backward compat).

    Proč jeden engine:
    - Konzistentní formule — PvP a PvE mají stejný feel
    - DRY — žádná duplikace
    - Snadná extensibilita — raidy, guild wars, spectator mode
    - Deterministická náhoda — seed pro replay
    """
    if seed is not None:
        random.seed(seed)

    attacker = _FighterState(attacker_cfg)
    defender = _FighterState(defender_cfg)

    events: list[CombatEvent] = []
    log:    list[str]         = []

    # ── Header logu ───────────────────────────────────────────────────────────
    log.append(f"⚔️  {attacker_cfg.name} (Lv.{attacker_cfg.level}) vs {defender_cfg.name} (Lv.{defender_cfg.level})")
    log.append(f"📊  HP: {attacker.hp} | DMG: {attacker.effective_atk()} | ARM: {attacker.armor_value} | SPD: {attacker.spd}")
    log.append("─" * 40)

    # ── Kdo jde první ─────────────────────────────────────────────────────────
    a_goes_first = attacker.effective_spd() >= defender.effective_spd()
    # Set bonus: Přízračný Chodec 5pc — First Strike (zaručený první útok útočníka)
    if attacker.first_strike:
        a_goes_first = True
    # Ranger class: always first strike
    if attacker.has_class_first_strike and not defender.has_class_first_strike:
        a_goes_first = True
    elif defender.has_class_first_strike and not attacker.has_class_first_strike:
        a_goes_first = False

    total_dmg_by_attacker = 0
    round_num = 0

    for round_num in range(1, max_rounds + 1):
        log.append(f"\n[Kolo {round_num}]")
        events.append(CombatEvent(
            type=EVENT_ROUND_START,
            round=round_num,
            actor="",
            target="",
            actor_hp=attacker.hp,
            target_hp=defender.hp,
            actor_hp_max=attacker.hp_max,
            target_hp_max=defender.hp_max,
            text=f"[Kolo {round_num}]",
        ))

        # ── Status ticky (začátek kola) ────────────────────────────────────
        _process_status_ticks(attacker, defender, round_num, events, log)
        _process_status_ticks(defender, attacker, round_num, events, log)

        if attacker.hp <= 0 or defender.hp <= 0:
            break

        # ── Boss phase check ───────────────────────────────────────────────
        if defender.cfg.is_boss:
            _check_boss_phases(defender, attacker, round_num, events, log)
        if attacker.cfg.is_boss:
            _check_boss_phases(attacker, defender, round_num, events, log)

        # ── Speciální boss ability (every_n_rounds) ────────────────────────
        if attacker.cfg.is_boss:
            _try_boss_special(attacker, defender, round_num, events, log, "every_n_rounds")
        if defender.cfg.is_boss:
            _try_boss_special(defender, attacker, round_num, events, log, "every_n_rounds")

        # ── Tahy (order podle SPD) ─────────────────────────────────────────
        if a_goes_first:
            # F.1 Warrior Berserker Burst — aktivuje se před útokem při rage >= 100
            if attacker.cfg.cls == "warrior" and attacker.rage >= 100:
                _warrior_berserker_burst(attacker, defender, round_num, events, log)
                if defender.hp <= 0:
                    break
            dmg = _execute_attack(attacker, defender, round_num, events, log)
            total_dmg_by_attacker += dmg
            if defender.hp <= 0:
                break
            # F.1 Warrior Berserker Burst pro obránce (pokud jde druhý)
            if defender.cfg.cls == "warrior" and defender.rage >= 100:
                _warrior_berserker_burst(defender, attacker, round_num, events, log)
                if attacker.hp <= 0:
                    break
            _execute_attack(defender, attacker, round_num, events, log)
            if attacker.hp <= 0:
                break
        else:
            # F.1 Warrior Berserker Burst pro obránce (jde první v tomto pořadí)
            if defender.cfg.cls == "warrior" and defender.rage >= 100:
                _warrior_berserker_burst(defender, attacker, round_num, events, log)
                if attacker.hp <= 0:
                    break
            _execute_attack(defender, attacker, round_num, events, log)
            if attacker.hp <= 0:
                break
            # F.1 Warrior Berserker Burst pro útočníka (jde druhý v tomto pořadí)
            if attacker.cfg.cls == "warrior" and attacker.rage >= 100:
                _warrior_berserker_burst(attacker, defender, round_num, events, log)
                if defender.hp <= 0:
                    break
            dmg = _execute_attack(attacker, defender, round_num, events, log)
            total_dmg_by_attacker += dmg
            if defender.hp <= 0:
                break

        # ── T2 aktivní schopnost — každé 4. kolo ──────────────────────────
        if round_num % T2_COOLDOWN == 0:
            if attacker.talent_t2 and attacker.hp > 0:
                _execute_t2_ability(attacker, defender, events, log, round_num)
            if defender.hp <= 0:
                break
            if defender.talent_t2 and defender.hp > 0:
                _execute_t2_ability(defender, attacker, events, log, round_num)
            if attacker.hp <= 0:
                break

    # ── Výsledek ──────────────────────────────────────────────────────────────
    if defender.hp <= 0:
        attacker_won = True
        winner = "attacker"
        log.append(f"\n🏆 {attacker_cfg.name} zvítězil po {round_num} kolech!")
    elif attacker.hp <= 0:
        attacker_won = False
        winner = "defender"
        log.append(f"\n💀 {attacker_cfg.name} byl poražen v kole {round_num}.")
    else:
        # Timeout — kdo má více % HP
        a_pct = attacker.hp / attacker.hp_max
        d_pct = defender.hp / defender.hp_max
        attacker_won = a_pct >= d_pct
        winner = "attacker" if attacker_won else "defender"
        winner_name = attacker_cfg.name if attacker_won else defender_cfg.name
        log.append(f"\n⏰ Čas vypršel! Vítěz: {winner_name}.")

    events.append(CombatEvent(
        type=EVENT_COMBAT_END,
        round=round_num,
        actor=attacker_cfg.name if attacker_won else defender_cfg.name,
        target="",
        actor_hp=attacker.hp,
        target_hp=defender.hp,
        actor_hp_max=attacker.hp_max,
        target_hp_max=defender.hp_max,
        text=log[-1].strip(),
    ))

    return CombatResult(
        winner=winner,
        rounds=round_num,
        events=events,
        log=log,
        attacker_hp_remaining=max(0, attacker.hp),
        defender_hp_remaining=max(0, defender.hp),
        attacker_hp_max=attacker.hp_max,
        defender_hp_max=defender.hp_max,
        attacker_won=attacker_won,
        total_damage_dealt=total_dmg_by_attacker,
    )


# ── Zpětně kompatibilní adaptéry ───────────────────────────────────────────────

def events_to_dict_list(events: list[CombatEvent]) -> list[dict]:
    """Převede list[CombatEvent] na list[dict] pro JSON serializaci."""
    return [
        {
            "type":          e.type,
            "round":         e.round,
            "actor":         e.actor,
            "target":        e.target,
            "damage":        e.damage,
            "heal":          e.heal,
            "actor_hp":      e.actor_hp,
            "target_hp":     e.target_hp,
            "actor_hp_max":  e.actor_hp_max,
            "target_hp_max": e.target_hp_max,
            "is_crit":       e.is_crit,
            "ability_name":  e.ability_name,
            "ability_emoji": e.ability_emoji,
            "status_name":   e.status_name,
            "status_emoji":  e.status_emoji,
            "phase_num":     e.phase_num,
            "phase_msg":     e.phase_msg,
            "text":          e.text,
        }
        for e in events
    ]


def calculate_win_chance(attacker: CombatantConfig, defender: CombatantConfig) -> float:
    """
    Rychlý odhad šance na výhru bez simulace. Pro UI display.
    Používá soft-cappované hodnoty pro konzistenci s combat enginem.
    """
    from game.combat_stats import calc_damage_components as _cdc
    def power(c: CombatantConfig) -> float:
        base_dmg, _, _ = _cdc(c.cls or "", c.primary_stat, c.secondary_a, c.secondary_b, c.weapon_dmg)
        return (c.hp * 0.4
                + base_dmg * 2.5
                + c.armor_value * 1.5
                + soft_cap_stat(c.luck) * 0.5)

    a_pow = power(attacker)
    d_pow = power(defender)
    ratio = a_pow / max(1.0, a_pow + d_pow)
    return round(min(0.97, max(0.03, ratio)), 2)
