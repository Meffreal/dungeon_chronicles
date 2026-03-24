"""0054 — Profese v3: nový systém (enchanter, alchymista, blacksmith)

Revision ID: 0054
Revises: 0053
Create Date: 2026-03-24

Zahodí starý profession systém (6 profesí), legacy tabulky (runes, item_runes,
prophecy_scrolls, forge_logs, bets, lotteries, lottery_entries, agent_operations,
agent_identities, sabotage_effects, fate_bonds) a vytvoří nový charakter_professions
s UniqueConstraint(character_id). Přidá enchants_json + override_rarity do inventory.
Naseeduje profession items do tabulky items.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision      = '0054'
down_revision = '0053'
branch_labels = None
depends_on    = None

# Profession items k naseedování
PROFESSION_ITEMS = [
    # Reagents
    ("Arcane Dust",          "reagent", "common",    "⚗",  5,   "Magický prach získaný disenchantováním itemů."),
    ("Enchanted Shard",      "reagent", "uncommon",  "💎", 15,  "Střep enchantovaného itemu plný magické energie."),
    ("Void Crystal",         "reagent", "rare",      "🔮", 50,  "Krystal prázdnoty z epic/legendary itemů."),
    ("Alchemic Residue",     "reagent", "common",    "🧪",  5,  "Zbytek po rozložení základních lektvarů."),
    ("Potent Extract",       "reagent", "uncommon",  "💧", 15,  "Koncentrovaný extrakt z pokročilých lektvarů."),
    ("Essence Concentrate",  "reagent", "rare",      "✨", 50,  "Čistá esence z legendárních lektvarů."),
    ("Metal Scraps",         "reagent", "common",    "⚙",  3,   "Kovové zbytky z rozebraného vybavení."),
    ("Refined Ore",          "reagent", "uncommon",  "🪨", 20,  "Přečištěná ruda z rare/epic itemů."),
    ("Soulsteel Fragment",   "reagent", "rare",      "⚔",  75,  "Fragment duší-oceli z legendary itemů."),
    # Potions
    ("HP Potion",            "potion",  "common",    "❤",  20,  "Obnoví 30% HP."),
    ("MP Potion",            "potion",  "common",    "💙", 20,  "Obnoví 30% MP."),
    # Elixirs
    ("Combat Elixir: Attack",  "elixir","uncommon",  "⚔",  50,  "Dočasně +20% útok na 1 souboj."),
    ("Combat Elixir: Defense", "elixir","uncommon",  "🛡",  50,  "Dočasně +20% obrana na 1 souboj."),
    ("XP Elixir",            "elixir",  "rare",      "📚", 100, "+25% XP z příštího questu."),
    ("Gold Elixir",          "elixir",  "rare",      "💰", 100, "+25% zlata z příštího questu."),
    ("Crit Boost Elixir",    "elixir",  "epic",      "⚡", 200, "+15% šance na kritický úder na 1 souboj."),
    ("Shield Elixir",        "elixir",  "epic",      "🌟", 200, "Štít absorbující 20% max HP."),
    ("Legendary Elixir: Berserk",     "elixir","legendary","🔥",500,"+ 50% útok, -20% obrana. Trvá 3 souboje."),
    ("Legendary Elixir: Arcane Surge","elixir","legendary","✨",500,"+40% všech statů. Trvá 2 souboje."),
    # Scrolls
    ("Enchant Scroll",       "scroll",  "rare",      "📜", 150, "Lze použít k enchantování itemu bez Zaklínač profese."),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()

    # 1. Smaž legacy tabulky (order matters — FK constraints)
    legacy_tables = [
        "item_runes",
        "runes",
        "prophecy_scrolls",
        "forge_logs",
        "lottery_entries",
        "lotteries",
        "bets",
        "sabotage_effects",
        "agent_identities",
        "agent_operations",
        "fate_bonds",
    ]
    for tbl in legacy_tables:
        if tbl in tables:
            op.drop_table(tbl)

    # 2. Přebuduj character_professions (nové schéma)
    if "character_professions" in tables:
        op.drop_table("character_professions")

    op.create_table(
        "character_professions",
        sa.Column("id",             sa.Integer, primary_key=True),
        sa.Column("character_id",   sa.Integer, sa.ForeignKey("characters.id"), nullable=False, unique=True),
        sa.Column("profession_key", sa.String(32), nullable=False),
        sa.Column("rank",           sa.Integer, nullable=False, server_default="0"),
        sa.Column("xp",             sa.Integer, nullable=False, server_default="0"),
        sa.Column("chosen_at",      sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )

    # 3. Přidej enchants_json + override_rarity do inventory
    inv_cols = [c['name'] for c in inspector.get_columns('inventory')]
    if 'enchants_json' not in inv_cols:
        op.add_column('inventory', sa.Column('enchants_json', sa.Text, nullable=True))
    if 'override_rarity' not in inv_cols:
        op.add_column('inventory', sa.Column('override_rarity', sa.String(16), nullable=True))

    # 4. Naseeduj profession items
    for (name, item_type, rarity, icon, sell_price, description) in PROFESSION_ITEMS:
        existing = bind.execute(
            text("SELECT id FROM items WHERE name = :n"), {"n": name}
        ).fetchone()
        if not existing:
            bind.execute(
                text(
                    "INSERT INTO items (name, item_type, rarity, icon, sell_price, description, "
                    "bonus_atk, bonus_def, bonus_hp, bonus_str, bonus_dex, bonus_int, bonus_end, "
                    "bonus_luck, bonus_xp, min_level) "
                    "VALUES (:name, :item_type, :rarity, :icon, :sell_price, :description, "
                    "0, 0, 0, 0, 0, 0, 0, 0, 0, 1)"
                ),
                {
                    "name": name, "item_type": item_type, "rarity": rarity,
                    "icon": icon, "sell_price": sell_price, "description": description,
                }
            )


def downgrade() -> None:
    pass
