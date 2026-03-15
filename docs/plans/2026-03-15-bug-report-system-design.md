# Bug Report System — Design

**Datum:** 2026-03-15
**Status:** Schváleno

---

## Přehled

Systém pro hlášení bugů přímo ze hry. Hráč klikne na tlačítko v topbaru, vyplní formulář a report se uloží do DB. Admin vidí reporty v novém tabu admin panelu, může měnit stav a publikovat opravy jako "Bug Fix" novinku.

---

## Datový model

Nová tabulka `BugReport` (Alembic migrace):

| Sloupec | Typ | Popis |
|---------|-----|-------|
| `id` | Integer PK | Auto |
| `character_id` | FK → Character.id (nullable) | Autor |
| `title` | String(120) | Název bugu |
| `description` | Text | Co se stalo |
| `steps` | Text | Kroky k reprodukci |
| `severity` | Enum: `cosmetic/minor/critical` | Závažnost |
| `page_context` | String(80) | Aktivní sekce hry (auto JS) |
| `status` | Enum: `open/in_progress/resolved/closed` | Stav |
| `char_name` | String(80) | Snapshot jména (pro případ smazání) |
| `char_level` | Integer | Snapshot levelu |
| `char_class` | String(60) | Snapshot třídy |
| `admin_note` | Text (nullable) | Interní poznámka admina |
| `created_at` | DateTime | |
| `updated_at` | DateTime | |

---

## Backend API

### Nový router: `backend/routers/bugs.py`

| Endpoint | Metoda | Auth | Popis |
|----------|--------|------|-------|
| `/bugs/report` | POST | JWT | Hráč odešle bug report |

Rate limit: max 5 reportů za 24h na character_id.

### Rozšíření `backend/routers/admin.py`

| Endpoint | Metoda | Auth | Popis |
|----------|--------|------|-------|
| `/admin/bugs` | GET | Admin key | Seznam (filter: status, severity) |
| `/admin/bugs/{id}` | GET | Admin key | Detail reportu |
| `/admin/bugs/{id}/status` | PATCH | Admin key | Změna stavu |
| `/admin/bugs/{id}/note` | PATCH | Admin key | Admin poznámka |
| `/admin/bugs/{id}` | DELETE | Admin key | Smazání |

---

## Frontend — Hra (game.html / bugs.js)

### Topbar tlačítko
Přidat do `.tb-actions` před "Odhlásit":
```html
<button class="tb-btn" onclick="openModal('modal-bug-report')" title="Report a Bug">🐛</button>
```

### Modal `modal-bug-report`
Standardní pattern `overlay > modal`:
- Nadpis: "🐛 Report a Bug"
- Input: Název bugu (max 120 znaků, required)
- Textarea: Popis — co se stalo (required)
- Textarea: Kroky k reprodukci (optional)
- Select: Závažnost
  - 💅 Kosmetická (cosmetic)
  - ⚠️ Menší (minor)
  - 🔥 Kritická (critical)
- Hidden fields: page_context (z aktivní stránky), char data
- Submit: "Odeslat report"
- Feedback: toast("Díky za report! Budeme se tím zabývat.", 's')

### Nový soubor: `frontend/js/bugs.js`
- `submitBugReport()` — POST `/bugs/report`, validace, toast
- Detekce aktivní stránky z globální proměnné nebo DOM

**Pořadí v game.html:** Za `achievements.js`, před `crystals.js` (nebo konec před main.js).

---

## Frontend — Admin Panel (admin.html)

### Nový tab: `🐛 Bug Reporty` (12. tab)

**Filtrační lišta:**
- Dropdown: Status (Vše / Open / In Progress / Resolved / Closed)
- Dropdown: Závažnost (Vše / Kosmetická / Menší / Kritická)
- Tlačítko: Načíst / Refresh

**Tabulka reportů:**
| Závažnost | Název | Hráč | Sekce | Datum | Stav |
Barevné badges: Kosmetická=šedá, Menší=žlutá, Kritická=červená

**Detail panel** (klik na řádek):
- Všechna pole reportu (read-only zobrazení)
- Dropdown: Změna stavu
- Textarea: Admin poznámka
- Tlačítko: "Uložit změny"
- Tlačítko: "📰 Vytvořit Bug Fix novinku" → prefilluje existující news formulář s kategorií Bug Fix
- Tlačítko: "🗑 Smazat report"

---

## NewsArticle rozšíření

Přidat hodnotu `bug_fix` do kategorie `NewsArticle` (nebo typ zprávy).
Admin kliknutím "Vytvořit Bug Fix novinku" prefilluje news formulář s:
- Nadpis: auto z názvu bugu
- Kategorie: Bug Fix
- Odkaz na report (interně)

---

## Anti-spam

- Max 5 reportů / 24h / character — kontrola v `/bugs/report` endpointu
- Validace délky polí server-side

---

## Migrace

Nová Alembic migrace: `0043_bug_reports.py`
Guard: `inspect()` před `add_column` / `create_table`
