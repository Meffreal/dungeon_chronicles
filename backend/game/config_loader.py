"""
game/config_loader.py — Načítání herních dat z JSON konfigurace.
Nový quest/dungeon/boss = nový řádek/soubor bez deploymentu.
"""
import json
from pathlib import Path

CONFIG_DIR = Path(__file__).parent.parent / "config"


def _load(filename: str):
    with open(CONFIG_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def load_quest_definitions() -> list:
    """Vrátí questy jako listy (kompatibilní s qdef[index] přístupem)."""
    return _load("quests.json")


def load_guild_bosses() -> list[dict]:
    return _load("guild_bosses.json")


def load_attunement_chains() -> list[dict]:
    return _load("attunements.json")


def load_dungeon_config() -> list[dict]:
    return _load("dungeons.json")


def reload_config() -> dict:
    """Znovu načte questy z JSON a aktualizuje modul models.quest (bez restartu).

    Volá se z admin endpointu POST /admin/config/reload nebo automaticky
    po vytvoření nového questu přes POST /admin/quest/create.
    """
    import models.quest as quest_module
    quests = load_quest_definitions()
    quest_module.QUEST_DEFINITIONS = quests
    return {"quest_count": len(quests)}
