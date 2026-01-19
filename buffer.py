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
            return 

        # Capture the time when the update ARRIVED
        current_time = datetime.now(timezone.utc)

        async with self._lock:
            for item in updates:
                data = item.model_dump(exclude_unset=True)
                name = data.pop("unique_name")

                if not data:
                    continue

                # ================= NEW LOGIC =================
                # Iterate over keys to find price fields and add timestamps
                # We use list(data.keys()) to avoid error while modifying the dict
                for key in list(data.keys()):
                    if key.startswith("price_"):
                        # Example: "price_martlock" -> "martlock"
                        city_slug = key.replace("price_", "")
                        
                        # Create the timestamp field: "martlock_updated_at"
                        timestamp_field = f"{city_slug}_updated_at"
                        
                        # Set the time
                        data[timestamp_field] = current_time
                # =============================================

                if name not in self._buffers[type_]:
                    self._buffers[type_][name] = {}
                
                # Update the buffer (merges new prices + new timestamps)
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
            # This updates the ROW'S global "updated_at" (last time anything changed)
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