import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from database import Base, get_db_url
import models  # Important to register models

async def reset_database():
    # Ensure these match your actual Cloud SQL database names
    db_names = ["trade_bot_db", "crypto_backend_db"]
    
    for db_name in db_names:
        url = get_db_url(db_name)
        print(f"--- Connecting to {db_name} at {url.split('@')[1]} ---") # Log connection (hiding password)
        
        engine = create_async_engine(url)
        
        async with engine.begin() as conn:
            print(f"[{db_name}] Dropping Schema public...")
            # NUCLEAR OPTION: Drops everything regardless of metadata
            await conn.execute(text("DROP SCHEMA public CASCADE;"))
            await conn.execute(text("CREATE SCHEMA public;"))
            
            print(f"[{db_name}] Creating New Tables...")
            # Re-grant permissions (standard fix after recreating schema)
            await conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
            
            # Create new tables (EU, US, AS, Users, Invoices)
            await conn.run_sync(Base.metadata.create_all)
            print(f"[{db_name}] Reset Complete.")
            
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset_database())