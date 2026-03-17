# Dungeon Chronicles — HC Gauntlet Roadplan
## Strategická roadmapa: Pivot na Hardcore Browser RPG

> **Identita hry po pivotu:**
> *"Jediný browser RPG kde riskuješ postavu — a celý svět ví, jak jsi zemřel."*

> **Cílový hráč:** Taktický + kompetitivní. Hráč který chce buildcraft, optimalizaci a prestiž z překonávání skutečného rizika.

> **Klíčová diferenciace od Shakes & Fidget:** S&F je casual persistent grinding. Dungeon Chronicles je HC-only — každá postava je příběh, každá smrt ho dokončí.

---

## 📍 AKTUÁLNÍ POZICE

```
Poslední session : 2026-03-12
Aktuální fáze    : PRE-PIVOT — design schválen, implementace nezačata
Roadplan verze   : 1.0
Předchozí práce  : Fáze 1–6 CHRONICLES_ROADPLAN.md ✅ (technická základna zachována)
```

---

## 🏗️ ARCHITEKTURA PIVOTU

### Co se zachovává
- Celý backend (FastAPI, modely, routery, combat engine)
- Systémy: questy, dungeony, aréna, cechy, economy, talenty, subclassy
- Alembic migrace (přidáváme nové, nerušíme staré)
- Frontend struktura (JS moduly, API vrstva)

### Co se mění
- Vizuální identita — kompletní CSS overhaul (Obsidian Codex)
- Game mode — pouze HC, žádný standard mode
- Smrt v dungeonu = permadeath postavy
- Nové systémy: Bloodline, Legacy Item, Hall of the Fallen, Living Ladder
- Třídy — asymetrická mechanická pravidla (Rage / Chain / First Strike)
- Combat — nový unikátní systém (viz Fáze G)

---

## 🎨 FÁZE A — Vizuální identita: Obsidian Codex

> **Cíl:** Hra musí vypadat jako komerční produkt, ne hobby projekt.
> Inspirace: Path of Exile, Hades, Elden Ring, Disco Elysium, Slay the Spire.
> Aesthetic: "Středověký grimoire vytesaný do vulkanického skla."

### A1 — CSS Design System

- [x] **[A.1]** Design system foundation
  - Nový soubor `frontend/css/design-system.css`
  - Kompletní CSS custom properties: paleta (void/obsidian/slate/stone/ash), akcenty (gold/blood/crimson/soul/poison/ember)
  - Font imports: Cinzel Decorative, Cinzel, IM Fell English, Josefin Sans, UnifrakturMaguntia
  - Spacing systém (--space-1 až --space-16)
  - Border/glow proměnné (--border-rune, --glow-gold, --glow-soul, --glow-blood)
  - Odstranit existující barevné proměnné z theme.css — přesunout do design-system.css

- [x] **[A.2]** Base layout overhaul
  - Soubor: `frontend/css/layout.css`
  - Topbar: ornamentální SVG oddělovače, hex avatar clip-path, animated HP/MP bars
  - Sidebar: collapsible skupiny, runové ikonky, zlatý border active state
  - Content area: dark panels s CSS mask-image pergamenovými okraji

- [x] **[A.3]** SVG asset knihovna
  - Nový soubor: `frontend/css/assets.css` (inline SVG jako CSS background-image / mask)
  - Nebo: `frontend/assets/` složka se SVG soubory
  - Sada: icon-sword, icon-shield, icon-skull, icon-rune-atk/def/spd/hp/mp/luck, icon-gold
  - Ornamenty: ornament-divider (horizontální linka s runami), ornament-corner (rohový panel ornament)
  - Wax seals: seal-common/uncommon/rare/epic/legendary (5 designů pro rarity)

- [x] **[A.4]** Component library
  - Soubor: `frontend/css/components.css` (přepis)
  - Buttony: zlatý glow inward na hover, scale(1.02), GPU-only (transform + opacity)
  - Karty: tmavé panely s backdrop-filter blur, zlaté headery, stat řádky s SVG ikonami
  - Badges: rarity color system (common bílá / uncommon modrá / rare zlatá / epic fialová / legendary červená)
  - Tooltips: absolutně pozicované, tmavé sklo, animated entrance

- [x] **[A.5]** Quest board
  - Soubor: `frontend/css/quest.css`
  - Pergamenové karty: CSS border-image + SVG noise filter textury, roztrhané okraje
  - Difficulty glowy (bílá/modrá/zlatá/červená)
  - Wax seal ornament na každé kartě
  - Active quest: pulsující golden border + animated rune pattern na pozadí
  - Hover: translateY(-2px) + depth shadow

- [x] **[A.6]** Combat screen
  - Soubor: `frontend/css/combat.css`
  - Full-viewport layout (Hades styl)
  - Combatant cards: draconic ornamental SVG borders
  - HP bars: damage flash (červený overlay → fade)
  - Combat log: barevné řádky (hit=bílá, crit=zlatá, miss=šedá, death=červená)
  - Floating damage numbers: CSS keyframe "vyletí nahoru + zmizí"
  - Screen shake na critical hit
  - Victory screen: SVG particle burst, Cinzel "VICTORY" s golden glow

- [x] **[A.7]** Inventory + Equipment
  - Soubor: `frontend/css/inventory.css`
  - PoE-style grid: 48×48px sloty, dark panel
  - Item rarity border colors
  - Equipment silueta: wireframe SVG postavy, sloty jako labeled regions
  - Drag & drop ghost element

- [x] **[A.8]** Character panel
  - Soubory: `frontend/css/components.css` (rozšíření)
  - "Codex entry" layout — jako stránka z bestiary
  - Stat bars: barevné dle typu (STR=červená, AGI=zelená, INT=modrá, DEF=šedá, LCK=zlatá)
  - SVG horizontal dividers s runovým vzorem
  - Talent tree: SVG hexagonal/diamond grid, activated nodes s glow, SVG path connectors

- [x] **[A.9]** Hub / Home screen
  - Soubory: `frontend/js/hub.js`, `frontend/css/layout.css`
  - Atmospheric background: CSS radial gradients (mlha, vzdálené hory)
  - Time of day systém (dawn/day/dusk/night) — gradientové přechody, již částečně implementováno
  - District cards: velké karty pro oblasti (Quest Board, Market, Guild, Gauntlet)
  - Ambient particles: floating ash/ember CSS animation (nebo minimal Canvas v `frontend/js/particles.js`)

- [x] **[A.10]** Animations & micro-interactions
  - Soubor: `frontend/css/animations.css`
  - Page load: staggered reveal (logo → topbar → content), fade + slide-up
  - Logo: SVG stroke-dashoffset "rune inscription" animace při loadu
  - Level up: zlatá záře z centra screenu
  - Gold gain: +N text flies up from coin
  - Item drop: karta "padá" z vrcholu screenu
  - Quest complete: seal symbol "pečetí" quest kartu
  - Všechny animace: GPU-only (transform, opacity)

- [x] **[A.11]** Mobile responsivita
  - Breakpoint 768px
  - Bottom navigation bar (ne topbar)
  - Full-screen modaly
  - Swipeable panely
  - Soubory: `frontend/css/layout.css` (media queries)

---

## ☠️ FÁZE B — HC Core: Permadeath Foundation

> **Cíl:** Hra existuje pouze v HC módu. Smrt v dungeonu = permanentní smrt postavy.
> Aréna a questy jsou bezpečné (budování postavy). Dungeony jsou nebezpečné (srdce hry).

### B1 — Character Creation Pivot

- [ ] **[B.1]** HC-only character creation
  - Odstranit jakýkoliv "standard mode" z frontend UI
  - Character creation screen: dramatický, atmosférický — hráč ví co riskuje
  - Varování: jasný text "Tato postava zemře jednou. Navždy."
  - Soubory: `frontend/js/character.js`, `frontend/game.html`

- [ ] **[B.2]** HC character flag v databázi
  - Přidat `is_hardcore: bool = True` na Character model (default True, povinné)
  - Migrace: `0033_hardcore_character_flag.py`
  - Soubory: `backend/models/character.py`, `backend/alembic/versions/`

### B2 — Permadeath Mechanics

- [ ] **[B.3]** Permadeath trigger v dungeonu
  - Při HP = 0 v dungeonu: místo standardního "failed" spustit permadeath sekvenci
  - Postava označena jako `is_dead = True`, `died_at = now()`, `killed_by = enemy_name`
  - Přidat sloupce na Character: `is_dead`, `died_at`, `killed_by`, `death_dungeon`
  - Migrace: `0034_permadeath_columns.py`
  - Soubory: `backend/routers/dungeon.py`, `backend/models/character.py`

- [ ] **[B.4]** Mrtvá postava je read-only
  - Všechny endpointy zkontrolují `is_dead` — mrtvá postava nemůže provádět akce
  - Dependency helper: `get_living_character()` (rozšíření `get_current_user`)
  - Soubory: `backend/routers/` (všechny relevantní routery)

- [ ] **[B.5]** Death screen (frontend)
  - Dedikovaná fullscreen stránka při permadeath — ne toast, ne modal
  - Dramatická animace: temnota, epitaf postavy, "padlý" portrétem
  - Zobrazí: jméno, třída, level, čím zemřel, délka přežití (dny)
  - Tlačítka: "Zobrazit v Hall of the Fallen" + "Vybrat Legacy Item" + "Začít nový run"
  - Soubory: `frontend/js/main.js`, `frontend/game.html`, `frontend/css/combat.css`

- [ ] **[B.6]** Aréna safety
  - Aréna: žádný permadeath, pouze ELO + gold změny
  - Explicitní UI label: "Boj bez sázky o život"
  - Soubory: `frontend/js/arena.js`

---

## 🩸 FÁZE C — Bloodline System (Meta-progression)

> **Cíl:** Každý run — ať zemřeš na levelu 3 nebo 45 — přispívá k permanentní rodinné linii.
> Bloodline XP se akumuluje, odemyká bonusy a třídy pro budoucí hrdiny.
> Hráč nikdy "nezačíná od nuly" — jen od mírně silnějšího základu.

- [ ] **[C.1]** Bloodline model
  - Nový model `Bloodline` (per user, ne per character)
  - Sloupce: `user_id`, `total_xp`, `level`, `unlocks_json`
  - Migrace: `0035_bloodline.py`
  - Soubory: `backend/models/bloodline.py`, `backend/models/__init__.py`

- [ ] **[C.2]** Bloodline XP accumulation
  - Při permadeath: vypočti Bloodline XP z délky přežití + levelu dosaženého
  - Formula: `bloodline_xp = char.level * 10 + days_survived * 5 + dungeons_cleared * 3`
  - Přičíst k `Bloodline.total_xp`, přepočítat `Bloodline.level`
  - Soubory: `backend/game/bloodline.py` (nový), `backend/routers/dungeon.py`

- [ ] **[C.3]** Bloodline unlock tabulka
  - Soubor: `backend/game/bloodline.py`
  - Level 1–5: startovní bonusy (+5% HP, +50 gold, +small stat)
  - Level 6–10: odemknutí subclass variant dříve (level 15 místo 20)
  - Level 11–20: exkluzivní kosmetika (portrait frames, tituly)
  - Level 21+: "Ancestor Memories" — pasivní bonusy (příběhově: paměť předka)
  - Implementovat jako `BLOODLINE_UNLOCKS` dict v config

- [ ] **[C.4]** Ancestor Memories
  - Speciální tier Bloodline unlocks (level 21+)
  - Příklady: "Předek byl Mage" → +3% spell damage | "Předek přežil 30 dní" → +5 max HP
  - Dynamicky generované z historie padlých hrdinů uživatele
  - Aplikovat v `recalculate_stats()` jako poslední modifikační vrstva
  - Soubory: `backend/game/bloodline.py`, `backend/models/character.py`

- [ ] **[C.5]** Bloodline API + UI
  - GET `/bloodline/status` — aktuální level, XP, odemčené bonusy, memories
  - Frontend: nová stránka "Krevní linie" — timeline padlých hrdinů, XP progress, odemčené bonusy
  - Soubory: `backend/routers/bloodline.py`, `frontend/js/bloodline.js`

---

## ⚔️ FÁZE D — Legacy Item System

> **Cíl:** Při smrti si vyber jeden předmět. Ten zdědí tvůj příští hrdina.
> Předmět nese historii — každá generace přidá svůj zápis. Starý item může mít 5 jmen.

- [ ] **[D.1]** Legacy item výběr
  - Na death screenu: hráč vybere jeden item z inventáře jako "legacy"
  - Pokud hráč nevybere (timeout/zavře): automaticky nejhodnotnější item
  - Soubory: `frontend/js/main.js` (death screen flow)

- [ ] **[D.2]** Legacy item tagging v databázi
  - Přidat na InventoryItem: `legacy_chain_json` (pole zápisů: jméno/třída/level/datum/dungeon)
  - Při zdědění: append nový zápis do řetězce
  - Migrace: `0036_legacy_item_chain.py`
  - Soubory: `backend/models/item.py`, `backend/routers/character.py`

- [ ] **[D.3]** Legacy item v character creation
  - Při tvorbě nového hrdiny: GET `/legacy/pending` vrátí předmět čekající na zdědění
  - Nový hrdina začne s legacy itemem v inventáři (automaticky)
  - Legacy item UI: speciální visual treatment — zlatý border, "Dědictví" badge
  - Tooltip zobrazí celou historii (chain zápisů)
  - Soubory: `backend/routers/character.py`, `frontend/js/character.js`

---

## 🏛️ FÁZE E — Hall of the Fallen + Living Ladder

> **Hall of the Fallen:** Každý padlý hrdina immortalizován navždy — jméno, build, smrt.
> **Living Ladder:** Leaderboard živých postav. Každý na žebříčku může zítra zemřít.

### E1 — Hall of the Fallen

- [ ] **[E.1]** FallenHero model
  - Nový model `FallenHero` — snapshot při permadeath
  - Sloupce: `user_id`, `char_name`, `class_name`, `level`, `prestige_level`, `subclass`,
    `days_survived`, `killed_by`, `death_dungeon`, `equipment_snapshot_json`,
    `talent_snapshot_json`, `died_at`, `legacy_item_name`
  - Migrace: `0037_hall_of_fallen.py`
  - Soubory: `backend/models/fallen_hero.py`

- [ ] **[E.2]** Automatický snapshot při permadeath
  - Při death trigger: vytvoř FallenHero záznam ze současného stavu postavy
  - Soubory: `backend/routers/dungeon.py`, `backend/game/bloodline.py`

- [ ] **[E.3]** Hall of the Fallen API + UI
  - GET `/hall/fallen?page=N&sort=level|date|days` — paginated seznam
  - GET `/hall/fallen/{id}` — detail (full build snapshot)
  - Frontend: veřejná stránka přístupná bez loginu
  - UI: tmavá síň, každý hrdina jako "náhrobek" karta — epitaf styl
  - Kliknutím: detail buildu (equipment, talenty, jak zemřel)
  - Soubory: `backend/routers/hall.py`, `frontend/js/hall.js`

### E2 — Living Ladder

- [ ] **[E.4]** Living Ladder endpoint
  - GET `/ladder/living` — seřazení živých HC postav dle level desc, days_survived desc
  - Vrací: jméno, třída, level, days_survived, prestige, subclass (read-only preview)
  - Cache: 60s TTL (stejný pattern jako arena leaderboard)
  - Soubory: `backend/routers/ladder.py`

- [ ] **[E.5]** Living Ladder UI
  - Stránka s live žebříčkem — pravidelný auto-refresh (30s)
  - Vizuální důraz: "Tito hrdinové jsou naživu — zatím."
  - Kliknutím na hráče: read-only profil build preview
  - Pokud hráč zemře: jeho řádek na chvíli zčervená a zmizí (animated removal)
  - Soubory: `frontend/js/ladder.js`

---

## 🗡️ FÁZE F — Asymetrické třídy

> **Cíl:** Každá třída hraje jinak na úrovni systémových pravidel — ne jen různá čísla.
> Warrior = resource management | Mage = chain reactions | Ranger = diminishing returns

### F1 — Warrior: Rage System

- [ ] **[F.1]** Rage mechanikem v combat engine
  - Warrior nepoužívá MP pro standardní útoky
  - Místo toho: `rage` resource (0–100), builduješ každým tahem (+15/hit, +25/hit received)
  - Na 100 rage: automaticky spustí "Berserker Burst" (double damage, +stun efekt)
  - Rage resetuje na 0 po burstu
  - Soubory: `backend/game/combat_engine.py` (rozšíření _FighterState)

### F2 — Mage: Chain Reactions

- [ ] **[F.2]** Spell chain systém v combat engine
  - Mage spell má "chain type": Fire / Ice / Arcane / Void
  - Pokud předchozí spell byl jiného chain type: +20% damage (combo bonus)
  - Pokud stejného chain type: -10% damage (repetition penalty)
  - `last_spell_type` tracked v _FighterState
  - Pořadí castování rozhoduje — AI Mage střídá typy, hráč nastavuje strategii
  - Soubory: `backend/game/combat_engine.py`

### F3 — Ranger: First Strike Advantage

- [ ] **[F.3]** Diminishing returns per round
  - Ranger má bonus +40% damage a +15% crit na kolo 1
  - Každé další kolo: bonus klesá o 8% damage, 3% crit (floor 0)
  - Kolo 6+: standardní stats bez bonusu
  - Mechanikem odměňuje rychlé dungeony, penalizuje zdlouhavé
  - Soubory: `backend/game/combat_engine.py`

### F4 — Class Selection UI

- [ ] **[F.4]** Redesign class selection screenu
  - Každá třída má vlastní "flavor card": ilustrace (CSS art), unikátní mechanikem popsaný
  - Warrior: "Tvoje zuřivost roste s každou ránou. Přežij dost dlouho a staneš se neovladatelný."
  - Mage: "Magie reaguje na sebe. Každé kouzlo nastaví to příští. Poznej pořadí."
  - Ranger: "První šíp zasáhne vždy. Druhý trochu míň. Třetí... doufej, že ho nepotřebuješ."
  - Soubory: `frontend/js/character.js`, `frontend/css/components.css`

---

## ⚡ FÁZE G — Combat: Grafický upgrade

> **Rozhodnutí (2026-03-12):** Combat systém zůstává mechanicky beze změny.
> Pouze vizuální vylepšení — dramatičtější animace, lepší combat screen layout, floating numbers.
> Toto je součástí Fáze A.6 (combat.css). Separátní fáze G není potřeba.

---

## 📊 Progress Tracker

| Fáze | Název | Úkolů | Hotovo | Zbývá |
|------|-------|-------|--------|-------|
| A | Vizuální identita (Obsidian Codex) | 11 | 11 | 0 ✅ |
| B | HC Core — Permadeath | 6 | 6 | 0 ✅ |
| C | Bloodline System | 5 | 5 | 0 ✅ |
| D | Legacy Item | 3 | 3 | 0 ✅ |
| E | Hall of the Fallen + Living Ladder | 5 | 5 | 0 ✅ |
| F | Asymetrické třídy | 4 | 4 | 0 ✅ |
| G | Unikátní Combat System | TBD | — | — |
| **Celkem** | | **34+** | **34** | **0** ✅ |

---

## 🔗 Závislosti mezi fázemi

```
A (Vizuál) ──────────────────────────────── nezávislá, může začít ihned
B (HC Core) ─────────────────────────────── nezávislá, může začít ihned
C (Bloodline) ──── závisí na B.3 (permadeath trigger)
D (Legacy Item) ─── závisí na B.3 + C.1
E (Hall/Ladder) ─── závisí na B.3 + D.2
F (Asymetrické třídy) ─── závisí na combat engine (existující)
G (Combat System) ──── závisí na F (třídy musí být hotové)
```

**Doporučené pořadí:** A paralelně s B → C → D → E → F → G

---

## 🎯 Technické poznámky

### Backend migrace
- Migrace 0033–0037 jsou nové HC systémy
- Nikdy neupravuj existující migrace (pravidlo projektu)
- Každá migrace musí mít `inspect()` guard (idempotentní)

### Frontend pořadí scriptů (game.html)
Nové moduly přidat ZA existující v tomto pořadí:
```
... (existující) ... → bloodline → hall → ladder → particles → (main)
```

### CSS soubory — nová struktura
```
frontend/css/
├── design-system.css   ← NOVÝ (základ všeho)
├── layout.css          ← PŘEPIS
├── components.css      ← PŘEPIS
├── animations.css      ← NOVÝ
├── quest.css           ← NOVÝ (extrahován z theme.css)
├── combat.css          ← NOVÝ (extrahován z theme.css)
├── inventory.css       ← NOVÝ (extrahován z theme.css)
└── theme.css           ← ZACHOVÁN (pouze HC-specific overrides)
```

### Nové routery (registrovat v main.py)
```python
from routers import bloodline, hall, ladder
app.include_router(bloodline.router, prefix="/bloodline", tags=["bloodline"])
app.include_router(hall.router, prefix="/hall", tags=["hall"])
app.include_router(ladder.router, prefix="/ladder", tags=["ladder"])
```

---

## 📝 Session Log

| Datum | Co bylo uděláno |
|-------|----------------|
| 2026-03-12 | Design session — HC Gauntlet identity definována, tento roadplan vytvořen |
| 2026-03-13 | A.1+A.2 (předchozí session) · A.3 assets.css · A.4 components.css (OC rozšíření) · A.5 quest.css · A.6 combat.css · A.7 inventory.css · A.8 char panel · A.9 hub · A.10 animations.css · A.11 mobile → **FÁZE A DOKONČENA ✅** |
| 2026-03-14 (1) | Audit: B–E již implementováno v předchozích sessions (modely, migrace 0036-0041, routery, game logika, frontend JS) · Doplnění chybějících kusů: B.3 permadeath trigger v dungeon.py (_trigger_permadeath helper + volání v /enter + /next-stage) · B.1 is_hardcore=True default + povolení nového runu po smrti · B.5 showDeathScreen CSS fix (.active třída místo style.display) + propojení s dungeon.js · B.6 arena-safety-badge CSS class ověřena → **FÁZE B–E DOKONČENA ✅** |
| 2026-03-14 (2) | F.1 Warrior Rage (rage 0–100, Berserker Burst double dmg + stun) · F.2 Mage Spell Chain (Fire/Ice/Arcane/Void cyklus, ±20%/-10% dmg) · F.3 Ranger First Strike (+40% dmg +15% crit kolo 1, klesá každé kolo) · F.4 class selection redesign (flavor texty, mechanic detail, styled stats, .hc-warning) → **FÁZE F DOKONČENA ✅** |

---

## 💬 Design rozhodnutí k dokumentaci

| Rozhodnutí | Volba | Důvod |
|-----------|-------|-------|
| Standard mode | Odstraněn | Čistá identita — HC-only, žádná diluce |
| Permadeath zdroj | Pouze dungeons | Aréna = taktika bez existenčního rizika |
| Bloodline scope | Per-user, ne per-character | Meta-progression překlenuje všechny runy |
| Legacy item count | 1 item | Težší volba = emocionálnější rozhodnutí |
| Combat system | TBD (Fáze G) | Vyžaduje separátní design session |
| Vizuální inspirace | Path of Exile + Hades + Elden Ring | Vlastní DNA, ne kopie |
