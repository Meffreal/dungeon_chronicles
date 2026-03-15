from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
import os

from database import init_db
from core.logging import setup_logging, get_logger
from core.cache import init_cache, close_cache
from middleware.rate_limit import RateLimitMiddleware
from middleware.request_id import RequestIdMiddleware
from middleware.instance_id import InstanceIdMiddleware

setup_logging()
log = get_logger(__name__)

# Modely v správném pořadí (FK závislosti)
from models.user         import User           # noqa: F401
from models.item         import Item, InventoryItem  # noqa: F401
from models.guild        import Guild, GuildMessage, GuildDungeon, GuildDungeonContrib, GuildWeeklyQuest, GuildWeeklyContrib  # noqa: F401
from models.character    import Character      # noqa: F401
from models.quest        import Quest, DailyQuestRotation  # noqa: F401
from models.market       import MarketListing  # noqa: F401
from models.notification import Notification   # noqa: F401
from models.arena        import ArenaMatch, Season, SeasonResult  # noqa: F401
from models.achievement  import PlayerAchievement  # noqa: F401
from models.shop_sale    import ShopSale            # noqa: F401
from models.faction      import FactionReputation  # noqa: F401
# Profesní systém
from models.profession   import CharacterProfession  # noqa: F401
from models.runosmith    import Rune, ItemRune        # noqa: F401
from models.diviner      import ProphecyScroll        # noqa: F401
from models.soulforger   import ForgeLog              # noqa: F401
from models.gambler      import Bet, Lottery, LotteryEntry  # noqa: F401
from models.agent        import AgentOperation, AgentIdentity, SabotageEffect  # noqa: F401
from models.fateweaver   import FateBond              # noqa: F401
# Nové combat systémy
from models.world_boss   import WorldBoss, BossParticipation  # noqa: F401
from models.dungeon_run  import DungeonRun                    # noqa: F401
from models.weekly_quest import WeeklyQuestProgress           # noqa: F401
from models.season_pass  import SeasonPass, SeasonPassProgress # noqa: F401
from models.crystal      import CrystalTransaction            # noqa: F401
from models.guild_war    import GuildWar, GuildWarAttack       # noqa: F401
from models.prestige     import PrestigeLog                    # noqa: F401
from models.world_event  import WorldEvent, WorldEventContrib, WorldEventClaim  # noqa: F401
from models.dungeon_modifier import WeeklyDungeonModifier                       # noqa: F401
from models.transmog        import TransmogSlot                                 # noqa: F401
from models.cron_job        import CronJob                                      # noqa: F401
from models.disabled_quest  import DisabledQuest                                # noqa: F401
from models.news            import GameNews                                     # noqa: F401
from models.balance_alert   import BalanceAlert                                  # noqa: F401

from routers import auth, character, quest, inventory, market, arena, notifications, guild, achievements, admin, shop
from routers import faction
from routers import attunement
from routers import profession, runosmith, diviner, soulforger, gambler, agent, fateweaver
from routers import boss, dungeon
from routers import weekly_quest
from routers import season_pass as season_pass_router
from routers import crystals as crystals_router
from routers import guild_war as guild_war_router
from routers import prestige as prestige_router
from routers import world_event as world_event_router
from routers import dungeon_modifier as dungeon_modifier_router
from routers import transmog as transmog_router
from routers import health as health_router
from routers import account as account_router
from routers import news as news_router
from routers import bloodline as bloodline_router
from routers import hall as hall_router
from routers import bugs as bugs_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_cache()
    await init_db()
    try:
        from game.seed import seed
        await seed()
    except Exception as e:
        log.warning("Seed skipped", extra={"data": {"error": str(e)}})
    # Vytvoř první sezónu pokud žádná neexistuje
    try:
        from game.season import ensure_active_season
        await ensure_active_season()
    except Exception as e:
        log.warning("Season init skipped", extra={"data": {"error": str(e)}})

    # Vytvoř sezónní pass pokud žádný neexistuje
    try:
        from game.season_pass_manager import ensure_active_season_pass
        await ensure_active_season_pass()
    except Exception as e:
        log.warning("Season pass init skipped", extra={"data": {"error": str(e)}})

    # Vytvoř World Event pokud žádný není aktivní
    try:
        from routers.world_event import ensure_active_world_event
        await ensure_active_world_event()
    except Exception as e:
        log.warning("World event init skipped", extra={"data": {"error": str(e)}})

    # Vytvoř týdenní dungeon modifikátor pokud žádný není aktivní
    try:
        from routers.dungeon_modifier import ensure_active_modifier
        await ensure_active_modifier()
    except Exception as e:
        log.warning("Dungeon modifier init skipped", extra={"data": {"error": str(e)}})

    # Spusť background tasky
    from tasks.elo_decay import elo_decay_loop
    from tasks.balance_monitor import balance_monitor_loop
    decay_task   = asyncio.create_task(elo_decay_loop())
    monitor_task = asyncio.create_task(balance_monitor_loop())

    log.info("Dungeon Chronicles ready", extra={"data": {"version": "0.7.0"}})
    yield

    # Zastav background tasky při shutdown
    decay_task.cancel()
    monitor_task.cancel()
    for t in (decay_task, monitor_task):
        try:
            await t
        except asyncio.CancelledError:
            pass
    await close_cache()

app = FastAPI(title="Dungeon Chronicles API", version="0.7.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(InstanceIdMiddleware)

app.include_router(auth.router)
app.include_router(character.router)
app.include_router(quest.router)
app.include_router(inventory.router)
app.include_router(market.router)
app.include_router(arena.router)
app.include_router(notifications.router)
app.include_router(guild.router)
app.include_router(achievements.router)
app.include_router(admin.router)
app.include_router(shop.router)
app.include_router(faction.router)
app.include_router(attunement.router)
# Profesní systém
app.include_router(profession.router)
app.include_router(runosmith.router)
app.include_router(diviner.router)
app.include_router(soulforger.router)
app.include_router(gambler.router)
app.include_router(agent.router)
app.include_router(fateweaver.router)
# Nové combat systémy
app.include_router(boss.router)
app.include_router(dungeon.router)
app.include_router(weekly_quest.router)
app.include_router(season_pass_router.router)
app.include_router(crystals_router.router)
app.include_router(guild_war_router.router)
app.include_router(prestige_router.router)
app.include_router(world_event_router.router)
app.include_router(dungeon_modifier_router.router)
app.include_router(transmog_router.router)
app.include_router(health_router.router)
app.include_router(account_router.router)
app.include_router(news_router.router)
app.include_router(bloodline_router.router)
app.include_router(hall_router.router)
app.include_router(bugs_router.router)

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(frontend_path, "index.html"))

    @app.get("/game")
    async def serve_game():
        return FileResponse(os.path.join(frontend_path, "game.html"))

    @app.get("/admin-panel")
    async def serve_admin():
        return FileResponse(os.path.join(frontend_path, "admin.html"))

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.7.0"}
