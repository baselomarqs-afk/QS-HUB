"""UAE Market Prices API — serves live web-grounded UAE construction material
and labor rates across all 7 Emirates with honest timestamps & citations."""
import asyncio
from fastapi import APIRouter, Depends, Query
from typing import Optional
from api.auth import get_current_user
from utils.market_prices_logic import (
    get_live_market_snapshot,
    update_db_prices,
    auto_daily_update,
)

router = APIRouter()


@router.get("/prices")
async def get_market_prices(
    category: str = Query("all"),
    emirate: str = Query("dubai"),
    search: Optional[str] = Query(None),
    compare: bool = Query(False),
    current_user: dict = Depends(get_current_user),
):
    # Trigger non-blocking background live weekly refresh if stale (>7 days)
    auto_daily_update()
    return await asyncio.to_thread(get_live_market_snapshot, category, emirate, search, compare)


@router.post("/prices/update")
async def trigger_prices_update(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        return {"ok": False, "message": "Only administrators can trigger a live market price sync."}
    import threading
    from utils import market_prices_logic as mpl
    if mpl._SYNC_IN_PROGRESS:
        return {"ok": True, "in_progress": True, "message": "A live market price sync is already running in the background. Please refresh shortly."}
    threading.Thread(target=update_db_prices, kwargs={"force_live": True}, daemon=True).start()
    return {
        "ok": True,
        "in_progress": True,
        "message": "Live UAE Google Search market price sync started in the background (takes ~30–60s). Refresh shortly to see the latest rates.",
    }
