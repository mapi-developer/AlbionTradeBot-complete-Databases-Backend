import sys
import os

# --- 1. CRITICAL FIX: Add project root to sys.path ---
# This allows imports like 'import models' to work from inside the tests/ folder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool 

# 2. Imports now work because of sys.path above
import models 
from database import Base 
from main import app
from dependencies import get_trade_db, get_crypto_db

# --- CONFIGURATION ---
TEST_TRADE_DB_URL = "sqlite+aiosqlite:///:memory:"
TEST_CRYPTO_DB_URL = "sqlite+aiosqlite:///:memory:"

# --- ENGINES ---
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
    async with test_trade_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with test_crypto_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
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