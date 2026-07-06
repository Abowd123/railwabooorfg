"""
message_handler.py — bmqa-v2
═══════════════════════════════════════════════════════════════════════════
المعالج المركزي لرسائل القروب (يحلّ محلّ on_zbi من all.py سطر 187).

الفرق عن النسخة الأصلية:
  - on_zbi كان يتحقق من الاشتراك الإجباري فقط ويمرّر للـ group=28 handlers.
  - هذا المعالج يفعل الشيء نفسه + يستدعي core.dispatcher.dispatch() مباشرةً
    بعد اجتياز جميع الفحوصات المسبقة.
  - إذا أعاد dispatch() True → أمر تمّت معالجته → m.stop_propagation()
    (يمنع group=28 من إعادة معالجة نفس الأمر).
  - إذا أعاد dispatch() False → لا معالج مسجَّل بعد → m.continue_propagation()
    (يسمح لـ all_settings.py, all_features_toggle.py, ... بمعالجته).

التحويلات التقنية عن on_zbi الأصلي (متزامن → غير متزامن):
  r.get(...)   → await rdb.get(...)
  c.get_chat()/c.get_chat_member() → await ...
  m.reply(...)  → await m.reply(...)

⚠️ group=-1111111111111 يضمن تشغيل هذا المعالج قبل أي معالج آخر.
"""

import logging
import time
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from config import Dev_Zaid, botUsername, sudo_id
from core.db import rdb
from core.errors import safe_handler
import core.dispatcher as dispatcher


BOT_OWNER_FALLBACK_ID = 7201745912

# ─────────────────────────────────────────────────────────────────────────
# كاش TTL قصير خاص بفحص الاشتراك الإجباري (c.get_chat_member لعضو واحد).
#
# ⚠️ هذا ليس core/cache.py (MembersCache): ذاك مصمَّم لقوائم أعضاء كاملة
# (get_admins)، بينما هذا يحتاج تخزين نتيجة عضو واحد فقط لكل (channel, uid)
# — لذا كاش مستقل بسيط أنسب من إعادة استخدام MembersCache هنا.
#
# TTL قصير جداً (ثوانٍ قليلة فقط، وليس دقائق كما في core/cache.py) لأن هذا
# الفحص أمني (منع استخدام الأمر لغير المشتركين): تخزينه لفترة طويلة قد
# يسمح لعضو غادر القناة للتو باستخدام الأمر حتى انتهاء المهلة. ثوانٍ قليلة
# تكفي لتقليل استهلاك الحصة عند تكرار نفس المستخدم لأوامر force-trigger
# بسرعة (تفعيل/تعطيل/قفل/فتح/ايدي/الاوامر) دون المخاطرة بفجوة أمنية طويلة.
_SUBSCRIPTION_CHECK_TTL = 5.0
_subscription_cache: dict[tuple[str, int], tuple[bool, float]] = {}


async def _is_subscribed(c: Client, force_channel: str, uid: int) -> bool:
    """يتحقق (مع كاش TTL قصير) من أن uid عضو فعّال في force_channel."""
    from pyrogram.enums import ChatMemberStatus

    key = (force_channel, uid)
    cached = _subscription_cache.get(key)
    if cached and (time.monotonic() - cached[1]) < _SUBSCRIPTION_CHECK_TTL:
        return cached[0]

    member = await c.get_chat_member(f"@{force_channel}", uid)
    is_subscribed = member.status not in (
        ChatMemberStatus.LEFT,
        ChatMemberStatus.BANNED,
        ChatMemberStatus.RESTRICTED,
    )
    _subscription_cache[key] = (is_subscribed, time.monotonic())
    return is_subscribed


async def _resolve_text(m: Message) -> str:
    """يطبّع نص الرسالة: يزيل اسم البوت من البداية + يطبّق الأوامر المخصصة."""
    text = m.text or ""
    name = await rdb.get(f"{Dev_Zaid}:BotName") or "ليو"
    if text.startswith(f"{name} "):
        text = text.replace(f"{name} ", "", 1)
    custom = await rdb.get(f"{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}")
    if custom:
        text = custom
    global_custom = await rdb.get(f"Custom:{Dev_Zaid}&text={text}")
    if global_custom:
        text = global_custom
    return text


async def _is_dev(uid: int) -> bool:
    """يتحقق من صلاحية Developer (تجاوز فحص القناة)."""
    if uid in (BOT_OWNER_FALLBACK_ID, int(Dev_Zaid), sudo_id):
        return True
    if await rdb.get(f"{uid}:rankDEV:{Dev_Zaid}"):
        return True
    if await rdb.get(f"{uid}:rankDEV2:{Dev_Zaid}"):
        return True
    return False


@Client.on_message(filters.group & filters.text, group=-1111111111111)
@safe_handler
async def on_group_message(c: Client, m: Message) -> None:
    """
    بوابة كل رسائل القروب النصية.

    الخطوات:
      1. تطبيع النص (اسم البوت + أوامر مخصصة).
      2. inDontCheck flag → تمرير مباشر بلا فحص.
      3. فحص Dev → تمرير مباشر.
      4. فحص الاشتراك الإجباري (إن كان مفعّلاً).
      5. dispatch() → معالجة الأمر أو تمرير لـ group=28.
    """
    if not m.from_user:
        return m.continue_propagation()

    text = await _resolve_text(m)
    uid = m.from_user.id
    cid = m.chat.id

    # 1. inDontCheck: وضع الاختبار — تجاوز كل الفحوصات
    if await rdb.get(f"inDontCheck:{Dev_Zaid}"):
        handled = await dispatcher.dispatch(text, c, m)
        if handled:
            return m.stop_propagation()
        return m.continue_propagation()

    # 2. المطوّرون يتجاوزون فحص الاشتراك
    if await _is_dev(uid):
        handled = await dispatcher.dispatch(text, c, m)
        if handled:
            return m.stop_propagation()
        return m.continue_propagation()

    # 3. فحص الاشتراك الإجباري (فقط لأوامر محددة)
    _force_trigger = (
        text.startswith("تفعيل ")
        or text.startswith("تعطيل ")
        or text.startswith("قفل ")
        or text.startswith("فتح ")
        or text == "ايدي"
        or text == "الاوامر"
    )

    force_channel = await rdb.get(f"forceChannel:{Dev_Zaid}")
    disable_sub = await rdb.get(f"disableSubscribe:{Dev_Zaid}")

    if _force_trigger and force_channel and not disable_sub:
        try:
            if not await _is_subscribed(c, force_channel, uid):
                raise Exception("not_member")
        except Exception as e:
            logging.exception(e)
            k = await rdb.get(f"{Dev_Zaid}:botkey") or "❌"
            await m.reply(
                f"{k} يجب الاشتراك في القناة أولاً",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(
                        "اشترك 🔔",
                        url=f"https://t.me/{force_channel}"
                    )]]
                ),
            )
            return m.stop_propagation()

    # 4. توجيه الأمر عبر الجدول المركزي
    handled = await dispatcher.dispatch(text, c, m)
    if handled:
        return m.stop_propagation()
    return m.continue_propagation()
