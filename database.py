import asyncio
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# .env 파일에서 환경 변수 로드
load_dotenv()

# 데이터베이스 설정 (MySQL)
DATABASE_URL = f"mysql+aiomysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"

# 비동기 엔진 생성
async_engine = create_async_engine(DATABASE_URL, echo=False)

# 비동기 세션 설정
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

Base = declarative_base()

# FastAPI 의존성 주입용 비동기 제너레이터 함수
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# async with 구문에서 사용하기 위한 비동기 컨텍스트 매니저 함수
@asynccontextmanager
async def get_db_context():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
