# UI Textures + Palette Sweep — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Odstranit starou modrou paletu ze všech feature sekcí + přidat materiálové textury (kov, kámen, pergamen) do panelů.

**Architecture:** CSS-only, žádné JS ani nové soubory. Palette sweep pomocí globálního replace, textury jako CSS `background-image` (SVG data URI + vrstvené gradienty).

**Tech Stack:** Vanilla CSS (CSS vars, gradients, SVG data URI patterns)

---

## Task 1: Palette sweep — theme.css (globální replace)

**Files:**
- Modify: `frontend/css/theme.css`

**Co se mění:** 24 výskytů staré modré palety. Klíčové mapování:

| Stará hodnota | Nová hodnota |
|---------------|--------------|
| `rgba(30,127,184,` | `rgba(192,57,43,` |
| `rgba(56,212,196,` | `rgba(230,126,34,` |
| `#06101e` | `#120806` |
| `#0e1830` | `#1c0e08` |
| `#7ec8f0` | `var(--accent2)` |

**Step 1: Globální replace v theme.css**

Použij replace_all=true pro každý vzor:

1. `rgba(30,127,184,` → `rgba(192,57,43,`
2. `rgba(56,212,196,` → `rgba(230,126,34,`
3. `#06101e` → `#120806`
4. `#0e1830` → `#1c0e08`
5. Najdi `.qloot-time` a změň `color:#7ec8f0` na `color:var(--accent2)`
6. Najdi `.nrc--time` a změň `color:#7ec8f0` na `color:var(--accent2)`

**Step 2: Ověř specifické sekce — shop-npc-stage**

Najdi `.shop-npc-stage` (řádek ~21) a zkontroluj/nahraď gradient:

```css
.shop-npc-stage{display:flex;align-items:center;gap:20px;padding:20px 24px;margin-bottom:20px;background:linear-gradient(135deg,rgba(200,144,32,.06) 0%,var(--panel) 50%,rgba(192,57,43,.06) 100%);border:1px solid rgba(200,144,32,.25);border-radius:8px;position:relative;overflow:hidden;}
```

**Step 3: Zkontroluj crystal modal**

Najdi `.cr-modal` (řádek ~1399) a ověř:
```css
background: linear-gradient(160deg, #120806, #1c0e08);
```
(měl by být již nahrazen Step 1, jen ověř)

**Step 4: Commit**

```bash
git add frontend/css/theme.css
git commit -m "style: palette sweep theme.css — crimson replaces cold blue (24 occurrences)"
```

---

## Task 2: Palette sweep — components.css (globální replace)

**Files:**
- Modify: `frontend/css/components.css`

**Co se mění:** 17 výskytů. Dotčené sekce: `.cls-card`, `.faction-card`, `.strategy-bar`, `.strat-btn`, `.appearance-preview`, `.appearance-avatar-container`, input focus glows.

**Step 1: Globální replace v components.css**

1. `rgba(30,127,184,` → `rgba(192,57,43,`
2. `rgba(56,212,196,` → `rgba(230,126,34,`

**Step 2: Oprav appearance-avatar-container**

Najdi `.appearance-avatar-container` a nahraď — toto je preview okno postavy, teplý dark fantasy ambient je vhodný:

```css
.appearance-avatar-container{display:flex;align-items:center;justify-content:center;margin-bottom:12px;min-height:140px;background:radial-gradient(ellipse at 50% 30%,rgba(192,57,43,.12),rgba(10,3,1,.8));border-radius:8px;padding:10px;position:relative;border:1px solid rgba(192,57,43,.25);}
```

**Step 3: Oprav appearance-avatar drop-shadow**

Najdi `.appearance-avatar` a `.appearance-avatar-img` — nahraď modré drop-shadow na amber:

```css
.appearance-avatar{font-size:4rem;line-height:1;margin-bottom:8px;filter:drop-shadow(0 0 16px rgba(212,160,48,.4));}
.appearance-avatar-img{max-width:130px;max-height:130px;width:auto;height:auto;filter:drop-shadow(0 0 16px rgba(212,160,48,.35));border-radius:8px;object-fit:contain;transition:opacity 0.3s ease;display:block;}
```

**Step 4: Commit**

```bash
git add frontend/css/components.css
git commit -m "style: palette sweep components.css — crimson replaces cold blue (17 occurrences)"
```

---

## Task 3: Kovový topbar — texture

**Files:**
- Modify: `frontend/css/layout.css` (řádek 2 — `.topbar`)

**Co se mění:** Přidat brush-line texture a hloubkový shadow do topbaru.

**Step 1: Najdi `.topbar` (řádek 2) a nahraď**

```css
.topbar{height:50px;flex-shrink:0;display:flex;align-items:center;gap:10px;padding:0 12px;background:rgba(10,5,3,.92);background-image:repeating-linear-gradient(180deg,rgba(255,255,255,.018) 0px,rgba(255,255,255,.018) 1px,transparent 1px,transparent 4px);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);box-shadow:inset 0 -2px 12px rgba(0,0,0,.6),inset 0 1px 0 rgba(255,160,50,.04);position:relative;z-index:30;}
```

Co přibývá:
- `background-image: repeating-linear-gradient(180deg, ...)` — horizontální brush marks 1px/4px cyklus
- `box-shadow: inset 0 -2px 12px rgba(0,0,0,.6)` — hloubka dole
- `inset 0 1px 0 rgba(255,160,50,.04)` — jemný zlatý odlesk nahoře

**Step 2: Commit**

```bash
git add frontend/css/layout.css
git commit -m "style: topbar metal texture — brush lines + depth shadow"
```

---

## Task 4: Kamenný levý panel — SVG pattern

**Files:**
- Modify: `frontend/css/layout.css` (řádek 41 — `.lpanel`)

**Co se mění:** Přidat kamenný brick pattern jako `background-image` nad gradient.

**Step 1: Najdi `.lpanel` (řádek 41) a nahraď**

```css
.lpanel{background:linear-gradient(180deg,#120806,#0a0503);background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='48' height='24'%3E%3Crect x='.5' y='.5' width='47' height='11' fill='none' stroke='%23d8c8b8' stroke-width='.4' stroke-opacity='.04'/%3E%3Crect x='.5' y='12.5' width='23' height='11' fill='none' stroke='%23d8c8b8' stroke-width='.4' stroke-opacity='.04'/%3E%3Crect x='24.5' y='12.5' width='23' height='11' fill='none' stroke='%23d8c8b8' stroke-width='.4' stroke-opacity='.04'/%3E%3C/svg%3E"),linear-gradient(180deg,#120806,#0a0503);border-right:1px solid var(--border);display:flex;flex-direction:column;overflow-y:auto;}
```

SVG pattern detail:
- 48×24px tile — klasický brick offset
- Horní řada: 1 plný blok (48×12)
- Dolní řada: 2 poloïbloky (24×12 každý, offset)
- Stroke: `#d8c8b8` (barva textu) s opacity 0.04 — sotva viditelné, ale přidává hloubku

**Step 2: Také přidej vnitřní shadow na `.portrait-wrap`**

Najdi `.portrait-wrap` a nahraď:
```css
.portrait-wrap{padding:10px;background:rgba(12,6,3,.6);border-bottom:1px solid var(--border);box-shadow:inset 0 -1px 0 rgba(61,26,10,.5);}
```

**Step 3: Commit**

```bash
git add frontend/css/layout.css
git commit -m "style: lpanel stone texture — brick SVG pattern + portrait wrap depth"
```

---

## Task 5: Pergamenové modaly — vrstvené gradienty

**Files:**
- Modify: `frontend/css/components.css` (`.modal` — řádek ~4)

**Co se mění:** Nahradit jednoduché `linear-gradient(160deg,#120806,#1c0e08)` za 4-vrstvý pergamenový efekt.

**Step 1: Najdi `.modal` a nahraď background**

```css
.modal{background:radial-gradient(ellipse at 12% 88%,rgba(50,15,5,.7) 0%,transparent 48%),radial-gradient(ellipse at 88% 12%,rgba(70,25,5,.5) 0%,transparent 45%),radial-gradient(ellipse at 50% 0%,rgba(100,40,10,.15) 0%,transparent 40%),linear-gradient(160deg,#150a05,#1c0e08);border:1px solid var(--border2);border-radius:8px;padding:20px;width:min(500px,94vw);max-height:88vh;overflow-y:auto;transform:translateY(10px);transition:transform .2s;position:relative;box-shadow:0 0 32px rgba(192,57,43,.2),inset 0 0 80px rgba(0,0,0,.3);}
```

Co přibývá oproti předchozímu stavu:
- 3× `radial-gradient`: tmavší levý dolní roh, tmavší pravý horní roh, světlejší střed nahoře
- `inset 0 0 80px rgba(0,0,0,.3)` — vnitřní vignette pro hloubku

**Step 2: Přidej texture do `.overlay`**

Najdi `.overlay` (řádek 2) a přidej subtle noise feel přes background:
```css
.overlay{position:fixed;inset:0;z-index:100;background:rgba(0,0,0,.88);backdrop-filter:blur(8px);display:flex;align-items:center;justify-content:center;opacity:0;pointer-events:none;transition:opacity .2s;}
```
(zvýšit opacity z .85 na .88 pro lepší kontrast s pergamenem)

**Step 3: Commit**

```bash
git add frontend/css/components.css
git commit -m "style: parchment modals — layered radial gradients + vignette depth"
```

---

## Shrnutí pořadí

1. **Palette sweep theme.css** — základ, 24 míst
2. **Palette sweep components.css** — 17 míst + appearance fixes
3. **Kovový topbar** — 2 vlastnosti v 1 řádku
4. **Kamenný panel** — SVG brick pattern
5. **Pergamenové modaly** — 4-vrstvý gradient

Žádné JS změny. Žádné nové soubory. Čistě CSS.
