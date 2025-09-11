from fastapi import APIRouter, Depends, Query

from ..auth import verify_api_key
from ..storage import redis_client


router = APIRouter(prefix="/streams", dependencies=[Depends(verify_api_key)])


@router.get("/{stream}")
async def read_stream(stream: str, limit: int = Query(10, ge=1, le=100)):
    """Return recent entries from a Redis stream.

    Parameters
    ----------
    stream: str
        Name of the stream without namespace prefix.
    limit: int
        Maximum number of entries to return.
    """

    entries = await redis_client.xrange(stream)
    recent = entries[-limit:]
    return [{"id": entry_id, "fields": fields} for entry_id, fields in recent]

