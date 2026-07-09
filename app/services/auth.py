import random
import string
import hashlib
import secrets
import jwt
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.schemas.auth import (
    SignupRequest, VerifyEmailRequest, ResendOtpRequest,
    SigninRequest, OAuthRequest, RefreshRequest,
    ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest
)
from app.services.relationships import relationship_service

# JWT configuration algorithm
JWT_ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hash_val = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
    return f"{salt}${hash_val}"

def verify_password(password: str, hashed_password: str) -> bool:
    try:
        salt, hash_val = hashed_password.split("$")
        check_val = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
        return secrets.compare_digest(hash_val, check_val)
    except Exception:
        return False

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access", "jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh", "jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, settings.REFRESH_SECRET_KEY, algorithm=JWT_ALGORITHM)

def decode_token(token: str, secret: Optional[str] = None) -> Optional[dict]:
    try:
        if secret:
            return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        # Try access token key, fallback to refresh token key
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
        except jwt.PyJWTError:
            return jwt.decode(token, settings.REFRESH_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None

def send_otp_email(to_email: str, otp: str, subject: str = "Verify your email - Aligned") -> bool:
    if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print(f"[SMTP Warning] Credentials missing in .env, skipping email to {to_email}. OTP is {otp}")
        return False
        
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Aligned <{settings.FROM_EMAIL or settings.SMTP_USER}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        plain_body = f"""Welcome to Aligned. Here is your key to get in.
        
Your One-Time Password (OTP) is: {otp}

This code unlocks your account for the next 15 minutes.
If you didn't request this, you can safely ignore this email.
"""
        msg.attach(MIMEText(plain_body, 'plain'))
        
        html_body = f"""
        <html>
        <head>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;1,400&family=Inter:wght@400;500&display=swap');
            </style>
        </head>
        <body style="font-family: 'Inter', Arial, sans-serif; background-color: #EFE7DD; padding: 40px 20px; color: #1A1614; margin: 0;">
            <div style="max-width: 500px; margin: 0 auto; background: #FFFFFF; border-radius: 16px; padding: 40px; box-shadow: 0 10px 25px rgba(26, 22, 20, 0.05); border: 1px solid #C9BDA5;">
                <h1 style="font-family: 'Playfair Display', serif; color: #B8553E; text-align: center; margin-bottom: 8px; font-size: 32px; font-weight: 600; letter-spacing: -0.5px;">Aligned.</h1>
                <p style="font-family: 'Playfair Display', serif; font-style: italic; text-align: center; color: #8A7E6C; margin-top: 0; margin-bottom: 32px; font-size: 16px;">Welcome to Aligned. Here is your key to get in.</p>
                
                <div style="font-size: 36px; font-family: 'Inter', sans-serif; font-weight: 500; text-align: center; margin: 40px 0; letter-spacing: 8px; color: #1A1614; background: #EFE7DD; padding: 24px; border-radius: 12px; border: 1px dashed #B8553E;">
                    {otp}
                </div>
                
                <p style="font-size: 13px; color: #8A7E6C; text-align: center; margin-top: 40px; line-height: 1.6;">
                    This code unlocks your account for the next 15 minutes.<br>If you didn't request this, you can safely ignore this email.
                </p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_body, 'html'))
        
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
        server.quit()
        print(f"[SMTP Success] Sent email to {to_email}")
        return True
    except Exception as e:
        print(f"[SMTP Error] Failed to send email to {to_email}: {e}. Falling back to stdout. OTP is {otp}")
        return False

class AuthService:
    def __init__(self) -> None:
        self.collection = relationship_service.collection

    async def signup(self, payload: SignupRequest) -> Dict[str, Any]:
        email = payload.email.lower()
        password_hash = hash_password(payload.password)
        otp = "".join(random.choices(string.digits, k=6))
        
        # Check existing user
        existing = await self.collection.find_one({"email": email})
        if existing:
            if existing.get("is_verified"):
                raise ValueError("Email already registered")
            
            # Seamless Flow: User exists but is unverified. 
            # Update their password and generate a new OTP.
            await self.collection.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "password_hash": password_hash,
                    "otp": otp
                }}
            )
            existing["id"] = str(existing["_id"])
            send_otp_email(email, otp, subject="Verify your email - Loukarver")
            return existing
            
        # Generate unique secret key for relationship
        secret_key = await relationship_service.generate_unique_secret_key()
        
        new_user = {
            "email": email,
            "password_hash": password_hash,
            "name": email.split("@")[0],
            "is_verified": False,
            "otp": otp,
            "is_aligned": False,
            "partner": None,
            "secret_key": secret_key,
            "city_name": "",
            "relationship_start_date": "",
            "is_long_distance": False
        }
        
        result = await self.collection.insert_one(new_user)
        new_user["id"] = str(result.inserted_id)
        
        # Deliver SMTP verification email
        send_otp_email(email, otp, subject="Verify your email - Loukarver")
        
        return new_user

    async def verify_email(self, payload: VerifyEmailRequest) -> Dict[str, Any]:
        email = payload.email.lower()
        user = await self.collection.find_one({"email": email})
        if not user:
            raise ValueError("User not found")
            
        if user.get("is_verified"):
            raise ValueError("Email already verified")
            
        if user.get("otp") != payload.otp:
            raise ValueError("Invalid OTP code")
            
        await self.collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"is_verified": True}, "$unset": {"otp": ""}}
        )
        
        # Generate tokens for immediate sign-in
        token_data = {"user_id": str(user["_id"]), "email": email}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    async def resend_otp(self, payload: ResendOtpRequest) -> bool:
        email = payload.email.lower()
        user = await self.collection.find_one({"email": email})
        if not user:
            raise ValueError("User not found")
            
        if user.get("is_verified"):
            raise ValueError("Email already verified")
            
        otp = "".join(random.choices(string.digits, k=6))
        await self.collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"otp": otp}}
        )
        
        # Resend SMTP email
        send_otp_email(email, otp, subject="Resend verification email - Loukarver")
        return True

    async def signin(self, payload: SigninRequest) -> Dict[str, Any]:
        email = payload.email.lower()
        user = await self.collection.find_one({"email": email})
        if not user or not user.get("password_hash") or not verify_password(payload.password, user["password_hash"]):
            raise ValueError("Invalid email or password")
            
        if not user.get("is_verified"):
            raise PermissionError("Email not verified")
            
        # Generate tokens
        token_data = {"user_id": str(user["_id"]), "email": email}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        user["id"] = str(user["_id"])
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user
        }

    async def oauth_signin(self, provider: str, token: str) -> Dict[str, Any]:
        import httpx
        
        email = None
        name = "Google User"
        
        if provider == "google":
            # Verify the Google ID Token
            url = f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    raise ValueError("Invalid Google token")
                payload = resp.json()
                email = payload.get("email", "").lower()
                name = payload.get("name", email.split("@")[0].capitalize())
                
                if not email:
                    raise ValueError("No email found in Google token")
        else:
            # For Apple or mocked logic
            import re
            if re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", token):
                email = token.lower()
                name = email.split("@")[0].capitalize()
            else:
                raise ValueError("Invalid mocked token or unsupported provider")

        user = await self.collection.find_one({"email": email})
        if not user:
            # Auto-signup verified OAuth user
            secret_key = await relationship_service.generate_unique_secret_key()
            user = {
                "email": email,
                "password_hash": None,
                "name": name,
                "is_verified": True,
                "is_aligned": False,
                "partner": None,
                "secret_key": secret_key,
                "city_name": "",
                "relationship_start_date": "",
                "is_long_distance": False
            }
            result = await self.collection.insert_one(user)
            user["id"] = str(result.inserted_id)
        else:
            user["id"] = str(user["_id"])
            if not user.get("is_verified"):
                await self.collection.update_one({"_id": user["_id"]}, {"$set": {"is_verified": True}})
                user["is_verified"] = True
                
        token_data = {"user_id": user["id"], "email": email}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user
        }

    async def refresh(self, payload: RefreshRequest) -> str:
        # Pins refresh token validation to settings.REFRESH_SECRET_KEY
        token_payload = decode_token(payload.refresh_token, secret=settings.REFRESH_SECRET_KEY)
        if not token_payload or token_payload.get("type") != "refresh":
            raise ValueError("Invalid or expired refresh token")
            
        user_id = token_payload.get("user_id")
        email = token_payload.get("email")
        
        from bson import ObjectId
        user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("User not found")
            
        return create_access_token({"user_id": user_id, "email": email})

    async def forgot_password(self, payload: ForgotPasswordRequest) -> bool:
        email = payload.email.lower()
        user = await self.collection.find_one({"email": email})
        if not user:
            raise ValueError("User not found")
            
        otp = "".join(random.choices(string.digits, k=6))
        await self.collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"otp": otp}}
        )
        
        # Deliver password reset OTP email
        send_otp_email(email, otp, subject="Password Reset Request - Loukarver")
        return True

    async def reset_password(self, payload: ResetPasswordRequest) -> bool:
        email = payload.email.lower()
        user = await self.collection.find_one({"email": email})
        if not user:
            raise ValueError("User not found")
            
        if user.get("otp") != payload.otp:
            raise ValueError("Invalid OTP code")
            
        password_hash = hash_password(payload.new_password)
        await self.collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"password_hash": password_hash}, "$unset": {"otp": ""}}
        )
        return True

    async def change_password(self, user_id: str, payload: ChangePasswordRequest) -> bool:
        from bson import ObjectId
        user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("User not found")
            
        if not user.get("password_hash") or not verify_password(payload.old_password, user["password_hash"]):
            raise ValueError("Invalid old password")
            
        password_hash = hash_password(payload.new_password)
        await self.collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"password_hash": password_hash}}
        )
        return True

    async def delete_user(self, user_id: str, password: str, target: str = "all") -> bool:
        from bson import ObjectId
        user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("User not found")
            
        if not user.get("password_hash") or not verify_password(password, user["password_hash"]):
            raise ValueError("Invalid password")

        # Define which collections to clean up based on target
        # Vibe Check collections typically start with "vibe_"
        
        # 1. Break alignment to safely unlink partner (if target is aligned or all)
        if target in ["all", "aligned"] and user.get("is_aligned"):
            try:
                await relationship_service.break_alignment(user_id)
            except Exception as e:
                print(f"Failed to break alignment during account deletion: {e}")
                
        # 2. Cleanup user data across specified collections
        collections = await self.collection.database.list_collection_names()
        for coll_name in collections:
            if coll_name == "users":
                continue
                
            # Filter collections based on target
            is_vibe_collection = coll_name.startswith("vibe_")
            if target == "aligned" and is_vibe_collection:
                continue
            if target == "vibe_check" and not is_vibe_collection:
                continue
            
            coll = self.collection.database[coll_name]
            await coll.delete_many({
                "$or": [
                    {"user_id": user_id},
                    {"user_id": ObjectId(user_id)},
                    {"sender_id": user_id},
                    {"sender_id": ObjectId(user_id)},
                    {"recipient_id": user_id},
                    {"recipient_id": ObjectId(user_id)},
                    {"created_by": user_id},
                    {"created_by": ObjectId(user_id)},
                    {"participant_ids": user_id},
                    {"participant_ids": ObjectId(user_id)},
                    {"partner_id": user_id},
                    {"partner_id": ObjectId(user_id)},
                    {"user_id_1": user_id},
                    {"user_id_1": ObjectId(user_id)},
                    {"user_id_2": user_id},
                    {"user_id_2": ObjectId(user_id)}
                ]
            })
            
        # 3. Update or Delete the user document
        if target == "all":
            result = await self.collection.delete_one({"_id": ObjectId(user_id)})
            return result.deleted_count > 0
        elif target == "aligned":
            # Reset aligned-specific fields
            await self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {
                    "city_name": "",
                    "relationship_start_date": "",
                    "is_long_distance": False,
                    "secret_key": None,
                    "is_aligned": False,
                    "partner": None
                }}
            )
            return True
        elif target == "vibe_check":
            # Just return true since we deleted the vibe collections above
            return True
        return False

auth_service = AuthService()
