"""
core/assistant.py — bmqa-v2
حساب مساعد (Userbot) اختياري للانضمام للمكالمات الصوتية لاحقاً.

يتبع نمط التهيئة الكسولة (Lazy Initialization) نفسه المستخدم في core/db.py:
- المتغير معرَّف بـ None على مستوى الوحدة.
- يُنشأ الكائن الحقيقي داخل start_assistant() بعد بدء حلقة الأحداث النشطة.

إذا كان ASSISTANT_SESSION فارغاً تُعطَّل الميزة بصمت تام دون إيقاف البوت.
"""

import logging

from pyrogram import Client

import config

logger = logging.getLogger("bmqa")

# ─────────────────────────────────────────────────────────────────────────────
# Singleton — يبقى None حتى نجاح start_assistant()
# قابل للاستيراد مباشرةً:  from core.assistant import assistant
# ─────────────────────────────────────────────────────────────────────────────
assistant: Client | None = None


async def start_assistant() -> None:
    """
    يبدأ تشغيل الحساب المساعد إن توفّرت جلسته في config.ASSISTANT_SESSION.

    السلوك:
    - إذا كان ASSISTANT_SESSION فارغاً → رسالة توضيحية + عودة هادئة.
    - إذا نجح التشغيل → رسالة نجاح بـ username/id الحساب.
    - إذا فشل لأي سبب → رسالة خطأ مع الـ traceback، والـ assistant يبقى None.
    لا يُرفع أي استثناء في جميع الحالات — البوت الأساسي يعمل دائماً.
    """
    global assistant

    if not config.ASSISTANT_SESSION:
        logger.info("ميزة الموسيقى معطلة - لا يوجد ASSISTANT_SESSION")
        return

    try:
        assistant = Client(
            name="assistant",
            api_id=config.api_id,
            api_hash=config.api_hash,
            session_string=config.ASSISTANT_SESSION,
        )
        await assistant.start()
        me = await assistant.get_me()
        logger.info(
            "الحساب المساعد بدأ بنجاح | @%s (id=%d)",
            me.username or me.first_name,
            me.id,
        )
    except Exception:
        logger.error(
            "فشل تشغيل الحساب المساعد — ميزة الموسيقى معطلة.",
            exc_info=True,
        )
        assistant = None


async def stop_assistant() -> None:
    """
    يوقف الحساب المساعد بأمان إن كان يعمل.
    يُستدعى دائماً عند الإغلاق حتى لو لم يكن المساعد يعمل.
    """
    global assistant

    if assistant is None:
        return

    try:
        await assistant.stop()
        logger.info("الحساب المساعد توقف بنجاح.")
    except Exception:
        logger.warning(
            "حدث خطأ أثناء إيقاف الحساب المساعد.",
            exc_info=True,
        )
    finally:
        assistant = None
