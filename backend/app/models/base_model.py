from typing import Any, List, Optional, Type, TypeVar, Dict
from datetime import datetime, timezone
import asyncpg
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class DBModel:
    """
    Base class for database models.
    Handles connection management and common serialization tasks.
    """
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    @staticmethod
    def _record_to_dict(record: asyncpg.Record) -> Dict[str, Any]:
        """Convert asyncpg Record to a clean dictionary."""
        return dict(record)

    @staticmethod
    def _records_to_list(records: List[asyncpg.Record]) -> List[Dict[str, Any]]:
        """Convert list of Records to list of dicts."""
        return [dict(r) for r in records]

    def _normalize_timestamp(self, dt: Any) -> Optional[datetime]:
        """Ensure timestamps are timezone-aware UTC."""
        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        return dt
