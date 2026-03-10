# Page Header Atmospheric Gradients — Design Doc

**Datum:** 2026-03-11
**Cíl:** Každá feature stránka dostane vlastní barevnou identitu v page headeru — atmospheric gradient, colored glow, Gothic dekorace.

## Mechanika

CSS custom property `--ph-rgb` nastavená per-page selektory v layout.css. Žádný JS, žádný HTML zásah.

## Barevná mapa

| Stránka | RGB |
|---------|-----|
| #page-quests | 32,178,170 |
| #page-arena | 192,57,43 |
| #page-dungeon (boss) | 123,47,191 |
| #page-boss | 180,20,20 |
| #page-shop | 200,120,16 |
| #page-market | 200,144,32 |
| #page-guild | 42,184,112 |
| #page-achievements | 212,160,48 |
| #page-equipment | 180,130,60 |
| default | 192,57,43 |

## Vizuální změny

- `.page-hdr` background: `linear-gradient(180deg, rgba(--ph-rgb,.10), transparent)`
- Levý bar (`::before`) barva → `rgb(--ph-rgb)`
- `::after` linka → plná šířka, `rgba(--ph-rgb,.35)` fade
- Title text-shadow: `0 0 30px rgba(--ph-rgb,.3)`
- Gothic ornament: `::before` na `.page-hdr` — `✦ ━━━ ✦`, opacity 0.15, Cinzel 0.5rem

## Scope

Pouze `frontend/css/layout.css`. Žádné JS ani HTML změny.
