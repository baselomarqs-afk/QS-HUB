"""ASGI webhook endpoint for Dodo Payments.

Run separately from Streamlit:
    uvicorn payment_webhook_app:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from utils.payments import handle_dodo_webhook


app = FastAPI(title="THE QTO Dodo Payments Webhooks")


@app.post("/webhooks/dodopayments")
async def dodo_webhook(request: Request):
    payload = await request.body()
    try:
        ok, message = handle_dodo_webhook(payload, request.headers)
        return JSONResponse({"ok": ok, "message": message})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
