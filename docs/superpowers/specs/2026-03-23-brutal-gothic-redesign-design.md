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
--clr-faint:     #666666;

/* STATUSY */
--clr-success:   #22c55e;
--clr-warning:   #f59e0b;
--clr-danger:    #cc0000;
```

### Typografie — 3 rodiny (z 6)

| Role | Font | Použití |
|------|------|---------|
| `--font-display` | Cinzel | Page titles, modal titles |
| `--font-body` | Inter | UI, labels, čísla, navigace |
| `--font-lore` | Crimson Text | Quest text, item flavor text |

**Odstraněny:** Cinzel Decorative, IM Fell English, Josefin Sans, UnifrakturMaguntia

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
- **Žádný backdrop-filter blur** na modalech — výkon + charakter

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
- Font: Inter, `font-size: var(--fs-sm)`, `text-transform: uppercase`, `letter-spacing: 0.04em`

### SVG ikony (Lucide, 16×16, stroke-width: 2)

| Položka | Ikona |
|---------|-------|
| City Hub | `home` |
| Quests | `scroll` |
| Arena | `swords` |
| World Boss | `skull` |
| Dungeons | `door-open` |
| Equipment | `shield` |
| Inventory | `backpack` |
| Guild | `users` |
| Faction | `flag` |
| Market | `store` |
| Shop | `shopping-bag` |
| Profile | `user` |

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

Rarity: `border-top-color` nahrazuje rarity barvu.

### Modaly

```css
.overlay { background: rgba(0,0,0,0.92); }  /* žádný backdrop-filter */
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
}
```

`[data-type="s"]` → `border-left-color: var(--clr-success)`
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

### Contrast (všechny páry splňují WCAG AA+)

| Kombinace | Poměr | Standard |
|-----------|-------|----------|
| `#f0f0f0` na `#080808` | 18.5:1 | AAA |
| `#f0f0f0` na `#1a1a1a` | 13.2:1 | AAA |
| `#999999` na `#111111` | 5.8:1 | AA |
| `#fff` na `#cc0000` | 5.9:1 | AA |

### ARIA

- `<nav aria-label="Hlavní navigace">`
- `aria-current="page"` na aktivní nav položce
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

### Font loading

```html
<link rel="preload" href="Inter.woff2" as="font" crossorigin>
<link rel="preload" href="Cinzel.woff2" as="font" crossorigin>
```

Crimson Text: `font-display: swap` přes Google Fonts.

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

## 7. Soubory k úpravě / vytvoření

| Soubor | Akce |
|--------|------|
| `frontend/css/design-system.css` | Přepsat — nová paleta, tokeny, typografie |
| `frontend/css/base.css` | Aktualizovat — fs-base na 1rem, focus ring, skip link |
| `frontend/css/layout.css` | Přepsat — nový grid, sidebar, topbar, mobile drawer |
| `frontend/css/components.css` | Přepsat — buttony, karty, modaly, toasty |
| `frontend/css/theme.css` | Aktualizovat — aplikovat nové tokeny |
| `frontend/css/combat.css` | Aktualizovat — HP/MP bary |
| `frontend/css/animations.css` | Aktualizovat — reduced-motion selektor |
| `frontend/css/physical.css` | Zjednodušit — pouze grain texture + worn metal |
| `frontend/game.html` | Aktualizovat — skip link, ARIA, SVG ikony, nav struktura, font imports |
| `frontend/js/main.js` | Aktualizovat — mobile drawer toggle, aria-current management |

---

## 8. Co se NEMĚNÍ

- Herní logika (JS moduly — combat, quests, dungeon, atd.)
- Backend API
- Rarity barevné kódy (common/uncommon/rare/epic/legendary)
- Toast systém API (`toast(msg, type, duration)`)
- Modal systém API (`openModal(id)` / `closeModal(id)`)
- Z-index stack hodnoty (30/50/100/200)
- Pořadí JS scriptů
