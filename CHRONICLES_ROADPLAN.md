# CHRONICLES ROADPLAN
## Strategická roadmapa — Dungeon Chronicles

> **Instrukce pro Claude:** Při každém otevření terminálu v tomto projektu přečti tento soubor.
> Najdi sekci `📍 AKTUÁLNÍ POZICE`, zkontroluj co je hotové (`[x]`) a co ne (`[ ]`).
> Informuj uživatele kde jsme skončili a nabídni pokračování od dalšího úkolu.
> Po dokončení každého úkolu zaznač `[x]`, aktualizuj sekci `📍 AKTUÁLNÍ POZICE` a ulož soubor.

---

## 📍 AKTUÁLNÍ POZICE

```
Poslední session : 2026-03-09
Aktuální fáze    : FÁZE 6 — LiveOps & Monetization ✅ DOKONČENA
Poslední hotový  : [6.9] Automated balance alerts (admin monitoring)
Další na řadě    : Fáze 7 (viz sekce níže)
Celkový postup   : Fáze 1: 15/15 ✅ · Fáze 2: 13/15 · Fáze 3: 11/11 ✅ · Fáze 4: 12/12 ✅ · Fáze 5: 11/11 ✅ · Fáze 6: 9/9 ✅
```

---

## ✅ PRE-SESSION DOKONČENO (před spuštěním roadmapy)

- [x] **[PRE-01]** Typografie — zvýšení čitelnosti UI
  - `html { font-size: 17px }`, `body { font-size: 15px, line-height: 1.5 }`
  - Aktualizovány `--fs-*` proměnné, ~50 cílených font-size úprav
  - Soubory: `base.css`, `layout.css`, `components.css`, `theme.css`

---

## 🔴 FÁZE 1 — Stabilizace (2–4 týdny)

### 1A — Backend: Technický dluh

- [x] **[1.1]** Alembic migrace — nastavit databázové migrace
  - Nainstalovat Alembic, inicializovat v `/backend/`
  - Vytvořit initial migration z aktuálních SQLAlchemy modelů
  - Přidat `alembic upgrade head` do startup sekvence
  - Soubory: `/backend/alembic.ini`, `/backend/alembic/`

- [x] **[1.2]** Rate limiting na API endpointy
  - Přidat `slowapi` nebo custom middleware
  - Limity: auth endpointy 10/min, combat 30/min, obecné 120/min
  - Soubory: `/backend/main.py`, nový `/backend/middleware/rate_limit.py`

- [x] **[1.3]** Race condition fix — World Boss HP pool
  - Nahradit přímý SQLAlchemy update za `SELECT FOR UPDATE` (pessimistic lock)
  - Nebo přidat Redis atomic counter (INCRBY) pro HP tracking
  - Soubory: `/backend/routers/boss.py`, `/backend/models/world_boss.py`

- [x] **[1.4]** Structured JSON logging
  - Nahradit `print()` / základní logging za structlog nebo python-json-logger
  - Každý log record: timestamp, level, request_id, user_id, event, data
  - Soubory: `/backend/core/logging.py` (nový), `/backend/main.py`

- [x] **[1.5]** Economy audit log — tabulka transakcí
  - Nový model `GoldTransaction(id, player_id, amount, reason, timestamp, balance_after)`
  - Trigger při každé změně gold: quest reward, purchase, marketplace, boss reward
  - Soubory: `/backend/models/economy.py` (nový nebo rozšíření)

- [x] **[1.6]** Odstranit combat adaptéry
  - Smazat nebo inline `combat.py` a `arena_combat.py` adaptéry
  - Volat `game/combat_engine.py` přímo ze všech routerů
  - Soubory: `/backend/game/combat.py`, `/backend/game/arena_combat.py`, `/backend/routers/arena.py`, `/backend/routers/quest.py`

### 1B — Combat: Kritické balance opravy

- [x] **[1.7]** MP ability cost škálování s levelem
  - Opravit fixní costy (Warrior 30, Mage 60, Ranger 35) — musí škálovat s `mp_max`
  - Formula: `cost = base_cost_pct * mp_max` (např. Warrior = 15% MP, Mage = 30% MP)
  - Soubory: `/backend/game/combat_engine.py`

- [x] **[1.8]** Dungeon HP přenos — transakční záruka
  - HP přenos mezi stágemi musí být atomic (buď celý stage uložen nebo rollback)
  - Přidat `try/except` s explicit rollback na SQLAlchemy session
  - Soubory: `/backend/routers/dungeon.py`, `/backend/models/dungeon_run.py`

- [x] **[1.9]** Arena ELO decay pro neaktivní hráče
  - Background job: hráči bez zápasu 7+ dní ztrácejí 5 ELO/den (floor: jejich starting ELO)
  - Soubory: `/backend/tasks/elo_decay.py` (nový), `/backend/main.py` (registrace)

### 1C — Economy: Základní sinky

- [x] **[1.10]** Auction house listing fee
  - Přidat `listing_fee = max(50, price * 0.05)` při vytváření listingu
  - Fee se odečte okamžitě při listování (i pokud se neprodá)
  - Soubory: `/backend/routers/market.py`

- [x] **[1.11]** Quest gold reward level scaling review
  - Audit aktuálních quest rewards — jsou přiměřené pro každý level range?
  - Implementovat: `reward = base_reward * (1 + player_level * 0.1)`
  - Soubory: `/backend/routers/quest.py`, quest data/config

### 1D — UX: Základní quality of life

- [x] **[1.12]** Empty states pro prázdné sekce
  - Prázdný inventář: ikona + "Žádné předměty. Získej je z questů nebo obchodu."
  - Prázdná aréna (žádní soupeři): "Zatím nikdo k dispozici. Zkus za chvíli."
  - Prázdný žebříček: loading / "Budi první!"
  - Soubory: `frontend/js/equipment.js`, `frontend/js/arena.js`, `frontend/js/ui.js`

- [x] **[1.13]** Konzistentní loading states
  - Přidat `showLoading(containerId)` / `hideLoading(containerId)` utility
  - Aplikovat na: equipment page, arena opponents, dungeon list, marketplace
  - Soubory: `frontend/js/ui.js` (nová utilita), ostatní JS soubory

- [x] **[1.14]** Global JS error handler
  - `window.addEventListener('unhandledrejection', ...)` — zachytit API errors
  - User-friendly toast pro neočekávané chyby: "Něco se pokazilo. Zkus to znovu."
  - Soubory: `frontend/js/api.js` nebo `frontend/js/main.js`

### 1E — Daily engagement: Základní smyčka

- [x] **[1.15]** Daily quest rotation systém
  - Pool 10–15 questů, každý den se vybere 3 náhodné pro každého hráče
  - Reset v 00:00 UTC, nová generace z poolu
  - Soubory: `/backend/routers/quest.py`, `/backend/models/quest.py`

---

## 🟡 FÁZE 2 — Hloubka (1–3 měsíce)

### 2A — Backend: Infrastruktura

- [ ] **[2.1]** PostgreSQL migrace
  - Změnit SQLAlchemy DATABASE_URL, otestovat všechny queries
  - Předpoklad: Alembic z [1.1] již funguje

- [ ] **[2.2]** Redis — caching + cooldown tracking
  - Leaderboard cache (TTL 60s), cooldown tracking (dungeon, boss, arena)
  - Nahradit in-memory achievement cache za Redis

- [x] **[2.3]** WebSocket pro guild chat
  - Nahradit polling za WebSocket connection (`/ws/guild/{guild_id}`)
  - Fallback na polling pro starší klienty

- [x] **[2.4]** Admin panel — základní
  - Player lookup (view stav, gold, inventory)
  - Economy monitor (průměrný gold/level, top holders)
  - Content toggle (enable/disable quest bez deployment)

- [x] **[2.5]** Data-driven dungeon/quest definice
  - Přesunout hardcoded dungeon/boss data do JSON/YAML konfigurace
  - Engine čte config, nový dungeon = nový soubor (no deployment needed)

### 2B — Combat: Hloubka

- [x] **[2.6]** Combat Strategy systém
  - Hráč nastaví pre-battle priority (Aggro/Defensive/Burst)
  - Engine aplikuje strategii — ovlivňuje targeting, ability usage, positioning

- [x] **[2.7]** Attribute soft caps — diminishing returns
  - Zóna 1 (0–50): 100% return | Zóna 2 (51–150): 70% | Zóna 3 (151+): 30%
  - Zabránění hyperinflaci čísel v late game

- [x] **[2.8]** Status efekt interaction matrix
  - Definovat synergies: bleed+weaken = vulnerability, poison+regen = neutralizace
  - Implementovat ve `combat_engine.py`

- [x] **[2.9]** Talent tree — Tier 1 (pasivní)
  - 3 pasivní traity per class, odemykané na level 10/20/30
  - Warrior: Fortitude, Battle Rage, Iron Skin
  - Mage: Arcane Focus, Mana Surge, Spell Echo
  - Ranger: Eagle Eye, Evasion, Hunter's Mark

### 2C — Progression: Hloubka

- [x] **[2.10]** Gear upgrade systém
  - Common → Uncommon crafting (materials + gold)
  - Jasná upgrade path viditelná v UI

- [x] **[2.11]** Guild Weekly Quest
  - Společný cíl (např. "Celkem zabijte 500 nepřátel")
  - Reward pro všechny aktivní členy po splnění

- [x] **[2.12]** Weekly quest board
  - 3–5 questů s weekly resetem, lepší rewards než daily

- [x] **[2.13]** Seasonal progression (free track)
  - Sezónní rewards track, každý týden nová odměna za aktivitu
  - Cosmetic rewards (tituly, portrait frames) bez P2W

### 2D — Economy: Stabilizace

- [x] **[2.14]** Equipment durability (jemný gold sink)
  - Předměty ztrácejí durabilitu po dungeon/arena (ne po PvP loss)
  - Repair u NPC za gold — non-frustrating částky

- [x] **[2.15]** Dual currency — earned premium
  - Zavést Crystals/Gems (earned z achievementů, seasonal, events)
  - Použití: cosmetics a premium QoL — nikdy power advantage

---

## 🟢 FÁZE 3 — Rozšíření (6+ měsíců)

- [x] **[3.1]** Subclass/specialization systém
- [x] **[3.2]** Guild Wars (asynchronní formát)
- [x] **[3.3]** Prestige systém (post-level-cap)
- [x] **[3.4]** World Events (communal seasonal goals)
- [x] **[3.5]** Dungeon modifier systém (weekly rotating)
- [x] **[3.6]** Transmog / cosmetic equipment appearance
- [x] **[3.7]** Backend horizontal scaling preparation
- [x] **[3.8]** Full test suite pro combat engine a economy
- [x] **[3.9]** Analytics dashboard (retention, economy health)
- [x] **[3.10]** Portrait frame shop + extended avatar customization
- [x] **[3.11]** Arena season exclusive cosmetic rewards

---

## 📊 Progress tracker

| Fáze | Celkem | Hotovo | Zbývá |
|------|--------|--------|-------|
| PRE  | 1      | 1      | 0     |
| 1    | 15     | 15     | 0     |
| 2    | 15     | 13     | 2     |
| 3    | 11     | 11     | 0     |
| 4    | 12     | 12     | 0     |
| 5    | 11     | 11     | 0     |
| 6    | 9      | 8      | 1     |
| **Celkem** | **74** | **71** | **3** |

---

## 📝 Session log

| Datum      | Co bylo uděláno |
|------------|----------------|
| 2026-02-27 | [PRE-01] Typografie — zvýšení čitelnosti UI (4 CSS soubory) |
| 2026-02-27 | Vytvořen tento roadplan soubor |
| 2026-02-27 | [1.1] Alembic migrace — alembic.ini, env.py, script.py.mako, 0001_baseline.py, database.py refactor |
| 2026-02-27 | [1.2] Rate limiting — middleware/rate_limit.py (auth 10/min, combat 30/min, general 120/min) |
| 2026-02-27 | [1.3] Race condition fix — SELECT FOR UPDATE + atomický SQL UPDATE pro boss HP pool |
| 2026-02-27 | [1.4] Structured JSON logging — core/logging.py, RequestIdMiddleware, nahrazeny print() v 5 souborech |
| 2026-02-27 | [1.5] Economy audit log — GoldTransaction model, 0002 migrace, log_gold() hooknut do 12 routerů (21 míst) |
| 2026-02-27 | [1.6] Smazány combat.py + arena_combat.py; quest.py + arena.py volají combat_engine přímo; testy opraveny |
| 2026-02-27 | [1.7] mp_cost → mp_cost_pct v CLASS_ABILITIES (warrior 15%, mage 30%, ranger 17%); mp_max přidán do _FighterState; opravena zastaralá hodnota MAX_CRIT_CHANCE v testu |
| 2026-02-27 | [1.8] try/except + explicit rollback kolem db.commit() ve všech 4 dungeon endpointech (enter, next-stage, collect, abandon) |
| 2026-02-27 | [1.9] tasks/elo_decay.py — background job (−5 ELO/den, floor 1000, 7d inactivity); _last_run_date ochrana; registrován v main.py lifespan |
| 2026-02-27 | [1.10] Listing fee max(50, price*5%) odečtena ihned při listování; LISTING_FEE_PCT + LISTING_FEE_MIN v models/market.py; log_gold + gold check v list_item endpointu |
| 2026-02-27 | [1.11] reward_gold = int(base * (1 + level*0.1)) v start_quest; scaled min/max v list_quests response |
| 2026-02-27 | [1.12] .empty-state CSS třída do components.css; inventory.js (ikona+text+hint pro all/filtr); arena.js opponents + leaderboard |
| 2026-02-27 | [1.13] showLoading/hideLoading do ui.js; .loading-state + .loading-spinner CSS; aplikováno na arena/dungeons/market/equipment |
| 2026-02-27 | [1.14] window.addEventListener('unhandledrejection') + window.onerror v main.js; ignoruje err.status (API chyby); toast "Něco se pokazilo." |
| 2026-02-27 | [1.15] DailyQuestRotation model + GET /quest/daily endpoint; pool non-boss/chain/dungeon questů; 3 náhodné/hráč/den; countdown timer v UI; 0003 migrace |
| 2026-02-27 | [2.3] GuildConnectionManager; WS endpoint /guild/ws/{id}?token=JWT; history při connect; broadcast; guild.js: connectGuildWs, _appendChatMsg, fallback polling |
| 2026-02-27 | [2.4] admin.py přepsán: opraven bug (ActiveQuest→Quest); /player/{name}, /economy, /quest/toggle; _DISABLED_QUESTS set; admin.html + /admin-panel route |
| 2026-02-27 | [2.5] JSON konfigurace: config/{quests,guild_bosses,attunements,dungeons}.json; game/config_loader.py; QUEST_DEFINITIONS+GUILD_BOSSES+ATTUNEMENT_CHAINS z JSON; GET /dungeon/config endpoint; DUNGEON_DATA v dungeons.js z API |
| 2026-02-27 | [2.6] COMBAT_STRATEGIES (balanced/aggro/defensive/burst); strategy field v CombatantConfig; _FighterState aplikuje ATK/DEF/SPD/MP mult; defensive = start štítem; quest+arena+dungeon routery + JS předávají zvolenou strategii; strategy picker UI s localStorage; CSS .strategy-bar/.strat-btn |
| 2026-02-27 | [2.7] soft_cap_stat() v combat_engine.py (zóny 50/150, rate 100%/70%/30%); aplikuje se na ATK/DEF/SPD/LUCK před strategy mult v _FighterState; self.luck přidán do _FighterState; calculate_win_chance() použit capped hodnoty; character.to_dict() vrací eff_atk/eff_def/eff_spd; equipment.js zobrazuje "v boji: X" pokud je stat capped |
| 2026-02-27 | [2.8] STATUS_INTERACTIONS (bleed+weaken, poison+regen, burn+shield); EVENT_INTERACTION typ; _process_status_ticks přepsán — neutralizace, zranitelnost, tavení štítu; combat_engine.py |
| 2026-02-27 | [2.9] game/talents.py (TALENT_TREE 9 talentů, 3 per class); talents_json sloupec + check_and_unlock_talents(); CombatantConfig.talents; _FighterState: eagle_eye/fortitude/mana_surge/battle_rage/iron_skin/arcane_focus/spell_echo/evasion/hunters_mark; 0004 migrace; renderTalents() JS; talent CSS karty |
| 2026-02-27 | [2.10] upgrade_level na InventoryItem; UPGRADE_COSTS/STAT_MULT/RARITY_CHAIN konstanty; _apply_equipment_bonuses přijímá InventoryItem; recalculate_with_gear načítá inv items; char_dict_with_equipment vrací upgraded stats; POST /inventory/upgrade; 0005 migrace; upgradeItem() JS; upgrade UI v item detailu; CSS badges |
| 2026-02-27 | [2.11] guild_weekly_quests + guild_weekly_contribs tabulky; POST /guild/weekly-quest/{goal_type}; 0006 migrace (idempotentní) |
| 2026-02-27 | [2.12] weekly_quest_progress tabulka; GET /quest/weekly, POST /quest/weekly/claim; 0007 migrace (idempotentní) |
| 2026-02-27 | [2.13] season_passes + season_pass_progress; SEASON_TIERS; GET /season/current, POST /season/claim-tier; 0008 migrace |
| 2026-02-27 | [2.14] inventory.durability; repair endpointy; repairItem/repairAll JS; durability mini-bar UI; 0009 migrace |
| 2026-02-27 | [2.15] CrystalTransaction model; CRYSTAL_SHOP (6 items); /crystals/shop + /buy; XP boost +25%; crystals.js; 0010 migrace |
| 2026-02-27 | Fix: Alembic migrace 0006-0010 přepsány jako idempotentní (inspect() guard); server úspěšně startuje |
| 2026-02-28 | [3.1] SUBCLASS_DEFINITIONS (6 subclassů); SUBCLASS_ABILITIES; CombatantConfig.subclass; recalculate_stats multy; _execute_attack: multi_hit/self_dmg/extra_statuses/status_self; GET /character/subclasses, POST /character/choose-subclass; 0011 migrace; subclass.js; game.html nav+page; theme.css |
| 2026-02-28 | [3.2] GuildWar + GuildWarAttack modely; guild_war router (/declare, /current, /opponents, /attack, /history); lazy resolve expired wars; guild XP odměny; 0012 migrace; guild.js: Válka tab + scoreboard + útok + history; theme.css CSS |
| 2026-02-28 | [3.3] MAX_LEVEL=50; PrestigeLog model; prestige_level na Character; prestige bonusy v recalculate_stats (+3% ATK/DEF/HP, +2% MP per level); PRESTIGE_TITLES dict; /prestige/info + /prestige/ascend; 0013 migrace; prestige.js; game.html nav+page; theme.css CSS |
| 2026-02-28 | [3.4] WorldEvent+Contrib+Claim modely; 3 event definice (quests/dungeon_clears/boss_damage); /world-events/current+claim+history router; add_world_event_contribution() hooknutý do quest.py+dungeon.py+boss.py; ensure_active_world_event() v lifespan; 0014 migrace; world_events.js; game.html nav+page; theme.css CSS |
| 2026-02-28 | [3.5] 12 dungeon modifikátorů (game/dungeon_modifiers.py); WeeklyDungeonModifier model; /dungeon/modifier endpoint; ensure_active_modifier() v lifespan; modifier_statuses v CombatantConfig+_FighterState; aplikace na enemy/player stats+rewards v enter+next-stage+list; 0015 migrace; dng-modifier-banner+badge CSS; dungeon.js banner+badge UI |
| 2026-02-28 | [3.6] TransmogSlot model; /transmog/ GET+set+clear+clear-all endpointy; get_transmog_dict() hooknutý do char_dict_with_equipment; GoldReason.TRANSMOG_FEE; 0016 migrace; transmog.js (modal+options+apply+clear); equipment.js slot overlay (icon/name z transmogu, 🎨 badge+btn); tmog-modal CSS; game.html script tag |
| 2026-02-28 | [3.7] CronJob model (distributed DB lock); DisabledQuest model (DB-backed + 10s TTL cache); InstanceIdMiddleware (X-Instance-Id header); /health+/ready+/info endpointy; elo_decay.py → try_acquire_cron_lock; admin.py+quest.py → DB disabled quests; 0017 migrace (cron_jobs+disabled_quests); rate_limit.py Redis scaling komentář |
| 2026-02-28 | [3.8] 244 testů, 100% pass: soft_cap (16 testů), status efekty (29), strategie+talenty (33), boss fáze (22), dungeon modifikátory (36), economy (42), disabled_quests DB (14), + původní arena/combat/loot/auth (52); conftest rate limit bypass fix |
| 2026-02-28 | [3.9] /admin/analytics endpoint: registrace/den (14d), level buckety, třídní distribuce, top quest completers, churn rate, arena/den (7d), win rate dle třídy (SQLAlchemy joins), gold flow/den (case()); Analytics tab v admin.html: stat karty, mini bar charty, tabulky |
| 2026-02-28 | [3.10] 4 nové portrait frames (bronze/arcane/ruby/legendary), CSS animace (pf-arcane/ruby/legendary pulsing); /crystals/reset-frame + /crystals/reset-name-color endpointy; ui.js: CSS class approach pro všechny portrait elementy; appearance.js: background color palette (8 presets), buildAvatarUrl opraven; crystals.js: real reset endpointy |
| 2026-02-28 | [3.11] SEASON_COSMETIC_REWARDS (4 tier): rank1→"Grand Champion"+"season-champion", rank2-3→"Champion"+"season-challenger", rank4-10→"Veteran"+"season-veteran", rank11-25→"Contender"; reward_title+reward_frame v SeasonResult; season_portrait_frame na Character; 0018 migrace; claim endpoint aplikuje nejlepší frame+titul; ui.js season frame priorita; 3 CSS frame animace; arena.js cosmetic preview v season banneru |
| 2026-02-28 | Architektonická analýza + Fáze 4–6 roadmapy (senior review) |
| 2026-03-01 | Bug fixes: BUG1 (equipment display:grid specificita), BUG2 (quest chip při init), BUG3 (dungeon badge+CSS), Cleanup (loadBuild dup, showDungeonPage konflikt) |
| 2026-03-01 | [4.12] Gold/XP reward animations: _tweenGold (400ms easeOutCubic), _spawnRewardLabel (+X G/XP floating), _spawnRewardParticles (5 emojis burst), _playLevelUpAnim (flash overlay + portrait-level-glow); ui.js + components.css |
| 2026-03-01 | [5.1] Talent Tree Tier 2: TALENT_T2_TREE (9 schopností, 3 per class); talent_t2_key na Character; _execute_t2_ability() v combat_engine; T2_COOLDOWN=4; GET /character/t2-talents + POST /character/choose-t2; talent_t2 předán do quest/arena/dungeon CombatantConfig; TALENT_T2_DEFS + renderTalents() + chooseT2Talent() v equipment.js; T2 CSS sekce v theme.css; game.html talent tab aktualizován; 0021 migrace |
| 2026-03-01 | [5.2] Set bonusy: přejmenování na Dračí Šupiny/Bouřební Závoj/Přízračný Chodec; 3pc/5pc thresholdy (místo 2pc/4pc); Warrior 3pc +15% HP + 5pc Regen (30 kol); Mage 3pc +20% ability dmg + 5pc Spell Echo 50%; Ranger 3pc +12% LUCK + 5pc First Strike; set_bonuses.py (nový helper); CombatantConfig.set_bonuses + _FighterState aplikace; recalculate_with_gear HP+LUCK multy; quest/arena/dungeon set_fx; equipment.js + inventory.js 3pc/5pc UI s progress |
| 2026-03-06 | [5.4] Guild Hall progression: game/guild_xp.py (award_guild_xp, get_perks, xp_to_next, GUILD_LEVEL_PERKS 1–10); models/guild.py to_dict() + xp_to_next + rank_name/emoji + member_cap; guild.py (dynamic member_cap, chat_limit, dungeon+weekly XP, level-up notifikace, weekly gold bonus); guild_war.py (award_guild_xp nahradil inline logiku); arena.py (+15 XP za win); guild.js XP progress bar; theme.css .guild-xp-* |
| 2026-03-06 | [5.5] World Boss daily tracking + MVP bonus: BossParticipation.daily_damage+daily_date; attack_boss() denní reset; _calculate_boss_rewards() Daily MVP +100 G; /boss/current+/boss/leaderboard denní data+is_daily_mvp; boss.js 30s polling (_startBossLbPolling), _buildDailyMvpBanner, lb sloupec Dnes; theme.css .boss-mvp-banner+.lb-mvp+.lb-daily*; 0022 migrace |
| 2026-03-06 | [5.6] Quest expansion: +20 nových questů → celkem 59 (IDs 50–69); typy 🛡 Escort (4), 🎯 Lov/Hunt (5), 💰 Odměna/Bounty (5), fill (6); pouze config/quests.json |
| 2026-03-06 | [5.9] Seasonal storyline framing: SEASON_THEMES (8 sezón) v game/season.py; theme_name+theme_lore na Season modelu+to_dict(); 0025 migrace; renderSeasonBanner() s theme name+lore; .season-theme-name/.season-theme-lore CSS; backfill existujících sezón |
| 2026-03-06 | [5.10] Season recap screen: recap_shown na SeasonResult; 0026 migrace; GET /arena/season/recap (rank+ELO vývoj+W/L+top opponent+cosmetics) + POST /arena/season/recap/dismiss; showSeasonRecap() modal s SVG line chart; _maybeShowSeasonRecap() trigger v loadArena(); CSS .season-recap-overlay/.season-recap-modal |
| 2026-03-06 | [5.7] Dungeon branching: DungeonRun.secret_path_offered+taken; next_stage 2-fázový roll (40%/70%); _SECRET_ENEMY_MULT=1.6 / _SECRET_REWARD_MULT=2.0; cursed_grounds secret_path_chance=0.70; dialog JS+CSS overlay; stage progress badge; 0023 migrace |
| 2026-03-07 | [6.1] PostgreSQL + Redis migrace: core/cache.py (_InMemoryCache + _RedisCache, graceful fallback), REDIS_URL v config.py, rate_limit.py Redis sorted-set sliding window + in-memory fallback, leaderboard cache (arena 60s, season_lb 60s, boss 30s, character 60s) + invalidace po útocích, alembic/env.py podmíněný render_as_batch (jen SQLite), requirements.txt redis==5.2.1, .env.example; verze 0.7.0; 244 testů OK |
| 2026-03-07 | [6.2] Content Management API: POST /admin/quest/create (quests.json hot reload), POST /admin/config/reload, POST /admin/world-event/schedule (vlastní event), GET/admin/crystal-shop-items, GET/POST/DELETE /admin/crystal-sale(s), ScheduledCrystalSale model + 0028 migrace; crystals.py aplikuje slevy v shop+buy; admin.html Content tab (quest form + crystal sales form + seznam) + World Events vlastní form; 244 testů OK |
| 2026-03-07 | [6.3] A/B testing framework: experiment_group (0–9) na Character (0029 migrace); models/experiment.py (Experiment model + OVERRIDABLE_PARAMS); game/experiments.py (get_experiment_overrides + 10s cache + apply_overrides_to_engine/router); combat_engine: experiment_overrides v CombatantConfig → _FighterState (crit_damage_mult, dodge_chance_cap, ability_damage_mult); quest.py + arena.py: načítání overrides + xp_reward_mult + gold_reward_win; admin.py: CRUD + toggle + delete + GET /admin/experiments/analytics (metriky per skupina); admin.html: 🧪 Experimenty tab (formulář + seznam + analytics tabulka); 244 testů OK |
| 2026-03-08 | [6.4] GDPR account management: 0030 migrace (is_deleted+deleted_at+anonymized na users); models/user.py rozšíření; routers/account.py (GET /account/status, GET /account/export JSON dump char+inventory+gold+crystal+arena+achievements, POST /account/delete soft delete 30d retention, POST /account/delete/cancel, POST /account/anonymize email+appearance reset); main.py router registrace; account.js (loadAccount, accountExport stažení JSON, accountRequestDelete, accountCancelDelete, accountAnonymize); game.html Account page + nav tlačítko + script tag; acc-* CSS v theme.css; 244 testů OK |
| 2026-03-08 | [6.5] Crystal economy audit & balance: achievement chain rewards zvýšeny (2-3→15-25 💎, celkem 90 max); guild war výhry +25 💎 každému členovi vítězného cechu; login streak systém (7d: +20💎, 30d: +50💎, last_login_date+login_streak na Character); 0031 migrace; GET /admin/crystals/analytics (earned/spent/breakdown/top earneři+spenderé/denní 14d); crystals.py bugfix (now před použitím); crystals.js login streak widget + aktualizované earning sources; admin.html 💎 Crystaly tab; 244 testů OK |
| 2026-03-08 | [6.6] Ethical monetization declaration + in-game transparency: GET /crystals/transparency (drop rates z loot.py, crystal sources, shop ceny, design commitments, herní mechaniky); support.js (hero banner, 6 design závazků, crystal sources+shop ceny 2-panel, drop rate tabulky s vizuálními bary, mechanics přehled); nav "💚 Podpora hry" v Kosmetika skupině; page-support; sup-* CSS v theme.css; PAGE_TIPS doplněn; 244 testů OK |
| 2026-03-08 | [6.7] Advanced analytics dashboard: GET /admin/analytics/advanced (funnel 5 kroků, class vs class matchup matrix aliased Character joins, DAU 14d z GoldTransaction distinct, economy health: velocity/sink ratio/trend/Gini); loadAdvancedAnalytics() + _renderMatchupMatrix() v admin.html (funnel bary s drop-off %, DAU mini bary, economy health karty, 3×3 matchup matrix s color coding); tab button + auto-load; 244 testů OK |
| 2026-03-08 | [6.8] In-game news feed: GameNews model (title/body/news_type/expires_at/is_active/author); 0032 migrace; GET /news/current (aktivní, ≤14 dní, před expirací); admin CRUD (GET/POST/PUT/DELETE /admin/news); news.js (loadNewsFeed, dismissNews, localStorage dc_dismissed_news); #hub-news-feed div v game.html; 5 news_type variant CSS (info/event/maintenance/balance/hotfix); 📰 Novinky tab v admin.html; 244 testů OK |
| 2026-03-04 | [5.3] Veřejné hráčské profily: GET /character/profile/{name} (jméno, třída, level, subclass, prestige, arena stats, 5 posledních zápasů, achievements count, combat stats, appearance); profile.js (showPlayerProfile modal + renderProfileModal + Compare feature); modal-profile v game.html; CSS .profile-* + .compare-* v theme.css; klikatelná jména v arena.js (opponents/history/leaderboard) + guild.js (member list + war opponents) |
| 2026-02-28 | [4.1] Grouped sidebar navigation — 5 collapsible skupin (⚔️ Boj / 🎯 Postava / 👥 Sociální / 🌟 Sezónní / 🎨 Kosmetika); localStorage state; auto-expand při navigaci; group badge pro stat points; game.html + layout.css + ui.js |
| 2026-02-28 | [4.2] Hub contextual dashboard — GET /character/hub-summary (quest+arena+dungeon+season+guild_weekly+world_event+next_action); hub-summary-strip s barevnými chipy; next-action widget; hub.js refactor (1 request místo 4); theme.css; character.py |
| 2026-02-28 | [4.3] Combat Build stránka — nový build.js (strategie+radar SVG+talent strom+subclass karta+eff stats+dungeon mod+shrnutí); nav tlačítko v Boj skupině; theme.css 70+ nových pravidel; ui.js update; game.html |
| 2026-02-28 | [4.4] Combat Insights — analyzeCombatEvents()+_generateCombatTip()+showCombatInsights() v combat-anim.js; CSS .ci-panel v theme.css; napojení v arena.js (po výsledku)+quest.js (po collect)+dungeon.js (po stage); frontend-only analýza structured events |
| 2026-02-28 | [4.5] Onboarding flow — 6-step guided tour; onboarding.js (startOnboarding/closeOnboarding/_obNext); Character.onboarding_completed flag; 0019 migrace (+ arena_gold_today/date); POST /character/complete-onboarding; character.js+main.js napojení; CSS .ob-card/.ob-highlight-target; game.html script tag |
| 2026-02-28 | [4.6] Feature tooltips — PAGE_TIPS dict (20 stránek)+showFeatureTip(pageId,text) v ui.js; volání z showPage() (skip overview); localStorage dc_seen_tips; auto-zmizí 7s; CSS .feature-tip+.ft-close animace |
| 2026-02-28 | [4.7] Arena gold daily cap — ARENA_DAILY_GOLD_CAP=500; arena_gold_today+arena_gold_date na Character (migrace 0019 již); _reset_arena_gold_if_new_day(); cap logika v attack endpoint; arena_gold_today+daily_cap v /opponents i /attack response; JS: denní limit progress bar v renderArenaStats; cap-reached badge ve výsledku; CSS .arena-gold-cap-card+.arena-cap-track |
| 2026-02-28 | [4.8] Prestige soft cap — PRESTIGE_POWER_CAP=10 v prestige.py; prestige_bonus_mult() cappuje na 10; PRESTIGE_FRAME_REWARDS (10 unikátních framu); prestige_frame_key(); prestige_portrait_frame na Character + to_dict(); migrace 0020; prestige_ascend uděluje frame, post-cap zpráva; prestige_info vrací is_power_capped+upcoming_frame; ui.js priorita season>prestige>crystal; prestige.js cap banner+nextBonuses+frame reward; CSS 10 pf-prestige-N framu+animace |
| 2026-02-28 | [4.9] Responsive layout — @media(max-width:768px): layout single-col, lpanel hidden, rpanel jako mob-open overlay; mob-tabbar (5 nav skupin + Aktivita tab) fixed bottom; mob-drawer slides up s klonovanými nav-btn; mob-backdrop; _initMobileUI()+openMobileDrawer()+openMobileActivity()+closeMobileDrawer() v ui.js; showPage() autoclose drawer; cr-combatants vertical na mobilu; layout.css + ui.js |
| 2026-02-28 | [4.10] Visual hierarchy refactor — mannequin grid layout (5 řádků, grid-areas kolem portrétu); eq-mslot-* CSS třídy; HP dominantní (1.7rem), MP subdued (1.15rem); sp-cg-primary (ATK/DEF/SPD 1.6rem) vs sp-cg-secondary (Krit/Dodge 0.9rem, opacity 0.78); responsive fallback ≤560px; equipment.js + theme.css |
| 2026-02-28 | [4.11] Stat allocation visual feedback — .stat-alloc-float (fixed, animace nahoru 0.7s); @keyframes stat-float-up; .stat-flash (@keyframes stat-flash-green 0.65s glow); .sp-attr-cap-warn (⚠ zone2>50, ⚠⚠ zone3>150); id="sp-attr-${key}" na kartách; allocStat(stat, ev) s btn.getBoundingClientRect(); components.css + equipment.js + character.js |
| 2026-02-28 | [BUG] mob-drawer fix — přidáno display:none do .mob-drawer (desktop), display:block do @media(≤768px); layout.css |
| 2026-02-28 | [UX] Equipment redesign — 2-pane grid (#page-equipment: 1fr 320px); .equip-char-card (portrait 76px+info vpravo); .equip-slots-grid (2-col grid, boots full-width); stat-panel sticky; removals: mannequin grid, eq-mslot grid-areas, equip-center; renderEquip() restrukturalizovaný; theme.css + equipment.js |

---

---

# 🔬 ARCHITEKTONICKÁ ANALÝZA — Senior Review
## Dungeon Chronicles: Holistické hodnocení stavu projektu
*Datum: 2026-02-28 | Autor: Senior Architect Review*

---

## 📐 Stav backendu

### Silné stránky
- **Unified combat engine** (1 320 řádků) je výborné architektonické rozhodnutí — jeden engine pro PvP, PvE, Boss a Dungeon eliminuje duplicitní logiku a je testovatelný jako celek
- **Transakční bezpečnost** je konzistentní: SELECT FOR UPDATE na World Boss HP, try/except + rollback v dungeon, CronJob distributed lock pro background tasky
- **Economy audit log** (GoldTransaction) je správná praxe pro live service — umožní post-hoc analýzu inflace
- **Data-driven obsah** (config/*.json) umožňuje přidávat questy a dungeony bez deploye
- **Structured JSON logging** + RequestId = dobrý základ pro observabilitu
- **Alembic migrace** jsou idempotentní — bezpečné pro produkci

### Architektonická rizika

**RIZIKO 1 — `recalculate_stats()` jako god funkce** *(vysoké)*
`Character.recalculate_stats()` aplikuje v jednom průchodu: base stats dle třídy, level bonusy, equipment bonusy, buff systém, talent bonusy, prestige bonusy, subclass multiplery. Každý nový systém musí hacknout do této metody. Přidáš-li Tier 2 talenty, set bonusy nebo nový buff typ, míra selhání pro stávající testy roste nelineárně. **Řešení:** Zavést pipeline architekturu — `StatPipeline` s explicitními kroky, kde každý systém registruje svůj `StatModifier`.

**RIZIKO 2 — 32 routerů s inline importy** *(střední)*
`arena.py` importuje `from routers.weekly_quest import increment_weekly_board` přímo uvnitř endpoint funkce. Stejný vzor v `quest.py` pro diviner, gambler, fateweaver. Toto je skrytý coupling — přejmenování jakéhokoliv z těchto routerů rozbije ostatní. **Řešení:** Event bus pattern — routery emitují události (`QuestCompleted`, `ArenaWin`), ostatní systémy se přihlásí jako listenery.

**RIZIKO 3 — SQLite jako bottleneck** *(kritické pro škálování)*
SQLite zvládne read-heavy workloady, ale jakýkoliv concurrent write (boss HP, arena ELO, guild chat) způsobí lock contention při >20 souběžných uživatelích. SELECT FOR UPDATE na SQLite je méně robustní než na PostgreSQL. Migrace [2.1] musí být prioritou před jakýmkoliv veřejným launchem.

**RIZIKO 4 — 7 profesí jako ghost systémy** *(střední)*
Runosmith, Diviner, Soulforger, Gambler, Agent, FateWeaver — každá profese hookuí do quest/arena/dungeon dokončení. Nicméně pokud má hra 10-50 aktivních hráčů, tyto systémy budou prakticky neviditelné. Každý přidává kognitivní load bez proporcionálního value. **Doporučení:** Konsolidovat 4-5 profesí do 2-3 s hlubokou mechanikou místo 7 s mělkou.

**RIZIKO 5 — Absence API verzování** *(nízké nyní, vysoké po launchin)*
Veškeré API je bez verzování (`/arena/attack` místo `/v1/arena/attack`). Jakákoliv breaking change v response struktuře rozbije všechny klienty najednou. Přidání `X-API-Version` headeru nebo URL prefix je nutné před veřejným launchem.

---

## ⚔️ Combat: Hloubka a balance

### Silné stránky
- Soft caps (zóny 50/150/∞) zabraňují hyperinflaci
- 8 status efektů s interaction matrix (bleed+weaken = vulnerability atd.)
- 4 strategie s reálným dopadem na combat outcome
- Boss fáze s trigger na % HP
- MP-cost jako % z mp_max — správné škálování s levelem

### Balancovací rizika

**Hunter's Mark (+75% damage na první útok) je pravděpodobně broken v PvP.** Sharpshooter Ranger s Eagle Eye (+8 LUCK → +8% crit) a Hunter's Mark na prvním kole může way too consistently one-shot nízko-HP třídy jako Mage. Nutný audit dat po prvních sezónách.

**ABILITY_TRIGGER_PROB = 0.40 vytváří variance hell.** Ve 30-kolovém souboji to znamená, že ability se spustí průměrně 12×, ale variance je ±4. Dva identicky stavbovaní hráči mohou mít wildly different výsledky. Pro async RPG je to přijatelné, ale frustrating pro hráče kteří chtějí prediktabilní výsledky. Zvažit snížení na 0.30 a přidat mechanic "guaranteed ability on round 3".

**Guardian subclass (DEF×1.35 + HP×1.20) + defensive strategy + Iron Skin talent (-20% dmg)** = potenciálně unkillable tanky v aréně. Nemá-li Mage burst damage dostačující k proražení tohoto combina, metagame se zúží na "hraj Guardianu nebo prohraj."

**30-kolový cap bez tiebreakeru.** Při draw (oba přežijí) není jasné kdo "vyhrál" — ELO změna, gold, XP? Ujistit se že draw má konzistentní chování ve všech combat kontextech.

---

## 💰 Economy: Stabilita

### Silné stránky
- Listing fee (5%) jako gold sink při každé marketplace transakci
- Durability repair jako recurring náklad
- Upgrade systém (500 / 2 000 / 8 000 G) jako velký gold sink
- Level-scaled quest rewards zabraňují triviálnímu farmení na high levelu
- Crystal shop odděluje kosmetiku od power (správné etické rozhodnutí)

### Ekonomická rizika

**INFLACE z arény je nevázaná.** 5 minut cooldown = 12 bojů/hodinu = minimum 600 G/hodinu (při 50G za výhru). S win rate 60% je reálný příjem ~450 G/h. Za 20 hodin farmění má hráč peníze na max upgrade libovolného slotu. Chybí denní cap na arena gold rewards nebo scaling fee za časté boje.

**Marketplace má deflační tlak na nízké itemy.** Bez NPC floor pricing může common item prodávat za 1 G (nebo vůbec ne) protože supply převyšuje demand. Hráči budou preferovat sell-to-NPC pro convenience. Real player economy vznikne jen u rare+ itemů.

**Prestige bonusy jsou uncapped.** +3% ATK/DEF/HP a +2% MP za každý prestige level bez horní hranice. Pokud hráč dosáhne prestige 10, má +30% na všechny stats — bez soft capu to obchází existující soft cap systém. Nutný hard cap na prestige level nebo klesající returns.

**Crystal economy může být nerovnováhová.** Crystaly se vydělávají z achievementů a sezónního passu, ale není jasné zda je možné earned crystaly realisticky dosáhnout pro smysluplné purchases bez grind zdi.

---

## 📈 Progression: Systémy

### Silné stránky
- XP curve (`100 * n^1.8`) je dobře zvolená — exponenciální bez být prohibitivní
- Daily/weekly/seasonal questy vytvářejí přirozené re-engagement smyčky
- Talent tier 1 (level 10/20/30) dává konkrétní milníky k těšení se na
- Subclass jako trvalá irreverzibilní volba dává weight k rozhodnutí

### Progression rizika

**Level 1-9 je progression void.** Žádné talenty, žádný subclass, žádná specializace. Hráč dělá questy a alokuje stat body bez výraznějšího identity building. Prvních 9 levelů by mělo být kratší (snížit XP requirements) nebo obsahově bohatší.

**7 profesí jako discovery problém.** Nový hráč nemá žádné vodítko že Professions existují, jak se odemykají, a proč by mu mělo záležet. Professions systém je pravděpodobně nejméně discoverabilní feature v celém projektu.

**Attunement chains jsou mystery.** Bez in-game průvodce nebo vizualizace chain progressu je obtížné vědět: co je attunement, jaké jsou chains, kde začít. Systém existuje ale možná ho nikdo nepoužívá.

**Season Pass (free track) nemá dostatečnou HODNOTU PREVIEW.** Hráč musí aktivně navštívit Season Pass stránku aby viděl co na něj čeká. Chybí "tease" na hlavní obrazovce — "Dokončením 3 questů dnes odemkneš..."

---

## 👥 Sociální systémy

### Silné stránky
- Guild WebSocket chat je real-time a funkční
- Guild Wars (async) umožňují kompetici bez časové synchronizace
- Arena leaderboard s ELO dává smysl pro rankingovou kompetici
- Marketplace je player-driven economy

### Sociální rizika

**Žádné veřejné hráčské profily.** Nelze zobrazit build, equipmment ani stats jiného hráče. To je zásadní missing feature pro sociální hru — sdílení buildů, srovnávání, inspirace jsou základní sociální mechaniky.

**Guild systém postrádá hloubku mimo chat a weekly quest.** Guild nemá vlastní identitu (banner, lore, specialization), žádné sdílené cíle nad rámec weekly questu, žádnou progresivní guild-level mechanic. Hráči jsou v guildě "protože existuje", ne protože jim to dává strategickou hodnotu.

**World Boss je cooperative but anonymní.** Hráči přispívají k shared HP pool ale neexistuje real-time contribution tracker ani "kdo dal nejvíce dnes" mini-leaderboard. Spolupráce je invisibilní, což snižuje engagement.

**Neexistuje friends systém ani player lookup.** Nemůžeš vyhledat konkrétního hráče, zobrazit jeho profil, nebo ho sledovat. V multi-player hře je to zásadní absence.

---

## 🖥️ UI/UX: Kvalita a konzistence

### Silné stránky
- Konzistentní dark theme s dobře definovanými CSS variables
- Toast systém je funkční a neobtruzivní
- Combat replay animace přidává spectacle
- Loading + empty states jsou implementované
- Portrait frame animace jsou vizuálně výrazné

### UX rizika — Information Hierarchy

**18 navigačních tlačítek v levém panelu je cognitive overload.** Sidebar obsahuje: Overview, Questy, Equipment, Inventář, Obchod, Trh, Aréna, Dungeon, Boss, Cechy, Achievementy, Profese, Frakce, Attunement, Prestiž, Season Pass, World Events, Crystaly, Subclass, Transmog. To je 20 položek bez jakékoliv skupinové logiky. Hráč nemá mentální mapu jak navigovat.

**Všechny systémy mají stejnou vizuální váhu.** "Questy" a "Transmog" jsou zobrazeny identicky v navigaci navzdory dramaticky rozdílné důležitosti. Primární gameplay smyčka (quest → combat → equipment) by měla být vizuálně dominantní.

**Talents + Subclass + Strategy + Dungeon Modifiers = 4 vrstvené "build" systémy bez unified view.** Hráč nemá žádné místo kde vidí: "Takhle vypadá můj kompletní combat build." Equipment page zobrazuje stats, Talents tab zobrazuje pasives, ale jejich interakce není vizualizována.

**Combat result screen neposkytuje výukový moment.** Po souboji hráč vidí výsledek (win/loss, ELO, gold), ale ne "proč." Která schopnost rozhodla? Který status efekt byl klíčový? Tato data jsou ve structured events ale frontend je nevyužívá pro educational feedback.

**Topbar je information-dense ale nedostupný.** HP/MP/XP bary, gold, quest chip, arena chip, refresh — všechno na 50px. Na menším monitoru nebo při zvětšení fontu se začíná překrývat.

### UX rizika — Cognitive Load

**Professions (7) + Attunements + Season Pass + Arena Season + World Events + Daily Quests + Weekly Quests + Crystal Shop** = hráč mid-game žongluje 8+ parallel progression tracks bez jasné priority. Každý track má svůj vlastní timer, svou vlastní měnu (gold, crystaly, guild XP, attunement progress, season XP...), svůj vlastní reset cyklus.

**First-time user experience neexistuje.** Nový hráč vytvoří postavu a ocitne se na Hub stránce s 20 navigačními položkami a žádnou nápovědou co dělat jako první.

**Čitelnost combat logu.** Text-based combat log (pro lidi kteří si ho otevřou) je raw string dump. Structured events existují, ale UI pro jejich čtení není pedagogické.

---

## ⚖️ Over-engineered vs. Under-developed

### Over-engineered (zjednodušit nebo sloučit)

**7 profesí jsou 5 profesí příliš.** Každá profese je independently implementovaná s vlastním modelem, routerem, JS souborem a hook points ve všech ostatních systémech. Výsledek: velká surface area kódu, malý přínos pro hráče který si vybral jednu profesi a ostatní ignoruje. Ekonomika pozornosti je nulová — hráč si vybere profesi jednou a pak ji pasivně zapomene.

**Diviner (prophecy) + Gambler (bets) + FateWeaver (bonds) jsou tři podobné systémy.** Každý z nich interceptuje quest completion a modifikuje outcome. Jsou thematicky zajímavé ale mechanicky skoro identické (trigger → podmínka → reward/penalty). Mohly by být jedním systémem "NPC Events" s různými flavour texts.

**Tři překrývající se kosmetické systémy.** Crystal portrait frames + season portrait frames + transmog slots — každý s jiným model souborech, jinými endpoint naming conventions, jiným claim flow. Z perspektivy hráče všechny modifikují "jak vypadám" ale bez jednotného "cosmetic wardrobe" UI.

### Under-developed (potřebuje hloubku)

**Quest pool.** Data-driven systém existuje, ale pokud je v poolu 15-20 questů, hráč je projde za týden a daily rotation se stane opakující se. Obsah (questy) je kriticky pod-investovaný oproti systémům které ho doručují.

**Item pool.** Upgrade systém Common→Legendary existuje, ale pokud je item pool malý, hráči rychle optimalizují jeden "best in slot" build pro každý slot a přestanou experimentovat.

**Tutorial / onboarding.** Nulová investice. První dojmy jsou nejdůležitější pro retention.

**Dungeon variety.** 5 stagů, fixed structure. Dungeon modifiers (12 rotating) přidávají variance, ale základní flow se nikdy nemění — enter, fight, fight, fight, fight, collect. Chybí environmental storytelling, branching paths, nebo secret stages.

**Player profiles.** Neexistují. Pro sociální hru je to nejnákladnější absence.

---

## 🚫 CO NESTAVĚT DÁLE (a proč)

### ❌ Real-time PvP
Async combat je výhoda, ne limitace. Real-time PvP vyžaduje: WebSocket session management, matchmaking queue, timeout handling, connection recovery, anti-cheat pro rychlé inputs. S <100 concurrent hráči by wait times v matchmaking byly prohibitivní. Async "attack when you want" je lepší UX pro cílovou skupinu.

### ❌ Crafting systém (gather materials → craft items)
Existuje upgrade systém (Common→Legendary), marketplace (player economy) a Crystal shop (cosmetics). Přidání resource gathering + crafting recipes přidá další progression track bez řešení skutečného problému (malý item pool). Pokud chceš větší item variety, přidej více položek do item JSONu — nekomplikuj flow.

### ❌ 4. třída (Druid, Paladin, atd.)
Přidáním nové třídy neopravíš balance problémy u existujících 3. Guardian subclass potenciálně dominuje PvP. Mage má nevýhodu v dlouhých soubojích. Ranger's Hunter's Mark je pravděpodobně OP. Tyto problémy musí být vyřešeny PŘED přidáváním nové třídy, jinak nová třída přidá do neurovnáhovaného systému další layer.

### ❌ Raids (group PvE, 3-6 hráčů)
Raidy vyžadují synchronizaci hráčů — společný čas, společná strategie, role-based combat (tank/healer/DPS). Dungeon Chronicles nemá žádnou z těchto mechanic. Bez real-time systémů jsou raids nemožné. Bez silné guild community jsou organizačně neproveditelné.

### ❌ Přidávat další profese
7 je příliš mnoho. Každá přidaná profese ředí pozornost hráče a přidává maintenance kód. Místo nové profese: prohloubni existující nebo sloučí 7 do 3.

### ❌ Housing / player spaces
Dekorování virtuálního prostoru nepropojuje s žádnou existující progression smyčkou. Je to content sink bez gameplay substance v kontextu tohoto projektu.

---

---

## 🔵 FÁZE 4 — Product Polish & UX Cohesion
*Strategický cíl: Přeměnit feature-complete hru na playable hru. Každý nový hráč musí pochopit co dělat a proč to dělá — bez external guidance. Snížit kognitivní zátěž, zvýšit discoverability, unifikovat mentální model.*

### 4A — Navigation & Information Architecture

- [x] **[4.1]** Grouped sidebar navigation (5 kategorií)
  - Sloučit 20 navigačních položek do 5 collapsible skupin: ⚔️ Combat · 🎯 Progression · 👥 Social · 🌟 Seasonal · 🎨 Cosmetics
  - Každá skupina: ikonka + název + indikátor nových notifikací uvnitř
  - Aktivní item skupiny: skupina zůstává expandovaná
  - Uložit stav do localStorage
  - Backend: žádná změna — čistě frontend refactor
  - Soubory: `frontend/css/layout.css`, `frontend/js/ui.js`, `game.html`

- [x] **[4.2]** Hub redesign — contextual dashboard
  - Hub přestane být statický grid budov a stane se dynamickým dashboardem
  - Zobrazí: aktuální denní quest progress (X/3 hotové), arena rank + percentil, season pass aktuální tier, dungeon cooldown, guild weekly quest progress, world event contribution
  - "Next action" widget: AI-picked doporučení co dělat dál ("Máš nevyzvednutý quest", "Arena cooldown skončil")
  - Backend: GET /character/hub-summary endpoint agregující data z více tabulek
  - Soubory: `frontend/js/hub.js`, `backend/routers/character.py`

### 4B — Combat Clarity & Build View

- [x] **[4.3]** Unified "Combat Build" stránka
  - Jedna stránka zobrazující: zvolená strategie + subclass stats + talent bonusy + effective stats (s soft cap overlay) + aktivní dungeon modifier + set bonusy pokud jsou
  - Vizualizace: strom talentů s ikonami (ne jen textový seznam), subclass card s porovnáním oproti base class, strategy radar chart (5 os: ATK/DEF/SPD/MP/LUCK)
  - "What this means in combat" — plain-language překlad: "Tvůj Berserker s Battle Rage a Aggro strategií způsobí průměrně X poškození za kolo ale umře dříve než Guardian"
  - Backend: žádná nová data — kombinace stávajících endpoints
  - Soubory: nový `frontend/js/build.js`, `frontend/css/theme.css`

- [x] **[4.4]** Combat result educational feedback
  - Po každém souboji (quest, arena, dungeon) zobrazit "Combat Insights" panel
  - Zvýraznit: kolo které rozhodlo výsledek, která ability přidala nejvíce damage, zda byl aktivní status efekt klíčový
  - "Tip": kontextuální rada na základě výsledku ("Tvůj Guardian by získal z Defensive strategy, protože ...")
  - Backend: endpoint `/combat/analyze/{match_id}` post-hoc analýza structured events
  - Soubory: `frontend/js/combat-anim.js`, `backend/routers/arena.py`

### 4C — Onboarding & Discoverability

- [x] **[4.5]** First-time user onboarding flow
  - Po vytvoření postavy: 6-step guided tour (dismissable modal sequence)
  - Krok 1: "Vítej — tady je tvůj quest log" (šipka na Quest nav item)
  - Krok 2: "Splň první quest a vrať se"
  - Krok 3: Equipment page — "Tady equip to co jsi dostal"
  - Krok 4: Arena — "Zkus první PvP boj"
  - Krok 5: Guild — "Přidej se k cechu pro bonusy"
  - Krok 6: "Vše ostatní najdeš v navigaci — prozkoumej!"
  - Backend: `onboarding_completed` flag na Character (boolean, 0019 migrace)
  - Soubory: `frontend/js/main.js`, nový `frontend/js/onboarding.js`

- [x] **[4.6]** Feature discovery tooltips systém
  - Při prvním otevření každé stránky: jednorázový "co je tato stránka" tooltip
  - Stored v localStorage: `dc_seen_tips = {"arena":true, "dungeon":true, ...}`
  - Každý tooltip: max 2 věty + dismiss button
  - Žádný backend needed
  - Soubory: `frontend/js/ui.js` (nová funkce `showFeatureTip(pageId, text)`)

### 4D — Economy & Balance Audit

- [x] **[4.7]** Arena gold daily cap
  - Max 500 G za den z arénových zápasů (win reward se sníží na 0 po dosažení denního cap)
  - Cap viditelný v arena UI: "Denní limit: 340/500 G"
  - Backend: `arena_gold_today` + `arena_gold_date` na Character; reset na 00:00 UTC
  - Soubory: `backend/routers/arena.py`, `backend/models/character.py`, 0019 migrace

- [x] **[4.8]** Prestige soft cap
  - Prestige level cap na 10 (maximální +30% ATK/DEF/HP, +20% MP)
  - Nad level 10: každý prestige přidá pouze kosmetické odměny (nové Prestige titles, unique portrait frame per level)
  - Tím se zabrání nekonečné power escalaci
  - Soubory: `backend/routers/prestige.py`, `backend/models/prestige.py`, 0019 migrace

### 4E — UI Scale & Visual Consistency

- [x] **[4.9]** Responsive layout — mobile breakpoint
  - `@media (max-width: 768px)`: single-column layout, hamburger nav, topbar zjednodušen
  - Left panel se schovají — navigation přejde do bottom tab bar (5 skupin z [4.1])
  - Right panel (activity log) přejde do collapsible drawer
  - Combat replay funguje vertikálně
  - Soubory: `frontend/css/layout.css`, `frontend/css/base.css`

- [x] **[4.10]** Visual hierarchy refactor pro Equipment/Stats stránku
  - Primary stats (ATK, DEF, HP, SPD) vizuálně dominantní — větší, barevné
  - Secondary stats (LUCK, MP) menší, subdued
  - "In combat (after soft cap)" hodnoty zobrazeny jako subtle annotation, ne jako primární číslo
  - Equipment sloty reorganizovány: mannequin layout místo flat listu
  - Soubory: `frontend/js/equipment.js`, `frontend/css/theme.css`

### 4F — Microinteractions & Feedback Loops

- [x] **[4.11]** Stat allocation visual feedback
  - Při alokování stat pointu: animovaný "+1" number floats up z tlačítka
  - Affected stats v stat panelu flash highlight (zelený glow po dobu 0.6s)
  - "Stat cap warning": jestli allocated stat přesáhne soft cap zona, zobrazit subtle žlutý warning icon
  - Soubory: `frontend/js/character.js`, `frontend/css/components.css`

- [x] **[4.12]** Gold/XP reward animations
  - Při příjmu goldu/XP (quest collect, arena win): coins/stars particle animation v topbaru
  - Counter animace: gold counter v topbaru animovaně "čítá" do nové hodnoty (300ms tween)
  - Level up: full-screen momentary flash + character portrait "glows" na 2s
  - Soubory: `frontend/js/ui.js`, `frontend/css/components.css`

**📊 Měřitelné success metriky pro Fázi 4:**
- Průměrný počet kliků k dosažení libovolné core feature: ≤ 3 (z huba)
- Nový hráč dokončí první quest bez external dokumentace: 90% completion rate
- Session time: nárůst o ≥ 20% oproti baseline (měřit z analytics)
- Bounce rate (odchod před prvním questem): pokles o ≥ 30%
- Mobile hráči: ≥ 15% session share do 60 dní

---

## 🟣 FÁZE 5 — Systems Depth & Long-Term Retention
*Strategický cíl: Dát hráčům důvody se vracet po měsících, ne jen týdnech. Přeměnit "feature tourists" na "invested builders". Vytvořit content flywheel — každé nové content přidání zvyšuje hodnotu existujícího obsahu.*

### 5A — Talent Tree Tier 2 (Active Abilities)

- [x] **[5.1]** Talent Tree Tier 2 — aktivní schopnosti (level 25/35/45)
  - Tier 1 jsou pasivní bonusy. Tier 2 jsou aktivní taktické volby použitelné v combat strategii
  - Mechanika: hráč si vybere JEDNU Tier 2 schopnost z 3 možností pro svou třídu (irreverzibilní jako subclass)
  - Warrior Tier 2: **Cyclone Strike** (multi-hit všechny) | **Rallying Cry** (self-regen + shield) | **Execute** (bonus dmg pod 25% HP)
  - Mage Tier 2: **Arcane Storm** (3 menší hits, pierce) | **Mana Void** (drains enemy MP) | **Time Warp** (extra kolo)
  - Ranger Tier 2: **Rain of Arrows** (multi-hit, bleeding) | **Shadow Step** (dodge + counter) | **Mark for Death** (permanent -DEF debuff)
  - Tier 2 schopnosti mají cooldown (každé 4 kola místo ABILITY_TRIGGER_PROB)
  - Backend: `talent_t2_key` na Character; rozšíření combat_engine; nový choosable mechanizmus
  - Soubory: `backend/game/talents.py`, `backend/game/combat_engine.py`, `backend/models/character.py`, migrace

- [x] **[5.2]** Set bonusy — implementace (`sets.py` model existuje, bonus není aktivní)
  - 3 základní sety: **Dragonscale Set** (warrior, 3pc: +15% HP, 5pc: Regen každé kolo), **Stormweave Set** (mage, 3pc: +20% ability dmg, 5pc: Spell Echo chance 50%), **Voidwalker Set** (ranger, 3pc: +12% LUCK, 5pc: First Strike vždy)
  - Set detekce v `recalculate_with_gear()` — zkontroluj počet set itemů v inventory equip slotů
  - Set bonus zobrazení v Equipment page: "2/5 Dragonscale — 3 more for set bonus"
  - Backend: `backend/game/set_bonuses.py` (nový), integrace do character router
  - Soubory: `backend/models/sets.py`, `backend/game/set_bonuses.py`, `backend/routers/character.py`

### 5B — Social Depth

- [x] **[5.3]** Veřejné hráčské profily
  - GET `/character/profile/{name}` endpoint — vrátí: jméno, třída, level, subclass, prestige, arena rank + history (win%, ELO), tituly, portrait frame, achievement count
  - **Nesdílí:** gold, inventory detail (bezpečnost / privacy)
  - Frontend: `frontend/js/profile.js` — modal dialog zobrazitelný odkudkoliv (z leaderboardu, arena opponents, guild member listu)
  - Součást: "Compare" feature — "Můj build vs jejich build" side-by-side stat srovnání
  - Migrace: žádná nová DB tabulka (existující data)

- [x] **[5.4]** Guild Hall progression (Guild Levels)
  - Guildy získávají XP z: guild wars (výhry), weekly quest completions, member arena wins
  - Guild Levels 1-10 s perky: Lv.2 chat history 100 zpráv, Lv.4 member cap 25, Lv.6 weekly quest bonusy +10%, Lv.8 second weekly quest slot, Lv.10 exclusive guild title pro všechny members
  - Guild Level viditelný na guild stránce jako progress bar + rank badge
  - Backend: `guild_level` + `guild_xp` na Guild model; `award_guild_xp()` helper hooknutý do war/weekly/arena
  - Migrace: 2 sloupce na guild tabulce

- [x] **[5.5]** World Boss real-time contribution tracker
  - GET `/boss/leaderboard` — top contributors za aktuální boss session (hourly reset)
  - Frontend: živě updatovaný mini-leaderboard na Boss stránce (polling každých 30s)
  - "Daily MVP": hráč s nejvyšší contribution za den dostane +100 G bonus reward
  - Cooperation je teď viditelná — motivace přispívat

### 5C — Content Depth

- [x] **[5.6]** Quest expansion — 40+ questů (z current ~15-20)
  - Přidáno 20 nových questů (IDs 50–69) → celkem 59 questů
  - Level distribuce: 1-10 (28 questů), 11-20 (18), 21-35 (10), 36-50 (3)
  - Nové typy: 🛡 **Escort** (50-53), 🎯 **Lov/Hunt** (54-58), 💰 **Odměna/Bounty** (59-63)
  - Ostatní fill questy (64-69) pokrývají mezery v level ranges
  - Pouze JSON — žádný backend kód

- [x] **[5.7]** Dungeon branching a secret stages
  - Stage 3 ze 5 má 40% šanci na "secret path" — obtížnější fight ale lepší loot
  - Backend: rozšíření `DungeonRun` o `secret_path` boolean; `enter_dungeon` random roll pro stage 3
  - Frontend: dungeon UI zobrazí "❓ Tajný průchod nalezen — riskuješ?" confirm dialog
  - Dungeon modifier "Cursed Depths" zvyšuje secret path šanci na 70%

- [x] **[5.8]** Achievement chains (progression paths)
  - Místo izolovaných achievementů: chains jako "Cesta Bojovníka" = 5 linked achievements, každý odemkne další
  - Chain completion reward: crystal + exclusive title
  - Vizualizace: achievement gallery stránka s chain progress vizy (podobně jako quest attunement chains)
  - Backend: `achievement_chain` model; `backend/game/achievements.py` rozšíření
  - Migrace: nová tabulka `achievement_chains`

### 5D — Season Narrative & LiveOps Foundation

- [x] **[5.9]** Seasonal storyline framing
  - Každá aréna sezóna dostane název a krátký lore blurb (2-3 věty)
  - Zobrazeno na arena banner + v season history
  - Sezóna 1: "Úsvit Gladiátorů" | Sezóna 2: "Krvavá luna" | atd.
  - Čistě content change — string v `Season` modelu (`theme_name`, `theme_lore`)
  - Migrace: 2 sloupce na `seasons`

- [x] **[5.10]** Season recap screen
  - Na začátku každé nové sezóny: animovaný "Recap" modal pro hráče kteří hráli předchozí
  - Zobrazí: tvůj final rank, ELO vývoj (line chart), W/L record, top opponent, earned cosmetics
  - Trigger: první login po start nové sezóny + `season_recap_shown` flag
  - Soubory: `frontend/js/arena.js`, migrace (1 boolean flag na SeasonResult)

- [x] **[5.11]** Profession konsolidace (7 → 3)
  - Sloučit 7 profesí do 3 hlubokých:
    - **Runist** = Runosmith + Soulforger (item enhancement + spirit binding)
    - **Oracle** = Diviner + FateWeaver (prophecy + fate bonds)
    - **Broker** = Gambler + Agent (risk/reward + contracts)
  - Každá konsolidovaná profese: 2 active abilities + 1 passive, znatelný dopad na gameplay
  - Migrace: zachovat existující data, přidat mapping old→new profession key
  - Toto je breaking change — nutný graceful migration pro existující hráče

**📊 Měřitelné success metriky pro Fázi 5:**
- DAU/MAU ratio ≥ 0.35 (aktivita alespoň každý 3. den)
- Guild membership rate: ≥ 60% hráčů v cechu
- Arena participation: ≥ 70% hráčů alespoň 1 zápas/týden
- Average sessions before churn: ≥ 30 (z 3-7 na současné odhadované)
- Content completion: průměrný hráč dokončí ≥ 25 různých questů před level 20

---

## ⬛ FÁZE 6 — LiveOps & Monetization Ethics Layer
*Strategický cíl: Vytvořit infrastrukturu pro hru která žije a vyvíjí se bez full developer deployment cycle pro každý update. Definovat udržitelný, eticky čistý monetization model. Postavit foundation pro měřitelný a opravitelný live service.*

### 6A — Backend LiveOps Infrastructure

- [x] **[6.1]** PostgreSQL + Redis migrace (deferred [2.1] + [2.2])
  - PostgreSQL: Změnit DATABASE_URL, otestovat všechny queries (pozor na SQLite-specific syntax)
  - Redis: Leaderboard cache (TTL 60s), cooldown tracking (dungeon, boss, arena daily cap), session invalidation
  - Redis nahradí in-memory achievement cache (2min TTL) — nyní cross-instance safe
  - Rate limiter: upgrade z in-memory counter na Redis sliding window (multi-instance správná)
  - Toto odblokovává horizontální škálování bez distributed lock workarounds
  - Soubory: `backend/database.py`, `backend/middleware/rate_limit.py`, `backend/core/cache.py` (nový)

- [x] **[6.2]** Content Management API (admin panel rozšíření)
  - Admin panel schopnost: vytvořit nový quest bez code deploy (form → JSON → config/quests.json hot reload)
  - Admin panel schopnost: naplánovat World Event (start time, end time, goal type, reward)
  - Admin panel schopnost: naplánovat timed sale v Crystal shopu
  - `config_loader.py`: přidat `reload_config()` endpoint pro live refresh bez restart
  - Backend: rozšíření `backend/routers/admin.py`

- [x] **[6.3]** A/B testing framework pro balance changes
  - Character dostane `experiment_group` (0-9 = 10 skupin, přiděleno při vytvoření náhodně)
  - Combat engine: přijme `experiment_overrides` dict — umožní testovat balance changes na podmnožině hráčů
  - Admin panel: definovat experiment (skupina → override hodnoty jako `ABILITY_TRIGGER_PROB`, `GOLD_REWARD_WIN`)
  - Analytics: srovnat key metrics per experiment group
  - Backend: nový `backend/models/experiment.py`, rozšíření analytics endpoint
  - Migrace: 1 sloupec na `characters`

- [x] **[6.4]** Player data export & account management (GDPR foundation)
  - GET `/account/export` — JSON dump všech dat hráče (character, inventory, transactions, arena history, achievements)
  - POST `/account/delete` — soft delete (flag `is_deleted`, data retention 30 dní pak hard delete)
  - POST `/account/anonymize` — anonymizuj jméno + appearance pro GDPR right-to-erasure
  - Frontend: Account settings stránka s těmito akcemi
  - Backend: nový `backend/routers/account.py`

### 6B — Monetization Ethics Layer

- [x] **[6.5]** Crystal economy audit & balance
  - Audit: kolik crystalů hráč vydělá za 30 dní aktivní hry? Kolik stojí všechny crystal shop items?
  - Target: hráč vydělá dost crystalů za 3-4 měsíce aktivity na koupi libovolné non-rotating položky
  - Přidat crystal earning z: guild wars (vítězství), achievement chains (completion), monthly login streak bonus
  - Admin dashboard: crystal flow analytics (earned vs spent, top spenders vs earners)
  - Zajistit: žádná crystal shop položka nesmí dávat combat advantage (power = never for sale)

- [x] **[6.6]** "Ethical monetization" declaration + in-game transparency
  - In-game "Support the Game" stránka (ne "Store" ani "Shop") — jasně kommunikuje co crystaly jsou a nejsou
  - Zobrazit: "Crystaly lze získat zdarma [X způsoby]. Platba urychlí kosmetiku, nikdy power."
  - Zobrazit: real probability rates pro jakýkoliv náhodný element (dungeon loot drop rates apod.)
  - Toto je záměrně anti-predatory design — buduje trust u hráčů

### 6C — Observability & Health Monitoring

- [x] **[6.7]** Advanced analytics dashboard rozšíření
  - Funnel analýza: Character created → First quest → First arena → Guild joined → Level 20 (kde se hráči ztrácejí)
  - Economy health: gold velocity (kolik G projde systémem za den), sink vs source ratio
  - Combat balance: win rate per class matchup (Warrior vs Mage, Mage vs Ranger, atd.) — detekce dominantního buildu
  - Session analysis: average session duration, sessions per day per user
  - Soubory: `backend/routers/admin.py`, `backend/admin.html`

- [x] **[6.8]** In-game news feed / patch notes systém
  - Admin může publikovat krátkou zprávu (100 znaků) viditelnou na Hub stránce
  - Model: `GameNews(id, title, body, published_at, expires_at)`
  - GET `/news/current` — aktuální aktivní zprávy (ne starší než 14 dní)
  - Frontend: banner na Hub stránce, dismissable per-news-item (localStorage)
  - Umožní komunikovat balance changes, eventy, maintenance okna přímo ve hře

- [x] **[6.9]** Automated balance alerts (admin monitoring)
  - Background job (denně) detekuje anomálie a zapíše alert do DB:
    - Win rate jedné třídy v arénách > 60%
    - Top 10 hráčů vlastní > 40% veškerého goldu v ekonomice
    - Daily arena gold farm > 3× expected cap (indikátor exploitu)
    - Season výsledky skewnuté (top 1 hráč má 5× více wins než top 2)
  - Admin dashboard: `⚠️ Alerts` tab zobrazující aktuální anomálie
  - Backend: `backend/tasks/balance_monitor.py`, `backend/models/balance_alert.py`

**📊 Měřitelné success metriky pro Fázi 6:**
- Mean time to detect balance anomály: ≤ 24 hodin (z "nikdy" na current)
- New content deployment time: ≤ 15 minut (nový quest bez code deploy)
- Crystal economy: ≥ 80% hráčů může získat alespoň 1 crystal item za 60 dní bez platby
- GDPR compliance: 100% zpracování export requestu do 24 hodin
- A/B test cycle: schopnost měřit a deployovat balance change do 7 dní od detekce problému

---

---

## 🔭 12-MĚSÍČNÍ VISION STATEMENT

### Co Dungeon Chronicles je a stává se

**Dungeon Chronicles je taktické async RPG pro hráče kteří chtějí hloubku bez grind diktátu.**

Není to MMORPG — nevyžaduje synchronizaci s ostatními hráči.
Není to idle game — každé rozhodnutí (build, strategie, ekonomika) má dopad.
Je to **"thinking person's RPG"** — hra kde si sednete na 15 minut, uděláte 3 chytrá rozhodnutí, a progress pokračuje asynchronně zatímco žijete svůj život.

### Cílový long-term hráč

**Primární persona:** 25-40 let, pracující profesionál. Hrál WoW nebo Path of Exile ale nemá čas. Chce hloubku theorycraftingu, komunitu, progression — ale v jeho tempu. Oceňuje transparentní systémy (soft caps, viditelné statistiky, žádné pay-to-win).

**Sekundární persona:** Hardcore RPG theorycrafter každého věku. Přijde pro build optimization, zůstane pro sezónní PvP metagame a guild wars.

### Co hru činí defensible a unikátní

1. **Server-authoritative async combat s transparentní matematikou.** Hráč MŮŽE vidět přesný výpočet každého souboje. Žádné black-boxy, žádné RNG bez vysvětlení. Důvěra je produkt.

2. **Etický monetization jako feature, ne omezení.** Crystaly jsou earnable. Žádná power za peníze. Toto je aktivně marketovatelné v prostředí plném predatory free-to-play.

3. **Depth through interaction, ne accumulation.** Hra není o farmaření X reource Y hodiny — je o správné kombinaci talentů, subclass, strategie a guild spolupráce. Hloubka plyne ze systémů které spolu interagují, ne ze sheer množství obsahu.

4. **Async social bez FOMO.** Arena funguje 24/7. Guild chat může počkat. World Boss má 6h okno. Žádná hra nevyžaduje tvoji přítomnost v konkrétní chvíli — ale vždy je proč se vrátit.

5. **Vývojář-hráčský vztah transparency.** In-game patch notes, A/B testy komunikované hráčům, crystal economy stats veřejně dostupné. Komunita vidí jak hra funguje a věří tvůrci.

### Aktuální největší hrozba

Největším rizikem není technický dluh ani balance — je to **content void**. Pokud je quest pool 15-20 questů, systémy jsou robustní ale prázdné. Hráč projde obsah za 2 týdny a nemá důvod se vrátit. **Fáze 4-6 musí paralelně investovat do content tvorby**, ne jen systémů.

### Prioritní pořadí (12 měsíců)

```
Měsíc 1-2  : Fáze 4 — UX polishing, onboarding, navigation refactor
Měsíc 2-3  : Fáze 6.1 — PostgreSQL + Redis (blocker pro scaling)
Měsíc 3-5  : Fáze 5 — Talent T2, set bonusy, profil hráče, quest expansion
Měsíc 4-6  : Content investment — 40+ questů, 20+ nových itemů, 2 nové dungeony
Měsíc 6-9  : Fáze 5 dokončení + Fáze 6 LiveOps infrastruktura
Měsíc 9-12 : First public soft launch + Fáze 6 monetization ethics layer
```

**Hra bude připravena na soft launch tehdy, kdy:**
- Nový hráč pochopí co dělat bez dokumentace (měřitelné playtestem)
- Backend běží na PostgreSQL (ne SQLite)
- Quest pool: ≥ 40 questů
- Session retention D7 ≥ 30% (7 dní po registraci stále hraje 30% hráčů)
- Monetization: jasně komunikované, etické, netoxické

---
*Analýza zpracována na základě kompletního code review, 2026-02-28*
*Autoři systémů jsou respektováni — tato analýza nepopírá dosažené, ale ukazuje kudy dál.*
