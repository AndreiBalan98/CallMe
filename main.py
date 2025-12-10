from fastapi import FastAPI, Form, Response, Request
from fastapi.responses import FileResponse
from openai import OpenAI
import logging
import os
import hashlib
import time
from datetime import datetime

# Enhanced logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s │ %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Disable noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

app = FastAPI()
client = OpenAI()

# Directory for audio files (works on Render)
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio_cache")
os.makedirs(AUDIO_DIR, exist_ok=True)

# In-memory conversation storage per call
conversations: dict[str, list[dict]] = {}

# Call metadata for timing
call_metadata: dict[str, dict] = {}

SYSTEM_PROMPT = """Ești un asistent vocal prietenos care vorbește în română.
Răspunde concis și natural, ca într-o conversație telefonică.
La finalul fiecărui răspuns în care ai rezolvat cererea utilizatorului, întreabă politicos dacă mai poți ajuta cu ceva sau dacă e ok să închizi.
Când utilizatorul confirmă că poate închide (ex: "da", "ok", "gata", "pa", "la revedere"), răspunde cu exact: "ÎNCHIDE_APEL" la început, urmat de un mesaj scurt de rămas bun."""

# TTS Settings
TTS_MODEL = "tts-1"
TTS_VOICE = "nova"  # Feminine, warm voice
LANGUAGE = "ro-RO"


def log_separator(call_sid: str, char: str = "─", length: int = 60):
    """Print a visual separator."""
    logger.info(f"[{call_sid[:8]}] {char * length}")


def log_header(call_sid: str, title: str):
    """Print a section header."""
    logger.info(f"[{call_sid[:8]}] ┌{'─' * 58}┐")
    logger.info(f"[{call_sid[:8]}] │ {title:^56} │")
    logger.info(f"[{call_sid[:8]}] └{'─' * 58}┘")


def generate_audio(text: str, call_sid: str) -> tuple[str, float]:
    """Generate audio file using OpenAI TTS and return filename and duration."""
    start_time = time.time()
    
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
    
    elapsed = time.time() - start_time
    file_size = os.path.getsize(filepath) / 1024  # KB
    
    logger.info(f"[{call_sid[:8]}] 🔊 TTS: {elapsed:.2f}s │ {file_size:.1f}KB │ {len(text)} chars")
    logger.info(f"[{call_sid[:8]}]    Text: \"{text[:80]}{'...' if len(text) > 80 else ''}\"")
    
    return filename, elapsed


def get_llm_response(call_sid: str, user_message: str) -> tuple[str, float]:
    """Get LLM response and return it with timing."""
    start_time = time.time()
    
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
    
    elapsed = time.time() - start_time
    tokens_in = response.usage.prompt_tokens
    tokens_out = response.usage.completion_tokens
    
    logger.info(f"[{call_sid[:8]}] 🤖 LLM: {elapsed:.2f}s │ tokens: {tokens_in}→{tokens_out}")
    
    return assistant_message, elapsed


def twiml_response(content: str) -> Response:
    return Response(content=content, media_type="application/xml")


def cleanup_audio(call_sid: str):
    """Remove all audio files for a call."""
    count = 0
    for filename in os.listdir(AUDIO_DIR):
        if filename.startswith(call_sid):
            try:
                os.remove(os.path.join(AUDIO_DIR, filename))
                count += 1
            except Exception as e:
                logger.error(f"[{call_sid[:8]}] ❌ Failed to clean {filename}: {e}")
    if count > 0:
        logger.info(f"[{call_sid[:8]}] 🧹 Cleaned up {count} audio files")


def get_call_duration(call_sid: str) -> str:
    """Get formatted call duration."""
    if call_sid in call_metadata and "start_time" in call_metadata[call_sid]:
        duration = time.time() - call_metadata[call_sid]["start_time"]
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        return f"{minutes}:{seconds:02d}"
    return "0:00"


@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve generated audio files."""
    filepath = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(filepath):
        # Extract call_sid from filename
        call_sid = filename.split("_")[0] if "_" in filename else "unknown"
        logger.info(f"[{call_sid[:8]}] 📤 Serving audio: {filename}")
        return FileResponse(filepath, media_type="audio/mpeg")
    logger.warning(f"[????????] ⚠️  Audio not found: {filename}")
    return Response(status_code=404)


@app.post("/voice")
async def voice_webhook(
    CallSid: str = Form(...),
    SpeechResult: str = Form(None),
    Digits: str = Form(None),
    From: str = Form(None),
    To: str = Form(None),
    Confidence: float = Form(None),
):
    total_start = time.time()
    sid = CallSid[:8]  # Short version for logs
    
    # First call - no input yet
    if not SpeechResult:
        log_header(CallSid, "📞 NEW CALL")
        logger.info(f"[{sid}] From: {From} → To: {To}")
        logger.info(f"[{sid}] CallSid: {CallSid}")
        
        # Initialize call metadata
        call_metadata[CallSid] = {
            "start_time": time.time(),
            "from": From,
            "turns": 0,
            "total_llm_time": 0,
            "total_tts_time": 0,
        }
        
        # Generate greeting audio
        greeting_text = "Salut, cu ce te pot ajuta?"
        audio_filename, tts_time = generate_audio(greeting_text, CallSid)
        call_metadata[CallSid]["total_tts_time"] += tts_time
        
        # Fallback text for no response
        no_response_text = "Nu am auzit nimic. La revedere!"
        no_response_audio, tts_time2 = generate_audio(no_response_text, CallSid)
        call_metadata[CallSid]["total_tts_time"] += tts_time2
        
        total_time = time.time() - total_start
        logger.info(f"[{sid}] ⏱️  Total response time: {total_time:.2f}s")
        log_separator(CallSid)
        
        return twiml_response(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>/audio/{audio_filename}</Play>
    <Gather input="speech" language="{LANGUAGE}" speechTimeout="auto" action="/voice" method="POST">
    </Gather>
    <Play>/audio/{no_response_audio}</Play>
</Response>""")
    
    # Continuing conversation
    call_metadata[CallSid]["turns"] = call_metadata.get(CallSid, {}).get("turns", 0) + 1
    turn = call_metadata[CallSid]["turns"]
    duration = get_call_duration(CallSid)
    
    log_separator(CallSid, "─")
    logger.info(f"[{sid}] 🎤 TURN {turn} │ Duration: {duration}")
    logger.info(f"[{sid}] 👤 USER: \"{SpeechResult}\"")
    if Confidence:
        logger.info(f"[{sid}]    Confidence: {Confidence:.1%}")
    
    # Get LLM response
    llm_response, llm_time = get_llm_response(CallSid, SpeechResult)
    call_metadata[CallSid]["total_llm_time"] += llm_time
    
    # Check if call should end
    if llm_response.startswith("ÎNCHIDE_APEL"):
        goodbye_message = llm_response.replace("ÎNCHIDE_APEL", "").strip()
        
        logger.info(f"[{sid}] 🤖 ASSISTANT: \"{goodbye_message}\"")
        
        # Generate goodbye audio
        audio_filename, tts_time = generate_audio(goodbye_message, CallSid)
        call_metadata[CallSid]["total_tts_time"] += tts_time
        
        total_time = time.time() - total_start
        
        # Final stats
        log_header(CallSid, "📴 CALL ENDING")
        meta = call_metadata.get(CallSid, {})
        logger.info(f"[{sid}] Duration: {duration}")
        logger.info(f"[{sid}] Turns: {meta.get('turns', 0)}")
        logger.info(f"[{sid}] Total LLM time: {meta.get('total_llm_time', 0):.2f}s")
        logger.info(f"[{sid}] Total TTS time: {meta.get('total_tts_time', 0):.2f}s")
        logger.info(f"[{sid}] ⏱️  Final response: {total_time:.2f}s")
        log_separator(CallSid, "═")
        
        # Cleanup
        conversations.pop(CallSid, None)
        call_metadata.pop(CallSid, None)
        
        return twiml_response(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>/audio/{audio_filename}</Play>
    <Hangup/>
</Response>""")
    
    logger.info(f"[{sid}] 🤖 ASSISTANT: \"{llm_response}\"")
    
    # Generate response audio
    audio_filename, tts_time = generate_audio(llm_response, CallSid)
    call_metadata[CallSid]["total_tts_time"] += tts_time
    
    # Fallback for silence
    silence_text = "Nu am auzit nimic. Mai ești acolo?"
    silence_audio, tts_time2 = generate_audio(silence_text, CallSid)
    call_metadata[CallSid]["total_tts_time"] += tts_time2
    
    total_time = time.time() - total_start
    logger.info(f"[{sid}] ⏱️  Total response time: {total_time:.2f}s")
    log_separator(CallSid)
    
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
async def status_callback(
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    CallDuration: int = Form(None),
):
    sid = CallSid[:8]
    
    status_emoji = {
        "initiated": "🔔",
        "ringing": "🔔",
        "in-progress": "📞",
        "completed": "✅",
        "failed": "❌",
        "busy": "⛔",
        "no-answer": "📵",
    }.get(CallStatus, "❓")
    
    logger.info(f"[{sid}] {status_emoji} Status: {CallStatus}" + 
                (f" │ Duration: {CallDuration}s" if CallDuration else ""))
    
    if CallStatus in ("completed", "failed", "busy", "no-answer"):
        conversations.pop(CallSid, None)
        call_metadata.pop(CallSid, None)
        cleanup_audio(CallSid)
    
    return Response(status_code=200)


@app.on_event("startup")
async def startup_event():
    logger.info("═" * 60)
    logger.info("🚀 CallMe Voice Assistant Started")
    logger.info(f"   TTS Model: {TTS_MODEL} │ Voice: {TTS_VOICE}")
    logger.info(f"   Language: {LANGUAGE}")
    logger.info("═" * 60)