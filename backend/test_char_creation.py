import asyncio
from sqlalchemy import select
from database import AsyncSessionLocal, init_db
from models.user import User
from models.character import Character, CharacterClass, CLASS_BASE_STATS
from models.quest import Quest, QuestStatus
from models.faction import FactionReputation
from game.factions import FACTIONS

async def test():
    await init_db()
    
    async with AsyncSessionLocal() as db:
        # Create a test user
        user = User(username='testuser2', email='test2@test.com', password_hash='fake')
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Try to create a character manually
        try:
            cls = CharacterClass.WARRIOR
            base = CLASS_BASE_STATS[cls]
            char = Character(
                user_id=user.id,
                name="TestChar2",
                cls=cls.value,
                level=1, xp=0, gold=150,
                strength=base["strength"],
                dexterity=base["dexterity"],
                intelligence=base["intelligence"],
                endurance=base["endurance"],
                luck=base["luck"],
                faction="rad_popele",
            )
            char.recalculate_stats()
            db.add(char)
            await db.flush()
            print(f"Created character with id={char.id}")
            
            # Create quest
            quest = Quest(character_id=char.id, status=QuestStatus.IDLE)
            db.add(quest)
            print("Added quest")
            
            # Create faction rep
            faction_rep = FactionReputation(
                character_id=char.id,
                faction="rad_popele",
                reputation=0,
            )
            db.add(faction_rep)
            print("Added faction reputation")
            
            await db.commit()
            print("Committed successfully")
            
            # Now try to call char.to_dict()
            print("Calling char.to_dict()...")
            char_dict = char.to_dict()
            print(f"char.to_dict() succeeded")
            
            # Now try char_dict_with_equipment
            from routers.character import char_dict_with_equipment
            print("Calling char_dict_with_equipment()...")
            full_dict = await char_dict_with_equipment(char, db)
            print(f"char_dict_with_equipment() succeeded")
            print(f"Keys: {full_dict.keys()}")
            
        except Exception as e:
            import traceback
            print(f"ERROR: {e}")
            traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test())
