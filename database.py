import os
import urllib.parse
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Retrieve individual components from Environment Variables
db_user = os.getenv("DB_USER", "postgres")
db_pass = os.getenv("DB_PASSWORD", "password") # This comes from your Secret
db_host = os.getenv("INSTANCE_CONNECTION_NAME", "localhost") 
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")
NOWPAYMENTS_IPN_SECRET = os.getenv("NOWPAYMENTS_IPN_SECRET")

# DB Names
trade_db_name = os.getenv("DB_NAME_TRADE", "trade_bot_db")
crypto_db_name = os.getenv("DB_NAME_CRYPTO", "crypto_backend_db")

# Function to build URL
def get_db_url(db_name):
    # Retrieve and URL-encode the password
    raw_pass = os.getenv("DB_PASSWORD", "password")
    encoded_pass = urllib.parse.quote_plus(raw_pass)  # <--- USE THIS

    is_ip = "." in db_host and ":" not in db_host
    if os.getenv("K_SERVICE") and not is_ip:
        # Use Unix Socket
        return f"postgresql+asyncpg://{db_user}:{encoded_pass}@/{db_name}?host=/cloudsql/{db_host}"
    else:
        # Use TCP
        return f"postgresql+asyncpg://{db_user}:{encoded_pass}@{db_host}/{db_name}"

# Create Engines
trade_bot_engine = create_async_engine(get_db_url(trade_db_name), echo=False)
crypto_backend_engine = create_async_engine(get_db_url(crypto_db_name), echo=False)

# Create Sessions
TradeBotSession = async_sessionmaker(trade_bot_engine, expire_on_commit=False)
CryptoBackendSession = async_sessionmaker(crypto_backend_engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass