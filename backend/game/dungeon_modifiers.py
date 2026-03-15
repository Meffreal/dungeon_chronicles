"""
game/dungeon_modifiers.py — Definice týdenních dungeon modifikátorů.

Každý týden se automaticky rotuje jeden modifikátor (deterministicky dle ISO týdne).
Modifikátor platí pro VŠECHNY dungeony a mění statistiky nepřátel, hráče i odměny.
Hráči musí přizpůsobit strategii aktuálnímu modifikátoru.

Možné efekty (klíče v dict):
  enemy_hp_mult, enemy_atk_mult, enemy_def_mult, enemy_spd_mult  — násobič stat nepřítele
  boss_hp_mult, boss_def_mult                                     — extra násobič pro bosse
  player_hp_mult, player_atk_mult, player_def_mult, player_mp_mult — násobič stat hráče
  reward_xp_mult, reward_gold_mult                                — násobič odměn
  start_status_player                                             — hráč začíná s tímto statusem
  start_status_enemy                                              — nepřítel začíná s tímto statusem
"""

# ── Definice modifikátorů ──────────────────────────────────────────────────────
DUNGEON_MODIFIERS: dict[str, dict] = {
    "iron_fortress": {
        "name":        "Železná Pevnost",
        "emoji":       "🏰",
        "description": "Nepřátelé jsou těžce obrnění. +50% DEF, +20% HP. Bonus gold za výhru.",
        "type":        "enemy_buff",
        "color":       "#e67e22",
        "enemy_hp_mult":   1.20,
        "enemy_def_mult":  1.50,
        "reward_gold_mult": 1.25,
    },
    "berserker_rage": {
        "name":        "Zuřivost Berserkrů",
        "emoji":       "😡",
        "description": "Nepřátelé útočí šíleně agresivně. +40% ATK, ale -20% DEF. Bonus XP.",
        "type":        "enemy_buff",
        "color":       "#e74c3c",
        "enemy_atk_mult":  1.40,
        "enemy_def_mult":  0.80,
        "reward_xp_mult":  1.20,
    },
    "swift_predators": {
        "name":        "Rychlí Predátoři",
        "emoji":       "⚡",
        "description": "Nepřátelé jsou bleskově rychlí. +35% SPD, +15% ATK.",
        "type":        "enemy_buff",
        "color":       "#f39c12",
        "enemy_spd_mult":  1.35,
        "enemy_atk_mult":  1.15,
    },
    "cursed_grounds": {
        "name":        "Prokletá Půda",
        "emoji":       "☠️",
        "description": "Jedovatá atmosféra. Hráč začíná každý souboj s jedem. +30% XP. Tajné průchody na 70%.",
        "type":        "player_debuff",
        "color":       "#8e44ad",
        "start_status_player": "poison",
        "reward_xp_mult": 1.30,
        "secret_path_chance": 0.70,
    },
    "ancient_blessing": {
        "name":        "Starodávné Požehnání",
        "emoji":       "✨",
        "description": "Dungeony jsou prosyceny prastarou silou. Hráč +20% HP, +10% ATK.",
        "type":        "player_buff",
        "color":       "#27ae60",
        "player_hp_mult":  1.20,
        "player_atk_mult": 1.10,
    },
    "double_loot": {
        "name":        "Dvojitá Kořist",
        "emoji":       "💰",
        "description": "Týden hojnosti! Všechny XP i gold odměny za dungeony jsou zdvojnásobeny.",
        "type":        "special",
        "color":       "#f1c40f",
        "reward_xp_mult":   2.0,
        "reward_gold_mult": 2.0,
    },
    "weakened_enemies": {
        "name":        "Oslabení Nepřátelé",
        "emoji":       "💤",
        "description": "Nepřátelé jsou unavení a zranitelní. -25% ATK i DEF. Ideální pro farming.",
        "type":        "player_buff",
        "color":       "#3498db",
        "enemy_atk_mult": 0.75,
        "enemy_def_mult": 0.75,
    },
    "bloodmoon": {
        "name":        "Krvavý Měsíc",
        "emoji":       "🌕",
        "description": "Pod krvavým měsícem nepřátelé zuří (+30% ATK). Hráč krvácí od začátku. +40% XP.",
        "type":        "mixed",
        "color":       "#c0392b",
        "enemy_atk_mult":      1.30,
        "start_status_player": "bleed",
        "reward_xp_mult":      1.40,
        "reward_gold_mult":    1.30,
    },
    "mana_void": {
        "name":        "Prázdnota Many",
        "emoji":       "🌀",
        "description": "Magie se rozpadá. Hráč má jen 50% MP — méně speciálních schopností. +20% XP.",
        "type":        "player_debuff",
        "color":       "#7f8c8d",
        "player_mp_mult":  0.50,
        "reward_xp_mult":  1.20,
    },
    "fortified_bosses": {
        "name":        "Zpevnění Bossové",
        "emoji":       "💪",
        "description": "Finální bossové jsou zesíleni — +40% HP, +30% DEF. Vyplatí se ale double. +50% odměny.",
        "type":        "enemy_buff",
        "color":       "#d35400",
        "boss_hp_mult":    1.40,
        "boss_def_mult":   1.30,
        "reward_xp_mult":  1.50,
        "reward_gold_mult": 1.50,
    },
    "blessed_warriors": {
        "name":        "Požehnaní Bojovníci",
        "emoji":       "🛡️",
        "description": "Hráč je chráněn bariérou. +30% DEF a každý souboj začíná se štítem.",
        "type":        "player_buff",
        "color":       "#1abc9c",
        "player_def_mult":     1.30,
        "start_status_player": "shield",
    },
    "chaos_week": {
        "name":        "Týden Chaosu",
        "emoji":       "🌪️",
        "description": "Vše je zesíleno! Nepřátelé i hráč +20% všech statistik. Chaos vládne. +30% odměny.",
        "type":        "special",
        "color":       "#9b59b6",
        "enemy_atk_mult":   1.20,
        "enemy_def_mult":   1.20,
        "enemy_hp_mult":    1.20,
        "enemy_spd_mult":   1.20,
        "player_atk_mult":  1.20,
        "player_def_mult":  1.20,
        "player_hp_mult":   1.20,
        "reward_xp_mult":   1.30,
        "reward_gold_mult": 1.30,
    },
}

# Seřazený seznam klíčů pro rotaci (deterministic per-week)
MODIFIER_ROTATION: list[str] = list(DUNGEON_MODIFIERS.keys())


# ── Helper funkce ──────────────────────────────────────────────────────────────

def apply_modifier_to_enemy(
    modifier: dict | None,
    hp: int, atk: int, def_: int, spd: int,
    is_boss: bool = False,
) -> tuple[int, int, int, int]:
    """
    Aplikuje modifikátor na nepřátelské statistiky.
    Pro bosse se navíc uplatní boss_hp_mult / boss_def_mult (pokud jsou definovány).
    Vrátí (hp, atk, def_, spd).
    """
    if not modifier:
        return hp, atk, def_, spd

    hp_mult  = modifier.get("boss_hp_mult",  modifier.get("enemy_hp_mult",  1.0)) if is_boss else modifier.get("enemy_hp_mult",  1.0)
    atk_mult = modifier.get("enemy_atk_mult", 1.0)
    def_mult = modifier.get("boss_def_mult", modifier.get("enemy_def_mult", 1.0)) if is_boss else modifier.get("enemy_def_mult", 1.0)
    spd_mult = modifier.get("enemy_spd_mult", 1.0)

    return (
        int(hp   * hp_mult),
        int(atk  * atk_mult),
        int(def_ * def_mult),
        int(spd  * spd_mult),
    )


def apply_modifier_to_player(
    modifier: dict | None,
    hp: int, atk: int, def_: int, spd: int, mp: int,
) -> tuple[int, int, int, int, int]:
    """
    Aplikuje modifikátor na hráčské statistiky.
    Vrátí (hp, atk, def_, spd, mp).
    """
    if not modifier:
        return hp, atk, def_, spd, mp

    hp_mult  = modifier.get("player_hp_mult",  1.0)
    atk_mult = modifier.get("player_atk_mult", 1.0)
    def_mult = modifier.get("player_def_mult", 1.0)
    mp_mult  = modifier.get("player_mp_mult",  1.0)

    return (
        int(hp   * hp_mult),
        int(atk  * atk_mult),
        int(def_ * def_mult),
        spd,                   # SPD není modifikováno (beze změny)
        int(mp   * mp_mult),
    )


def get_modifier_start_statuses(modifier: dict | None) -> dict[str, str | None]:
    """
    Vrátí start statusy pro hráče a nepřítele.
    Výsledek: {"player": "poison" | None, "enemy": None | str}
    """
    if not modifier:
        return {"player": None, "enemy": None}
    return {
        "player": modifier.get("start_status_player"),
        "enemy":  modifier.get("start_status_enemy"),
    }


def scale_rewards(modifier: dict | None, xp: int, gold: int) -> tuple[int, int]:
    """Aplikuje reward multiplikátory na XP a gold odměny."""
    if not modifier:
        return xp, gold
    xp_mult   = modifier.get("reward_xp_mult",   1.0)
    gold_mult = modifier.get("reward_gold_mult", 1.0)
    return int(xp * xp_mult), int(gold * gold_mult)
