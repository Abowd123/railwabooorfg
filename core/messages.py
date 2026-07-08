"""
core/messages.py — bmqa-v2
طبقة موحّدة لإدارة نصوص ردود البوت مع دعم التخصيص (override) عبر Redis.

الفكرة:
  - كل رسالة لها معرّف ثابت (message_id) ونص افتراضي في DEFAULT_MESSAGES.
  - يمكن لأي مشرف/مطوّر استبدال النص الافتراضي بنص مخصّص يُحفظ في Redis،
    شرط أن يستخدم النص المخصّص نفس أسماء الـ placeholders الأصلية فقط (أو جزءاً منها).
  - get_message تقرأ الـ override إن وُجد وإلا ترجع للنص الافتراضي، ثم تُنسّقه.

هذا الملف يمثّل فقط الطبقة البرمجية الأساسية (core layer) — بلا أي أوامر
Telegram أو Plugins مرتبطة به في هذه المرحلة.
"""

from __future__ import annotations

import string

from core.db import rdb
from core.keys import message_override_key

# ══════════════════════════════════════════════════════════════════════════════
# DEFAULT_MESSAGES — 3 ردود فقط كبداية تجريبية
# مأخوذة حرفياً من قالبَي lock وOpen في Plugins/all_locks_1.py، مع تحويل
# الـ placeholders الرقمية {} إلى أسماء واضحة:
#   {botkey}  → مفتاح/توقيع البوت (كان يُمرَّر مرتين: في الأعلى وقبل الفعل)
#   {mention} → منشن العضو الذي نفّذ الأمر
#   {feature} → اسم الميزة المقفولة/المفتوحة ("الشات"، "التعديل"، ...)
# ══════════════════════════════════════════════════════════════════════════════

DEFAULT_MESSAGES: dict[str, str] = {
    # من قالب lock — يُستخدم عند تنفيذ أمر "قفل الشات"
    "lock_chat": """
{botkey} من 「 {mention} 」
{botkey} ابشر قفلت {feature}
☆
""",
    # من قالب Open — يُستخدم عند تنفيذ أمر "فتح الشات"
    "unlock_chat": """
{botkey} من 「 {mention} 」
{botkey} ابشر فتحت {feature}
☆
""",
    # قالب lock العام — نفس المحتوى حرفياً — مربوط فعلياً في _lock_toggle()
    # ضمن Plugins/all_locks_1.py (مستخدَم لكل أزواج القفل/الفتح، وليس فقط
    # "الشات"؛ اسم "feature" هو المتغيّر الذي يحدد نوع القفل المعروض).
    "locks.chat_locked": """
{botkey} من 「 {mention} 」
{botkey} ابشر قفلت {feature}
☆
""",
    # قالب Open العام — نفس المحتوى حرفياً — مربوط فعلياً في _lock_toggle()
    # ضمن Plugins/all_locks_1.py.
    "locks.chat_opened": """
{botkey} من 「 {mention} 」
{botkey} ابشر فتحت {feature}
☆
""",
    # من قالب lock أيضاً — لكن لمعرّف مستقل (أمر "قفل التعديل")
    # حتى يمكن تخصيص نص كل أمر لاحقاً بشكل مستقل رغم تطابق القالب الافتراضي.
    "lock_edit": """
{botkey} من 「 {mention} 」
{botkey} ابشر قفلت {feature}
☆
""",
}


def _placeholders(template: str) -> set[str]:
    """يستخرج أسماء الـ placeholders الموجودة داخل نص .format() معيّن."""
    formatter = string.Formatter()
    return {
        field_name
        for _, field_name, _, _ in formatter.parse(template)
        if field_name
    }


async def get_message(message_id: str, **kwargs) -> str:
    """
    يرجع نص الرسالة الجاهز للاستخدام:
      1. يقرأ override من Redis إن وُجد.
      2. وإلا يستخدم DEFAULT_MESSAGES.
      3. ينسّق النص بالـ kwargs المُمرَّرة.
    """
    if message_id not in DEFAULT_MESSAGES:
        raise ValueError(f"message_id غير معروف: {message_id!r}")

    override = await rdb.get(message_override_key(message_id))
    template = override if override else DEFAULT_MESSAGES[message_id]
    return template.format(**kwargs)


async def set_message_override(message_id: str, new_text: str) -> None:
    """
    يحفظ نصاً مخصّصاً (override) لمعرّف رسالة معيّن في Redis، بعد التحقق أن
    كل الـ placeholders الموجودة في new_text معروفة ضمن القالب الأصلي لنفس
    المعرّف. يرفع ValueError إن وُجد placeholder غير معروف.
    """
    if message_id not in DEFAULT_MESSAGES:
        raise ValueError(f"message_id غير معروف: {message_id!r}")

    original_placeholders = _placeholders(DEFAULT_MESSAGES[message_id])
    new_placeholders = _placeholders(new_text)

    unknown = new_placeholders - original_placeholders
    if unknown:
        raise ValueError(
            f"placeholders غير معروفة لمعرّف {message_id!r}: {sorted(unknown)} "
            f"— المسموح به فقط: {sorted(original_placeholders)}"
        )

    await rdb.set(message_override_key(message_id), new_text)


async def reset_message(message_id: str) -> None:
    """يحذف الـ override الخاص بمعرّف رسالة معيّن من Redis، فيعود للنص الافتراضي."""
    if message_id not in DEFAULT_MESSAGES:
        raise ValueError(f"message_id غير معروف: {message_id!r}")

    await rdb.delete(message_override_key(message_id))


def list_message_ids() -> list[str]:
    """يرجع كل معرّفات الرسائل المتاحة (مفاتيح DEFAULT_MESSAGES)."""
    return list(DEFAULT_MESSAGES.keys())
