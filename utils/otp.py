import random
import string
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

PENDING_OTP = {}

def generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))

def create_otp(chat_id: int, channel_type: str, value: str, expiry_minutes: int = 10):
    otp = generate_otp()
    PENDING_OTP[chat_id] = {
        "otp": otp,
        "type": channel_type,
        "value": value,
        "created_at": datetime.now(),
        "expiry": datetime.now() + timedelta(minutes=expiry_minutes),
        "attempts": 0
    }
    logger.info(f"OTP created for chat {chat_id}, type {channel_type}")
    return otp

def verify_otp(chat_id: int, user_otp: str) -> dict:
    data = PENDING_OTP.get(chat_id)
    
    if not data:
        logger.warning(f"No OTP found for chat {chat_id}")
        return {"success": False, "message": "Koi pending OTP nahi mila."}
    
    if datetime.now() > data["expiry"]:
        PENDING_OTP.pop(chat_id, None)
        logger.warning(f"OTP expired for chat {chat_id}")
        return {"success": False, "message": "OTP expire ho gaya, dobara /signup karo."}
    
    data["attempts"] += 1
    
    if data["attempts"] > 3:
        PENDING_OTP.pop(chat_id, None)
        logger.warning(f"Max OTP attempts reached for chat {chat_id}")
        return {"success": False, "message": "Bahut zyada galat attempts. Dobara /signup karo."}
    
    if user_otp != data["otp"]:
        logger.warning(f"Wrong OTP attempt {data['attempts']} for chat {chat_id}")
        return {"success": False, "message": f"Galat OTP. {3 - data['attempts']} attempts bache hain."}
    
    logger.info(f"OTP verified successfully for chat {chat_id}")
    return {"success": True, "data": data}

def clear_otp(chat_id: int):
    PENDING_OTP.pop(chat_id, None)
    logger.info(f"OTP cleared for chat {chat_id}")
