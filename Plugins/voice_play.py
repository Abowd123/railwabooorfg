"""
Plugins/voice_play.py — bmqa-v2
أوامر التشغيل الصوتي في المكالمات الجماعية.

مُعزَّل في Plugin مستقل عن downloader.py لأن منطق البث
(PyTgCalls + queue + assistant) مختلف تماماً عن منطق
التنزيل وإرسال الملف الذي يعتمد على arq workers.

⚠️ تنبيه تعارض "ايقاف":
   الكلمة "ايقاف" مستخدمة في Plugins/all_settings.py (سطر 348)
   لإيقاف عملية المنشن، وهي غير مسجَّلة في COMMAND_HANDLERS لكنها
   معالَجة عبر @Client.on_message. تسجيلها هنا سيُطغى على تلك الوظيفة.
   القرار: استخدام "ايقاف التشغيل" بدلاً من "ايقاف" لإيقاف المكالمة.
   إذا أردت استخدام "ايقاف" مستقبلاً يجب أولاً إعادة تسمية
   المعالج في all_settings.py سطر 348 أو دمج المنطقَين.

قرار الصلاحيات:
   جميع أوامر التشغيل والتحكم تتطلب صلاحية مشرف (admin_pls)
   لأن المحرك يُشغِّل userbot حقيقي يتصل بمكالمات صوتية ويستهلك
   موارد شبكة، والسماح لأي عضو بذلك ثغرة أمنية في بوت حماية.
   الاستثناء الوحيد: "قائمة الانتظار" — قراءة فقط، لا ضرر.
"""

from __future__ import annotations

import logging

from pyrogram import Client, filters

import config
from core import calls_db
from core.calls_engine import engine
from core.db import rdb
from core.dispatcher import register
from core.errors import safe_handler
from core.youtube_calls import extract_video_id, search
from helpers.ranks import admin_pls, isLockCommand

logger = logging.getLogger("bmqa.voice_play")


# ─────────────────────────────────────────────────────────────────────────────
# مساعدات داخلية
# ─────────────────────────────────────────────────────────────────────────────

async def _k() -> str:
    """مفتاح البوت (الإيموجي) من Redis."""
    return await rdb.get(f"{config.Dev_Zaid}:botkey") or "🧚‍♀️"


async def _is_enabled(chat_id: int) -> bool:
    """هل البوت مفعَّل في هذه المجموعة؟ — نفس الفحص المستخدم في downloader.py"""
    return bool(await rdb.get(f"{chat_id}:enable:{config.Dev_Zaid}"))


def _engine_ok() -> bool:
    """هل محرك المكالمات بدأ بنجاح؟"""
    return engine._engine_started


# ─────────────────────────────────────────────────────────────────────────────
# 1. تشغيل <استعلام>  /  تشغيل فيديو <استعلام>
#    الصلاحية: مشرف فقط
# ─────────────────────────────────────────────────────────────────────────────

@register("تشغيل ")
@Client.on_message(
    filters.text & filters.group & filters.regex(r"^تشغيل "),
    group=32,
)
@safe_handler
async def play_handler(c: Client, m) -> None:
    if not await _is_enabled(m.chat.id):
        return
    if await isLockCommand(m.from_user.id, m.chat.id, m.text):
        return

    k    = await _k()
    text = (m.text or "").strip()

    # ── تحديد نوع البث ──────────────────────────────────────────────────────
    if text.startswith("تشغيل فيديو "):
        audio_only = False
        query      = text[len("تشغيل فيديو "):].strip()
    else:
        audio_only = True
        query      = text[len("تشغيل "):].strip()

    if not query:
        return await m.reply(f"{k} أرسل اسم أغنية أو رابط يوتيوب.")

    # ── التحقق من الصلاحية ──────────────────────────────────────────────────
    if not await admin_pls(m.from_user.id, m.chat.id):
        return await m.reply(f"{k} هذا الأمر يخص المشرفين فقط.")

    # ── فحص ASSISTANT_SESSION ───────────────────────────────────────────────
    if not config.ASSISTANT_SESSION:
        return await m.reply(
            f"{k} ميزة تشغيل الصوت غير مفعلة، لم يتم إعداد ASSISTANT_SESSION."
        )

    # ── فحص ArtistBots ──────────────────────────────────────────────────────
    if not config.API_URL or not config.API_KEYS:
        return await m.reply(
            f"{k} تعذر تنزيل المقطع عبر ArtistBots لأن الخدمة غير مهيأة."
        )

    # ── فحص الفيديو ─────────────────────────────────────────────────────────
    if not audio_only and not config.VC_VIDEO_ENABLED:
        return await m.reply(
            f"{k} تشغيل الفيديو غير مفعَّل، يمكن تفعيله عبر VC_VIDEO_ENABLED=true في .env"
        )

    # ── فحص المحرك ──────────────────────────────────────────────────────────
    if not _engine_ok():
        return await m.reply(
            f"{k} محرك المكالمات لم يبدأ بعد، تحقق من إعداد ASSISTANT_SESSION."
        )

    # ── استخراج video_id ─────────────────────────────────────────────────────
    video_id = extract_video_id(query)
    if not video_id:
        # البحث عبر yt-dlp
        sent    = await m.reply(f"{k} ⏳ جاري البحث...")
        results = await search(query, limit=1)
        if not results:
            return await sent.edit_text(f"{k} لم يُعثر على نتائج لـ: {query}")
        video_id = results[0]["video_id"]
        title    = results[0].get("title", video_id)
    else:
        sent  = await m.reply(f"{k} ⏳ جاري التحضير...")
        title = query

    # ── هل هناك مكالمة نشطة؟ ────────────────────────────────────────────────
    active = await calls_db.get_active_call(m.chat.id)

    if active:
        # أضف للانتظار
        await calls_db.queue_push(m.chat.id, {
            "video_id":  video_id,
            "title":     title,
            "video":     not audio_only,
            "requested": m.from_user.mention,
        })
        return await sent.edit_text(
            f"{k} تمت إضافته إلى قائمة الانتظار.\n"
            f"▸ {title}"
        )

    # ── تشغيل مباشر ──────────────────────────────────────────────────────────
    try:
        await engine.join_and_play(m.chat.id, video_id, m, audio_only=audio_only)
        await sent.edit_text(
            f"{k} يتم التشغيل الآن:\n"
            f"▸ {title}"
        )
    except ValueError:
        # تجاوز الحد الزمني المضبوط في VC_DURATION_LIMIT_MINUTES
        await sent.edit_text(
            f"{k} المقطع طويل جداً ويتجاوز الحد الزمني المسموح به.\n"
            f"يمكن تعديل الحد عبر VC_DURATION_LIMIT_MINUTES في .env"
        )
    except RuntimeError:
        # فشل التنزيل أو التشغيل — التفاصيل في سجلات السيرفر
        await sent.edit_text(
            f"{k} تعذّر تشغيل المقطع، يرجى المحاولة مرة أخرى.\n"
            f"إذا تكرّر الخطأ تحقق من إعدادات API_URL وAPI_KEYS."
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. ايقاف مؤقت
#    الصلاحية: مشرف فقط
# ─────────────────────────────────────────────────────────────────────────────

@register("ايقاف مؤقت")
@Client.on_message(
    filters.text & filters.group & filters.regex(r"^ايقاف مؤقت$"),
    group=32,
)
@safe_handler
async def pause_handler(c: Client, m) -> None:
    if not await _is_enabled(m.chat.id):
        return
    k = await _k()

    if not await admin_pls(m.from_user.id, m.chat.id):
        return await m.reply(f"{k} هذا الأمر يخص المشرفين فقط.")
    if not _engine_ok():
        return await m.reply(f"{k} محرك المكالمات غير نشط.")

    active = await calls_db.get_active_call(m.chat.id)
    if not active:
        return await m.reply(
            f"{k} لا توجد مكالمة صوتية نشطة، ابدأ مكالمة أولًا."
        )
    if active.get("paused"):
        return await m.reply(f"{k} التشغيل متوقف مؤقتاً بالفعل.")

    await engine.pause(m.chat.id)
    await m.reply(f"{k} ⏸ تم الإيقاف المؤقت.")


# ─────────────────────────────────────────────────────────────────────────────
# 3. استئناف
#    الصلاحية: مشرف فقط
# ─────────────────────────────────────────────────────────────────────────────

@register("استئناف")
@Client.on_message(
    filters.text & filters.group & filters.regex(r"^استئناف$"),
    group=32,
)
@safe_handler
async def resume_handler(c: Client, m) -> None:
    if not await _is_enabled(m.chat.id):
        return
    k = await _k()

    if not await admin_pls(m.from_user.id, m.chat.id):
        return await m.reply(f"{k} هذا الأمر يخص المشرفين فقط.")
    if not _engine_ok():
        return await m.reply(f"{k} محرك المكالمات غير نشط.")

    active = await calls_db.get_active_call(m.chat.id)
    if not active:
        return await m.reply(
            f"{k} لا توجد مكالمة صوتية نشطة، ابدأ مكالمة أولًا."
        )
    if not active.get("paused"):
        return await m.reply(f"{k} التشغيل يعمل بالفعل، لم يتوقف.")

    await engine.resume(m.chat.id)
    await m.reply(f"{k} ▶️ تم الاستئناف.")


# ─────────────────────────────────────────────────────────────────────────────
# 4. تخطي
#    الصلاحية: مشرف فقط
# ─────────────────────────────────────────────────────────────────────────────

@register("تخطي")
@Client.on_message(
    filters.text & filters.group & filters.regex(r"^تخطي$"),
    group=32,
)
@safe_handler
async def skip_handler(c: Client, m) -> None:
    if not await _is_enabled(m.chat.id):
        return
    k = await _k()

    if not await admin_pls(m.from_user.id, m.chat.id):
        return await m.reply(f"{k} هذا الأمر يخص المشرفين فقط.")
    if not _engine_ok():
        return await m.reply(f"{k} محرك المكالمات غير نشط.")

    active = await calls_db.get_active_call(m.chat.id)
    if not active:
        return await m.reply(
            f"{k} لا توجد مكالمة صوتية نشطة، ابدأ مكالمة أولًا."
        )

    await m.reply(f"{k} ⏭ جاري التخطي...")
    await engine.play_next(m.chat.id)


# ─────────────────────────────────────────────────────────────────────────────
# 5. ايقاف التشغيل
#    الصلاحية: مشرف فقط
#
#    ⚠️ تعارض محتمل: "ايقاف" مستخدمة في all_settings.py سطر 348
#    لإيقاف عملية المنشن (يوقف @all). تم استخدام "ايقاف التشغيل"
#    تفادياً لهذا التعارض. إذا أردت استخدام "ايقاف" فقط، يجب
#    مراجعة all_settings.py وإعادة تسمية معالجها أولاً.
# ─────────────────────────────────────────────────────────────────────────────

@register("ايقاف التشغيل")
@Client.on_message(
    filters.text & filters.group & filters.regex(r"^ايقاف التشغيل$"),
    group=32,
)
@safe_handler
async def stop_handler(c: Client, m) -> None:
    if not await _is_enabled(m.chat.id):
        return
    k = await _k()

    if not await admin_pls(m.from_user.id, m.chat.id):
        return await m.reply(f"{k} هذا الأمر يخص المشرفين فقط.")
    if not _engine_ok():
        return await m.reply(f"{k} محرك المكالمات غير نشط.")

    active = await calls_db.get_active_call(m.chat.id)
    if not active:
        return await m.reply(
            f"{k} لا توجد مكالمة صوتية نشطة، ابدأ مكالمة أولًا."
        )

    await engine.stop(m.chat.id)
    await m.reply(f"{k} ⏹ تم إيقاف التشغيل وتفريغ قائمة الانتظار.")


# ─────────────────────────────────────────────────────────────────────────────
# 6. قائمة الانتظار
#    الصلاحية: متاح للجميع (قراءة فقط، لا ضرر أمني)
# ─────────────────────────────────────────────────────────────────────────────

@register("قائمة الانتظار")
@Client.on_message(
    filters.text & filters.group & filters.regex(r"^قائمة الانتظار$"),
    group=32,
)
@safe_handler
async def queue_handler(c: Client, m) -> None:
    if not await _is_enabled(m.chat.id):
        return
    k = await _k()

    active = await calls_db.get_active_call(m.chat.id)
    if not active:
        return await m.reply(
            f"{k} لا توجد مكالمة صوتية نشطة، ابدأ مكالمة أولًا."
        )

    items = await calls_db.queue_list(m.chat.id)
    if not items:
        return await m.reply(f"{k} قائمة الانتظار فارغة حالياً.")

    lines = [f"{k} قائمة الانتظار ({len(items)} {'مقطع' if len(items) == 1 else 'مقاطع'}):\n"]
    for i, item in enumerate(items, start=1):
        title     = item.get("title") or item.get("video_id", "—")
        requester = item.get("requested", "")
        vtype     = "📹 فيديو" if item.get("video") else "🎵 صوت"
        line      = f"{i}. {title[:50]} [{vtype}]"
        if requester:
            line += f"\n    طلبه: {requester}"
        lines.append(line)

    await m.reply("\n".join(lines))
