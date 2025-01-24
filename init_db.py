import asyncio
from database import async_engine, Base
from src.models.auto_ten_min import TenMinModel  # 모델 import

async def init_db():
    async with async_engine.begin() as conn:
        # 기존 테이블 삭제 (필요한 경우)
        # await conn.run_sync(Base.metadata.drop_all)
        
        # 새 테이블 생성
        await conn.run_sync(Base.metadata.create_all)
        print("Database tables created successfully!")

if __name__ == "__main__":
    asyncio.run(init_db())
