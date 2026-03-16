# Backend rules — načítá se při práci v /backend

## Combat engine
- Entry point: `game/combat_engine.py` → `run_combat(CombatantConfig, CombatantConfig)`
- `CombatantConfig` fields: atk, def_, hp, mp, spd, luck, class_name, level, talents, talent_t2, subclass, set_bonuses, strategy
- Vždy předej: `talent_t2=char.talent_t2_key or ""` a `set_bonuses=get_set_bonuses(char, db)`
- Status efekty: bleed, poison, stun, shield, burn, weaken, slow, regen
- Soft caps: 0–50 (100%) / 51–150 (70%) / 151+ (30%) — aplikuje `soft_cap_stat()`

## Gold & economy
- VŽDY loguj přes `log_gold(db, char, amount, reason, GoldReason.X)` — nikdy přímá editace
- `GoldReason` enum v `models/economy.py`

## Alembic migrace
- Poslední: `0044_fix_hardcore_flag.py` → příští `0045_`
- Šablona idempotentní guard:
  ```python
  cols = [c['name'] for c in inspect(bind).get_columns('table')]
  if 'col' not in cols: op.add_column(...)
  ```
- Nikdy neupravuj existující migraci

## Route registrace
- Nový router: přidat do `main.py` jako `app.include_router(X.router, prefix="/x", tags=["x"])`
- Nový model: importovat v `main.py` před `create_all`

## Quest timing
- `finish_at = now + duration` při startu; server validuje `finish_at` při collect — nikdy client-side
