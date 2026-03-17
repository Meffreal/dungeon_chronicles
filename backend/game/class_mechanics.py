"""
game/class_mechanics.py — Asymetrické třídní mechaniky pro HC Gauntlet

Každá třída má pasivní systém který mění průběh boje.
Tyto mechaniky se aplikují jako modifikátory v combat_engine.py.

Integrace s _FighterState:
- Warrior rage_stacks a base_atk jsou uloženy jako atributy na _FighterState
- Chain hity a multi-hit kola se volají z hlavního combat loopu
- Mage opening crit / spell_burn / spirit_revenge mají příznaky na _FighterState

F.1 — Rage (Warrior):
  - Každý přijatý úder zvyšuje ATK o 3% base ATK (stacks, max 10 = +30%)
  - Při HP < 30%: Berserker Mode — ATK +50%, DEF -20%
  - Pasivní: imunita na stun

F.2 — Chain (Ranger):
  - Po každém hitu: 25% šance na bonus hit (nelze chainovat znovu)
  - Multi-target aura: každé 3. kolo útočí 2× místo 1×
  - Pasivní: v kole 1 vždy útočí první (nezávisle na SPD)

F.3 — First Strike (Mage):
  - Pokud SPD > nepřítel: v kole 1 guaranteed critical
  - Spell burn: každý útok zanechá burn DoT (3% max HP nepřítele za kolo)
  - Pasivní: pokud zemře v kole 1 → spirit revenge (nepřítel ztratí 20% max HP)
"""
from __future__ import annotations


# ── Rage (Warrior) ─────────────────────────────────────────────────────────────
RAGE_ATK_PER_HIT_RECEIVED  = 0.03   # +3% base ATK za každý přijatý hit
RAGE_MAX_STACKS            = 10     # max 10 stacků → +30% ATK
RAGE_BERSERK_HP_THRESHOLD  = 0.30   # Berserker Mode aktivní při HP < 30% max HP
RAGE_BERSERK_ATK_BONUS     = 0.50   # +50% ATK v berserku (stacks na vrchol rage)
RAGE_BERSERK_DEF_PENALTY   = -0.20  # -20% DEF v berserku


def apply_rage_on_hit_received(rage_stacks: int, base_atk: int) -> tuple[int, int]:
    """
    Volat poté, co warrior obdrží úspěšný hit.

    Args:
        rage_stacks: aktuální počet stacků (z _FighterState.rage_stacks)
        base_atk:    základní ATK bez rage bonus (z _FighterState.base_atk)

    Returns:
        (new_stacks, new_atk) — nové hodnoty pro uložení zpět do _FighterState
    """
    new_stacks = min(rage_stacks + 1, RAGE_MAX_STACKS)
    new_atk    = int(base_atk * (1.0 + new_stacks * RAGE_ATK_PER_HIT_RECEIVED))
    return new_stacks, new_atk


def check_berserk_mode(current_hp: int, hp_max: int) -> dict:
    """
    Vrátí multiplikátory pro Berserker Mode.

    Args:
        current_hp: aktuální HP warriors
        hp_max:     maximální HP warriors

    Returns:
        {"is_berserk": bool, "atk_mult": float, "def_mult": float}
    """
    if hp_max > 0 and current_hp / hp_max < RAGE_BERSERK_HP_THRESHOLD:
        return {
            "is_berserk": True,
            "atk_mult":   1.0 + RAGE_BERSERK_ATK_BONUS,
            "def_mult":   1.0 + RAGE_BERSERK_DEF_PENALTY,
        }
    return {"is_berserk": False, "atk_mult": 1.0, "def_mult": 1.0}


def warrior_is_stun_immune() -> bool:
    """Warrior má permanentní imunitu na stun — stun efekt se nepřipojí."""
    return True


# ── Chain (Ranger) ─────────────────────────────────────────────────────────────
CHAIN_BONUS_HIT_CHANCE   = 0.25   # 25% šance na chain (bonus) hit po útoku
CHAIN_MULTI_HIT_EVERY_N  = 3      # každé N-té kolo ranger útočí 2× místo 1×


def check_chain_hit(rng_roll: float) -> bool:
    """
    Vrátí True pokud se aktivuje chain (bonus) hit.
    Chain nesmí dále řetězit — volat pouze jednou po primárním hitu.

    Args:
        rng_roll: float 0.0–1.0 (z random.random())
    """
    return rng_roll < CHAIN_BONUS_HIT_CHANCE


def check_multi_hit_round(round_num: int) -> bool:
    """
    Vrátí True pokud je toto kolo multi-hit kolo (každé CHAIN_MULTI_HIT_EVERY_N).
    round_num: 1-based číslo kola.
    """
    return round_num >= CHAIN_MULTI_HIT_EVERY_N and round_num % CHAIN_MULTI_HIT_EVERY_N == 0


def ranger_first_round_first_strike() -> bool:
    """Ranger vždy útočí první v kole 1 bez ohledu na SPD porovnání."""
    return True


# ── First Strike (Mage) ────────────────────────────────────────────────────────
MAGE_SPELL_BURN_PCT      = 0.03   # burn DoT za kolo = 3% z max HP nepřítele
MAGE_SPIRIT_REVENGE_PCT  = 0.20   # Spirit Revenge škoda = 20% z max HP nepřítele


def calculate_spell_burn_damage(enemy_hp_max: int) -> int:
    """
    Burn DoT aplikovaný po každém útoku mage.
    Vrátí celé číslo — minimálně 1.
    """
    return max(1, int(enemy_hp_max * MAGE_SPELL_BURN_PCT))


def check_spirit_revenge_trigger(mage_died_round: int) -> bool:
    """Spirit Revenge se aktivuje pouze pokud mage zemřel v kole 1."""
    return mage_died_round == 1


def calculate_spirit_revenge_damage(enemy_hp_max: int) -> int:
    """Spirit Revenge okamžitý damage = 20% z max HP nepřítele."""
    return max(1, int(enemy_hp_max * MAGE_SPIRIT_REVENGE_PCT))


# ── Class mechanics registry ───────────────────────────────────────────────────
CLASS_MECHANICS: dict[str, dict] = {
    "warrior": {
        "name": "Rage",
        "description": (
            "Každý přijatý úder zvyšuje ATK o 3% (max +30%). "
            "Při HP < 30%: Berserker Mode (+50% ATK, -20% DEF). "
            "Imunita na stun."
        ),
        "passives": ["rage_stacks", "berserk_mode", "stun_immune"],
        "constants": {
            "rage_atk_per_hit": RAGE_ATK_PER_HIT_RECEIVED,
            "rage_max_stacks":  RAGE_MAX_STACKS,
            "berserk_threshold": RAGE_BERSERK_HP_THRESHOLD,
        },
    },
    "ranger": {
        "name": "Chain",
        "description": (
            "25% šance na bonus hit po každém útoku. "
            "Každé 3. kolo: dvojitý útok. "
            "V kole 1 vždy útočí první bez ohledu na SPD."
        ),
        "passives": ["chain_hit", "multi_hit", "first_round_first_strike"],
        "constants": {
            "chain_chance":     CHAIN_BONUS_HIT_CHANCE,
            "multi_hit_every":  CHAIN_MULTI_HIT_EVERY_N,
        },
    },
    "mage": {
        "name": "First Strike",
        "description": (
            "Při vyšší SPD než nepřítel: guaranteed crit v kole 1. "
            "Každý útok aplikuje burn DoT (3% max HP/kolo). "
            "Spirit Revenge: pokud mage zemře v kole 1, nepřítel ztratí 20% max HP."
        ),
        "passives": ["opening_crit", "spell_burn", "spirit_revenge"],
        "constants": {
            "spell_burn_pct":      MAGE_SPELL_BURN_PCT,
            "spirit_revenge_pct":  MAGE_SPIRIT_REVENGE_PCT,
        },
    },
}


def get_class_mechanics(cls: str) -> dict:
    """
    Vrátí mechanics dict pro danou třídu.
    Vrátí prázdný dict pro neznámé třídy (AI monster, boss).
    """
    return CLASS_MECHANICS.get(cls.lower(), {})
