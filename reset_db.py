import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from database import Base, get_db_url
import models 

async def reset_database():
    db_names = ["trade_bot_db", "crypto_backend_db"]
    
    for db_name in db_names:
        url = get_db_url(db_name)
        engine = create_async_engine(url)
        
        async with engine.begin() as conn:
            print(f"Dropping and Recreating {db_name}...")
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset_database())