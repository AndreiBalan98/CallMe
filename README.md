# CallMe - Voice Assistant cu OpenAI Realtime API

Asistent vocal în timp real folosind **Twilio Media Streams** și **OpenAI Realtime API**.

## 🚀 Ce face diferit față de versiunea veche?

| Versiunea veche | Versiunea nouă |
|-----------------|----------------|
| HTTP polling secvențial | WebSocket bidirecțional |
| STT → LLM → TTS separat | Speech-to-speech nativ |
| ~3-5 secunde latență | ~500ms latență |
| Multiple API calls | 2 WebSocket-uri persistente |

## Arhitectură

```
Telefon → Twilio → WebSocket → Server → WebSocket → OpenAI Realtime API
              ↑                              ↓
              └────── Audio bidirecțional ───┘
```

## Cum funcționează

1. Utilizatorul sună numărul Twilio
2. Twilio face POST la `/incoming-call` și primește TwiML
3. TwiML deschide un WebSocket bidirecțional la `/media-stream`
4. Serverul deschide un WebSocket la OpenAI Realtime API
5. Audio circulă în timp real între Twilio și OpenAI
6. OpenAI detectează automat când user-ul termină de vorbit (VAD)
7. Răspunsul audio este trimis înapoi instant

## Setup local

```bash
# Clone și setup
git clone <repo>
cd callme-realtime

# Virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# sau: venv\Scripts\activate  # Windows

# Dependențe
pip install -r requirements.txt

# Configurare
cp .env.example .env
# Editează .env și adaugă OPENAI_API_KEY

# Pornire server
uvicorn main:app --reload --port 5050
```

## Expunere cu ngrok

```bash
ngrok http 5050
```

Copiază URL-ul `https://xxxx.ngrok-free.app`

## Configurare Twilio

1. Mergi la [Twilio Console](https://console.twilio.com) → Phone Numbers
2. Selectează numărul tău
3. La **Voice Configuration** → **A call comes in**:
   - **Webhook URL**: `https://xxxx.ngrok-free.app/incoming-call`
   - **Method**: POST

## Deploy pe Render

1. Push codul pe GitHub
2. Conectează repo-ul la Render
3. Render va detecta automat `render.yaml`
4. Setează `OPENAI_API_KEY` în Environment Variables
5. Deploy!

URL-ul va fi: `https://callme-realtime.onrender.com`

Actualizează webhook-ul Twilio la: `https://callme-realtime.onrender.com/incoming-call`

## Configurare

### Voce

În `main.py`, modifică `VOICE`:
- `shimmer` - feminină, caldă (default)
- `alloy` - neutră
- `echo` - masculină
- `fable` - masculină expresivă
- `onyx` - masculină gravă
- `nova` - feminină energică

### System Prompt

Modifică `SYSTEM_PROMPT` în `main.py` pentru a schimba personalitatea.

### VAD (Voice Activity Detection)

```python
"turn_detection": {
    "type": "server_vad",
    "threshold": 0.5,           # Sensibilitate (0.0-1.0)
    "prefix_padding_ms": 300,   # Audio păstrat înainte de speech
    "silence_duration_ms": 500  # Cât tăcere = sfârșit de turn
}
```

## Costuri OpenAI Realtime API

| Tip | Cost |
|-----|------|
| Audio input | $0.06 / minut |
| Audio output | $0.24 / minut |
| Text input | $5.00 / 1M tokens |
| Text output | $20.00 / 1M tokens |

**Estimare**: Un apel de 5 minute costă ~$1.50

## Endpoints

| Endpoint | Metodă | Descriere |
|----------|--------|-----------|
| `/` | GET | Health check |
| `/incoming-call` | POST | Webhook Twilio |
| `/media-stream` | WebSocket | Media Streams |

## Troubleshooting

### "No audio" / Liniște
- Verifică că `OPENAI_API_KEY` e valid
- Verifică că ai acces la OpenAI Realtime API (beta)
- Check logs pentru erori

### Latență mare
- Render poate avea cold starts
- Folosește un plan paid pe Render pentru always-on

### "Connection closed"
- WebSocket timeout - normal dacă nu se vorbește
- Twilio închide automat după ~60s de liniște

## Licență

MIT
