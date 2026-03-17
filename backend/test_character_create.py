import asyncio
import httpx
from sqlalchemy import select
from database import AsyncSessionLocal, init_db
from models.user import User
from jose import jwt
from config import settings
from datetime import datetime, timedelta


async def test():
    # Inicializuj DB
    await init_db()
    
    # Vytvoř testovacího uživatele
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.username == 'testuser'))
        user = existing.scalar_one_or_none()
        if not user:
            user = User(username='testuser', email='test@test.com', password_hash='fake')
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        user_id = user.id
        
        # Vytvoř token
        token_data = {'sub': str(user_id), 'exp': datetime.utcnow() + timedelta(hours=1)}
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        print(f'Token: {token}')
        print(f'User ID: {user_id}')
        
        # Zkus zavolat API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'http://localhost:8000/character/create',
                json={'name': 'TestChar', 'cls': 'warrior', 'faction': None},
                headers={'Authorization': f'Bearer {token}'}
            )
            print(f'Status: {response.status_code}')
            print(f'Response: {response.text}')

if __name__ == '__main__':
    asyncio.run(test())
