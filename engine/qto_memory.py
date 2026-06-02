"""
THE QS HUB - AI Memory Loop
Handles user-specific and global AI classification rules.
"""
from utils.db import safe_query, safe_execute

def record_mapping(user_id: int, original_text: str, mapped_category: str) -> bool:
    """
    Records a mapping rule.
    Creates a 'personal' rule for the user, and a 'pending' rule for the Admin to review.
    """
    original_text = original_text.strip().lower()
    mapped_category = mapped_category.strip()
    
    # Check if a global rule already exists
    global_df = safe_query(
        "SELECT id FROM qto_memory_rules WHERE status='global' AND original_text=%s",
        (original_text,)
    )
    if not global_df.empty:
        return True # Already globally mapped

    # Check if this user already mapped it
    personal_df = safe_query(
        "SELECT id FROM qto_memory_rules WHERE user_id=%s AND status='personal' AND original_text=%s",
        (user_id, original_text)
    )
    if personal_df.empty:
        # Create personal rule
        safe_execute(
            "INSERT INTO qto_memory_rules (user_id, original_text, mapped_category, status) VALUES (%s, %s, %s, 'personal')",
            (user_id, original_text, mapped_category)
        )
    else:
        # Update personal rule
        safe_execute(
            "UPDATE qto_memory_rules SET mapped_category=%s WHERE user_id=%s AND status='personal' AND original_text=%s",
            (mapped_category, user_id, original_text)
        )

    # Queue a pending rule for Admin (if one doesn't already exist for this exact mapping)
    pending_df = safe_query(
        "SELECT id FROM qto_memory_rules WHERE status='pending' AND original_text=%s AND mapped_category=%s",
        (original_text, mapped_category)
    )
    if pending_df.empty:
        safe_execute(
            "INSERT INTO qto_memory_rules (user_id, original_text, mapped_category, status) VALUES (%s, %s, %s, 'pending')",
            (user_id, original_text, mapped_category)
        )
    return True


def get_active_rules(user_id: int = None) -> dict:
    """
    Returns a dictionary of active rules.
    Global rules apply to everyone.
    Personal rules override global rules for this specific user.
    """
    rules = {}
    
    # 1. Load global rules
    global_df = safe_query("SELECT original_text, mapped_category FROM qto_memory_rules WHERE status='global'")
    for _, row in global_df.iterrows():
        rules[row['original_text']] = row['mapped_category']

    # 2. Load personal rules (Overrides global if they conflict)
    if user_id:
        personal_df = safe_query(
            "SELECT original_text, mapped_category FROM qto_memory_rules WHERE user_id=%s AND status='personal'",
            (user_id,)
        )
        for _, row in personal_df.iterrows():
            rules[row['original_text']] = row['mapped_category']

    return rules


def format_rules_for_prompt(user_id: int) -> str:
    """
    Formats the active rules into a string block to be injected into the AI Prompt.
    """
    rules = get_active_rules(user_id)
    if not rules:
        return ""
        
    prompt_lines = ["\nCRITICAL USER MAPPING RULES:"]
    prompt_lines.append("You MUST apply these specific mappings if you encounter the exact original text (case-insensitive):")
    for original, mapped in rules.items():
        prompt_lines.append(f"- If you see '{original}', classify it as '{mapped}'")
    
    return "\n".join(prompt_lines) + "\n"
