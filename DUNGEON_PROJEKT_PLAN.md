# ⚔️ DUNGEON CHRONICLES — Projektový plán
### Shakes & Fidget inspirovaná webová RPG | Multiplayer | Python backend

---

## 🎯 Vize projektu

Browserová multiplayer RPG ve stylu Shakes & Fidget kombinující **pixel-art fantasy humor** s **tmavou serious RPG estetikou**. Hráč vytvoří postavu, plní questy, bojuje v aréně s ostatními hráči, buduje cech a obchoduje na trhu — vše asynchronně (nepotřebuješ být online současně s ostatními).

---

## 🏗️ Tech Stack

| Vrstva | Technologie | Proč |
|--------|------------|------|
| **Backend** | Python · FastAPI | Rychlý, moderní, async, ideální pro REST + WebSocket |
| **Databáze** | SQLite → PostgreSQL | SQLite pro vývoj, Postgres pro produkci |
| **ORM** | SQLAlchemy 2.0 | Pythonic, async podpora |
| **Auth** | JWT tokeny | Jednoduché, stateless |
| **Frontend** | Vanilla JS + HTML/CSS | Žádný framework = méně závislostí, ty řídíš vše |
| **Real-time** | WebSocket (FastAPI) | Notifikace, aréna, live chat cechu |
| **Hosting (later)** | Railway / Render | Free tier, Python nativní podpora |

---

## 📁 Struktura projektu

```
dungeon-chronicles/
│
├── backend/
│   ├── main.py               # FastAPI app entry point
│   ├── database.py           # SQLAlchemy setup
│   ├── models/
│   │   ├── user.py           # User účet
│   │   ├── character.py      # Postava, stats, inventář
│   │   ├── quest.py          # Questy a dungeony
│   │   ├── arena.py          # PvP záznamy
│   │   ├── guild.py          # Cechy
│   │   └── market.py         # Tržiště
│   ├── routers/
│   │   ├── auth.py           # /register, /login
│   │   ├── character.py      # /character/create, /stats
│   │   ├── quest.py          # /quest/start, /quest/collect
│   │   ├── arena.py          # /arena/attack, /arena/ranking
│   │   ├── guild.py          # /guild/create, /guild/join
│   │   └── market.py         # /market/list, /market/buy
│   ├── game/
│   │   ├── combat.py         # Bojová logika (auto-fight výpočty)
│   │   ├── loot.py           # Drop systém
│   │   ├── xp.py             # Level up křivky
│   │   └── scheduler.py      # Časované eventy (quest dokončení)
│   └── requirements.txt
│
├── frontend/
│   ├── index.html            # Login / Register
│   ├── game.html             # Hlavní herní UI
│   ├── css/
│   │   ├── base.css          # Reset + proměnné
│   │   ├── layout.css        # Panely, grid
│   │   ├── components.css    # Tlačítka, bary, karty
│   │   └── theme.css         # Dark fantasy + pixel font
│   └── js/
│       ├── api.js            # Fetch wrapper pro backend
│       ├── auth.js           # Login/logout/JWT
│       ├── character.js      # Postava UI
│       ├── quest.js          # Quest UI
│       ├── arena.js          # PvP UI
│       ├── guild.js          # Cech UI
│       ├── market.js         # Trh UI
│       └── ui.js             # Sdílené UI komponenty
│
└── README.md
```

---

## 🗄️ Databázový model (přehled)

```
users           → id, username, password_hash, created_at, last_login
characters      → id, user_id, name, class, level, xp, gold, stats (JSON)
inventory       → id, character_id, item_id, quantity, equipped
items           → id, name, type, stats (JSON), rarity, icon
quests          → id, character_id, quest_type, started_at, finish_at, reward (JSON)
arena_log       → id, attacker_id, defender_id, result, timestamp, loot
guilds          → id, name, leader_id, description, level, xp
guild_members   → id, guild_id, character_id, role, joined_at
market_listings → id, seller_id, item_id, price, listed_at, expires_at
```

---

## 🎮 Herní systémy — detailní popis

### 1. Postavy & Třídy
- **3 třídy:** Válečník · Mág · Lovec
- Každá třída má jiné **base stats** a **scaling** při level upu
- Stats: Síla · Obratnost · Inteligence · Výdrž · Štěstí
- **Equip sloty:** Zbraň · Přilba · Brnění · Rukavice · Boty · Prsten · Amulet

### 2. Questy & Dungeony (auto-fight)
- Hráč vybere quest a "odejde" — hra počítá výsledek na pozadí
- Po uplynutí doby (minuty–hodiny) hráč "sesbírá" odměnu
- Výsledek (výhra/prohra) je určen porovnáním stats postavy vs. obtížnosti
- Dungeony = série questů s boss fajtem na konci
- Odměny: XP · Gold · Equipment drops (náhodný loot)

### 3. Aréna PvP
- Asynchronní souboje (jako S&F) — útočíš na offline hráče
- Bojová logika: deterministický výpočet z stats obou postav + náhoda
- **Ranking žebříček** s sezonami (reset každé 2 týdny)
- Odměny za arénu: speciální měna · exkluzivní itemy

### 4. Cech (Guild systém)
- Tvorba / vstup do cechu
- **Cech dungeon** — společný boss, hráči přispívají damage
- Guild chat (WebSocket)
- Role: Vůdce · Důstojník · Člen
- Guild level → bonusy pro členy (% XP boost, gold bonus...)

### 5. Obchod / Trh
- Hráči listují itemy za gold
- Vyhledávání podle typu / raritou / cenou
- Automatické expiry listingů (24h)
- **Bazarové poplatky** (5% daň) → gold sink

---

## 🚀 Fáze vývoje (roadmap)

### Fáze 1 — Základ (Sessions 1–3)
> *Cíl: fungující hra pro jednoho hráče bez frontendu*
- [ ] FastAPI projekt setup + SQLAlchemy + SQLite
- [ ] User registrace + login + JWT auth
- [ ] Character create + stats systém
- [ ] Quest systém (start quest → časovač → collect)
- [ ] Combat logika (výpočty)
- [ ] Basic loot a XP systém
- [ ] Level up křivka

### Fáze 2 — Frontend (Sessions 4–6)
> *Cíl: hratelné UI v prohlížeči*
- [ ] HTML/CSS layout (dark fantasy theme)
- [ ] Login / Register stránka
- [ ] Hlavní herní dashboard (postava, stats, gold)
- [ ] Quest panel (výběr, timer, collect)
- [ ] Inventář a equipování itemů
- [ ] Pixel font + ikonky

### Fáze 3 — Multiplayer systémy (Sessions 7–10)
> *Cíl: interakce mezi hráči*
- [ ] Aréna PvP (žebříček, útoky, log)
- [ ] Guild systém (create, join, roster)
- [ ] Guild chat (WebSocket)
- [ ] Tržiště (list, buy, search)

### Fáze 4 — Content & Polish (Sessions 11+)
> *Cíl: skutečná hratelnost a obsah*
- [ ] 50+ itemů s raritami (Common → Legendary)
- [ ] 20+ questů + 5 dungeonů
- [ ] Guild dungeon (společný boss)
- [ ] Sezony arény + odměny
- [ ] Achievementy
- [ ] Admin panel
- [ ] Deploy na cloud (Railway/Render)

---

## 🖼️ UI Design principy

```
Barevná paleta:
  Pozadí:     #0d0d1a  (velmi tmavá modrá)
  Panel:      #1a1a2e
  Akcent:     #e94560  (červená) + #f5a623 (zlatá)
  Text:       #c8c8d4
  Success:    #4caf7d
  
Font:        "Press Start 2P" (Google Fonts) — pixel styl
             + běžný sans-serif pro delší texty

Layout:      3-sloupcový panel (vlevo postava, střed hlavní obsah, vpravo sidebar)
Inspirace:   S&F tmavý skin + Diablo II UI estetika
```

---

## 📋 Jak budeme pracovat

1. **Každá session = jedna fáze nebo jeden systém** — vždy funkční výsledek
2. Nejdřív **backend logika** (Python) → pak **frontend UI** (HTML/JS)
3. Každý systém bude mít **testy** (pytest) aby se nic nerozbilo
4. Průběžně **commitovat** do git repozitáře
5. Na konci každé session = **hratelná verze** co si můžeš spustit

---

## ✅ Kde začneme příště

**Session 1: Backend základ**
```
1. Projekt struktura + virtual environment
2. FastAPI + SQLAlchemy setup
3. User model + /register + /login (JWT)
4. Character model + /character/create + /character/stats
5. Spustitelný server: uvicorn main:app
```

Stačí říct "začínáme" a jdeme na to! 🔥
