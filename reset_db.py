import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from database import Base, get_db_url
import models # Crucial: Imports all models so SQLAlchemy knows which tables to create

async def reset_database():
    # List of databases to clean
    for db_name in ["trade_bot_db", "crypto_backend_db"]:
        url = get_db_url(db_name)
        engine = create_async_engine(url)
        
        print(f"Resetting {db_name} at {url}...")
        async with engine.begin() as conn:
            # WARNING: This deletes all existing data!
            print(f"Dropping all tables in {db_name}...")
            await conn.run_sync(Base.metadata.drop_all)
            
            print(f"Creating all tables in {db_name}...")
            await conn.run_sync(Base.metadata.create_all)
            
        await engine.dispose()
    print("Database reset complete.")

if __name__ == "__main__":
    asyncio.run(reset_database())