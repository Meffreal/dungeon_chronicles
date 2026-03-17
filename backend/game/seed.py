"""
game/seed.py — Naplní databázi počátečními itemy
Spusť: python game/seed.py
"""
import asyncio
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db, AsyncSessionLocal
from core.logging import get_logger

log = get_logger(__name__)

# Všechny modely musí být importovány aby SQLAlchemy vyřešilo relationships
from models.user         import User             # noqa: F401
from models.item         import Item, Rarity, ItemType, InventoryItem  # noqa: F401
from models.guild        import Guild            # noqa: F401
from models.character    import Character        # noqa: F401
from models.quest        import Quest            # noqa: F401
from models.market       import MarketListing    # noqa: F401
from models.notification import Notification     # noqa: F401
from models.arena        import ArenaMatch       # noqa: F401
from models.faction      import FactionReputation  # noqa: F401
from models.achievement  import PlayerAchievement  # noqa: F401

SEED_ITEMS = [
    # ── WEAPONS ──────────────────────────────────────────────────────────────
    # Common
    ("Rezavý meč",       "weapon", "common",    "Starý meč s rezavou čepelí.",       "⚔️",  5, 0, 0, 0, 0, 0,0,0,0,0, 1,  8),
    ("Dřevěná hůl",      "weapon", "common",    "Obyčejná dřevěná hůl.",             "🪄",  4, 0, 0, 0, 0, 0,0,4,0,0, 1,  6),
    ("Lovecký luk",      "weapon", "common",    "Primitivní luk z kmene stromu.",    "🏹",  4, 0, 0, 0, 0, 0,4,0,0,0, 1,  7),
    # Uncommon
    ("Železný meč",      "weapon", "uncommon",  "Spolehlivý meč zkušeného bojovníka.","⚔️", 14, 0, 1, 0, 0, 4,0,0,0,0, 3, 35),
    ("Učňovská hůl",     "weapon", "uncommon",  "Hůl začínajícího mága.",            "🪄",  9, 0, 2, 0, 0, 0,0,7,0,0, 3, 30),
    ("Kompozitní luk",   "weapon", "uncommon",  "Silnější luk z vrstveného dřeva.",  "🏹", 11, 0, 1, 0, 0, 0,6,0,0,3, 3, 32),
    # Rare
    ("Stříbrná čepel",   "weapon", "rare",      "Zbraň kovaná ze stříbra.",          "🗡️", 25, 0, 2, 5, 0, 6,0,0,0,3, 6, 120),
    ("Ohnivá hůl",       "weapon", "rare",      "Hůl naplněná ohnivou magií.",       "🔥", 17, 0, 3,15, 0, 0,0,13,0,0, 6, 110),
    ("Elfský luk",       "weapon", "rare",      "Elegantní luk z elfího dřeva.",     "🏹", 21, 0, 2, 8, 0, 0,11,0,0,5, 6, 115),
    # Epic
    ("Démonická čepel",  "weapon", "epic",      "Meč zkovaný v pekelném ohni.",      "😈", 42, 0, 4,10, 0, 9,0,0,7,0,12, 400),
    ("Chaos hůl",        "weapon", "epic",      "Hůl překypující chaotickou mocí.",  "💜", 28, 0, 5,30, 0, 0,0,22,0,0,12, 380),
    ("Stínový luk",      "weapon", "epic",      "Luk z temné energie utkaný.",       "🌑", 34, 0, 5,20, 0, 0,18,0,0,11,12, 390),
    # Legendary
    ("Excalibur",        "weapon", "legendary", "Legendární meč krále Artuše.",      "✨", 65,13, 8,15, 0,16,8, 0,11,7,20,2000),
    ("Žezlo věčnosti",   "weapon", "legendary", "Artefakt staré civilizace.",        "⚡", 45, 5,10,60, 0, 0,0,30,0,0,20,1800),
    ("Luk osudu",        "weapon", "legendary", "Střela tohoto luku nikdy nechybí.", "🌟", 55,10, 8,25, 0, 0,26,7,0,20,20,1900),
    ("Meffova hůlka osudu",   "weapon", "legendary", "Hůlka, která určuje osud.",        "🪥", 55, 15,30,120, 0, 0,0,100,0,0,20,1800),

    # ── ARMOR ────────────────────────────────────────────────────────────────
    # Common
    ("Kožená zbroj",     "armor",  "common",    "Základní ochrana z kůže.",          "🥋",  0, 6, 0, 0, 0, 0,0,0,2,0, 1, 10),
    ("Vlněný plášť",     "armor",  "common",    "Teplý vlněný plášť.",               "🧥",  0, 5, 0, 5, 0, 0,0,2,1,0, 1,  9),
    # Uncommon
    ("Pletivo",          "armor",  "uncommon",  "Ochranné kroužkové brnění.",        "🛡️",  0,17, 0, 0, 0, 0,0,0,5,0, 3, 50),
    ("Enchantovaný plášť","armor", "uncommon",  "Magicky posílený plášť.",           "✨",  0,10, 0,24, 0, 0,0,5,4,0, 3, 45),
    # Rare
    ("Plátové brnění",   "armor",  "rare",      "Těžké plátové brnění rytíře.",      "⚔️",  0,28, 0, 0, 0, 6,0,0,10,0, 6, 180),
    ("Runový plášť",     "armor",  "rare",      "Plášť pokrytý runami moci.",        "🔮",  0,15, 0,40,25, 0,0,9,5,0, 6, 165),
    # Epic & Legendary
    ("Brnění draka",     "armor",  "epic",      "Zkované z šupin draka.",            "🐲",  0,44,12, 0, 0,12,0,8,15,0,12, 650),
    ("Nebeská zbroj",    "armor",  "legendary", "Dar samotných bohů.",               "🌤️",  0,65,15,20, 0,15,8,12,18,13,20,3000),

    # ── HELMETS ──────────────────────────────────────────────────────────────
    ("Kožená čapka",     "helmet", "common",    "Jednoduchá kožená ochrana hlavy.",  "🪖",  0, 3, 0, 0, 0, 0,0,0,1,0, 1,  6),
    ("Železná helma",    "helmet", "uncommon",  "Solidní železná helma.",            "⛑️",  0,11, 0, 0, 0, 3,0,0,3,0, 3, 42),
    ("Arkanická koruna", "helmet", "rare",      "Koruna zasvěcená magii.",           "👑",  0, 7, 0,28, 0, 0,0,10,3,3, 6, 160),
    ("Korunka draka",    "helmet", "epic",      "Koruna z drakovy lebky.",           "🐉",  0,20, 5,18, 0, 6,4,10,7,4,12, 550),

    # ── BOOTS ────────────────────────────────────────────────────────────────
    ("Kožené boty",      "boots",  "common",    "Pohodlné kožené boty.",             "👢",  0, 2, 2, 0, 0, 0,1,0,0,0, 1,  5),
    ("Boty větru",       "boots",  "uncommon",  "Lehké boty zvyšující rychlost.",    "💨",  0, 5, 8, 0, 0, 0,5,0,0,3, 3, 40),
    ("Stínové boty",     "boots",  "rare",      "Pohyb v nich nevydává zvuk.",       "🌑",  0, 8,15, 0, 0, 0,8,0,0,6, 6, 140),

    # ── RINGS & AMULETS ──────────────────────────────────────────────────────
    ("Prsten síly",      "ring",   "uncommon",  "Zesiluje fyzickou sílu.",           "💪",  0, 0, 0, 0, 0, 8,0,0,0,0, 3, 38),
    ("Prsten magie",     "ring",   "uncommon",  "Zesiluje magické schopnosti.",      "🔮",  0, 0, 0,14, 0, 0,0,6,0,0, 3, 36),
    ("Prsten štěstí",    "ring",   "rare",      "Přináší štěstí nositeli.",          "🍀",  0, 0, 3, 8, 0, 0,3,0,0,12, 6, 130),
    ("Amulet ochrany",   "amulet", "uncommon",  "Chrání nositele před zlem.",        "🧿",  0, 7, 0, 8,14, 0,0,4,3,3, 3, 44),
    ("Amulet draka",     "amulet", "legendary", "Dává moc prastarého draka.",        "🐲",  0,18, 8,25, 0,10,8,10,12,8,20,2500),

    # ── GLOVES ───────────────────────────────────────────────────────────────
    ("Kožené rukavice",  "gloves", "common",    "Chrání ruce v boji.",               "🧤",  0, 2, 0, 0, 0, 2,0,0,0,0, 1,  5),
    ("Bojové rukavice",  "gloves", "uncommon",  "Rukavice ostřílených bojovníků.",   "👊",  0, 5, 0, 0, 0, 6,0,0,2,0, 3, 38),
    ("Runové rukavice",  "gloves", "rare",      "Runy na nich zesilují kouzla.",     "✨",  0, 4, 0,18, 0, 0,0,7,2,2, 6, 145),
    ("Rukavice vraha",   "gloves", "epic",      "Rukavice skrz něž proudí tma.",     "🩸",  0, 7, 7, 0, 0, 8,10,0,0,6,12, 480),
    ("Rukavice titána",  "gloves", "legendary", "Kdysi patřily titánovi válek.",     "⚡",  0,10,10,38, 0,16,8,0,7,7,20,2200),

    # ── WEAPONS (rozšíření) ───────────────────────────────────────────────────
    ("Krvavá šavle",     "weapon", "rare",      "Čepel napitá krví nepřátel.",       "🩸", 23, 0, 4, 0, 0, 7,3,0,0,4, 7, 125),
    ("Duševní zlomitel", "weapon", "epic",      "Hůl roztrhávající mysl protivníka.","💀", 22, 0, 3,25, 0, 0,0,26,0,0,13, 420),
    ("Hrom a blesk",     "weapon", "legendary", "Zbraň kovaná z blesku samotného.",  "⚡", 60, 7,12,22, 0,13,12,8,7,11,20,2100),

    # ── ARMOR (rozšíření) ─────────────────────────────────────────────────────
    ("Elfské roucho",    "armor",  "rare",      "Lehké roucho tkané elfy.",          "🌿",  0,12, 5,28, 0, 0,6,7,3,4, 7, 170),
    ("Titanské brnění",  "armor",  "epic",      "Brnění z kovu titan, neprůstřelné.","🏔️",  0,54,10, 0, 0,16,0,0,18,0,13, 700),

    # ── HELMETS (rozšíření) ───────────────────────────────────────────────────
    ("Druidská čelenka", "helmet", "rare",      "Čelenka s magií přírody.",          "🌿",  0, 8, 4,24, 0, 0,4,8,3,5, 7, 155),
    ("Stínová maska",    "helmet", "epic",      "Skrývá tvář i duši nositele.",      "🎭",  0,18, 6, 0, 0, 5,10,3,6,7,13, 560),
    ("Koruna věčnosti",  "helmet", "legendary", "Korunuje toho, kdo přežil vše.",    "👑",  0,30,10,36, 0,13,9,14,11,11,20,3200),

    # ── BOOTS (rozšíření) ─────────────────────────────────────────────────────
    ("Démonické boty",   "boots",  "epic",      "Boty z kůže démona. Rychlé.",       "😈",  0,10,22, 0, 0, 0,14,0,0,8,13, 510),
    ("Boty boha větru",  "boots",  "legendary", "Nositel se pohybuje jako vítr.",    "💨",  0,10,38,25, 0, 0,20,0,0,13,20,2300),

    # ── RINGS (rozšíření) ─────────────────────────────────────────────────────
    ("Prsten krve",      "ring",   "epic",      "Saje životní sílu nepřátel.",       "🩸",  0, 0, 3,25, 0,12,0,0,0,6,13, 430),
    ("Prsten věčnosti",  "ring",   "legendary", "Kdo ho nosí, je blíže nesmrtelnosti.","⚡", 0,10,10,50, 0, 9,9,9,8,14,20,2400),

    # ── AMULETS (rozšíření) ───────────────────────────────────────────────────
    ("Přívěsek lesa",    "amulet", "rare",      "Lesní magie chrání nositele.",      "🌿",  0,10, 6,20, 0, 0,5,7,5,7, 7, 160),
    ("Amulet bouře",     "amulet", "epic",      "Přívěsek nabíjený bleskem.",        "⛈️",  0, 8, 8,20, 0, 7,7,12,4,6,13, 520),

    # ── INT / MAGE ITEMS (doplnění chybějících slotů) ─────────────────────────
    # Common
    ("Čelenka studenta",      "helmet", "common",    "Jednoduchá čelenka začínajícího mága.",       "🎓",  0, 2, 0, 0, 0, 0,0,2,1,1, 1,  7),
    ("Říza novice",           "armor",  "common",    "Lehká říza pro začátečníky v magii.",          "👘",  0, 3, 0, 3, 0, 0,0,2,1,0, 1,  9),
    # Uncommon
    ("Mystické boty",         "boots",  "uncommon",  "Boty posílené magickými runami.",              "✨",  0, 3, 5, 0, 0, 0,0,3,1,1, 3, 38),
    ("Rukavice mága",         "gloves", "uncommon",  "Tenké rukavice zesilující magii.",             "🌟",  0, 3, 0, 0, 0, 0,0,4,1,1, 3, 36),
    # Rare
    ("Runové boty",           "boots",  "rare",      "Boty pokryté runami staré magie.",             "🔮",  0, 5, 8, 0, 0, 0,2,7,2,2, 6, 138),
    ("Prsten myslitele",      "ring",   "rare",      "Prsten zostřující mysl svého nositele.",       "💙",  0, 0, 0,12, 0, 0,0,8,0,3, 6, 128),
    # Epic
    ("Arkanické boty",        "boots",  "epic",      "Boty prosycené arkánnou energií.",             "💜",  0, 8,16, 0, 0, 0,4,12,2,2,12, 490),
    ("Prsten arcána",         "ring",   "epic",      "Prsten koncentrující magickou sílu.",          "🔵",  0, 0, 0,20, 0, 0,0,16,0,4,12, 420),
    ("Rukavice čaroděje",     "gloves", "epic",      "Rukavice starověkých čarodějů.",               "🌌",  0, 6, 5, 0, 0, 0,3,16,2,2,12, 470),
    # Legendary
    ("Boty věčné moudrosti",  "boots",  "legendary", "Boty nesoucí moudrost tisíce mágů.",           "🌠",  0,10,28,22, 0, 0,5,20,4,6,20,2250),
    ("Prsten Velekouzlíka",   "ring",   "legendary", "Prsten Velekouzlíka z dávných věků.",          "💎",  0, 0, 0,40, 0, 0,0,24,0,8,20,2350),
    ("Rukavice Velekouzlíka", "gloves", "legendary", "Rukavice naplněné silou největšího mága.",     "⚡",  0,10, 8,28, 0, 0,5,24,5,6,20,2150),

    # ── POTIONS / SCROLLS / ELIXIRS ──────────────────────────────────────────
    # bonus_xp = XP okamžitě při použití (svitky)
    # bonus_str/dex/int/end/luck = dočasný buff (common=1d, uncommon=2d, rare=3d, epic/leg=3d)
    ("Lektvar síly",          "potion","common",   "+1 Síla po dobu 1 dne.",                   "🧪",  0,0,0,0,  0, 1,0,0,0,0, 1, 20),
    ("Lektvar obratnosti",    "potion","common",   "+1 Obratnost po dobu 1 dne.",              "🧪",  0,0,0,0,  0, 0,1,0,0,0, 1, 20),
    ("Lektvar magie",         "potion","common",   "+1 Inteligence po dobu 1 dne.",            "🔮",  0,0,0,0,  0, 0,0,1,0,0, 1, 20),
    ("Lektvar výdrže",        "potion","common",   "+1 Výdrž po dobu 1 dne.",                  "🧪",  0,0,0,0,  0, 0,0,0,1,0, 1, 20),
    ("Lektvar štěstí",        "potion","uncommon", "+1 Štěstí po dobu 2 dnů.",                 "🍀",  0,0,0,0,  0, 0,0,0,0,1, 1, 40),
    ("Svitek zkušeností",     "potion","uncommon", "Okamžitě přidá 80 XP.",                    "📜",  0,0,0,0, 80, 0,0,0,0,0, 1, 50),
    ("Velký svitek zkušeností","potion","rare",    "Okamžitě přidá 220 XP.",                   "📜",  0,0,0,0,220, 0,0,0,0,0, 5,130),
    ("Elixír hrdinství",      "potion","rare",     "+2 Síla, +1 Výdrž po dobu 3 dnů.",         "⚗️", 0,0,0,0,  0, 2,0,0,1,0, 5,120),
    ("Elixír moudrosti",      "potion","rare",     "+2 Inteligence, +1 Štěstí po 3 dny.",      "⚗️", 0,0,0,0,  0, 0,0,2,0,1, 5,120),
    ("Elixír titána",         "potion","epic",     "+2 ke všem primárním statům na 3 dny.",    "🧬",  0,0,0,0,  0, 2,2,2,2,2,10,450),
    ("Božský nektar",         "potion","legendary","+5 ke všem primárním statům na 3 dny.",   "✨",  0,0,0,0,  0, 5,5,5,5,5,15,2000),
]

# ── SETOVÉ ITEMY ─────────────────────────────────────────────────────────────
# Formát: (name, itype, desc, icon, atk, def_, spd, hp, mp(ignorováno),
#           s_str, s_dex, s_int, s_end, s_luck, min_lv, sell, set_id, set_name)
# rarity je vždy "set"

SEED_SET_ITEMS = [
    # ── WARRIOR SET — "Sada Titanovy Krve" (set_id=1) ─────────────────────────
    ("Titanův Bijec",         "weapon", "Mohutný kladivo zkovaný z titanovy krve. Ničivá síla každého úderů.",
     "⚒️",  70, 5, 3, 30, 0, 14, 0, 0, 6, 0,  20, 3500, 1, "Sada Titanovy Krve"),
    ("Přilba Titanovy Krve",  "helmet", "Těžká přilba nesoucí znamení titána. Chrání hlavu i duši.",
     "⛑️",   0,35, 0, 70, 0,  8, 0, 0,12, 0,  20, 2800, 1, "Sada Titanovy Krve"),
    ("Kyrys Titanovy Krve",   "armor",  "Neprorazitelný kyrys z kovu titána. Chrání jako hora.",
     "🏔️",   0,60, 0,110, 0, 10, 0, 0,16, 0,  20, 4000, 1, "Sada Titanovy Krve"),
    ("Pěsti Titana",          "gloves", "Rukavice zesílené titanovou magií. Každý úder otřásá zemí.",
     "💪",   0,12, 0,  0, 0, 16, 0, 0, 4, 0,  20, 2500, 1, "Sada Titanovy Krve"),
    ("Boty Titana",           "boots",  "Masivní boty z titanovy kůže. Pevný krok nepřítele zastraší.",
     "👢",   0,18, 8,  0, 0,  5, 0, 0, 8, 0,  20, 2200, 1, "Sada Titanovy Krve"),
    ("Pečeť Titána",          "ring",   "Prsten nesoucí pečeť titána. Zesiluje každý útok nositele.",
     "💍",   0, 0, 0,  0, 0, 14, 0, 0, 4, 0,  20, 2000, 1, "Sada Titanovy Krve"),
    ("Duše Titána",           "amulet", "Amulet obsahující duši dávného titána. Přetéká surovou mocí.",
     "🔮",   0, 0, 0, 90, 0, 12, 0, 0,10, 0,  20, 2300, 1, "Sada Titanovy Krve"),

    # ── MAGE SET — "Sada Arkanního Mistra" (set_id=2) ─────────────────────────
    ("Žezlo Arkanního Mistra",    "weapon", "Starověké žezlo naplněné arkánnou mocí. Kouzla z něj vylétají jako blesky.",
     "⚡",  50, 0, 5,  0,50,  0, 0,18, 0, 0,  20, 3500, 2, "Sada Arkanního Mistra"),
    ("Koruna Arkanních Mistrů",   "helmet", "Koruna zasvěcená prastaré magii. Mysl nositele je jasná jako křišťál.",
     "👑",   0,18, 0,  0,40,  0, 0,16, 0, 7,  20, 2800, 2, "Sada Arkanního Mistra"),
    ("Roucho Arkanního Mistra",   "armor",  "Roucho tkaná z čisté arkánné energie. Lehké, ale magicky odolné.",
     "✨",   0,30, 0, 20,80,  0, 0,18, 0, 0,  20, 4000, 2, "Sada Arkanního Mistra"),
    ("Rukavice Arkanního Mistra", "gloves", "Rukavice zesilující magické schopnosti. Kouzla proudí snáze.",
     "🌟",   0, 0, 3,  0,20,  0, 0,20, 0, 0,  20, 2500, 2, "Sada Arkanního Mistra"),
    ("Sandály Arkanního Mistra",  "boots",  "Lehké sandály umožňující rychlé přesunování i v boji.",
     "💫",   0,12,12,  0,15,  0, 0, 9, 0, 0,  20, 2200, 2, "Sada Arkanního Mistra"),
    ("Prsten Arkanního Mistra",   "ring",   "Prsten zesilující každé kouzlo. Nositel cítí moc v každém prstu.",
     "💜",   0, 0, 0,  0,25,  0, 0,24, 0, 0,  20, 2000, 2, "Sada Arkanního Mistra"),
    ("Přívěsek Arkanního Mistra", "amulet", "Přívěsek plný arkánné energie. Každé kouzlo je s ním destruktivnější.",
     "🌐",   0, 0, 0,  0,100, 0, 0,26, 0, 5,  20, 2300, 2, "Sada Arkanního Mistra"),

    # ── RANGER SET — "Sada Zákeřného Lovce" (set_id=3) ────────────────────────
    ("Luk Zákeřného Lovce",        "weapon", "Luk ze dřeva černého stromu. Šípy z něj nikdy neminout.",
     "🏹",  60, 0, 8,  0, 0,  0,16, 0, 0, 7,  20, 3500, 3, "Sada Zákeřného Lovce"),
    ("Kukla Zákeřného Lovce",      "helmet", "Temná kukla skrývající identitu lovce. Zvyšuje přesnost.",
     "🎭",   0,24, 5,  0, 0,  0,14, 0, 0, 7,  20, 2800, 3, "Sada Zákeřného Lovce"),
    ("Plášť Zákeřného Lovce",      "armor",  "Plášť splývající se stíny. Lovec se v něm stává přízrakem.",
     "🌑",   0,35,10, 30, 0,  0,12, 0, 0, 0,  20, 4000, 3, "Sada Zákeřného Lovce"),
    ("Rukavice Zákeřného Lovce",   "gloves", "Rukavice ze zákeřné kůže. Každý šíp je vystřelen s přesností.",
     "🍃",   0, 0, 4,  0, 0,  0,18, 0, 0, 5,  20, 2500, 3, "Sada Zákeřného Lovce"),
    ("Boty Zákeřného Lovce",       "boots",  "Boty lovce pohybujícího se jako duch. Rychlost nad vše.",
     "💨",   0,14,20,  0, 0,  0,18, 0, 0, 4,  20, 2200, 3, "Sada Zákeřného Lovce"),
    ("Prsten Zákeřného Lovce",     "ring",   "Prsten nabitý loveckou magií. Šance na kritický zásah roste.",
     "🍀",   0, 0, 3,  0, 0,  0,12, 0, 0,15,  20, 2000, 3, "Sada Zákeřného Lovce"),
    ("Amulet Zákeřného Lovce",     "amulet", "Amulet zákeřného lovce. Každý kus sady zesiluje smrtonosnost.",
     "🌿",   0, 0, 0, 25, 0,  0,18, 0, 0,15,  20, 2300, 3, "Sada Zákeřného Lovce"),
]


SEED_CLASS_ITEMS = [
    # Formát: (name, type, rarity, desc, icon, atk, def_, spd, hp, xp, s_str, s_dex, s_int, s_end, s_luck, min_level, sell, hint_class)
    # POZNÁMKA: spd (pole 8) je v Item modelu ignorováno — vždy 0

    # ── WARRIOR ──────────────────────────────────────────────────────────────
    # Common
    ("Těžký sekáč",              "weapon",  "common",   "Masivní sekáč pro silné ruce.",              "🪓",  6,  0, 0,  0, 0,  2,0,0,0,0,  1,  10, "warrior"),
    ("Zbroj bojovníka",          "armor",   "common",   "Jednoduchá ale odolná zbroj.",               "🛡️",  0,  5, 0,  0, 0,  0,0,0,1,0,  1,  12, "warrior"),
    # Uncommon
    ("Válečnická sekera",        "weapon",  "uncommon", "Sekera tesaná pro boj z blízka.",            "🪓", 16,  0, 0,  0, 0,  5,0,0,1,0,  3,  38, "warrior"),
    ("Ocelová helma",            "helmet",  "uncommon", "Ochrana hlavy zkušeného bojovníka.",         "⛑️",  0,  9, 0,  8, 0,  0,0,0,2,0,  3,  35, "warrior"),
    ("Válečné rukavice",         "gloves",  "uncommon", "Těžké rukavice pro boj z blízka.",           "🥊",  0,  5, 0,  0, 0,  3,0,0,1,0,  3,  32, "warrior"),
    # Rare
    ("Ocelový bastard",          "weapon",  "rare",     "Dvouruční meč z nejtvrdší oceli.",           "⚔️", 28,  0, 0,  8, 0,  7,0,0,0,0,  6, 130, "warrior"),
    ("Plátová zbroj válečníka",  "armor",   "rare",     "Těžká plátová ochrana pro frontový boj.",    "🛡️",  0, 24, 0, 12, 0,  0,0,0,4,0,  6, 125, "warrior"),
    ("Bojové boty válečníka",    "boots",   "rare",     "Pevné boty pro frontový boj.",               "👢",  0,  7, 0,  8, 0,  3,0,0,1,0,  6, 115, "warrior"),
    # Epic
    ("Hněv titana",              "weapon",  "epic",     "Zbraň hodná pravého válečníka.",             "🪓", 50,  0, 0, 15, 0, 12,0,0,5,0, 12, 450, "warrior"),
    ("Prsten silákův",           "ring",    "epic",     "Magický prsten zesilující fyzickou sílu.",   "💍",  0,  6, 0, 12, 0,  8,0,0,5,0, 10, 420, "warrior"),

    # ── RANGER ───────────────────────────────────────────────────────────────
    # Common
    ("Průzkumnický luk",         "weapon",  "common",   "Lehký luk pro rychlé střelce.",              "🏹",  4,  0, 0,  0, 0,  0,2,0,0,1,  1,   9, "ranger"),
    ("Lehké boty lovce",         "boots",   "common",   "Boty pro pohyb v terénu.",                   "👟",  0,  3, 0,  0, 0,  0,2,0,0,0,  1,  10, "ranger"),
    # Uncommon
    ("Ostrostřelecký luk",       "weapon",  "uncommon", "Přesný luk z jasanového dřeva.",             "🏹", 13,  0, 0,  0, 0,  0,6,0,0,2,  3,  34, "ranger"),
    ("Kůže lovce",               "armor",   "uncommon", "Ohebná zbroj z dračí kůže.",                 "🥋",  0,  8, 0,  0, 0,  0,3,0,0,1,  3,  33, "ranger"),
    ("Rukavice střelce",         "gloves",  "uncommon", "Lehké rukavice pro přesnou střelbu.",        "🧤",  0,  4, 0,  0, 0,  0,4,0,0,1,  3,  30, "ranger"),
    # Rare
    ("Stříbrný luk",             "weapon",  "rare",     "Luk zdobený stříbrnými runy přesnosti.",     "🏹", 23,  0, 0,  6, 0,  0,9,0,0,4,  6, 118, "ranger"),
    ("Průzkumnická kukla",       "helmet",  "rare",     "Lehká kukla pro přesné střelce.",            "🪖",  0, 11, 0,  6, 0,  0,5,0,0,2,  6, 112, "ranger"),
    ("Přívěsek lovce",           "amulet",  "rare",     "Talisman ostrých smyslů.",                   "🌿",  0,  4, 0,  8, 0,  0,6,0,0,5,  7, 120, "ranger"),
    # Epic
    ("Stín a vítr",              "weapon",  "epic",     "Luk tak rychlý, že zní jako vítr.",          "🏹", 44,  0, 0, 10, 0,  0,14,0,0,6, 12, 430, "ranger"),
    ("Zbroj stínového lovce",    "armor",   "epic",     "Zbroj splývající se stínem.",                "🥷",  0, 21, 0, 15, 0,  0,10,0,0,4, 10, 410, "ranger"),

    # ── MAGE ─────────────────────────────────────────────────────────────────
    # Common
    ("Větvičková hůlka",         "weapon",  "common",   "Malá hůlka pro začínající mága.",            "🪄",  3,  0, 0,  0, 0,  0,0,3,0,0,  1,   8, "mage"),
    ("Mystické roucho",          "armor",   "common",   "Jednoduché roucho s magickými vzory.",       "👘",  0,  3, 0,  0, 0,  0,0,2,0,0,  1,   9, "mage"),
    # Uncommon
    ("Arkanická tyč",            "weapon",  "uncommon", "Tyč kanalizující arkanickou energii.",       "🔮", 10,  0, 0,  0, 0,  0,0,8,0,0,  3,  33, "mage"),
    ("Čepice zaříkávače",        "helmet",  "uncommon", "Čepice zvyšující soustředění mága.",         "🎓",  0,  6, 0,  0, 0,  0,0,5,0,0,  3,  31, "mage"),
    ("Prsten moudra",            "ring",    "uncommon", "Prsten zesilující arkanickou sílu.",         "💍",  0,  0, 0,  5, 0,  0,0,6,0,0,  3,  30, "mage"),
    # Rare
    ("Runová hůlka",             "weapon",  "rare",     "Hůlka vyřezaná z runového kamene.",          "🔮", 19,  0, 0, 12, 0,  0,0,14,0,0,  6, 122, "mage"),
    ("Arkanické roucho",         "armor",   "rare",     "Roucho tkané z magických vláken.",           "👘",  0, 13, 0, 15, 0,  0,0, 8,0,0,  6, 118, "mage"),
    ("Boty učence",              "boots",   "rare",     "Komfortní boty pro dlouhé studium kouzel.",  "👡",  0,  5, 0, 10, 0,  0,0, 6,0,0,  6, 110, "mage"),
    # Epic
    ("Arcimágova hůl",           "weapon",  "epic",     "Hůl napájená arkanickým krystalem.",         "🔮", 38,  0, 0, 20, 0,  0,0,16,0,0, 12, 440, "mage"),
    ("Amulet arkanisty",         "amulet",  "epic",     "Amulet posilující magické schopnosti.",      "📿",  0,  5, 0, 18, 0,  0,0,12,0,0, 10, 415, "mage"),
]


async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select

        # Načti existující jména (upsert by name — bezpečné opakované spuštění)
        existing_res = await db.execute(select(Item.name))
        existing_names = {row[0] for row in existing_res.all()}

        count = 0

        # ── Normální itemy ────────────────────────────────────────────────────
        for row in SEED_ITEMS:
            (name, itype, rarity, desc, icon,
             atk, def_, spd, hp, xp,
             s_str, s_dex, s_int, s_end, s_luck,
             min_lv, sell) = row

            if name in existing_names:
                from sqlalchemy import update as sql_update
                await db.execute(
                    sql_update(Item).where(Item.name == name).values(
                        bonus_atk=atk,  bonus_def=def_,
                        bonus_hp=hp,    bonus_xp=xp,
                        bonus_str=s_str, bonus_dex=s_dex, bonus_int=s_int,
                        bonus_end=s_end, bonus_luck=s_luck,
                    )
                )
                count += 1
                continue

            item = Item(
                name=name, item_type=itype, rarity=rarity,
                description=desc, icon=icon,
                bonus_atk=atk,  bonus_def=def_,
                bonus_hp=hp,    bonus_xp=xp,
                bonus_str=s_str, bonus_dex=s_dex, bonus_int=s_int,
                bonus_end=s_end, bonus_luck=s_luck,
                min_level=min_lv, sell_price=sell,
            )
            db.add(item)
            count += 1

        # ── Setové itemy ──────────────────────────────────────────────────────
        for row in SEED_SET_ITEMS:
            (name, itype, desc, icon,
             atk, def_, spd, hp, mp,
             s_str, s_dex, s_int, s_end, s_luck,
             min_lv, sell, set_id, set_name) = row

            if name in existing_names:
                from sqlalchemy import update as sql_update
                await db.execute(
                    sql_update(Item).where(Item.name == name).values(
                        bonus_atk=atk,  bonus_def=def_,
                        bonus_hp=hp,
                        bonus_str=s_str, bonus_dex=s_dex, bonus_int=s_int,
                        bonus_end=s_end, bonus_luck=s_luck,
                    )
                )
                count += 1
                continue

            item = Item(
                name=name, item_type=itype, rarity="set",
                description=desc, icon=icon,
                bonus_atk=atk,  bonus_def=def_,
                bonus_hp=hp,
                bonus_str=s_str, bonus_dex=s_dex, bonus_int=s_int,
                bonus_end=s_end, bonus_luck=s_luck,
                min_level=min_lv, sell_price=sell,
                set_id=set_id, set_name=set_name,
            )
            db.add(item)
            count += 1

        # ── Class-focused itemy ───────────────────────────────────────────────
        for row in SEED_CLASS_ITEMS:
            (name, itype, rarity, desc, icon,
             atk, def_, spd, hp, xp,
             s_str, s_dex, s_int, s_end, s_luck,
             min_lv, sell, hint_cls) = row

            if name in existing_names:
                from sqlalchemy import update as sql_update
                await db.execute(
                    sql_update(Item).where(Item.name == name).values(
                        bonus_atk=atk,  bonus_def=def_,
                        bonus_hp=hp,    bonus_xp=xp,
                        bonus_str=s_str, bonus_dex=s_dex, bonus_int=s_int,
                        bonus_end=s_end, bonus_luck=s_luck,
                        hint_class=hint_cls,
                    )
                )
                count += 1
                continue

            item = Item(
                name=name, item_type=itype, rarity=rarity,
                description=desc, icon=icon,
                bonus_atk=atk,  bonus_def=def_,
                bonus_hp=hp,    bonus_xp=xp,
                bonus_str=s_str, bonus_dex=s_dex, bonus_int=s_int,
                bonus_end=s_end, bonus_luck=s_luck,
                min_level=min_lv, sell_price=sell,
                hint_class=hint_cls,
            )
            db.add(item)
            count += 1

        if count > 0:
            await db.commit()
            log.info("Seed completed", extra={"data": {"items_upserted": count}})
        else:
            log.info("Seed skipped", extra={"data": {"reason": "nothing to upsert"}})

if __name__ == "__main__":
    asyncio.run(seed())
