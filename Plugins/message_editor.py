"""
Plugins/message_editor.py — bmqa-v2
أدوات المطوّرين لاستعراض وتعديل ردود البوت المُدارة عبر core/messages.py.

الأوامر (للمطوّرين فقط — dev_pls أو devp_pls):
  1. قائمة_الردود        → يعرض كل معرّفات الرسائل (list_message_ids) بصفحات
                            Inline (10 معرّفات/صفحة)، مجمّعة حسب البادئة قبل
                            النقطة في المعرّف (مثال: locks., moderation.,...).
  2. عرض_رد <المعرّف>    → يعرض النص الحالي (مخصّص عبر Redis إن وُجد وإلا
                            الافتراضي من DEFAULT_MESSAGES) لمعرّف رسالة معيّن،
                            بعد تعبئته ببيانات وهمية لأغراض المعاينة فقط
                            (مثال: mention="أحمد").
  3. تعديل_رد <المعرّف>  → يبدأ تدفق تعديل تفاعلي: يعرض النص الحالي بصيغة
                            [اسم_القيمة] + أزرار Inline (زر لكل placeholder
                            متاح لهذا المعرّف تحديداً)، ويحفظ حالة "بانتظار
                            تعديل" مرتبطة بـ (user_id, chat_id) في Redis بمهلة
                            TTL = 5 دقائق بالضبط. الرسالة النصية التالية من نفس
                            المستخدم في نفس المحادثة تُعتبر النص الجديد.
  4. إلغاء                → يحذف حالة "بانتظار تعديل" الحالية لنفس المستخدم
                            (يُعالَج ضمن بوابة الرسائل أدناه، فقط إن كانت هناك
                            حالة نشطة).
  5. استرجاع_رد <المعرّف> → يعرض زر تأكيد Inline "نعم/لا" قبل استدعاء
                            reset_message() فعلياً. لا يُحذف أي شيء إلا بعد
                            ضغط "نعم" من نفس المستخدم الذي أرسل الأمر.
  6. تصدير_الردود        → يجمع كل مفاتيح msgoverride:*{Dev_Zaid} الموجودة
                            فعلياً في Redis (وليس كل DEFAULT_MESSAGES، فقط ما
                            تم تخصيصه فعلاً)، ويرسلها كملف JSON واحد
                            {معرّف: النص} إلى نفس المحادثة.
  7. استيراد_الردود      → يُرسَل كرد على ملف JSON مُصدَّر سابقاً عبر
                            تصدير_الردود. لكل معرّف داخل الملف: يتحقق أنه
                            موجود ضمن DEFAULT_MESSAGES وأن كل الـ placeholders
                            المستخدَمة بنص الاستيراد معروفة ضمن القالب الأصلي
                            لنفس المعرّف. تُجمَّع كل الأخطاء أولاً وتُرسَل دفعة
                            واحدة دون حفظ أي شيء إن وُجد ولو خطأ واحد (لا حفظ
                            جزئي أبداً) — الحفظ الفعلي عبر set_message_override
                            يتم فقط لو نجحت كل المعرّفات في الملف بالتحقق.

بوابة الرسائل النصية العادية (group=17 — قبل أي dispatcher رئيسي بمجموعة 21+):
  تتحقق من وجود حالة "بانتظار تعديل" لنفس (user_id, chat_id):
    - لا يوجد  → raise ContinuePropagation فوراً (لا تلمس الرسالة إطلاقاً).
    - يوجد    → تحلّل [اسم_القيمة] من النص، تقارنها بالأسماء العربية المسموحة
                لمعرّف الرسالة المطلوب تعديله تحديداً، ثم:
                  * اسم غير معروف → رد بالخطأ + القائمة الصحيحة، والحالة تبقى
                    (يُسمح بإعادة المحاولة فوراً).
                  * كل الأسماء صحيحة → تحويلها لـ {internal_placeholder}
                    المطابقة، حفظ عبر set_message_override()، حذف الحالة،
                    ثم إرسال معاينة فعلية بالنص الجديد ببيانات وهمية.

تسجيل الأوامر عبر core/dispatcher.py (@register) والـ callback عبر
core/callback_dispatcher.py (@register_callback)، بنفس نمط بقية الملفات.
"""

from __future__ import annotations

import json
import os
import re
import string
from datetime import datetime

from pyrogram import Client, ContinuePropagation, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from core.callback_dispatcher import register_callback
from core.keys import message_override_key
from helpers.ranks import dev_pls, devp_pls
from core.messages import (
    DEFAULT_MESSAGES,
    list_message_ids,
    get_message,
    set_message_override,
    reset_message,
)

# ══════════════════════════════════════════════════════════════════════════════
# إعدادات عامة
# ══════════════════════════════════════════════════════════════════════════════

_PAGE_SIZE = 10
_CB_PREFIX = "msgeditor_list:"  # msgeditor_list:{page}:{uid}
_DEV_PERM = "هذا الامر يخص ( المطور وفوق ) وبس"

# بيانات وهمية لتعبئة الـ placeholders أثناء المعاينة فقط — لا تُحفظ ولا تُستخدم
# في أي منطق فعلي، فقط لإظهار شكل الرسالة كما ستظهر للمستخدم.
_DUMMY_PLACEHOLDERS = {
    "botkey": "🧚‍♀️",
    "mention": "أحمد",
    "feature": "الميزة التجريبية",
}

# خريطة الاسم الداخلي (internal placeholder) ← الاسم العربي الذي يكتبه المطوّر
# بين قوسين [مثل_هذا] أثناء التعديل. أي placeholder جديد يُضاف لاحقاً في
# core/messages.py يجب أن يُضاف اسمه هنا أيضاً حتى يصبح قابلاً للاستخدام في
# تدفق التعديل التفاعلي.
PLACEHOLDER_LABELS: dict[str, str] = {
    "botkey": "اسم_البوت",
    "mention": "الشخص",
    "feature": "الميزة",
}

_BRACKET_RE = re.compile(r"\[([^\[\]]+)\]")

# ══════════════════════════════════════════════════════════════════════════════
# حالة "بانتظار تعديل" — Redis بمهلة TTL = 5 دقائق بالضبط
# ══════════════════════════════════════════════════════════════════════════════

_PENDING_TTL = 300  # 5 دقائق بالضبط


def _pending_key(uid: int, cid: int) -> str:
    """مفتاح Redis لحالة التعديل المُعلَّقة الخاصة بـ (user_id, chat_id)."""
    return f"msgedit_pending:{uid}:{cid}{Dev_Zaid}"


async def _set_pending(uid: int, cid: int, message_id: str) -> None:
    """يحفظ أن (uid, cid) بانتظار تعديل message_id، لمدة 5 دقائق بالضبط."""
    await rdb.set(_pending_key(uid, cid), message_id, ex=_PENDING_TTL)


async def _get_pending(uid: int, cid: int) -> str | None:
    """يرجع معرّف الرسالة قيد التعديل حالياً لـ (uid, cid)، أو None."""
    return await rdb.get(_pending_key(uid, cid))


async def _clear_pending(uid: int, cid: int) -> None:
    """يحذف حالة التعديل المُعلَّقة لـ (uid, cid) دون حفظ أي شيء."""
    await rdb.delete(_pending_key(uid, cid))


async def _is_dev(uid: int, cid: int) -> bool:
    """يتحقق أن المستخدم مطوّر عبر dev_pls أو devp_pls (أيّهما صحّ)."""
    if await dev_pls(uid, cid):
        return True
    return await devp_pls(uid, cid)


def _group_of(message_id: str) -> str:
    """البادئة قبل أول نقطة في المعرّف، أو 'عام' لو لا توجد نقطة."""
    return message_id.split(".", 1)[0] if "." in message_id else "عام"


def _grouped_ids() -> list[str]:
    """كل المعرّفات مرتّبة: مجمّعة حسب البادئة، ثم أبجدياً داخل كل مجموعة."""
    return sorted(list_message_ids(), key=lambda mid: (_group_of(mid), mid))


def _render_page(page: int) -> tuple[str, int]:
    """يبني نص صفحة مُعيّنة من القائمة المُجمَّعة، ويرجع (النص، عدد الصفحات)."""
    ids = _grouped_ids()
    total_pages = max(1, -(-len(ids) // _PAGE_SIZE))  # سقف القسمة
    page = max(1, min(page, total_pages))

    start = (page - 1) * _PAGE_SIZE
    chunk = ids[start:start + _PAGE_SIZE]

    lines = [f"📋 قائمة الردود — صفحة {page}/{total_pages}"]
    current_group = None
    for mid in chunk:
        group = _group_of(mid)
        if group != current_group:
            lines.append(f"\n▪️ {group}")
            current_group = group
        lines.append(f"  ├ {mid}")

    lines.append("\n\nللمعاينة: عرض_رد <المعرّف>")
    return "\n".join(lines), total_pages


def _list_keyboard(page: int, total_pages: int, uid: int) -> InlineKeyboardMarkup | None:
    row = []
    if page > 1:
        row.append(InlineKeyboardButton("◀️ السابق", callback_data=f"{_CB_PREFIX}{page - 1}:{uid}"))
    if page < total_pages:
        row.append(InlineKeyboardButton("التالي ▶️", callback_data=f"{_CB_PREFIX}{page + 1}:{uid}"))
    return InlineKeyboardMarkup([row]) if row else None


# ══════════════════════════════════════════════════════════════════════════════
# أدوات مساعدة لتدفق التعديل التفاعلي (placeholders ↔ [أسماء عربية])
# ══════════════════════════════════════════════════════════════════════════════

def _original_placeholders(message_id: str) -> set[str]:
    """الـ placeholders الموجودة فعلياً ضمن القالب الافتراضي لهذا المعرّف."""
    formatter = string.Formatter()
    return {
        field_name
        for _, field_name, _, _ in formatter.parse(DEFAULT_MESSAGES[message_id])
        if field_name
    }


def _labels_for(message_id: str) -> dict[str, str]:
    """
    يرجع {الاسم_العربي: internal_placeholder} مقصورة فقط على الـ placeholders
    الموجودة فعلياً في قالب هذا المعرّف تحديداً (وليس كل الأسماء الممكنة).
    """
    used = _original_placeholders(message_id)
    return {
        arabic: internal
        for internal, arabic in PLACEHOLDER_LABELS.items()
        if internal in used
    }


def _to_display(template: str) -> str:
    """يحوّل {internal_placeholder} داخل القالب إلى [الاسم_العربي] لعرضها للمطوّر."""
    result = template
    for internal, arabic in PLACEHOLDER_LABELS.items():
        result = result.replace("{" + internal + "}", f"[{arabic}]")
    return result


def _translate_and_validate(message_id: str, text: str) -> tuple[str | None, list[str]]:
    """
    يستخرج كل [اسم_قيمة] من النص، ويقارنها بالأسماء العربية المسموحة لهذا
    المعرّف تحديداً (_labels_for). لو كل الأسماء معروفة، يحوّلها لصيغة
    {internal_placeholder} المطابقة ويرجع (النص المحوَّل، []).
    لو وُجد اسم غير معروف، يرجع (None، قائمة الأسماء الخاطئة) دون أي تحويل.
    """
    allowed = _labels_for(message_id)  # {عربي: internal}
    found = list(dict.fromkeys(_BRACKET_RE.findall(text)))  # بترتيب الظهور، بلا تكرار

    unknown = [name for name in found if name not in allowed]
    if unknown:
        return None, unknown

    def _sub(match: re.Match) -> str:
        return "{" + allowed[match.group(1)] + "}"

    return _BRACKET_RE.sub(_sub, text), []


# ══════════════════════════════════════════════════════════════════════════════
# 1) قائمة_الردود
# ══════════════════════════════════════════════════════════════════════════════

@register("قائمة_الردود")
@Client.on_message(filters.text & filters.regex(r"^قائمة_الردود$"), group=1500)
@safe_handler
async def listMessagesHandler(c: Client, m) -> None:
    if not await _is_dev(m.from_user.id, m.chat.id):
        k = await rdb.get(f"{Dev_Zaid}:botkey") or "🧚‍♀️"
        return await m.reply(quote=True, text=f"{k} {_DEV_PERM}")

    text, total_pages = _render_page(1)
    await m.reply(
        quote=True,
        text=text,
        reply_markup=_list_keyboard(1, total_pages, m.from_user.id),
    )


@register_callback(_CB_PREFIX)
@safe_handler
async def listMessagesCallback(c: Client, m) -> None:
    # m.data بالصيغة: msgeditor_list:{page}:{uid}
    parts = m.data.split(":")
    if len(parts) != 3:
        return await m.answer()

    _, page_str, uid_str = parts
    try:
        page = int(page_str)
        uid = int(uid_str)
    except ValueError:
        return await m.answer()

    if m.from_user.id != uid:
        return await m.answer("هذه القائمة ليست لك", show_alert=True)

    if not await _is_dev(m.from_user.id, m.message.chat.id):
        return await m.answer(_DEV_PERM, show_alert=True)

    text, total_pages = _render_page(page)
    await m.edit_message_text(text, reply_markup=_list_keyboard(page, total_pages, uid))
    await m.answer()


# ══════════════════════════════════════════════════════════════════════════════
# 2) عرض_رد <المعرّف>
# ══════════════════════════════════════════════════════════════════════════════

@register("عرض_رد ")
@register("عرض_رد")
@Client.on_message(filters.text & filters.regex(r"^عرض_رد(\s|$)"), group=1500)
@safe_handler
async def viewMessageHandler(c: Client, m) -> None:
    if not await _is_dev(m.from_user.id, m.chat.id):
        k = await rdb.get(f"{Dev_Zaid}:botkey") or "🧚‍♀️"
        return await m.reply(quote=True, text=f"{k} {_DEV_PERM}")

    parts = m.text.split(None, 1)
    message_id = parts[1].strip() if len(parts) > 1 else None

    if not message_id:
        return await m.reply(
            quote=True,
            text=(
                "اكتب: عرض_رد <المعرّف>\n"
                "مثال: عرض_رد lock_chat\n\n"
                "لعرض كل المعرّفات المتاحة استخدم: قائمة_الردود"
            ),
        )

    if message_id not in list_message_ids():
        return await m.reply(
            quote=True,
            text=f"لا يوجد معرّف رسالة باسم: {message_id}\n\nاستخدم: قائمة_الردود لعرض كل المعرّفات المتاحة",
        )

    rendered = await get_message(message_id, **_DUMMY_PLACEHOLDERS)
    await m.reply(
        quote=True,
        text=(
            f"📄 معاينة الرد: {message_id}\n"
            f'(ببيانات وهمية للمعاينة: mention="أحمد")\n'
            f"────────────────\n"
            f"{rendered}"
        ),
    )


# ══════════════════════════════════════════════════════════════════════════════
# 3) تعديل_رد <المعرّف> — بدء تدفق التعديل التفاعلي
# ══════════════════════════════════════════════════════════════════════════════

_CB_PH_PREFIX = "msgeditor_ph:"  # msgeditor_ph:{internal_placeholder}:{uid}


@register("تعديل_رد ")
@Client.on_message(filters.text & filters.regex(r"^تعديل_رد(\s|$)"), group=1500)
@safe_handler
async def editMessageHandler(c: Client, m) -> None:
    if not await _is_dev(m.from_user.id, m.chat.id):
        k = await rdb.get(f"{Dev_Zaid}:botkey") or "🧚‍♀️"
        return await m.reply(quote=True, text=f"{k} {_DEV_PERM}")

    parts = m.text.split(None, 1)
    message_id = parts[1].strip() if len(parts) > 1 else None

    if not message_id:
        return await m.reply(
            quote=True,
            text="اكتب: تعديل_رد <المعرّف>\n\nلعرض المعرّفات المتاحة استخدم: قائمة_الردود",
        )

    if message_id not in DEFAULT_MESSAGES:
        return await m.reply(
            quote=True,
            text=f"لا يوجد معرّف رسالة باسم: {message_id}\n\nاستخدم: قائمة_الردود لعرض كل المعرّفات المتاحة",
        )

    current_raw = await rdb.get(message_override_key(message_id)) or DEFAULT_MESSAGES[message_id]
    labels = _labels_for(message_id)  # {عربي: internal}

    allowed_list = "\n".join(f"• [{arabic}]" for arabic in labels) or "— (لا توجد قيم متغيّرة لهذا الرد)"
    buttons = [
        [InlineKeyboardButton(f"[{arabic}]", callback_data=f"{_CB_PH_PREFIX}{internal}:{m.from_user.id}")]
        for arabic, internal in labels.items()
    ]
    kb = InlineKeyboardMarkup(buttons) if buttons else None

    await _set_pending(m.from_user.id, m.chat.id, message_id)

    await m.reply(
        quote=True,
        text=(
            f"✏️ تعديل الرد: {message_id}\n\n"
            f"النص الحالي:\n{_to_display(current_raw)}\n\n"
            f"الأسماء المتاحة لهذا الرد:\n{allowed_list}\n\n"
            "أرسل الآن النص الجديد بنفس الصيغة (استبدل القيم بـ [الاسم] كما بالأعلى)، "
            "خلال 5 دقائق.\n"
            "لإلغاء التعديل أرسل: إلغاء"
        ),
        reply_markup=kb,
    )


@register_callback(_CB_PH_PREFIX)
@safe_handler
async def placeholderHintCallback(c: Client, m) -> None:
    """يرد بتلميح صغير (toast) عن صيغة القيمة الصحيحة، دون تعديل أي رسالة."""
    parts = m.data.split(":")
    if len(parts) != 3:
        return await m.answer()

    _, internal, uid_str = parts
    try:
        uid = int(uid_str)
    except ValueError:
        return await m.answer()

    if m.from_user.id != uid:
        return await m.answer("هذا الزر ليس لك", show_alert=True)

    arabic = PLACEHOLDER_LABELS.get(internal, internal)
    await m.answer(f"استخدم [{arabic}] بنصك", show_alert=False)


# ══════════════════════════════════════════════════════════════════════════════
# بوابة الرسائل النصية العادية — تعالج (إلغاء) والنص الجديد أثناء تعديل مُعلَّق.
# group=17: يجب أن تعمل قبل أي dispatcher رئيسي (مجموعات 21+ في المشروع).
# لو لا توجد حالة "بانتظار تعديل" لنفس (user_id, chat_id) → تمرّ فوراً دون
# لمس الرسالة عبر ContinuePropagation، حتى تصل لبقية المعالجات كالمعتاد.
# ══════════════════════════════════════════════════════════════════════════════

@register("message_editor_pending_gate")
@Client.on_message(filters.text, group=17)
@safe_handler
async def pendingEditGateHandler(c: Client, m) -> None:
    uid = m.from_user.id
    cid = m.chat.id

    pending_id = await _get_pending(uid, cid)
    if not pending_id:
        raise ContinuePropagation

    # ── إلغاء ──────────────────────────────────────────────────────────
    if m.text.strip() == "إلغاء":
        await _clear_pending(uid, cid)
        return await m.reply(quote=True, text="✅ تم إلغاء التعديل.")

    # ── تحليل [اسم_القيمة] وتحويلها لِ {internal_placeholder} ──────────
    converted, unknown = _translate_and_validate(pending_id, m.text)

    if unknown:
        allowed_list = "\n".join(f"• [{a}]" for a in _labels_for(pending_id)) or "— (لا توجد قيم متغيّرة لهذا الرد)"
        wrong = "، ".join(f"[{u}]" for u in unknown)
        # لا تُحذف الحالة — يُسمح بإعادة المحاولة فوراً.
        return await m.reply(
            quote=True,
            text=(
                f"❌ اسم غير معروف: {wrong}\n\n"
                f"الأسماء المسموحة لهذا الرد ({pending_id}):\n{allowed_list}\n\n"
                "أعد المحاولة، أو أرسل: إلغاء"
            ),
        )

    try:
        await set_message_override(pending_id, converted)
    except ValueError as e:
        # حالة احترازية إضافية (لن تحدث عادة بعد التحقق أعلاه) — لا تُحذف الحالة.
        return await m.reply(quote=True, text=f"❌ {e}\n\nأعد المحاولة، أو أرسل: إلغاء")

    await _clear_pending(uid, cid)

    rendered = await get_message(pending_id, **_DUMMY_PLACEHOLDERS)
    await m.reply(
        quote=True,
        text=(
            f"✅ تم حفظ الرد الجديد: {pending_id}\n\n"
            f"📄 معاينة (ببيانات وهمية: mention=\"أحمد\"):\n"
            f"────────────────\n"
            f"{rendered}"
        ),
    )


# ══════════════════════════════════════════════════════════════════════════════
# 5) استرجاع_رد <المعرّف> — تأكيد Inline "نعم/لا" قبل reset_message() الفعلي
# ══════════════════════════════════════════════════════════════════════════════

_CB_RESET_PREFIX = "msgeditor_reset:"  # msgeditor_reset:{yes|no}:{message_id}:{uid}


@register("استرجاع_رد ")
@Client.on_message(filters.text & filters.regex(r"^استرجاع_رد(\s|$)"), group=1500)
@safe_handler
async def resetMessageHandler(c: Client, m) -> None:
    if not await _is_dev(m.from_user.id, m.chat.id):
        k = await rdb.get(f"{Dev_Zaid}:botkey") or "🧚‍♀️"
        return await m.reply(quote=True, text=f"{k} {_DEV_PERM}")

    parts = m.text.split(None, 1)
    message_id = parts[1].strip() if len(parts) > 1 else None

    if not message_id:
        return await m.reply(
            quote=True,
            text="اكتب: استرجاع_رد <المعرّف>\n\nلعرض المعرّفات المتاحة استخدم: قائمة_الردود",
        )

    if message_id not in DEFAULT_MESSAGES:
        return await m.reply(
            quote=True,
            text=f"لا يوجد معرّف رسالة باسم: {message_id}\n\nاستخدم: قائمة_الردود لعرض كل المعرّفات المتاحة",
        )

    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ نعم، استرجاع",
                    callback_data=f"{_CB_RESET_PREFIX}yes:{message_id}:{m.from_user.id}",
                ),
                InlineKeyboardButton(
                    "❌ لا، إلغاء",
                    callback_data=f"{_CB_RESET_PREFIX}no:{message_id}:{m.from_user.id}",
                ),
            ]
        ]
    )

    await m.reply(
        quote=True,
        text=(
            f"⚠️ هل أنت متأكد من استرجاع الرد التالي للنص الافتراضي؟\n\n"
            f"المعرّف: {message_id}\n\n"
            "سيتم حذف أي تخصيص حالي لهذا الرد نهائياً ولا يمكن التراجع عن هذا بعد التأكيد."
        ),
        reply_markup=kb,
    )


@register_callback(_CB_RESET_PREFIX)
@safe_handler
async def resetMessageCallback(c: Client, m) -> None:
    # m.data بالصيغة: msgeditor_reset:{yes|no}:{message_id}:{uid}
    rest = m.data[len(_CB_RESET_PREFIX):]
    parts = rest.split(":", 2)
    if len(parts) != 3:
        return await m.answer()

    action, message_id, uid_str = parts
    try:
        uid = int(uid_str)
    except ValueError:
        return await m.answer()

    if m.from_user.id != uid:
        return await m.answer("هذا التأكيد ليس لك", show_alert=True)

    if not await _is_dev(m.from_user.id, m.message.chat.id):
        return await m.answer(_DEV_PERM, show_alert=True)

    if action == "no":
        await m.edit_message_text(f"❎ تم إلغاء استرجاع الرد: {message_id}")
        return await m.answer()

    if action != "yes":
        return await m.answer()

    if message_id not in DEFAULT_MESSAGES:
        await m.edit_message_text(f"لا يوجد معرّف رسالة باسم: {message_id}")
        return await m.answer()

    await reset_message(message_id)
    await m.edit_message_text(f"✅ تم استرجاع الرد للنص الافتراضي: {message_id}")
    await m.answer("تم الاسترجاع")


# ══════════════════════════════════════════════════════════════════════════════
# 6) تصدير_الردود — يصدّر فقط الردود المُخصَّصة فعلياً (موجودة في Redis)
# ══════════════════════════════════════════════════════════════════════════════

@register("تصدير_الردود")
@Client.on_message(filters.text & filters.regex(r"^تصدير_الردود$"), group=1500)
@safe_handler
async def exportMessagesHandler(c: Client, m) -> None:
    if not await _is_dev(m.from_user.id, m.chat.id):
        k = await rdb.get(f"{Dev_Zaid}:botkey") or "🧚‍♀️"
        return await m.reply(quote=True, text=f"{k} {_DEV_PERM}")

    prefix = "msgoverride:"
    suffix = Dev_Zaid
    pattern = f"{prefix}*{suffix}"

    keys = await rdb.keys(pattern)
    data: dict[str, str] = {}
    for key in keys:
        # احترازي: تجاهل أي مفتاح لا يطابق شكل message_override_key بالضبط
        if not key.startswith(prefix) or not key.endswith(suffix):
            continue
        message_id = key[len(prefix): len(key) - len(suffix)]
        value = await rdb.get(key)
        if value is not None:
            data[message_id] = value

    if not data:
        return await m.reply(
            quote=True,
            text="لا توجد ردود مخصّصة حالياً في Redis — كل الردود تستخدم نصوصها الافتراضية.",
        )

    filename = f"msgoverrides_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    try:
        await m.reply_document(
            filename,
            quote=True,
            caption=f"📦 تصدير الردود المخصّصة — {len(data)} رد",
        )
    finally:
        if os.path.exists(filename):
            os.remove(filename)


# ══════════════════════════════════════════════════════════════════════════════
# 7) استيراد_الردود — كرد على ملف JSON مُصدَّر سابقاً عبر تصدير_الردود.
#    تحقّق كامل (وجود المعرّف ضمن DEFAULT_MESSAGES + تطابق الـ placeholders)
#    لكل المعرّفات أولاً، وتجميع كل الأخطاء دفعة واحدة، قبل أي حفظ فعلي.
#    لا يوجد حفظ جزئي: لو وُجد ولو خطأ واحد، لا يُحفظ أي معرّف إطلاقاً.
# ══════════════════════════════════════════════════════════════════════════════

@register("استيراد_الردود")
@Client.on_message(filters.text & filters.regex(r"^استيراد_الردود$"), group=1500)
@safe_handler
async def importMessagesHandler(c: Client, m) -> None:
    if not await _is_dev(m.from_user.id, m.chat.id):
        k = await rdb.get(f"{Dev_Zaid}:botkey") or "🧚‍♀️"
        return await m.reply(quote=True, text=f"{k} {_DEV_PERM}")

    if not m.reply_to_message or not m.reply_to_message.document:
        return await m.reply(
            quote=True,
            text=(
                "أرسل هذا الأمر كرد (Reply) على ملف JSON مُصدَّر سابقاً عبر أمر: تصدير_الردود"
            ),
        )

    doc = m.reply_to_message.document
    if doc.file_name and not doc.file_name.lower().endswith(".json"):
        return await m.reply(quote=True, text="❌ الملف المُرفَق يجب أن يكون بصيغة JSON (.json)")

    local_path = f"./msgimport_{m.from_user.id}_{int(datetime.now().timestamp())}.json"
    try:
        local_path = await m.reply_to_message.download(local_path)
        with open(local_path, "r", encoding="utf-8") as f:
            raw = f.read()
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)

    try:
        payload = json.loads(raw)
    except Exception:
        return await m.reply(quote=True, text="❌ الملف ليس JSON صالحاً.")

    if not isinstance(payload, dict):
        return await m.reply(
            quote=True,
            text="❌ صيغة الملف غير صحيحة — يجب أن يكون كائن JSON بصيغة {\"المعرّف\": \"النص\"}.",
        )

    if not payload:
        return await m.reply(quote=True, text="⚠️ الملف فارغ — لا يوجد شيء لاستيراده.")

    errors: list[str] = []
    to_save: dict[str, str] = {}

    for message_id, text in payload.items():
        if message_id not in DEFAULT_MESSAGES:
            errors.append(f"• {message_id} → معرّف غير موجود ضمن DEFAULT_MESSAGES")
            continue

        if not isinstance(text, str):
            errors.append(f"• {message_id} → القيمة يجب أن تكون نصاً (string)")
            continue

        original_ph = _original_placeholders(message_id)
        imported_ph = {
            field_name
            for _, field_name, _, _ in string.Formatter().parse(text)
            if field_name
        }
        unknown_ph = imported_ph - original_ph
        if unknown_ph:
            errors.append(
                f"• {message_id} → placeholders غير معروفة: {sorted(unknown_ph)} "
                f"(المسموح به فقط: {sorted(original_ph)})"
            )
            continue

        to_save[message_id] = text

    if errors:
        error_text = "\n".join(errors)
        return await m.reply(
            quote=True,
            text=(
                "❌ تم رفض الاستيراد بالكامل — لم يُحفظ أي شيء بسبب الأخطاء التالية:\n\n"
                f"{error_text}\n\n"
                "صحّح الملف وأعد إرساله (كرد عليه بنفس الأمر) دون حفظ جزئي."
            ),
        )

    for message_id, text in to_save.items():
        await set_message_override(message_id, text)

    saved_list = "\n".join(f"• {mid}" for mid in to_save)
    await m.reply(
        quote=True,
        text=f"✅ تم استيراد وحفظ {len(to_save)} رد بنجاح:\n\n{saved_list}",
    )
