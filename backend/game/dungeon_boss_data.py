"""
game/dungeon_boss_data.py — Static data for the 50-boss dungeon system.

Each dungeon has 50 bosses. enemy_mult formula: 0.5 + (boss_num / 50) * 2.0
Milestone bosses (boss_num % 5 == 0) guarantee a class-specific item drop.
Item tier for milestone: item_index = (boss_num // 5 - 1) // 2  → 0-4
"""
from __future__ import annotations

# ── enemy_mult helper ─────────────────────────────────────────────────────────
def boss_enemy_mult(boss_num: int) -> float:
    return round(0.5 + (boss_num / 50) * 2.0, 3)


# ── Boss definitions ──────────────────────────────────────────────────────────
# Format per boss: {"num": int, "name": str, "desc": str}
# enemy_mult is computed dynamically via boss_enemy_mult(boss_num)

DUNGEON_BOSS_DEFINITIONS: dict[str, list[dict]] = {
    "tomb_of_forgotten": [
        {"num": 1,  "name": "Ashbone Crawler",          "desc": "A mindless skeleton animated by residual death magic."},
        {"num": 2,  "name": "The Lurking Shade",         "desc": "A restless spirit feeding on the grief of the living."},
        {"num": 3,  "name": "Graveclaw Revenant",        "desc": "A corpse that refused to stay buried, driven by ancient rage."},
        {"num": 4,  "name": "Bonecage Sentinel",         "desc": "A warden of the dead, sealed within its own skeletal framework."},
        {"num": 5,  "name": "Mirewalker Wraith",         "desc": "A marsh ghost that has drowned the living for centuries."},
        {"num": 6,  "name": "The Hollow Seeker",         "desc": "A soul stripped of memory, endlessly hunting what it lost."},
        {"num": 7,  "name": "Tombveil Specter",          "desc": "A veil between realms given monstrous, hungry form."},
        {"num": 8,  "name": "Deadwhisper Wight",         "desc": "Its voice carries curses from a forgotten age."},
        {"num": 9,  "name": "Soulless Reaper",           "desc": "An executioner who chose undeath over oblivion."},
        {"num": 10, "name": "Dreadbone Desecrator",      "desc": "A lich-spawn that profanes every grave it walks over."},
        {"num": 11, "name": "Shroudmaw Husk",            "desc": "A hollow husk animated by a thousand restless souls."},
        {"num": 12, "name": "Gravebloom Crawler",        "desc": "Death and decay bloom wherever it feeds."},
        {"num": 13, "name": "Rotbound Sentinel",         "desc": "Ancient armor fused permanently with a rotting corpse."},
        {"num": 14, "name": "The Ashen Prophet",         "desc": "A prophet who cursed himself to live forever in ashes."},
        {"num": 15, "name": "Void-Touched Lich",         "desc": "A lich whose necromantic power has been corrupted by the void."},
        {"num": 16, "name": "Duskbound Revenant",        "desc": "Bound to the dusk hour, it is neither living nor truly dead."},
        {"num": 17, "name": "Tombheart Executioner",     "desc": "Its beating heart was ripped out and replaced with a tombstone."},
        {"num": 18, "name": "Cryptsoul Shade",           "desc": "A shade that has haunted the deepest crypts since antiquity."},
        {"num": 19, "name": "Fleshknit Abomination",     "desc": "Stitched together from the bodies of fallen heroes."},
        {"num": 20, "name": "Grimshroud Weaver",         "desc": "Weaves a death-shroud from the souls it harvests."},
        {"num": 21, "name": "The Pallid Specter",        "desc": "So pale it seems made of moonlight and malice."},
        {"num": 22, "name": "Bonebreak Juggernaut",      "desc": "Breaks the bones of the living to build its ever-growing form."},
        {"num": 23, "name": "Soulchain Warden",          "desc": "Ancient chains bind countless souls to its will."},
        {"num": 24, "name": "Decaymaw Leviathan",        "desc": "A massive undead creature that devours entire graveyards."},
        {"num": 25, "name": "Verglas the Deathlord",     "desc": "Once a great king, now master of the Tomb's inner sanctum."},
        {"num": 26, "name": "Blacksoul Remnant",         "desc": "A fragment of a shattered dark soul, endlessly wrathful."},
        {"num": 27, "name": "Gravebound Horror",         "desc": "It crawls from the deepest graves, dragging the earth with it."},
        {"num": 28, "name": "Withered Revenant",         "desc": "Withered by centuries of undeath, yet still terrifyingly strong."},
        {"num": 29, "name": "Darkroot Haunter",          "desc": "Roots of darkness follow where it walks."},
        {"num": 30, "name": "Soulpyre Flamewraith",      "desc": "Burns with the cold fire of ten thousand trapped souls."},
        {"num": 31, "name": "Tombshard Golem",           "desc": "A golem built entirely from shattered tombstones."},
        {"num": 32, "name": "The Mourning Shade",        "desc": "It mourns its victims softly just before it slays them."},
        {"num": 33, "name": "Ashwalker Revenant",        "desc": "Walks through ash as though born from it."},
        {"num": 34, "name": "Boneweald Heretic",         "desc": "A heretic priest who consorted with undead powers."},
        {"num": 35, "name": "Cryptwatch Colossus",       "desc": "A colossus that has guarded the Tomb's deepest vault for millennia."},
        {"num": 36, "name": "Soulharvest Reaper",        "desc": "Reaps souls from the living to feed the Tomb's power."},
        {"num": 37, "name": "The Grim Wanderer",         "desc": "A wanderer who lost itself in the tomb and became something else."},
        {"num": 38, "name": "Deadfrost Warden",          "desc": "Ice and death walk hand in hand through this warden."},
        {"num": 39, "name": "Voidborn Wraith",           "desc": "Spawned from the void that grows at the heart of the Tomb."},
        {"num": 40, "name": "Deathpact Invoker",         "desc": "An invoker who made a binding pact with death itself."},
        {"num": 41, "name": "Shadowflesh Amalgam",       "desc": "Shadow and rotting flesh fused into a singular horror."},
        {"num": 42, "name": "The Undying Keeper",        "desc": "It has guarded the Tomb's final secret for an age."},
        {"num": 43, "name": "Gravefire Oracle",          "desc": "It sees the death of all things and shapes fate accordingly."},
        {"num": 44, "name": "Bonestorm Awakened",        "desc": "When it moves, bones from nearby graves join its form."},
        {"num": 45, "name": "Soulwarden Prime",          "desc": "The prime guardian, ancient beyond all reckoning."},
        {"num": 46, "name": "Darkbound Lich",            "desc": "A lich bound so deeply to darkness it has become shadow."},
        {"num": 47, "name": "The Eternal Pale",          "desc": "Pale as death itself, it knows no hunger except for souls."},
        {"num": 48, "name": "Tombfall Annihilator",      "desc": "It tears apart both the tomb and anything living within it."},
        {"num": 49, "name": "Gravewatch Devastator",     "desc": "The final defender before the Tomb's deepest secret."},
        {"num": 50, "name": "The Deathlord Eternal",     "desc": "Supreme ruler of the Tomb — an ancient evil that predates memory."},
    ],
    "fiery_depths": [
        {"num": 1,  "name": "Cinder Grunt",              "desc": "A lowly fire elemental thrown up from the earth's depths."},
        {"num": 2,  "name": "Embershard Seeker",         "desc": "Sharp shards of obsidian animated by trapped flame."},
        {"num": 3,  "name": "Moltenscale Lizard",        "desc": "Its scales are perpetually molten and dripping."},
        {"num": 4,  "name": "Scorchbound Wretch",        "desc": "A creature consumed by fire from the inside out."},
        {"num": 5,  "name": "Lavaborn Sentinel",         "desc": "Born directly from a lava flow, with iron-hard skin."},
        {"num": 6,  "name": "Ashen Fangbeast",           "desc": "A beast whose maw is filled with ash and roaring flame."},
        {"num": 7,  "name": "Scorchclaw Ravager",        "desc": "It leaves scorched claw marks on everything it touches."},
        {"num": 8,  "name": "Emberfist Brawler",         "desc": "Its fists strike with the impact of a volcanic eruption."},
        {"num": 9,  "name": "Cinder Prophet",            "desc": "A prophet who received a vision of a world consumed by fire."},
        {"num": 10, "name": "Magmahide Colossus",        "desc": "A colossal creature whose hide runs with living magma."},
        {"num": 11, "name": "The Burning Shade",         "desc": "Even its shadow sears the ground it falls on."},
        {"num": 12, "name": "Igniteborn Berserker",      "desc": "Born during a volcanic eruption, it fights in a constant frenzy."},
        {"num": 13, "name": "Volcanis Drake",            "desc": "A drake that breathes not flames but streams of magma."},
        {"num": 14, "name": "Flameveil Specter",         "desc": "A specter who died in an ancient volcanic eruption, still burning."},
        {"num": 15, "name": "Cinderheart Warlord",       "desc": "A warlord who sold his heart to the fire in exchange for power."},
        {"num": 16, "name": "Scorchmantle Titan",        "desc": "Wears a mantle made from charred bones and cooled magma."},
        {"num": 17, "name": "The Infernal Crawler",      "desc": "Crawls through lava as though it were water."},
        {"num": 18, "name": "Ashwing Gargoyle",          "desc": "Stone and ash fused into a winged horror."},
        {"num": 19, "name": "Lavaform Devourer",         "desc": "Devours everything organic it encounters to fuel its flame."},
        {"num": 20, "name": "Emberstoke Champion",       "desc": "Champion of the inner fire realms, veteran of a thousand battles."},
        {"num": 21, "name": "Ashscale Tormentor",        "desc": "Torments prey with burning scales and suffocating ash clouds."},
        {"num": 22, "name": "The Pyreclad Stalker",      "desc": "Cloaked in flames, it stalks prey through rivers of magma."},
        {"num": 23, "name": "Magmaborne Horror",         "desc": "An abomination of fused rock and living fire."},
        {"num": 24, "name": "Cinderfall Brute",          "desc": "Falls from above, leaving craters of cinder on impact."},
        {"num": 25, "name": "Ignaros the Flamelord",     "desc": "First lord of the inner flame, ancient ruler of these depths."},
        {"num": 26, "name": "Scorchsoul Revenant",       "desc": "The revenant of a mage who perished surrounded by his own fire spells."},
        {"num": 27, "name": "Moltenbound Behemoth",      "desc": "So large it bends the cave floor under each step."},
        {"num": 28, "name": "Ashcrown Tyrant",           "desc": "Claims a crown of hardened ash and molten gold."},
        {"num": 29, "name": "Flamewoven Specter",        "desc": "Its body is woven entirely from interlocked threads of flame."},
        {"num": 30, "name": "Infernus Guardian",         "desc": "A guardian of the deep fire chambers, sworn to deny all intruders."},
        {"num": 31, "name": "Emberthorn Slayer",         "desc": "Named for the jagged thorns of slag that cover its body."},
        {"num": 32, "name": "Cinderbane Destroyer",      "desc": "A destroyer who leaves only cinders in its wake."},
        {"num": 33, "name": "The Magma Warden",          "desc": "Seals the passage between the upper and lower fire realms."},
        {"num": 34, "name": "Volcanis Tormentor",        "desc": "Channels the fury of the volcano to torment intruders."},
        {"num": 35, "name": "Ashpyre Colossus",          "desc": "A colossal being of ash and dying fire, endlessly patient."},
        {"num": 36, "name": "Scorchveil Nightmare",      "desc": "A nightmare given form by the screams of those who burned here."},
        {"num": 37, "name": "Emberlord Ravager",         "desc": "A ravager lord who can melt stone with a single strike."},
        {"num": 38, "name": "The Burning Throne",        "desc": "The throne itself, animated by the primordial fire that birthed it."},
        {"num": 39, "name": "Lavafall Annihilator",      "desc": "A being of pure destructive volcanic energy."},
        {"num": 40, "name": "Moltenbound Deathlord",     "desc": "A deathlord of fire who guards the passage to the volcano's heart."},
        {"num": 41, "name": "Ashveil Desecrator",        "desc": "It desecrates all that it touches, leaving only ash behind."},
        {"num": 42, "name": "Cinder Eternal",            "desc": "It has burned since before history was written."},
        {"num": 43, "name": "Flameheart Tyrant",         "desc": "Its heart is a furnace that has never gone cold."},
        {"num": 44, "name": "The Searing Colossus",      "desc": "So hot that standing near it blisters skin in seconds."},
        {"num": 45, "name": "Ignareth the Burned",       "desc": "A god of fire stripped of divinity, burning eternally in hate."},
        {"num": 46, "name": "Scorchborn Annihilator",    "desc": "Born of scorch and fury at the world's creation."},
        {"num": 47, "name": "Moltensoul Keeper",         "desc": "Keeps the inner fire alive at any cost."},
        {"num": 48, "name": "Ashfall Leviathan",         "desc": "A leviathan that swims through pools of magma effortlessly."},
        {"num": 49, "name": "The Final Conflagration",   "desc": "The last fire before the void — a living apocalypse."},
        {"num": 50, "name": "Infernus the Undying",      "desc": "The supreme fire lord, who cannot be slain by conventional means."},
    ],
    "citadel_of_chaos": [
        {"num": 1,  "name": "Shatterveil Drone",         "desc": "A mindless drone sent through a rift in reality."},
        {"num": 2,  "name": "Voidborn Watcher",          "desc": "Watches from between dimensions, unseen until it strikes."},
        {"num": 3,  "name": "Chaosform Wretch",          "desc": "A being whose form shifts unpredictably between states of matter."},
        {"num": 4,  "name": "Riftwalker Shade",          "desc": "Slides through rifts in reality to attack from any angle."},
        {"num": 5,  "name": "Entropy Herald",            "desc": "A herald who announces the arrival of true chaos."},
        {"num": 6,  "name": "Mindshred Cultist",         "desc": "A cultist whose mind was torn apart by chaos energies."},
        {"num": 7,  "name": "Voidmantle Stalker",        "desc": "Cloaked in the void, it stalks its prey unseen."},
        {"num": 8,  "name": "Fracturborn Horror",        "desc": "Born from a fracture in the fabric of reality itself."},
        {"num": 9,  "name": "Chaosbound Reaver",         "desc": "A reaver bound to the service of chaos for eternity."},
        {"num": 10, "name": "Nullborn Colossus",         "desc": "A colossus spawned from the void between worlds."},
        {"num": 11, "name": "The Shattered Visage",      "desc": "Its face is a kaleidoscope of shattered realities."},
        {"num": 12, "name": "Voidheart Tormentor",       "desc": "It reaches into its victims' hearts with tendrils of void."},
        {"num": 13, "name": "Riftpiercer Assassin",      "desc": "An assassin who strikes through dimensional rifts."},
        {"num": 14, "name": "Chaosweave Specter",        "desc": "A specter woven from raw threads of chaos energy."},
        {"num": 15, "name": "The Fractured Mind",        "desc": "A mind so broken by chaos it has become a weapon."},
        {"num": 16, "name": "Voidthorn Ravager",         "desc": "Its thorns draw not blood but void energy from victims."},
        {"num": 17, "name": "Nullforged Juggernaut",     "desc": "Forged in the null-space between worlds."},
        {"num": 18, "name": "Chaosborn Berserker",       "desc": "Born into chaos, it fights with zero regard for self-preservation."},
        {"num": 19, "name": "Riftbound Abomination",     "desc": "Bound across multiple rifts, it exists in several places at once."},
        {"num": 20, "name": "Entropy Warden",            "desc": "A warden who has embraced entropy as a guiding philosophy."},
        {"num": 21, "name": "The Collapsing Star",       "desc": "A being whose core perpetually collapses like a dying star."},
        {"num": 22, "name": "Voidweave Destabilizer",    "desc": "Destabilizes the fabric of reality with each strike."},
        {"num": 23, "name": "Chaosform Annihilator",     "desc": "Takes on the most destructive form available to it."},
        {"num": 24, "name": "Nullrift Prophet",          "desc": "A prophet who has glimpsed the void at the end of all things."},
        {"num": 25, "name": "Malachar the Unbound",      "desc": "An ancient entity that escaped its dimensional prison at great cost."},
        {"num": 26, "name": "Voidshard Devourer",        "desc": "Devours the very light of creation."},
        {"num": 27, "name": "Chaosborn Tyrant",          "desc": "Claims dominion over all chaotic spaces."},
        {"num": 28, "name": "Riftcrown Warlord",         "desc": "A warlord crowned by a rift that tears space around their head."},
        {"num": 29, "name": "Nullbound Revenant",        "desc": "Bound to the null-void, seeking release through destruction."},
        {"num": 30, "name": "The Dimensional Horror",    "desc": "A horror that exists across multiple dimensions simultaneously."},
        {"num": 31, "name": "Voidflame Incinerator",     "desc": "Burns with the cold flame of the void."},
        {"num": 32, "name": "Chaosmantle Slayer",        "desc": "A slayer whose mantle is sewn from the skins of shattered realities."},
        {"num": 33, "name": "The Entropy Engine",        "desc": "A machine-like entity that converts order into chaos."},
        {"num": 34, "name": "Riftwalker Leviathan",      "desc": "A leviathan-scale being that walks between worlds."},
        {"num": 35, "name": "Nullfire Colossus",         "desc": "A colossus whose inner fire burns with void-energy."},
        {"num": 36, "name": "Chaosweaver Prime",         "desc": "The prime chaos weaver who shapes the citadel's reality."},
        {"num": 37, "name": "Voidborn Annihilator",      "desc": "Annihilates all it touches, replacing matter with void."},
        {"num": 38, "name": "The Shattered Codex",       "desc": "An ancient text given terrifying, chaotic life."},
        {"num": 39, "name": "Riftborn Destroyer",        "desc": "A destroyer who came through a rift from somewhere far worse."},
        {"num": 40, "name": "Nullcrown Champion",        "desc": "The champion of the null-crown, protector of the inner sanctum."},
        {"num": 41, "name": "Chaosflesh Abomination",    "desc": "What happens when chaos consumes living flesh completely."},
        {"num": 42, "name": "Voidbound Devastator",      "desc": "Bound to the void by ancient pacts, devastating all."},
        {"num": 43, "name": "The Collapsing Form",       "desc": "Its form collapses and reforms in cycles of destruction."},
        {"num": 44, "name": "Riftpiercer Prime",         "desc": "The prime rifter, able to open dimensional tears at will."},
        {"num": 45, "name": "The Void Incarnate",        "desc": "Void made manifest. Everything about it is fundamentally wrong."},
        {"num": 46, "name": "Nullborn Apocalypse",       "desc": "The harbinger of a void that will consume all reality."},
        {"num": 47, "name": "Chaosbound Ancient",        "desc": "An ancient chaos entity who predates the citadel itself."},
        {"num": 48, "name": "Voidweave Harbinger",       "desc": "Harbinger of the final collapse of all ordered reality."},
        {"num": 49, "name": "The Fractal Nightmare",     "desc": "A fractal nightmare — the more you look, the worse it becomes."},
        {"num": 50, "name": "Malachar the Eternal",      "desc": "The supreme chaos entity, fully unbound, seeking to unmake all things."},
    ],
}


# ── Dungeon-only items ────────────────────────────────────────────────────────
# Tuple format identical to SEED_CLASS_ITEMS:
# (name, type, rarity, desc, icon, atk, def_, spd, hp, xp,
#  s_str, s_dex, s_int, s_end, s_luck, min_level, sell, hint_class)
#
# Item tier per milestone: tier = (boss_num // 5 - 1) // 2  → 0-4
# DUNGEON_ONLY_ITEMS[dungeon_key][cls][tier_index] → item tuple
#
# 5 items × 3 classes × 3 dungeons = 45 items total.

DUNGEON_ONLY_ITEMS: dict[str, dict[str, list[tuple]]] = {
    "tomb_of_forgotten": {
        "warrior": [
            # tier 0 — bosses 5, 10
            ("Gravewarden's Cleaver", "weapon", "rare",
             "A cleaver blessed by the warden of eternal graves.",
             "⚔️", 18, 0, 0, 0, 0, 6, 0, 0, 3, 0, 8, 120, "warrior"),
            # tier 1 — bosses 15, 20
            ("Bonecrusher's Pauldrons", "armor", "rare",
             "Pauldrons forged from the bones of fallen champions.",
             "🛡️", 0, 14, 0, 0, 0, 8, 0, 0, 4, 0, 12, 200, "warrior"),
            # tier 2 — bosses 25, 30
            ("Skull Basher's Helm", "helmet", "epic",
             "A helm carved from the skull of an undead colossus.",
             "⛑️", 0, 10, 0, 0, 0, 10, 0, 0, 6, 0, 18, 450, "warrior"),
            # tier 3 — bosses 35, 40
            ("Soulchain Gauntlets", "gloves", "epic",
             "Gauntlets wreathed in chains of trapped souls.",
             "🧤", 0, 8, 0, 0, 0, 12, 0, 0, 8, 0, 22, 550, "warrior"),
            # tier 4 — bosses 45, 50
            ("Deathlord's Signet", "ring", "legendary",
             "The signet of the Tomb's supreme ruler, radiating death-power.",
             "💍", 0, 0, 0, 0, 0, 16, 0, 0, 10, 3, 28, 2000, "warrior"),
        ],
        "mage": [
            # tier 0
            ("Staff of the Hollow Shade", "weapon", "rare",
             "A gnarled staff imbued with the power of hollow shades.",
             "🪄", 16, 0, 0, 0, 0, 0, 0, 6, 2, 0, 8, 120, "mage"),
            # tier 1
            ("Shroud of the Pale", "armor", "rare",
             "A robe woven from the very fabric of death.",
             "👘", 0, 12, 0, 0, 0, 0, 0, 8, 3, 0, 12, 200, "mage"),
            # tier 2
            ("Cryptwatch Crown", "helmet", "epic",
             "A crown worn by the watchers of the ancient crypt.",
             "👑", 0, 8, 0, 0, 0, 0, 0, 12, 5, 2, 18, 450, "mage"),
            # tier 3
            ("Bonewraith Wraps", "gloves", "epic",
             "Wraps made from the sinew of wraith-bone.",
             "🧤", 0, 6, 0, 0, 0, 0, 0, 14, 4, 3, 22, 550, "mage"),
            # tier 4
            ("The Eternal Pale's Focus", "amulet", "legendary",
             "The focus crystal of the Tomb's most ancient specter.",
             "📿", 0, 0, 0, 0, 0, 0, 0, 20, 8, 4, 28, 2000, "mage"),
        ],
        "ranger": [
            # tier 0
            ("Graveclaw Shortbow", "weapon", "rare",
             "A shortbow strung with sinew from a graveclaw revenant.",
             "🏹", 17, 0, 0, 0, 0, 0, 6, 0, 2, 1, 8, 120, "ranger"),
            # tier 1
            ("Tombveil Leather", "armor", "rare",
             "Leather armor tanned from the hide of a tombveil specter.",
             "🥋", 0, 13, 0, 0, 0, 0, 8, 0, 3, 1, 12, 200, "ranger"),
            # tier 2
            ("Deathwhisper Hood", "helmet", "epic",
             "A hood that whispers the weaknesses of nearby undead.",
             "🎭", 0, 8, 0, 0, 0, 0, 11, 0, 4, 3, 18, 450, "ranger"),
            # tier 3
            ("Specterfoot Boots", "boots", "epic",
             "Boots that let the wearer move silently over any surface.",
             "👟", 0, 7, 0, 0, 0, 0, 13, 0, 3, 4, 22, 550, "ranger"),
            # tier 4
            ("Soulhunt Amulet", "amulet", "legendary",
             "An amulet that marks the souls of enemies for the hunt.",
             "📿", 0, 0, 0, 0, 0, 0, 18, 0, 6, 6, 28, 2000, "ranger"),
        ],
    },
    "fiery_depths": {
        "warrior": [
            ("Emberstoke Axe", "weapon", "rare",
             "An axe forged in the fires of the Emberstoke champions.",
             "⚔️", 22, 0, 0, 0, 0, 7, 0, 0, 4, 0, 15, 180, "warrior"),
            ("Moltenscale Plate", "armor", "epic",
             "Plate armor forged from cooled molten-scale lizard hide.",
             "🛡️", 0, 18, 0, 0, 0, 9, 0, 0, 6, 0, 18, 500, "warrior"),
            ("Cindercrown", "helmet", "rare",
             "A crown of cinders that never fully cools.",
             "⛑️", 0, 14, 0, 0, 0, 11, 0, 0, 5, 0, 21, 280, "warrior"),
            ("Lavaborn Greaves", "boots", "epic",
             "Greaves cast in a river of lava, worn by fire lords.",
             "👢", 0, 12, 0, 0, 0, 13, 0, 0, 7, 0, 24, 600, "warrior"),
            ("Infernus Brand", "ring", "legendary",
             "A ring branded with the seal of the supreme fire lord.",
             "💍", 0, 0, 0, 0, 0, 18, 0, 0, 12, 2, 28, 2200, "warrior"),
        ],
        "mage": [
            ("Ashmantle Staff", "weapon", "rare",
             "A staff capped with a crystal of concentrated ash-fire.",
             "🪄", 20, 0, 0, 0, 0, 0, 0, 7, 3, 0, 15, 180, "mage"),
            ("Scorchweave Robe", "armor", "epic",
             "A robe woven from fireproof thread and embroidered with flame.",
             "👘", 0, 16, 0, 0, 0, 0, 0, 10, 5, 0, 18, 500, "mage"),
            ("Cinder Oracle Helm", "helmet", "rare",
             "A helm that grants visions within the flame.",
             "👑", 0, 12, 0, 0, 0, 0, 0, 13, 4, 2, 21, 280, "mage"),
            ("Emberstoke Gloves", "gloves", "epic",
             "Gloves that draw additional power from fire-based spells.",
             "🧤", 0, 9, 0, 0, 0, 0, 3, 16, 4, 0, 24, 600, "mage"),
            ("Flamelord's Scepter", "amulet", "legendary",
             "The sacred scepter of Ignaros, radiating primordial heat.",
             "📿", 0, 0, 0, 0, 0, 0, 0, 22, 10, 3, 28, 2200, "mage"),
        ],
        "ranger": [
            ("Scorchclaw Longbow", "weapon", "rare",
             "A longbow carved from scorchwood, never warped by heat.",
             "🏹", 21, 0, 0, 0, 0, 0, 7, 0, 3, 1, 15, 180, "ranger"),
            ("Ashveil Leather", "armor", "epic",
             "Leather treated with volcanic ash, light and heat-resistant.",
             "🥋", 0, 15, 0, 0, 0, 0, 10, 0, 5, 2, 18, 500, "ranger"),
            ("Ignite Tracker Hood", "helmet", "rare",
             "A hood that glows faintly, marking heated prey in darkness.",
             "🎭", 0, 11, 0, 0, 0, 0, 12, 0, 3, 3, 21, 280, "ranger"),
            ("Cinder Stalker Boots", "boots", "epic",
             "Boots that leave no tracks even in cooled lava.",
             "👟", 0, 9, 0, 0, 0, 0, 15, 0, 4, 4, 24, 600, "ranger"),
            ("Pyreclad Hunter's Ring", "ring", "legendary",
             "Ring of the supreme pyreclad hunters, searing as it blazes.",
             "💍", 0, 0, 0, 0, 0, 4, 20, 0, 7, 5, 28, 2200, "ranger"),
        ],
    },
    "citadel_of_chaos": {
        "warrior": [
            ("Nullforged Greatsword", "weapon", "epic",
             "A greatsword forged in the null-space between dimensions.",
             "⚔️", 28, 0, 0, 0, 0, 9, 0, 0, 5, 0, 24, 700, "warrior"),
            ("Chaosbound Plate", "armor", "epic",
             "Plate armor held together by chaotic dimensional energy.",
             "🛡️", 0, 22, 0, 0, 0, 11, 0, 0, 8, 0, 26, 750, "warrior"),
            ("Voidcrown Bastion", "helmet", "legendary",
             "A crown-helm worn by the void's greatest champions.",
             "⛑️", 0, 18, 0, 0, 0, 14, 0, 0, 10, 2, 28, 2500, "warrior"),
            ("Rift-Gauntlets of Annihilation", "gloves", "epic",
             "Gauntlets that punch through rift-tears in reality.",
             "🧤", 0, 14, 0, 0, 0, 16, 0, 0, 9, 0, 28, 800, "warrior"),
            ("Malachar's Iron Brand", "ring", "legendary",
             "A ring bearing the seal of the supreme chaos entity Malachar.",
             "💍", 0, 0, 0, 0, 0, 22, 0, 0, 14, 3, 30, 3000, "warrior"),
        ],
        "mage": [
            ("Staff of Fractured Reality", "weapon", "epic",
             "A staff channeling power from fractures in the fabric of reality.",
             "🪄", 26, 0, 0, 0, 0, 0, 0, 9, 5, 0, 24, 700, "mage"),
            ("Voidweave Shroud", "armor", "epic",
             "A shroud that phases in and out of normal reality.",
             "👘", 0, 20, 0, 0, 0, 0, 0, 12, 7, 0, 26, 750, "mage"),
            ("Nullborn Crown", "helmet", "legendary",
             "A crown born from the null-void, amplifying all null-magic.",
             "👑", 0, 15, 0, 0, 0, 0, 0, 16, 8, 4, 28, 2500, "mage"),
            ("Chaosform Wraps", "gloves", "epic",
             "Wraps that shift form to better channel whatever chaos demands.",
             "🧤", 0, 12, 0, 0, 0, 0, 0, 18, 8, 0, 28, 800, "mage"),
            ("The Unbound Codex", "amulet", "legendary",
             "A fragment of the Shattered Codex, containing unbound chaos-spells.",
             "📿", 0, 0, 0, 0, 0, 0, 0, 26, 12, 5, 30, 3000, "mage"),
        ],
        "ranger": [
            ("Riftpiercer Recurve", "weapon", "epic",
             "A recurve bow that fires arrows through dimensional rifts.",
             "🏹", 27, 0, 0, 0, 0, 0, 9, 0, 4, 2, 24, 700, "ranger"),
            ("Chaoscloak Leather", "armor", "epic",
             "Leather armor that shifts color to match any environment.",
             "🥋", 0, 19, 0, 0, 0, 0, 12, 0, 6, 3, 26, 750, "ranger"),
            ("Voidmantle Hood", "helmet", "legendary",
             "A hood that renders the wearer effectively invisible in void-spaces.",
             "🎭", 0, 14, 0, 0, 0, 0, 16, 0, 7, 5, 28, 2500, "ranger"),
            ("Nullstalker Boots", "boots", "epic",
             "Boots that leave no trace in any dimension.",
             "👟", 0, 11, 0, 0, 0, 0, 18, 0, 6, 4, 28, 800, "ranger"),
            ("Fractal Huntmaster's Ring", "ring", "legendary",
             "Ring of the fractured huntmasters — strikes from everywhere at once.",
             "💍", 0, 0, 0, 0, 0, 5, 24, 0, 9, 6, 30, 3000, "ranger"),
        ],
    },
}


# ── Dungeon unlock conditions ─────────────────────────────────────────────────
# First dungeon has no prerequisite. Others require:
#   - min_bosses_in_prev: how many bosses must be defeated in the previous dungeon
#   - attunement_chain_id: integer chain ID from config/attunements.json that must
#     appear in char.get_attunements() (list of completed chain IDs).
#     Chain IDs: 1=Stezka Mrtvých (tomb), 2=Cesta Ohně (fiery), 3=Cesta Chaosu (citadel)
DUNGEON_UNLOCK_CONDITIONS: dict[str, dict] = {
    "tomb_of_forgotten": {
        "min_level":           8,
        "prev_dungeon":        None,
        "min_bosses_in_prev":  0,
        "attunement_chain_id": None,
    },
    "fiery_depths": {
        "min_level":           15,
        "prev_dungeon":        "tomb_of_forgotten",
        "min_bosses_in_prev":  25,
        "attunement_chain_id": 1,   # must have completed tomb attunement (chain 1)
    },
    "citadel_of_chaos": {
        "min_level":           24,
        "prev_dungeon":        "fiery_depths",
        "min_bosses_in_prev":  25,
        "attunement_chain_id": 2,   # must have completed fiery attunement (chain 2)
    },
}
