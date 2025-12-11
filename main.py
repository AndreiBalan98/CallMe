"""
CallMe - Voice Assistant cu ElevenLabs Conversational AI + Twilio Media Streams
Comunicare bidirecțională în timp real prin WebSockets
"""

import os
import json
import base64
import asyncio
import logging
import aiohttp
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
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")
PORT = int(os.getenv("PORT", 5050))

# Flag pentru debugging
DEBUG_ALL_EVENTS = os.getenv("DEBUG", "false").lower() == "true"

app = FastAPI()

if not ELEVENLABS_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY lipsește din .env")
if not ELEVENLABS_AGENT_ID:
    raise ValueError("ELEVENLABS_AGENT_ID lipsește din .env")


async def get_elevenlabs_ws_url() -> str:
    """
    Obține URL-ul WebSocket pentru ElevenLabs.
    Încearcă mai întâi signed URL (pentru agenți privați),
    dacă eșuează, folosește conexiune directă (pentru agenți publici).
    """
    # Încearcă să obții signed URL pentru agent privat
    if ELEVENLABS_API_KEY:
        try:
            url = f"https://api.elevenlabs.io/v1/convai/conversation/get-signed-url?agent_id={ELEVENLABS_AGENT_ID}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers={"xi-api-key": ELEVENLABS_API_KEY}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info("🔐 Folosesc signed URL (agent privat)")
                        return data["signed_url"]
                    else:
                        error_text = await response.text()
                        logger.warning(f"⚠️ Nu pot obține signed URL: {response.status} - {error_text}")
                        logger.info("📢 Încerc conexiune directă (agent public)...")
        except Exception as e:
            logger.warning(f"⚠️ Eroare la signed URL: {e}")
            logger.info("📢 Încerc conexiune directă (agent public)...")
    
    # Fallback: conexiune directă pentru agent public
    direct_url = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={ELEVENLABS_AGENT_ID}"
    logger.info("🌐 Folosesc conexiune directă (agent public)")
    return direct_url


@app.get("/", response_class=HTMLResponse)
async def root():
    """Health check endpoint"""
    return HTMLResponse(content="<h1>CallMe Voice Assistant - ElevenLabs - Running</h1>")


@app.api_route("/incoming-call", methods=["GET", "POST"])
async def incoming_call(request: Request):
    """
    Webhook Twilio pentru apeluri primite.
    Returnează TwiML care conectează apelul la WebSocket-ul nostru pentru Media Streams.
    """
    host = request.url.hostname
    port_suffix = f":{request.url.port}" if request.url.port and request.url.port not in (80, 443) else ""
    
    # TwiML: conectează direct la WebSocket pentru Media Streams
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
    Face proxy bidirecțional între Twilio și ElevenLabs Conversational AI.
    """
    await websocket.accept()
    logger.info("🔌 Twilio WebSocket conectat")
    
    stream_sid = None
    elevenlabs_ws = None
    
    try:
        # Variabilă pentru stream_sid (closure workaround)
        def set_stream_sid(sid):
            nonlocal stream_sid
            stream_sid = sid
        
        # Obține URL WebSocket pentru ElevenLabs
        logger.info("🔑 Pregătire conexiune ElevenLabs...")
        try:
            elevenlabs_url = await get_elevenlabs_ws_url()
        except Exception as e:
            logger.error(f"❌ EROARE la obținerea URL-ului: {e}")
            await websocket.close()
            return
        
        # Conectare la ElevenLabs Conversational AI
        logger.info("🔄 Conectare la ElevenLabs Conversational AI...")
        try:
            elevenlabs_ws = await websockets.connect(elevenlabs_url)
            logger.info("🤖 Conectat la ElevenLabs Conversational AI")
        except Exception as e:
            logger.error(f"❌ EROARE CONEXIUNE ELEVENLABS: {e}")
            await websocket.close()
            return
        
        # Pornește task-uri paralele pentru comunicare bidirecțională
        receive_from_twilio = asyncio.create_task(
            handle_twilio_messages(websocket, elevenlabs_ws, lambda: stream_sid, set_stream_sid)
        )
        receive_from_elevenlabs = asyncio.create_task(
            handle_elevenlabs_messages(elevenlabs_ws, websocket, lambda: stream_sid)
        )
        
        # Așteaptă până când unul dintre task-uri se termină
        done, pending = await asyncio.wait(
            [receive_from_twilio, receive_from_elevenlabs],
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
        if elevenlabs_ws:
            await elevenlabs_ws.close()
            logger.info("🔌 ElevenLabs WebSocket închis")


async def handle_twilio_messages(twilio_ws, elevenlabs_ws, get_stream_sid, set_stream_sid):
    """
    Primește mesaje de la Twilio și le trimite la ElevenLabs.
    Twilio trimite audio în format μ-law 8kHz base64.
    """
    conversation_started = False
    
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
                call_sid = data["start"].get("callSid", "N/A")
                logger.info(f"🎙️ Stream început - SID: {stream_sid[:20]}... CallSID: {call_sid[:15]}...")
                
                # Trimite inițializare conversație către ElevenLabs
                # IMPORTANT: Formatul audio trebuie configurat în ElevenLabs Dashboard!
                if not conversation_started:
                    init_message = {
                        "type": "conversation_initiation_client_data"
                    }
                    await elevenlabs_ws.send(json.dumps(init_message))
                    logger.info("📤 Inițializare conversație trimisă")
                    conversation_started = True
                
            elif event_type == "media":
                # Forward audio de la Twilio la ElevenLabs
                # Twilio trimite audio μ-law 8kHz base64, ElevenLabs îl acceptă direct
                audio_payload = data["media"]["payload"]
                
                audio_message = {
                    "user_audio_chunk": audio_payload
                }
                await elevenlabs_ws.send(json.dumps(audio_message))
                
            elif event_type == "stop":
                logger.info("🛑 Stream oprit de Twilio")
                break
                
    except WebSocketDisconnect:
        logger.info("📴 Twilio deconectat")
    except Exception as e:
        logger.error(f"❌ Eroare Twilio handler: {e}")


async def handle_elevenlabs_messages(elevenlabs_ws, twilio_ws, get_stream_sid):
    """
    Primește mesaje de la ElevenLabs și le trimite la Twilio.
    ElevenLabs trimite audio și evenimente conversaționale.
    """
    audio_chunks_sent = 0
    
    try:
        async for message in elevenlabs_ws:
            data = json.loads(message)
            event_type = data.get("type", "")
            
            # Procesare evenimente ElevenLabs
            if event_type == "conversation_initiation_metadata":
                conversation_id = data.get("conversation_initiation_metadata_event", {}).get("conversation_id", "N/A")
                logger.info(f"✅ Conversație inițiată - ID: {conversation_id}")
                
            elif event_type == "audio":
                # Forward audio de la ElevenLabs la Twilio
                audio_event = data.get("audio_event", {})
                audio_base64 = audio_event.get("audio_base_64", "")
                
                if audio_base64:
                    stream_sid = get_stream_sid()
                    if stream_sid:
                        media_message = {
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {
                                "payload": audio_base64
                            }
                        }
                        await twilio_ws.send_json(media_message)
                        audio_chunks_sent += 1
                        
                        if DEBUG_ALL_EVENTS and audio_chunks_sent % 50 == 1:
                            logger.info(f"🔊 Audio chunks trimise: {audio_chunks_sent}")
                    else:
                        logger.warning("⚠️ Audio primit dar stream_sid lipsește!")
                        
            elif event_type == "user_transcript":
                # Transcrierea a ce spune utilizatorul
                transcript_event = data.get("user_transcription_event", {})
                transcript = transcript_event.get("user_transcript", "")
                if transcript:
                    logger.info(f"👤 Utilizator: {transcript}")
                    
            elif event_type == "agent_response":
                # Răspunsul agentului (text)
                response_event = data.get("agent_response_event", {})
                response = response_event.get("agent_response", "")
                if response:
                    logger.info(f"🤖 Agent: {response}")
                    
            elif event_type == "agent_response_correction":
                # Corecție la răspunsul agentului
                correction_event = data.get("agent_response_correction_event", {})
                corrected = correction_event.get("corrected_agent_response", "")
                if corrected and DEBUG_ALL_EVENTS:
                    logger.info(f"🔄 Agent (corectat): {corrected}")
                    
            elif event_type == "interruption":
                # Utilizatorul a întrerupt agentul
                logger.info("⚡ Utilizator a întrerupt agentul")
                
                # Trimite clear la Twilio pentru a opri audio-ul curent
                stream_sid = get_stream_sid()
                if stream_sid:
                    clear_message = {
                        "event": "clear",
                        "streamSid": stream_sid
                    }
                    await twilio_ws.send_json(clear_message)
                    logger.info("🔇 Buffer audio Twilio curățat")
                    
            elif event_type == "ping":
                # Răspunde la ping pentru a menține conexiunea
                ping_event = data.get("ping_event", {})
                event_id = ping_event.get("event_id")
                
                pong_message = {
                    "type": "pong",
                    "event_id": event_id
                }
                await elevenlabs_ws.send(json.dumps(pong_message))
                
                if DEBUG_ALL_EVENTS:
                    logger.info(f"🏓 Ping/Pong - event_id: {event_id}")
                    
            elif event_type == "error":
                error_message = data.get("error", data.get("message", "Unknown error"))
                logger.error(f"❌ ElevenLabs Error: {error_message}")
                
            elif DEBUG_ALL_EVENTS:
                # Log alte evenimente pentru debugging
                logger.info(f"📨 ElevenLabs Event: {event_type}")
                        
    except websockets.exceptions.ConnectionClosed as e:
        logger.info(f"🔌 ElevenLabs WebSocket închis: {e.code} - {e.reason}")
    except Exception as e:
        logger.error(f"❌ Eroare ElevenLabs handler: {e}")
    finally:
        logger.info(f"📊 Total audio chunks trimise: {audio_chunks_sent}")


if __name__ == "__main__":
    import uvicorn
    logger.info("=" * 60)
    logger.info("🚀 CallMe Voice Assistant - ElevenLabs Conversational AI")
    logger.info(f"   Agent ID: {ELEVENLABS_AGENT_ID[:20]}...")
    logger.info(f"   Port: {PORT}")
    logger.info(f"   Debug: {DEBUG_ALL_EVENTS}")
    logger.info("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=PORT)