"""
core/keys.py — bmqa-v2
مركزيّة بناء مفاتيح Redis الموحّدة عبر المشروع.
"""

from config import Dev_Zaid


def message_override_key(message_id: str) -> str:
    """يبني مفتاح Redis الموحّد لتخزين نص رسالة مُخصَّص (override) لمعرّف رسالة معيّن."""
    return f"msgoverride:{message_id}{Dev_Zaid}"
