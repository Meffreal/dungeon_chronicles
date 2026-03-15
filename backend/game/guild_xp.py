"""
game/guild_xp.py — Guild Hall progression: levely, perky, award_guild_xp() helper
"""

GUILD_MAX_LEVEL = 10

# Perky per level
GUILD_LEVEL_PERKS = {
    1:  {"name": "Učni",       "emoji": "🌱", "member_cap": 20, "chat_history": 50,  "weekly_gold_pct": 0,  "unlock": "Startovní úroveň cechu."},
    2:  {"name": "Rekruti",    "emoji": "🔰", "member_cap": 20, "chat_history": 100, "weekly_gold_pct": 0,  "unlock": "Historie chatu: 100 zpráv."},
    3:  {"name": "Vojáci",     "emoji": "⚔",  "member_cap": 20, "chat_history": 100, "weekly_gold_pct": 5,  "unlock": "Týdenní quest: odměna +5 %."},
    4:  {"name": "Veteráni",   "emoji": "🛡",  "member_cap": 25, "chat_history": 100, "weekly_gold_pct": 5,  "unlock": "Kapacita: 25 členů."},
    5:  {"name": "Elita",      "emoji": "🌟",  "member_cap": 25, "chat_history": 100, "weekly_gold_pct": 10, "unlock": "Týdenní quest: odměna +10 %."},
    6:  {"name": "Šampioni",   "emoji": "💎",  "member_cap": 25, "chat_history": 200, "weekly_gold_pct": 10, "unlock": "Historie chatu: 200 zpráv."},
    7:  {"name": "Rytíři",     "emoji": "⚡",  "member_cap": 30, "chat_history": 200, "weekly_gold_pct": 15, "unlock": "Kapacita: 30 členů."},
    8:  {"name": "Hrdinové",   "emoji": "🔥",  "member_cap": 30, "chat_history": 200, "weekly_gold_pct": 20, "unlock": "Týdenní quest: odměna +20 %."},
    9:  {"name": "Legendy",    "emoji": "👑",  "member_cap": 35, "chat_history": 200, "weekly_gold_pct": 25, "unlock": "Kapacita: 35 členů."},
    10: {"name": "Nesmrtelní", "emoji": "✨",  "member_cap": 35, "chat_history": 200, "weekly_gold_pct": 25, "unlock": "Exkluzivní titul pro všechny členy."},
}

GUILD_LV10_TITLE = "Člen Nesmrtelných"


def xp_to_next(level: int) -> int:
    """XP potřebné pro level-up z daného levelu."""
    if level >= GUILD_MAX_LEVEL:
        return 0
    return level * 500


def get_perks(level: int) -> dict:
    return GUILD_LEVEL_PERKS.get(min(max(level, 1), GUILD_MAX_LEVEL), GUILD_LEVEL_PERKS[1])


def award_guild_xp(guild, amount: int) -> bool:
    """
    Přidá XP cechu a zpracuje level-up (cap na GUILD_MAX_LEVEL).
    Vrátí True pokud cech právě postoupil na nový level.
    """
    if guild.level >= GUILD_MAX_LEVEL:
        return False
    guild.xp += amount
    needed = xp_to_next(guild.level)
    if guild.xp >= needed:
        guild.xp   -= needed
        guild.level += 1
        return True
    return False
