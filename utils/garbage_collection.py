import os
import time
import shutil
import asyncio

CACHE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_qto_cache")
MAX_AGE_SECONDS = 48 * 60 * 60  # 48 hours

async def cache_cleanup_task():
    """
    Background worker for Single-Instance MVP.
    Periodically checks the _qto_cache directory and deletes project folders
    that are older than MAX_AGE_SECONDS to prevent the server's disk from filling up.
    """
    while True:
        try:
            if os.path.exists(CACHE_ROOT):
                now = time.time()
                # Iterate over project folders in the cache (e.g. _qto_cache/123)
                for entry in os.listdir(CACHE_ROOT):
                    folder_path = os.path.join(CACHE_ROOT, entry)
                    if os.path.isdir(folder_path):
                        # Get folder modification time
                        mtime = os.path.getmtime(folder_path)
                        if now - mtime > MAX_AGE_SECONDS:
                            try:
                                shutil.rmtree(folder_path)
                                print(f"[Garbage Collection] Deleted old cache folder: {folder_path}")
                            except Exception as e:
                                print(f"[Garbage Collection] Error deleting {folder_path}: {e}")
        except Exception as ex:
            print(f"[Garbage Collection] Critical error in cleanup task: {ex}")
        
        # Sleep for 6 hours before checking again
        await asyncio.sleep(6 * 60 * 60)
