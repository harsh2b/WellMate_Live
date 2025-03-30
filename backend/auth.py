import os
import random
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from database import get_db_connection

# Twilio configuration for SMS
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Generate a 6-digit OTP
def generate_otp() -> str:
    return str(random.randint(100000, 999999))

# Send OTP via SMS using Twilio
def send_otp_sms(phone: str, otp: str, purpose: str = "verification") -> bool:
    try:
        message = twilio_client.messages.create(
            body=f"Your OTP for {purpose} is: {otp}. Valid for 5 minutes.",
            from_=TWILIO_PHONE_NUMBER,
            to=phone
        )
        return True
    except TwilioRestException as e:
        print(f"Twilio error: {e}")
        return False

# Signup logic with phone only
def signup(phone: str) -> dict:
    if not phone or not phone.startswith('+') or not phone[1:].isdigit() or len(phone) < 11:
        return {"status": "error", "message": "Invalid phone number format. Use + followed by 10-14 digits."}
    
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT phone FROM users WHERE phone = ?", (phone,))
        if c.fetchone():
            return {"status": "error", "message": "Phone number already exists"}
        
        otp = generate_otp()
        c.execute("INSERT INTO users (phone, otp) VALUES (?, ?)", (phone, otp))
        conn.commit()
        
        if send_otp_sms(phone, otp, "account verification"):
            return {"status": "success", "message": "OTP sent to your phone"}
        return {"status": "error", "message": "Failed to send OTP"}
    finally:
        conn.close()

# Verify OTP for signup
def verify_otp(phone: str, otp: str) -> dict:
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT otp FROM users WHERE phone = ? AND is_verified = 0", (phone,))
        result = c.fetchone()
        if not result:
            return {"status": "error", "message": "Invalid phone or already verified"}
        if result[0] == otp:
            c.execute("UPDATE users SET is_verified = 1, otp = NULL WHERE phone = ?", (phone,))
            conn.commit()
            return {"status": "success", "message": "Account verified"}
        return {"status": "error", "message": "Invalid OTP"}
    finally:
        conn.close()

# Login logic with phone
def login(identifier: str) -> dict:
    if not identifier or not identifier.startswith('+') or not identifier[1:].isdigit() or len(identifier) < 11:
        return {"status": "error", "message": "Invalid phone number format. Use + followed by 10-14 digits."}
    
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT phone, is_verified FROM users WHERE phone = ?", (identifier,))
        result = c.fetchone()
        if not result:
            return {"status": "error", "message": "Phone not registered"}
        if not result[1]:
            return {"status": "error", "message": "Account not verified"}
        
        otp = generate_otp()
        c.execute("UPDATE users SET otp = ? WHERE phone = ?", (otp, identifier))
        conn.commit()
        
        if send_otp_sms(identifier, otp, "login"):
            return {"status": "success", "message": "OTP sent to your phone"}
        return {"status": "error", "message": "Failed to send OTP"}
    finally:
        conn.close()

# Verify OTP for login
def verify_login_otp(identifier: str, otp: str) -> dict:
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT otp FROM users WHERE phone = ? AND is_verified = 1", (identifier,))
        result = c.fetchone()
        if not result:
            return {"status": "error", "message": "Invalid phone or not verified"}
        if result[0] == otp:
            c.execute("UPDATE users SET otp = NULL WHERE phone = ?", (identifier,))
            conn.commit()
            return {"status": "success", "message": "Login successful"}
        return {"status": "error", "message": "Invalid OTP"}
    finally:
        conn.close()