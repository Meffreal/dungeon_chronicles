# Profese v3 — Design Spec

**Datum:** 2026-03-17
**Status:** Schváleno, čeká na implementaci

---

## Přehled

Tři specializované profese propojené reagent ekonomikou. Každý hráč si vybere **jednu profesi navždy** (nebo za velmi vysokou cenu reset). Profese tvoří vzájemnou závislost — nikdo není soběstačný, trh žije.

Stávající implementace profesí (`backend/routers/profession.py`, `backend/game/professions.py`, `backend/models/profession.py`) se **zahodí a přepíše od nuly**. Legacy routery (runosmith, soulforger, diviner, fateweaver, gambler, agent) se odstraní.

---

## Tři profese

### ⚗ Enchanter (Zaklínač)

**Core fantasy:** Vdechuješ předmětům magické vlastnosti. Víš jak je zase rozložit na prach.

**Schopnosti:**
- **Enchant** — přidá magický efekt na item
- **Disenchant** — rozloží item na reagenty
- **Prodej Enchant Scrollů** — na rank 5 může vytvářet scrolly které si jiní hráči koupí na trhu a použijí sami (bez Enchanter profese)

**Rank progression:**

| Rank | Unlock |
|------|--------|
| 1 | Enchant common/uncommon (+atk, +def, +hp) · Disenchant common → Arcane Dust |
| 2 | Enchant rare · Disenchant uncommon/rare → Enchanted Shard |
| 3 | Enchant epic · Dual enchant (2 efekty na 1 item) |
| 4 | Enchant legendary · Disenchant epic/legendary → Void Crystal |
| 5 | Signature enchanty (lifesteal, reflect, %crit) · Výroba Enchant Scrollů pro trh |

**Produkuje reagenty:** Arcane Dust · Enchanted Shard · Void Crystal
**Spotřebovává:** Metal Scraps (Kovář) · Alchemic Extract (Alchymista)

---

### 🧪 Alchymista

**Core fantasy:** Vaříš věci co mění průběh boje. Víš jak každý lektvar rozebrat na součástky.

**Schopnosti:**
- **Brew** — uvaří lektvar nebo elixír
- **Dissolve** — rozloží lektvar na reagenty

**Rank progression:**

| Rank | Unlock |
|------|--------|
| 1 | Základní HP/MP potiony · Dissolve basic → Alchemic Residue |
| 2 | Combat elixíry (temp +atk, +def na 1 souboj) |
| 3 | XP elixír (+25% XP z příštího questu) · Gold elixír · Dissolve advanced → Potent Extract |
| 4 | Speciální elixíry (crit boost, shield on low HP) |
| 5 | Legendary elixíry (multi-soubojové buffery, rare efekty) · Dissolve legendary → Essence Concentrate |

**Produkuje reagenty:** Alchemic Residue · Potent Extract · Essence Concentrate
**Spotřebovává:** Arcane Dust (Enchanter) · Metal Scraps (Kovář)

---

### ⚒ Kovář (Blacksmith)

**Core fantasy:** Ničíš aby ses znovu postavil. Na nejvyšším ranku posouváš gear za hranice legendary.

**Schopnosti:**
- **Destroy** — rozloží item na reagenty (kovové materiály)
- **Upgrade** — povýší item o jeden rarity tier
  - Výstup rank 5: **Soul Crafted** 🩷 (pink) — tier nad Legendary, exkluzivní výstup Kováře

**Rank progression:**

| Rank | Unlock |
|------|--------|
| 1 | Destroy common/uncommon → Metal Scraps · Upgrade common→uncommon |
| 2 | Upgrade uncommon→rare |
| 3 | Destroy rare/epic → Refined Ore · Upgrade rare→epic |
| 4 | Upgrade epic→legendary |
| 5 | Destroy legendary → Soulsteel Fragment · Upgrade legendary→**Soul Crafted** 🩷 |

**Produkuje reagenty:** Metal Scraps · Refined Ore · Soulsteel Fragment
**Spotřebovává:** Void Crystal (Enchanter) · Essence Concentrate (Alchymista)

---

## Reagent ekonomika

```
Enchanter  ──► Arcane Dust, Enchanted Shard, Void Crystal  ──► Alchymista + Kovář
Alchymista ──► Alchemic Residue, Potent Extract, Essence Concentrate ──► Enchanter + Kovář
Kovář      ──► Metal Scraps, Refined Ore, Soulsteel Fragment ──► Enchanter + Alchymista
Questy/Dungeony ──► Raw materiály pro všechny tři (drop)
```

Každá profese je závislá na ostatních dvou. Žádná není soběstačná.

---

## Rarity tier hierarchie

```
Common → Uncommon → Rare → Epic → Legendary → Soul Crafted (pink) → Mythic (red)
```

- **Soul Crafted** — exkluzivní Kovářův výstup, rank 5
- **Mythic** — pouze drop z nejtěžšího endgame contentu, nevyrobitelné

---

## Progression systém

**XP zdroje:**
- Primárně: Enchant, Disenchant, Brew, Dissolve, Destroy, Upgrade
- Sekundárně: questy a dungeony (padají i raw reagenty jako drop)

**Rank-up:** Každý rank odemyká nové schopnosti (success rate improvement = future scope, neimplementovat nyní)

**Počet profesí:** 1 na hráče. Reset možný za vysokou cenu (design later).

---

## Tržiště integrace

Vše vyrobené jde prodat na market:
- Reagenty (Arcane Dust, Metal Scraps, atd.)
- Hotové potiony a elixíry
- Enchant Scrolly (rank 5 Enchanter)
- Enchantnuté itemy
- Soul Crafted itemy

---

## Co se zahazuje (legacy)

Stávající soubory k odstranění/přepsání:
- `backend/routers/profession.py` → přepsat
- `backend/game/professions.py` → přepsat
- `backend/models/profession.py` → přepsat
- `backend/routers/runosmith.py` → smazat
- `backend/routers/soulforger.py` → smazat
- `backend/routers/diviner.py` → smazat
- `backend/routers/fateweaver.py` → smazat
- `backend/routers/gambler.py` → smazat
- `backend/routers/agent.py` → smazat
- Odpovídající modely a migrace pro legacy profese

---

## Open questions (pro implementaci)

- Jaké jsou přesné recipes? (kolik Metal Scraps stojí upgrade common→uncommon?)
- Cooldown na crafting akce, nebo neomezené?
- Stacking reagentů v inventáři — vlastní tabulka nebo rozšíření items?
- Enchant efekty — pevný seznam nebo dynamický systém?
