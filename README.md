# 🦷 Dental Voice Assistant

Real-time voice assistant for dental clinic appointment booking using **OpenAI Realtime API** and **Twilio Media Streams**.

## Features

- **Real-time Voice Conversations** - Natural speech-to-speech interactions
- **Live Dashboard** - See conversations and appointments in real-time
- **AI-powered Booking** - The assistant collects patient info and creates appointments
- **3 Doctors Schedule** - Visual calendar showing today's appointments
- **WebSocket Updates** - Instant dashboard updates when appointments are made

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND (React + TypeScript)               │
│  ┌─────────────────────┐    ┌─────────────────────────────────┐ │
│  │   Chat Live (50%)   │    │     Calendar Doctori (50%)      │ │
│  │   - User messages   │    │   - Dr. Popescu (Ortodonție)    │ │
│  │   - Agent responses │    │   - Dr. Ionescu (Chirurgie)     │ │
│  │   - Call status     │    │   - Dr. Dumitrescu (General)    │ │
│  └─────────────────────┘    └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                    │ WebSocket
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐   │
│  │   Call Handler  │  │  Appointment    │  │   Event Bus    │   │
│  │   (Twilio ↔ AI) │  │    Service      │  │  (WebSocket)   │   │
│  └────────┬────────┘  └─────────────────┘  └────────────────┘   │
│           │                                                      │
│  ┌────────▼────────┐                                            │
│  │ OpenAI Realtime │ ← Session config + Function calling        │
│  │    Service      │                                            │
│  └─────────────────┘                                            │
└─────────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────┐            ┌─────────────────┐
│ OpenAI Realtime │            │     Twilio      │
│  (STT+LLM+TTS)  │            │  Media Streams  │
└─────────────────┘            └─────────────────┘
                                       │
                                       ▼
                                   📞 Phone
```

## Tech Stack

### Backend
- **Python 3.11+**
- **FastAPI** - Async web framework
- **WebSockets** - Real-time communication
- **Pydantic** - Data validation
- **JSON files** - Simple data storage

### Frontend
- **React 18** + **TypeScript**
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Zustand** - State management
- **Lucide React** - Icons

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API key (with Realtime API access)
- Twilio account with a phone number
- ngrok (for local development)

### 1. Clone and Setup

```bash
git clone <repo-url>
cd dental-voice-assistant
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your OPENAI_API_KEY
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
```

### 4. Run Locally

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
python -m app.main
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Terminal 3 - ngrok (for Twilio):**
```bash
ngrok http 5050
```

### 5. Configure Twilio

1. Go to [Twilio Console](https://console.twilio.com/)
2. Select your phone number
3. Under "Voice & Fax" → "A Call Comes In":
   - Webhook URL: `https://your-ngrok-url.ngrok.io/incoming-call`
   - HTTP Method: POST

### 6. Test

1. Open http://localhost:5173 in your browser
2. Call your Twilio number
3. Watch the conversation appear in real-time!

## Project Structure

```
dental-voice-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Settings
│   │   ├── routers/             # API endpoints
│   │   │   ├── health.py
│   │   │   ├── config.py
│   │   │   ├── appointments.py
│   │   │   ├── calls.py
│   │   │   └── websockets.py
│   │   ├── services/            # Business logic
│   │   │   ├── event_bus.py
│   │   │   ├── appointment.py
│   │   │   ├── openai_realtime.py
│   │   │   └── call_handler.py
│   │   ├── models/              # Pydantic models
│   │   └── utils/               # Utilities
│   ├── data/                    # JSON data files
│   │   ├── clinic.json
│   │   ├── doctors.json
│   │   ├── services.json
│   │   └── appointments.json
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/           # Chat UI
│   │   │   ├── calendar/       # Schedule UI
│   │   │   └── layout/         # Dashboard
│   │   ├── hooks/              # Custom hooks
│   │   ├── stores/             # Zustand stores
│   │   ├── services/           # API client
│   │   ├── types/              # TypeScript types
│   │   └── lib/                # Utilities
│   ├── package.json
│   └── vite.config.ts
│
├── render.yaml                  # Render deployment config
└── README.md
```

## API Endpoints

### REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/config` | Full clinic configuration |
| GET | `/api/appointments` | Today's appointments |
| POST | `/api/appointments` | Create appointment |
| DELETE | `/api/appointments/:id` | Cancel appointment |

### WebSocket Endpoints

| Endpoint | Description |
|----------|-------------|
| `/ws/dashboard` | Real-time dashboard updates |
| `/media-stream` | Twilio media stream (audio) |

### Twilio Webhook

| Endpoint | Description |
|----------|-------------|
| `/incoming-call` | Twilio incoming call webhook |

## WebSocket Events

Events sent to dashboard:

```typescript
// Call started
{ type: "call_started", data: { call_id, caller_number } }

// Call ended
{ type: "call_ended", data: { call_id, duration_seconds } }

// User speech transcript
{ type: "transcript_user", data: { call_id, text, is_final } }

// Agent response transcript
{ type: "transcript_agent", data: { call_id, text, is_final } }

// Appointment created (by AI or dashboard)
{ type: "appointment_created", data: { appointment } }

// Connection status
{ type: "connection_status", data: { status, message } }
```

## AI Assistant Behavior

The AI assistant is configured to:

1. **Greet** with one of several Romanian greeting templates
2. **Provide information** about services and prices
3. **Check availability** for doctors
4. **Collect patient information**:
   - Full name
   - Phone number
   - Desired service
   - Preferred doctor
   - Preferred time
5. **Create appointments** via function calling
6. **Confirm** the booking verbally

### Function Calling

The assistant uses OpenAI's function calling to create appointments:

```json
{
  "name": "create_appointment",
  "parameters": {
    "doctor_id": "dr-popescu",
    "time": "10:00",
    "patient_name": "Ion Popescu",
    "patient_phone": "+40722123456",
    "service_id": "consultatie"
  }
}
```

## Deployment on Render

1. Fork this repository
2. Connect to [Render](https://render.com)
3. Create new "Blueprint" and select the repo
4. Add environment variable:
   - `OPENAI_API_KEY`: Your OpenAI API key
5. Deploy!

After deployment:
1. Get your backend URL (e.g., `https://dental-voice-backend.onrender.com`)
2. Configure Twilio webhook to: `https://dental-voice-backend.onrender.com/incoming-call`

## Environment Variables

### Backend (.env)

```env
# Required
OPENAI_API_KEY=sk-...

# Optional
OPENAI_MODEL=gpt-4o-realtime-preview-2024-12-17
OPENAI_VOICE=alloy
PORT=5050
ENVIRONMENT=development
DEBUG=false
CORS_ORIGINS=http://localhost:5173
```

## Customization

### Change Clinic Info

Edit `backend/data/clinic.json`:

```json
{
  "name": "Your Clinic Name",
  "phone": "+40 XXX XXX XXX",
  "address": "Your Address",
  "greeting_templates": [
    "Your custom greeting..."
  ]
}
```

### Add/Modify Doctors

Edit `backend/data/doctors.json`

### Add/Modify Services

Edit `backend/data/services.json`

### Change AI Voice

Set `OPENAI_VOICE` environment variable to one of:
- `alloy`
- `echo`
- `fable`
- `onyx`
- `nova`
- `shimmer`

## Troubleshooting

### "Failed to connect to OpenAI"
- Verify `OPENAI_API_KEY` is correct
- Check you have Realtime API access

### No audio / Call disconnects
- Ensure ngrok is running and URL is correct in Twilio
- Check Twilio console for errors

### Dashboard not updating
- Check WebSocket connection in browser dev tools
- Verify CORS_ORIGINS includes your frontend URL

### Appointment not created
- Check backend logs for function call errors
- Verify all required fields are being collected

## License

MIT
