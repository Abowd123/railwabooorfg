"""
main.py — bmqa-v2
"""

import asyncio
import logging
import logging.handlers
import os

from pyrogram import Client

import config
from core.dispatcher import COMMAND_HANDLERS
# استيراد دالة التهيئة فقط في الأعلى لتجنب تضارب الـ Loop أثناء الـ Import
from core.db import init_databases
from core.assistant import start_assistant, stop_assistant
from core.calls_engine import engine


# ============================================================
# 1) Logging
# ============================================================
LOG_DIR = os.environ.get("LOG_DIR", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "bmqa.log")

logger = logging.getLogger("bmqa")
logger.setLevel(logging.INFO)

_formatter = logging.Formatter(
    fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(_formatter)

_file_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE,
    maxBytes=5 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
_file_handler.setLevel(logging.INFO)
_file_handler.setFormatter(_formatter)

logger.addHandler(_console_handler)
logger.addHandler(_file_handler)

logging.getLogger("pyrogram").setLevel(logging.WARNING)


# ============================================================
# 4) Pyrogram Client
# ============================================================
app = Client(
    name=f"{config.Dev_Zaid}bmqa",
    api_id=config.api_id,
    api_hash=config.api_hash,
    bot_token=config.token,
    plugins={"root": "Plugins"},
)


async def _connect_services() -> None:
    """يتحقق من جاهزية Redis و kvsqlite قبل بدء العميل."""
    # استيراد الكائنات هنا (داخل الدالة) بعد أن نضمن أنه تم إنشاؤها داخل الـ Loop الصحيح
    from core.db import redis_client, ytdb, sounddb, wsdb

    try:
        await redis_client.ping()
        logger.info("Redis: اتصال ناجح.")
    except Exception:
        logger.error("Redis: فشل الاتصال.", exc_info=True)
        raise

    try:
        # فحص الجاهزية الذكي الخاص بك
        await ytdb.exists("__healthcheck__")
        await sounddb.exists("__healthcheck__")
        await wsdb.exists("__healthcheck__")
        logger.info("kvsqlite: تم التحقق من جاهزية جميع القواعد (ytdb, sounddb, wsdb).")
    except Exception:
        logger.error("kvsqlite: فشل الاتصال بإحدى القواعد.", exc_info=True)
        raise


async def main() -> None:
    # 🌟 أول خطوة: تهيئة القواعد فوراً داخل حلقة الأحداث النشطة
    await init_databases()

    # التحقق من الخدمات بأمان
    await _connect_services()

    logger.info("عدد الأوامر المسجّلة in dispatcher حالياً: %d", len(COMMAND_HANDLERS))

    # تشغيل الحساب المساعد — لا يوقف البوت إن فشل أو كان ASSISTANT_SESSION فارغاً
    try:
        await start_assistant()
    except Exception:
        logger.error("خطأ غير متوقع أثناء تشغيل الحساب المساعد.", exc_info=True)

    # تشغيل محرك المكالمات — يعتمد على الحساب المساعد، لا يوقف البوت إن فشل
    try:
        await engine.start()
    except Exception:
        logger.error(
            "فشل تشغيل محرك المكالمات — ميزة الموسيقى معطلة.", exc_info=True
        )

    try:
        async with app:
            logger.info("bmqa-v2 بدأ التشغيل بنجاح.")
            await asyncio.Event().wait()
    finally:
        # إيقاف محرك المكالمات أولاً ثم الحساب المساعد
        try:
            await engine.stop_engine()
        except Exception:
            logger.warning("خطأ أثناء إيقاف محرك المكالمات عند الإغلاق.", exc_info=True)

        try:
            await stop_assistant()
        except Exception:
            logger.warning("خطأ أثناء إيقاف الحساب المساعد عند الإغلاق.", exc_info=True)

        try:
            from core.youtube_calls import close_api_session
            await close_api_session()
        except Exception:
            logger.warning("خطأ أثناء إغلاق جلسة ArtistBots عند الإغلاق.", exc_info=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.warning("تم إيقاف البوت يدوياً.")
