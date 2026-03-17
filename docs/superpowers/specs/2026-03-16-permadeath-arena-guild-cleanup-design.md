# Permadeath — Arena & Guild cleanup

**Datum:** 2026-03-16
**Stav:** Schváleno

## Problém

Po permadeath zůstávají mrtvé postavy viditelné v:
- Aréna: seznam soupeřů, leaderboard, season leaderboard (lze na ně i útočit)
- Cech: seznam členů, počet členů
- Guild master succession nefunguje — leadership zůstane na mrtvé postavě bez přenosu

## Řešení (Přístup B)

### 1. Arena — oprava queries (`routers/arena.py`)

**`get_opponents`** — přidat `Character.is_dead == False` do obou dotazů (ELO range i fallback).

**`attack/{defender_id}`** — přidat `Character.is_dead == False` do načtení obránce. Pokud je obránce mrtvý → `HTTPException(404, "Soupeř nenalezen.")`. Tím se zabrání mutaci `gold`, `arena_rank`, `arena_losses` mrtvé postavy.

**`arena_leaderboard`** — přidat `Character.is_dead == False` do top 20.

**`season_leaderboard`** — přidat `Character.is_dead == False` do top 25.

### 2. Guild — oprava queries (`routers/guild.py`)

**`_member_count`** — přidat `Character.is_dead == False`. Tím se zároveň opraví:
- `join_guild` cap check (záměrné chování — mrtví členové neuvolňují slot automaticky do cleanup, ale po permadeath cleanup již slot uvolněný je)
- `list_guilds` — používá `_member_count`, tedy opraveno jako vedlejší efekt
- `my_guild` → `guild.to_dict(member_count=...)` — tento count pochází z `len(members)`, ne z `_member_count`, proto musí být filter přidán přímo do members query

**`my_guild` members** — přidat `Character.is_dead == False` do dotazu. `member_count=len(members)` pak automaticky zobrazuje správný počet.

**WebSocket auth** (`/guild/ws/{guild_id}`) — po cleanup bude `char.guild_id = None` u mrtvé postavy, takže WS handler ji odmítne (`guild_id != guild_id`). Bezpečné by design, ale pro konzistenci přidat `Character.is_dead == False` do char načtení.

### 3. `_trigger_permadeath` — guild cleanup (`routers/dungeon.py`)

Blok se vloží **po** `db.add(hall_entry)`, **před** `return {...}`. Caller commituje, takže vše musí být nastaveno před returnem.

```
# --- Guild cleanup ---
if char.guild_id is not None:
    guild_res = await db.execute(select(Guild).where(Guild.id == char.guild_id))
    guild = guild_res.scalar_one_or_none()
    if guild and guild.leader_id == char.id:
        # Najdi alive nástupce s nejvyšším levelem
        succ_res = await db.execute(
            select(Character)
            .where(
                Character.guild_id == guild.id,
                Character.is_dead == False,
                Character.id != char.id,
            )
            .order_by(Character.level.desc())
            .limit(1)
        )
        successor = succ_res.scalar_one_or_none()
        if successor:
            guild.leader_id = successor.id
            db.add(Notification(
                character_id=successor.id,
                type=NotifType.SYSTEM,
                title="⚜ Stal ses Guild Masterem!",
                body=f"{char.name} padl v boji. Vedení cechu přechází na tebe.",
            ))
        # else: guild.leader_id zůstane na mrtvé postavě jako owner marker
    char.guild_id = None
```

### 4. Automatické převzetí cechu při vytvoření nové postavy (`routers/character.py`)

Po `db.flush()` (získání `char.id`), před `db.commit()`:

```
# Auto-rejoin: zkontroluj jestli uživatel vlastnil cech (přes mrtvou postavu jako leader marker)
dead_res = await db.execute(
    select(Character)
    .where(Character.user_id == user.id, Character.is_dead == True)
    .order_by(Character.id.desc())  # nejnovější mrtvá postava první
)
for dead_char in dead_res.scalars().all():
    orphan_guild_res = await db.execute(
        select(Guild).where(Guild.leader_id == dead_char.id)
    )
    orphan_guild = orphan_guild_res.scalar_one_or_none()
    if orphan_guild:
        char.guild_id = orphan_guild.id
        orphan_guild.leader_id = char.id
        break  # max jeden cech na uživatele
    # Pokud guild neexistuje (byla rozpuštěna), pokračuj na další mrtvou postavu — silent skip
```

Pokud žádná mrtvá postava neměla cech jako leader, nová postava nevstupuje do žádného cechu (standardní flow).

## Invarianty

- `guild.leader_id` může dočasně ukazovat na `is_dead=True` postavu — pouze jako owner marker
- Tato situace nastane pouze pokud je leader posledním živým členem
- Mrtvé postavy nikdy nejsou vidět v member listu ani jako soupeři v aréně
- Slot v cechu se uvolní okamžitě při permadeath (`char.guild_id = None`)

## Záměrné chování

- `_member_count` s filtrem `is_dead==False` mění cap check v `join_guild` — záměrné, mrtví neblokují slot
- Arena leaderboard cache (TTL 60s) se neinvaliduje při permadeath — mrtvá postava zmizí do 60s, akceptovatelné
- Character obecný leaderboard/search (`/character/leaderboard`, `/character/search`) — mimo scope tohoto fixu, kandidát na follow-up

## Co se NEMĚNÍ

- Hall of Fallen, Bloodline XP — čtou mrtvé postavy záměrně, beze změny
- `_get_char` helper (již filtruje `is_dead == False`) — beze změny
- Žádná Alembic migrace — neměníme schéma
