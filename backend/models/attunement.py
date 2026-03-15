"""
models/attunement.py — Attunement systém (vstupenky do dungeonů)
"""

# ── Definice attunement chainů — načteny z config/attunements.json ────────────
# Přidat nový chain = přidat záznam do backend/config/attunements.json
from game.config_loader import load_attunement_chains as _lac
ATTUNEMENT_CHAINS = _lac()

# Rychlý lookup: quest_id → {"chain_id", "step", "chain"}
QUEST_CHAIN_MAP: dict[int, dict] = {}
for _chain in ATTUNEMENT_CHAINS:
    for _step, _qid in enumerate(_chain["quest_ids"], 1):
        QUEST_CHAIN_MAP[_qid] = {
            "chain_id": _chain["id"],
            "step": _step,
            "chain": _chain,
        }

# Dungeon quest ID → požadovaný attunement chain ID
DUNGEON_QUEST_ATTUNEMENT: dict[int, int] = {
    c["dungeon_quest_id"]: c["id"] for c in ATTUNEMENT_CHAINS
}
