import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from database import Base

# 테스트용 데이터베이스 URL
TEST_DATABASE_URL = "mysql+aiomysql://root:0000@localhost/auto_daenak_test"

@pytest.fixture(scope="session")
def event_loop():
    """pytest-asyncio용 이벤트 루프 픽스처"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    """테스트용 데이터베이스 엔진"""
    engine = create_async_engine(TEST_DATABASE_URL)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def test_session(test_engine):
    """테스트용 데이터베이스 세션"""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()
