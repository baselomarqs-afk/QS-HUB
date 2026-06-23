from fastapi import APIRouter, Depends, Query
from typing import Optional, List, Dict
import pandas as pd
from api.auth import get_current_user
from utils.db import safe_query
from utils.market_prices_logic import DEFAULT_MATERIALS, EMIRATES, CATEGORIES, update_db_prices, auto_daily_update

router = APIRouter()

# Auto daily update background execution when api handles requests
try:
    auto_daily_update()
except:
    pass

@router.get("/prices")
async def get_market_prices(
    category: str = Query("all"),
    emirate: str = Query("dubai"),
    search: Optional[str] = Query(None),
    compare: bool = Query(False),
    current_user: dict = Depends(get_current_user)
):
    # Fetch live database values
    db_df = safe_query("SELECT item_name, unit, rate_aed, last_updated FROM qto_market_prices ORDER BY item_name ASC")
    
    materials = [m.copy() for m in DEFAULT_MATERIALS]
    
    if not db_df.empty:
        price_map = {}
        for idx, row in db_df.iterrows():
            price_map[row['item_name']] = row['rate_aed']
            
        for m in materials:
            for em in ["dubai", "abudhabi", "sharjah", "ajman"]:
                em_name = "Abu Dhabi" if em == "abudhabi" else em.capitalize()
                item_name = f"{m['name_en']} ({em_name})"
                if item_name in price_map:
                    m[em] = price_map[item_name]

    # Filters
    filtered = []
    for m in materials:
        if category != "all" and m["category"] != category:
            continue
            
        if search:
            q = search.lower()
            m_en = q in m["name_en"].lower()
            m_ar = q in m["name_ar"]
            m_code = q in m["code"].lower()
            if not (m_en or m_ar or m_code):
                continue
        filtered.append(m)
        
    # Format response
    result_list = []
    for m in filtered:
        item = {
            "code": m["code"],
            "name_en": m["name_en"],
            "name_ar": m["name_ar"],
            "unit": m["unit"],
            "category": m["category"],
            "accuracy": m["accuracy"],
            "last_verified": m["last_verified"]
        }
        if compare:
            item["prices"] = {
                "dubai": m["dubai"],
                "abudhabi": m["abudhabi"],
                "sharjah": m["sharjah"],
                "ajman": m["ajman"]
            }
        else:
            item["price"] = m.get(emirate, m["dubai"])
            item["emirate"] = emirate
            
        result_list.append(item)
        
    return {
        "prices": result_list,
        "emirates": EMIRATES,
        "categories": CATEGORIES
    }

@router.post("/prices/update")
async def trigger_prices_update(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        return {"ok": False, "message": "Only admins can force price updates."}
    ok, msg = update_db_prices()
    return {"ok": ok, "message": msg}
