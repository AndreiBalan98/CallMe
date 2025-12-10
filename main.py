from fastapi import FastAPI, Form, Response
from openai import OpenAI
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()
client = OpenAI()

# In-memory conversation storage per call
conversations: dict[str, list[dict]] = {}

SYSTEM_PROMPT = """Ești un asistent vocal prietenos care vorbește în română.
Răspunde concis și natural, ca într-o conversație telefonică.
La finalul fiecărui răspuns în care ai rezolvat cererea utilizatorului, întreabă politicos dacă mai poți ajuta cu ceva sau dacă e ok să închizi.
Când utilizatorul confirmă că poate închide (ex: "da", "ok", "gata", "pa", "la revedere"), răspunde cu exact: "ÎNCHIDE_APEL" la început, urmat de un mesaj scurt de rămas bun."""

VOICE = "Google.ro-RO-Wavenet-B"
LANGUAGE = "ro-RO"


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
        return twiml_response(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="{VOICE}" language="{LANGUAGE}">Salut, cu ce te pot ajuta?</Say>
    <Gather input="speech" language="{LANGUAGE}" speechTimeout="auto" action="/voice" method="POST">
    </Gather>
    <Say voice="{VOICE}" language="{LANGUAGE}">Nu am auzit nimic. La revedere!</Say>
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
        # Cleanup
        conversations.pop(CallSid, None)
        return twiml_response(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="{VOICE}" language="{LANGUAGE}">{goodbye_message}</Say>
    <Hangup/>
</Response>""")
    
    # Continue conversation
    return twiml_response(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="{VOICE}" language="{LANGUAGE}">{llm_response}</Say>
    <Gather input="speech" language="{LANGUAGE}" speechTimeout="auto" action="/voice" method="POST">
    </Gather>
    <Say voice="{VOICE}" language="{LANGUAGE}">Nu am auzit nimic. Mai ești acolo?</Say>
    <Redirect>/voice</Redirect>
</Response>""")


@app.post("/status")
async def status_callback(CallSid: str = Form(...), CallStatus: str = Form(...)):
    logger.info(f"[{CallSid}] Status: {CallStatus}")
    if CallStatus in ("completed", "failed", "busy", "no-answer"):
        conversations.pop(CallSid, None)
    return Response(status_code=200)