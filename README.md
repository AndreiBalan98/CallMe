# CallMe - Twilio Voice Assistant

Backend FastAPI pentru asistent vocal cu Twilio și OpenAI TTS.

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
$env:OPENAI_API_KEY="sk-your-key"
uvicorn main:app --reload --port 8000
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

## OpenAI TTS

Folosim OpenAI TTS API în loc de vocile Twilio/Google:

| Setting | Valoare |
|---------|---------|
| Model | `tts-1` (~$0.015/1000 caractere) |
| Voice | `nova` (feminină, caldă) |
| Format | MP3 |

### Voci disponibile
- `nova` - feminină, caldă, prietenoasă ✓
- `shimmer` - feminină, calmă
- `alloy` - neutră
- `echo` - masculină
- `fable` - masculină, expresivă
- `onyx` - masculină, gravă

## Endpoints

| Endpoint | Metodă | Descriere |
|----------|--------|-----------|
| `/voice` | POST | Webhook principal Twilio |
| `/status` | POST | Status callback (cleanup) |
| `/audio/{filename}` | GET | Servește fișierele audio generate |

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
    <Play>/audio/filename.mp3</Play>
    <Gather input="speech" language="ro-RO" speechTimeout="auto" action="/voice" method="POST">
    </Gather>
</Response>
```

## Flow

1. User sună → Twilio trimite POST la `/voice`
2. Server generează audio cu OpenAI TTS → salvează în `/tmp/audio/`
3. Server răspunde cu TwiML: `<Play>` (audio) + `<Gather>` (ascultă)
4. Twilio cere audio de la `/audio/{filename}`
5. User vorbește → Twilio transcrie → POST la `/voice` cu `SpeechResult`
6. Server trimite la OpenAI Chat → generează audio TTS → răspunde
7. Repeat până când LLM zice să închidă → `<Hangup/>`
8. La final, cleanup audio files via `/status` callback