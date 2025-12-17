import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
# 1. CRITICAL IMPORT: Needed to keep in-memory DB alive
from sqlalchemy.pool import StaticPool 

# 2. CRITICAL IMPORT: Registers your tables (Item, User) with Base.metadata
import models 
from database import Base 
from main import app
from dependencies import get_trade_db, get_crypto_db

# --- CONFIGURATION ---
TEST_TRADE_DB_URL = "sqlite+aiosqlite:///:memory:"
TEST_CRYPTO_DB_URL = "sqlite+aiosqlite:///:memory:"

# --- ENGINES ---
# We use StaticPool to share the same in-memory DB across setup & tests.
# We use check_same_thread=False because asyncio runs on a different thread.
test_trade_engine = create_async_engine(
    TEST_TRADE_DB_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool, 
    echo=False
)

test_crypto_engine = create_async_engine(
    TEST_CRYPTO_DB_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool, 
    echo=False
)

TestingTradeSession = async_sessionmaker(test_trade_engine, expire_on_commit=False)
TestingCryptoSession = async_sessionmaker(test_crypto_engine, expire_on_commit=False)

# --- FIXTURES ---

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_databases():
    """
    Creates tables before each test and drops them after.
    """
    # Create tables
    async with test_trade_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with test_crypto_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Drop tables (Clean slate for next test)
    async with test_trade_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        
    async with test_crypto_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

async def override_get_trade_db():
    async with TestingTradeSession() as session:
        yield session

async def override_get_crypto_db():
    async with TestingCryptoSession() as session:
        yield session

app.dependency_overrides[get_trade_db] = override_get_trade_db
app.dependency_overrides[get_crypto_db] = override_get_crypto_db

@pytest_asyncio.fixture(scope="function")
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c