import warnings
warnings.filterwarnings("ignore", module="streamlit")

# Make the app's own loggers (qto.*) actually emit — without this, all the
# diagnostic logging added across the codebase would be silently dropped.
import logging as _logging
_logging.getLogger("qto").setLevel(_logging.INFO)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import json
import traceback
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi import Request

import asyncio
from contextlib import asynccontextmanager

from api.auth import router as auth_router
from api.projects import router as projects_router
from api.workflow import router as workflow_router
from api.market import router as market_router
from api.agents import router as agents_router
from api.billing import router as billing_router
from api.admin import router as admin_router
from api.modules import router as modules_router
from api.routers.feedback import router as feedback_router
from utils.garbage_collection import cache_cleanup_task

# ── RENDER PROXY MODE ──
# If running on Render, serve the high-speed HuggingFace Space via an iframe for all GET requests.
# This allows keeping the custom domain (qshub.online) while using 16GB RAM for processing!
is_render = os.environ.get("RENDER") == "true" or os.environ.get("RENDER") == "1"

def _ensure_feedback_tables():
    """Ensure the ratings + complaints tables exist on MySQL.

    These were only defined in the local SQLite bootstrap, so on the production
    MySQL DB the "Rate Your Experience" insert (and the admin panel that reads
    it) had no table to hit. This runs only the two idempotent CREATE TABLE IF
    NOT EXISTS statements — it deliberately does NOT run the full migration
    suite, because migration 008 drops qto_active_projects and would wipe every
    user's in-progress project state on each startup.
    """
    from utils.db import is_sqlite, safe_execute
    if is_sqlite():
        return  # SQLite bootstrap (initialize_sqlite_db) already creates these.
    safe_execute(
        """
        CREATE TABLE IF NOT EXISTS qto_project_feedback (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            tool_name VARCHAR(100) NOT NULL,
            project_name VARCHAR(255) NOT NULL,
            rating INT NOT NULL,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    safe_execute(
        """
        CREATE TABLE IF NOT EXISTS qto_customer_complaints (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            complaint_text TEXT NOT NULL,
            status VARCHAR(50) DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Make sure the feedback/complaints tables exist (MySQL prod). Best-effort:
    # never let a DB hiccup stop the app from booting.
    try:
        _ensure_feedback_tables()
    except Exception as _e:
        _logging.getLogger("qto").warning("ensure feedback tables failed: %s", _e)
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

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    err_str = traceback.format_exc()
    _logging.getLogger("qto").error("GLOBAL EXCEPTION: %s", err_str)
    return JSONResponse(status_code=200, content={"detail": "Internal Server Error", "traceback": err_str})

@app.get("/test-health")
def test_health():
    return {"status": "ok"}



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



# Include API Routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(projects_router, prefix="/api/projects", tags=["Projects"])
app.include_router(workflow_router, prefix="/api/workflow", tags=["Workflow"])
app.include_router(market_router, prefix="/api/market", tags=["Market Prices"])
app.include_router(agents_router, prefix="/api/agents", tags=["AI Agents"])
app.include_router(billing_router, prefix="/api/billing", tags=["Billing"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin Dashboard"])
app.include_router(modules_router, prefix="/api/modules", tags=["Programme & Cash Flow"])
app.include_router(feedback_router, prefix="/api/feedback", tags=["Feedback"])

@app.post("/webhooks/dodopayments")
async def dodo_webhook(request: Request):
    payload = await request.body()
    try:
        from utils.payments import handle_dodo_webhook
        ok, message = handle_dodo_webhook(payload, request.headers)
        return {"ok": ok, "message": message}
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

# Cached PDF page images. These are CONFIDENTIAL engineering drawings, so the
# folder is NOT served as public static files. Access requires a valid session
# and (for project-scoped paths) ownership of that project.
cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_qto_cache")
os.makedirs(cache_dir, exist_ok=True)

from fastapi import HTTPException as _HTTPException
from fastapi.responses import FileResponse

# ── Cache-image serving speedup ──
# A drawing page fires one <img> request per preview, so this route runs in a
# burst of dozens of hits. The security-hardening pass replaced the old instant
# StaticFiles mount with per-request DB auth (token check + ownership check),
# which turned every image into 2 remote-DB round-trips and made previews slow.
# We keep the exact same security, but:
#   1. run as a plain `def` (FastAPI runs it in a threadpool, so the blocking DB
#      calls no longer freeze the whole server's event loop), and
#   2. cache the token/ownership results in-memory for a few seconds so a burst
#      of images for the same user/project doesn't re-hit the DB every time.
# Revocation still takes effect after the short TTL expires.
import time as _time

_AUTH_TTL = 60           # seconds a verified token is trusted before re-checking
_OWN_TTL = 300           # seconds an ownership result is cached
_auth_cache: dict = {}   # token -> (expires_at, user_dict)
_own_cache: dict = {}     # (user_id, pid) -> expires_at


@app.get("/cache/{file_path:path}")
def serve_cache(file_path: str, request: Request):
    from api.auth import verify_session_token
    from utils.db import safe_query

    now = _time.time()

    # Token from ?token= / ?Authorization= (img tags can't set headers) or header.
    token = request.query_params.get("token") or request.query_params.get("Authorization")
    if not token:
        auth = request.headers.get("authorization", "")
        token = auth
    if token and token.startswith("Bearer "):
        token = token.split(" ", 1)[1]
    if not token:
        raise _HTTPException(status_code=401, detail="Authentication required.")

    cached = _auth_cache.get(token)
    if cached and cached[0] > now:
        user = cached[1]
    else:
        user = verify_session_token(token)  # raises 401 on invalid/expired
        _auth_cache[token] = (now + _AUTH_TTL, user)

    # Path-traversal protection.
    rel = os.path.normpath(file_path).replace("\\", "/")
    full = os.path.abspath(os.path.join(cache_dir, rel))
    if not full.startswith(os.path.abspath(cache_dir) + os.sep):
        raise _HTTPException(status_code=400, detail="Invalid path.")

    # Ownership: cache images live under /cache/{project_id}/... — verify the
    # requester owns that project (admins bypass).
    parts = rel.split("/")
    if len(parts) >= 2 and parts[0].isdigit() and user.get("role") != "admin":
        pid = int(parts[0])
        own_key = (user["id"], pid)
        own_exp = _own_cache.get(own_key)
        if not (own_exp and own_exp > now):
            owned = safe_query(
                "SELECT 1 FROM qto_projects WHERE id=%s AND user_id=%s "
                "UNION SELECT 1 FROM qto_active_projects WHERE project_id=%s AND user_id=%s",
                (pid, user["id"], pid, user["id"]),
            )
            if owned.empty:
                raise _HTTPException(status_code=403, detail="Access denied.")
            _own_cache[own_key] = now + _OWN_TTL

    if not os.path.isfile(full):
        raise _HTTPException(status_code=404, detail="Not found.")
    # Let the browser reuse the image instead of re-downloading it on every
    # revisit. Short max-age + ETag revalidation means a re-upload to the same
    # project (which reuses filenames) still gets picked up quickly.
    return FileResponse(full, headers={"Cache-Control": "private, max-age=300"})

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

@app.get("/test-html", response_class=HTMLResponse)
def test_html():
    print("HTML ENDPOINT HIT!")
    return "<html><body>Hello HF Space!</body></html>"

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
    @app.get("/")
    async def serve_index():
        index_path = os.path.join(_frontend_dist, "index.html")
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=html_content)
        return {"detail": "Not Found"}

    app.mount("/", StaticFiles(directory=_frontend_dist, html=False), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
