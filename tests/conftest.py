import sys
import os

# 1. Add project root to path so we can import 'models' and 'main'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool 

import models 
from database import Base 
from main import app
from dependencies import get_trade_db, get_crypto_db

# --- CONFIGURATION ---
TEST_TRADE_DB_URL = "sqlite+aiosqlite:///:memory:"
TEST_CRYPTO_DB_URL = "sqlite+aiosqlite:///:memory:"

# --- GLOBAL ENGINES ---
# We keep these global so they persist for the session, 
# but we MUST access them via fixtures in tests to avoid import issues.
_test_trade_engine = create_async_engine(
    TEST_TRADE_DB_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool, 
    echo=False
)

_test_crypto_engine = create_async_engine(
    TEST_CRYPTO_DB_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool, 
    echo=False
)

TestingTradeSession = async_sessionmaker(_test_trade_engine, expire_on_commit=False)
TestingCryptoSession = async_sessionmaker(_test_crypto_engine, expire_on_commit=False)

# --- FIXTURES ---

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_databases():
    """Reset databases before every test."""
    async with _test_trade_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _test_crypto_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    async with _test_trade_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    async with _test_crypto_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# --- EXPOSE ENGINES AS FIXTURES ---
@pytest.fixture
def trade_db_engine():
    """Passes the correct engine instance to tests."""
    return _test_trade_engine

@pytest.fixture
def crypto_db_engine():
    return _test_crypto_engine

# --- OVERRIDES ---
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