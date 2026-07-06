"""
main.py — bmqa-v2

نقطة الدخول الرئيسية. مسؤوليتها فقط:
  1) تهيئة نظام الـ logging (قبل أي شيء آخر) بمستويات INFO/WARNING/ERROR
     مع RotatingFileHandler.
  2) تهيئة اتصال Redis عبر redis.asyncio (غير متزامن بالكامل).
  3) تهيئة اتصال kvsqlite عبر نسخته الـ async.
  4) تهيئة عميل Pyrogram (Client) وربطه بجدول التوجيه في core/dispatcher.py.

لا تُكتب هنا أي قيمة سرية: كل شيء يُقرأ عبر config.py (الذي بدوره يقرأ من
os.environ / .env). هذا الملف لا ينقل أي أوامر/Plugins فعلية بعد — فقط الهيكل.
"""

import asyncio
import logging
import logging.handlers
import os

from pyrogram import Client

import config
from core.dispatcher import COMMAND_HANDLERS
from core.db import redis_client, ytdb, sounddb, wsdb


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

# Console handler — لعرض INFO فما فوق مباشرة في الطرفية.
_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(_formatter)

# Rotating file handler — يدور الملف بعد 5MB ويحتفظ بـ 5 نسخ قديمة.
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

# نخفض ضجيج مكتبات خارجية مزعجة في اللوج بدون كتمها بالكامل.
logging.getLogger("pyrogram").setLevel(logging.WARNING)


# ============================================================
# 2) Redis (async) و3) kvsqlite (async)
# ============================================================
# النسخ الفعلية (singletons) أصبحت في core/db.py (RedisDB/KVSqliteDB) حتى
# تكون طبقة بيانات مشتركة واحدة يستوردها main.py وكل Plugin لاحقاً، بدل
# إنشاء عميل Redis/kvsqlite منفصل في كل ملف.


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

# ملاحظة: COMMAND_HANDLERS من core/dispatcher.py هو جدول توجيه فارغ حالياً
# (dict: اسم الأمر -> handler). سيُستخدم لاحقاً بدل سلسلة if/elif، لكن ربطه
# الفعلي بمعالج رسائل Pyrogram يتم في مرحلة لاحقة بعد نقل الأوامر.


async def _connect_services() -> None:
    """يتحقق من جاهزية Redis و kvsqlite قبل بدء العميل."""
    try:
        await redis_client.ping()
        logger.info("Redis: اتصال ناجح.")
    except Exception:
        logger.error("Redis: فشل الاتصال.", exc_info=True)
        raise

    try:
        await ytdb.connect()
        await sounddb.connect()
        await wsdb.connect()
        logger.info("kvsqlite: تم الاتصال بجميع القواعد (ytdb, sounddb, wsdb).")
    except Exception:
        logger.error("kvsqlite: فشل الاتصال بإحدى القواعد.", exc_info=True)
        raise


async def main() -> None:
    await _connect_services()
    logger.info("عدد الأوامر المسجّلة في dispatcher حالياً: %d", len(COMMAND_HANDLERS))

    async with app:
        logger.info("bmqa-v2 بدأ التشغيل بنجاح.")
        await asyncio.Event().wait()  # ينتظر إلى الأبد (حتى إيقاف يدوي).


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.warning("تم إيقاف البوت يدوياً.")
