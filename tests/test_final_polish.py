"""Tests for final polish fixes: free-trial QTO export, Plan Comparison DPI, and Inquiry admin email alert."""
from unittest.mock import MagicMock, patch
import inspect
import pandas as pd
import pytest
from fastapi import BackgroundTasks


def test_free_trial_user_with_owned_qto_project_can_export():
    """Free-trial (tier 0, exports=0) and expired subscribers who own a QTO project must NOT hit 403 0/0."""
    from utils.plans import PLANS
    from utils.usage import EVENT_EXPORT, check_limit, monthly_usage

    monthly_usage.clear()
    fake_user = {"id": 999001, "role": "user", "email": "trial@example.com"}

    with patch("utils.usage.get_plan_for_user", return_value=PLANS[0]), \
         patch("utils.features.extra_projects_for", return_value=0), \
         patch("utils.usage.monthly_usage", return_value=0), \
         patch("utils.usage.safe_query", return_value=pd.DataFrame([{"c": 1}])):
        ok, msg = check_limit(fake_user, EVENT_EXPORT, feature="qto")
        assert ok is True, f"Expected free-trial user with 1 saved QTO project to export, got: {msg}"

    # Verify someone with 0 projects and tier 0 is still blocked (limit 0)
    with patch("utils.usage.get_plan_for_user", return_value=PLANS[0]), \
         patch("utils.features.extra_projects_for", return_value=0), \
         patch("utils.usage.monthly_usage", return_value=0), \
         patch("utils.usage.safe_query", return_value=pd.DataFrame([{"c": 0}])):
        ok_none, msg_none = check_limit(fake_user, EVENT_EXPORT, feature="qto")
        assert ok_none is False
        assert "0/0" in msg_none


def test_compare_plans_passes_clamped_dpi():
    """compare_plans accepts dpi parameter and forwards safe clamped DPI to render_pdf_page."""
    from utils.plan_comparer import compare_plans
    import numpy as np

    sig = inspect.signature(compare_plans)
    assert "dpi" in sig.parameters

    dummy_img = np.full((100, 100, 3), 255, dtype=np.uint8)
    with patch("utils.plan_comparer.render_pdf_page", return_value=dummy_img) as mock_render:
        assert compare_plans("a.pdf", "b.pdf", page_num=0, output_path=None, dpi=120) is True
        assert mock_render.call_count == 2
        for call in mock_render.call_args_list:
            assert call.kwargs.get("dpi") == 120

    # Extreme DPI should be safely clamped to 220 max (protects Render 512MB RAM)
    with patch("utils.plan_comparer.render_pdf_page", return_value=dummy_img) as mock_render:
        assert compare_plans("a.pdf", "b.pdf", page_num=0, output_path=None, dpi=1200) is True
        for call in mock_render.call_args_list:
            assert call.kwargs.get("dpi") == 220


@pytest.mark.anyio
async def test_submit_inquiry_queues_admin_email():
    """POST /api/community/inquiries schedules an instant admin email notification."""
    from api.routers.community import InquiryCreateReq, submit_inquiry

    bg = BackgroundTasks()
    req = InquiryCreateReq(
        name="Eng. Khalid",
        email="khalid@contractor.ae",
        subject="Enterprise Team Inquiry",
        message="We have 15 villas per month in Dubai.",
        category="pricing",
    )

    with patch("api.routers.community.safe_execute", return_value=(True, None)), \
         patch("utils.mailer.send_admin_email", return_value=True) as mock_mail:
        res = await submit_inquiry(req, bg, current_user=None)
        assert res["success"] is True
        assert len(bg.tasks) == 1
        # Run queued background task to verify send_admin_email is invoked cleanly
        for task in bg.tasks:
            await task()
        mock_mail.assert_called_once()
        subj_arg, html_arg = mock_mail.call_args[0]
        assert "Enterprise Team Inquiry" in subj_arg
        assert "khalid@contractor.ae" in html_arg
