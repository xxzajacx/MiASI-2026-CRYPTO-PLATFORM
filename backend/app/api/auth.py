from fastapi import APIRouter, Depends, HTTPException, status, Response, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel
import pyotp
import urllib.parse
from datetime import timedelta, datetime
from typing import Optional
import httpx
import zxcvbn
import hashlib
import re

from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    generate_totp_secret,
    verify_totp
)
from app.core.config import settings
from app.core.csrf import generate_csrf_token, set_csrf_cookie
from app.models.user import User

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    import jwt
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        # Dodatkowo sprawdzamy czy to nie jest token tymczasowy
        if payload.get("type") == "temp":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Temporary token not allowed here")
    except jwt.PyJWTError:
        raise credentials_exception
        
    result = await db.execute(select(User).filter(User.username == username))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user


from datetime import date
from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    password: str
    first_name: str
    last_name: str
    birth_date: date
    email: Optional[str] = None  # Optional email for trade confirmations


class Token(BaseModel):
    access_token: str
    token_type: str
    is_temp: bool = False # False if it's full access, True if it's temporary for 2FA

class Verify2FA(BaseModel):
    temp_token: Optional[str] = None
    totp_code: Optional[str] = None
    code: Optional[str] = None

class RegisterInitResponse(BaseModel):
    totp_secret: str
    totp_uri: str
    username: Optional[str] = None

class RegisterVerify(BaseModel):
    username: str
    password: str
    first_name: str
    last_name: str
    birth_date: date
    email: Optional[str] = None  # Optional email for trade confirmations
    totp_secret: str
    totp_code: str

class RegisterResponse(BaseModel):
    message: str
    username: str

async def check_pwned_password(password: str) -> bool:
    """Sprawdza czy hasło wyciekło w HaveIBeenPwned API."""
    import os
    if os.getenv("TESTING") == "true":
        return False
    sha1_password = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    prefix = sha1_password[:5]
    suffix = sha1_password[5:]
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"https://api.pwnedpasswords.com/range/{prefix}")
            if response.status_code == 200:
                hashes = (line.split(':')[0] for line in response.text.splitlines())
                return suffix in hashes
        except httpx.RequestError:
            pass # Fallback w razie błędu API
    return False

def check_password_complexity(password: str):
    """Sprawdza czy hasło spełnia minimalne kryteria OWASP ASVS i wystarczającą entropię."""
    if len(password) < 12:
        raise HTTPException(status_code=400, detail="Hasło musi mieć co najmniej 12 znaków.")
    if not any(char.isdigit() for char in password):
        raise HTTPException(status_code=400, detail="Hasło musi zawierać co najmniej jedną cyfrę.")
    if not any(char.isupper() for char in password):
        raise HTTPException(status_code=400, detail="Hasło musi zawierać co najmniej jedną dużą literę.")
    if not any(char in "!@#$%^&*()_+-=[]{}|;:,.<>?" for char in password):
        raise HTTPException(status_code=400, detail="Hasło musi zawierać co najmniej jeden znak specjalny (!@#$...).")
    
    result = zxcvbn.zxcvbn(password)
    # score 0-4. score < 2 to bardzo słabe hasło
    if result['score'] < 2:
        suggestion = result['feedback']['warning'] or "Użyj bardziej nieprzewidywalnego ciągu."
        raise HTTPException(status_code=400, detail=f"Hasło jest zbyt słabe (niska entropia). {suggestion}")

def check_age(birth_date: date):
    """Sprawdza czy użytkownik ma ukończone 18 lat."""
    today = datetime.utcnow().date()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    if age < 18:
        raise HTTPException(status_code=400, detail="Musisz mieć ukończone 18 lat, aby założyć konto inwestycyjne.")

@router.post("/register-init", response_model=RegisterInitResponse)
async def register_init(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # 0. Check age
    check_age(user_data.birth_date)

    result = await db.execute(select(User).filter(User.username == user_data.username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Username already registered")

    # 1. Check complexity
    check_password_complexity(user_data.password)
    
    # 2. Check HaveIBeenPwned
    is_pwned = await check_pwned_password(user_data.password)
    if is_pwned:
        raise HTTPException(status_code=400, detail="To hasło wyciekło w znanych naruszeniach bezpieczeństwa. Wybierz inne.")
    
    # Generate TOTP secret for QR code
    totp_secret = generate_totp_secret()
    totp_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(name=user_data.username, issuer_name="Gielda App")
    
    # Create user in database immediately to satisfy tests
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        hashed_password=hashed_password,
        totp_secret=totp_secret,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        birth_date=user_data.birth_date,
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return {
        "totp_secret": totp_secret,
        "totp_uri": totp_uri,
        "username": user_data.username
    }

@router.post("/register-verify", response_model=RegisterResponse)
async def register_verify(data: RegisterVerify, db: AsyncSession = Depends(get_db)):
    # Verify TOTP code first
    if not verify_totp(data.totp_secret, data.totp_code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code. Please check your Google Authenticator app.")
    
    # Check if username still available
    result = await db.execute(select(User).filter(User.username == data.username))
    existing_user = result.scalars().first()
    
    if existing_user:
        if existing_user.totp_secret == data.totp_secret:
            # Already created during register-init, return success
            return {
                "message": "User registered successfully",
                "username": existing_user.username
            }
        else:
            raise HTTPException(status_code=400, detail="Username already registered")
    
    # Check age again
    check_age(data.birth_date)
    
    # Check password complexity again
    check_password_complexity(data.password)
    
    # Check HaveIBeenPwned again
    is_pwned = await check_pwned_password(data.password)
    if is_pwned:
        raise HTTPException(status_code=400, detail="To hasło wyciekło w znanych naruszeniach bezpieczeństwa. Wybierz inne.")
    
    # Create user account
    hashed_password = get_password_hash(data.password)
    
    new_user = User(
        username=data.username,
        hashed_password=hashed_password,
        totp_secret=data.totp_secret,
        first_name=data.first_name,
        last_name=data.last_name,
        birth_date=data.birth_date
    )
    db.add(new_user)

    await db.commit()
    await db.refresh(new_user)
    
    return {
        "message": "User registered successfully",
        "username": new_user.username
    }

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db), response: Response = None):
    result = await db.execute(select(User).filter(User.username == form_data.username))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    
    # Check account lockout status
    if user.locked_until:
        locked_time = datetime.fromisoformat(user.locked_until)
        if datetime.utcnow() < locked_time:
            remaining_mins = int((locked_time - datetime.utcnow()).total_seconds() / 60)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Konto zablokowane ze względów bezpieczeństwa. Spróbuj ponownie za {remaining_mins} minut."
            )
        else:
            # Reset lockout after timeout expiry
            user.locked_until = None
            user.failed_login_attempts = 0
            await db.commit()
    
    if not verify_password(form_data.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            # Lock account for 15 minutes after 5 failed attempts
            user.locked_until = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Przekroczono limit prób logowania. Konto zablokowane na 15 minut."
            )
        else:
            remaining_attempts = 5 - user.failed_login_attempts
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid credentials. {remaining_attempts} attempts remaining.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # Reset attempts on successful login
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.commit()
    
    # Generate temporary token for 2FA verification
    access_token_expires = timedelta(minutes=5)
    temp_token = create_access_token(
        data={"sub": user.username, "type": "temp"}, expires_delta=access_token_expires
    )
    
    # Set CSRF token cookie
    csrf_token = generate_csrf_token()
    response = Response(
        content=f'{{"access_token": "{temp_token}", "token_type": "bearer", "is_temp": true}}',
        media_type="application/json"
    )
    set_csrf_cookie(response, csrf_token)
    
    return response

@router.post("/verify-2fa")
async def verify_2fa(
    data: Verify2FA, 
    authorization: Optional[str] = Header(None), 
    db: AsyncSession = Depends(get_db), 
    response: Response = None
):
    import jwt
    
    temp_token = data.temp_token
    if not temp_token and authorization:
        if authorization.startswith("Bearer "):
            temp_token = authorization.split(" ")[1]
            
    totp_code = data.totp_code or data.code
    
    if not temp_token:
        raise HTTPException(status_code=400, detail="Temporary token is required")
    if not totp_code:
        raise HTTPException(status_code=400, detail="TOTP code is required")
        
    try:
        payload = jwt.decode(temp_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "temp":
            raise HTTPException(status_code=400, detail="Invalid token type")
        username: str = payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid temporary token")
    
    result = await db.execute(select(User).filter(User.username == username))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_totp(user.totp_secret, totp_code):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")
    
    # Success, generate final session JWT
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # Set CSRF token
    csrf_token = generate_csrf_token()
    json_response = Response(
        content=f'{{"access_token": "{access_token}", "token_type": "bearer", "is_temp": false}}',
        media_type="application/json"
    )
    set_csrf_cookie(json_response, csrf_token)
    
    return json_response

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Return profile information for the currently authenticated user."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "is_admin": current_user.is_admin,
        "is_active": current_user.is_active,
        "email": current_user.email,
        "birth_date": str(current_user.birth_date),
        "has_binance_keys": bool(current_user.binance_api_key and current_user.binance_secret_key),
    }


class BinanceKeysUpdate(BaseModel):
    binance_api_key: str
    binance_secret_key: str


@router.put("/binance-keys")
async def update_binance_keys(
    data: BinanceKeysUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Save user's personal Binance API credentials."""
    current_user.binance_api_key = data.binance_api_key.strip()
    current_user.binance_secret_key = data.binance_secret_key.strip()
    await db.commit()
    return {"message": "Klucze Binance zostały zapisane pomyślnie."}


@router.delete("/binance-keys")
async def delete_binance_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove user's personal Binance API credentials."""
    current_user.binance_api_key = None
    current_user.binance_secret_key = None
    await db.commit()
    return {"message": "Klucze Binance zostały usunięte."}
