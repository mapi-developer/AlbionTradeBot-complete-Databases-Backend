import asyncio
from typing import Dict, Any, Literal
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
import models

class PriceUpdateBuffer:
    def __init__(self):
        # Structure: self._buffers[server][type] = { item_name: data }
        self._buffers: Dict[str, Dict[str, Dict[str, Any]]] = {
            "EU": {"fast": {}, "order": {}},
            "US": {"fast": {}, "order": {}},
            "AS": {"fast": {}, "order": {}},
        }
        self._lock = asyncio.Lock()

    async def add_updates(self, server: str, type_: str, updates: list):
        # Basic validation
        if server not in self._buffers or type_ not in self._buffers[server]:
            return 

        current_time = datetime.now(timezone.utc)

        async with self._lock:
            for item in updates:
                data = item.model_dump(exclude_unset=True)
                name = data.pop("unique_name")

                if not data:
                    continue

                # Add timestamps dynamically
                for key in list(data.keys()):
                    if key.startswith("price_"):
                        city_slug = key.replace("price_", "")
                        timestamp_field = f"{city_slug}_updated_at"
                        data[timestamp_field] = current_time

                if name not in self._buffers[server][type_]:
                    self._buffers[server][type_][name] = {}
                
                # Merge updates
                self._buffers[server][type_][name].update(data)

    async def flush(self, db: AsyncSession):
        async with self._lock:
            # Deep copy to snapshot current state
            buffers_snapshot = {
                server: {
                    "fast": self._buffers[server]["fast"].copy(),
                    "order": self._buffers[server]["order"].copy()
                } for server in self._buffers
            }
            
            # Clear original buffers
            for server in self._buffers:
                self._buffers[server]["fast"].clear()
                self._buffers[server]["order"].clear()

        total_count = 0
        
        try:
            # Iterate through servers (EU, US, AS)
            for server, types in buffers_snapshot.items():
                # Iterate through types (fast, order)
                for type_name, data_map in types.items():
                    if data_map:
                        # Dynamic Model Selection
                        model_class = models.MODEL_MAP[server][type_name]
                        total_count += await self._flush_data(db, model_class, data_map)
            
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