import warnings
warnings.filterwarnings("ignore", module="streamlit")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import json

import asyncio
from contextlib import asynccontextmanager

from api.auth import router as auth_router
from api.projects import router as projects_router
from api.workflow import router as workflow_router
from api.market import router as market_router
from api.agents import router as agents_router
from api.billing import router as billing_router
from api.admin import router as admin_router
from utils.garbage_collection import cache_cleanup_task

# ── RENDER PROXY MODE ──
# If running on Render, serve the high-speed HuggingFace Space via an iframe for all GET requests.
# This allows keeping the custom domain (qshub.online) while using 16GB RAM for processing!
is_render = os.environ.get("RENDER") == "true" or os.environ.get("RENDER") == "1"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the garbage collection background task on startup
    task = asyncio.create_task(cache_cleanup_task())
    yield
    # Cancel the task on shutdown
    task.cancel()

app = FastAPI(
    title="THE QS HUB API",
    description="SaaS Backend API for Quantity Takeoff (QTO) and BOQ Automation",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for the React frontend.
# Restrict to explicit origins in production via CORS_ALLOW_ORIGINS (comma-separated).
# NOTE: allow_credentials=True is invalid with a "*" wildcard per the CORS spec.
_cors_env = os.environ.get("CORS_ALLOW_ORIGINS", "http://localhost:5173,http://localhost:8000")
ALLOWED_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Lightweight in-process rate limiting (per client IP, /api/* only) ──
# Baseline abuse protection. For multi-instance deploys move this to Redis.
# Tune with RATE_LIMIT_PER_MIN (default 120 req/min/IP).
import time as _time
from collections import defaultdict, deque
from fastapi import Request
from fastapi.responses import JSONResponse

_RATE_LIMIT = int(os.environ.get("RATE_LIMIT_PER_MIN", "120"))
_RATE_WINDOW = 60.0
_rate_hits = defaultdict(deque)


@app.middleware("http")
async def _rate_limit(request: Request, call_next):
    path = request.url.path
    if path == "/api/health" or not path.startswith("/api/"):
        return await call_next(request)
    ip = request.client.host if request.client else "unknown"
    now = _time.time()
    dq = _rate_hits[ip]
    while dq and dq[0] < now - _RATE_WINDOW:
        dq.popleft()
    if len(dq) >= _RATE_LIMIT:
        return JSONResponse(status_code=429, content={"detail": "Too many requests. Please slow down."})
    dq.append(now)
    return await call_next(request)


# Include API Routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(projects_router, prefix="/api/projects", tags=["Projects"])
app.include_router(workflow_router, prefix="/api/workflow", tags=["Workflow"])
app.include_router(market_router, prefix="/api/market", tags=["Market Prices"])
app.include_router(agents_router, prefix="/api/agents", tags=["AI Agents"])
app.include_router(billing_router, prefix="/api/billing", tags=["Billing"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin Dashboard"])

@app.post("/webhooks/dodopayments")
async def dodo_webhook(request: Request):
    payload = await request.body()
    try:
        from utils.payments import handle_dodo_webhook
        ok, message = handle_dodo_webhook(payload, request.headers)
        return {"ok": ok, "message": message}
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

# Serve static files for PDF page images cache if directory exists
cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_qto_cache")
os.makedirs(cache_dir, exist_ok=True)
app.mount("/cache", StaticFiles(directory=cache_dir), name="cache")

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_settings.json")

from fastapi import Depends
from api.admin import verify_admin

@app.get("/api/settings")
def get_settings(admin: dict = Depends(verify_admin)):
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

@app.post("/api/settings")
async def save_settings(request: Request, admin: dict = Depends(verify_admin)):
    data = await request.json()
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return {"status": "success"}

@app.get("/api/health")
async def health():
    return {
        "status": "online",
        "message": "THE QS HUB API is fully operational."
    }

# ── Serve the built React SPA (production) ──
# Mounted LAST so /api/* and /cache/* always take precedence over the catch-all.
# Skipped automatically in dev (no frontend/dist yet) — use `npm run dev` there.
_frontend_dist = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist"
)

if is_render:
    from fastapi.responses import HTMLResponse
    @app.get("/{full_path:path}")
    async def serve_iframe(full_path: str):
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>THE QS HUB</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
            <style>
                body, html { 
                    margin: 0; 
                    padding: 0; 
                    width: 100%;
                    height: 100%; 
                    height: -webkit-fill-available;
                    overflow: hidden; 
                    background: #0f172a; 
                }
                iframe { 
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%; 
                    height: 100%; 
                    border: none; 
                }
            </style>
        </head>
        <body>
            <iframe src="https://basel0-qshub.hf.space/?embed=true"></iframe>
        </body>
        </html>
        """)
elif os.path.isdir(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
