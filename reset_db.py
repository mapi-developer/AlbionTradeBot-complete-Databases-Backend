import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import MetaData
from database import Base, get_db_url
import models 

async def reset_database():
    db_names = ["trade_bot_db", "crypto_backend_db"]
    
    for db_name in db_names:
        url = get_db_url(db_name)
        engine = create_async_engine(url)
        
        async with engine.begin() as conn:
            print(f"Dropping and Recreating {db_name}...")
            
            # 1. Reflect and Drop Everything (including old tables like 'Payment')
            def drop_everything(connection):
                meta = MetaData()
                meta.reflect(bind=connection)
                meta.drop_all(bind=connection)
            
            await conn.run_sync(drop_everything)
            
            # 2. Create New Schema
            await conn.run_sync(Base.metadata.create_all)
            
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset_database())