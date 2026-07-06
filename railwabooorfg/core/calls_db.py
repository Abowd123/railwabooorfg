"""
core/calls_db.py — bmqa-v2
تخزين حالة المكالمات الصوتية وقوائم الانتظار داخل Redis.

سبب الفصل عن core/db.py:
  - db.py مسؤول حصراً عن تهيئة عملاء قواعد البيانات (Redis + kvsqlite).
  - إضافة منطق المكالمات إليه سيُضخّمه بمسؤوليات لا علاقة لها بالتهيئة.
  - الفصل يُسهّل استيراد وحدة المكالمات بشكل مستقل من محرك PyTgCalls لاحقاً.

بنية مفاتيح Redis:
  vc:{chat_id}:state  → Hash  (حالة المكالمة النشطة: video, paused)
  vc:{chat_id}:queue  → List  (قائمة الانتظار، FIFO: rpush + lpop)
"""

from __future__ import annotations

import json
import logging

# rdb يُستورد بعد تهيئته في init_databases() — آمن لأن calls_db
# لن يُستخدم إلا بعد بدء تشغيل البوت (نفس نمط Plugins/downloader.py).
from core.db import rdb

logger = logging.getLogger("bmqa.calls_db")


# ─────────────────────────────────────────────────────────────────────────────
# حالة المكالمة النشطة  (Redis Hash)
# ─────────────────────────────────────────────────────────────────────────────

async def set_active_call(chat_id: int, video: bool = False) -> None:
    """تخزّن مكالمة نشطة جديدة بحالة إيقاف مؤقت = False."""
    await rdb.hset(
        f"vc:{chat_id}:state",
        mapping={
            "video":  int(video),
            "paused": 0,          # False عند البداية دائماً
        },
    )
    logger.debug("set_active_call chat_id=%d video=%s", chat_id, video)


async def get_active_call(chat_id: int) -> dict | None:
    """
    تعيد حالة المكالمة الحالية:
        {"video": bool, "paused": bool}
    أو None إذا لم توجد مكالمة نشطة.
    """
    data = await rdb.hgetall(f"vc:{chat_id}:state")
    if not data:
        return None
    return {
        "video":  bool(int(data.get("video",  0))),
        "paused": bool(int(data.get("paused", 0))),
    }


async def set_paused(chat_id: int, paused: bool) -> None:
    """تحدّث حقل paused فقط دون المساس ببقية بيانات المكالمة."""
    await rdb.hset(f"vc:{chat_id}:state", "paused", int(paused))
    logger.debug("set_paused chat_id=%d paused=%s", chat_id, paused)


async def remove_active_call(chat_id: int) -> None:
    """
    تحذف بيانات المكالمة النشطة وقائمة الانتظار معاً دفعةً واحدة.
    يُستدعى عند إيقاف المكالمة نهائياً أو مغادرة البوت للمجموعة.
    """
    await rdb.delete(f"vc:{chat_id}:state", f"vc:{chat_id}:queue")
    logger.debug("remove_active_call chat_id=%d", chat_id)


# ─────────────────────────────────────────────────────────────────────────────
# قائمة الانتظار  (Redis List — FIFO)
# rpush يضيف للنهاية، lpop يسحب من البداية
# ─────────────────────────────────────────────────────────────────────────────

async def queue_push(chat_id: int, item: dict) -> None:
    """تضيف عنصراً إلى نهاية قائمة الانتظار (JSON مُسلسَل)."""
    await rdb.rpush(f"vc:{chat_id}:queue", json.dumps(item, ensure_ascii=False))
    logger.debug("queue_push chat_id=%d item_keys=%s", chat_id, list(item.keys()))


async def queue_pop_next(chat_id: int) -> dict | None:
    """
    تسحب أول عنصر في القائمة (FIFO) وتعيده كـ dict.
    تعيد None إذا كانت القائمة فارغة.
    """
    raw = await rdb.lpop(f"vc:{chat_id}:queue")
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("queue_pop_next: فشل تحليل JSON لـ chat_id=%d", chat_id)
        return None


async def queue_list(chat_id: int) -> list[dict]:
    """
    تعيد جميع عناصر القائمة بنفس ترتيب التشغيل (الأول → الأخير).
    تعيد قائمة فارغة إن لم توجد عناصر.
    """
    items = await rdb.lrange(f"vc:{chat_id}:queue", 0, -1)
    result = []
    for raw in items:
        try:
            result.append(json.loads(raw))
        except json.JSONDecodeError:
            logger.warning("queue_list: تخطّي عنصر تالف في chat_id=%d", chat_id)
    return result


async def queue_clear(chat_id: int) -> None:
    """تحذف قائمة الانتظار بالكامل دون المساس ببيانات المكالمة النشطة."""
    await rdb.delete(f"vc:{chat_id}:queue")
    logger.debug("queue_clear chat_id=%d", chat_id)
