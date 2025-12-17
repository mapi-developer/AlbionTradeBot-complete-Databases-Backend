import asyncio
from typing import Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
import models

class PriceUpdateBuffer:
    def __init__(self):
        self._buffer: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def add_updates(self, updates: list):
        async with self._lock:
            for item in updates:
                data = item.model_dump(exclude_unset=True)
                name = data.pop("unique_name")

                if not data:
                    continue

                if name not in self._buffer:
                    self._buffer[name] = {}
                
                self._buffer[name].update(data)

    async def flush(self, db: AsyncSession):
        async with self._lock:
            if not self._buffer:
                return 0
            
            items_to_update = self._buffer.copy()
            self._buffer.clear()

        count = 0
        try:
            for unique_name, fields in items_to_update.items():
                fields["updated_at"] = datetime.now(timezone.utc)
                
                stmt = (
                    update(models.Item)
                    .where(models.Item.unique_name == unique_name)
                    .values(**fields)
                )
                await db.execute(stmt)
                count += 1
            
            await db.commit()
            return count
        except Exception as e:
            print(f"Error flushing buffer: {e}")
            return 0

price_buffer = PriceUpdateBuffer()