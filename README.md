# CallMe - Voice Assistant cu ElevenLabs Conversational AI

Asistent vocal telefonic care folosește **ElevenLabs Conversational AI** și **Twilio Media Streams** pentru conversații naturale, bidirecționale, în timp real.

## 🎯 Caracteristici

- **Voce naturală** - Folosește vocile premium ElevenLabs
- **Latență minimă** - Streaming audio bidirecțional în timp real
- **Limba română** - Configurat nativ pentru conversații în română
- **Profesionist dar prietenos** - Ton cald, răspunsuri concise
- **Întreruperi naturale** - Utilizatorul poate întrerupe agentul oricând
- **Deploy simplu** - Gata pentru Render/Railway/orice platform

## 🏗️ Arhitectură

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐
│   Telefon   │────▶│   Twilio    │────▶│   Server (FastAPI)  │
│  (Apelant)  │◀────│Media Streams│◀────│                     │
└─────────────┘     └─────────────┘     └──────────┬──────────┘
                                                   │
                                                   │ WebSocket
                                                   │
                                        ┌──────────▼──────────┐
                                        │     ElevenLabs      │
                                        │  Conversational AI  │
                                        │  (STT + LLM + TTS)  │
                                        └─────────────────────┘
```

## 📋 Cerințe

- Cont **ElevenLabs** cu acces la Conversational AI
- Cont **Twilio** cu număr de telefon
- Python 3.11+

## 🚀 Setup

### 1. Creează un Agent în ElevenLabs

1. Mergi la [ElevenLabs Agents](https://elevenlabs.io/app/conversational-ai)
2. Creează un agent nou sau folosește unul existent
3. Configurează:
   - **Vocea**: Alege o voce care îți place
   - **Limba**: Română (sau multilingv)
   - **Setări audio**: μ-law 8kHz (pentru Twilio)
4. Copiază **Agent ID** din setările agentului

### 2. Configurare locală

```bash
# Clonează repository-ul
git clone <repo-url>
cd callme-elevenlabs

# Creează virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# sau: venv\Scripts\activate  # Windows

# Instalează dependențele
pip install -r requirements.txt

# Configurează variabilele de mediu
cp .env.example .env
# Editează .env și adaugă cheile tale
```

### 3. Configurare .env

```env
ELEVENLABS_API_KEY=your-elevenlabs-api-key
ELEVENLABS_AGENT_ID=your-agent-id
PORT=5050
DEBUG=false
```

### 4. Rulare locală cu ngrok

```bash
# Terminal 1: Pornește serverul
python main.py

# Terminal 2: Expune serverul cu ngrok
ngrok http 5050
```

### 5. Configurare Twilio

1. În [Twilio Console](https://console.twilio.com/), mergi la numărul tău
2. La **Voice & Fax** → **A Call Comes In**:
   - Webhook: `https://your-ngrok-url.ngrok.io/incoming-call`
   - Method: POST

## 🌐 Deploy pe Render

1. Fork acest repository pe GitHub
2. În [Render Dashboard](https://dashboard.render.com/):
   - New → Web Service
   - Conectează repository-ul
   - Render va detecta automat `render.yaml`
3. Adaugă variabilele de mediu:
   - `ELEVENLABS_API_KEY`
   - `ELEVENLABS_AGENT_ID`
4. Deploy!

După deploy, configurează webhook-ul Twilio cu URL-ul Render:
```
https://your-app.onrender.com/incoming-call
```

## 📁 Structura proiectului

```
.
├── main.py              # Aplicația principală FastAPI
├── requirements.txt     # Dependențe Python
├── render.yaml          # Configurare Render
├── .env.example         # Template variabile de mediu
└── README.md           # Documentație
```

## 🔧 Cum funcționează

1. **Apel primit** → Twilio trimite webhook la `/incoming-call`
2. **TwiML Response** → Serverul răspunde cu instrucțiuni de conectare WebSocket
3. **Media Stream** → Twilio deschide WebSocket la `/media-stream`
4. **ElevenLabs Connect** → Serverul obține signed URL și se conectează la ElevenLabs
5. **Audio bidirecțional**:
   - Twilio → Server → ElevenLabs (vocea utilizatorului)
   - ElevenLabs → Server → Twilio (răspunsul agentului)
6. **Evenimente speciale**:
   - `interruption` → Curăță buffer-ul audio Twilio
   - `ping/pong` → Menține conexiunea activă

## 🎛️ Personalizare

### Modificare prompt agent

În `main.py`, găsește secțiunea `conversation_config_override` și modifică prompt-ul:

```python
"prompt": {
    "prompt": """Ești un asistent vocal..."""
}
```

### Setări voce

Poți suprascrie vocea agentului:

```python
"tts": {
    "voice_id": "your-voice-id"  # sau None pentru default
}
```

## 🐛 Debugging

Activează modul debug pentru logging detaliat:

```env
DEBUG=true
```

Vei vedea:
- Toate evenimentele ElevenLabs
- Contorul de audio chunks
- Transcrierile în timp real

## 📊 Evenimente ElevenLabs

| Event | Descriere |
|-------|-----------|
| `conversation_initiation_metadata` | Conversația a început |
| `audio` | Chunk audio de la agent |
| `user_transcript` | Ce spune utilizatorul |
| `agent_response` | Răspunsul text al agentului |
| `interruption` | Utilizatorul a întrerupt |
| `ping` | Keep-alive (necesită pong) |

## ⚠️ Troubleshooting

### "Failed to get signed URL"
- Verifică `ELEVENLABS_API_KEY` este corect
- Verifică agentul există și `ELEVENLABS_AGENT_ID` e corect

### Nu se aude audio
- Verifică agentul ElevenLabs e configurat pentru μ-law 8kHz
- Verifică webhook-ul Twilio e configurat corect
- Activează DEBUG=true pentru mai multe informații

### Latență mare
- Verifică serverul e în aceeași regiune cu ElevenLabs
- Folosește un plan ElevenLabs cu latență mai mică

## 📜 Licență

MIT

## 🙏 Credit

- [ElevenLabs](https://elevenlabs.io/) - Conversational AI & TTS
- [Twilio](https://www.twilio.com/) - Media Streams
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
