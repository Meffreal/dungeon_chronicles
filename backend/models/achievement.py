"""
models/achievement.py — Achievement systém + Achievement chains
"""
from datetime import datetime
from sqlalchemy import Integer, ForeignKey, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

# ── Definice achievementů ─────────────────────────────────────────────────────
# (id, name, desc, icon, category, points, title, condition_type, condition_value)
#
# title: string nebo None — titul odemčený splněním achievementu
#
# condition_type:
#   "level"         — char.level >= value
#   "quests"        — char.quests_completed >= value
#   "arena_wins"    — char.arena_wins >= value
#   "arena_fights"  — char.arena_wins + char.arena_losses >= value
#   "arena_rank"    — char.arena_rank >= value
#   "gold"          — char.gold >= value (aktuální)
#   "market_buys"   — počet koupených listingů >= value
#   "guild"         — char.guild_id is not None
#   "guild_leader"  — existuje guild kde leader_id == char.id
#   "legendary_item"— má v inventáři legendary item

ACHIEVEMENT_DEFINITIONS = [
    # ── LEVEL ──────────────────────────────────────────────────────────────
    (1,  "První kroky",        "Dosáhni levelu 2.",                  "👣", "level",   10,  None,               "level",          2),
    (2,  "Zkušený dobrodruh",  "Dosáhni levelu 5.",                  "⚔️", "level",   25,  None,               "level",          5),
    (3,  "Válečný veterán",    "Dosáhni levelu 10.",                 "🏆", "level",   50,  "Veterán",          "level",         10),
    (4,  "Mistr dungeonu",     "Dosáhni levelu 15.",                 "💪", "level",   75,  "Mistr dungeonu",   "level",         15),
    (5,  "Legenda",            "Dosáhni levelu 20.",                 "👑", "level",  100,  "Legenda",          "level",         20),
    (6,  "Nesmrtelný",         "Dosáhni levelu 25.",                 "⚡", "level",  200,  "Nesmrtelný",       "level",         25),

    # ── QUESTY ─────────────────────────────────────────────────────────────
    (7,  "První výzva",        "Dokonči svůj první quest.",          "📜", "quest",   10,  None,               "quests",         1),
    (8,  "Průzkumník",         "Dokonči 5 questů.",                  "🗺️", "quest",   25,  None,               "quests",         5),
    (9,  "Lovec odměn",        "Dokonči 10 questů.",                 "🎯", "quest",   50,  None,               "quests",        10),
    (10, "Neúnavný bojovník",  "Dokonči 25 questů.",                 "⚔️", "quest",   75,  None,               "quests",        25),
    (11, "Mistr questů",       "Dokonči 50 questů.",                 "🌟", "quest",  150,  "Lovec odměn",      "quests",        50),

    # ── ARÉNA ──────────────────────────────────────────────────────────────
    (12, "Arénní debut",       "Zúčastni se prvního arénního boje.", "🩸", "arena",   10,  None,               "arena_fights",   1),
    (13, "Krvavý vítěz",       "Vyhraj svůj první arénní boj.",      "🗡️", "arena",   15,  None,               "arena_wins",     1),
    (14, "Arénní bojovník",    "Vyhraj 10 bitev v aréně.",           "⚔️", "arena",   35,  None,               "arena_wins",    10),
    (15, "Gladiátor",          "Vyhraj 25 bitev v aréně.",           "🏟", "arena",   75,  "Gladiátor",        "arena_wins",    25),
    (16, "Šampión arény",      "Vyhraj 50 bitev v aréně.",           "🏆", "arena",  150,  "Šampión arény",    "arena_wins",    50),
    (17, "Elita",              "Dosáhni ELO ratingu 1 100.",         "💜", "arena",   50,  None,               "arena_rank",  1100),
    (18, "Mistr arény",        "Dosáhni ELO ratingu 1 200.",         "👑", "arena",  100,  "Mistr arény",      "arena_rank",  1200),

    # ── BOHATSTVÍ ──────────────────────────────────────────────────────────
    (19, "První zlatý",        "Nashromáždi 500 zlatých.",           "💰", "wealth",  10,  None,               "gold",         500),
    (20, "Zlatokop",           "Nashromáždi 5 000 zlatých.",         "💎", "wealth",  40,  None,               "gold",        5000),
    (21, "Boháč",              "Nashromáždi 10 000 zlatých.",        "🤑", "wealth",  80,  "Boháč",            "gold",       10000),

    # ── TRŽIŠTĚ ────────────────────────────────────────────────────────────
    (22, "Obchodník",          "Kup svůj první item na tržišti.",    "🛒", "market",  20,  None,               "market_buys",    1),
    (23, "Trhovník",           "Kup 10 itemů na tržišti.",           "💹", "market",  50,  None,               "market_buys",   10),

    # ── CECH ───────────────────────────────────────────────────────────────
    (24, "Sdružení",           "Vstup do cechu.",                    "⚜️", "guild",   20,  None,               "guild",          1),
    (25, "Zakladatel",         "Vytvoř vlastní cech.",               "🏰", "guild",   50,  "Zakladatel cechu", "guild_leader",   1),

    # ── SPECIÁLNÍ ──────────────────────────────────────────────────────────
    (26, "Sběratel legend",    "Získej legendární item.",            "✨", "special", 100, "Sběratel legend",  "legendary_item", 1),
]

ACHIEVEMENT_CATEGORY_NAMES = {
    "level":   "Úroveň",
    "quest":   "Questy",
    "arena":   "Aréna",
    "wealth":  "Bohatství",
    "market":  "Tržiště",
    "guild":   "Cech",
    "special": "Speciální",
}

# ── Achievement chains — propojené sekvence achievementů ──────────────────────
# steps: seznam achievement IDs v pořadí, které musí být odemčeny
# reward_crystals: krystaly za dokončení celého chainu
# reward_title: exkluzivní titul za dokončení
CHAIN_DEFINITIONS = [
    {
        "id":              "warrior_path",
        "name":            "Cesta Bojovníka",
        "desc":            "Projdi cestu od prvních kroků po legendu bojového umění.",
        "icon":            "⚔️",
        "steps":           [1, 2, 3, 4, 5],   # level 2, 5, 10, 15, 20
        "reward_crystals": 20,
        "reward_title":    "Legenda bojového umění",
    },
    {
        "id":              "arena_champion",
        "name":            "Šampión Arén",
        "desc":            "Zdolej všechny milníky arénního boje od debutu po 50 vítězství.",
        "icon":            "🏟",
        "steps":           [12, 13, 14, 15, 16],  # debut, 1W, 10W, 25W, 50W
        "reward_crystals": 25,
        "reward_title":    "Šampión Arén",
    },
    {
        "id":              "bounty_hunter",
        "name":            "Lovec Odměn",
        "desc":            "Splň questy od prvního po padesátý a staň se mistrem odměn.",
        "icon":            "📜",
        "steps":           [7, 8, 9, 10, 11],   # quests 1, 5, 10, 25, 50
        "reward_crystals": 15,
        "reward_title":    "Mistr lovce odměn",
    },
    {
        "id":              "wealth_ruler",
        "name":            "Vládce Zlatem",
        "desc":            "Nashromáždi jmění hodné krále od prvního zlatého po desítky tisíc.",
        "icon":            "💰",
        "steps":           [19, 20, 21],         # gold 500, 5000, 10000
        "reward_crystals": 15,
        "reward_title":    "Zlatý král",
    },
    {
        "id":              "adventurer",
        "name":            "Velký Dobrodruh",
        "desc":            "Prozkoumej tržiště, cech i tajemství legendárních předmětů.",
        "icon":            "🗺️",
        "steps":           [22, 24, 26],         # market buy, join guild, legendary item
        "reward_crystals": 15,
        "reward_title":    "Velký dobrodruh",
    },
]

# ── DB model — odemčené achievementy hráče ────────────────────────────────────
class PlayerAchievement(Base):
    __tablename__ = "player_achievements"

    id:           Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id"))
    achievement_id: Mapped[int] = mapped_column(Integer)
    unlocked_at:  Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    character = relationship("Character")

    def to_dict(self) -> dict:
        defn = next((a for a in ACHIEVEMENT_DEFINITIONS if a[0] == self.achievement_id), None)
        if not defn:
            return {}
        return {
            "id":          defn[0],
            "name":        defn[1],
            "desc":        defn[2],
            "icon":        defn[3],
            "category":    defn[4],
            "points":      defn[5],
            "title":       defn[6],
            "unlocked_at": self.unlocked_at.isoformat(),
        }


# ── DB model — dokončené achievement chainy hráče ────────────────────────────
class PlayerChainCompletion(Base):
    __tablename__ = "player_chain_completions"

    id:           Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id"))
    chain_id:     Mapped[str] = mapped_column(String(64))
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    character = relationship("Character")
