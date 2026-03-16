# Haunted Scroll Tooltip — Design Spec

**Datum:** 2026-03-17
**Stav:** Schváleno

## Problém

Itemy v inventáři, obchodě a na vybavovacích slotech nemají žádný hover tooltip. Hráč musí otevřít plný detail modal pro základní informace (staty, raritu, typ, level). Chybí rychlý přehled bez přerušení flow.

## Řešení — Design D "Haunted Scroll"

Hover tooltip na všech item kartách. Vychází z varianty D (`frontend/tooltip-proposals.html`): tmavý pergamen, barevný glow band nahoře podle rarity, 2-sloupcové staty, lore popis, ornamentální HR. CSS-first animace (opacity + translateY).

## Rozsah

Tooltips se zobrazují na **5 lokacích**:
1. **Inventář batoh** — každá karta v `.inv-grid` (`.inv-card`)
2. **Equip strip** — nasazené sloty v horním pásu inventáře (`.inv-strip-slot`, jen zaplněné)
3. **Character sheet** — vybavovací sloty (`.eq-slot`, jen zaplněné)
4. **Obchod** — karty zboží NPC (`.shop-card`)
5. **Tržiště** — řádky tabulky (`renderMarketTable`), trigger na `.mkt-item-cell`

## Architektura

### CSS — `frontend/css/components.css`

Přidat sekci `/* ── Item Tooltip D — Haunted Scroll ── */`:

**Trigger mechanismus:**
```css
.has-tip { position: relative; overflow: visible !important; }
/* !important nutné: theme.css načte se po components.css a definuje overflow:hidden
   na .inv-card, .eq-slot, .inv-strip-slot — bez !important tooltip bude oříznut */
.has-tip:hover .tip-d { opacity: 1; transform: translateX(-50%) translateY(0); }
@media (max-width: 768px) { .tip-d { display: none; } }
```

**Rarity CSS vars:**
```css
.r-common    { --rc: #9d9d9d !important; }
.r-uncommon  { --rc: #1eff00 !important; }
.r-rare      { --rc: #0070dd !important; }
.r-epic      { --rc: #a335ee !important; }
.r-legendary { --rc: #ff8000 !important; }
.r-set       { --rc: #00d4ff !important; }
```
Pozn.: `!important` je nutné — inline `style="--rc:..."` na kartách by jinak přebil class-based hodnotu.

**Tooltip base (`.tip-d`):**
- `position: absolute; bottom: calc(100% + 10px); left: 50%`
- `transform: translateX(-50%) translateY(6px)` → hover: `translateY(0)`
- `width: 250px; pointer-events: none; opacity: 0; z-index: 9999`
- Transition: `opacity 0.22s, transform 0.22s ease-out`

**Tooltip inner (`.tip-d-inner`):**
- Pozadí: `radial-gradient` (rarity glow na vrcholu) + `linear-gradient(180deg, #141218 → #0b0a12)`
- Border: `1px solid color-mix(in srgb, var(--rc) 25%, rgba(201,168,76,0.15))`
- Box-shadow: `0 16px 48px rgba(0,0,0,0.95)` + outer ring + rarity ambient

**Subkomponenty** (přímý přepis z proposals, beze změn):
- `.tip-d-glow-band` — 3px pruh rarity barvy nahoře
- `.tip-d-body` / `.tip-d-head` / `.tip-d-ico` / `.tip-d-info`
- `.tip-d-name` — Cinzel serif, rarity color, glow text-shadow
- `.tip-d-rarity-row` → `.tip-d-rarity-gem` (6px dot) + `.tip-d-rarity-label`
- `.tip-d-slot-label` — typ slotu, italic, faded
- `.tip-d-upgrade` — `★`/`★★`/`★★★` badge, gold color
- `.tip-d-hr` / `.tip-d-hr-line` / `.tip-d-hr-gem` — ornamentální oddělovač
- `.tip-d-stats` — `grid-template-columns: 1fr 1fr`, 2-sloupce
- `.tip-d-stat` / `.tip-d-sk` (label, italic, faded) / `.tip-d-sv` (hodnota, Cinzel, gold)
- `.tip-d-set` / `.tip-d-set-gem` / `.tip-d-set-name` — set item badge (cyan)
- `.tip-d-desc` — lore text, italic, opacity 0.48
- `.tip-d-foot` — `justify-content: space-between`
- `.tip-d-lvl` — level requirement (vlevo, faded)
- `.tip-d-price` — cena (vpravo, gold; jen v shop kontextu)
- `.tip-d::after` — trojúhelníkový pointer, rarity color

**Cinzel font** — game.html má jen `preconnect` ale žádnou Google Fonts URL. Přidat do `<head>` v `game.html` stejné URL jako v `index.html` (konzistentní sada fontů):
```html
<link href="https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700;900&family=Cinzel:wght@400;600;700&family=Crimson+Text:ital@0;1&family=Share+Tech+Mono&display=swap" rel="stylesheet">
```

### JS Helper — `frontend/js/ui.js`

Přidat funkci `buildItemTooltipHTML(item, inv, opts)` za existující utility:

**Parametry:**
- `item` — item objekt (`name`, `icon`, `rarity`, `type`, `bonuses`, `min_level`, `description`, `set_name`)
- `inv` — inventory záznam nebo `null` (pro `durability`, `upgrade_level`)
- `opts` — `{ price }` — volitelná cena (jen pro shop)

**Logika:**
1. Rarity → CSS třída (`.r-common` atd.) + label (CZ: Běžný / Neobvyklý / Vzácný / Epický / Legendární / Sada)
2. Slot label CZ (weapon → Zbraň, helmet → Helma atd.) přes existující `SLOT_CZ`
3. Upgrade badge: `ul > 0` → `★`/`★★`/`★★★`
4. Stats rows: `Object.entries(item.bonuses || {}).filter(([, v]) => v > 0)` → 2-sloupcový grid
5. Set block: jen pokud `rarity === 'set'` a `item.set_name`
6. Desc block: jen pokud `item.description`
7. Footer: level vlevo, cena vpravo (cena se zobrazí jen pokud `opts.price`)

**Výstup:** HTML string — celý `.tip-d` element.

**Bonus label mapa** (stat key → CZ label):
```
atk → Útok, def → Obrana, hp → Max HP, mp → Max MP,
spd → Rychlost, luck → Štěstí, str → Síla, dex → Obratnost,
int → Inteligence, end → Výdrž
```

### Integrace

#### `market.js` — `renderMarketTable()`

Tržiště renderuje `<table>`, nikoliv karty. Trigger je `.mkt-item-cell` div (první `<td>` každého řádku). Přidat třídu `has-tip` na `.mkt-item-cell` a tooltip s cenou za kus:

```js
`<div class="mkt-item-cell has-tip">
  <div class="mkt-item-icon">${l.item?.icon||'📦'}</div>
  <div>
    <div class="mkt-item-name" style="color:${rc}">${esc(l.item?.name||'?')}</div>
    <div class="mkt-item-type">${l.item?.type||''}</div>
  </div>
  ${l.item ? buildItemTooltipHTML(l.item, null, { price: l.price }) : ''}
</div>`
```

`l.price` je cena za 1 kus — to se zobrazí v tooltip footeru.

#### `inventory.js` — `renderInv()`

```js
// V šabloně inv-card, přidat třídu has-tip a tooltip na konec:
`<div class="inv-card has-tip ..." style="--rc:${rc}" onclick="...">
  ...stávající obsah...
  ${buildItemTooltipHTML(item, inv, {})}
</div>`
```

#### `inventory.js` — `renderEquipStrip()`

Proměnná `invItem` je v `renderEquipStrip` skutečně definována jako `invData.find(i => i.equipped && i.item?.type === s)` — je správné ji předat jako `inv` argument.

```js
// Jen pro zaplněné sloty (item !== null):
`<div class="inv-strip-slot has-tip ..." ...>
  ...stávající obsah...
  ${item ? buildItemTooltipHTML(item, invItem, {}) : ''}
</div>`
```

#### `equipment.js` — `renderEquip()` (funkce `slot()`)

Vždy se předává skutečný `item` (tj. `eq[s.k]`), **nikoli** `displayItem` (transmog). Tooltip zobrazuje reálné staty itemu — to je záměrné, transmog mění jen vizuál, ne hodnoty.

```js
// Na konec šablony eq-slot, jen pokud has:
`<div class="eq-slot has-tip ..." ...>
  ...stávající obsah...
  ${has ? buildItemTooltipHTML(item, invObj, {}) : ''}
</div>`
```

#### `shop.js` — `renderShopItemCards()`

```js
// V šabloně shop-card, přidat has-tip a tooltip s price:
`<div class="shop-card has-tip ..." ...>
  ...stávající obsah...
  ${buildItemTooltipHTML(item, null, { price: item.shop_price })}
</div>`
```

### Overflow fix

Karty mají někdy `overflow: hidden`. Třída `.has-tip` přepíše na `overflow: visible`. Pokud konkrétní karta potřebuje `overflow: hidden` z jiného důvodu (clip dekorace), bude tooltip obalený extra `<div style="position:absolute;inset:0;overflow:visible;pointer-events:none">` — toto řešíme jen pokud narazíme (není předpokládaný problém).

## Invarianty

- Tooltip nenahrazuje detail modal — jen přidává hover preview
- `onclick` zůstává funkční (tooltip je `pointer-events: none`)
- Tooltip je celý client-side, bez extra API volání
- Shop tooltip zobrazuje shop_price; inventář/equip tooltip cenu nezobrazuje
- Mobile: tooltip skryt přes `@media (max-width: 768px) { .tip-d { display: none; } }`
- Z-index: 9999 — nad vším kromě modálů (100) a toastů (200) — **OPRAVA**: 9999 > 100, tedy tooltip by překryl modál. Tooltips se nezobrazí uvnitř modálů (inventář/obchod jsou stránky, ne modály), takže konflikt nevznikne.

## Co se NEMĚNÍ

- Item detail modal (`openItemDetail`) — beze změn
- Backend routes — žádné změny
- Alembic migrace — žádné
- Ostatní JS moduly (quest, arena, guild) — beze změn

## Testování

Manuální ověření:
1. Hover na item v inventáři → tooltip se zobrazí nad kartou s correct rarity barvou
2. Hover na nasazený item v equip stripu → tooltip zobrazí item data
3. Hover na slot ve vybavení (character sheet) → tooltip
4. Hover na item v obchodě → tooltip zobrazí cenu v footeru
5. Hover na item v tržišti (`.mkt-item-cell`) → tooltip zobrazí staty + cenu/ks
6. Kliknutí otevře modal (tooltip neblokuje click)
7. Mobile (< 768px): tooltip se nezobrazí
8. Legendární item: oranžový glow band + oranžová jména
9. Set item: cyan set badge + cyan barvy
