"""
JSON file storage utility for simple data persistence.
Provides async read/write operations for JSON files.
"""

import json
import os
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, date

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime and date objects."""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


class JsonStore:
    """
    Simple JSON file-based storage.
    Thread-safe through asyncio locks.
    """
    
    def __init__(self):
        self._locks: Dict[str, asyncio.Lock] = {}
    
    def _get_lock(self, filename: str) -> asyncio.Lock:
        """Get or create a lock for the given file."""
        if filename not in self._locks:
            self._locks[filename] = asyncio.Lock()
        return self._locks[filename]
    
    def _get_path(self, filename: str) -> str:
        """Get full path for a data file."""
        return os.path.join(settings.data_dir, filename)
    
    async def read(self, filename: str) -> Any:
        """
        Read data from a JSON file.
        
        Args:
            filename: Name of the JSON file (e.g., 'appointments.json')
            
        Returns:
            Parsed JSON data, or empty list/dict if file doesn't exist.
        """
        path = self._get_path(filename)
        lock = self._get_lock(filename)
        
        async with lock:
            try:
                if not os.path.exists(path):
                    logger.warning(f"File not found: {path}")
                    return [] if 'appointments' in filename else {}
                
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in {filename}: {e}")
                return [] if 'appointments' in filename else {}
            except Exception as e:
                logger.error(f"Error reading {filename}: {e}")
                raise
    
    async def write(self, filename: str, data: Any) -> None:
        """
        Write data to a JSON file.
        
        Args:
            filename: Name of the JSON file
            data: Data to write (must be JSON serializable)
        """
        path = self._get_path(filename)
        lock = self._get_lock(filename)
        
        async with lock:
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(path), exist_ok=True)
                
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
                    
                logger.debug(f"Wrote data to {filename}")
            except Exception as e:
                logger.error(f"Error writing {filename}: {e}")
                raise
    
    async def append_to_list(self, filename: str, item: Dict) -> None:
        """
        Append an item to a JSON array file.
        
        Args:
            filename: Name of the JSON file containing an array
            item: Item to append
        """
        data = await self.read(filename)
        if not isinstance(data, list):
            data = []
        data.append(item)
        await self.write(filename, data)
    
    async def update_in_list(
        self, 
        filename: str, 
        item_id: str, 
        updates: Dict,
        id_field: str = "id"
    ) -> Optional[Dict]:
        """
        Update an item in a JSON array file by ID.
        
        Args:
            filename: Name of the JSON file
            item_id: ID of the item to update
            updates: Dictionary of fields to update
            id_field: Name of the ID field
            
        Returns:
            Updated item or None if not found.
        """
        data = await self.read(filename)
        if not isinstance(data, list):
            return None
        
        for i, item in enumerate(data):
            if item.get(id_field) == item_id:
                data[i] = {**item, **updates}
                await self.write(filename, data)
                return data[i]
        
        return None
    
    async def delete_from_list(
        self, 
        filename: str, 
        item_id: str,
        id_field: str = "id"
    ) -> bool:
        """
        Delete an item from a JSON array file by ID.
        
        Args:
            filename: Name of the JSON file
            item_id: ID of the item to delete
            id_field: Name of the ID field
            
        Returns:
            True if deleted, False if not found.
        """
        data = await self.read(filename)
        if not isinstance(data, list):
            return False
        
        original_length = len(data)
        data = [item for item in data if item.get(id_field) != item_id]
        
        if len(data) < original_length:
            await self.write(filename, data)
            return True
        
        return False


# Global store instance
json_store = JsonStore()
