# Brutal Gothic Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Přepsat frontend Dungeon Chronicles z "Obsidian Codex" na "Brutal Gothic" styl — červená + ocelová šedá, ostré hrany, SVG ikony, full accessibility pass.

**Architecture:** Design-system.css se přepíše jako základ (všechny ostatní CSS soubory z něj dědí tokeny). Poté layout, komponenty, HTML a minimální JS v ui.js. theme.css jako poslední — remapuje zbývající staré tokeny.

**Tech Stack:** Vanilla CSS custom properties, HTML5, Vanilla JS, Lucide SVG icons (inline), Google Fonts CDN (Cinzel + Rajdhani + Crimson Text)

**Spec:** `docs/superpowers/specs/2026-03-23-brutal-gothic-redesign-design.md`

---

## Kritická pravidla (přečíst před implementací)

- `id="nav-{page}"` na nav buttonech je NEMĚNNÉ — `showPage()` v `ui.js:295` to vyžaduje
- `id="ng-{group}"`, `id="ngh-{group}"`, `id="ngbody-{group}"` jsou NEMĚNNÉ
- `openModal(id)` / `closeModal(id)` přes `.open` CSS class — NEMĚNIT na `style.display`
- `toast(msg, type, dur)` typy: POUZE `'s'` / `'e'` / `'i'`
- JS script pořadí v `game.html` je KRITICKÉ — nepřehazovat
- `updateUI(char)` se volá po každé akci — NEMĚNIT signaturu
- Stará CSS třída `.btn` se ZACHOVÁVÁ jako alias pro `.btn-primary` (theme.css ji používá)

---

## Mapa souborů (v pořadí implementace)

| Task | Soubor | Akce | Poznámka |
|------|--------|------|----------|
| 1 | `frontend/css/design-system.css` | **Přepsat** | Základ — dělat jako první |
| 2 | `frontend/css/base.css` | **Aktualizovat** | Fonty, focus ring, skip link |
| 3 | `frontend/game.html` | **Aktualizovat** | Font imports, skip link, Lucide SVG ikony, ARIA |
| 4 | `frontend/css/layout.css` | **Přepsat** | Grid, topbar, sidebar, tablet fly-out, mobile |
| 5 | `frontend/css/components.css` | **Přepsat** | Buttony, karty, modaly, toasty |
| 6 | `frontend/js/ui.js` | **Aktualizovat** | aria-current, toast ARIA, hamburger, aria-expanded |
| 7 | `frontend/css/physical.css` | **Zjednodušit** | Jen grain noise (z-index: 1) |
| 8 | `frontend/css/combat.css` | **Aktualizovat** | HP/MP bary |
| 8 | `frontend/css/animations.css` | **Aktualizovat** | Reduced-motion selektor |
| 9 | `frontend/css/assets.css` | **Aktualizovat** | Zachovat rarity, remapovat tokeny |
| 9 | `frontend/css/quest.css` | **Aktualizovat** | Remapovat staré tokeny |
| 9 | `frontend/css/inventory.css` | **Aktualizovat** | Remapovat staré tokeny |
| 10 | `frontend/css/textures.css` | **Aktualizovat** | Odstranit co koliduje |
| 10 | `frontend/css/ui-enhance.css` | **Aktualizovat** | Odstranit co koliduje |
| 11 | `frontend/css/theme.css` | **Aktualizovat** | Remapovat staré tokeny — dělat jako poslední |

---

## Task 1: Nový design-system.css

**Files:**
- Modify: `frontend/css/design-system.css`

Kompletní přepis tokenů. Zachovat `--z-topbar`, `--z-flash`, `--z-modal`, `--z-toast`.
Přidat compat aliasy pro staré tokeny, které `theme.css` stále používá.

- [ ] **Krok 1: Přepsat design-system.css**

```css
/* ═══════════════════════════════════════════════════════════════════════════
   BRUTAL GOTHIC — Design System Foundation
   Dungeon Chronicles v0.8
   ═══════════════════════════════════════════════════════════════════════════ */

/* Fonty se načítají v game.html — zde jen definice proměnných */

:root {

  /* ── BACKGROUNDS ─────────────────────────────────────────────────────────── */
  --clr-void:      #080808;
  --clr-base:      #111111;
  --clr-surface:   #1a1a1a;
  --clr-raised:    #222222;
  --clr-border:    #2e2e2e;

  /* ── PRIMÁRNÍ ACCENT — Krev ──────────────────────────────────────────────── */
  --clr-blood:     #cc0000;
  --clr-crimson:   #e61919;
  --clr-ember:     #ff4d4d;

  /* ── TEXT ────────────────────────────────────────────────────────────────── */
  --clr-text:      #f0f0f0;
  --clr-muted:     #999999;
  --clr-faint:     #666666;   /* POUZE dekorativní — nesplňuje AA pro malý text */

  /* ── STATUSY ─────────────────────────────────────────────────────────────── */
  --clr-success:   #22c55e;
  --clr-warning:   #f59e0b;
  --clr-danger:    #ff3333;   /* sémantická chyba — odlišná od --clr-blood */

  /* ── TYPOGRAFIE ──────────────────────────────────────────────────────────── */
  --font-display:  'Cinzel', serif;
  --font-body:     'Rajdhani', sans-serif;
  --font-lore:     'Crimson Text', Georgia, serif;

  /* ── TYPOGRAFICKÁ ŠKÁLA ──────────────────────────────────────────────────── */
  --fs-xs:   0.75rem;
  --fs-sm:   0.875rem;
  --fs-base: 1rem;
  --fs-lg:   1.125rem;
  --fs-xl:   1.25rem;
  --fs-2xl:  1.5rem;
  --fs-3xl:  2rem;

  /* ── SPACING (4px base grid) ─────────────────────────────────────────────── */
  --sp-1:   4px;
  --sp-2:   8px;
  --sp-3:  12px;
  --sp-4:  16px;
  --sp-6:  24px;
  --sp-8:  32px;
  --sp-12: 48px;
  --sp-16: 64px;

  /* ── BORDER RADIUS — ostré hrany ────────────────────────────────────────── */
  --radius-sm: 2px;
  --radius-md: 4px;
  --radius-lg: 6px;

  /* ── TRANSITIONS ─────────────────────────────────────────────────────────── */
  --transition-fast: 120ms ease-out;
  --transition-mid:  200ms ease-out;
  --transition-slow: 300ms ease-out;

  /* ── Z-INDEX STACK (neměnit!) ────────────────────────────────────────────── */
  --z-topbar: 30;
  --z-flash:  50;
  --z-modal:  100;
  --z-toast:  200;

  /* ══════════════════════════════════════════════════════════════════════════
     COMPAT ALIASY — staré tokeny mapované na nový systém
     Používá je theme.css, nemazat dokud není theme.css přepsán
     ══════════════════════════════════════════════════════════════════════════ */
  --clr-obsidian:    var(--clr-base);
  --clr-slate:       var(--clr-surface);
  --clr-stone:       var(--clr-raised);
  --clr-ash:         var(--clr-border);
  --clr-gold:        var(--clr-blood);
  --clr-gold-bright: var(--clr-crimson);
  --clr-soul:        #2563eb;
  --clr-soul-bright: #3b82f6;
  --clr-poison:      var(--clr-success);
  /* POZOR: --clr-ember NESMÍ být přepsáno — používá ho focus ring a hover */
  /* Pro staré kód které použily ember jako warning: */
  --clr-ember-compat: var(--clr-warning);

  --surface:   var(--clr-surface);
  --panel2:    var(--clr-raised);
  --frame1:    rgba(204, 0, 0, 0.08);
  --frame2:    rgba(204, 0, 0, 0.15);
  --frame3:    rgba(204, 0, 0, 0.25);
  --border2:   1px solid var(--clr-border);
  --border3:   1px solid rgba(204, 0, 0, 0.15);
  --border-rune:        1px solid rgba(204, 0, 0, 0.2);
  --border-rune-active: 1px solid rgba(204, 0, 0, 0.6);

  --accent:  var(--clr-blood);
  --accent2: var(--clr-crimson);
  --text1:   rgba(240, 240, 240, 0.5);
  --text2:   var(--clr-muted);
  --text3:   var(--clr-faint);
  --green:   var(--clr-success);
  --green2:  #4ade80;
  --gold2:   var(--clr-text);
  --ls-base:  0.01em;
  --ls-wide:  0.05em;
  --ls-wider: 0.1em;
  --gold-rgb: 204, 0, 0;

  --glow-gold:  0 0 8px rgba(204,0,0,0.4);
  --glow-blood: 0 0 8px rgba(204,0,0,0.5);
  --glow-soul:  0 0 8px rgba(37,99,235,0.4);
  --glow-ember: 0 0 8px rgba(245,158,11,0.4);

  /* ── SPACE aliasy ────────────────────────────────────────────────────────── */
  --space-1:   var(--sp-1);
  --space-2:   var(--sp-2);
  --space-3:   var(--sp-3);
  --space-4:   var(--sp-4);
  --space-6:   var(--sp-6);
  --space-8:   var(--sp-8);
  --space-12:  var(--sp-12);
  --space-16:  var(--sp-16);
}
```

- [ ] **Krok 2: Otevřít browser, ověřit v DevTools**

Otevřít `http://localhost:8000/game.html`, DevTools → Elements → `<html>` → Computed → ověřit:
- `--clr-blood` = `#cc0000`
- `--clr-surface` = `#1a1a1a`
- `--font-body` obsahuje Rajdhani
- Stránka se nezhroutí (zobrazí se, i když vypadá jinak)

- [ ] **Krok 3: Commit**

```bash
git add frontend/css/design-system.css
git commit -m "feat: new Brutal Gothic design-system tokens"
```

---

## Task 2: base.css — fonty, focus ring, skip link

**Files:**
- Modify: `frontend/css/base.css`

- [ ] **Krok 1: Přečíst aktuální base.css (prvních 80 řádků)**

```bash
# Zkontroluj existující reset a font-size deklarace
head -80 frontend/css/base.css
```

- [ ] **Krok 2: Aktualizovat font-size, focus ring, skip link**

Najít a nahradit sekci `body` a přidat na začátek base.css:

```css
/* ── SKIP LINK (accessibility — první element v <body>) ─────────────────── */
.skip-link {
  position: absolute;
  top: -100%;
  left: 8px;
  z-index: 9999;
  background: var(--clr-blood);
  color: #fff;
  padding: 8px 16px;
  font-family: var(--font-body);
  font-size: var(--fs-sm);
  font-weight: 600;
  text-decoration: none;
  border-radius: var(--radius-md);
}
.skip-link:focus {
  top: 8px;
}
```

Nahradit v sekci `body`:
- `font-size` na `var(--fs-base)` (1rem)
- `font-family` na `var(--font-body)`
- `background` na `var(--clr-void)`
- `color` na `var(--clr-text)`

Přidat globální focus ring (na konec base.css):
```css
/* ── FOCUS RING (accessibility) ────────────────────────────────────────── */
:focus-visible {
  outline: 2px solid var(--clr-ember);
  outline-offset: 3px;
  border-radius: var(--radius-sm);
}
:focus:not(:focus-visible) {
  outline: none;
}

/* ── REDUCED MOTION ─────────────────────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

- [ ] **Krok 3: Ověřit v browseru**

- Fokusovat klávesou Tab na první element → červený focus ring viditelný
- Zkontrolovat font body v DevTools → Rajdhani (pokud je Rajdhani načtený)

- [ ] **Krok 4: Commit**

```bash
git add frontend/css/base.css
git commit -m "feat: base.css — Rajdhani font, focus ring, skip link, reduced motion"
```

---

## Task 3: game.html — font imports, skip link, ARIA, SVG ikony

**Files:**
- Modify: `frontend/game.html`

Toto je největší HTML změna — nahrazení emoji ikon za Lucide SVG, přidání skip linku, ARIA atributů a nové font imports.

- [ ] **Krok 1: Aktualizovat font imports v `<head>`**

Nahradit stávající `@import` / font link (řádek 8 v design-system.css to dělá — zkontrolovat zda game.html má vlastní):
```html
<!-- Nahradit stávající Google Fonts link -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Rajdhani:wght@400;500;600;700&family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
```

- [ ] **Krok 2: Přidat skip link jako první element v `<body>`**

```html
<body>
<a href="#main-content" class="skip-link">Přeskočit na obsah</a>
<!-- zbytek topbaru... -->
```

- [ ] **Krok 3: Nahradit emoji v topbaru za SVG / text**

```html
<!-- Topbar akční buttony — přidat aria-label -->
<button class="tb-btn" id="notif-bell" onclick="showPage('notifications')"
        aria-label="Notifikace" title="Notifikace" style="position:relative">
  <!-- ponechat existující badge span -->
</button>
<button class="tb-btn" onclick="openBugReportModal()"
        aria-label="Nahlásit chybu" title="Report a Bug">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       stroke-width="2" aria-hidden="true">
    <path d="M12 2a3 3 0 0 1 3 3v1h2a2 2 0 0 1 2 2v2a2 2 0 0 1-1 1.73l.5 2.27H18l-.5-2H6.5L6 13H4.5l.5-2.27A2 2 0 0 1 4 9V8a2 2 0 0 1 2-2h2V5a3 3 0 0 1 3-3z"/>
    <path d="M9 11v4M15 11v4M3 9h18"/>
  </svg>
</button>
<button class="tb-btn" onclick="refreshChar()" aria-label="Obnovit postavu" title="Obnovit">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       stroke-width="2" aria-hidden="true">
    <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>
    <path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>
    <path d="M3 21v-5h5"/>
  </svg>
</button>
```

- [ ] **Krok 4: Přidat `id="main-content"` na hlavní oblast**

```html
<div class="main" id="main-content">
```

- [ ] **Krok 5: Obalit sidebar do `<nav>` s ARIA**

```html
<nav class="lpanel" aria-label="Hlavní navigace">
  <!-- veškerý obsah lpanel -->
</nav>
```

- [ ] **Krok 6: Nahradit emoji ikony v navigaci za Lucide SVG**

Pro KAŽDÝ `<button class="nav-btn">` nahradit `<span class="ni">EMOJI</span>` za inline Lucide SVG.
Vzorový snippet (opakovat pro všechny položky):

```html
<!-- PŘED -->
<button class="nav-btn active" id="nav-overview" onclick="showPage('overview')">
  <span class="ni">🏤</span> City Hub
</button>

<!-- PO -->
<button class="nav-btn active" id="nav-overview" onclick="showPage('overview')"
        aria-label="City Hub">
  <svg class="nav-icon" width="16" height="16" viewBox="0 0 24 24" fill="none"
       stroke="currentColor" stroke-width="2" aria-hidden="true">
    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
    <polyline points="9,22 9,12 15,12 15,22"/>
  </svg>
  City Hub
</button>
```

Kompletní SVG kódy pro všechny nav položky (Lucide paths):

| id | Text | SVG path(s) |
|----|------|-------------|
| `nav-overview` | City Hub | `<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9,22 9,12 15,12 15,22"/>` |
| `nav-quests` | Quests | `<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14,2 14,8 20,8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10,9 9,9 8,9"/>` |
| `nav-arena` | Arena | `<path d="M14.5 10c-.83 0-1.5-.67-1.5-1.5v-5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5v5c0 .83-.67 1.5-1.5 1.5z"/><path d="M20.5 10H19V8.5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/><path d="M9.5 14.5c.83 0 1.5.67 1.5 1.5v5c0 .83-.67 1.5-1.5 1.5S8 21.83 8 21v-5c0-.83.67-1.5 1.5-1.5z"/><path d="M3.5 14H5v1.5c0 .83-.67 1.5-1.5 1.5S2 16.33 2 15.5 2.67 14 3.5 14z"/><path d="M14 14h-4"/><path d="M14 10v4"/><path d="M10 10v4"/>` |
| `nav-boss` | World Boss | `<circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/><path d="M9 9l1.5 1.5M15 9l-1.5 1.5M9 15l1.5-1.5M15 15l-1.5-1.5"/>` |
| `nav-dungeons` | Dungeons | `<path d="M13 4h3a2 2 0 0 1 2 2v14"/><path d="M2 20h3"/><path d="M13 20h9"/><path d="M10 12v.01"/><path d="M13 4.562v16.157a1 1 0 0 1-1.242.97L4 20V5.562a2 2 0 0 1 1.515-1.94l4-1A2 2 0 0 1 13 4.561z"/>` |
| `nav-equipment` | Equipment | `<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>` |
| `nav-inventory` | Inventory | `<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>` |
| `nav-subclass` | Specialization | `<line x1="6" y1="3" x2="6" y2="15"/><path d="M18 3a3 3 0 0 0-3 3v12a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3z"/><path d="M6 15a3 3 0 1 0 6 0 3 3 0 0 0-6 0z"/>` |
| `nav-prestige` | Prestige | `<circle cx="12" cy="8" r="6"/><path d="M15.477 12.89L17 22l-5-3-5 3 1.523-9.11"/>` |
| `nav-attunement` | Attunement | `<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>` |
| `nav-bloodline` | Bloodline | `<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>` |
| `nav-guild` | Guild | `<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>` |
| `nav-faction` | Faction | `<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/>` |
| `nav-market` | Market | `<path d="M3 9l1-7h16l1 7"/><path d="M3 9H21"/><path d="M3 9a2 2 0 0 0 2 2 2 2 0 0 0 2-2 2 2 0 0 0 2 2 2 2 0 0 0 2-2 2 2 0 0 0 2 2 2 2 0 0 0 2-2"/><path d="M5 22H19"/><path d="M5 11v11"/><path d="M19 11v11"/><path d="M9 22v-4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v4"/>` |
| `nav-shop` | Shop | `<path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/>` |
| `nav-hall` | Hall of Fallen | `<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><line x1="9" y1="22" x2="9" y2="12"/><line x1="15" y1="22" x2="15" y2="12"/><line x1="3" y1="9" x2="21" y2="9"/>` |
| `nav-achievements` | Achievements | `<circle cx="12" cy="8" r="6"/><path d="M15.477 12.89L17 22l-5-3-5 3 1.523-9.11"/>` |
| `nav-weekly` | Weekly | `<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>` |
| `nav-season` | Season | `<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>` |
| `nav-world-events` | World Events | `<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>` |
| `nav-crystals` | Blood Crystals | `<polygon points="6 3 18 3 22 9 12 22 2 9"/><line x1="12" y1="22" x2="12" y2="9"/><line x1="2" y1="9" x2="22" y2="9"/>` |
| `nav-support` | About the Game | `<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>` |
| `nav-account` | Správa účtu | `<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>` |

- [ ] **Krok 7: Aktualizovat nav-group headers — nahradit emoji za text label**

```html
<!-- PŘED -->
<button class="nav-group-header" id="ngh-combat" onclick="toggleNavGroup('combat')">
  ⚔️ Combat
</button>

<!-- PO -->
<button class="nav-group-header" id="ngh-combat" onclick="toggleNavGroup('combat')"
        aria-expanded="true">
  Combat
</button>
```

- [ ] **Krok 8: Ověřit v browseru**

- Navigace zobrazuje SVG ikony místo emoji
- Tab navigace prochází skrz nav položky
- DevTools → Accessibility tree → nav má label "Hlavní navigace"

- [ ] **Krok 9: Commit**

```bash
git add frontend/game.html
git commit -m "feat: game.html — Lucide SVG nav icons, skip link, ARIA labels, font imports"
```

---

## Task 4: Přepsat layout.css

**Files:**
- Modify: `frontend/css/layout.css`

Kompletní přepis — nový topbar (56px, červené akcenty), sidebar (240px, section labels), grid layout, tablet a mobile breakpoints.

- [ ] **Krok 1: Přepsat layout.css**

```css
/* ═══════════════════════════════════════════════════════════════════════════
   BRUTAL GOTHIC — Layout
   Topbar · Sidebar · Grid · XP Strip · Mobile
   ═══════════════════════════════════════════════════════════════════════════ */

/* ── TOPBAR ──────────────────────────────────────────────────────────────── */
.topbar {
  height: 56px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  padding: 0 var(--sp-4);
  background: var(--clr-base);
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
  border-bottom: 1px solid var(--clr-border);
  box-shadow: 0 1px 0 var(--clr-blood), 0 4px 16px rgba(0,0,0,0.5);
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: var(--z-topbar);
}

.tb-logo {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--fs-sm);
  color: var(--clr-text);
  letter-spacing: 0.15em;
  text-transform: uppercase;
  white-space: nowrap;
  text-shadow: 0 0 40px rgba(204,0,0,0.3);
  flex-shrink: 0;
}
.tb-sep {
  width: 1px;
  height: 24px;
  background: var(--clr-border);
  flex-shrink: 0;
}
.topbar-divider {
  width: 1px;
  height: 24px;
  background: var(--clr-border);
}
.tb-char {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  cursor: pointer;
}
.tb-avatar {
  width: 36px;
  height: 36px;
  background: var(--clr-surface);
  border: 2px solid var(--clr-blood);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  flex-shrink: 0;
}
.tb-avatar[data-cls="warrior"] { border-color: #c8965a; }
.tb-avatar[data-cls="mage"]    { border-color: #5090d0; }
.tb-avatar[data-cls="ranger"]  { border-color: #4aad6a; }
/* Frame overrides — zachováme existující data-frame logiku */
.tb-avatar[data-frame="bronze"]   { border-color: #cd7f32; }
.tb-avatar[data-frame="silver"]   { border-color: #b0b8c8; }
.tb-avatar[data-frame="gold"]     { border-color: #d4a030; }
.tb-avatar[data-frame="arcane"]   { border-color: #8850c0; }
.tb-avatar[data-frame="ruby"]     { border-color: #c03050; }
.tb-avatar[data-frame="legendary"]{ border-color: #d07020; }
.tb-avatar[data-frame^="prestige-"]{ border-color: #a060d8; }
.tb-name {
  font-family: var(--font-display);
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--clr-text);
  letter-spacing: 0.05em;
}
.tb-meta { display: flex; align-items: center; gap: var(--sp-1); }
.tb-lvl {
  background: var(--clr-blood);
  color: #fff;
  font-family: var(--font-body);
  font-size: 0.7rem;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  letter-spacing: 0.05em;
  min-width: 32px;
  text-align: center;
}
.tb-cls {
  color: var(--clr-muted);
  font-size: var(--fs-xs);
  font-family: var(--font-body);
}
.tb-gold {
  display: flex;
  align-items: center;
  gap: var(--sp-1);
  font-family: var(--font-body);
  font-weight: 600;
  font-size: var(--fs-sm);
  color: var(--clr-text);
  font-variant-numeric: tabular-nums;
}
.tb-crystals {
  display: flex;
  align-items: center;
  gap: var(--sp-1);
  font-family: var(--font-body);
  font-size: var(--fs-sm);
  color: #a78bfa;
}
.tb-online {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  padding: 0 var(--sp-2);
  flex-shrink: 0;
}
.tb-online-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--clr-success);
  box-shadow: 0 0 6px var(--clr-success);
  flex-shrink: 0;
  animation: online-pulse 2s ease-in-out infinite;
}
.tb-online-count {
  font-family: var(--font-body);
  font-size: var(--fs-xs);
  font-weight: 600;
  color: var(--clr-success);
  letter-spacing: 0.05em;
}
@keyframes online-pulse {
  0%,100% { box-shadow: 0 0 4px var(--clr-success); }
  50%     { box-shadow: 0 0 10px var(--clr-success), 0 0 20px rgba(34,197,94,0.4); }
}
/* Quest chip */
.tb-quest-chip {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  background: rgba(34,197,94,0.1);
  border: 1px solid rgba(34,197,94,0.3);
  cursor: pointer;
  font-family: var(--font-body);
  font-size: var(--fs-xs);
  font-weight: 600;
  color: var(--clr-success);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  transition: all var(--transition-fast);
}
.tb-quest-chip:hover { background: rgba(34,197,94,0.18); border-color: rgba(34,197,94,0.6); }
.tb-quest-chip.collecting { background: rgba(245,158,11,0.1); border-color: rgba(245,158,11,0.4); color: var(--clr-warning); }
.tb-quest-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--clr-success);
  box-shadow: 0 0 5px var(--clr-success);
  animation: online-pulse 1.5s ease-in-out infinite;
}
/* Rank chip */
.tb-rank-chip {
  display: flex; align-items: center; gap: 5px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  background: rgba(167,139,250,0.08);
  border: 1px solid rgba(167,139,250,0.25);
  cursor: pointer;
  font-family: var(--font-body);
  font-size: var(--fs-xs);
  font-weight: 600;
  color: #a78bfa;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  transition: all var(--transition-fast);
}
.tb-rank-chip:hover { background: rgba(167,139,250,0.16); }
/* Buff chip */
.tb-buff-chip {
  display: flex; align-items: center; gap: 5px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  background: rgba(245,158,11,0.08);
  border: 1px solid rgba(245,158,11,0.25);
  cursor: pointer;
  font-family: var(--font-body);
  font-size: var(--fs-xs);
  font-weight: 600;
  color: var(--clr-warning);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  transition: all var(--transition-fast);
  position: relative;
}
.tb-buff-chip:hover { background: rgba(245,158,11,0.16); }
.tb-buff-dropdown {
  display: none;
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  background: var(--clr-surface);
  border: 1px solid var(--clr-border);
  border-radius: var(--radius-md);
  box-shadow: 4px 4px 0 rgba(0,0,0,0.6);
  min-width: 200px;
  z-index: 40;
  padding: var(--sp-2);
}
.tb-buff-dropdown.open { display: block; }
/* Topbar action buttons */
.tb-actions { display: flex; gap: var(--sp-1); flex-shrink: 0; }
.tb-btn {
  background: transparent;
  border: 1px solid var(--clr-border);
  color: var(--clr-muted);
  padding: 6px 10px;
  min-height: 36px;
  border-radius: var(--radius-sm);
  font-family: var(--font-body);
  font-size: var(--fs-xs);
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  cursor: pointer;
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  gap: var(--sp-1);
}
.tb-btn:hover { border-color: var(--clr-blood); color: var(--clr-ember); }
.tb-btn:active { transform: scale(0.95); }
.tb-btn.dng { border-color: rgba(204,0,0,0.3); color: var(--clr-muted); }
.tb-btn.dng:hover { border-color: var(--clr-crimson); color: var(--clr-crimson); }
.tb-btn.has-notif {
  border-color: rgba(204,0,0,0.5);
  color: var(--clr-ember);
  animation: notif-pulse 2.5s ease-in-out infinite;
}
@keyframes notif-pulse {
  0%,100% { box-shadow: none; }
  50% { box-shadow: 0 0 8px rgba(204,0,0,0.4), 0 0 16px rgba(204,0,0,0.15); }
}

/* ── XP STRIP ────────────────────────────────────────────────────────────── */
.xp-strip {
  position: fixed;
  top: 56px;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--clr-border);
  z-index: calc(var(--z-topbar) - 1);
  overflow: hidden;
}
.xp-strip-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--clr-blood), var(--clr-crimson));
  transition: width 0.6s ease-out;
}
.xp-strip-lbl { display: none; } /* skryto — zobrazovat jen na hover pokud je potřeba */

/* ── LAYOUT GRID ─────────────────────────────────────────────────────────── */
body {
  padding-top: 59px; /* topbar 56px + xp-strip 3px */
}

/* ── SIDEBAR ─────────────────────────────────────────────────────────────── */
.lpanel {
  width: 240px;
  position: fixed;
  top: 59px;
  left: 0;
  bottom: 0;
  background: var(--clr-base);
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)' opacity='0.025'/%3E%3C/svg%3E");
  border-right: 1px solid var(--clr-border);
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-width: thin;
  scrollbar-color: var(--clr-border) transparent;
  z-index: 20;
}
.lpanel::-webkit-scrollbar { width: 4px; }
.lpanel::-webkit-scrollbar-track { background: transparent; }
.lpanel::-webkit-scrollbar-thumb { background: var(--clr-border); border-radius: 2px; }

/* ── CHARACTER CHIP ──────────────────────────────────────────────────────── */
.portrait-wrap {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-3) var(--sp-4);
  border-bottom: 1px solid var(--clr-border);
}
.portrait-outer,
.portrait-inner {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
}
.portrait-inner {
  background: var(--clr-surface);
  border: 2px solid var(--clr-blood);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  position: relative;
}
.portrait-inner img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.portrait-emoji {
  font-size: 1.1rem;
  position: absolute;
}
.portrait-name {
  font-family: var(--font-display);
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--clr-text);
  letter-spacing: 0.05em;
  line-height: 1.3;
}
.portrait-guild {
  font-family: var(--font-body);
  font-size: var(--fs-xs);
  color: var(--clr-muted);
  letter-spacing: 0.04em;
}
.portrait-level {
  font-family: var(--font-body);
  font-size: var(--fs-xs);
  color: var(--clr-blood);
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

/* ── NAVIGACE ────────────────────────────────────────────────────────────── */
.lnav { padding: var(--sp-2) 0 var(--sp-8); }

/* Standalone top-level nav-btn (City Hub) */
.nav-btn {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  width: 100%;
  padding: 10px var(--sp-4);
  min-height: 44px;
  border: none;
  border-left: 3px solid transparent;
  background: transparent;
  color: var(--clr-muted);
  font-family: var(--font-body);
  font-size: var(--fs-sm);
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  text-align: left;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.nav-btn:hover {
  color: var(--clr-text);
  background: rgba(204,0,0,0.04);
  border-left-color: rgba(204,0,0,0.4);
}
.nav-btn.active {
  color: var(--clr-text);
  border-left-color: var(--clr-blood);
  background: rgba(204,0,0,0.08);
}
.nav-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  color: inherit;
}

/* Nav group header */
.nav-group { margin: var(--sp-1) 0; }
.nav-group-header {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 6px var(--sp-4);
  border: none;
  background: transparent;
  color: var(--clr-faint);
  font-family: var(--font-body);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  cursor: pointer;
  gap: var(--sp-2);
  transition: color var(--transition-fast);
}
.nav-group-header::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--clr-border);
  margin-left: var(--sp-2);
}
.nav-group-header:hover { color: var(--clr-muted); }
.nav-group-body { overflow: hidden; }
.nav-group-body.collapsed { display: none; }

/* Nav badge (equipment unspent points) */
.sp-nav-badge {
  margin-left: auto;
  background: var(--clr-blood);
  color: #fff;
  font-size: 0.65rem;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: var(--radius-sm);
  min-width: 16px;
  text-align: center;
}
.sp-nav-badge:empty { display: none; }

/* ── MAIN CONTENT ────────────────────────────────────────────────────────── */
.main {
  margin-left: 240px;
  min-height: calc(100vh - 59px);
}
.main-scroll {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--sp-6);
}

/* Page visibility */
.page { display: none; }
.page.active { display: block; }

/* Page header */
.page-hdr {
  margin-bottom: var(--sp-6);
  padding-bottom: var(--sp-4);
  border-bottom: 1px solid var(--clr-border);
}
.page-hdr-title {
  font-family: var(--font-display);
  font-size: var(--fs-2xl);
  font-weight: 700;
  color: var(--clr-text);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  text-shadow: 0 0 40px rgba(204,0,0,0.3);
}
.page-hdr-sub {
  font-family: var(--font-body);
  font-size: var(--fs-sm);
  color: var(--clr-muted);
  margin-top: var(--sp-1);
  letter-spacing: 0.04em;
}

/* HP/MP bars */
.hp-bar-fill {
  background: linear-gradient(90deg, #8b0000, var(--clr-blood));
  box-shadow: 0 0 8px rgba(204,0,0,0.4);
  height: 8px;
  transition: width 0.4s ease;
}
.mp-bar-fill {
  background: linear-gradient(90deg, #1a3a6b, #2563eb);
  height: 8px;
  transition: width 0.4s ease;
}
.hp-bar-fill.damage-pulse {
  animation: hp-damage-pulse 0.4s ease;
}
@keyframes hp-damage-pulse {
  0%  { filter: brightness(1); }
  30% { filter: brightness(1.8); }
  100%{ filter: brightness(1); }
}

/* ── TABLET (768–1023px) — icon-only sidebar + hover fly-out ────────────── */
@media (max-width: 1023px) {
  .lpanel {
    width: 56px;
    overflow: visible;
    transition: width var(--transition-mid);
  }
  /* Fly-out na hover — rozšíří sidebar zpět na 240px */
  .lpanel:hover {
    width: 240px;
    box-shadow: 4px 0 16px rgba(0,0,0,0.6);
  }
  .lpanel:hover .portrait-name,
  .lpanel:hover .portrait-guild,
  .lpanel:hover .portrait-level { display: block; }
  .lpanel:hover .nav-btn { justify-content: flex-start; gap: var(--sp-2); }
  .lpanel:hover .nav-btn span:not(.nav-icon):not(.sp-nav-badge) { display: inline; }
  .lpanel:hover .nav-group-header { display: flex; }
  .lpanel:hover .nav-group-body.collapsed { display: none; }
  .lpanel:hover .sp-nav-badge { position: static; }

  .portrait-wrap { padding: var(--sp-2); justify-content: center; overflow: hidden; }
  .portrait-name, .portrait-guild, .portrait-level { display: none; }
  .nav-btn {
    padding: 12px;
    justify-content: center;
    gap: 0;
    min-height: 48px;
    position: relative;
  }
  .nav-btn span:not(.nav-icon):not(.sp-nav-badge) { display: none; }
  .nav-btn .nav-icon { width: 18px; height: 18px; }
  .nav-group-header { display: none; }
  .nav-group-body.collapsed { display: block; } /* vždy viditelné v icon-only módu */
  .sp-nav-badge {
    position: absolute;
    top: 4px;
    right: 4px;
    min-width: 14px;
    font-size: 0.6rem;
    padding: 0 3px;
  }
  .main { margin-left: 56px; }
}

/* ── MOBILE (<768px) — hamburger + sidebar drawer ────────────────────────── */
@media (max-width: 767px) {
  .lpanel { display: none; }
  .main   { margin-left: 0; }
  .main-scroll { padding: var(--sp-3); }
}

/* Mobile drawer — zobrazení sidebaru přes celou výšku */
.mob-sidebar-drawer {
  position: fixed;
  top: 59px;
  left: 0;
  bottom: 0;
  width: 280px;
  background: var(--clr-base);
  border-right: 1px solid var(--clr-border);
  box-shadow: 4px 0 20px rgba(0,0,0,0.6);
  z-index: calc(var(--z-modal) - 1);
  transform: translateX(-100%);
  transition: transform var(--transition-mid);
  overflow-y: auto;
}
.mob-sidebar-drawer.open { transform: translateX(0); }
.mob-sidebar-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.7);
  z-index: calc(var(--z-modal) - 2);
  opacity: 0;
  pointer-events: none;
  transition: opacity var(--transition-mid);
}
.mob-sidebar-backdrop.open { opacity: 1; pointer-events: all; }
/* Hamburger button — zobrazit jen na mobilu */
.tb-hamburger {
  display: none;
  background: transparent;
  border: 1px solid var(--clr-border);
  border-radius: var(--radius-sm);
  color: var(--clr-muted);
  padding: 8px;
  min-width: 44px;
  min-height: 44px;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--transition-fast);
  flex-shrink: 0;
}
.tb-hamburger:hover { border-color: var(--clr-blood); color: var(--clr-ember); }
@media (max-width: 767px) {
  .tb-hamburger { display: flex; }
}
```

- [ ] **Krok 2: Ověřit v browseru**

- Desktop: sidebar 240px vlevo, main content s max-width 1200px
- Zmenšit okno na 900px → sidebar se zmenší na 56px ikono-only
- Zmenšit na 600px → sidebar zmizí

- [ ] **Krok 3: Commit**

```bash
git add frontend/css/layout.css
git commit -m "feat: layout.css — new 240px sidebar, 56px topbar, responsive breakpoints"
```

---

## Task 5: Přepsat components.css

**Files:**
- Modify: `frontend/css/components.css`

Nové komponenty: 3 btn varianty, karty, modaly bez backdrop-filter, toasty s ARIA data.

- [ ] **Krok 1: Přečíst prvních 50 řádků components.css pro kontext**

```bash
head -50 frontend/css/components.css
```

- [ ] **Krok 2: Přidat na začátek components.css nové komponenty**

Najít sekce `.btn`, `.card`, `.overlay`, `.modal`, `.toast` a nahradit:

**Buttony:**
```css
/* ── BUTTONY ─────────────────────────────────────────────────────────────── */
.btn,
.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--sp-2);
  min-height: 44px;
  padding: 10px var(--sp-4);
  background: var(--clr-blood);
  color: #fff;
  border: 1px solid var(--clr-crimson);
  border-radius: var(--radius-md);
  font-family: var(--font-body);
  font-size: var(--fs-sm);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  cursor: pointer;
  box-shadow: 3px 3px 0 rgba(0,0,0,0.6);
  transition: all var(--transition-fast);
  text-decoration: none;
}
.btn:hover,
.btn-primary:hover {
  background: var(--clr-crimson);
  box-shadow: 4px 4px 0 #000;
}
.btn:active,
.btn-primary:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 #000;
}
.btn:disabled,
.btn-primary:disabled {
  background: var(--clr-raised);
  border-color: var(--clr-border);
  color: var(--clr-faint);
  box-shadow: none;
  cursor: not-allowed;
  opacity: 0.6;
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--sp-2);
  min-height: 44px;
  padding: 10px var(--sp-4);
  background: transparent;
  color: var(--clr-text);
  border: 1px solid var(--clr-border);
  border-radius: var(--radius-md);
  font-family: var(--font-body);
  font-size: var(--fs-sm);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.btn-secondary:hover {
  border-color: var(--clr-blood);
  color: var(--clr-ember);
}
.btn-secondary:active { transform: scale(0.97); }

.btn-ghost {
  background: transparent;
  color: var(--clr-muted);
  border: none;
  font-family: var(--font-body);
  font-size: var(--fs-sm);
  font-weight: 500;
  letter-spacing: 0.04em;
  text-decoration: underline;
  text-underline-offset: 3px;
  cursor: pointer;
  padding: 6px var(--sp-2);
  transition: color var(--transition-fast);
}
.btn-ghost:hover { color: var(--clr-text); }

/* Specifické button varianty zachovány jako aliasy */
.btn-gold   { background: #8b6a1a; border-color: #c9a84c; }
.btn-gold:hover { background: #a07820; }
.btn-green  { background: #166534; border-color: #22c55e; }
.btn-green:hover { background: #15803d; }
.btn-sm     { min-height: 36px; padding: 6px var(--sp-3); font-size: var(--fs-xs); }
.btn-lg     { min-height: 52px; padding: 14px var(--sp-6); font-size: var(--fs-base); }
```

**Karty:**
```css
/* ── KARTY ───────────────────────────────────────────────────────────────── */
.card {
  background: var(--clr-surface);
  border: 1px solid var(--clr-border);
  border-top: 2px solid var(--clr-blood);
  border-radius: var(--radius-md);
  box-shadow: 4px 4px 0 rgba(0,0,0,0.5);
  padding: var(--sp-4);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast), border-top-color var(--transition-fast);
}
.card:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 rgba(0,0,0,0.6);
  border-top-color: var(--clr-crimson);
}
/* Rarity top-border variants */
.card[data-rarity="common"]    { border-top-color: #9d9d9d; }
.card[data-rarity="uncommon"]  { border-top-color: #1eff00; }
.card[data-rarity="rare"]      { border-top-color: #0070dd; }
.card[data-rarity="epic"]      { border-top-color: #a335ee; }
.card[data-rarity="legendary"] { border-top-color: #ff8000; }
.card[data-rarity="set"]       { border-top-color: #00d4ff; }
```

**Modaly:**
```css
/* ── MODALY ──────────────────────────────────────────────────────────────── */
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.92);
  z-index: var(--z-modal);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--sp-4);
  opacity: 0;
  pointer-events: none;
  transition: opacity var(--transition-mid);
}
.overlay.open {
  opacity: 1;
  pointer-events: all;
}
.modal {
  background: var(--clr-surface);
  border: 1px solid var(--clr-border);
  border-top: 3px solid var(--clr-blood);
  border-radius: var(--radius-lg);
  box-shadow: 8px 8px 0 rgba(0,0,0,0.8), 8px 8px 0 rgba(204,0,0,0.08);
  max-width: 560px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  padding: var(--sp-6);
  position: relative;
  animation: modal-in var(--transition-mid) ease-out;
}
@keyframes modal-in {
  from { transform: translateY(8px) scale(0.98); opacity: 0; }
  to   { transform: translateY(0) scale(1); opacity: 1; }
}
.modal-x {
  position: absolute;
  top: var(--sp-3);
  right: var(--sp-3);
  min-width: 44px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--clr-border);
  border-radius: var(--radius-sm);
  color: var(--clr-muted);
  font-size: 1rem;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.modal-x:hover { border-color: var(--clr-blood); color: var(--clr-ember); }
.modal-title {
  font-family: var(--font-display);
  font-size: var(--fs-xl);
  font-weight: 700;
  color: var(--clr-text);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding-bottom: var(--sp-4);
  margin-bottom: var(--sp-4);
  border-bottom: 1px solid var(--clr-border);
  padding-right: 48px; /* prostor pro modal-x */
}
```

**Toasty:**
```css
/* ── TOASTY ──────────────────────────────────────────────────────────────── */
.toasts,
#toasts {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: var(--z-toast);
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  pointer-events: none;
}
.toast {
  background: var(--clr-raised);
  border: 1px solid var(--clr-border);
  border-left: 4px solid var(--clr-muted);
  border-radius: var(--radius-sm);
  box-shadow: 4px 4px 0 rgba(0,0,0,0.6);
  padding: 12px var(--sp-4);
  font-family: var(--font-body);
  font-size: var(--fs-sm);
  font-weight: 500;
  color: var(--clr-text);
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  pointer-events: all;
  max-width: 320px;
  animation: toast-in 0.25s ease-out;
}
.toast.removing { animation: toast-out 0.25s ease-in forwards; }
@keyframes toast-in  { from { transform: translateX(110%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
@keyframes toast-out { from { transform: translateX(0); opacity: 1; } to { transform: translateX(110%); opacity: 0; } }
.toast.ts  { border-left-color: var(--clr-success); }
.toast.te  { border-left-color: var(--clr-blood); }
.toast.ti  { border-left-color: var(--clr-muted); }
```

- [ ] **Krok 3: Ověřit v browseru**

- Zkusit `toast('Test', 's')` v konzoli → zelená left-border
- Otevřít jakýkoliv modal → červená top border, žádný blur
- Zkontrolovat buttony na stránce Equipment

- [ ] **Krok 4: Commit**

```bash
git add frontend/css/components.css
git commit -m "feat: components.css — Brutal Gothic buttons, cards, modals, toasts"
```

---

## Task 6: ui.js — ARIA management

**Files:**
- Modify: `frontend/js/ui.js`

- [ ] **Krok 1: Přidat `aria-current` do `showPage()`**

Najít `showPage()` (řádek 285) a přidat za řádek 295 (`document.getElementById('nav-${name}')?.classList.add('active')`):

```javascript
// aria-current management
document.querySelectorAll('.nav-btn[id]').forEach(b => b.removeAttribute('aria-current'));
document.getElementById(`nav-${name}`)?.setAttribute('aria-current', 'page');
```

- [ ] **Krok 1b: Přidat `aria-expanded` do `toggleNavGroup()`**

Najít `toggleNavGroup()` (řádek 183) a přidat na konec funkce (po `_saveNavGroupState`):

```javascript
// Synchronizovat aria-expanded s vizuálním stavem
const header = document.getElementById(`ngh-${id}`);
const body = document.getElementById(`ngbody-${id}`);
if (header && body) {
  const isOpen = !body.classList.contains('collapsed');
  header.setAttribute('aria-expanded', String(isOpen));
}
```

- [ ] **Krok 1c: Přidat hamburger button + mobile sidebar drawer**

Najít `_initMobileUI()` (řádek 92) a přidat novou funkci pro sidebar drawer (existující mobile bottom tab bar nechat beze změny):

```javascript
function _initMobileSidebarDrawer() {
  if (document.getElementById('mob-sidebar-drawer')) return;

  const backdrop = document.createElement('div');
  backdrop.className = 'mob-sidebar-backdrop';
  backdrop.id = 'mob-sidebar-backdrop';
  backdrop.onclick = closeMobileSidebar;

  // Klonujeme .lpanel obsah do draweru
  const drawer = document.createElement('nav');
  drawer.className = 'mob-sidebar-drawer';
  drawer.id = 'mob-sidebar-drawer';
  drawer.setAttribute('aria-label', 'Mobilní navigace');
  const lpanel = document.querySelector('.lpanel');
  if (lpanel) drawer.innerHTML = lpanel.innerHTML;

  document.body.append(backdrop, drawer);
}

function openMobileSidebar() {
  _initMobileSidebarDrawer();
  document.getElementById('mob-sidebar-drawer')?.classList.add('open');
  document.getElementById('mob-sidebar-backdrop')?.classList.add('open');
}

function closeMobileSidebar() {
  document.getElementById('mob-sidebar-drawer')?.classList.remove('open');
  document.getElementById('mob-sidebar-backdrop')?.classList.remove('open');
}
```

Přidat volání `_initMobileSidebarDrawer()` na konec `_initMobileUI()`.

Přidat hamburger button do `game.html` (hned za `<div class="topbar">`):

```html
<button class="tb-hamburger" onclick="openMobileSidebar()" aria-label="Otevřít navigaci">
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       stroke-width="2" aria-hidden="true">
    <line x1="3" y1="6" x2="21" y2="6"/>
    <line x1="3" y1="12" x2="21" y2="12"/>
    <line x1="3" y1="18" x2="21" y2="18"/>
  </svg>
</button>
```

- [ ] **Krok 2: Přidat ARIA atributy do `toast()` funkce**

Najít `toast()` (řádek 37) a aktualizovat:

```javascript
function toast(msg, type='i', dur=3500) {
  const el = document.createElement('div');
  el.className = `toast t${type}`;

  // ARIA: error = alert (okamžité), ostatní = polite
  if (type === 'e') {
    el.setAttribute('role', 'alert');
  } else {
    el.setAttribute('aria-live', 'polite');
  }

  // SVG ikony místo emoji
  const icons = {
    s: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg>`,
    e: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
    i: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
  };
  el.innerHTML = `<span style="flex-shrink:0;color:${type==='s'?'var(--clr-success)':type==='e'?'var(--clr-blood)':'var(--clr-muted)'}">${icons[type]}</span><span>${msg}</span>`;
  document.getElementById('toasts').append(el);

  const removeEl = () => {
    el.classList.add('removing');
    el.addEventListener('animationend', () => el.remove(), { once: true });
    setTimeout(() => el.remove(), 300);
  };
  setTimeout(removeEl, dur);
}
```

- [ ] **Krok 3: Ověřit v browseru**

- Vyvolat toast v konzoli: `toast('Úspěch', 's')` → SVG checkmark ikona, zelená border
- `toast('Chyba', 'e')` → SVG X ikona, červená border
- DevTools Accessibility → toast element má `role="alert"` nebo `aria-live`

- [ ] **Krok 4: Commit**

```bash
git add frontend/js/ui.js
git commit -m "feat: ui.js — aria-current in showPage(), toast ARIA roles, SVG icons"
```

---

## Task 7: Zjednodušit physical.css

**Files:**
- Modify: `frontend/css/physical.css`

Odstranit: vignette, turbulence na kartách, depth efekty, všechny dekorativní textury mimo grain + worn metal.

- [ ] **Krok 1: Přečíst physical.css pro inventář efektů**

```bash
grep -n "vignette\|turbulence\|depth\|fractalNoise\|grain\|metal" frontend/css/physical.css
```

- [ ] **Krok 2: Zachovat pouze grain a worn metal**

Smazat všechny sekce vyjma:
- Grain noise overlay na `body::before` (5% opacity SVG)
- Worn metal texture na `.topbar` a `.lpanel` (2.5% opacity)

```css
/* ═══════════════════════════════════════════════════════════════════════════
   BRUTAL GOTHIC — Physical Textures
   Zachováno: grain noise (body) + worn metal (topbar, sidebar)
   ═══════════════════════════════════════════════════════════════════════════ */

/* Grain noise — přidává materiálovost celé stránce */
/* z-index: 1 — nad body background, pod vším ostatním (topbar=30, modal=100, toast=200) */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23n)' opacity='0.05'/%3E%3C/svg%3E");
  pointer-events: none;
  z-index: 1;
}
```

Worn metal je již zahrnutý v `layout.css` jako background-image na `.topbar` a `.lpanel`.

- [ ] **Krok 3: Commit**

```bash
git add frontend/css/physical.css
git commit -m "refactor: physical.css — keep only grain noise, remove decorative effects"
```

---

## Task 8: Aktualizovat combat.css, animations.css

**Files:**
- Modify: `frontend/css/combat.css`
- Modify: `frontend/css/animations.css`

- [ ] **Krok 1: Aktualizovat HP/MP bary v combat.css**

Najít existující bar styly a nahradit výšku a barvy:

```css
/* HP bar height — z ~6px na 8px */
/* Najít selector pro HP bar container a nastavit height: 8px */
```

Přidat pokud chybí:
```css
.bar-hp { background: linear-gradient(90deg, #8b0000, var(--clr-blood)); box-shadow: 0 0 8px rgba(204,0,0,0.4); height: 8px; }
.bar-mp { background: linear-gradient(90deg, #1a3a6b, #2563eb); height: 8px; }
```

- [ ] **Krok 2: Aktualizovat reduced-motion v animations.css**

Najít `@media (prefers-reduced-motion: reduce)` a nahradit selektor:

```css
/* NAHRADIT existující reduced-motion sekci: */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

- [ ] **Krok 3: Commit**

```bash
git add frontend/css/combat.css frontend/css/animations.css
git commit -m "feat: combat.css HP/MP bars 8px, animations.css reduced-motion fix"
```

---

## Task 9: Remapovat tokeny v assets.css, quest.css, inventory.css

**Files:**
- Modify: `frontend/css/assets.css`
- Modify: `frontend/css/quest.css`
- Modify: `frontend/css/inventory.css`

- [ ] **Krok 1: Audit starých tokenů v souborech**

```bash
grep -n "clr-gold\|clr-obsidian\|clr-slate\|border-rune\|glow-gold\|font-heading\|font-display\|font-ui\|font-rune\|font-lore" frontend/css/assets.css frontend/css/quest.css frontend/css/inventory.css
```

- [ ] **Krok 2: Nahradit staré tokeny**

Systematicky projít výsledky a nahradit:

| Starý token | Nový token |
|-------------|------------|
| `var(--font-heading)` | `var(--font-display)` |
| `var(--font-ui)` | `var(--font-body)` |
| `var(--font-rune)` | `var(--font-display)` |
| `var(--clr-obsidian)` | `var(--clr-base)` |
| `var(--clr-slate)` | `var(--clr-surface)` |
| `var(--clr-stone)` | `var(--clr-raised)` |
| Rarity barvy | **ZACHOVAT beze změny** |

- [ ] **Krok 3: Ověřit v browseru — stránky Quests a Inventory**

Zkontrolovat že quest karty a inventory grid vypadají rozumně.

- [ ] **Krok 4: Commit**

```bash
git add frontend/css/assets.css frontend/css/quest.css frontend/css/inventory.css
git commit -m "refactor: remap old CSS tokens to Brutal Gothic system"
```

---

## Task 10: Audit textures.css a ui-enhance.css

**Files:**
- Modify: `frontend/css/textures.css`
- Modify: `frontend/css/ui-enhance.css`

- [ ] **Krok 1: Vyhledat kolidující styly**

```bash
grep -n "backdrop-filter\|blur\|turbulence\|vignette\|gold\|clr-gold\|font-heading" frontend/css/textures.css frontend/css/ui-enhance.css
```

- [ ] **Krok 2: Odstranit / nahradit kolidující pravidla**

- Všechny `backdrop-filter: blur(*)` → odstranit
- `var(--clr-gold)` → `var(--clr-blood)` (compat alias existuje, ale explicitní je lepší)
- Dekorativní textury na kartách → odstranit (physical.css je source of truth)

- [ ] **Krok 3: Commit**

```bash
git add frontend/css/textures.css frontend/css/ui-enhance.css
git commit -m "refactor: textures.css, ui-enhance.css — remove backdrop-filter, align tokens"
```

---

## Task 11: Remapovat theme.css

**Files:**
- Modify: `frontend/css/theme.css`

Největší soubor (5692 řádků). Cíl: opravit místa kde stávající compat aliasy nestačí, zajistit že shop/equipment/inventory stránky vypadají správně.

- [ ] **Krok 1: Najít nejpoužívanější staré tokeny**

```bash
grep -c "clr-gold\|clr-obsidian\|clr-slate\|glow-gold\|border-rune\|font-heading\|font-ui\|font-rune" frontend/css/theme.css
```

- [ ] **Krok 2: Bulk nahrazení tokenů (Python — cross-platform)**

```python
# Spustit z rootu projektu: python scripts/fix_theme_tokens.py
# Nebo přímo v shellu:

python -c "
import re, pathlib

f = pathlib.Path('frontend/css/theme.css')
txt = f.read_text(encoding='utf-8')

replacements = [
    ('var(--font-heading)', 'var(--font-display)'),
    ('var(--font-ui)',      'var(--font-body)'),
    ('var(--font-rune)',    'var(--font-display)'),
]
for old, new in replacements:
    txt = txt.replace(old, new)

# Odstranit backdrop-filter deklarace (jednořádkové i víceřádkové)
txt = re.sub(r'backdrop-filter\s*:[^;]+;', '', txt)

f.write_text(txt, encoding='utf-8')
print('Done — theme.css updated')
"
```

- [ ] **Krok 3: Vizuálně projít všechny hlavní stránky**

Projít v browseru: Equipment → Inventory → Shop → Guild → Arena → Quests
Zkontrolovat že texty jsou čitelné a layout nevypadá rozbitě.

- [ ] **Krok 4: Smazat zálohu a commitnout**

```bash
rm frontend/css/theme.css.bak
git add frontend/css/theme.css
git commit -m "refactor: theme.css — remap old font/color tokens, remove backdrop-filter"
```

---

## Task 12: Finální accessibility pass

**Files:**
- Modify: `frontend/game.html` (pokud zbývají opravy)

- [ ] **Krok 1: Zkontrolovat modal close buttony**

```bash
grep -n "modal-x" frontend/game.html | head -20
```

Každý `.modal-x` musí mít `aria-label="Zavřít"`:
```html
<button class="modal-x" aria-label="Zavřít">✕</button>
```

- [ ] **Krok 2: Zkontrolovat touch targets**

V DevTools → mobile view 375px → zkontrolovat že nav buttony, modal-x, tb-btn mají min 44px výšku.

- [ ] **Krok 3: Tab navigace test**

- Stisknout Tab opakovaně → focus ring (červený outline) viditelný na každém interaktivním prvku
- Skip link se zobrazí jako první při prvním Tabu
- Modaly: Tab uvnitř modalu by neměl unikat ven (pokud existuje focus trap)

- [ ] **Krok 4: Kontrast check**

DevTools → Rendering → "Emulate vision deficiencies" → Protanopia
Ověřit že rarity barvy jsou rozlišitelné i bez červené složky.

- [ ] **Krok 5: Commit**

```bash
git add frontend/game.html
git commit -m "fix: accessibility pass — modal-x aria-labels, touch target verification"
```

---

## Ověřovací checklist (po dokončení všech tasků)

- [ ] Stránka se načte bez JS errors v konzoli
- [ ] Fonty: Rajdhani pro UI, Cinzel pro nadpisy, Crimson Text pro lore text
- [ ] Topbar: 56px, červená spodní border-shadow, žádné zlaté ornámenty
- [ ] Sidebar: 240px, SVG ikony, aktivní item má červenou left-border
- [ ] Nav: žádné emoji ikony kdekoliv
- [ ] Toast (`toast('x','s')` v konzoli): SVG ikona, zelená left border
- [ ] Toast (`toast('x','e')`): SVG X, červená left border, `role="alert"` v DOM
- [ ] Modal: červená top border, žádný backdrop blur
- [ ] HP bar: 8px výška, červený gradient
- [ ] Focus ring: červeno-oranžový outline na všech interaktivních prvcích při Tab
- [ ] Skip link: viditelný při prvním Tab
- [ ] Responsivita: 375px → sidebar skrytý, 900px → icon-only sidebar
- [ ] `prefers-reduced-motion`: animace deaktivovány
