# CallMe - Twilio Voice Assistant

Backend FastAPI pentru asistent vocal cu Twilio și OpenAI.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
OPENAI_API_KEY="sk-your-key" uvicorn main:app --reload --port 8000
```

## ngrok

```bash
ngrok http 8000
```

## Twilio Config

1. Mergi la [Twilio Console](https://console.twilio.com) → Phone Numbers → Active Numbers
2. Selectează numărul tău
3. La **Voice Configuration** → **A call comes in**:
   - Webhook: `https://YOUR-NGROK-URL.ngrok-free.app/voice`
   - Method: POST
4. (Opțional) La **Status callback URL**: `https://YOUR-NGROK-URL.ngrok-free.app/status`

## Parametri Twilio (ce primești în POST)

| Parametru | Descriere |
|-----------|-----------|
| `CallSid` | ID unic al apelului |
| `SpeechResult` | Text transcris din vocea utilizatorului |
| `Confidence` | Scor de încredere pentru transcriere (0-1) |
| `From` | Numărul apelantului |
| `To` | Numărul Twilio |

## TwiML Response (ce trimiți înapoi)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Google.ro-RO-Wavenet-B" language="ro-RO">Text de vorbit</Say>
    <Gather input="speech" language="ro-RO" speechTimeout="auto" action="/voice" method="POST">
    </Gather>
</Response>
```

## Flow

1. User sună → Twilio trimite POST la `/voice`
2. Server răspunde cu TwiML: Say (salut) + Gather (ascultă)
3. User vorbește → Twilio transcrie → POST la `/voice` cu `SpeechResult`
4. Server trimite la OpenAI → răspunde cu TwiML
5. Repeat până când LLM zice să închidă → `<Hangup/>`