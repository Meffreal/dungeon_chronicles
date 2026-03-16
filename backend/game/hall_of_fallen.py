"""
game/hall_of_fallen.py — Helper pro zápis do Hall of the Fallen při permadeath
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from models.character import Character


async def record_death_in_hall(char: "Character", db: "AsyncSession") -> None:
    """
    Zapíše padlého hrdinu do Hall of the Fallen.
    Volat těsně po nastavení char.is_dead = True a char.died_at.
    """
    from models.hall_of_fallen import HallOfFallen

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    died_at = getattr(char, 'died_at', None) or now
    created_at = getattr(char, 'created_at', None) or now

    if created_at and getattr(created_at, 'tzinfo', None) is not None:
        created_at = created_at.replace(tzinfo=None)
    days_survived = max(0, (died_at - created_at).days) if died_at and created_at else 0

    # Build snapshot — talents, subclass, stats
    build_snapshot = {
        "talent":    getattr(char, 'talent_key', None),
        "talent_t2": getattr(char, 'talent_t2_key', None),
        "subclass":  getattr(char, 'subclass_key', None),
        "stats": {
            "hp":  getattr(char, 'max_hp', 0),
            "atk": getattr(char, 'atk', 0),
            "def": getattr(char, 'def_', 0),
            "spd": getattr(char, 'spd', 0),
        },
    }

    entry = HallOfFallen(
        user_id=char.user_id,
        character_id=char.id,
        hero_name=char.name,
        hero_cls=char.cls,
        hero_level=char.level,
        hero_faction=getattr(char, 'faction', None),
        killed_by=getattr(char, 'killed_by', None),
        death_dungeon=getattr(char, 'death_dungeon', None),
        died_at=died_at,
        days_survived=days_survived,
        dungeons_cleared=0,  # TODO: napojit na DungeonRun count
        build_snapshot=build_snapshot,
        recorded_at=now,
    )
    db.add(entry)
    await db.flush()
