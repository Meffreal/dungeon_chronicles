# UI RPG Redesign — Design Doc

**Datum:** 2026-03-11
**Projekt:** Dungeon Chronicles
**Cíl:** Přeměnit UI z "tmavá webová aplikace" na plnohodnotné dark fantasy RPG. 4 fáze, každá jako samostatná PR.

---

## Fáze 1 — Topbar & Navigace

Hra musí vypadat jako RPG hned při vstupu.

- **Topbar:** gotické pozadí s jemnou texturou, oddělení zlatou linkou s ornamentem
- **Charakter chip:** avatar rámeček s class barvou + level badge stylizovaný jako štítek
- **Nav ikony:** hover efekt se září (glow) v accent barvě + aktivní stav s runovou podtržkou
- **Gold display:** zlatá mince ikona, animace při změně
- **Notifikace bell:** pulse animace s gotickým rámečkem

## Fáze 2 — Karty & Panely (Statické prvky)

Nejrozšířenější prvek — ovlivní celý pocit hry.

- **.card redesign:** gotické rohové ornamenty, subtilní border texture
- **Stat panely:** řádky s diamond separátory místo plain textu
- **Item karty:** rarity glow border (commons šedé, epic fialové atd.)
- **Section headers:** ornamentální linka vlevo + dekorativní zakončení vpravo
- **Empty states:** stylizované s atmosferickým textem ("Žádné questy nebyly nalezeny... zatím.")

## Fáze 3 — Animace & Micro-interactions

Váha a dopad každé akce.

- **Tlačítka:** press effect (scale down + glow pulse), ne jen hover color change
- **Quest start/complete:** dramatická animace (rune flash + fanfára toast)
- **Item equip:** slot "přijme" item s krátkým glow efektem
- **Gold změna:** číslo letí animovaně (float up + fade)
- **Combat log:** řádky se "typewritují" postupně
- **Level up:** full-screen overlay s gotickými runami (vylepšení existujícího)

## Fáze 4 — Stránky (postupně)

Deep dive jednotlivých klíčových stránek.

- **Equipment** — 2-pane layout s postavou/siluetou uprostřed, sloty kolem
- **Questy** — quest scroll/pergamen design, NPC avatar + řeč
- **Aréna** — dramatické skóre, PvP versus screen, battle log s ikonkami
- **Hub (město)** — budovy jako ilustrované karty s weather/time of day ambience

---

## Pořadí implementace

`1 → 2 → 3 → 4` — každá fáze je samostatná PR.
