"""
core/assistant.py — bmqa-v2
حساب مساعد (Userbot) اختياري للانضمام للمكالمات الصوتية لاحقاً.
"""

import logging
import struct  # استيراد مكتبة struct لمعالجة الخطأ مباشرة

from pyrogram import Client

import config

logger = logging.getLogger("bmqa")

assistant: Client | None = None


async def start_assistant() -> None:
    """
    يبدأ تشغيل الحساب المساعد إن توفّرت جلسته في config.ASSISTANT_SESSION.
    يحمي البوت من الانهيار حتى لو كان كود الجلسة (Session String) تالفاً أو غير متوافق.
    """
    global assistant

    if not config.ASSISTANT_SESSION:
        logger.info("ميزة الموسيقى معطلة - لا يوجد ASSISTANT_SESSION")
        return

    try:
        # استخدام إعدادات الذاكرة المؤقتة بالكامل
        assistant = Client(
            name=None,
            api_id=config.api_id,
            api_hash=config.api_hash,
            session_string=config.ASSISTANT_SESSION,
            in_memory=True,
        )
        await assistant.start()
        me = await assistant.get_me()
        logger.info(
            "الحساب المساعد بدأ بنجاح | @%s (id=%d)",
            me.username or me.first_name,
            me.id,
        )
    except (struct.error, Exception) as e:
        # إذا كان الخطأ هو تفكيك الجلسة التالفة، يتم طباعة تحذير واضح لمنع انهيار المحرك
        logger.error(
            f"فشل تشغيل الحساب المساعد بسبب كود جلسة تالف أو غير متوافق (struct.error). ميزة الموسيقى معطلة. الخطأ: {e}"
        )
        assistant = None


async def stop_assistant() -> None:
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
