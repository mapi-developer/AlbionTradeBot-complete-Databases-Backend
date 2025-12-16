from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os

# --- Configuration ---
TRADE_BOT_DB_URL = os.getenv("TRADE_BOT_DB_URL", "postgresql+asyncpg://user:pass@localhost/trade_bot_db")
CRYPTO_BACKEND_DB_URL = os.getenv("CRYPTO_BACKEND_DB_URL", "postgresql+asyncpg://user:pass@localhost/crypto_backend_db")

# --- Engines ---
trade_bot_engine = create_async_engine(TRADE_BOT_DB_URL, echo=False)
crypto_backend_engine = create_async_engine(CRYPTO_BACKEND_DB_URL, echo=False)

# --- Sessions ---
TradeBotSession = async_sessionmaker(trade_bot_engine, expire_on_commit=False)
CryptoBackendSession = async_sessionmaker(crypto_backend_engine, expire_on_commit=False)

# --- Base Model ---
class Base(DeclarativeBase):
    pass