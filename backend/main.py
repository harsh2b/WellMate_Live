from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uuid
from dotenv import load_dotenv
import os
from chatbot import generate_response
from langchain_community.chat_message_histories import ChatMessageHistory
from auth import signup, verify_otp, login, verify_login_otp
from starlette.middleware.sessions import SessionMiddleware

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Mount static files using a dynamic path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "../static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# app.mount("/static", StaticFiles(directory="../static"), name="static")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "your-secret-key"))

# In-memory session storage
sessions = {}

# Pydantic models for request validation
class PatientInfo(BaseModel):
    name: str
    age: int
    gender: str
    language: str
    phone: str

class ChatRequest(BaseModel):
    session_id: str
    message: str

class SignupRequest(BaseModel):
    phone: str

class OTPRequest(BaseModel):
    identifier: str
    otp: str

class LoginRequest(BaseModel):
    identifier: str

# Serve login page as root
@app.get("/")
def read_root():
    return FileResponse("../static/login.html")

# Signup endpoint
@app.post("/signup")
def signup_endpoint(request: SignupRequest):
    return signup(request.phone)

# Verify OTP for signup
@app.post("/verify-otp")
def verify_otp_endpoint(request: OTPRequest):
    return verify_otp(request.identifier, request.otp)

# Login endpoint
@app.post("/login")
def login_endpoint(request: LoginRequest):
    return login(request.identifier)

# Verify OTP for login and create session
@app.post("/verify-login-otp")
def verify_login_otp_endpoint(request: OTPRequest):
    result = verify_login_otp(request.identifier, request.otp)
    if result["status"] == "success":
        session_id = str(uuid.uuid4())
        name = request.identifier[:5]
        sessions[session_id] = {
            "patient_info": {"name": name, "age": 0, "gender": "Unknown", "language": "English", "phone": request.identifier},
            "chat_history": ChatMessageHistory()
        }
        return {"status": "success", "message": "Login successful", "session_id": session_id}
    return result

# Update patient info endpoint
@app.post("/update-patient")
def update_patient_info(request: dict):
    session_id = request.get("session_id")
    patient_info = request.get("patient_info")
    
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    if not patient_info or not isinstance(patient_info, dict):
        raise HTTPException(status_code=400, detail="Invalid patient info")
    
    required_fields = {"name": "Unknown", "age": 0, "gender": "Unknown", "language": "English", "phone": ""}
    updated_info = {key: patient_info.get(key, default) for key, default in required_fields.items()}
    updated_info["age"] = int(updated_info["age"]) if isinstance(updated_info["age"], (str, int)) else 0
    
    sessions[session_id]["patient_info"] = updated_info
    return {"status": "success"}

# Chat endpoint
@app.post("/chat")
def chat(chat_request: ChatRequest):
    session_id = chat_request.session_id
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    patient_info = session["patient_info"]
    chat_history = session["chat_history"]
    user_message = chat_request.message

    default_info = {"name": "Unknown", "age": 0, "gender": "Unknown", "language": "English", "phone": ""}
    for key, default in default_info.items():
        if key not in patient_info:
            patient_info[key] = default
    patient_info["age"] = int(patient_info["age"]) if isinstance(patient_info["age"], (str, int)) else 0

    system_prompt = (
        "You are a female physician with 30 years of experience in general practice; your name is Dr. Black. "
        f"IMPORTANT PATIENT INFO: The patient's name is {patient_info['name']}, age {patient_info['age']}, gender {patient_info['gender']}. "
        f"You MUST always respond in the patient's preferred language ({patient_info['language']}) using simple, clear sentences. "
        f"Always consider the patient's age ({patient_info['age']}) and gender ({patient_info['gender']}) in your responses. "
        "Act as a doctor: ask clarifying questions to understand symptoms before diagnosing or prescribing. "
        "NEVER use apologetic sentences like 'Sorry to hear that...'. "
        "You MUST use retrieved documents if they exist; otherwise, say 'I don't know'. "
        "DO NOT suggest visiting your clinic, but DO NOT forget to prescribe medicine if needed after a full consultation. "
        "When prescribing medicine, ALWAYS include how to use it (e.g., dosage and timing) and how many days to take it. "
        "Use positive vibes and emojis (e.g., 😊) appropriately. "
        "{context}"
    )

    chat_history.add_user_message(user_message)
    bot_response = generate_response(system_prompt, chat_history, user_message)
    chat_history.add_ai_message(bot_response)
    return {"response": bot_response}