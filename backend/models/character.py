"""
models/character.py — Postava, stats, inventář, equipment
"""
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import String, Integer, Float, ForeignKey, Text, DateTime, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from sqlalchemy.sql import func
from database import Base
import enum

BUFF_DURATION_DAYS = {
    "common":    1,
    "uncommon":  2,
    "rare":      3,
    "epic":      3,
    "legendary": 3,
}

class CharacterClass(str, enum.Enum):
    WARRIOR = "warrior"
    MAGE    = "mage"
    RANGER  = "ranger"

# ── Base stats per třída (hodnoty na level 1) ─────────────────────────────────
CLASS_BASE_STATS = {
    CharacterClass.WARRIOR: {
        "strength": 15, "dexterity": 8,  "intelligence": 5,
        "endurance": 12, "luck": 5,
        "hp_base": 120,  "mp_base": 30,
        "atk_base": 18,  "def_base": 14, "spd_base": 8,
        "description": "Silný bojovník v přední linii. Vysoký HP a obrana.",
        "emoji": "⚔️",
    },
    CharacterClass.MAGE: {
        "strength": 5,  "dexterity": 8,  "intelligence": 18,
        "endurance": 6,  "luck": 8,
        "hp_base": 70,   "mp_base": 120,
        "atk_base": 10,  "def_base": 5,  "spd_base": 10,
        "description": "Mistr arkánné magie. Devastující kouzla, křehké tělo.",
        "emoji": "🔮",
    },
    CharacterClass.RANGER: {
        "strength": 9,  "dexterity": 16, "intelligence": 8,
        "endurance": 9,  "luck": 13,
        "hp_base": 90,   "mp_base": 60,
        "atk_base": 14,  "def_base": 8,  "spd_base": 18,
        "description": "Rychlý a přesný lovec. Mistr dálkového boje a pastí.",
        "emoji": "🏹",
    },
}

# ── HP multiplikátory per třída (nová formule: END × mult × (level+1)) ───────
CLASS_HP_MULT = {
    CharacterClass.WARRIOR: 5,
    CharacterClass.MAGE:    2,
    CharacterClass.RANGER:  4,
}

# ── XP křivka ─────────────────────────────────────────────────────────────────
def xp_for_level(level: int) -> int:
    """Kolik XP celkem je potřeba pro daný level."""
    return int(100 * (level ** 1.8))

def xp_to_next(level: int) -> int:
    """Kolik XP je potřeba pro přechod z `level` na `level+1`."""
    return xp_for_level(level + 1) - xp_for_level(level)

# ── Character model ───────────────────────────────────────────────────────────
class Character(Base):
    __tablename__ = "characters"

    id:         Mapped[int] = mapped_column(primary_key=True)
    user_id:    Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name:       Mapped[str] = mapped_column(String(32), unique=True, index=True)
    cls:        Mapped[str] = mapped_column(String(16))   # CharacterClass value
    level:      Mapped[int] = mapped_column(Integer, default=1)
    xp:         Mapped[int] = mapped_column(Integer, default=0)
    gold:       Mapped[int] = mapped_column(Integer, default=150)

    # Primary stats
    strength:     Mapped[int] = mapped_column(Integer, default=5)
    dexterity:    Mapped[int] = mapped_column(Integer, default=5)
    intelligence: Mapped[int] = mapped_column(Integer, default=5)
    endurance:    Mapped[int] = mapped_column(Integer, default=5)
    luck:         Mapped[int] = mapped_column(Integer, default=5)

    # Derived / combat stats — hp_max přepočítáváno recalculate_stats()
    # atk, def_, spd, mp_max jsou deprecated (odstraněny v stat redesign)
    hp_max:  Mapped[int]       = mapped_column(Integer, default=100)
    mp_max:  Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    atk:     Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    def_:    Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    spd:     Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)

    # Equip sloty (item ID nebo null)
    eq_weapon:  Mapped[int | None] = mapped_column(Integer, ForeignKey("items.id"), nullable=True)
    eq_helmet:  Mapped[int | None] = mapped_column(Integer, ForeignKey("items.id"), nullable=True)
    eq_armor:   Mapped[int | None] = mapped_column(Integer, ForeignKey("items.id"), nullable=True)
    eq_gloves:  Mapped[int | None] = mapped_column(Integer, ForeignKey("items.id"), nullable=True)
    eq_boots:   Mapped[int | None] = mapped_column(Integer, ForeignKey("items.id"), nullable=True)
    eq_ring:    Mapped[int | None] = mapped_column(Integer, ForeignKey("items.id"), nullable=True)
    eq_amulet:  Mapped[int | None] = mapped_column(Integer, ForeignKey("items.id"), nullable=True)

    # Arena
    arena_rank:          Mapped[int]            = mapped_column(Integer, default=1000)  # ELO-like
    arena_wins:          Mapped[int]            = mapped_column(Integer, default=0)
    arena_losses:        Mapped[int]            = mapped_column(Integer, default=0)
    arena_cooldown_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    arena_gold_today:    Mapped[int]            = mapped_column(Integer, default=0, server_default="0")
    arena_gold_date:     Mapped[str | None]     = mapped_column(String(10), nullable=True)

    # Guild
    guild_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("guilds.id"), nullable=True)

    # Statistiky pro achievementy
    quests_completed: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Nerozdělelné stat body (získávají se za každý level up)
    stat_points: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Dočasné buffy z lektvarů / elixírů (JSON)
    active_buffs_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Aktivní titul hráče (odemčený přes achievementy nebo frakce)
    current_title: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Zvolená frakce (rad_popele / pakt_stinu / kongregace_prazdna)
    faction: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Attunement systém
    attunements_json:         Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list odemčených chain ID
    attunement_progress_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON dict {chain_id: [quest_id, ...]}

    # Vzhled postavy (hybrid: predefined + RGB barvy)
    appearance_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON s hair_style, hair_color, skin_tone, eye_color, etc.

    # Talent tree Tier 1 — odemčené klíče talentů (auto-unlock na level 10/20/30)
    talents_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Crystal (earned premium) currency
    crystals:               Mapped[int]            = mapped_column(Integer, default=0, server_default="0")
    crystal_name_color:     Mapped[str | None]     = mapped_column(String(20), nullable=True)
    crystal_portrait_frame: Mapped[str | None]     = mapped_column(String(32), nullable=True)
    crystal_xp_boost_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Arena season exkluzivní kosmetika (trvale odemčená výkonem v sezóně)
    season_portrait_frame:  Mapped[str | None]     = mapped_column(String(32), nullable=True)

    # Specializace (subclass) — odemkne se na level 10, trvalá volba
    subclass: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Prestige — trvalý level po dosažení max levelu a resetu
    prestige_level:          Mapped[int]        = mapped_column(Integer, default=0, server_default="0")
    prestige_portrait_frame: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Talent Tier 2 — aktivní schopnost, irreverzibilní volba na levelu 25
    talent_t2_key: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Hardcore mode — postava hraje v permadeath módu
    is_hardcore: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="0")

    # Permadeath — stav smrti postavy
    is_dead:       Mapped[bool]              = mapped_column(Boolean, default=False, nullable=False, server_default="0")
    died_at:       Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    killed_by:     Mapped[Optional[str]]      = mapped_column(String(255), nullable=True)
    death_dungeon: Mapped[Optional[str]]      = mapped_column(String(255), nullable=True)

    # Onboarding — byl průvodce pro nové hráče dokončen?
    onboarding_completed: Mapped[bool] = mapped_column(Integer, default=0, server_default="0")

    # A/B testing — skupina hráče (0–9), přiřazena náhodně při vytvoření postavy
    experiment_group: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Login streak — počet po sobě jdoucích dní přihlášení
    login_streak:     Mapped[int]      = mapped_column(Integer, default=0, server_default="0")
    last_login_date:  Mapped[str | None] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD UTC

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Vztahy
    user      = relationship("User", back_populates="character")
    inventory = relationship("InventoryItem", back_populates="character")
    quest             = relationship("Quest", back_populates="character", uselist=False)
    notifications     = relationship("Notification", back_populates="character", cascade="all, delete-orphan")
    guild             = relationship("Guild", back_populates="members", foreign_keys=[guild_id])
    faction_reputation = relationship("FactionReputation", back_populates="character", uselist=False)
    professions        = relationship("CharacterProfession", back_populates="character", cascade="all, delete-orphan")

    # ── Buff systém ───────────────────────────────────────────────────────────

    def get_active_buffs(self) -> list:
        """Vrátí seznam aktivních (neexpirovaných) buffů."""
        if not self.active_buffs_json:
            return []
        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            return [b for b in json.loads(self.active_buffs_json) if b.get("expires_at", "") > now]
        except Exception:
            return []

    def add_buff(self, name: str, expires_at: datetime,
                 bonus_str: int = 0, bonus_dex: int = 0, bonus_int: int = 0,
                 bonus_end: int = 0, bonus_luck: int = 0):
        """Přidá nový buff (nebo obnoví expiraci stávajícího)."""
        buffs = self.get_active_buffs()
        # Pokud buff se stejným jménem již existuje, aktualizuj ho
        updated = False
        for b in buffs:
            if b["name"] == name:
                b["expires_at"] = expires_at.isoformat()
                b["bonus_str"]  = bonus_str
                b["bonus_dex"]  = bonus_dex
                b["bonus_int"]  = bonus_int
                b["bonus_end"]  = bonus_end
                b["bonus_luck"] = bonus_luck
                updated = True
                break
        if not updated:
            buffs.append({
                "name":       name,
                "expires_at": expires_at.isoformat(),
                "bonus_str":  bonus_str,
                "bonus_dex":  bonus_dex,
                "bonus_int":  bonus_int,
                "bonus_end":  bonus_end,
                "bonus_luck": bonus_luck,
            })
        self.active_buffs_json = json.dumps(buffs)

    def buff_totals(self) -> dict:
        """Vrátí součet stat bonusů ze všech aktivních buffů."""
        totals = {"strength": 0, "dexterity": 0, "intelligence": 0, "endurance": 0, "luck": 0}
        for b in self.get_active_buffs():
            totals["strength"]     += b.get("bonus_str",  0)
            totals["dexterity"]    += b.get("bonus_dex",  0)
            totals["intelligence"] += b.get("bonus_int",  0)
            totals["endurance"]    += b.get("bonus_end",  0)
            totals["luck"]         += b.get("bonus_luck", 0)
        return totals

    def recalculate_stats(self):
        """Přepočítá hp_max z primary stats + level.

        Nová formule: END × class_mult × (level + 1), min 10
        atk / def_ / spd / mp_max jsou deprecated — tato metoda je NENASTAVUJE.
        """
        bt  = self.buff_totals()
        lvl = self.level
        cls = CharacterClass(self.cls)

        eff_end = self.endurance + bt.get("endurance", 0)

        # HP: END × class_mult × (level + 1), min 10
        hp_mult = CLASS_HP_MULT[cls]
        self.hp_max = max(10, eff_end * hp_mult * (lvl + 1))

        # Talent fortitude: +15% HP
        _talents = self.get_talents()
        if "fortitude" in _talents:
            self.hp_max = int(self.hp_max * 1.15)

        # Bonus HP z itemů (fallback — plný bonus aplikován v recalculate_with_gear())
        self.hp_max += self._equipped_hp_bonus()

        # Prestige: pouze HP bonus
        _pl = self.prestige_level or 0
        if _pl > 0:
            from models.prestige import prestige_bonus_mult
            _pmult = prestige_bonus_mult(_pl)
            self.hp_max = max(10, int(self.hp_max * _pmult["hp"]))

        # Subclass hp_mult
        if self.subclass:
            from models.subclass import SUBCLASS_DEFINITIONS
            _mults = SUBCLASS_DEFINITIONS.get(self.subclass, {}).get("stat_mults", {})
            if "hp_mult" in _mults:
                self.hp_max = max(10, int(self.hp_max * _mults["hp_mult"]))

    def _equipped_hp_bonus(self) -> int:
        """Fallback — plný bonus_hp se aplikuje v inventory.py::recalculate_with_gear()."""
        return 0

    @property
    def xp_to_next_level(self) -> int:
        return xp_to_next(self.level)

    def to_dict(self) -> dict:
        from game.combat_engine import _crit_chance
        bt = self.buff_totals()
        eff_lck = self.luck + bt.get("luck", 0)
        return {
            "id": self.id,
            "name": self.name,
            "cls": self.cls,
            "level": self.level,
            "xp": self.xp,
            "xp_to_next": self.xp_to_next_level,
            "gold": self.gold,
            "stats": {
                "strength":     self.strength     + bt.get("strength", 0),
                "dexterity":    self.dexterity    + bt.get("dexterity", 0),
                "intelligence": self.intelligence + bt.get("intelligence", 0),
                "endurance":    self.endurance    + bt.get("endurance", 0),
                "luck":         self.luck         + bt.get("luck", 0),
            },
            "active_buffs": self.get_active_buffs(),
            "combat": {
                "hp_max":    self.hp_max,
                "crit_pct":  round(_crit_chance(eff_lck) * 100, 1),
                "crit_mult": 175,
            },
            "stat_points": self.stat_points or 0,
            "arena": {
                "rank": self.arena_rank,
                "wins": self.arena_wins,
                "losses": self.arena_losses,
                "cooldown_until": self.arena_cooldown_until.isoformat() + "Z" if self.arena_cooldown_until else None,
            },
            "current_title": self.current_title,
            "faction": self.faction,
            "equipment": {
                "weapon":  self.eq_weapon,
                "helmet":  self.eq_helmet,
                "armor":   self.eq_armor,
                "gloves":  self.eq_gloves,
                "boots":   self.eq_boots,
                "ring":    self.eq_ring,
                "amulet":  self.eq_amulet,
            },
            "attunements": self.get_attunements(),
            "appearance": self.get_appearance(),
            "talents": self.get_talents(),
            "crystals":               self.crystals or 0,
            "crystal_name_color":     self.crystal_name_color,
            "crystal_portrait_frame": self.crystal_portrait_frame,
            "crystal_xp_boost_until": (
                self.crystal_xp_boost_until.isoformat()
                if self.crystal_xp_boost_until else None
            ),
            "season_portrait_frame":  self.season_portrait_frame,
            "subclass":               self.subclass,
            "prestige_level":         self.prestige_level or 0,
            "prestige_portrait_frame": self.prestige_portrait_frame,
            "onboarding_completed":   bool(self.onboarding_completed),
            "talent_t2":              self.talent_t2_key,
        }

    # ── Attunement helpers ────────────────────────────────────────────────────

    def get_attunements(self) -> list[int]:
        """Vrátí seznam ID odemčených attunementů."""
        if not self.attunements_json:
            return []
        try:
            return json.loads(self.attunements_json)
        except Exception:
            return []

    def get_attunement_progress(self) -> dict[str, list[int]]:
        """Vrátí slovník {chain_id_str: [dokončené quest_id]}."""
        if not self.attunement_progress_json:
            return {}
        try:
            return json.loads(self.attunement_progress_json)
        except Exception:
            return {}

    def add_attunement_quest_progress(self, quest_id: int) -> bool:
        """
        Zaznamená dokončení chain questu.
        Vrátí True pokud tímto questem byl chain zcela dokončen (attunement odemčen).
        """
        from models.attunement import QUEST_CHAIN_MAP, ATTUNEMENT_CHAINS
        if quest_id not in QUEST_CHAIN_MAP:
            return False

        info     = QUEST_CHAIN_MAP[quest_id]
        chain_id = str(info["chain_id"])
        progress = self.get_attunement_progress()

        if chain_id not in progress:
            progress[chain_id] = []
        if quest_id not in progress[chain_id]:
            progress[chain_id].append(quest_id)
        self.attunement_progress_json = json.dumps(progress)

        # Zkontroluj, jestli je chain kompletní
        chain = next(c for c in ATTUNEMENT_CHAINS if str(c["id"]) == chain_id)
        if set(chain["quest_ids"]).issubset(set(progress[chain_id])):
            attunements = self.get_attunements()
            if int(chain_id) not in attunements:
                attunements.append(int(chain_id))
                self.attunements_json = json.dumps(attunements)
    # ── Talent helpers ────────────────────────────────────────────────────────

    def get_talents(self) -> list[str]:
        """Vrátí seznam klíčů odemčených talentů."""
        if not self.talents_json:
            return []
        try:
            return json.loads(self.talents_json)
        except Exception:
            return []

    def get_t2_talent(self) -> str | None:
        """Vrátí klíč zvoleného T2 talentu nebo None."""
        return self.talent_t2_key or None

    def check_and_unlock_talents(self) -> list[str]:
        """
        Zkontroluje a odemkne všechny dostupné talenty pro aktuální level a třídu.
        Vrátí seznam nově odemčených klíčů (prázdný = nic nového).
        """
        from game.talents import get_unlockable_keys
        current   = set(self.get_talents())
        available = set(get_unlockable_keys(self.cls, self.level))
        newly     = list(available - current)
        if newly:
            self.talents_json = json.dumps(sorted(current | available))
        return newly

    # ── Appearance helpers ────────────────────────────────────────────────────

    def get_appearance(self) -> dict:
        """
        Return appearance dict with DiceBear Adventurer options.
        Falls back to DEFAULT_APPEARANCE if not set.
        """
        from game.appearance import DEFAULT_APPEARANCE
        if not self.appearance_json:
            return DEFAULT_APPEARANCE.copy()
        try:
            loaded = json.loads(self.appearance_json)
            # Merge with defaults to ensure new fields have defaults
            result = DEFAULT_APPEARANCE.copy()
            result.update(loaded)
            return result
        except Exception:
            return DEFAULT_APPEARANCE.copy()

    def set_appearance(self, appearance_dict: dict):
        """Set appearance from dict (validation happens in router)."""
        self.appearance_json = json.dumps(appearance_dict)
