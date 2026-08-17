from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
import logging

from utils.db import safe_execute, safe_query, is_sqlite
from api.auth import get_optional_current_user

logger = logging.getLogger("qto.community")
router = APIRouter()


class InquiryCreateReq(BaseModel):
    email: EmailStr
    subject: str = Field(..., min_length=2, max_length=255)
    message: str = Field(..., min_length=5, max_length=5000)
    name: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field("general", max_length=50)


class ReviewCreateReq(BaseModel):
    user_name: str = Field(..., min_length=2, max_length=255)
    user_role: Optional[str] = Field(None, max_length=255)
    company: Optional[str] = Field(None, max_length=255)
    rating: int = Field(..., ge=1, le=5)
    review_title: Optional[str] = Field(None, max_length=255)
    review_text: str = Field(..., min_length=10, max_length=4000)


@router.post("/inquiries")
async def submit_inquiry(
    req: InquiryCreateReq,
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """Public endpoint for any visitor or user to submit an inquiry / support message."""
    user_id = current_user.get("id") if current_user else None
    
    # Sanitize category
    category = req.category or "general"
    if category not in ["general", "pricing", "technical", "feature_request"]:
        category = "general"

    sql = """
        INSERT INTO qto_inquiries (user_id, name, email, subject, message, category, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'new')
    """
    
    success, err = safe_execute(sql, (
        user_id,
        (req.name or "").strip() or None,
        req.email.strip(),
        req.subject.strip(),
        req.message.strip(),
        category
    ))

    if not success:
        logger.error(f"Failed to save inquiry: {err}")
        raise HTTPException(status_code=500, detail="Failed to submit inquiry. Please try again.")

    return {
        "success": True,
        "message": "Inquiry received successfully. Our engineering support team will respond shortly."
    }


@router.post("/reviews")
async def submit_review(
    req: ReviewCreateReq,
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """
    Submit a user review/testimonial.
    CRITICAL: Reviews are always saved with is_approved = 0 (Pending Admin Approval).
    They will NOT be displayed publicly until approved by an administrator.
    """
    user_id = current_user.get("id") if current_user else None
    
    sql = """
        INSERT INTO qto_reviews (
            user_id, user_name, user_role, company, rating, review_title, review_text, is_approved, is_featured
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 0)
    """

    success, err = safe_execute(sql, (
        user_id,
        req.user_name.strip(),
        (req.user_role or "").strip() or None,
        (req.company or "").strip() or None,
        req.rating,
        (req.review_title or "").strip() or None,
        req.review_text.strip()
    ))

    if not success:
        logger.error(f"Failed to submit review: {err}")
        raise HTTPException(status_code=500, detail="Failed to submit review. Please try again.")

    return {
        "success": True,
        "is_approved": False,
        "message": "Thank you for your feedback! Your review has been submitted and will appear publicly once approved by our team."
    }


@router.get("/reviews/public")
async def get_public_reviews(featured_only: bool = False):
    """
    Fetch approved reviews for public display (Landing Page, Community Wall).
    Filters ONLY `is_approved = 1`.
    """
    # Ensure mockup reviews exist if database is fresh
    try:
        from utils.db import seed_mockup_reviews
        seed_mockup_reviews()
    except Exception as e:
        logger.debug(f"Seeder run notice: {e}")

    where_clause = "WHERE is_approved = 1"
    if featured_only:
        where_clause += " AND is_featured = 1"

    sql = f"""
        SELECT id, user_name, user_role, company, rating, review_title, review_text, is_featured, created_at
        FROM qto_reviews
        {where_clause}
        ORDER BY is_featured DESC, id DESC
        LIMIT 50
    """
    
    df = safe_query(sql)
    reviews = df.to_dict("records") if not df.empty else []

    # Calculate overall aggregate stats
    stats_df = safe_query("""
        SELECT 
            COUNT(*) as total_reviews,
            AVG(rating) as avg_rating,
            SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END) as count_5_star,
            SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END) as count_4_star,
            SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) as count_3_star,
            SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) as count_low_star
        FROM qto_reviews
        WHERE is_approved = 1
    """)

    stats = {
        "total_reviews": 0,
        "avg_rating": 5.0,
        "count_5_star": 0,
        "count_4_star": 0,
        "count_3_star": 0,
        "count_low_star": 0
    }

    if not stats_df.empty and stats_df.iloc[0]["total_reviews"]:
        row = stats_df.iloc[0]
        stats["total_reviews"] = int(row["total_reviews"] or 0)
        stats["avg_rating"] = round(float(row["avg_rating"] or 5.0), 1)
        stats["count_5_star"] = int(row["count_5_star"] or 0)
        stats["count_4_star"] = int(row["count_4_star"] or 0)
        stats["count_3_star"] = int(row["count_3_star"] or 0)
        stats["count_low_star"] = int(row["count_low_star"] or 0)

    return {
        "stats": stats,
        "reviews": reviews
    }
