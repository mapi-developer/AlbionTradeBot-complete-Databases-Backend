import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from database import Base, get_db_url
import models # Ensure all models are loaded

async def reset_database():
    # You might want to do this for both DBs if you have two
    for db_name in ["trade_bot_db", "crypto_backend_db"]:
        url = get_db_url(db_name)
        engine = create_async_engine(url)
        
        print(f"Resetting {db_name}...")
        async with engine.begin() as conn:
            # WARNING: This deletes all data!
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset_database())