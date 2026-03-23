# Dungeon Chronicles — Brutal Gothic Redesign

**Datum:** 2026-03-23
**Scope:** Kompletní frontend redesign (CSS + HTML + JS)
**Cíl:** Accessibility opravy + vizuální upgrade → Brutal Gothic styl

---

## 1. Kontext & Motivace

Aktuální "Obsidian Codex" design systém má gothickou atmosféru, ale trpí:
- Emoji ikonami v navigaci (nelze stylovat, nekonzistentní cross-platform)
- Přeplněným layoutem bez jasné hierarchie
- 6 font rodinami (výkon, CLS)
- Chybějícími ARIA labels, focus staty, skip linkem
- Body textem pod 16px (iOS auto-zoom bug)
- Žádnou mobilní responsivitou sidebaru

**Nový směr: Brutal Gothic** — temný, ostrý, atmosférický. Červená + ocelová šedá + bílá. Brutalistický offset shadow. Minimální dekorace, maximální charakter.

---

## 2. Layout & Grid

### Desktop (≥1024px)
- Topbar: `56px`, full width, `position: fixed`
- Sidebar: `240px`, fixed, `position: fixed`, `top: 56px`
- Main content: `margin-left: 240px`, `padding-top: 56px`, `max-width: 1200px` + auto margins

### Tablet (768–1023px)
- Sidebar kolapuje na `56px` ikono-only pruh
- Hover/klik → fly-out panel s popisky (`240px`)

### Mobil (<768px)
- Sidebar skrytý
- Hamburger button v topbaru (vlevo)
- Bottom sheet drawer ze spodu (`transform: translateY`)
- XP strip zůstává pod topbarem

### Spacing systém
Striktně 4px base grid: `4 / 8 / 12 / 16 / 24 / 32 / 48 / 64px`

---

## 3. Design System — Brutal Gothic

### Barevná paleta

```css
/* BACKGROUNDS */
--clr-void:      #080808;
--clr-base:      #111111;
--clr-surface:   #1a1a1a;
--clr-raised:    #222222;
--clr-border:    #2e2e2e;

/* PRIMÁRNÍ ACCENT */
--clr-blood:     #cc0000;
--clr-crimson:   #e61919;
--clr-ember:     #ff4d4d;

/* TEXT */
--clr-text:      #f0f0f0;
--clr-muted:     #999999;
--clr-faint:     #666666;   /* pouze dekorativní — nesplňuje AA pro malý text */

/* STATUSY */
--clr-success:   #22c55e;
--clr-warning:   #f59e0b;
--clr-danger:    #ff3333;   /* odlišné od --clr-blood: teplý červeno-oranžový pro error stavy */
```

> `--clr-danger` je záměrně odlišný od `--clr-blood` — blood je primární UI accent,
> danger je sémantická barva pro chybové stavy (formuláře, validace).

### Typografie — 3 rodiny (z 6)

| Role | Font | Použití |
|------|------|---------|
| `--font-display` | Cinzel | Page titles, modal titles |
| `--font-body` | Rajdhani | UI, labels, čísla, navigace |
| `--font-lore` | Crimson Text | Quest text, item flavor text |

> **Rajdhani** zvolen jako `--font-body`: angulární, silný, kontextuálně vhodný pro RPG UI.
> Splňuje pravidlo `frontend/CLAUDE.md` — ne Arial/Inter/Roboto.

**Odstraněny:** Cinzel Decorative, IM Fell English, Josefin Sans, UnifrakturMaguntia, Inter

### Typografická škála

```css
--fs-xs:   0.75rem;    /* 12px */
--fs-sm:   0.875rem;   /* 14px */
--fs-base: 1rem;       /* 16px — opravuje iOS auto-zoom */
--fs-lg:   1.125rem;   /* 18px */
--fs-xl:   1.25rem;    /* 20px */
--fs-2xl:  1.5rem;     /* 24px */
--fs-3xl:  2rem;       /* 32px */
```

### Border Radius — ostré hrany

```css
--radius-sm: 2px;   /* inputs, badges */
--radius-md: 4px;   /* karty, buttony */
--radius-lg: 6px;   /* modaly */
```

### Vizuální charakter

- **Grain texture:** SVG noise overlay, 5% opacity na `body` — materiálovost
- **Worn metal:** pouze topbar a sidebar — `opacity: 0.03`
- **Offset shadow:** `4px 4px 0 rgba(0,0,0,0.8)` — brutalistický, bez blur
- **Red accent lines:** `border-left: 3px solid var(--clr-blood)` pro aktivní stavy
- **Červená aura na titulech:** `text-shadow: 0 0 40px rgba(204,0,0,0.3)`
- **Jediný glow:** HP bar — `box-shadow: 0 0 8px rgba(204,0,0,0.4)`
- **Žádný `backdrop-filter`** — odstraněn ze `.overlay`, `.toast` i `.modal` (výkon + charakter)

---

## 4. Navigace & Sidebar

### Struktura
```html
<nav aria-label="Hlavní navigace">
  <div class="nav-char-chip">
    <!-- avatar 40x40, jméno, class/level, guild -->
  </div>

  <div class="nav-section" aria-label="Combat">
    <span class="nav-section-label">Combat</span>
    <button class="nav-btn" aria-current="page">
      <svg aria-hidden="true"><!-- lucide icon --></svg>
      Quests
    </button>
    <!-- ... -->
  </div>
</nav>
```

### Nav button styling
- `min-height: 44px` (touch target)
- `border-left: 3px solid transparent`
- Aktivní: `border-left-color: var(--clr-blood)` + `background: rgba(204,0,0,0.08)`
- Hover: `border-left-color: rgba(204,0,0,0.4)` + `background: var(--clr-raised)`
- Font: Rajdhani, `font-size: var(--fs-sm)`, `text-transform: uppercase`, `letter-spacing: 0.04em`

### SVG ikony — kompletní seznam (Lucide, 16×16, stroke-width: 2)

| Skupina | Položka | Ikona |
|---------|---------|-------|
| — | City Hub | `home` |
| Combat | Quests | `scroll` |
| Combat | Arena | `swords` |
| Combat | World Boss | `skull` |
| Combat | Dungeons | `door-open` |
| Character | Equipment | `shield` |
| Character | Inventory | `backpack` |
| Character | Specialization | `git-branch` |
| Character | Prestige | `award` |
| Character | Attunement | `zap` |
| Character | Bloodline | `dna` |
| Social | Guild | `users` |
| Social | Faction | `flag` |
| Social | Market | `store` |
| Social | Shop | `shopping-bag` |
| Social | Hall of Fallen | `cross` |
| Seasonal | World Events | `globe` |
| Seasonal | Weekly | `calendar` |
| Seasonal | Season | `star` |
| Cosmetic | Crystals | `gem` |
| — | Profile | `user` |
| — | Account | `settings` |

> Žádné emoji ikony — všechny položky mají Lucide SVG ekvivalent.

### Portrait → Character Chip
- Avatar: `40×40px`, `border-radius: 2px`, `border: 2px solid var(--clr-blood)`
- Žádný diamond clip-path, žádný radial gradient portrait
- Jméno + třída/level + guild v 3 řádcích vedle avataru

---

## 5. Komponenty

### Buttony — 3 varianty

**Primary** (`btn-primary`):
- `background: var(--clr-blood)`
- `border: 1px solid var(--clr-crimson)`
- `box-shadow: 3px 3px 0 rgba(0,0,0,0.6)`
- Hover: `background: var(--clr-crimson)`, `box-shadow: 4px 4px 0 #000`
- Active: `transform: translate(2px,2px)`, `box-shadow: 1px 1px 0 #000`

**Secondary** (`btn-secondary`):
- `background: transparent`, `border: 1px solid var(--clr-border)`
- Hover: `border-color: var(--clr-blood)`, `color: var(--clr-ember)`

**Ghost** (`btn-ghost`):
- `background: transparent`, `border: none`
- `text-decoration: underline`, `text-underline-offset: 3px`

Všechny buttony: `min-height: 44px`, `font-weight: 600`, `letter-spacing: 0.08em`, `text-transform: uppercase`

### Karty

```css
.card {
  background: var(--clr-surface);
  border: 1px solid var(--clr-border);
  border-top: 2px solid var(--clr-blood);
  border-radius: var(--radius-md);
  box-shadow: 4px 4px 0 rgba(0,0,0,0.5);
  padding: 16px;
}
.card:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 rgba(0,0,0,0.6);
  border-top-color: var(--clr-crimson);
}
```

Rarity: `border-top-color` nahrazuje rarity barvu (common/uncommon/rare/epic/legendary kódy zachovány).

### Modaly

```css
.overlay {
  background: rgba(0,0,0,0.92);
  /* backdrop-filter odstraněn */
}
.modal {
  background: var(--clr-surface);
  border: 1px solid var(--clr-border);
  border-top: 3px solid var(--clr-blood);
  border-radius: 6px;
  box-shadow: 8px 8px 0 rgba(0,0,0,0.8), 8px 8px 0 rgba(204,0,0,0.1);
  max-width: 560px;
  width: calc(100% - 32px);
}
.modal-title {
  font-family: var(--font-display);
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
```

### Toasty

```css
.toast {
  background: var(--clr-raised);
  border: 1px solid var(--clr-border);
  border-left: 4px solid;
  border-radius: 2px;
  box-shadow: 4px 4px 0 rgba(0,0,0,0.6);
  /* backdrop-filter odstraněn */
}
```

`[data-type="s"]` → `border-left-color: var(--clr-success)` + `aria-live="polite"`
`[data-type="e"]` → `border-left-color: var(--clr-blood)` + `role="alert"`
`[data-type="i"]` → `border-left-color: var(--clr-muted)` + `aria-live="polite"`

### HP/MP bary

```css
.bar-hp { background: linear-gradient(90deg, #8b0000, #cc0000); box-shadow: 0 0 8px rgba(204,0,0,0.4); }
.bar-mp { background: linear-gradient(90deg, #1a3a6b, #2563eb); }
```

Výška: `8px` (z aktuálních ~6px).

---

## 6. Accessibility

### Contrast (WCAG 2.1, ověřené hodnoty)

| Kombinace | Poměr | Standard |
|-----------|-------|----------|
| `#f0f0f0` na `#080808` | 17.6:1 | ✅ AAA |
| `#f0f0f0` na `#1a1a1a` | 15.3:1 | ✅ AAA |
| `#999999` na `#111111` | 6.6:1 | ✅ AA |
| `#fff` na `#cc0000` | 5.9:1 | ✅ AA |
| `#666666` na `#111111` | 3.4:1 | ⚠️ pouze dekorativní použití |

### ARIA

- `<nav aria-label="Hlavní navigace">`
- `aria-current="page"` na aktivní nav položce (spravuje `ui.js`)
- `aria-label="Zavřít"` na modal-x buttonech
- `role="alert"` na error toastech
- `aria-live="polite"` na success/info toastech
- Všechny SVG ikony: `aria-hidden="true"`

### Focus ring (globální)

```css
:focus-visible {
  outline: 2px solid var(--clr-ember);
  outline-offset: 3px;
  border-radius: 2px;
}
:focus:not(:focus-visible) { outline: none; }
```

### Skip link

```html
<a href="#main-content" class="skip-link">Přeskočit na obsah</a>
```
```css
.skip-link { position: absolute; top: -100%; left: 8px; }
.skip-link:focus { top: 8px; z-index: 9999; }
```

### Touch targets

- Všechny nav buttony: `min-height: 44px`
- Všechny akční buttony: `min-height: 44px`
- Modal close: `min-width: 44px; min-height: 44px`

### Font loading (Google Fonts CDN)

```html
<!-- Preconnect pro výkon -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<!-- Fonty přes CDN s display=swap pro eliminaci FOIT -->
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Rajdhani:wght@400;500;600;700&family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
```

> Fonty zůstávají na Google Fonts CDN (ne lokálně). `display=swap` eliminuje FOIT.
> `preconnect` nahrazuje neúčinný `preload` pro CDN fonty.

### Reduced motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 7. Soubory k úpravě

| Soubor | Akce |
|--------|------|
| `frontend/css/design-system.css` | **Přepsat** — nová paleta, tokeny, Rajdhani typografie |
| `frontend/css/base.css` | **Aktualizovat** — fs-base na 1rem, focus ring, skip link |
| `frontend/css/layout.css` | **Přepsat** — nový grid, sidebar, topbar, mobile drawer |
| `frontend/css/components.css` | **Přepsat** — buttony, karty, modaly, toasty (bez backdrop-filter) |
| `frontend/css/theme.css` | **Aktualizovat** — aplikovat nové tokeny |
| `frontend/css/combat.css` | **Aktualizovat** — HP/MP bary |
| `frontend/css/animations.css` | **Aktualizovat** — reduced-motion selektor |
| `frontend/css/physical.css` | **Zjednodušit** — zachovat pouze: grain noise overlay + worn metal na topbar/sidebar; odstranit: vignette, turbulence na kartách, depth efekty |
| `frontend/css/assets.css` | **Aktualizovat** — rarity barvy zachovat, ostatní tokeny přemapovat |
| `frontend/css/quest.css` | **Aktualizovat** — přemapovat staré tokeny na nové |
| `frontend/css/inventory.css` | **Aktualizovat** — přemapovat staré tokeny na nové |
| `frontend/css/textures.css` | **Zkontrolovat** — odstranit textury nahrazené v physical.css; zachovat co nekoliduje |
| `frontend/css/ui-enhance.css` | **Zkontrolovat** — odstranit co koliduje s novým systémem |
| `frontend/game.html` | **Aktualizovat** — skip link, ARIA, SVG ikony (Lucide), nav struktura, font imports |
| `frontend/js/ui.js` | **Aktualizovat** — mobile drawer toggle, `aria-current` management v `showPage()` |

---

## 8. Co se NEMĚNÍ

- Herní logika (JS moduly — combat, quests, dungeon, arena, guild atd.)
- Backend API
- Rarity barevné kódy (common/uncommon/rare/epic/legendary hodnoty v assets.css)
- Toast systém API: `toast(msg, type, duration)` — typy `'s'` / `'e'` / `'i'`
- Modal systém API: `openModal(id)` / `closeModal(id)` — `.open` CSS class přístup
- Z-index stack hodnoty: topbar 30 · level-flash 50 · modals 100 · toasts 200
- Pořadí JS scriptů (39 modulů, kritické)
- `showPage(id)`, `updateUI(char)`, `api()` funkce signatury
