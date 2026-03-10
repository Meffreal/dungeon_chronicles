# Fáze 1: Topbar & Navigace — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Topbar a navigace musí vypadat jako RPG ihned při vstupu — class-colored avatar border, runic nav active stav, ornamentální linka, notif bell pulse.

**Architecture:** Převážně CSS-only (layout.css). 2 malé JS zásahy: `ui.js` pro class border na avataru, `notifications.js` pro has-notif class. Žádné nové soubory, žádné nové závislosti.

**Tech Stack:** Vanilla CSS (custom properties, animations, clip-path), Vanilla JS (1–2 řádky per soubor)

---

## Task 1: Nav hover/active — crimson glow + runic aktivní stav

**Files:**
- Modify: `frontend/css/layout.css` (řádky 94–131)

**Co se mění:** Nav tlačítka stále používají starou modrou (`rgba(30,127,184,..)`). Nahradíme crimson/ember paletou + přidáme runic `::after` ornament pro aktivní stav.

**Step 1: Nahraď `.nav-btn:hover` a `.nav-btn.active` (řádky 101–115)**

```css
.nav-btn:hover{
  background:rgba(192,57,43,.1);color:var(--text);
  border-left-color:rgba(192,57,43,.4);
  box-shadow:inset 2px 0 8px rgba(192,57,43,.08);
}
.nav-btn:hover .ni{transform:scale(1.15);filter:drop-shadow(0 0 4px rgba(230,126,34,.5));}
.nav-btn.active{
  background:rgba(192,57,43,.14);color:var(--accent2);
  border-left-color:var(--accent);
  box-shadow:inset 2px 0 12px rgba(192,57,43,.12),-1px 0 8px rgba(192,57,43,.2);
}
.nav-btn.active .ni{transform:scale(1.1);filter:drop-shadow(0 0 5px rgba(230,126,34,.6));}
.nav-btn.active::after{
  content:'✦';position:absolute;right:8px;top:50%;transform:translateY(-50%);
  font-size:0.45rem;color:var(--accent);opacity:.7;
  animation:rune-pulse 2s ease-in-out infinite;
}
@keyframes rune-pulse{0%,100%{opacity:.4;text-shadow:none;}50%{opacity:.9;text-shadow:0 0 6px var(--accent);}}
```

**Step 2: Nahraď `.nav-group` a `.nav-group-header` (řádky 117–128)**

```css
.nav-group{border-bottom:1px solid rgba(192,57,43,.1);}
.nav-group-header{display:flex;align-items:center;gap:7px;width:100%;padding:7px 11px;background:none;border:none;border-left:2px solid transparent;cursor:pointer;transition:all .15s;text-align:left;color:var(--text3);font-family:'Cinzel',serif;font-size:0.63rem;letter-spacing:2px;text-transform:uppercase;}
.nav-group-header:hover{color:var(--text2);background:rgba(192,57,43,.07);border-left-color:rgba(192,57,43,.2);}
.nav-group-header.open{color:var(--accent2);}
```

**Step 3: Oprav `.stats-title` (řádek 56) — stará modrá border**

Najdi `.stats-title` a nahraď:
```css
.stats-title{font-family:'Cinzel',serif;font-size:0.67rem;letter-spacing:var(--ls-wider);text-transform:uppercase;color:var(--text3);padding:3px 0 4px;border-bottom:1px solid rgba(192,57,43,.2);margin-bottom:3px;}
```

**Step 4: Oprav `.ov-stat-cell` (řádek 86) — stará modrá**

```css
.ov-stat-cell{display:flex;flex-direction:column;align-items:center;background:rgba(192,57,43,.06);border:1px solid var(--border2);border-radius:4px;padding:6px 4px;text-align:center;gap:2px;}
```

**Step 5: Commit**

```bash
git add frontend/css/layout.css
git commit -m "style: nav crimson glow hover/active + runic rune indicator, fix remaining blue in lpanel"
```

---

## Task 2: Topbar ornament + avatar class-colored border

**Files:**
- Modify: `frontend/css/layout.css` (topbar sekce)
- Modify: `frontend/js/ui.js` (funkce `updateUI`, řádek ~485)

**Co se mění:**
- Topbar dostane center ornament (malý diamond ✦ uprostřed spodní zlaté linky)
- `.tb-avatar` dostane `data-cls` atribut a CSS border v barvě třídy

**Step 1: Přidej `.topbar::before` za `.topbar::after` (layout.css)**

Za `.topbar::after { ... }` přidej:
```css
.topbar::before{
  content:'✦';
  position:absolute;bottom:-5px;left:50%;transform:translateX(-50%);
  font-size:0.5rem;color:var(--gold2);
  text-shadow:0 0 8px rgba(212,160,48,.8);
  z-index:1;line-height:1;pointer-events:none;
}
```

**Step 2: Přidej CSS pro class-colored avatar (layout.css)**

Za `.tb-avatar { ... }` přidej:
```css
.tb-avatar[data-cls="warrior"]{border-color:var(--cls-warrior);box-shadow:0 0 8px rgba(200,150,90,.35),inset 0 0 4px rgba(200,150,90,.1);}
.tb-avatar[data-cls="mage"]   {border-color:var(--cls-mage);   box-shadow:0 0 8px rgba(80,144,208,.35),inset 0 0 4px rgba(80,144,208,.1);}
.tb-avatar[data-cls="ranger"] {border-color:var(--cls-ranger); box-shadow:0 0 8px rgba(74,173,106,.35),inset 0 0 4px rgba(74,173,106,.1);}
```

**Step 3: Přidej `data-cls` do `updateUI()` (ui.js, řádek ~485)**

Najdi řádek `set('tb-avatar', CLS_E[cl]);` a za něj přidej:
```javascript
const avatarEl = document.getElementById('tb-avatar');
if (avatarEl) avatarEl.dataset.cls = cl;
```

**Step 4: Commit**

```bash
git add frontend/css/layout.css frontend/js/ui.js
git commit -m "style: topbar gold ornament + avatar class-colored border (warrior/mage/ranger)"
```

---

## Task 3: Level badge shield styl + notif bell pulse

**Files:**
- Modify: `frontend/css/layout.css` (tb-lvl sekce)
- Modify: `frontend/js/notifications.js` (funkce `updateNotifBadge`, řádek 12)

**Co se mění:**
- `.tb-lvl` dostane tvar připomínající středověký štítek (clip-path + gradient)
- Notif bell dostane `has-notif` CSS class a pulse animaci při nepřečtených notifikacích

**Step 1: Nahraď `.tb-lvl` (layout.css)**

Najdi `.tb-lvl` (řádek ~10) a nahraď:
```css
.tb-lvl{
  background:linear-gradient(135deg,#6a1010,var(--accent));
  color:#f0d0b0;font-family:'Cinzel',serif;font-size:0.62rem;font-weight:700;
  padding:2px 7px 3px;
  clip-path:polygon(6px 0%,100% 0%,100% 70%,50% 100%,0% 70%,0% 0%);
  letter-spacing:.5px;min-width:36px;text-align:center;
  box-shadow:0 0 8px rgba(192,57,43,.4);
}
```

**Step 2: Přidej `.tb-btn.has-notif` animaci (layout.css)**

Za `.tb-btn.dng:hover { ... }` přidej:
```css
.tb-btn.has-notif{
  border-color:rgba(192,57,43,.5);color:var(--accent2);
  animation:notif-pulse 2.5s ease-in-out infinite;
}
@keyframes notif-pulse{
  0%,100%{box-shadow:0 0 0 rgba(192,57,43,0);}
  50%{box-shadow:0 0 10px rgba(192,57,43,.5),0 0 20px rgba(192,57,43,.2);}
}
```

**Step 3: Přidej `has-notif` class do `updateNotifBadge()` (notifications.js)**

Najdi funkci `updateNotifBadge(count)` (řádek 12) a nahraď:
```javascript
function updateNotifBadge(count) {
  const badge = document.getElementById('notif-badge');
  const bell  = document.getElementById('notif-bell');
  if (!badge) return;
  if (count > 0) {
    badge.textContent = count > 9 ? '9+' : count;
    badge.style.display = 'flex';
    if (bell) bell.classList.add('has-notif');
  } else {
    badge.style.display = 'none';
    if (bell) bell.classList.remove('has-notif');
  }
}
```

**Step 4: Commit**

```bash
git add frontend/css/layout.css frontend/js/notifications.js
git commit -m "style: level badge shield clip-path + notif bell pulse animation"
```

---

## Shrnutí Fáze 1

3 tasky, 2 soubory CSS + 2 soubory JS (po 2–3 řádcích každý):

1. **Nav crimson** — hover/active glow + runic `✦` rune indicator, fix ov-stat-cell a stats-title
2. **Topbar ornament + avatar class border** — gold diamond ornament na linku, class-colored avatar frame
3. **Level shield badge + notif pulse** — clip-path štítek, pulsující notif bell

Žádné nové soubory. Žádné závislosti.
