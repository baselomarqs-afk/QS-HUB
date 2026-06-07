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

async def background_cleanup_project(project_cache_path: str, delay_seconds: int = 3600):
    """
    Schedules a single project cache folder for deletion after a delay.
    Called after a project extraction completes to free disk space.
    """
    await asyncio.sleep(delay_seconds)
    try:
        if os.path.exists(project_cache_path) and os.path.isdir(project_cache_path):
            shutil.rmtree(project_cache_path)
            print(f"[Garbage Collection] Cleaned up project cache: {project_cache_path}")
    except Exception as e:
        print(f"[Garbage Collection] Error cleaning up {project_cache_path}: {e}")

def force_cleanup_now() -> int:
    """
    Synchronously deletes all project folders in CACHE_ROOT.
    Returns the number of folders deleted.
    """
    count = 0
    if os.path.exists(CACHE_ROOT):
        for entry in os.listdir(CACHE_ROOT):
            folder_path = os.path.join(CACHE_ROOT, entry)
            if os.path.isdir(folder_path):
                try:
                    shutil.rmtree(folder_path)
                    count += 1
                except Exception as e:
                    print(f"[Garbage Collection] Error force deleting {folder_path}: {e}")
    return count
