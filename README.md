# ⚔️ Dungeon Chronicles — Setup Guide

## Požadavky
- Python 3.11+
- pip

---

## 1. Instalace

```bash
cd backend
pip install -r requirements.txt
```

---

## 2. Spuštění serveru

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Server se spustí na `http://localhost:8000`

- Automaticky vytvoří databázi `dungeon.db`
- Automaticky naplní 40+ itemů (seed)

---

## 3. Otevření hry

Otevři v prohlížeči:
```
http://localhost:8000
```

Nebo přímo soubory:
- `frontend/index.html` — login stránka
- `frontend/game.html` — herní UI

> ⚠️ Pokud otevíráš přímo soubory (ne přes server), ujisti se že backend běží na portu 8000.

---

## 4. API dokumentace

FastAPI automaticky generuje dokumentaci:
```
http://localhost:8000/docs
```

---

## Struktura projektu

```
dungeon-chronicles/
├── backend/
│   ├── main.py          ← Entry point
│   ├── database.py      ← SQLAlchemy setup
│   ├── config.py        ← Nastavení / JWT secret
│   ├── models/          ← DB modely
│   ├── routers/         ← API endpointy
│   ├── game/            ← Herní logika
│   └── requirements.txt
└── frontend/
    ├── index.html       ← Login / Register
    └── game.html        ← Hlavní herní UI
```

---

## Hotové v Session 1

- ✅ User registrace + login (JWT auth)
- ✅ Tvorba postavy (3 třídy: Válečník, Mág, Lovec)
- ✅ Quest systém (start → timer → collect)
- ✅ Bojová logika (auto-fight výpočet)
- ✅ Loot / drop systém
- ✅ Level up systém
- ✅ 40+ itemů v databázi
- ✅ Dark fantasy UI

## Plánováno v Session 2

- 🔜 Aréna PvP (žebříček, útoky)
- 🔜 Guild systém (create, join, chat)
- 🔜 Inventář + equip systém
- 🔜 Trh (marketplace)
