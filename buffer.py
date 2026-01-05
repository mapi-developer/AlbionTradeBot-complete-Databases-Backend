import asyncio
from typing import Dict, Any, Literal
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
import models

class PriceUpdateBuffer:
    def __init__(self):
        # Separate buffers for Fast and Order items
        self._buffers: Dict[str, Dict[str, Dict[str, Any]]] = {
            "fast": {},
            "order": {}
        }
        self._lock = asyncio.Lock()

    async def add_updates(self, type_: Literal["fast", "order"], updates: list):
        if type_ not in self._buffers:
            return # Or raise error

        async with self._lock:
            for item in updates:
                data = item.model_dump(exclude_unset=True)
                name = data.pop("unique_name")

                if not data:
                    continue

                if name not in self._buffers[type_]:
                    self._buffers[type_][name] = {}
                
                self._buffers[type_][name].update(data)

    async def flush(self, db: AsyncSession):
        async with self._lock:
            # Snapshot data to flush and clear buffers
            fast_to_update = self._buffers["fast"].copy()
            order_to_update = self._buffers["order"].copy()
            
            self._buffers["fast"].clear()
            self._buffers["order"].clear()

        total_count = 0
        
        try:
            # 1. Flush ItemFast
            if fast_to_update:
                total_count += await self._flush_data(db, models.ItemFast, fast_to_update)

            # 2. Flush ItemOrder
            if order_to_update:
                total_count += await self._flush_data(db, models.ItemOrder, order_to_update)
            
            await db.commit()
            return total_count

        except Exception as e:
            print(f"Error flushing buffer: {e}")
            await db.rollback()
            return 0

    async def _flush_data(self, db: AsyncSession, model, data_map: Dict):
        count = 0
        for unique_name, fields in data_map.items():
            fields["updated_at"] = datetime.now(timezone.utc)
            
            # Update existing
            stmt = (
                update(model)
                .where(model.unique_name == unique_name)
                .values(**fields)
            )
            result = await db.execute(stmt)

            # Insert if not exists
            if result.rowcount == 0:
                new_item = model(unique_name=unique_name, **fields)
                db.add(new_item)
            
            count += 1
        return count

price_buffer = PriceUpdateBuffer()