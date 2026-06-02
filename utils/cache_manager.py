"""
مدير التخزين المؤقت لاستجابات الذكاء الاصطناعي (AI Response Caching)
يحفظ استجابات AI سحابياً/محلياً بصيغة JSON باستخدام هاش الملف لتجنب الاستدعاء المتكرر وتوفير التكلفة.
"""
import os
import hashlib
import json
import numpy as np

CACHE_DIR = ".qto_cache"


def get_file_hash(data) -> str:
    """Computes SHA256 of files, bytes, or numpy arrays to index the cache."""
    hasher = hashlib.sha256()
    
    if isinstance(data, str):
        # File path
        if not os.path.exists(data):
            return ""
        try:
            with open(data, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
        except Exception:
            return ""
    elif isinstance(data, bytes):
        hasher.update(data)
    elif isinstance(data, np.ndarray):
        hasher.update(data.tobytes())
    else:
        # Fallback to string representation
        hasher.update(str(data).encode("utf-8"))
        
    return hasher.hexdigest()


def get_cached_response(file_hash: str, prompt_key: str) -> str:
    """Reads response from local JSON cache if exists."""
    if not file_hash or not prompt_key:
        return None
        
    cache_file = os.path.join(CACHE_DIR, f"{file_hash}.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
                return cache_data.get(prompt_key)
        except Exception:
            pass
    return None


def save_cached_response(file_hash: str, prompt_key: str, response_text: str):
    """Saves AI response in the local JSON cache."""
    if not file_hash or not prompt_key or not response_text:
        return
        
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, f"{file_hash}.json")
    
    cache_data = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
        except Exception:
            pass
            
    cache_data[prompt_key] = response_text
    
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Cache Write Error] {e}")
