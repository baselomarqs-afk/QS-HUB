"""
حالة الـ workflow الكاملة — خطوة بخطوة
"""
import os

STEPS = {
    1: {"key": "upload",    "label": "Upload Drawings",     "label_ar": "رفع المخططات",          "icon": ""},
    2: {"key": "classify",  "label": "Classify Pages",      "label_ar": "تصنيف الصفحات",          "icon": "️"},
    3: {"key": "extract",   "label": "Extract Data",        "label_ar": "استخراج البيانات",        "icon": ""},
    4: {"key": "confirm",   "label": "Confirm Missing",     "label_ar": "تأكيد البيانات الناقصة", "icon": ""},
    5: {"key": "calculate", "label": "Apply Formulas",      "label_ar": "تطبيق المعادلات",         "icon": ""},
    6: {"key": "review",    "label": "Review Results",      "label_ar": "مراجعة النتائج",          "icon": "️"},
    7: {"key": "arrange",   "label": "Arrange BOQ",         "label_ar": "ترتيب الـ BOQ",           "icon": ""},
    8: {"key": "download",  "label": "Download Excel",      "label_ar": "تحميل Excel",             "icon": ""},
}


def get_current_step(state: dict) -> int:
    return state.get("current_step", 1)


def set_step(state: dict, step: int):
    state["current_step"] = step


def step_done(state: dict, step_key: str) -> bool:
    return state.get(f"step_done_{step_key}", False)


def mark_step_done(state: dict, step_key: str):
    state[f"step_done_{step_key}"] = True


def can_proceed_to(state: dict, step: int) -> bool:
    """كل خطوة محتاجة الخطوة اللي قبلها تكون خلصت"""
    if step == 1:
        return True
    prev_key = STEPS[step - 1]["key"]
    return step_done(state, prev_key)


def reset_pipeline(state: dict, user_id: int = None):
    """Wipe all extracted data and classifications when a new file is uploaded."""

    # 1. Clear state dict cache
    keys_to_delete = [
        "classified_pages", "extraction_results", "confirmed_auto_data",
        "current_step", 
    ]
    # Also delete all step_done markers
    for k in list(state.keys()):
        if k in keys_to_delete or k.startswith("step_done_") or k.startswith("auto_") or k.startswith("manual_") or k.startswith("ci_") or k.startswith("fin_") or k.startswith("super_") or k.startswith("sub_") or k.startswith("conf_") or k.startswith("open_"):
            del state[k]
            
    # Clear DB state
    if user_id:
        from utils.state_recovery import clear_project_state
        clear_project_state(user_id)
            
    # 2. Delete local json files
    if os.path.exists("_arch_data.json"):
        try: os.remove("_arch_data.json")
        except: pass
    if os.path.exists("_schedule_data.json"):
        try: os.remove("_schedule_data.json")
        except: pass
    if os.path.exists("_classified_pages.json"):
        try: os.remove("_classified_pages.json")
        except: pass
