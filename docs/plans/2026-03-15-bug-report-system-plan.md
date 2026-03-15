# Bug Report System — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Přidat systém bug reportů — tlačítko v topbaru hry otevře modal, hráč vyplní report, admin ho vidí v novém tabu admin panelu se stavovým workflow.

**Architecture:** Nová tabulka `BugReport` v DB, dedikovaný router `/bugs` pro hráčské endpointy + rozšíření `/admin/bugs` v existujícím admin routeru. Frontend: nový `bugs.js` modul + modal v `game.html` + nový tab v `admin.html`.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, Vanilla JS, aiosqlite (dev)

---

## Task 1: BugReport SQLAlchemy model

**Files:**
- Create: `backend/models/bug_report.py`
- Modify: `backend/models/__init__.py`

**Step 1: Vytvoř model**

```python
# backend/models/bug_report.py
"""
models/bug_report.py — Bug reports od hráčů
"""
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class BugReport(Base):
    __tablename__ = "bug_reports"

    id:           Mapped[int]          = mapped_column(primary_key=True)
    character_id: Mapped[int | None]   = mapped_column(Integer, ForeignKey("characters.id", ondelete="SET NULL"), nullable=True)
    title:        Mapped[str]          = mapped_column(String(120))
    description:  Mapped[str]          = mapped_column(Text)
    steps:        Mapped[str | None]   = mapped_column(Text, nullable=True)
    severity:     Mapped[str]          = mapped_column(String(20), default="minor")
    # cosmetic | minor | critical
    page_context: Mapped[str | None]   = mapped_column(String(80), nullable=True)
    status:       Mapped[str]          = mapped_column(String(20), default="open")
    # open | in_progress | resolved | closed
    char_name:    Mapped[str | None]   = mapped_column(String(80), nullable=True)
    char_level:   Mapped[int | None]   = mapped_column(Integer, nullable=True)
    char_class:   Mapped[str | None]   = mapped_column(String(60), nullable=True)
    admin_note:   Mapped[str | None]   = mapped_column(Text, nullable=True)
    created_at:   Mapped[datetime]     = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at:   Mapped[datetime]     = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "character_id": self.character_id,
            "title":        self.title,
            "description":  self.description,
            "steps":        self.steps,
            "severity":     self.severity,
            "page_context": self.page_context,
            "status":       self.status,
            "char_name":    self.char_name,
            "char_level":   self.char_level,
            "char_class":   self.char_class,
            "admin_note":   self.admin_note,
            "created_at":   self.created_at.isoformat() if self.created_at else None,
            "updated_at":   self.updated_at.isoformat() if self.updated_at else None,
        }
```

**Step 2: Přidej import do `backend/models/__init__.py`**

Za posledním importem přidej:
```python
from models.bug_report import BugReport
```

**Step 3: Commit**

```bash
git add backend/models/bug_report.py backend/models/__init__.py
git commit -m "feat: BugReport SQLAlchemy model"
```

---

## Task 2: Alembic migrace

**Files:**
- Create: `backend/alembic/versions/0043_bug_reports.py`

**Step 1: Vytvoř migraci**

```python
# backend/alembic/versions/0043_bug_reports.py
"""bug_reports table

Revision ID: 0043
Revises: 0042
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = '0043'
down_revision = '0042'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    existing_tables = inspector.get_table_names()

    if 'bug_reports' not in existing_tables:
        op.create_table(
            'bug_reports',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('character_id', sa.Integer(), sa.ForeignKey('characters.id', ondelete='SET NULL'), nullable=True),
            sa.Column('title', sa.String(120), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('steps', sa.Text(), nullable=True),
            sa.Column('severity', sa.String(20), nullable=False, server_default='minor'),
            sa.Column('page_context', sa.String(80), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='open'),
            sa.Column('char_name', sa.String(80), nullable=True),
            sa.Column('char_level', sa.Integer(), nullable=True),
            sa.Column('char_class', sa.String(60), nullable=True),
            sa.Column('admin_note', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )


def downgrade():
    op.drop_table('bug_reports')
```

**Step 2: Ověř, že migrace proběhne**

```bash
cd backend && alembic upgrade head
```

Očekávaný výstup: `Running upgrade 0042 -> 0043, bug_reports table`

**Step 3: Commit**

```bash
git add backend/alembic/versions/0043_bug_reports.py
git commit -m "feat: migrace 0043 — tabulka bug_reports"
```

---

## Task 3: Backend router `/bugs` (hráčský endpoint)

**Files:**
- Create: `backend/routers/bugs.py`

**Step 1: Vytvoř router**

```python
# backend/routers/bugs.py
"""
routers/bugs.py — Bug reporty od hráčů
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import get_db
from routers.auth import get_current_user
from models.user import User
from models.character import Character
from models.bug_report import BugReport

router = APIRouter(prefix="/bugs", tags=["bugs"])

DAILY_REPORT_LIMIT = 5


class BugReportCreate(BaseModel):
    title:        str            = Field(..., min_length=3, max_length=120)
    description:  str            = Field(..., min_length=10, max_length=2000)
    steps:        str | None     = Field(None, max_length=2000)
    severity:     str            = Field("minor", pattern="^(cosmetic|minor|critical)$")
    page_context: str | None     = Field(None, max_length=80)


@router.post("/report")
async def submit_bug_report(
    payload: BugReportCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Načti postavu
    char = (await db.execute(
        select(Character).where(Character.user_id == user.id)
    )).scalars().first()

    # Rate limit: max DAILY_REPORT_LIMIT reportů za posledních 24h
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
    if char:
        count = (await db.execute(
            select(func.count(BugReport.id)).where(
                BugReport.character_id == char.id,
                BugReport.created_at >= since
            )
        )).scalar_one()
        if count >= DAILY_REPORT_LIMIT:
            raise HTTPException(429, f"Denní limit {DAILY_REPORT_LIMIT} reportů byl dosažen.")

    report = BugReport(
        character_id = char.id if char else None,
        title        = payload.title,
        description  = payload.description,
        steps        = payload.steps,
        severity     = payload.severity,
        page_context = payload.page_context,
        char_name    = char.name if char else None,
        char_level   = char.level if char else None,
        char_class   = char.char_class if char else None,
        status       = "open",
    )
    db.add(report)
    await db.commit()
    return {"ok": True, "id": report.id}
```

**Step 2: Zaregistruj router v `backend/main.py`**

Za řádek `from routers import hall as hall_router` přidej:
```python
from routers import bugs as bugs_router
```

Za řádek `app.include_router(hall_router.router)` přidej:
```python
app.include_router(bugs_router.router)
```

**Step 3: Ověř, že server nastartuje bez chyb**

```bash
cd backend && uvicorn main:app --reload --port 8000
```

Očekávaný výstup: `Application startup complete.`

Zkontroluj endpoint v docs: http://localhost:8000/docs → sekce `bugs`

**Step 4: Commit**

```bash
git add backend/routers/bugs.py backend/main.py
git commit -m "feat: router /bugs — hráčský POST /bugs/report s rate limitem"
```

---

## Task 4: Admin endpointy pro bug reporty

**Files:**
- Modify: `backend/routers/admin.py`

**Step 1: Přidej import BugReport na začátek admin.py**

Za existující importy modelů přidej:
```python
from models.bug_report import BugReport
```

**Step 2: Přidej Pydantic schémata pro admin akce**

Za existující schémata (třídy BaseModel) v admin.py přidej:
```python
class BugStatusUpdate(BaseModel):
    status: str  # open | in_progress | resolved | closed

class BugNoteUpdate(BaseModel):
    admin_note: str
```

**Step 3: Přidej 5 admin endpointů na konec admin.py**

```python
# ── BUG REPORTS ──────────────────────────────────────────────────────────────

@router.get("/bugs")
async def admin_list_bugs(
    status: str | None = None,
    severity: str | None = None,
    _: str = Depends(_check_key),
    db: AsyncSession = Depends(get_db),
):
    q = select(BugReport).order_by(BugReport.created_at.desc())
    if status:
        q = q.where(BugReport.status == status)
    if severity:
        q = q.where(BugReport.severity == severity)
    reports = (await db.execute(q)).scalars().all()
    return [r.to_dict() for r in reports]


@router.get("/bugs/{report_id}")
async def admin_get_bug(
    report_id: int,
    _: str = Depends(_check_key),
    db: AsyncSession = Depends(get_db),
):
    report = (await db.execute(
        select(BugReport).where(BugReport.id == report_id)
    )).scalars().first()
    if not report:
        raise HTTPException(404, "Report nenalezen.")
    return report.to_dict()


@router.patch("/bugs/{report_id}/status")
async def admin_update_bug_status(
    report_id: int,
    payload: BugStatusUpdate,
    _: str = Depends(_check_key),
    db: AsyncSession = Depends(get_db),
):
    valid = {"open", "in_progress", "resolved", "closed"}
    if payload.status not in valid:
        raise HTTPException(400, f"Neplatný stav. Povoleno: {valid}")
    report = (await db.execute(
        select(BugReport).where(BugReport.id == report_id)
    )).scalars().first()
    if not report:
        raise HTTPException(404, "Report nenalezen.")
    report.status = payload.status
    report.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    return {"ok": True}


@router.patch("/bugs/{report_id}/note")
async def admin_update_bug_note(
    report_id: int,
    payload: BugNoteUpdate,
    _: str = Depends(_check_key),
    db: AsyncSession = Depends(get_db),
):
    report = (await db.execute(
        select(BugReport).where(BugReport.id == report_id)
    )).scalars().first()
    if not report:
        raise HTTPException(404, "Report nenalezen.")
    report.admin_note = payload.admin_note
    report.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    return {"ok": True}


@router.delete("/bugs/{report_id}")
async def admin_delete_bug(
    report_id: int,
    _: str = Depends(_check_key),
    db: AsyncSession = Depends(get_db),
):
    report = (await db.execute(
        select(BugReport).where(BugReport.id == report_id)
    )).scalars().first()
    if not report:
        raise HTTPException(404, "Report nenalezen.")
    await db.delete(report)
    await db.commit()
    return {"ok": True}
```

**Step 4: Ověř endpointy v docs**

Server musí jet — zkontroluj: http://localhost:8000/docs → sekce `admin` → bugs endpointy

**Step 5: Commit**

```bash
git add backend/routers/admin.py
git commit -m "feat: admin endpointy pro bug reporty (CRUD + status + note)"
```

---

## Task 5: Frontend — `bugs.js`

**Files:**
- Create: `frontend/js/bugs.js`

**Step 1: Vytvoř soubor**

```javascript
// frontend/js/bugs.js — Bug Report modal & submit

async function submitBugReport() {
  const title       = document.getElementById('br-title').value.trim();
  const description = document.getElementById('br-description').value.trim();
  const steps       = document.getElementById('br-steps').value.trim();
  const severity    = document.getElementById('br-severity').value;
  const pageContext = document.getElementById('br-page-context').value;

  if (!title || title.length < 3) {
    toast('Zadej název bugu (min. 3 znaky).', 'e'); return;
  }
  if (!description || description.length < 10) {
    toast('Popis je příliš krátký (min. 10 znaků).', 'e'); return;
  }

  const btn = document.getElementById('br-submit-btn');
  btn.disabled = true;
  btn.textContent = 'Odesílám...';

  try {
    await api('POST', '/bugs/report', {
      title,
      description,
      steps: steps || null,
      severity,
      page_context: pageContext || null,
    });
    toast('Díky za report! Budeme se tím zabývat.', 's');
    closeModal('modal-bug-report');
    _resetBugReportForm();
  } catch (e) {
    if (e.message && e.message.includes('429')) {
      toast('Denní limit reportů byl dosažen (max 5/den).', 'e');
    } else {
      toast('Chyba při odesílání reportu.', 'e');
    }
  } finally {
    btn.disabled = false;
    btn.textContent = 'Odeslat report';
  }
}

function _resetBugReportForm() {
  ['br-title', 'br-description', 'br-steps'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  const sev = document.getElementById('br-severity');
  if (sev) sev.value = 'minor';
}

function openBugReportModal() {
  // Detekce aktivní stránky z DOM
  const activePage = document.querySelector('.page.active');
  const pageCtx = document.getElementById('br-page-context');
  if (pageCtx && activePage) {
    pageCtx.value = activePage.id || '';
  }
  openModal('modal-bug-report');
}
```

**Step 2: Přidej script tag do `frontend/game.html`**

Najdi v game.html sekci se scripty. Přidej PŘED `<script defer src="js/main.js">`:

```html
<script defer src="js/bugs.js"></script>
```

**Step 3: Commit**

```bash
git add frontend/js/bugs.js frontend/game.html
git commit -m "feat: bugs.js — submitBugReport, openBugReportModal"
```

---

## Task 6: Frontend — Topbar tlačítko + modal v game.html

**Files:**
- Modify: `frontend/game.html`

**Step 1: Přidej tlačítko do topbaru**

Najdi v `game.html` sekci `.tb-actions`:
```html
<div class="tb-actions">
  <button class="tb-btn" id="notif-bell" onclick="showPage('notifications')">🔔</button>
  <button class="tb-btn" onclick="refreshChar()">↺</button>
  <button class="tb-btn dng" onclick="logout()">Odhlásit</button>
</div>
```

Přidej Bug Report tlačítko PŘED refresh:
```html
<div class="tb-actions">
  <button class="tb-btn" id="notif-bell" onclick="showPage('notifications')">🔔</button>
  <button class="tb-btn" onclick="openBugReportModal()" title="Report a Bug">🐛</button>
  <button class="tb-btn" onclick="refreshChar()">↺</button>
  <button class="tb-btn dng" onclick="logout()">Odhlásit</button>
</div>
```

**Step 2: Přidej modal na konec game.html (před `</body>`)**

Najdi sekci s ostatními modaly (hledej `id="modal-item"` nebo `id="modal-create"`). Za poslední modal přidej:

```html
<!-- BUG REPORT MODAL -->
<div class="overlay" id="modal-bug-report">
  <div class="modal" style="max-width:480px">
    <button class="modal-x" onclick="closeModal('modal-bug-report')">✕</button>
    <h2 style="margin-bottom:16px">🐛 Report a Bug</h2>

    <div style="margin-bottom:12px">
      <label style="display:block;font-size:.75rem;color:var(--clr-muted);margin-bottom:4px">Název bugu *</label>
      <input id="br-title" type="text" maxlength="120" placeholder="Krátký popis problému..."
        style="width:100%;background:var(--clr-surface);border:1px solid rgba(255,255,255,.1);color:var(--clr-text);padding:8px 12px;border-radius:6px;font-size:.85rem">
    </div>

    <div style="margin-bottom:12px">
      <label style="display:block;font-size:.75rem;color:var(--clr-muted);margin-bottom:4px">Co se stalo? *</label>
      <textarea id="br-description" maxlength="2000" placeholder="Popiš co se stalo a kde..."
        style="width:100%;height:90px;resize:vertical;background:var(--clr-surface);border:1px solid rgba(255,255,255,.1);color:var(--clr-text);padding:8px 12px;border-radius:6px;font-size:.85rem;font-family:inherit"></textarea>
    </div>

    <div style="margin-bottom:12px">
      <label style="display:block;font-size:.75rem;color:var(--clr-muted);margin-bottom:4px">Kroky k reprodukci</label>
      <textarea id="br-steps" maxlength="2000" placeholder="1. Jdi do... 2. Klikni na... 3. Stane se..."
        style="width:100%;height:70px;resize:vertical;background:var(--clr-surface);border:1px solid rgba(255,255,255,.1);color:var(--clr-text);padding:8px 12px;border-radius:6px;font-size:.85rem;font-family:inherit"></textarea>
    </div>

    <div style="margin-bottom:16px">
      <label style="display:block;font-size:.75rem;color:var(--clr-muted);margin-bottom:4px">Závažnost</label>
      <select id="br-severity"
        style="background:var(--clr-surface);border:1px solid rgba(255,255,255,.1);color:var(--clr-text);padding:8px 12px;border-radius:6px;font-size:.85rem;width:100%;cursor:pointer">
        <option value="cosmetic">💅 Kosmetická — vizuální, neblokuje hru</option>
        <option value="minor" selected>⚠️ Menší — nepříjemné, ale hratelné</option>
        <option value="critical">🔥 Kritická — blokuje hru / ztráta dat</option>
      </select>
    </div>

    <!-- Hidden: auto-fill page context -->
    <input type="hidden" id="br-page-context" value="">

    <button id="br-submit-btn" onclick="submitBugReport()"
      style="width:100%;background:var(--clr-accent);color:#000;border:none;padding:10px;border-radius:6px;font-size:.9rem;font-weight:600;cursor:pointer;letter-spacing:.5px">
      Odeslat report
    </button>
    <p style="font-size:.7rem;color:var(--clr-muted);margin-top:8px;text-align:center">
      Max 5 reportů za 24h · Děkujeme za pomoc! 🙏
    </p>
  </div>
</div>
```

**Step 3: Ověř ve hře**

Spusť server, přihlas se, zkontroluj:
- Tlačítko 🐛 v topbaru viditelné
- Klik otevře modal
- Formulář jde odeslat
- Toast "Díky za report!" se zobrazí

**Step 4: Commit**

```bash
git add frontend/game.html
git commit -m "feat: bug report tlacitko v topbaru + modal s formularem"
```

---

## Task 7: Admin panel — nový tab Bug Reporty

**Files:**
- Modify: `frontend/admin.html`

**Step 1: Přidej tab tlačítko**

Najdi v `admin.html` poslední tab:
```html
<button class="tab" onclick="switchTab('alerts');loadAlerts()" id="tab-alerts">⚠️ Alerts</button>
```

Za něj přidej:
```html
<button class="tab" onclick="switchTab('bugs');loadBugReports()" id="tab-bugs">🐛 Bug Reporty</button>
```

**Step 2: Přidej panel HTML**

Najdi poslední panel (hledej `id="panel-alerts"`). Za jeho uzavírací `</div>` přidej:

```html
<!-- BUG REPORTS -->
<div class="panel" id="panel-bugs">
  <h2>Bug Reporty</h2>

  <!-- Filtry -->
  <div class="search-row" style="margin-bottom:14px">
    <select id="bug-filter-status" class="txt-input" style="width:160px">
      <option value="">Všechny stavy</option>
      <option value="open">🔴 Open</option>
      <option value="in_progress">🟡 In Progress</option>
      <option value="resolved">🟢 Resolved</option>
      <option value="closed">⚫ Closed</option>
    </select>
    <select id="bug-filter-severity" class="txt-input" style="width:160px">
      <option value="">Všechny závažnosti</option>
      <option value="cosmetic">💅 Kosmetická</option>
      <option value="minor">⚠️ Menší</option>
      <option value="critical">🔥 Kritická</option>
    </select>
    <button class="btn" onclick="loadBugReports()">↺ Načíst</button>
    <span id="bug-count" style="font-size:.75rem;color:#707090;margin-left:auto"></span>
  </div>

  <!-- Tabulka -->
  <table id="bug-table">
    <thead>
      <tr>
        <th>Závažnost</th>
        <th>Název</th>
        <th>Hráč</th>
        <th>Sekce</th>
        <th>Datum</th>
        <th>Stav</th>
      </tr>
    </thead>
    <tbody id="bug-tbody"></tbody>
  </table>

  <!-- Detail panel -->
  <div id="bug-detail" style="display:none;margin-top:20px;background:#0e0e1e;border:1px solid rgba(255,255,255,.08);border-radius:6px;padding:18px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <h2 style="margin:0" id="bug-detail-title">Detail reportu</h2>
      <button class="btn btn-sm" onclick="document.getElementById('bug-detail').style.display='none'">✕ Zavřít</button>
    </div>

    <div class="two-col" style="margin-bottom:12px">
      <div>
        <div style="font-size:.7rem;color:#707090;margin-bottom:4px">HRÁČ</div>
        <div id="bd-player" style="font-size:.88rem"></div>
      </div>
      <div>
        <div style="font-size:.7rem;color:#707090;margin-bottom:4px">SEKCE / ČAS</div>
        <div id="bd-meta" style="font-size:.88rem"></div>
      </div>
    </div>

    <div style="margin-bottom:10px">
      <div style="font-size:.7rem;color:#707090;margin-bottom:4px">POPIS</div>
      <div id="bd-description" style="font-size:.85rem;line-height:1.6;background:#141428;padding:10px;border-radius:4px"></div>
    </div>

    <div id="bd-steps-wrap" style="margin-bottom:10px;display:none">
      <div style="font-size:.7rem;color:#707090;margin-bottom:4px">KROKY K REPRODUKCI</div>
      <div id="bd-steps" style="font-size:.85rem;line-height:1.6;background:#141428;padding:10px;border-radius:4px"></div>
    </div>

    <div class="action-row" style="margin-bottom:10px">
      <label>Stav:</label>
      <select id="bd-status-select" class="txt-input" style="width:160px">
        <option value="open">🔴 Open</option>
        <option value="in_progress">🟡 In Progress</option>
        <option value="resolved">🟢 Resolved</option>
        <option value="closed">⚫ Closed</option>
      </select>
    </div>

    <div style="margin-bottom:12px">
      <div style="font-size:.7rem;color:#707090;margin-bottom:4px">ADMIN POZNÁMKA (interní)</div>
      <textarea id="bd-note" class="txt-input" style="width:100%;height:70px" placeholder="Interní poznámka (hráč ji nevidí)..."></textarea>
    </div>

    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button class="btn btn-green" onclick="saveBugChanges()">💾 Uložit změny</button>
      <button class="btn" onclick="prefillBugFixNews()">📰 Vytvořit Bug Fix novinku</button>
      <button class="btn btn-red" onclick="deleteBugReport()">🗑 Smazat report</button>
    </div>
    <div id="bd-msg" class="msg-out"></div>
  </div>
</div>
```

**Step 3: Přidej JavaScript na konec admin.html (před `</script>` uzavírací tag nebo za poslední JS funkci)**

```javascript
// ── BUG REPORTS ──────────────────────────────────────────────────────────────

let _selectedBugId = null;

async function loadBugReports() {
  const status   = document.getElementById('bug-filter-status').value;
  const severity = document.getElementById('bug-filter-severity').value;
  let url = '/admin/bugs?';
  if (status)   url += `status=${status}&`;
  if (severity) url += `severity=${severity}&`;

  const reports = await adminFetch(url);
  if (!reports) return;

  const tbody = document.getElementById('bug-tbody');
  document.getElementById('bug-count').textContent = `${reports.length} reportů`;

  if (!reports.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="color:#707090;text-align:center;padding:20px">Žádné reporty.</td></tr>';
    return;
  }

  const severityBadge = {
    cosmetic: '<span class="badge" style="background:rgba(120,120,120,.2);color:#aaa;border:1px solid rgba(120,120,120,.3)">💅 Kosmetická</span>',
    minor:    '<span class="badge" style="background:rgba(200,170,0,.15);color:#c8a800;border:1px solid rgba(200,170,0,.3)">⚠️ Menší</span>',
    critical: '<span class="badge badge-d">🔥 Kritická</span>',
  };
  const statusBadge = {
    open:        '<span class="badge badge-d">🔴 Open</span>',
    in_progress: '<span class="badge" style="background:rgba(200,170,0,.15);color:#c8a800;border:1px solid rgba(200,170,0,.3)">🟡 In Progress</span>',
    resolved:    '<span class="badge badge-e">🟢 Resolved</span>',
    closed:      '<span class="badge" style="background:rgba(80,80,80,.2);color:#808080;border:1px solid rgba(80,80,80,.3)">⚫ Closed</span>',
  };

  tbody.innerHTML = reports.map(r => `
    <tr style="cursor:pointer" onclick="showBugDetail(${r.id})">
      <td>${severityBadge[r.severity] || r.severity}</td>
      <td><strong>${r.title}</strong></td>
      <td>${r.char_name || '—'} <span style="color:#707090;font-size:.72rem">Lv.${r.char_level || '?'} ${r.char_class || ''}</span></td>
      <td><span style="color:#707090;font-size:.78rem">${r.page_context || '—'}</span></td>
      <td style="color:#707090;font-size:.78rem">${r.created_at ? r.created_at.slice(0,16).replace('T',' ') : '—'}</td>
      <td>${statusBadge[r.status] || r.status}</td>
    </tr>
  `).join('');
}

async function showBugDetail(id) {
  _selectedBugId = id;
  const r = await adminFetch(`/admin/bugs/${id}`);
  if (!r) return;

  document.getElementById('bug-detail-title').textContent = `#${r.id} — ${r.title}`;
  document.getElementById('bd-player').textContent = `${r.char_name || '?'} · Lv.${r.char_level || '?'} ${r.char_class || ''}`;
  document.getElementById('bd-meta').textContent = `${r.page_context || 'neznámá sekce'} · ${r.created_at ? r.created_at.slice(0,16).replace('T',' ') : ''}`;
  document.getElementById('bd-description').textContent = r.description;

  const stepsWrap = document.getElementById('bd-steps-wrap');
  if (r.steps) {
    document.getElementById('bd-steps').textContent = r.steps;
    stepsWrap.style.display = 'block';
  } else {
    stepsWrap.style.display = 'none';
  }

  document.getElementById('bd-status-select').value = r.status;
  document.getElementById('bd-note').value = r.admin_note || '';
  document.getElementById('bd-msg').style.display = 'none';
  document.getElementById('bug-detail').style.display = 'block';
  document.getElementById('bug-detail').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function saveBugChanges() {
  if (!_selectedBugId) return;
  const status = document.getElementById('bd-status-select').value;
  const note   = document.getElementById('bd-note').value.trim();
  const msg    = document.getElementById('bd-msg');

  const [r1, r2] = await Promise.all([
    adminFetch(`/admin/bugs/${_selectedBugId}/status`, 'PATCH', { status }),
    adminFetch(`/admin/bugs/${_selectedBugId}/note`, 'PATCH', { admin_note: note }),
  ]);

  if (r1 && r2) {
    msg.textContent = '✓ Uloženo'; msg.style.background = 'rgba(50,200,80,.08)'; msg.style.color = '#80d080';
    msg.style.display = 'block';
    loadBugReports();
  } else {
    msg.textContent = '✗ Chyba při ukládání'; msg.style.background = 'rgba(200,50,50,.1)'; msg.style.color = '#d08080';
    msg.style.display = 'block';
  }
}

async function deleteBugReport() {
  if (!_selectedBugId) return;
  if (!confirm(`Smazat report #${_selectedBugId}?`)) return;
  const r = await adminFetch(`/admin/bugs/${_selectedBugId}`, 'DELETE');
  if (r) {
    document.getElementById('bug-detail').style.display = 'none';
    _selectedBugId = null;
    loadBugReports();
  }
}

function prefillBugFixNews() {
  // Přepni na tab Novinky a prefilluj formulář
  switchTab('news');
  loadAdminNews();
  setTimeout(() => {
    const titleEl = document.getElementById('news-title');
    const typeEl  = document.getElementById('news-type');
    const bugTitle = document.getElementById('bug-detail-title').textContent.replace(/^#\d+ — /, '');
    if (titleEl) titleEl.value = `[Bug Fix] ${bugTitle}`;
    if (typeEl)  typeEl.value = 'hotfix';
    document.getElementById('news-form')?.scrollIntoView({ behavior: 'smooth' });
  }, 300);
}
```

**Step 4: Ověř admin panel**

Otevři `admin.html` v prohlížeči:
- Tab "🐛 Bug Reporty" viditelný
- Filtery fungují
- Tabulka se načte
- Klik na řádek otevře detail
- Změna stavu + uložení funguje

**Step 5: Commit**

```bash
git add frontend/admin.html
git commit -m "feat: admin panel — tab Bug Reporty s filtraci, detailem a workflow"
```

---

## Task 8: Finální integrace a smoke test

**Step 1: Spusť server**
```bash
cd backend && uvicorn main:app --reload --port 8000
```

**Step 2: Smoke test — hráčský flow**
1. Přihlas se do hry
2. Klikni na 🐛 v topbaru → modal se otevře
3. Vyplň: "Test bug", "Toto je testovací popis bugu", severity: Menší
4. Odešli → toast "Díky za report!" se zobrazí
5. Zkontroluj DB: `SELECT * FROM bug_reports;` (nebo přes admin panel)

**Step 3: Smoke test — admin flow**
1. Otevři `admin.html`
2. Klikni na "🐛 Bug Reporty"
3. Klikni "↺ Načíst" → report se zobrazí v tabulce
4. Klikni na řádek → detail panel se otevře
5. Změň stav na "In Progress", přidej poznámku, ulož
6. Klikni "📰 Vytvořit Bug Fix novinku" → přepne na Novinky tab s prefillovaným titulkem

**Step 4: Final commit**
```bash
git add -A
git commit -m "feat: Bug Report System — kompletní implementace"
```

---

## Poznámky pro implementátora

- `adminFetch` je helper v `admin.html` — používej ho pro všechna volání
- `char_class` sloupec je na `Character` modelu — zkontroluj přesný název atributu (může být `char_class` nebo `character_class`)
- `GameNews.news_type` je string field — hodnota `hotfix` existuje, použijeme ji pro Bug Fix novinky (žádná schema změna)
- Pořadí scriptů v game.html: `bugs.js` vlož PŘED `main.js`
