import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from database import Base, get_db_url
import models 

async def reset_database():
    db_names = ["trade_bot_db", "crypto_backend_db"]
    
    for db_name in db_names:
        url = get_db_url(db_name)
        print(f"--- Connecting to {db_name} ---")
        
        # === FIX: Disable SSL for Localhost/Proxy ===
        # The Cloud SQL Proxy handles encryption externally. 
        # We must tell asyncpg NOT to use SSL locally, or it hangs/timeouts.
        connect_args = {}
        if "localhost" in url or "127.0.0.1" in url:
            connect_args["ssl"] = False
            
        engine = create_async_engine(url, connect_args=connect_args)
        
        async with engine.begin() as conn:
            print(f"[{db_name}] Dropping Schema public...")
            # NUCLEAR OPTION: Drops everything regardless of metadata
            await conn.execute(text("DROP SCHEMA public CASCADE;"))
            await conn.execute(text("CREATE SCHEMA public;"))
            
            print(f"[{db_name}] Creating New Tables...")
            # Re-grant permissions
            await conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
            
            # Create new tables
            await conn.run_sync(Base.metadata.create_all)
            print(f"[{db_name}] Reset Complete.")
            
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset_database())