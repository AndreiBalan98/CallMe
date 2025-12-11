"""
CallMe - Voice Assistant cu OpenAI Realtime API + Twilio Media Streams
Comunicare bidirecțională în timp real prin WebSockets
"""

import os
import json
import base64
import asyncio
import logging
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.websockets import WebSocketDisconnect
import websockets
from dotenv import load_dotenv

load_dotenv()

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s │ %(levelname)s │ %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)
logging.getLogger("websockets").setLevel(logging.WARNING)

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 5050))

# OpenAI Realtime API settings
# Modele disponibile:
# - gpt-4o-realtime-preview (ultima versiune preview)
# - gpt-realtime (GA - general availability, recomandat pentru producție)
OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview"
VOICE = "shimmer"  # Voci: alloy, ash, ballad, coral, echo, sage, shimmer, verse

# System prompt pentru asistentul vocal
SYSTEM_PROMPT = """Ești un asistent vocal prietenos care vorbește în limba română.

Reguli importante:
- Răspunde SCURT și NATURAL, ca într-o conversație telefonică normală
- Evită răspunsurile lungi - maxim 2-3 propoziții
- Fii cald și prietenos, dar concis
- Nu repeta informații deja spuse
- Când utilizatorul vrea să încheie (spune "pa", "la revedere", "gata", etc.), răspunde scurt cu un salut și conversația se va încheia automat
- Nu menționa că ești o inteligență artificială decât dacă ești întrebat direct"""

# Mesaje audio de început (vor fi generate și trimise la începutul apelului)
GREETING_MESSAGES = [
    "Bună! Cu ce te pot ajuta?",
]

# Evenimente OpenAI pe care le logăm (TOATE pentru debugging)
LOG_EVENT_TYPES = [
    'error',
    'session.created',
    'session.updated',
    'response.created',
    'response.done',
    'response.audio.delta',
    'response.audio.done',
    'response.text.delta',
    'response.text.done',
    'input_audio_buffer.speech_started',
    'input_audio_buffer.speech_stopped',
    'input_audio_buffer.committed',
    'conversation.item.created',
    'conversation.item.input_audio_transcription.completed',
    'rate_limits.updated',
]

# Flag pentru debugging - pune True pentru a vedea TOATE mesajele
DEBUG_ALL_EVENTS = True

app = FastAPI()

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY lipsește din .env")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Health check endpoint"""
    return HTMLResponse(content="<h1>CallMe Voice Assistant - Running</h1>")


@app.api_route("/incoming-call", methods=["GET", "POST"])
async def incoming_call(request: Request):
    """
    Webhook Twilio pentru apeluri primite.
    Returnează TwiML care conectează apelul la WebSocket-ul nostru pentru Media Streams.
    """
    host = request.url.hostname
    port_suffix = f":{request.url.port}" if request.url.port and request.url.port not in (80, 443) else ""
    
    # TwiML: conectează direct la WebSocket, fără mesaj Say
    # (vom trimite audio-ul de salut prin stream)
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://{host}{port_suffix}/media-stream" />
    </Connect>
</Response>"""
    
    logger.info(f"📞 Apel primit - conectare la wss://{host}{port_suffix}/media-stream")
    return HTMLResponse(content=twiml, media_type="application/xml")


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """
    WebSocket endpoint pentru Twilio Media Streams.
    Face proxy bidirecțional între Twilio și OpenAI Realtime API.
    """
    await websocket.accept()
    logger.info("🔌 Twilio WebSocket conectat")
    
    stream_sid = None
    openai_ws = None
    
    try:
        # Variabilă pentru stream_sid (closure workaround)
        def set_stream_sid(sid):
            nonlocal stream_sid
            stream_sid = sid
        
        # Conectare la OpenAI Realtime API
        logger.info(f"🔄 Conectare la OpenAI: {OPENAI_REALTIME_URL}")
        try:
            openai_ws = await websockets.connect(
                OPENAI_REALTIME_URL,
                extra_headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "OpenAI-Beta": "realtime=v1"
                }
            )
            logger.info("🤖 Conectat la OpenAI Realtime API")
        except Exception as e:
            logger.error(f"❌ EROARE CONEXIUNE OPENAI: {e}")
            logger.error(f"   Verifică: 1) API key valid 2) Acces la Realtime API 3) Model disponibil")
            await websocket.close()
            return
        
        # Configurare sesiune OpenAI
        await send_session_config(openai_ws)
        
        # Pornește task-uri paralele pentru comunicare bidirecțională
        receive_from_twilio = asyncio.create_task(
            handle_twilio_messages(websocket, openai_ws, lambda: stream_sid, set_stream_sid)
        )
        receive_from_openai = asyncio.create_task(
            handle_openai_messages(openai_ws, websocket, lambda: stream_sid)
        )
        
        # Așteaptă până când unul dintre task-uri se termină
        done, pending = await asyncio.wait(
            [receive_from_twilio, receive_from_openai],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Anulează task-urile rămase
        for task in pending:
            task.cancel()
            
    except WebSocketDisconnect:
        logger.info("📴 Twilio WebSocket deconectat")
    except Exception as e:
        logger.error(f"❌ Eroare: {e}")
    finally:
        if openai_ws:
            await openai_ws.close()
            logger.info("🔌 OpenAI WebSocket închis")


async def send_session_config(openai_ws):
    """Trimite configurația sesiunii la OpenAI"""
    session_config = {
        "type": "session.update",
        "session": {
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 500
            },
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_ulaw",
            "voice": VOICE,
            "instructions": SYSTEM_PROMPT,
            "modalities": ["text", "audio"],
            "temperature": 0.8,
        }
    }
    logger.info(f"📤 Trimit session.update: input={session_config['session']['input_audio_format']}, output={session_config['session']['output_audio_format']}")
    await openai_ws.send(json.dumps(session_config))
    logger.info(f"⚙️ Session config trimis - voce: {VOICE}")


async def send_initial_greeting(openai_ws):
    """
    Trimite mesajul de salut inițial prin OpenAI.
    Folosim response.create pentru a genera audio-ul de salut.
    """
    # Creăm un item de conversație cu salutul
    greeting_event = {
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "Salută utilizatorul scurt și întreabă cu ce îl poți ajuta."
                }
            ]
        }
    }
    await openai_ws.send(json.dumps(greeting_event))
    logger.info("📤 Trimis conversation.item.create pentru salut")
    
    # Solicită răspuns CU AUDIO EXPLICIT
    response_event = {
        "type": "response.create",
        "response": {
            "modalities": ["text", "audio"]
        }
    }
    await openai_ws.send(json.dumps(response_event))
    logger.info("👋 Salut inițial solicitat cu modalities: text, audio")


async def handle_twilio_messages(twilio_ws, openai_ws, get_stream_sid, set_stream_sid):
    """
    Primește mesaje de la Twilio și le trimite la OpenAI.
    """
    greeting_sent = False
    
    try:
        while True:
            message = await twilio_ws.receive_text()
            data = json.loads(message)
            event_type = data.get("event")
            
            if event_type == "connected":
                logger.info("📱 Twilio stream conectat")
                
            elif event_type == "start":
                stream_sid = data["start"]["streamSid"]
                set_stream_sid(stream_sid)
                logger.info(f"🎙️ Stream început - SID: {stream_sid[:20]}...")
                
                # Trimite salutul inițial după ce stream-ul a pornit
                if not greeting_sent:
                    await send_initial_greeting(openai_ws)
                    greeting_sent = True
                
            elif event_type == "media":
                # Forward audio de la Twilio la OpenAI
                audio_payload = data["media"]["payload"]
                audio_event = {
                    "type": "input_audio_buffer.append",
                    "audio": audio_payload
                }
                await openai_ws.send(json.dumps(audio_event))
                
            elif event_type == "stop":
                logger.info("🛑 Stream oprit de Twilio")
                break
                
    except WebSocketDisconnect:
        logger.info("📴 Twilio deconectat")
    except Exception as e:
        logger.error(f"❌ Eroare Twilio handler: {e}")


async def handle_openai_messages(openai_ws, twilio_ws, get_stream_sid):
    """
    Primește mesaje de la OpenAI și le trimite la Twilio.
    """
    audio_chunks_received = 0
    
    try:
        async for message in openai_ws:
            data = json.loads(message)
            event_type = data.get("type", "")
            
            # DEBUG: Log toate evenimentele
            if DEBUG_ALL_EVENTS:
                if event_type == "response.audio.delta":
                    audio_chunks_received += 1
                    if audio_chunks_received % 50 == 1:  # Log fiecare 50 chunks
                        logger.info(f"🔊 Audio chunks primite: {audio_chunks_received}")
                else:
                    # Log complet pentru non-audio events
                    logger.info(f"📨 OpenAI Event: {event_type}")
                    if event_type in ['error', 'session.created', 'session.updated']:
                        logger.info(f"   Details: {json.dumps(data, indent=2)[:500]}")
            
            # Log evenimente importante
            if event_type in LOG_EVENT_TYPES:
                if event_type == "error":
                    logger.error(f"❌ OpenAI Error: {json.dumps(data.get('error', {}), indent=2)}")
                elif event_type == "session.created":
                    logger.info(f"✅ Sesiune creată: {data.get('session', {}).get('id', 'N/A')}")
                elif event_type == "session.updated":
                    session = data.get('session', {})
                    logger.info(f"✅ Sesiune actualizată:")
                    logger.info(f"   - modalities: {session.get('modalities')}")
                    logger.info(f"   - input_audio_format: {session.get('input_audio_format')}")
                    logger.info(f"   - output_audio_format: {session.get('output_audio_format')}")
                    logger.info(f"   - voice: {session.get('voice')}")
                    logger.info(f"   - turn_detection: {session.get('turn_detection', {}).get('type')}")
                elif event_type == "input_audio_buffer.speech_started":
                    logger.info("🎤 Utilizator vorbește...")
                elif event_type == "input_audio_buffer.speech_stopped":
                    logger.info("🔇 Utilizator a terminat")
                elif event_type == "response.created":
                    logger.info("🤖 Generare răspuns început...")
                elif event_type == "response.done":
                    response_data = data.get('response', {})
                    output = response_data.get('output', [])
                    status = response_data.get('status')
                    logger.info(f"✅ Răspuns complet - audio chunks trimise: {audio_chunks_received}")
                    logger.info(f"   Response status: {status}")
                    
                    # Dacă a eșuat, afișează motivul
                    if status == 'failed':
                        status_details = response_data.get('status_details', {})
                        logger.error(f"   ❌ FAILED REASON: {status_details}")
                        logger.error(f"   Full response: {json.dumps(response_data, indent=2)[:1000]}")
                    
                    logger.info(f"   Output items: {len(output)}")
                    for i, item in enumerate(output):
                        logger.info(f"   Item {i}: type={item.get('type')}, role={item.get('role')}")
                        if item.get('content'):
                            for c in item.get('content', []):
                                logger.info(f"      Content: type={c.get('type')}, transcript={c.get('transcript', '')[:50] if c.get('transcript') else 'N/A'}")
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    transcript = data.get('transcript', '')
                    logger.info(f"📝 Transcriere: {transcript[:100]}")
            
            # Forward audio de la OpenAI la Twilio
            if event_type == "response.audio.delta":
                audio_payload = data.get("delta", "")
                if audio_payload:
                    stream_sid = get_stream_sid()
                    if stream_sid:
                        media_message = {
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {
                                "payload": audio_payload
                            }
                        }
                        await twilio_ws.send_json(media_message)
                    else:
                        logger.warning("⚠️ Audio primit dar stream_sid lipsește!")
                        
    except websockets.exceptions.ConnectionClosed as e:
        logger.info(f"🔌 OpenAI WebSocket închis: {e.code} - {e.reason}")
    except Exception as e:
        logger.error(f"❌ Eroare OpenAI handler: {e}")


if __name__ == "__main__":
    import uvicorn
    logger.info("=" * 60)
    logger.info("🚀 CallMe Voice Assistant - OpenAI Realtime")
    logger.info(f"   Voice: {VOICE}")
    logger.info(f"   Port: {PORT}")
    logger.info("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=PORT)