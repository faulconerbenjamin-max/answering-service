import os
import sqlite3
from datetime import datetime
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import HTMLResponse
from twilio.twiml.voice_response import VoiceResponse, Gather
from jose import jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-now")

def get_db():
    conn = sqlite3.connect("answering.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS businesses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        phone_number TEXT UNIQUE,
        forwarding_number TEXT,
        subscription_status TEXT DEFAULT 'trial',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS call_configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        business_id INTEGER NOT NULL,
        greeting TEXT,
        questions TEXT,
        send_to_email TEXT,
        is_active INTEGER DEFAULT 1
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS call_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        business_id INTEGER NOT NULL,
        caller_number TEXT,
        answers TEXT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        call_sid TEXT UNIQUE
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS pending_signups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        business_name TEXT NOT NULL,
        contact_email TEXT NOT NULL,
        phone_to_forward TEXT NOT NULL,
        notes TEXT,
        status TEXT DEFAULT 'pending',
        submitted_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

init_db()

# ========== MAIN WEBHOOK FOR INCOMING CALLS ==========
@app.post("/twilio/incoming")
async def twilio_incoming(request: Request):
    form = await request.form()
    from_number = form.get('From', 'Unknown')
    call_sid = form.get('CallSid')
    
    resp = VoiceResponse()
    
    # Main menu for demo lines
    gather = Gather(num_digits=1, action="/twilio/menu", method="POST")
    gather.say("Welcome to Call-Forward. Press 1 for Doctor's Office demo. Press 2 for Restaurant demo. Press 3 for Plumbing demo. Press 4 for Salon demo. Press 5 to speak with sales.")
    resp.append(gather)
    
    return Response(content=str(resp), media_type="application/xml")

@app.post("/twilio/menu")
async def handle_menu(request: Request):
    form = await request.form()
    digits = form.get('Digits')
    from_number = form.get('From', 'Unknown')
    call_sid = form.get('CallSid')
    
    resp = VoiceResponse()
    
    if digits == "1":
        # Doctor Demo
        gather = Gather(input='speech', action="/twilio/doctor/name", method="POST", speech_timeout="auto")
        gather.say("Thank you for calling Dr. Feelgood. If this is an emergency, please hang up and dial 911. For non-emergency appointments, please tell me your name and which doctor you normally see.")
        resp.append(gather)
    
    elif digits == "2":
        # Restaurant Demo
        gather = Gather(input='speech', action="/twilio/restaurant/order", method="POST", speech_timeout="auto")
        gather.say("Thank you for calling Pizza Palace. Please go ahead with your order when you're ready.")
        resp.append(gather)
    
    elif digits == "3":
        # Plumbing Demo
        gather = Gather(input='speech', action="/twilio/plumber/issue", method="POST", speech_timeout="auto")
        gather.say("Thank you for calling Roto Rooter Emergency Plumbing. Please tell me your name and what's the issue?")
        resp.append(gather)
    
    elif digits == "4":
        # Salon Demo
        gather = Gather(input='speech', action="/twilio/salon/service", method="POST", speech_timeout="auto")
        gather.say("Thank you for calling Nail Nirvana. Please tell me what service you'd like and which tech you prefer.")
        resp.append(gather)
    
    elif digits == "5":
        resp.say("Please visit our website at call-forward.org to sign up or contact us at hello@call-forward.org. Goodbye!")
    
    else:
        resp.say("Invalid option. Goodbye!")
    
    return Response(content=str(resp), media_type="application/xml")

# ========== DOCTOR DEMO FLOW ==========
@app.post("/twilio/doctor/name")
async def doctor_name(request: Request):
    form = await request.form()
    speech_result = form.get('SpeechResult', '')
    
    resp = VoiceResponse()
    gather = Gather(input='speech', action="/twilio/doctor/appointment", method="POST", speech_timeout="auto")
    gather.say(f"Thank you. Dr. Smith is fully booked today and tomorrow. However, we have an opening on Thursday at 2:15 PM or Friday at 10:30 AM. Which works better for you?")
    resp.append(gather)
    return Response(content=str(resp), media_type="application/xml")

@app.post("/twilio/doctor/appointment")
async def doctor_appointment(request: Request):
    form = await request.form()
    appointment_time = form.get('SpeechResult', '')
    
    resp = VoiceResponse()
    resp.say(f"Great! Your appointment is confirmed. This was a demo of Call-Forward. Visit call-forward.org to set this up for your business. Goodbye!")
    return Response(content=str(resp), media_type="application/xml")

# ========== RESTAURANT DEMO FLOW ==========
@app.post("/twilio/restaurant/order")
async def restaurant_order(request: Request):
    form = await request.form()
    order = form.get('SpeechResult', '')
    
    resp = VoiceResponse()
    gather = Gather(input='speech', action="/twilio/restaurant/confirm", method="POST", speech_timeout="auto")
    gather.say(f"Let me repeat that: {order}. Is that correct? Say yes or no.")
    resp.append(gather)
    return Response(content=str(resp), media_type="application/xml")

@app.post("/twilio/restaurant/confirm")
async def restaurant_confirm(request: Request):
    form = await request.form()
    confirm = form.get('SpeechResult', '')
    
    resp = VoiceResponse()
    resp.say("Great! Your order will be ready in 25 minutes. This was a demo of Call-Forward. Visit call-forward.org to set this up for your business. Goodbye!")
    return Response(content=str(resp), media_type="application/xml")

# ========== PLUMBER DEMO FLOW ==========
@app.post("/twilio/plumber/issue")
async def plumber_issue(request: Request):
    form = await request.form()
    issue = form.get('SpeechResult', '')
    
    resp = VoiceResponse()
    gather = Gather(input='speech', action="/twilio/plumber/address", method="POST", speech_timeout="auto")
    gather.say("Got it. I'm dispatching a plumber. What's your address?")
    resp.append(gather)
    return Response(content=str(resp), media_type="application/xml")

@app.post("/twilio/plumber/address")
async def plumber_address(request: Request):
    form = await request.form()
    address = form.get('SpeechResult', '')
    
    resp = VoiceResponse()
    resp.say("A plumber will arrive within 60 minutes. This was a demo of Call-Forward. Visit call-forward.org to set this up for your business. Goodbye!")
    return Response(content=str(resp), media_type="application/xml")

# ========== SALON DEMO FLOW ==========
@app.post("/twilio/salon/service")
async def salon_service(request: Request):
    form = await request.form()
    service = form.get('SpeechResult', '')
    
    resp = VoiceResponse()
    gather = Gather(input='speech', action="/twilio/salon/time", method="POST", speech_timeout="auto")
    gather.say(f"Great choice. We have openings today at 2 PM or tomorrow at 11 AM. Which works for you?")
    resp.append(gather)
    return Response(content=str(resp), media_type="application/xml")

@app.post("/twilio/salon/time")
async def salon_time(request: Request):
    form = await request.form()
    time = form.get('SpeechResult', '')
    
    resp = VoiceResponse()
    resp.say("Your appointment is confirmed. This was a demo of Call-Forward. Visit call-forward.org to set this up for your business. Goodbye!")
    return Response(content=str(resp), media_type="application/xml")

# ========== HEALTH CHECK ==========
@app.get("/")
async def home():
    return {"message": "Call-Forward.org API is live!", "status": "healthy"}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
