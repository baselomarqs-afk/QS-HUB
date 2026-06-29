from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from utils.db import safe_execute, is_sqlite
from api.auth import get_current_user

router = APIRouter()

class FeedbackReq(BaseModel):
    tool_name: str
    project_name: str
    rating: int
    reason: Optional[str] = None

@router.post("")
@router.post("/")
async def submit_feedback(req: FeedbackReq, current_user: dict = Depends(get_current_user)):
    try:
        sql = """
            INSERT INTO qto_project_feedback (user_id, tool_name, project_name, rating, reason)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        success, error = safe_execute(sql, (current_user["id"], req.tool_name, req.project_name, req.rating, req.reason))
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {error}")
            
        return {"status": "success", "message": "Feedback submitted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
