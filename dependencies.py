from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from .database import TradeBotSession, CryptoBackendSession

async def get_trade_db() -> AsyncGenerator[AsyncSession, None]:
    async with TradeBotSession() as session:
        yield session

async def get_crypto_db() -> AsyncGenerator[AsyncSession, None]:
    async with CryptoBackendSession() as session:
        yield session