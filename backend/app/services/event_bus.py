"""
Event bus for broadcasting events to connected dashboard clients.
Implements a simple pub/sub pattern using asyncio.
"""

import asyncio
from typing import Dict, Set, Any, Callable, Awaitable
from datetime import datetime
import json

from app.utils.logging import get_logger

logger = get_logger(__name__)


class EventBus:
    """
    In-memory event bus for broadcasting events to dashboard WebSocket clients.
    Thread-safe through asyncio primitives.
    """
    
    def __init__(self):
        # Set of asyncio queues for each connected client
        self._subscribers: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()
    
    async def subscribe(self) -> asyncio.Queue:
        """
        Subscribe to events.
        
        Returns:
            Queue that will receive events.
        """
        queue: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._subscribers.add(queue)
            logger.info(f"New subscriber added. Total: {len(self._subscribers)}")
        return queue
    
    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        """
        Unsubscribe from events.
        
        Args:
            queue: The queue to unsubscribe.
        """
        async with self._lock:
            self._subscribers.discard(queue)
            logger.info(f"Subscriber removed. Total: {len(self._subscribers)}")
    
    async def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event_type: Type of the event (e.g., 'call_started', 'transcript_user')
            data: Event data payload
        """
        event = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        async with self._lock:
            if not self._subscribers:
                logger.debug(f"No subscribers for event: {event_type}")
                return
            
            # Send to all subscribers
            dead_queues = []
            for queue in self._subscribers:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning("Subscriber queue full, marking for removal")
                    dead_queues.append(queue)
            
            # Remove dead queues
            for queue in dead_queues:
                self._subscribers.discard(queue)
        
        logger.debug(f"Published event '{event_type}' to {len(self._subscribers)} subscribers")
    
    async def publish_call_started(self, call_id: str, caller_number: str = "") -> None:
        """Publish call started event."""
        await self.publish("call_started", {
            "call_id": call_id,
            "caller_number": caller_number
        })
    
    async def publish_call_ended(self, call_id: str, duration_seconds: int = 0) -> None:
        """Publish call ended event."""
        await self.publish("call_ended", {
            "call_id": call_id,
            "duration_seconds": duration_seconds
        })
    
    async def publish_transcript(
        self, 
        call_id: str, 
        text: str, 
        is_user: bool,
        is_final: bool = True
    ) -> None:
        """Publish transcript event."""
        event_type = "transcript_user" if is_user else "transcript_agent"
        await self.publish(event_type, {
            "call_id": call_id,
            "text": text,
            "is_final": is_final
        })
    
    async def publish_appointment_created(self, appointment: Dict[str, Any]) -> None:
        """Publish appointment created event."""
        await self.publish("appointment_created", {
            "appointment": appointment
        })
    
    async def publish_appointment_updated(self, appointment: Dict[str, Any]) -> None:
        """Publish appointment updated event."""
        await self.publish("appointment_updated", {
            "appointment": appointment
        })
    
    async def publish_appointment_deleted(self, appointment_id: str) -> None:
        """Publish appointment deleted event."""
        await self.publish("appointment_deleted", {
            "appointment_id": appointment_id
        })
    
    async def publish_error(self, code: str, message: str) -> None:
        """Publish error event."""
        await self.publish("error", {
            "code": code,
            "message": message
        })
    
    @property
    def subscriber_count(self) -> int:
        """Get current number of subscribers."""
        return len(self._subscribers)
    
    async def shutdown(self) -> None:
        """Clean shutdown of the event bus."""
        async with self._lock:
            for queue in self._subscribers:
                # Send shutdown signal
                try:
                    queue.put_nowait({"type": "shutdown"})
                except asyncio.QueueFull:
                    pass
            self._subscribers.clear()
        logger.info("Event bus shut down")


# Global event bus instance
event_bus = EventBus()
