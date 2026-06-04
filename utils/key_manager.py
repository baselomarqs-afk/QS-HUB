"""
مدير مفاتيح الـ API — يدور بين المفاتيح والنماذج تلقائياً (2D Rotation)
=======================================================
يدور بين 3 نماذج مختلفة (Flash, Flash-Lite 2.5, Flash-Lite 3.1) 
مضروبة في عدد المفاتيح لتجاوز حدود الـ RPM والـ RPD تماماً.
=======================================================
"""
import os
import time
import threading
from typing import List, Optional, Tuple
from datetime import datetime, date


# ── Monkeypatch google.genai.Client to disable HTTP/2 and prevent timeouts on Windows / proxy networks ──
try:
    from google import genai
    from google.genai import types
    import httpx
    
    _orig_init = genai.Client.__init__

    def patched_init(self, *args, **kwargs):
        if 'http_options' not in kwargs:
            kwargs['http_options'] = {}
            
        http_opts = kwargs['http_options']
        if isinstance(http_opts, dict):
            timeout_val = http_opts.get('timeout', 60.0)
            http_opts['httpx_client'] = httpx.Client(timeout=timeout_val, http2=False)
            http_opts['httpx_async_client'] = httpx.AsyncClient(timeout=timeout_val, http2=False)
            
            clean_opts = {k: v for k, v in http_opts.items() if k != 'timeout'}
            kwargs['http_options'] = types.HttpOptions(**clean_opts)
        elif isinstance(http_opts, types.HttpOptions):
            if not http_opts.httpx_client:
                http_opts.httpx_client = httpx.Client(timeout=60.0, http2=False)
            if not http_opts.httpx_async_client:
                http_opts.httpx_async_client = httpx.AsyncClient(timeout=60.0, http2=False)
                
        _orig_init(self, *args, **kwargs)

    genai.Client.__init__ = patched_init
except Exception:
    pass

# النماذج التي سيتم التدوير بينها مع كل مفتاح
ROTATION_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash"
]

# ── حدود النماذج المختلفة (RPD) ──────────────────────────────────────────────
MODEL_DAILY_LIMITS = {
    "gemini-3.1-flash-lite":      500,
    "gemini-2.5-flash":           1500,
    "default":                    1500,
}

class KeyManager:
    """
    يدير مصفوفة ثنائية الأبعاد (مفتاح × نموذج) ويدور بينها.
    - يتتبع عدد الاستخدامات لكل (مفتاح، نموذج)
    - يتخطى التركيبة التي تصل حدها (429)
    """

    def __init__(self, keys: List[str]):
        self._keys  = [k.strip() for k in keys if k and k.strip()]
        self._lock  = threading.Lock()

        # Rotate keys first, then models — spreads RPM load across keys before hitting same model twice
        self._combinations = []
        for k in self._keys:
            for m in ROTATION_MODELS:
                self._combinations.append((k, m))

        self._index = 0
        self._usage: dict = {}
        for k, m in self._combinations:
            self._usage[(k, m)] = {"count": 0, "date": date.today(), "exhausted": False, "exhausted_at": 0}

    # ── Public API ────────────────────────────────────────────────────────────

    def get_key_and_model(self) -> Tuple[Optional[str], str]:
        """يرجع التركيبة الحالية النشطة (المفتاح والنموذج) ويزيد عدادها."""
        with self._lock:
            self._reset_daily_counts()
            combo = self._active_combo()
            if combo:
                self._usage[combo]["count"] += 1
                self._advance()
                return combo
            return None, "gemini-3.1-flash-lite" # fallback if all exhausted

    def mark_rate_limited(self, key: str, model: str):
        """استدعِ هذا عند استقبال 429 — يتخطى هذه التركيبة لمدة 60 ثانية فقط."""
        with self._lock:
            combo = (key, model)
            if combo in self._usage:
                self._usage[combo]["exhausted"] = True
                self._usage[combo]["exhausted_at"] = time.time()

    def mark_exhausted(self, key: str, model: str):
        """علّم تركيبة باعتبارها منتهية يدوياً."""
        self.mark_rate_limited(key, model)

    def status(self) -> List[dict]:
        """ملخص حالة كل التركيبات."""
        with self._lock:
            self._reset_daily_counts()
            active_combo = self._active_combo()
            res = []
            for combo in self._combinations:
                k, m = combo
                u = self._usage[combo]
                limit = MODEL_DAILY_LIMITS.get(m, MODEL_DAILY_LIMITS["default"])
                res.append({
                    "key_hint":  f"...{k[-8:]}",
                    "model":     m,
                    "requests":  u["count"],
                    "limit":     limit,
                    "remaining": max(limit - u["count"], 0),
                    "exhausted": u["exhausted"],
                    "active":    (combo == active_combo),
                })
            return res

    def total_remaining(self) -> int:
        """مجموع الطلبات المتبقية لكل التركيبات."""
        with self._lock:
            self._reset_daily_counts()
            total = 0
            for combo in self._combinations:
                k, m = combo
                if not self._usage[combo]["exhausted"]:
                    limit = MODEL_DAILY_LIMITS.get(m, MODEL_DAILY_LIMITS["default"])
                    total += max(limit - self._usage[combo]["count"], 0)
            return total

    def key_count(self) -> int:
        return len(self._keys)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _active_combo(self) -> Optional[Tuple[str, str]]:
        """يبحث عن أول تركيبة غير منتهية. المفاتيح المعلّقة تنتهي بعد 60 ثانية تلقائياً."""
        if not self._combinations:
            return None
        now = time.time()
        for _ in range(len(self._combinations)):
            combo = self._combinations[self._index % len(self._combinations)]
            u = self._usage[combo]
            # Auto-recover after 60 seconds
            if u["exhausted"] and (now - u.get("exhausted_at", 0)) > 60:
                u["exhausted"] = False
            if not u["exhausted"]:
                return combo
            self._index += 1
        return None

    def _advance(self):
        if self._combinations:
            self._index = (self._index + 1) % len(self._combinations)

    def _reset_daily_counts(self):
        """يصفّر العداد كل يوم جديد ويُشغّل auto-exhaustion عند بلوغ الحد."""
        today = date.today()
        for combo in self._combinations:
            k, m = combo
            u = self._usage[combo]
            if u["date"] != today:
                self._usage[combo] = {"count": 0, "date": today, "exhausted": False, "exhausted_at": 0}
            else:
                # Auto-mark exhausted when daily limit reached
                limit = MODEL_DAILY_LIMITS.get(m, MODEL_DAILY_LIMITS["default"])
                if u["count"] >= limit and not u["exhausted"]:
                    u["exhausted"] = True
                    u["exhausted_at"] = time.time()


# ── تحميل المفاتيح من .env أو متغيرات البيئة ──────────────────────────────────

def _load_keys_from_env() -> List[str]:
    try:
        from dotenv import load_dotenv
        import pathlib
        env_path = pathlib.Path(__file__).resolve().parent.parent / ".env"
        load_dotenv(dotenv_path=env_path, override=False)
    except ImportError:
        pass

    multi = os.environ.get("AI_API_KEYS", "")
    if multi:
        return [k.strip() for k in multi.split(",") if k.strip()]

    numbered = []
    for i in range(1, 21):
        k = os.environ.get(f"AI_API_KEY_{i}", "")
        if k.strip():
            numbered.append(k.strip())
    if numbered:
        return numbered

    single = (os.environ.get("GOOGLE_API_KEY") or
              os.environ.get("AI_API_KEY") or "")
    return [single] if single else []

# ── Singleton ──────────────────────────────────────────────────────────────────

_manager: Optional[KeyManager] = None
_manager_lock = threading.Lock()

def get_key_manager() -> KeyManager:
    global _manager
    with _manager_lock:
        if _manager is None:
            keys = _load_keys_from_env()
            # If no keys are provided, create a dummy key so the system doesn't crash
            if not keys:
                keys = ["NO_API_KEY_FOUND"]
            _manager = KeyManager(keys)
    return _manager

def reload_manager(keys: List[str]):
    global _manager
    with _manager_lock:
        if not keys:
            keys = ["NO_API_KEY_FOUND"]
        _manager = KeyManager(keys)

def print_status():
    mgr = get_key_manager()
    print(f"\n{'═'*80}")
    print(f"  مدير المفاتيح والنماذج — {mgr.key_count()} مفتاح | متبقي: {mgr.total_remaining()} طلب")
    print(f"{'═'*80}")
    for s in mgr.status():
        icon = "✅" if s["active"] else ("🔴" if s["exhausted"] else "⚪")
        bar  = "█" * int(s["requests"] / max(s["limit"], 1) * 20)
        bar  = bar.ljust(20, "░")
        rem  = "(منتهٍ)" if s["exhausted"] else f"متبقي: {s['remaining']}"
        m_name = s['model'][:25].ljust(25)
        print(f"  {icon} {s['key_hint']} | {m_name} | [{bar}] {s['requests']}/{s['limit']} {rem}")
    print(f"{'═'*80}\n")

