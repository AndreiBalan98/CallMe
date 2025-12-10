from fastapi import FastAPI, Form, Response
from fastapi.responses import FileResponse
from openai import OpenAI
import logging
import os
import hashlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()
client = OpenAI()

# Directory for audio files
AUDIO_DIR = "/tmp/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# In-memory conversation storage per call
conversations: dict[str, list[dict]] = {}

SYSTEM_PROMPT = """Ești un asistent vocal prietenos care vorbește în română.
Răspunde concis și natural, ca într-o conversație telefonică.
La finalul fiecărui răspuns în care ai rezolvat cererea utilizatorului, întreabă politicos dacă mai poți ajuta cu ceva sau dacă e ok să închizi.
Când utilizatorul confirmă că poate închide (ex: "da", "ok", "gata", "pa", "la revedere"), răspunde cu exact: "ÎNCHIDE_APEL" la început, urmat de un mesaj scurt de rămas bun."""

# TTS Settings
TTS_MODEL = "tts-1"
TTS_VOICE = "nova"  # Feminine, warm voice
LANGUAGE = "ro-RO"

# Base URL for audio files - will be set from request
BASE_URL = None


def generate_audio(text: str, call_sid: str) -> str:
    """Generate audio file using OpenAI TTS and return filename."""
    # Create unique filename based on call_sid and text hash
    text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
    filename = f"{call_sid}_{text_hash}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)
    
    # Generate audio
    response = client.audio.speech.create(
        model=TTS_MODEL,
        voice=TTS_VOICE,
        input=text,
        response_format="mp3"
    )
    
    # Save to file
    response.stream_to_file(filepath)
    logger.info(f"[{call_sid}] Generated audio: {filename}")
    
    return filename


def get_llm_response(call_sid: str, user_message: str) -> str:
    if call_sid not in conversations:
        conversations[call_sid] = []
    
    conversations[call_sid].append({"role": "user", "content": user_message})
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversations[call_sid]
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=5000,
        temperature=0.7
    )
    
    assistant_message = response.choices[0].message.content
    conversations[call_sid].append({"role": "assistant", "content": assistant_message})
    
    return assistant_message


def twiml_response(content: str) -> Response:
    return Response(content=content, media_type="application/xml")


def cleanup_audio(call_sid: str):
    """Remove all audio files for a call."""
    for filename in os.listdir(AUDIO_DIR):
        if filename.startswith(call_sid):
            try:
                os.remove(os.path.join(AUDIO_DIR, filename))
                logger.info(f"[{call_sid}] Cleaned up: {filename}")
            except Exception as e:
                logger.error(f"[{call_sid}] Failed to clean {filename}: {e}")


@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve generated audio files."""
    filepath = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="audio/mpeg")
    return Response(status_code=404)


@app.post("/voice")
async def voice_webhook(
    CallSid: str = Form(...),
    SpeechResult: str = Form(None),
    Digits: str = Form(None),
):
    logger.info(f"[{CallSid}] Incoming request - SpeechResult: {SpeechResult}, Digits: {Digits}")
    
    # First call - no input yet
    if not SpeechResult:
        logger.info(f"[{CallSid}] New call - sending greeting")
        
        # Generate greeting audio
        greeting_text = "Salut, cu ce te pot ajuta?"
        audio_filename = generate_audio(greeting_text, CallSid)
        
        # Fallback text for no response
        no_response_text = "Nu am auzit nimic. La revedere!"
        no_response_audio = generate_audio(no_response_text, CallSid)
        
        return twiml_response(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>/audio/{audio_filename}</Play>
    <Gather input="speech" language="{LANGUAGE}" speechTimeout="auto" action="/voice" method="POST">
    </Gather>
    <Play>/audio/{no_response_audio}</Play>
</Response>""")
    
    # Log user speech
    logger.info(f"[{CallSid}] USER: {SpeechResult}")
    
    # Get LLM response
    llm_response = get_llm_response(CallSid, SpeechResult)
    logger.info(f"[{CallSid}] ASSISTANT: {llm_response}")
    
    # Check if call should end
    if llm_response.startswith("ÎNCHIDE_APEL"):
        goodbye_message = llm_response.replace("ÎNCHIDE_APEL", "").strip()
        logger.info(f"[{CallSid}] Ending call")
        
        # Generate goodbye audio
        audio_filename = generate_audio(goodbye_message, CallSid)
        
        # Cleanup will happen via status callback
        conversations.pop(CallSid, None)
        
        return twiml_response(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>/audio/{audio_filename}</Play>
    <Hangup/>
</Response>""")
    
    # Generate response audio
    audio_filename = generate_audio(llm_response, CallSid)
    
    # Fallback for silence
    silence_text = "Nu am auzit nimic. Mai ești acolo?"
    silence_audio = generate_audio(silence_text, CallSid)
    
    # Continue conversation
    return twiml_response(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>/audio/{audio_filename}</Play>
    <Gather input="speech" language="{LANGUAGE}" speechTimeout="auto" action="/voice" method="POST">
    </Gather>
    <Play>/audio/{silence_audio}</Play>
    <Redirect>/voice</Redirect>
</Response>""")


@app.post("/status")
async def status_callback(CallSid: str = Form(...), CallStatus: str = Form(...)):
    logger.info(f"[{CallSid}] Status: {CallStatus}")
    if CallStatus in ("completed", "failed", "busy", "no-answer"):
        conversations.pop(CallSid, None)
        cleanup_audio(CallSid)
    return Response(status_code=200)