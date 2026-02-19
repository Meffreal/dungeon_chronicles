from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from database import init_db

# Modely v správném pořadí (FK závislosti)
from models.user         import User           # noqa: F401
from models.item         import Item, InventoryItem  # noqa: F401
from models.guild        import Guild, GuildMessage, GuildDungeon, GuildDungeonContrib  # noqa: F401
from models.character    import Character      # noqa: F401
from models.quest        import Quest          # noqa: F401
from models.market       import MarketListing  # noqa: F401
from models.notification import Notification   # noqa: F401
from models.arena        import ArenaMatch, Season, SeasonResult  # noqa: F401
from models.achievement  import PlayerAchievement  # noqa: F401

from routers import auth, character, quest, inventory, market, arena, notifications, guild, achievements, admin, shop

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    try:
        from game.seed import seed
        await seed()
    except Exception as e:
        print(f"⚠ Seed warning: {e}")
    # Vytvoř první sezónu pokud žádná neexistuje
    try:
        from game.season import ensure_active_season
        await ensure_active_season()
    except Exception as e:
        print(f"Season init warning: {e}")
    print("✅ Dungeon Chronicles v0.5 připraven!")
    yield

app = FastAPI(title="Dungeon Chronicles API", version="0.6.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(frontend_path, "index.html"))

    @app.get("/game")
    async def serve_game():
        return FileResponse(os.path.join(frontend_path, "game.html"))

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.3.0"}
