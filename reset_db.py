import asyncio
import os
import sys
import traceback
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from database import Base, get_db_url
import models 

# Force stdout to flush immediately so logs appear in Cloud Build
sys.stdout.reconfigure(line_buffering=True)

async def reset_database():
    print(">>> SCRIPT STARTED: reset_db.py")
    db_names = ["trade_bot_db", "crypto_backend_db"]
    
    for db_name in db_names:
        try:
            url = get_db_url(db_name)
            print(f">>> TARGET URL: {url.replace(os.getenv('DB_PASSWORD', ''), '***')}")
            
            # === SSL CONFIGURATION ===
            connect_args = {}
            # Check for localhost OR 127.0.0.1 to disable SSL for the proxy
            if "localhost" in url or "127.0.0.1" in url:
                print(">>> DETECTED LOCALHOST: Disabling SSL for Cloud SQL Proxy compatibility.")
                connect_args["ssl"] = False
            
            engine = create_async_engine(url, connect_args=connect_args)
            
            print(f">>> CONNECTING to {db_name}...")
            async with engine.begin() as conn:
                print(f"[{db_name}] Dropping Schema public...")
                await conn.execute(text("DROP SCHEMA public CASCADE;"))
                await conn.execute(text("CREATE SCHEMA public;"))
                
                print(f"[{db_name}] Granting Permissions...")
                await conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
                
                print(f"[{db_name}] Creating Tables...")
                await conn.run_sync(Base.metadata.create_all)
                print(f"[{db_name}] SUCCESS.")
                
            await engine.dispose()
            
        except Exception as e:
            print(f"\n!!! CRITICAL ERROR on {db_name} !!!")
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(reset_database())
    except Exception as e:
        print("\n!!! SCRIPT CRASHED !!!")
        traceback.print_exc()
        sys.exit(1)