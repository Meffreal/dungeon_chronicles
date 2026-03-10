# UI Textures + Palette Sweep — Design Doc

**Datum:** 2026-03-10
**Projekt:** Dungeon Chronicles
**Cíl:** Odstranit ploché jednobarevné panely, doladit paletu — celá hra jednotný dark fantasy look.

---

## Problém

1. `theme.css` má 30–40 míst se starou modrou paletou (`rgba(30,127,184`, `#06101e`, `#1e7fb8` atd.) — feature sekce (quest, arena, market, crystals, dungeon) vypadají genericky
2. Panely jsou ploché jednobarevné plochy — žádná hloubka, žádný materiál

---

## Řešení — 4 zóny

### Zóna 1: Palette sweep (theme.css)
Nahradit všechny zbývající studené modré hodnoty crimson/ember ekvivalenty.

| Stará hodnota | Nová hodnota |
|---------------|--------------|
| `rgba(30,127,184,.XX)` | `rgba(192,57,43,.XX)` |
| `rgba(56,212,196,.XX)` | `rgba(230,126,34,.XX)` |
| `#06101e`, `#0c1a2e` | `#120806`, `#1c0e08` |
| `#1e7fb8` | `var(--accent)` |
| `#38d4c4` | `var(--accent2)` |

Výjimky: `.cls-mage` barvy (zůstanou modré — tematicky správné), rarity colors.

### Zóna 2: Kamenný panel (lpanel)
CSS-only stone texture jako `background`:
- Base: `linear-gradient(180deg, #120806, #0a0503)` (již máme)
- Přidat: SVG `<pattern>` jako `background-image` — horizontální kamenné bloky, spáry 1px
- Pattern size: ~48px × 24px, opacity ~0.04 (sotva viditelný, ale přidává hloubku)
- Implementace: inline `url("data:image/svg+xml,...")` v CSS

### Zóna 3: Pergamenové modaly
Vrstvené `radial-gradient`y v `.modal` background:
```css
background:
  radial-gradient(ellipse at 15% 85%, rgba(60,20,5,.6) 0%, transparent 50%),
  radial-gradient(ellipse at 85% 15%, rgba(80,30,5,.4) 0%, transparent 45%),
  radial-gradient(ellipse at 50% 50%, rgba(28,14,8,.0) 0%, rgba(10,3,1,.4) 100%),
  linear-gradient(160deg, #150a05, #1c0e08);
```
Výsledek: tmavší rohy, mírně nerovnoměrný povrch — "starý pergamen/kůže".

### Zóna 4: Kovový topbar
Opakující se brush pattern v topbaru:
```css
background-image: repeating-linear-gradient(
  180deg,
  rgba(255,255,255,.015) 0px, rgba(255,255,255,.015) 1px,
  transparent 1px, transparent 4px
);
```
Plus `box-shadow: inset 0 -2px 8px rgba(0,0,0,.5)` pro hloubku.

---

## Scope

- **Žádné JS změny**
- **Žádné nové soubory** — pouze `theme.css`, `components.css`, `layout.css`
- CSS-only, žádné závislosti

## Pořadí implementace

1. Palette sweep (základ — bez toho by textury vypadaly divně na modrém pozadí)
2. Kovový topbar (layout.css — rychlé, 2 řádky)
3. Kamenný panel (layout.css — SVG pattern)
4. Pergamenové modaly (components.css — gradient layering)
