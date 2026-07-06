"""
core/rate_limit.py — bmqa-v2

throttling بسيط لكل مستخدم مبني على Redis: لا أكثر من N أمر في نافذة زمنية
محددة (افتراضياً: دقيقة واحدة). يُستخدم عادة كـ decorator ثانٍ فوق/تحت
safe_handler على كل command handler.

الفكرة (INCR + EXPIRE):
  - نبني مفتاح Redis مميّز للمستخدم + الأمر: "ratelimit:{user_id}:{command}".
  - أول استدعاء ينشئ العداد بقيمة 1 ويضبط له صلاحية = window_seconds.
  - أي استدعاء لاحق خلال نفس النافذة يزيد العداد فقط (بدون تجديد الصلاحية).
  - لو تجاوز العداد الحد المسموح، تُرفض المحاولة حتى تنتهي النافذة الحالية.

هذا الملف حالياً هيكل جاهز للاستخدام، لكن لم يُربط بعد بأي أمر حقيقي
(لا يوجد نقل لأي Plugin في هذه المرحلة).
"""

from __future__ import annotations

import functools
from typing import Awaitable, Callable, TypeVar

from redis.asyncio import Redis

DEFAULT_MAX_COMMANDS = 5
DEFAULT_WINDOW_SECONDS = 60

F = TypeVar("F", bound=Callable[..., Awaitable[None]])


async def is_allowed(
    redis_client: Redis,
    user_id: int,
    command: str,
    max_commands: int = DEFAULT_MAX_COMMANDS,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
) -> bool:
    """يتحقق (ويحدّث) عداد Redis الخاص بالمستخدم لهذا الأمر.

    يُعيد True لو ما زال مسموحاً بالتنفيذ، وFalse لو تجاوز المستخدم الحد.
    """
    key = f"ratelimit:{user_id}:{command}"
    current = await redis_client.incr(key)
    if current == 1:
        # أول أمر في هذه النافذة: نضبط مدة انتهاء الصلاحية.
        await redis_client.expire(key, window_seconds)
    return current <= max_commands


def rate_limited(
    redis_client: Redis,
    command: str,
    max_commands: int = DEFAULT_MAX_COMMANDS,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
) -> Callable[[F], F]:
    """Decorator يطبّق is_allowed تلقائياً قبل تنفيذ الـ handler.

    يتوقع أن أول وسيطين للدالة المغلَّفة هما (client, message) بنفس نمط
    Pyrogram، وأن message.from_user.id متاح.

    الاستخدام المستقبلي المتوقع (بعد نقل الأوامر الفعلية):

        @register("ban")
        @safe_handler
        @rate_limited(redis_client, "ban", max_commands=10)
        async def ban_command(client, message):
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(client, message, *args, **kwargs):
            user_id = message.from_user.id if message.from_user else None
            if user_id is not None:
                allowed = await is_allowed(
                    redis_client, user_id, command, max_commands, window_seconds
                )
                if not allowed:
                    await message.reply(
                        "⏳ استخدمت هذا الأمر كثيراً، حاول بعد قليل."
                    )
                    return
            return await func(client, message, *args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
