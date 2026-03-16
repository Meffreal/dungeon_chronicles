# Haunted Scroll Tooltip Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Přidat hover tooltip Design D "Haunted Scroll" na všechny item karty — inventář, equip strip, character sheet, obchod, tržiště.

**Architecture:** Jedna CSS sekce v `components.css`, jeden JS helper `buildItemTooltipHTML()` v `ui.js`, pak injekce do 5 renderovacích funkcí. Tooltip je absolutně pozicovaný uvnitř karty, viditelný na hover přes CSS, `pointer-events: none` — nezasahuje do kliknutí.

**Tech Stack:** Vanilla CSS (custom properties, color-mix), Vanilla JS template literals, Google Fonts (Cinzel)

---

## Chunk 1: CSS + Font

### Task 1: Google Fonts v game.html

**Files:**
- Modify: `frontend/game.html:8-9`

Přidat Google Fonts `<link>` za existující preconnect tagy. Aktuálně je v `game.html` jen `preconnect` bez skutečné font URL. `index.html` má plnou URL — přidáme stejnou do `game.html`.

- [ ] **Step 1: Přidat font link do game.html**

Najdi v `frontend/game.html` tyto dva řádky (jsou na pozici 8-9):
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
```

Přidej za ně (jako třetí řádek v `<head>`, před CSS linky):
```html
<link href="https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700;900&family=Cinzel:wght@400;600;700&family=Crimson+Text:ital@0;1&family=Share+Tech+Mono&display=swap" rel="stylesheet">
```

- [ ] **Step 2: Commitni**

```bash
git add frontend/game.html
git commit -m "feat: přidej Google Fonts link do game.html (Cinzel, Crimson Text)"
```

---

### Task 2: Tooltip CSS v components.css

**Files:**
- Modify: `frontend/css/components.css` (append na konec souboru, za řádek 1509)

CSS je přímý přepis z `frontend/tooltip-proposals.html` sekce "VARIANTA D", adaptovaný pro existující CSS vars projektu.

- [ ] **Step 1: Append tooltip CSS na konec `frontend/css/components.css`**

```css

/* ── Item Tooltip D — Haunted Scroll ──────────────────────────────────────── */

/* Trigger wrapper — přidej třídu has-tip na item kartu */
/* overflow: visible !important — nutné: theme.css (načítá se po components.css) definuje
   overflow:hidden na .inv-card, .eq-slot, .inv-strip-slot s nižší specificitou ale later order */
.has-tip { position: relative; overflow: visible !important; }
.has-tip:hover .tip-d { opacity: 1; transform: translateX(-50%) translateY(0); }

/* Skryj tooltip na mobile (dotykové zařízení hover neumí) */
@media (max-width: 768px) { .tip-d { display: none; } }

/* Rarity color vars — !important přebije inline style="--rc:..." na kartách */
.r-common    { --rc: #9d9d9d !important; }
.r-uncommon  { --rc: #1eff00 !important; }
.r-rare      { --rc: #0070dd !important; }
.r-epic      { --rc: #a335ee !important; }
.r-legendary { --rc: #ff8000 !important; }
.r-set       { --rc: #00d4ff !important; }

/* Tooltip base */
.tip-d {
  --rc: #9d9d9d;
  position: absolute;
  bottom: calc(100% + 10px);
  left: 50%;
  transform: translateX(-50%) translateY(6px);
  width: 250px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.22s, transform 0.22s ease-out;
  z-index: 9999;
}

/* Inner wrapper — dark parchment + rarity glow */
.tip-d-inner {
  background:
    radial-gradient(ellipse 100% 50% at 50% 0%,
      color-mix(in srgb, var(--rc) 10%, transparent), transparent 60%),
    linear-gradient(180deg, #141218 0%, #0f0d16 40%, #0b0a12 100%);
  border: 1px solid color-mix(in srgb, var(--rc) 25%, rgba(201,168,76,0.15));
  box-shadow:
    0 0 0 1px rgba(0,0,0,0.7),
    0 16px 48px rgba(0,0,0,0.95),
    0 0 50px color-mix(in srgb, var(--rc) 10%, transparent);
  padding: 0;
  overflow: hidden;
}

/* Top rarity glow band */
.tip-d-glow-band {
  height: 3px;
  background: linear-gradient(90deg,
    transparent 0%, var(--rc) 30%, var(--rc) 70%, transparent 100%);
  opacity: 0.7;
}

.tip-d-body { padding: 12px 14px 10px; }

/* Header: icon + name + rarity */
.tip-d-head {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 9px;
}
.tip-d-ico {
  font-size: 2rem;
  line-height: 1;
  filter: drop-shadow(0 0 8px color-mix(in srgb, var(--rc) 50%, transparent));
  flex-shrink: 0;
  margin-top: 2px;
}
.tip-d-info { flex: 1; min-width: 0; }
.tip-d-name {
  font-family: 'Cinzel', serif;
  font-size: 0.86rem;
  font-weight: 700;
  color: var(--rc);
  text-shadow: 0 0 12px color-mix(in srgb, var(--rc) 50%, transparent);
  line-height: 1.15;
}
.tip-d-rarity-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 3px;
}
.tip-d-rarity-gem {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--rc);
  box-shadow: 0 0 6px var(--rc);
  flex-shrink: 0;
}
.tip-d-rarity-label {
  font-family: 'Cinzel', serif;
  font-size: 0.58rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: color-mix(in srgb, var(--rc) 80%, white 20%);
}
.tip-d-slot-label {
  font-size: 0.65rem;
  font-style: italic;
  color: rgba(216,200,184,0.4);
  margin-top: 2px;
}

/* Upgrade badge (★/★★/★★★) */
.tip-d-upgrade {
  font-family: 'Cinzel', serif;
  font-size: 0.7rem;
  color: var(--clr-gold);
  text-shadow: 0 0 8px rgba(200,160,64,0.5);
  align-self: flex-start;
  flex-shrink: 0;
  margin-top: 1px;
}

/* Ornamental HR */
.tip-d-hr {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 9px;
}
.tip-d-hr-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg,
    transparent, rgba(255,255,255,0.07) 50%, transparent);
}
.tip-d-hr-gem {
  width: 4px; height: 4px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--rc) 50%, transparent);
}

/* Stats 2-column grid */
.tip-d-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 12px;
  margin-bottom: 9px;
}
.tip-d-stat {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 4px;
}
.tip-d-sk {
  font-size: 0.64rem;
  font-style: italic;
  color: rgba(216,200,184,0.42);
}
.tip-d-sv {
  font-family: 'Cinzel', serif;
  font-size: 0.7rem;
  font-weight: 600;
  color: #d4b868;
  text-align: right;
}

/* Set item badge */
.tip-d-set {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  background: rgba(0,212,255,0.05);
  border: 1px solid rgba(0,212,255,0.15);
  border-radius: 2px;
  margin-bottom: 9px;
}
.tip-d-set-gem {
  width: 5px; height: 5px; border-radius: 50%;
  background: #00d4ff;
  box-shadow: 0 0 5px #00d4ff;
  flex-shrink: 0;
}
.tip-d-set-name {
  font-family: 'Cinzel', serif;
  font-size: 0.62rem;
  color: #00d4ff;
  letter-spacing: 0.08em;
}

/* Lore description */
.tip-d-desc {
  font-size: 0.7rem;
  font-style: italic;
  color: rgba(216,200,184,0.48);
  line-height: 1.45;
}

/* Footer: level + price */
.tip-d-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 7px 14px 8px;
  border-top: 1px solid rgba(255,255,255,0.04);
  background: rgba(0,0,0,0.2);
}
.tip-d-lvl {
  font-family: 'Cinzel', serif;
  font-size: 0.6rem;
  color: rgba(216,200,184,0.3);
  letter-spacing: 0.07em;
}
.tip-d-price {
  font-family: 'Cinzel', serif;
  font-size: 0.64rem;
  color: var(--clr-gold);
  opacity: 0.8;
}

/* Triangle pointer */
.tip-d::after {
  content: '';
  position: absolute;
  top: 100%; left: 50%;
  transform: translateX(-50%);
  border: 6px solid transparent;
  border-top-color: color-mix(in srgb, var(--rc) 55%, rgba(201,168,76,0.3));
}
```

- [ ] **Step 2: Commitni**

```bash
git add frontend/css/components.css
git commit -m "feat: přidej Haunted Scroll tooltip CSS (Design D)"
```

**Manuální check:** Otevři hru v prohlížeči — žádné vizuální změny zatím (tooltip CSS je přidaný, ale žádná karta nemá ještě `has-tip` třídu).

---

## Chunk 2: JS Helper

### Task 3: buildItemTooltipHTML v ui.js

**Files:**
- Modify: `frontend/js/ui.js` (append za poslední řádek, řádek 761)

Helper přijme item objekt + volitelný inv záznam + opts a vrátí HTML string pro celý `.tip-d` element.

- [ ] **Step 1: Append helper na konec `frontend/js/ui.js`**

```js

// ── Item Tooltip D — Haunted Scroll ────────────────────────────────────────
const _TIP_RARITY_CLS = {
  common: 'r-common', uncommon: 'r-uncommon', rare: 'r-rare',
  epic: 'r-epic', legendary: 'r-legendary', set: 'r-set',
};
const _TIP_RARITY_LBL = {
  common: 'Běžný', uncommon: 'Neobvyklý', rare: 'Vzácný',
  epic: 'Epický', legendary: 'Legendární', set: 'Sada',
};
const _TIP_STAT_LBL = {
  atk: 'Útok', def: 'Obrana', hp: 'Max HP', mp: 'Max MP',
  spd: 'Rychlost', luck: 'Štěstí', str: 'Síla', dex: 'Obratnost',
  int: 'Inteligence', end: 'Výdrž',
};
const _TIP_UPGRADE_BADGE = ['', '★', '★★', '★★★'];

/**
 * buildItemTooltipHTML(item, inv, opts)
 * item — backend item object (name, icon, rarity, type, bonuses, min_level, description, set_name)
 * inv  — inventory record nebo null (upgrade_level, durability)
 * opts — { price } cena pro shop/market footer, jinak nenastavuj
 */
function buildItemTooltipHTML(item, inv, opts = {}) {
  if (!item) return '';
  const rarCls = _TIP_RARITY_CLS[item.rarity] || 'r-common';
  const rarLbl = _TIP_RARITY_LBL[item.rarity] || item.rarity || '';
  const slotLbl = (typeof SLOT_CZ !== 'undefined' && SLOT_CZ[item.type]) || item.type || '';
  const ul = inv?.upgrade_level || 0;
  const upgradeBadge = ul > 0
    ? `<div class="tip-d-upgrade">${_TIP_UPGRADE_BADGE[ul] || ''}</div>`
    : '';

  const bonusEntries = Object.entries(item.bonuses || {}).filter(([, v]) => v > 0);
  const statsHtml = bonusEntries.length
    ? `<div class="tip-d-hr">
        <div class="tip-d-hr-line"></div>
        <div class="tip-d-hr-gem"></div>
        <div class="tip-d-hr-line"></div>
      </div>
      <div class="tip-d-stats">
        ${bonusEntries.map(([k, v]) => `
          <div class="tip-d-stat">
            <span class="tip-d-sk">${_TIP_STAT_LBL[k] || k}</span>
            <span class="tip-d-sv">+${v}</span>
          </div>`).join('')}
      </div>`
    : '';

  const setHtml = item.rarity === 'set' && item.set_name
    ? `<div class="tip-d-set">
        <div class="tip-d-set-gem"></div>
        <div class="tip-d-set-name">${esc(item.set_name)}</div>
      </div>`
    : '';

  const descHtml = item.description
    ? `<div class="tip-d-desc">${esc(item.description)}</div>`
    : '';

  const lvlStr = item.min_level ? `Lv. ${item.min_level}+` : '';
  const priceStr = opts.price != null ? `${Number(opts.price).toLocaleString('cs')} G` : '';
  const footHtml = (lvlStr || priceStr)
    ? `<div class="tip-d-foot">
        <div class="tip-d-lvl">${lvlStr}</div>
        <div class="tip-d-price">${priceStr}</div>
      </div>`
    : '';

  return `<div class="tip-d ${rarCls}">
    <div class="tip-d-inner">
      <div class="tip-d-glow-band"></div>
      <div class="tip-d-body">
        <div class="tip-d-head">
          <div class="tip-d-ico">${item.icon || '📦'}</div>
          <div class="tip-d-info">
            <div class="tip-d-name">${esc(item.name || '?')}</div>
            <div class="tip-d-rarity-row">
              <div class="tip-d-rarity-gem"></div>
              <div class="tip-d-rarity-label">${rarLbl}</div>
            </div>
            ${slotLbl ? `<div class="tip-d-slot-label">${slotLbl}</div>` : ''}
          </div>
          ${upgradeBadge}
        </div>
        ${statsHtml}
        ${setHtml}
        ${descHtml}
      </div>
      ${footHtml}
    </div>
  </div>`;
}
```

- [ ] **Step 2: Commitni**

```bash
git add frontend/js/ui.js
git commit -m "feat: přidej buildItemTooltipHTML helper (Haunted Scroll tooltip)"
```

**Manuální check:** Otevři konzoli prohlížeče, spusť:
```js
console.log(buildItemTooltipHTML({name:'Test', icon:'⚔️', rarity:'rare', type:'weapon', bonuses:{atk:15,def:5}, min_level:10}, null, {}))
```
Měl by vrátit HTML string s `.tip-d.r-rare`.

---

## Chunk 3: Integrace

### Task 4: Inventář — renderInv()

**Files:**
- Modify: `frontend/js/inventory.js:98-110`

Přidat `has-tip` třídu na `.inv-card` a zavolat `buildItemTooltipHTML` na konci každé karty.

- [ ] **Step 1: Upravit šablonu inv-card v `renderInv()`**

Najdi řádek 98 v `frontend/js/inventory.js`:
```js
    return `<div class="inv-card ${inv.equipped?'equipped':''} ${isSet?'inv-card-set':''}" style="--rc:${rc}"
              onclick="openItemDetail(${JSON.stringify(inv).replace(/"/g,'&quot;')})">
```

Změň na (přidej `has-tip` do class):
```js
    return `<div class="inv-card has-tip ${inv.equipped?'equipped':''} ${isSet?'inv-card-set':''}" style="--rc:${rc}"
              onclick="openItemDetail(${JSON.stringify(inv).replace(/"/g,'&quot;')})">
```

Poté najdi konec šablony (řádek 109) — řádek s `${inv.equipped ? ...}` je poslední obsah, uzavírací `</div>` je na řádku 109. Přidej tooltip těsně před `</div>`:

```js
      ${inv.equipped ? '<div class="inv-card-equipped-badge">NASAZENO</div>' : ''}
      ${buildItemTooltipHTML(item, inv, {})}
    </div>`;
```

- [ ] **Step 2: Commitni**

```bash
git add frontend/js/inventory.js
git commit -m "feat: přidej Haunted Scroll tooltip do inventáře (renderInv)"
```

**Manuální check:** Otevři inventář → hover na item kartu → tooltip se zobrazí nad kartou. Ověř rarity barvy (rare = modrá, legendary = oranžová). Kliknutí stále otevírá detail modal.

---

### Task 5: Inventář — renderEquipStrip()

**Files:**
- Modify: `frontend/js/inventory.js:37-46`

Přidat `has-tip` na zaplněné sloty v equip stripu a tooltip.

- [ ] **Step 1: Upravit šablonu inv-strip-slot v `renderEquipStrip()`**

Najdi řádek 37 v `frontend/js/inventory.js`:
```js
    return `<div class="inv-strip-slot${item ? ' inv-strip-slot-filled' : ' inv-strip-slot-empty'}${durWarning}"
               style="--rc:${rc}"
               data-slot="${s}"
               ${invItem ? `onclick="openItemDetail(${JSON.stringify(invItem).replace(/"/g,'&quot;')})"` : ''}>
```

Změň na (přidej `${item ? ' has-tip' : ''}` do class):
```js
    return `<div class="inv-strip-slot${item ? ' inv-strip-slot-filled' : ' inv-strip-slot-empty'}${durWarning}${item ? ' has-tip' : ''}"
               style="--rc:${rc}"
               data-slot="${s}"
               ${invItem ? `onclick="openItemDetail(${JSON.stringify(invItem).replace(/"/g,'&quot;')})"` : ''}>
```

Poté najdi konec šablony (řádek 44-45) — přidej tooltip před uzavírací `</div>`:
```js
      ${dur !== null
        ? `<div class="inv-strip-dur"><div class="inv-strip-dur-fill" style="width:${dur}%;background:${durCol}"></div></div>`
        : `<div class="inv-strip-dur inv-strip-dur-empty"></div>`}
      ${item ? buildItemTooltipHTML(item, invItem, {}) : ''}
    </div>`;
```

- [ ] **Step 2: Commitni**

```bash
git add frontend/js/inventory.js
git commit -m "feat: přidej Haunted Scroll tooltip do equip stripu (renderEquipStrip)"
```

**Manuální check:** Otevři inventář → hover na nasazený item v horním pásu slotů → tooltip se zobrazí. Prázdné sloty tooltip nemají.

---

### Task 6: Character sheet — renderEquip()

**Files:**
- Modify: `frontend/js/equipment.js:75-90`

Přidat `has-tip` na zaplněné `.eq-slot` a tooltip. Vždy předáme `item` (reálný item, ne transmog), `invObj` (pro durability), bez price.

- [ ] **Step 1: Upravit šablonu eq-slot v `slot()` funkci v `renderEquip()`**

Najdi řádek 75 v `frontend/js/equipment.js`:
```js
    return `<div class="eq-slot eq-mslot-${s.k} ${has?'filled':''} ${hasTmog?'eq-slot-transmogged':''}" style="--slot-rc:${rc}"
```

Změň na (přidej `${has?' has-tip':''}` do class):
```js
    return `<div class="eq-slot eq-mslot-${s.k} ${has?'filled':''} ${hasTmog?'eq-slot-transmogged':''}${has?' has-tip':''}" style="--slot-rc:${rc}"
```

Poté najdi konec šablony (řádek 89) — přidej tooltip před uzavírací `</div>`:
```js
      ${has ? `<div class="rarity-pip" style="background:${rc}" title="${RARITY_CZ[(hasTmog?tmog:item).rarity]||''}"></div>` : ''}
      ${has ? buildItemTooltipHTML(item, invObj, {}) : ''}
    </div>`;
```

Poznámka: `item` je `eq[s.k]` — skutečný vybavený item. `invObj` je `invData.find(...)` s durability. Transmog se nepremiuje do tooltipu — tooltip vždy ukazuje reálné staty.

- [ ] **Step 2: Commitni**

```bash
git add frontend/js/equipment.js
git commit -m "feat: přidej Haunted Scroll tooltip do character sheet (renderEquip)"
```

**Manuální check:** Otevři stránku Vybavení → hover na nasazený slot → tooltip se zobrazí s real item stats. Prázdné sloty tooltip nemají. Pokud je transmog aktivní, tooltip stále ukazuje reálné staty (ne kosmetický item).

---

### Task 7: Obchod — renderShopItemCards()

**Files:**
- Modify: `frontend/js/shop.js:311-333`

Přidat `has-tip` na `.shop-card` a tooltip s cenou.

- [ ] **Step 1: Upravit šablonu shop-card v `renderShopItemCards()`**

Najdi řádek 312 v `frontend/js/shop.js`:
```js
    return `
    <div class="shop-card ${canAfford ? '' : 'shop-card-broke'}" data-rarity="${item.rarity}"
         style="--rc:${rc};--rgb:${rgb}">
```

Změň na (přidej `has-tip`):
```js
    return `
    <div class="shop-card has-tip ${canAfford ? '' : 'shop-card-broke'}" data-rarity="${item.rarity}"
         style="--rc:${rc};--rgb:${rgb}">
```

Poté najdi uzavírací `</div>` karty (řádek 333, těsně za `</div>` footeru na řádku 332):
```js
      </div>
    </div>`;
```

Přidej tooltip před finální `</div>`:
```js
      </div>
      ${buildItemTooltipHTML(item, null, { price: item.shop_price })}
    </div>`;
```

- [ ] **Step 2: Commitni**

```bash
git add frontend/js/shop.js
git commit -m "feat: přidej Haunted Scroll tooltip do obchodu (renderShopItemCards)"
```

**Manuální check:** Otevři Obchod → hover na item kartu → tooltip se zobrazí s rarity barvou a cenou v footeru. Kliknutí na tlačítko Koupit funguje normálně.

---

### Task 8: Tržiště — renderMarketTable()

**Files:**
- Modify: `frontend/js/market.js:56-62`

Tržiště renderuje tabulku. Trigger je `.mkt-item-cell` div (ikona + název v první buňce). Přidat `has-tip` a tooltip s cenou za kus.

- [ ] **Step 1: Upravit `.mkt-item-cell` v `renderMarketTable()`**

Najdi řádek 56 v `frontend/js/market.js`:
```js
            <td>
              <div class="mkt-item-cell">
                <div class="mkt-item-icon">${l.item?.icon||'📦'}</div>
                <div>
                  <div class="mkt-item-name" style="color:${rc}">${esc(l.item?.name||'?')}</div>
                  <div class="mkt-item-type">${l.item?.type||''}</div>
                </div>
              </div>
            </td>
```

Změň na (přidej `has-tip` a tooltip):
```js
            <td>
              <div class="mkt-item-cell has-tip">
                <div class="mkt-item-icon">${l.item?.icon||'📦'}</div>
                <div>
                  <div class="mkt-item-name" style="color:${rc}">${esc(l.item?.name||'?')}</div>
                  <div class="mkt-item-type">${l.item?.type||''}</div>
                </div>
                ${l.item ? buildItemTooltipHTML(l.item, null, { price: l.price }) : ''}
              </div>
            </td>
```

`l.price` je cena za 1 kus (backend vrací cenu/ks, množství je `l.quantity`).

- [ ] **Step 2: Commitni**

```bash
git add frontend/js/market.js
git commit -m "feat: přidej Haunted Scroll tooltip do tržiště (renderMarketTable)"
```

**Manuální check:** Otevři Tržiště → hover na ikonu/název itemu v prvním sloupci tabulky → tooltip se zobrazí s cenou/ks v footeru.

---

## Finální ověření

Po všech commitech prověř vizuálně všech 5 lokací:

| Lokace | Trigger | Očekávané chování |
|--------|---------|-------------------|
| Inventář batoh | hover na item kartu | tooltip nad kartou, rarity barva |
| Equip strip | hover na zaplněný slot | tooltip nad slotem |
| Character sheet | hover na zaplněný eq-slot | tooltip, real staty (ne transmog) |
| Obchod | hover na shop-card | tooltip s cenou v footeru |
| Tržiště | hover na mkt-item-cell | tooltip s cenou/ks |

Ověř edge cases:
- Karta bez bonusů (potion) — stats sekce chybí, tooltip stále zobrazí hlavičku + footer
- Set item — zobrazí cyan set badge s `set_name`
- Legendary item — oranžový glow band + oranžová rarity barva
- Upgrade ★★ item — badge v pravém horním rohu headeru
- Mobile (< 768px, DevTools) — tooltip se nezobrazí
