"""
OpenAI Realtime API service.
Handles WebSocket connection and communication with OpenAI's Realtime API.
"""

import json
import asyncio
from typing import Optional, Callable, Awaitable, Dict, Any
import websockets
from websockets.client import WebSocketClientProtocol

from app.config import settings
from app.utils.logging import get_logger, CallLogger

logger = get_logger(__name__)

# OpenAI Realtime API WebSocket URL
OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime"


class OpenAIRealtimeService:
    """
    Service for managing OpenAI Realtime API connections.
    Each instance handles one call session.
    """
    
    def __init__(self, call_id: str):
        self.call_id = call_id
        self.log = CallLogger(call_id)
        self.ws: Optional[WebSocketClientProtocol] = None
        self._connected = False
        
        # Callbacks
        self.on_audio: Optional[Callable[[bytes], Awaitable[None]]] = None
        self.on_transcript_user: Optional[Callable[[str, bool], Awaitable[None]]] = None
        self.on_transcript_agent: Optional[Callable[[str], Awaitable[None]]] = None
        self.on_function_call: Optional[Callable[[str, Dict], Awaitable[str]]] = None
        self.on_error: Optional[Callable[[str], Awaitable[None]]] = None
        self.on_interruption: Optional[Callable[[], Awaitable[None]]] = None
    
    async def connect(self, system_prompt: str, tools: list) -> bool:
        """
        Connect to OpenAI Realtime API and configure the session.
        
        Args:
            system_prompt: System instructions for the AI
            tools: List of tool definitions (e.g., create_appointment)
            
        Returns:
            True if connected successfully.
        """
        try:
            url = f"{OPENAI_REALTIME_URL}?model={settings.openai_model}"
            
            self.log.info(f"Connecting to OpenAI Realtime API...")
            
            self.ws = await websockets.connect(
                url,
                additional_headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "OpenAI-Beta": "realtime=v1"
                }
            )
            
            self._connected = True
            self.log.info("Connected to OpenAI Realtime API")
            
            # Configure session
            await self._send_session_update(system_prompt, tools)
            
            return True
            
        except Exception as e:
            self.log.error(f"Failed to connect to OpenAI: {e}")
            return False
    
    async def _send_session_update(self, system_prompt: str, tools: list) -> None:
        """Send session configuration to OpenAI."""
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": system_prompt,
                "voice": settings.openai_voice,
                "input_audio_format": "g711_ulaw",  # Twilio's format
                "output_audio_format": "g711_ulaw",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                },
                "tools": tools,
                "tool_choice": "auto"
            }
        }
        
        await self._send(session_config)
        self.log.info("Session configuration sent")
    
    async def _send(self, message: Dict[str, Any]) -> None:
        """Send a message to OpenAI."""
        if self.ws and self._connected:
            await self.ws.send(json.dumps(message))
    
    async def send_audio(self, audio_base64: str) -> None:
        """
        Send audio data to OpenAI.
        
        Args:
            audio_base64: Base64 encoded audio in g711_ulaw format
        """
        if not self._connected:
            return
            
        message = {
            "type": "input_audio_buffer.append",
            "audio": audio_base64
        }
        await self._send(message)
    
    async def send_function_result(
        self, 
        call_id: str, 
        result: str
    ) -> None:
        """
        Send function call result back to OpenAI.
        
        Args:
            call_id: The function call ID from OpenAI
            result: JSON string result of the function
        """
        # First, send the function output
        message = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": result
            }
        }
        await self._send(message)
        
        # Then request a response
        await self._send({"type": "response.create"})
        
        self.log.info(f"Sent function result for call_id: {call_id}")
    
    async def cancel_response(self) -> None:
        """Cancel the current response (for interruptions)."""
        await self._send({"type": "response.cancel"})
    
    async def handle_messages(self) -> None:
        """
        Main loop for handling incoming messages from OpenAI.
        Should be run as an asyncio task.
        """
        if not self.ws:
            return
            
        try:
            async for raw_message in self.ws:
                try:
                    message = json.loads(raw_message)
                    await self._process_message(message)
                except json.JSONDecodeError:
                    self.log.warning("Received invalid JSON from OpenAI")
                except Exception as e:
                    self.log.error(f"Error processing message: {e}")
                    
        except websockets.exceptions.ConnectionClosed as e:
            self.log.info(f"OpenAI connection closed: {e.code} - {e.reason}")
        except Exception as e:
            self.log.error(f"Error in message handler: {e}")
        finally:
            self._connected = False
    
    async def _process_message(self, message: Dict[str, Any]) -> None:
        """Process a single message from OpenAI."""
        event_type = message.get("type", "")
        
        # Session events
        if event_type == "session.created":
            self.log.info("Session created")
            
        elif event_type == "session.updated":
            self.log.info("Session updated")
            
        # Audio output
        elif event_type == "response.audio.delta":
            audio_base64 = message.get("delta", "")
            if audio_base64 and self.on_audio:
                await self.on_audio(audio_base64)
                
        # User transcription
        elif event_type == "conversation.item.input_audio_transcription.completed":
            transcript = message.get("transcript", "")
            if transcript and self.on_transcript_user:
                await self.on_transcript_user(transcript, True)
                
        # Agent response text
        elif event_type == "response.audio_transcript.delta":
            delta = message.get("delta", "")
            if delta and self.on_transcript_agent:
                await self.on_transcript_agent(delta)
                
        elif event_type == "response.audio_transcript.done":
            transcript = message.get("transcript", "")
            self.log.info(f"Agent: {transcript}")
                
        # Function calling
        elif event_type == "response.function_call_arguments.done":
            await self._handle_function_call(message)
            
        # Interruption
        elif event_type == "input_audio_buffer.speech_started":
            self.log.debug("User started speaking (potential interruption)")
            
        elif event_type == "input_audio_buffer.speech_stopped":
            self.log.debug("User stopped speaking")
            
        # Response lifecycle
        elif event_type == "response.created":
            self.log.debug("Response started")
            
        elif event_type == "response.done":
            self.log.debug("Response completed")
            
        # Errors
        elif event_type == "error":
            error_msg = message.get("error", {}).get("message", "Unknown error")
            self.log.error(f"OpenAI error: {error_msg}")
            if self.on_error:
                await self.on_error(error_msg)
                
        # Rate limits
        elif event_type == "rate_limits.updated":
            # Log for monitoring but don't act on it
            if settings.debug:
                self.log.debug(f"Rate limits updated: {message.get('rate_limits', [])}")
    
    async def _handle_function_call(self, message: Dict[str, Any]) -> None:
        """Handle a function call from OpenAI."""
        function_name = message.get("name", "")
        call_id = message.get("call_id", "")
        
        try:
            arguments = json.loads(message.get("arguments", "{}"))
        except json.JSONDecodeError:
            arguments = {}
        
        self.log.info(f"Function call: {function_name} with args: {arguments}")
        
        if self.on_function_call:
            try:
                result = await self.on_function_call(function_name, arguments)
                await self.send_function_result(call_id, result)
            except Exception as e:
                error_result = json.dumps({
                    "success": False,
                    "error": str(e)
                })
                await self.send_function_result(call_id, error_result)
    
    async def disconnect(self) -> None:
        """Disconnect from OpenAI."""
        self._connected = False
        if self.ws:
            await self.ws.close()
            self.log.info("Disconnected from OpenAI")
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to OpenAI."""
        return self._connected
