# Frontend rules — načítá se při práci v /frontend

## JS architektura
- `game.html` načítá skripty přes `<script defer>` — pořadí je kritické
- Pořadí: api→auth→ui→character→equipment→appearance→inventory→shop→arena→quest→dungeon→boss→guild→market→achievements→crystals→prestige→subclass→transmog→world_events→hub→build→profile→onboarding→combat-anim→main
- Global state: `char`, `invData`, `currentAppearance` — po každé akci zavolej `updateUI(char)`

## API a UI utility
- `api(method, path, body)` — async, hází error při selhání
- `toast(msg, type, duration)` — typy POUZE `'s'` / `'e'` / `'i'` (ne 'success'/'error')
- `showPage(id)` — navigace; `openModal(id)` / `closeModal(id)` — modaly přes `.open` CSS class
- `showLoading(id)` / `hideLoading(id)` — loading spinners

## CSS konvence
- `theme.css` — feature styly | `layout.css` — nav/topbar/mobile | `components.css` — sdílené
- Z-index: topbar 30 · level-flash 50 · modals 100 · toasts 200
- CSS vars: `--clr-bg` `--clr-surface` `--clr-accent` `--clr-text` `--clr-muted`
- Modaly: `<div class="overlay" id="modal-X">` — otevírat přes `classList.add('open')`, NE `style.display`

## Design principy
Vyhni se generickému "AI slop" designu:
- Fonty: ne Arial/Inter/Roboto — volej výrazné, kontextuálně vhodné
- Barvy: jasná dominantní paleta s ostrými akcenty; ne fialové gradienty na bílé
- Animace: CSS-first, focus na high-impact momenty (page load, level-up) ne scatter
- Layout: kontext-specifický charakter, ne cookie-cutter gridy
- Pozadí: atmosféra přes gradienty/textury — ne solid color default
