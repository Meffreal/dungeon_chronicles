"""
game/seed.py — Naplní databázi počátečními itemy
Spusť: python game/seed.py
"""
import asyncio
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db, AsyncSessionLocal
# Všechny modely musí být importovány aby SQLAlchemy vyřešilo relationships
from models.user         import User           # noqa: F401
from models.item         import Item, Rarity, ItemType, InventoryItem  # noqa: F401
from models.guild        import Guild          # noqa: F401
from models.character    import Character      # noqa: F401
from models.quest        import Quest          # noqa: F401
from models.market       import MarketListing  # noqa: F401
from models.notification import Notification   # noqa: F401
from models.arena        import ArenaMatch     # noqa: F401

SEED_ITEMS = [
    # ── WEAPONS ──────────────────────────────────────────────────────────────
    # Common
    ("Rezavý meč",       "weapon", "common",    "Starý meč s rezavou čepelí.",       "⚔️",  5, 0, 0, 0, 0, 0,0,0,0,0, 1,  8),
    ("Dřevěná hůl",      "weapon", "common",    "Obyčejná dřevěná hůl.",             "🪄",  3, 0, 0, 0, 0, 0,0,3,0,0, 1,  6),
    ("Lovecký luk",      "weapon", "common",    "Primitivní luk z kmene stromu.",    "🏹",  4, 0, 0, 0, 0, 0,3,0,0,0, 1,  7),
    # Uncommon
    ("Železný meč",      "weapon", "uncommon",  "Spolehlivý meč zkušeného bojovníka.","⚔️", 12, 0, 1, 0, 0, 2,0,0,0,0, 3, 35),
    ("Učňovská hůl",     "weapon", "uncommon",  "Hůl začínajícího mága.",            "🪄",  7, 0, 2, 0, 0, 0,0,5,0,0, 3, 30),
    ("Kompozitní luk",   "weapon", "uncommon",  "Silnější luk z vrstveného dřeva.",  "🏹",  9, 0, 1, 0, 0, 0,4,0,0,2, 3, 32),
    # Rare
    ("Stříbrná čepel",   "weapon", "rare",      "Zbraň kovaná ze stříbra.",          "🗡️", 22, 0, 2, 5, 0, 3,0,0,0,2, 6, 120),
    ("Ohnivá hůl",       "weapon", "rare",      "Hůl naplněná ohnivou magií.",       "🔥", 14, 0, 3,15, 0, 0,0,9,0,0, 6, 110),
    ("Elfský luk",       "weapon", "rare",      "Elegantní luk z elfího dřeva.",     "🏹", 18, 0, 2, 8, 0, 0,7,0,0,4, 6, 115),
    # Epic
    ("Démonická čepel",  "weapon", "epic",      "Meč zkovaný v pekelném ohni.",      "😈", 35, 0, 4,10, 0, 5,0,0,5,0,12, 400),
    ("Chaos hůl",        "weapon", "epic",      "Hůl překypující chaotickou mocí.",  "💜", 22, 0, 5,30, 0, 0,0,15,0,0,12, 380),
    ("Stínový luk",      "weapon", "epic",      "Luk z temné energie utkaný.",       "🌑", 28, 0, 5,20, 0, 0,12,0,0,8,12, 390),
    # Legendary
    ("Excalibur",        "weapon", "legendary", "Legendární meč krále Artuše.",      "✨", 55,10, 8,15,20,10,5, 0,8,5,20,2000),
    ("Žezlo věčnosti",   "weapon", "legendary", "Artefakt staré civilizace.",        "⚡", 35, 5,10,60,30, 0,0,20,0,0,20,1800),
    ("Luk osudu",        "weapon", "legendary", "Střela tohoto luku nikdy nechybí.", "🌟", 45, 8, 8,25,25, 0,18,5,0,15,20,1900),

    # ── ARMOR ────────────────────────────────────────────────────────────────
    # Common
    ("Kožená zbroj",     "armor",  "common",    "Základní ochrana z kůže.",          "🥋",  0, 6, 0, 0, 0, 0,0,0,2,0, 1, 10),
    ("Vlněný plášť",     "armor",  "common",    "Teplý vlněný plášť.",               "🧥",  0, 4, 0, 5, 0, 0,0,1,1,0, 1,  9),
    # Uncommon
    ("Pletivo",          "armor",  "uncommon",  "Ochranné kroužkové brnění.",        "🛡️",  0,14, 0, 0, 0, 0,0,0,4,0, 3, 50),
    ("Enchantovaný plášť","armor", "uncommon",  "Magicky posílený plášť.",           "✨",  0, 8, 0,20, 0, 0,0,3,3,0, 3, 45),
    # Rare
    ("Plátové brnění",   "armor",  "rare",      "Těžké plátové brnění rytíře.",      "⚔️",  0,24, 0, 0, 30,0,0,0,7,0, 6, 180),
    ("Runový plášť",     "armor",  "rare",      "Plášť pokrytý runami moci.",        "🔮",  0,12, 0,35, 20,0,0,5,4,0, 6, 165),
    # Epic & Legendary
    ("Brnění draka",     "armor",  "epic",      "Zkované z šupin draka.",            "🐲",  0,38,12, 0, 60,8,0,0,12,0,12, 650),
    ("Nebeská zbroj",    "armor",  "legendary", "Dar samotných bohů.",               "🌤️",  5,55,15,20, 80,10,5,5,15,10,20,3000),

    # ── HELMETS ──────────────────────────────────────────────────────────────
    ("Kožená čapka",     "helmet", "common",    "Jednoduchá kožená ochrana hlavy.",  "🪖",  0, 3, 0, 0, 0, 0,0,0,1,0, 1,  6),
    ("Železná helma",    "helmet", "uncommon",  "Solidní železná helma.",            "⛑️",  0, 9, 0, 0, 15,2,0,0,2,0, 3, 42),
    ("Arkanická koruna", "helmet", "rare",      "Koruna zasvěcená magii.",           "👑",  2, 5, 0,25, 10,0,0,6,2,2, 6, 160),
    ("Korunka draka",    "helmet", "epic",      "Koruna z drakovy lebky.",           "🐉",  3,16, 5,15, 25,4,2,2,5,3,12, 550),

    # ── BOOTS ────────────────────────────────────────────────────────────────
    ("Kožené boty",      "boots",  "common",    "Pohodlné kožené boty.",             "👢",  0, 2, 2, 0, 0, 0,1,0,0,0, 1,  5),
    ("Boty větru",       "boots",  "uncommon",  "Lehké boty zvyšující rychlost.",    "💨",  0, 4, 6, 0, 0, 0,3,0,0,2, 3, 40),
    ("Stínové boty",     "boots",  "rare",      "Pohyb v nich nevydává zvuk.",       "🌑",  0, 6,12, 0, 0, 0,5,0,0,4, 6, 140),

    # ── RINGS & AMULETS ──────────────────────────────────────────────────────
    ("Prsten síly",      "ring",   "uncommon",  "Zesiluje fyzickou sílu.",           "💪",  3, 0, 0, 0, 0, 4,0,0,0,0, 3, 38),
    ("Prsten magie",     "ring",   "uncommon",  "Zesiluje magické schopnosti.",      "🔮",  2, 0, 0,10, 0, 0,0,3,0,0, 3, 36),
    ("Prsten štěstí",    "ring",   "rare",      "Přináší štěstí nositeli.",          "🍀",  0, 0, 3, 5, 0, 0,0,0,0,8, 6, 130),
    ("Amulet ochrany",   "amulet", "uncommon",  "Chrání nositele před zlem.",        "🧿",  0, 5, 0, 5,10, 0,0,2,2,2, 3, 44),
    ("Amulet draka",     "amulet", "legendary", "Dává moc prastarého draka.",        "🐲", 10,15, 8,20,50,5,5,5,8,5,20,2500),

    # ── GLOVES ───────────────────────────────────────────────────────────────
    ("Kožené rukavice",  "gloves", "common",    "Chrání ruce v boji.",               "🧤",  1, 2, 0, 0, 0, 1,0,0,0,0, 1,  5),
    ("Bojové rukavice",  "gloves", "uncommon",  "Rukavice ostřílených bojovníků.",   "👊",  4, 4, 0, 0, 5, 3,0,0,1,0, 3, 38),
    ("Runové rukavice",  "gloves", "rare",      "Runy na nich zesilují kouzla.",     "✨",  2, 3, 0,15, 5, 0,0,4,1,1, 6, 145),
    ("Rukavice vraha",   "gloves", "epic",      "Rukavice skrz něž proudí tma.",     "🩸",  8, 5, 5, 0, 0, 4,6,0,0,4,12, 480),
    ("Rukavice titána",  "gloves", "legendary", "Kdysi patřily titánovi válek.",     "⚡", 14, 8, 8,30,15, 8,5,0,5,5,20,2200),

    # ── WEAPONS (rozšíření) ───────────────────────────────────────────────────
    ("Krvavá šavle",     "weapon", "rare",      "Čepel napitá krví nepřátel.",       "🩸", 20, 0, 4, 0, 0, 4,2,0,0,3, 7, 125),
    ("Duševní zlomitel", "weapon", "epic",      "Hůl roztrhávající mysl protivníka.","💀", 18, 0, 3,25, 0, 0,0,18,0,0,13, 420),
    ("Hrom a blesk",     "weapon", "legendary", "Zbraň kovaná z blesku samotného.",  "⚡", 50, 5,12,20,25, 8,8,5,5,8,20,2100),

    # ── ARMOR (rozšíření) ─────────────────────────────────────────────────────
    ("Elfské roucho",    "armor",  "rare",      "Lehké roucho tkané elfy.",          "🌿",  0,10, 5,25, 0, 0,4,4,2,3, 7, 170),
    ("Titanské brnění",  "armor",  "epic",      "Brnění z kovu titan, neprůstřelné.","🏔️",  0,45,10, 0,70,10,0,0,14,0,13, 700),

    # ── HELMETS (rozšíření) ───────────────────────────────────────────────────
    ("Druidská čelenka", "helmet", "rare",      "Čelenka s magií přírody.",          "🌿",  0, 6, 4,20,10, 0,2,5,2,4, 7, 155),
    ("Stínová maska",    "helmet", "epic",      "Skrývá tvář i duši nositele.",      "🎭",  4,14, 6, 0,15, 3,5,2,4,5,13, 560),
    ("Koruna věčnosti",  "helmet", "legendary", "Korunuje toho, kdo přežil vše.",    "👑", 10,25,10,30,40, 8,5,8,8,8,20,3200),

    # ── BOOTS (rozšíření) ─────────────────────────────────────────────────────
    ("Démonické boty",   "boots",  "epic",      "Boty z kůže démona. Rychlé.",       "😈",  5, 8,18, 0, 0, 0,8,0,0,6,13, 510),
    ("Boty boha větru",  "boots",  "legendary", "Nositel se pohybuje jako vítr.",    "💨",  8, 8,30,20,10, 0,12,0,0,10,20,2300),

    # ── RINGS (rozšíření) ─────────────────────────────────────────────────────
    ("Prsten krve",      "ring",   "epic",      "Saje životní sílu nepřátel.",       "🩸", 10, 0, 3,20, 0, 6,0,0,0,4,13, 430),
    ("Prsten věčnosti",  "ring",   "legendary", "Kdo ho nosí, je blíže nesmrtelnosti.","⚡", 8, 8, 8,40,30, 5,5,5,5,10,20,2400),

    # ── AMULETS (rozšíření) ───────────────────────────────────────────────────
    ("Přívěsek lesa",    "amulet", "rare",      "Lesní magie chrání nositele.",      "🌿",  0, 8, 6,15,25, 0,3,4,4,5, 7, 160),
    ("Amulet bouře",     "amulet", "epic",      "Přívěsek nabíjený bleskem.",        "⛈️", 12, 6, 8,15,20, 4,4,6,3,4,13, 520),

    # ── POTIONS / SCROLLS / ELIXIRS ──────────────────────────────────────────
    # Použití: atk/def/spd/hp pole se ignorují, bonus_mp = XP získané při použití,
    # bonus_str/dex/int/end/luck = trvalý stat bonus při použití
    ("Lektvar síly",          "potion","common",   "Vypij a získej +1 Sílu natrvalo.",         "🧪",  0,0,0,0,  0, 1,0,0,0,0, 1, 20),
    ("Lektvar obratnosti",    "potion","common",   "Vypij a získej +1 Obratnost natrvalo.",    "🧪",  0,0,0,0,  0, 0,1,0,0,0, 1, 20),
    ("Lektvar magie",         "potion","common",   "Vypij a získej +1 Inteligenci natrvalo.",  "🔮",  0,0,0,0,  0, 0,0,1,0,0, 1, 20),
    ("Lektvar výdrže",        "potion","common",   "Vypij a získej +1 Výdrž natrvalo.",        "🧪",  0,0,0,0,  0, 0,0,0,1,0, 1, 20),
    ("Lektvar štěstí",        "potion","uncommon", "Vypij a získej +1 Štěstí natrvalo.",       "🍀",  0,0,0,0,  0, 0,0,0,0,1, 1, 40),
    ("Svitek zkušeností",     "potion","uncommon", "Okamžitě ti přidá 200 XP.",                "📜",  0,0,0,0,200, 0,0,0,0,0, 1, 50),
    ("Velký svitek zkušeností","potion","rare",    "Okamžitě ti přidá 500 XP.",                "📜",  0,0,0,0,500, 0,0,0,0,0, 5,130),
    ("Elixír hrdinství",      "potion","rare",     "Trvalý +2 Sílu a +1 Výdrž.",               "⚗️", 0,0,0,0,  0, 2,0,0,1,0, 5,120),
    ("Elixír moudrosti",      "potion","rare",     "Trvalý +2 Inteligenci a +1 Štěstí.",       "⚗️", 0,0,0,0,  0, 0,0,2,0,1, 5,120),
    ("Elixír titána",         "potion","epic",     "Trvalý +2 ke všem primárním statům.",      "🧬",  0,0,0,0,  0, 2,2,2,2,2,10,450),
    ("Božský nektar",         "potion","legendary","Trvalý +5 ke všem primárním statům.",      "✨",  0,0,0,0,  0, 5,5,5,5,5,15,2000),
]

async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select

        # Načti existující jména (upsert by name — bezpečné opakované spuštění)
        existing_res = await db.execute(select(Item.name))
        existing_names = {row[0] for row in existing_res.all()}

        count = 0
        for row in SEED_ITEMS:
            (name, itype, rarity, desc, icon,
             atk, def_, spd, hp, mp,
             s_str, s_dex, s_int, s_end, s_luck,
             min_lv, sell) = row

            if name in existing_names:
                continue  # přeskoč existující

            item = Item(
                name=name, item_type=itype, rarity=rarity,
                description=desc, icon=icon,
                bonus_atk=atk,  bonus_def=def_, bonus_spd=spd,
                bonus_hp=hp,    bonus_mp=mp,
                bonus_str=s_str, bonus_dex=s_dex, bonus_int=s_int,
                bonus_end=s_end, bonus_luck=s_luck,
                min_level=min_lv, sell_price=sell,
            )
            db.add(item)
            count += 1

        if count > 0:
            await db.commit()
            print(f"[OK] Seed dokoncen - {count} novych itemu pridano.")
        else:
            print("[OK] Seed preskocen - vsechny itemy jiz existuji.")

if __name__ == "__main__":
    asyncio.run(seed())
