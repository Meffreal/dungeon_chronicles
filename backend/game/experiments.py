"""
game/experiments.py — Helper pro A/B testovací framework.

Načítá aktivní experimenty z DB a vrací merged override dict pro danou skupinu hráče.
Používá 10s in-memory cache aby se DB nepřetěžovalo při každém souboji.
"""
import time
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# ── Cache ────────────────────────────────────────────────────────────────────
_cache_data:      Optional[list] = None   # list[Experiment]
_cache_timestamp: float = 0.0
_CACHE_TTL:       float = 10.0            # 10 sekund TTL


def _cache_is_valid() -> bool:
    return _cache_data is not None and (time.monotonic() - _cache_timestamp) < _CACHE_TTL


def invalidate_experiment_cache():
    """Zavolej po změně experimentů v admin panelu."""
    global _cache_data, _cache_timestamp
    _cache_data      = None
    _cache_timestamp = 0.0


async def _load_experiments(db: AsyncSession) -> list:
    """Načte aktivní experimenty z DB a aktualizuje cache."""
    global _cache_data, _cache_timestamp
    from models.experiment import Experiment
    res = await db.execute(select(Experiment).where(Experiment.is_active == True))
    experiments = list(res.scalars().all())
    _cache_data      = experiments
    _cache_timestamp = time.monotonic()
    return experiments


async def get_experiment_overrides(group: int, db: AsyncSession) -> dict:
    """
    Vrátí merged override dict pro danou experiment_group.
    Pokud více experimentů pokrývá stejnou skupinu, novější (vyšší ID) vítězí.
    """
    if _cache_is_valid():
        experiments = _cache_data
    else:
        experiments = await _load_experiments(db)

    merged: dict = {}
    # Seřaď vzestupně — novější přepíší starší
    for exp in sorted(experiments, key=lambda e: e.id):
        if exp.applies_to_group(group):
            merged.update(exp.get_overrides())

    return merged


def apply_overrides_to_engine(overrides: dict) -> dict:
    """
    Normalizuje override dict pro použití v combat engine.
    Vrátí jen klíče relevantní pro engine (ostatní jsou pro routery).
    """
    engine_keys = {"ability_trigger_prob", "crit_damage_mult", "ability_damage_mult", "dodge_chance_cap"}
    return {k: v for k, v in overrides.items() if k in engine_keys}


def apply_overrides_to_router(overrides: dict) -> dict:
    """
    Normalizuje override dict pro použití v routerech (quest/arena rewards).
    """
    router_keys = {"gold_reward_win", "xp_reward_mult"}
    return {k: v for k, v in overrides.items() if k in router_keys}
