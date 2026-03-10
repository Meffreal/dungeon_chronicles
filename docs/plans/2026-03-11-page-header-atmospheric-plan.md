# Page Header Atmospheric Gradients — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Každá feature stránka dostane vlastní barevnou identitu v page headeru — atmospheric gradient, colored glow, Gothic ornament.

**Architecture:** CSS-only. CSS custom property `--ph-rgb` nastavená per-page selektory. Základní `.page-hdr` bloky v `layout.css` (řádky 143–165) se upraví, za ně se přidají per-page selektory. Žádný JS, žádný HTML zásah.

**Tech Stack:** Vanilla CSS (CSS custom properties, gradients, text-shadow)

---

## Task 1: Uprav `.page-hdr` základní styly

**Files:**
- Modify: `frontend/css/layout.css` (řádky 143–165)

Aktuální stav bloků (pro orientaci):
- `.page-hdr` řádky 143–148 — flex column, padding-bottom, border-bottom pevná bílá, position:relative
- `.page-hdr::after` řádky 149–152 — 60px pevná linka var(--accent)
- `.page-hdr-title` řádky 153–157 — Cinzel Decorative, color:var(--text)
- `.page-hdr-title::before` řádky 158–161 — 3px bar var(--accent)
- `.page-hdr-sub` řádky 162–165 — Cinzel, uppercase, text3

**Step 1: Nahraď celý blok `.page-hdr` až `.page-hdr-sub` (řádky 143–165)**

```css
.page-hdr{
  display:flex;flex-direction:column;gap:4px;
  padding:16px 0 16px;margin-bottom:18px;
  background:linear-gradient(180deg,rgba(var(--ph-rgb,192,57,43),.10) 0%,transparent 100%);
  border-bottom:1px solid rgba(var(--ph-rgb,192,57,43),.25);
  position:relative;
}
.page-hdr::before{
  content:'✦ ━━━ ✦';
  position:absolute;top:4px;left:50%;transform:translateX(-50%);
  font-family:'Cinzel',serif;font-size:0.45rem;letter-spacing:3px;
  color:rgba(var(--ph-rgb,192,57,43),.2);pointer-events:none;white-space:nowrap;
}
.page-hdr::after{
  content:'';position:absolute;bottom:-1px;left:0;right:0;height:1px;
  background:linear-gradient(90deg,rgba(var(--ph-rgb,192,57,43),.5),rgba(var(--ph-rgb,192,57,43),.1),transparent);
}
.page-hdr-title{
  font-family:'Cinzel Decorative',serif;font-size:1.1rem;
  color:var(--text);letter-spacing:.5px;
  display:flex;align-items:center;gap:10px;
  text-shadow:0 0 30px rgba(var(--ph-rgb,192,57,43),.3);
}
.page-hdr-title::before{
  content:'';display:block;width:3px;height:1.1rem;
  background:rgb(var(--ph-rgb,192,57,43));border-radius:2px;flex-shrink:0;
  box-shadow:0 0 8px rgba(var(--ph-rgb,192,57,43),.6);
}
.page-hdr-sub{
  font-family:'Cinzel',serif;font-size:.62rem;letter-spacing:2px;
  text-transform:uppercase;color:var(--text3);padding-left:13px;
}
```

Co se mění oproti originálu:
- `.page-hdr`: přidán `background` s `--ph-rgb`, `border-bottom` s `--ph-rgb` místo pevné bílé, padding upraven na `16px 0`
- `.page-hdr::before`: NOVÉ — Gothic ornament `✦ ━━━ ✦` centrovaný, opacity 0.2 v barvě stránky
- `.page-hdr::after`: `width:60px` → `left:0;right:0` (plná šířka), barva `--ph-rgb` místo `var(--accent)`
- `.page-hdr-title`: přidán `text-shadow` s `--ph-rgb`
- `.page-hdr-title::before`: `background:var(--accent)` → `rgb(var(--ph-rgb,...))` + `box-shadow` glow

**Step 2: Commit**

```bash
git add frontend/css/layout.css
git commit -m "style: page-hdr atmospheric base — ph-rgb system, gothic ornament, colored glow"
```

---

## Task 2: Per-page barevné identity

**Files:**
- Modify: `frontend/css/layout.css` — přidej za `.page-hdr-sub` blok (po řádku 165, před prázdným řádkem 167)

**Step 1: Přidej per-page selektory za `.page-hdr-sub`**

```css
/* ── Per-page color identity ─────────────────────────────────────────────── */
#page-quests       .page-hdr { --ph-rgb: 32,178,170; }
#page-arena        .page-hdr { --ph-rgb: 192,57,43; }
#page-dungeons     .page-hdr { --ph-rgb: 123,47,191; }
#page-boss         .page-hdr { --ph-rgb: 180,20,20; }
#page-shop         .page-hdr { --ph-rgb: 200,120,16; }
#page-market       .page-hdr { --ph-rgb: 200,144,32; }
#page-guild        .page-hdr { --ph-rgb: 42,184,112; }
#page-achievements .page-hdr { --ph-rgb: 212,160,48; }
#page-equipment    .page-hdr { --ph-rgb: 180,130,60; }
#page-inventory    .page-hdr { --ph-rgb: 160,110,50; }
#page-faction      .page-hdr { --ph-rgb: 180,60,180; }
#page-prestige     .page-hdr { --ph-rgb: 212,160,48; }
#page-subclass     .page-hdr { --ph-rgb: 128,48,200; }
#page-attunement   .page-hdr { --ph-rgb: 60,160,220; }
#page-season       .page-hdr { --ph-rgb: 180,80,20; }
#page-crystals     .page-hdr { --ph-rgb: 80,180,220; }
#page-professions  .page-hdr { --ph-rgb: 150,100,50; }
#page-world-events .page-hdr { --ph-rgb: 220,80,40; }
#page-build        .page-hdr { --ph-rgb: 80,160,80; }
#page-weekly       .page-hdr { --ph-rgb: 200,120,16; }
```

**Step 2: Vizuální check**

Otevři hru, přepni na stránku "Questy" → header by měl mít teal glow + teal gradient za titulem.
Přepni na "Arénu" → crimson.
Přepni na "Dungeon" → fialová.

**Step 3: Commit**

```bash
git add frontend/css/layout.css
git commit -m "style: per-page color identity — 20 pages, atmospheric headers"
```
