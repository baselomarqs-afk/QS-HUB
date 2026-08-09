"""
الوحدة المركزية لتتبع زوار الموقع — Centralized Visitor Analytics Helper
========================================================================
تسجيل آمن بدون أي تأثير على الأداء (Non-blocking & Error-Isolated)
"""
import logging
from datetime import datetime, timedelta
from utils.db import safe_execute, safe_query

logger = logging.getLogger("qto.visitor")

def log_visitor_hit(ip_address: str, path: str, user_agent: str = "", referer: str = "") -> None:
    """
    سجل زيارة جديدة في قاعدة البيانات بأمان كامل (إهمال الصامت لأي خطأ حتى لا يكتنز أداء السيرفر).
    """
    try:
        if not ip_address:
            ip_address = "127.0.0.1"
        clean_path = (path or "/")[:255]
        clean_ua = (user_agent or "")[:512]
        clean_ref = (referer or "")[:512]

        safe_execute(
            "INSERT INTO qto_visitor_logs (ip_address, path, user_agent, referer) VALUES (%s, %s, %s, %s)",
            (ip_address, clean_path, clean_ua, clean_ref)
        )
    except Exception as e:
        logger.debug(f"Silent visitor log failure: {e}")

def get_visitor_stats() -> dict:
    """
    إرجاع إحصائيات الزوار خلال الـ 24 ساعة الماضية واليوم الحسابي.
    """
    now = datetime.utcnow()
    t_24h = (now - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
    today = now.strftime('%Y-%m-%d')

    visitors_24h = 0
    unique_visitors_24h = 0
    visitors_today = 0

    try:
        df_24h = safe_query("SELECT ip_address FROM qto_visitor_logs WHERE created_at >= %s", (t_24h,))
        if not df_24h.empty:
            visitors_24h = len(df_24h)
            unique_visitors_24h = len(df_24h['ip_address'].unique())

        df_today = safe_query("SELECT id FROM qto_visitor_logs WHERE DATE(created_at) = %s", (today,))
        if not df_today.empty:
            visitors_today = len(df_today)
    except Exception as e:
        logger.error(f"Error fetching visitor stats: {e}")

    return {
        "visitors_24h": visitors_24h,
        "unique_visitors_24h": unique_visitors_24h,
        "visitors_today": visitors_today
    }
