import os
import urllib.parse
import secrets
import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from starlette.responses import RedirectResponse
from jose import jwt

# Import your project's dependencies and models
import models
import dependencies

router = APIRouter(tags=["Auth"])

# --- CONFIGURATION (Load from Environment) ---
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_THIS_TO_A_SECURE_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Discord Config
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")

# Google Config
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

# --- UTILS ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def generate_unique_username(email: str) -> str:
    """Generates a username from email. Append random string to ensure uniqueness."""
    base = email.split("@")[0]
    # Remove special chars if needed or keep simple
    random_suffix = secrets.token_hex(2)
    return f"{base}_{random_suffix}"

# --- DISCORD LOGIN ---

@router.get("/login/discord")
async def login_discord(
    code: str, 
    state: str = Query(..., description="Local Flet App redirect URL"), 
    db: AsyncSession = Depends(dependencies.get_crypto_db)
):
    async with httpx.AsyncClient() as client:
        # 1. Exchange Code for Token
        token_resp = await client.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": DISCORD_CLIENT_ID,
                "client_secret": DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": DISCORD_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        if token_resp.status_code != 200:
            print(f"❌ Discord Error: {token_resp.text}")
            raise HTTPException(status_code=400, detail="Invalid Discord Code")
            
        token_data = token_resp.json()
        access_token = token_data.get("access_token")

        # 2. Get User Profile
        user_resp = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        discord_data = user_resp.json()

    # 3. Process Login
    return await process_oauth_login(
        db, 
        email=discord_data.get("email"), 
        discord_id=str(discord_data.get("id")),
        google_id=None,
        local_redirect_url=state
    )

# --- GOOGLE LOGIN ---

@router.get("/login/google")
async def login_google(
    code: str, 
    state: str = Query(..., description="Local Flet App redirect URL"),
    db: AsyncSession = Depends(dependencies.get_crypto_db)
):
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        if token_resp.status_code != 200:
            print(f"❌ Google Error: {token_resp.text}")
            raise HTTPException(status_code=400, detail="Invalid Google Code")
            
        token_data = token_resp.json()
        access_token = token_data.get("access_token")

        user_resp = await client.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        google_data = user_resp.json()

    return await process_oauth_login(
        db, 
        email=google_data.get("email"), 
        discord_id=None,
        google_id=str(google_data.get("id")),
        local_redirect_url=state
    )

# --- CORE LOGIN LOGIC ---

async def process_oauth_login(
    db: AsyncSession, 
    email: str, 
    discord_id: str = None, 
    google_id: str = None, 
    local_redirect_url: str = None
):
    if not email:
        raise HTTPException(status_code=400, detail="Email is required from provider")

    # 1. Check if user exists by OAuth ID
    stmt = select(models.User).where(
        (models.User.discord_id == discord_id) if discord_id else (models.User.google_id == google_id)
    )
    result = await db.execute(stmt)
    user = result.scalars().first()

    # 2. If not found, check by Email (Account linking)
    if not user:
        stmt = select(models.User).where(models.User.email == email)
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        if user:
            # Link the new OAuth ID to the existing email account
            if discord_id: user.discord_id = discord_id
            if google_id: user.google_id = google_id
            await db.commit()
            await db.refresh(user)

    # 3. If still no user, create a new one
    if not user:
        # NOTE: Your User model requires 'username' and 'password'. 
        # We generate a unique username and a random unusable password.
        new_username = generate_unique_username(email)
        random_password = secrets.token_urlsafe(16) 
        
        # We need to hash the password because main.py expects hashed passwords if used there
        # but for now we just store the random string as it won't be used for login.
        
        user = models.User(
            email=email, 
            username=new_username,
            password=f"oauth_generated_{random_password}", 
            discord_id=discord_id, 
            google_id=google_id,
            joined_at=datetime.now(timezone.utc)
        )
        db.add(user)
        try:
            await db.commit()
            await db.refresh(user)
        except Exception:
            # Fallback if username collision (rare but possible)
            await db.rollback()
            user.username = generate_unique_username(email) + "_retry"
            db.add(user)
            await db.commit()
            await db.refresh(user)

    # 4. Generate Token
    # Use 'id' (int) not 'user_id' as per your models.py
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    
    # 5. Redirect
    query_params = {
        "access_token": access_token, 
        "user_id": str(user.id),
        "token_type": "bearer"
    }

    # Decode/Unquote the state URL provided by the client
    unquoted_local_url = urllib.parse.unquote(local_redirect_url)
    
    # Append params safely
    sep = "&" if "?" in unquoted_local_url else "?"
    redirect_to = f"{unquoted_local_url}{sep}{urllib.parse.urlencode(query_params)}"

    return RedirectResponse(redirect_to, status_code=status.HTTP_303_SEE_OTHER)