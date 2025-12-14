"""
Call handler service that orchestrates communication between Twilio and OpenAI.
Manages the full lifecycle of a voice call.
"""

import json
import asyncio
from datetime import datetime, date
from typing import Optional, Dict, Any
from fastapi import WebSocket

from app.config import settings
from app.utils.logging import get_logger, CallLogger
from app.utils.json_store import json_store
from app.utils.prompt_builder import build_system_prompt, get_appointment_tool_definition
from app.services.openai_realtime import OpenAIRealtimeService
from app.services.appointment import appointment_service
from app.services.event_bus import event_bus

logger = get_logger(__name__)


class CallHandler:
    """
    Handles a single voice call, managing bidirectional audio streaming
    between Twilio and OpenAI Realtime API.
    """
    
    def __init__(self, call_id: str):
        self.call_id = call_id
        self.log = CallLogger(call_id)
        
        self.twilio_ws: Optional[WebSocket] = None
        self.openai_service: Optional[OpenAIRealtimeService] = None
        
        self.stream_sid: Optional[str] = None
        self.caller_number: Optional[str] = None
        self.call_start_time: Optional[datetime] = None
        
        self._running = False
        self._agent_transcript_buffer = ""
    
    async def handle_call(self, twilio_ws: WebSocket) -> None:
        """
        Main entry point for handling a call.
        Sets up connections and manages the call lifecycle.
        """
        self.twilio_ws = twilio_ws
        self.call_start_time = datetime.utcnow()
        self._running = True
        
        try:
            # Load clinic data for the AI
            clinic_data = await self._load_clinic_data()
            
            # Initialize OpenAI connection
            self.openai_service = OpenAIRealtimeService(self.call_id)
            
            # Set up callbacks
            self.openai_service.on_audio = self._handle_openai_audio
            self.openai_service.on_transcript_user = self._handle_user_transcript
            self.openai_service.on_transcript_agent = self._handle_agent_transcript
            self.openai_service.on_function_call = self._handle_function_call
            self.openai_service.on_error = self._handle_openai_error
            
            # Connect to OpenAI
            system_prompt = build_system_prompt(
                clinic=clinic_data["clinic"],
                doctors=clinic_data["doctors"],
                services=clinic_data["services"],
                appointments=clinic_data["appointments"],
                target_date=date.today()
            )
            
            tools = [get_appointment_tool_definition()]
            
            connected = await self.openai_service.connect(system_prompt, tools)
            if not connected:
                self.log.error("Failed to connect to OpenAI")
                return
            
            # Run both handlers concurrently
            twilio_task = asyncio.create_task(self._handle_twilio_messages())
            openai_task = asyncio.create_task(self.openai_service.handle_messages())
            
            # Wait for either to complete (call ended)
            done, pending = await asyncio.wait(
                [twilio_task, openai_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
        except Exception as e:
            self.log.error(f"Error handling call: {e}")
        finally:
            await self._cleanup()
    
    async def _load_clinic_data(self) -> Dict[str, Any]:
        """Load all clinic data needed for the AI."""
        clinic = await json_store.read("clinic.json")
        doctors = await json_store.read("doctors.json")
        services = await json_store.read("services.json")
        appointments = await appointment_service.get_all(
            filter_date=date.today().isoformat()
        )
        
        return {
            "clinic": clinic,
            "doctors": doctors,
            "services": services,
            "appointments": appointments
        }
    
    async def _handle_twilio_messages(self) -> None:
        """Process incoming messages from Twilio."""
        try:
            while self._running:
                message = await self.twilio_ws.receive_text()
                data = json.loads(message)
                event_type = data.get("event")
                
                if event_type == "connected":
                    self.log.info("Twilio stream connected")
                    
                elif event_type == "start":
                    self.stream_sid = data["start"]["streamSid"]
                    self.caller_number = data["start"].get("callSid", "unknown")
                    self.log.info(f"Stream started - SID: {self.stream_sid[:20]}...")
                    
                    # Notify dashboard
                    await event_bus.publish_call_started(
                        self.call_id, 
                        self.caller_number
                    )
                    
                elif event_type == "media":
                    # Forward audio to OpenAI
                    audio_payload = data["media"]["payload"]
                    if self.openai_service and self.openai_service.is_connected:
                        await self.openai_service.send_audio(audio_payload)
                        
                elif event_type == "stop":
                    self.log.info("Twilio stream stopped")
                    self._running = False
                    break
                    
        except Exception as e:
            self.log.error(f"Error in Twilio handler: {e}")
            self._running = False
    
    async def _handle_openai_audio(self, audio_base64: str) -> None:
        """Send audio from OpenAI to Twilio."""
        if not self.twilio_ws or not self.stream_sid:
            return
            
        try:
            media_message = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {
                    "payload": audio_base64
                }
            }
            await self.twilio_ws.send_json(media_message)
        except Exception as e:
            self.log.error(f"Error sending audio to Twilio: {e}")
    
    async def _handle_user_transcript(self, text: str, is_final: bool) -> None:
        """Handle user speech transcription."""
        if is_final and text.strip():
            self.log.info(f"User: {text}")
            await event_bus.publish_transcript(
                self.call_id, 
                text, 
                is_user=True,
                is_final=is_final
            )
    
    async def _handle_agent_transcript(self, delta: str) -> None:
        """Handle agent response transcription (streaming)."""
        self._agent_transcript_buffer += delta
        
        # Send periodic updates for long responses
        if len(self._agent_transcript_buffer) > 50 or delta.endswith(('.', '!', '?')):
            await event_bus.publish_transcript(
                self.call_id,
                self._agent_transcript_buffer,
                is_user=False,
                is_final=delta.endswith(('.', '!', '?'))
            )
            if delta.endswith(('.', '!', '?')):
                self._agent_transcript_buffer = ""
    
    async def _handle_function_call(
        self, 
        function_name: str, 
        arguments: Dict[str, Any]
    ) -> str:
        """
        Handle function calls from OpenAI.
        Returns JSON string result.
        """
        if function_name == "create_appointment":
            return await self._create_appointment(arguments)
        
        return json.dumps({
            "success": False,
            "error": f"Unknown function: {function_name}"
        })
    
    async def _create_appointment(self, args: Dict[str, Any]) -> str:
        """Handle create_appointment function call."""
        try:
            success, message, appointment = await appointment_service.create(
                doctor_id=args.get("doctor_id", ""),
                target_date=date.today().isoformat(),
                time=args.get("time", ""),
                patient_name=args.get("patient_name", ""),
                patient_phone=args.get("patient_phone", ""),
                service_id=args.get("service_id", ""),
                created_by=f"call-{self.call_id[:8]}"
            )
            
            if success and appointment:
                # Load doctor and service names for confirmation
                doctors = await json_store.read("doctors.json")
                services = await json_store.read("services.json")
                
                doctor_name = next(
                    (d["name"] for d in doctors if d["id"] == appointment["doctor_id"]),
                    appointment["doctor_id"]
                )
                service_name = next(
                    (s["name"] for s in services if s["id"] == appointment["service_id"]),
                    appointment["service_id"]
                )
                
                return json.dumps({
                    "success": True,
                    "message": message,
                    "appointment": {
                        "doctor_name": doctor_name,
                        "service_name": service_name,
                        "date": appointment["date"],
                        "time": appointment["time"],
                        "patient_name": appointment["patient_name"]
                    }
                })
            else:
                return json.dumps({
                    "success": False,
                    "error": message
                })
                
        except Exception as e:
            self.log.error(f"Error creating appointment: {e}")
            return json.dumps({
                "success": False,
                "error": "A apărut o eroare. Vă rugăm să încercați din nou."
            })
    
    async def _handle_openai_error(self, error: str) -> None:
        """Handle errors from OpenAI."""
        self.log.error(f"OpenAI error: {error}")
        await event_bus.publish_error("openai_error", error)
    
    async def _clear_twilio_buffer(self) -> None:
        """Clear Twilio's audio buffer (for interruptions)."""
        if self.twilio_ws and self.stream_sid:
            try:
                clear_message = {
                    "event": "clear",
                    "streamSid": self.stream_sid
                }
                await self.twilio_ws.send_json(clear_message)
                self.log.debug("Cleared Twilio audio buffer")
            except Exception as e:
                self.log.error(f"Error clearing Twilio buffer: {e}")
    
    async def _cleanup(self) -> None:
        """Clean up resources when call ends."""
        self._running = False
        
        # Calculate call duration
        duration = 0
        if self.call_start_time:
            duration = int((datetime.utcnow() - self.call_start_time).total_seconds())
        
        # Disconnect from OpenAI
        if self.openai_service:
            await self.openai_service.disconnect()
        
        # Notify dashboard
        await event_bus.publish_call_ended(self.call_id, duration)
        
        self.log.info(f"Call ended. Duration: {duration}s")
