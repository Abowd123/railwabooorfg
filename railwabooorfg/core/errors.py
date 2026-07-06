"""
core/errors.py — bmqa-v2
مزخرف safe_handler: يلتقط الاستثناءات الشائعة بهدوء بلا تعطل.

الاستخدام:
    @safe_handler
    async def myHandler(c, m) -> None:
        ...

السلوك:
  - ContinuePropagation / StopPropagation    → يُعاد رفعها كما هي (راجع
    ملاحظة [E1] بالأسفل) — لا تُلتقط أبداً هنا.
  - UserNotParticipant / FloodWait(< 10 ث)   → تجاهل
  - FloodWait(≥ 10 ث)                        → تسجيل تحذير
  - أي استثناء آخر                            → تسجيل الخطأ كاملاً بدون رفع

[E1] لماذا يجب استثناء ContinuePropagation/StopPropagation صراحةً قبل
     `except Exception:` العام:
     كلا الصنفين استثناءان عاديان (Exception subclasses) تستخدمهما pyrogram
     كإشارات تحكّم (control-flow signals) للموزّع الداخلي (dispatcher)، لا
     كأخطاء فعلية. بما أن `except Exception:` يلتقط أي استثناء من فئة
     Exception (وهو ما يشمل هذين الصنفين حتماً، أياً كان أصلهما الدقيق في
     التسلسل الهرمي)، فإن ترك الكتلة العامة وحدها بدون استثناء صريح لهما
     أولاً كانت ستلتقطهما بصمت وتُسجّلهما كـ"خطأ غير معالَج" بدل أن تصل
     فعلياً إلى موزّع pyrogram الذي يعتمد عليهما لتحديد الانتقال إلى الـ
     handler التالي (أو التوقف الكامل) في نفس المجموعة الرقمية (group).
     بدون هذا الاستثناء الصريح هنا، أي `raise pyrogram.ContinuePropagation()`
     داخل أي Plugin مُزخرَف بـ @safe_handler لن يكون له أي أثر عملياً — وهي
     نفس المشكلة الموصوفة في [C4] بملف all_moderation_2.py، لكن على مستوى
     الديكوريتر المشترك بدل كل ملف على حدة.
     ⚠️ ملاحظة توافقية مهمة: تأكَّد عند رفع هذا الاستثناء داخل أي دالة
     `async def` (وليس فقط هنا) أن صنف ContinuePropagation في نسخة
     kurigram/pyrogram المُثبَّتة فعلياً ليس مبنياً على أساس StopIteration
     مباشرة؛ فبايثون (PEP 479) يحوّل تلقائياً أي StopIteration يُرفَع من
     داخل coroutine إلى RuntimeError("coroutine raised StopIteration")،
     مما كان سيُبطل هذه الآلية بالكامل. راجع الفحص التجريبي الموثَّق في
     tests/test_group28_continue_propagation.py لتفاصيل هذا الاكتشاف أثناء
     كتابة الاختبار.
"""
from __future__ import annotations

import asyncio
import functools
import logging
from typing import Callable

from pyrogram import ContinuePropagation, StopPropagation
from pyrogram.errors import FloodWait, UserNotParticipant

logger = logging.getLogger(__name__)


def safe_handler(fn: Callable) -> Callable:
    @functools.wraps(fn)
    async def wrapper(c, m, *args, **kwargs):
        try:
            return await fn(c, m, *args, **kwargs)
        except (ContinuePropagation, StopPropagation):
            # يجب أن تمرّ هذه الإشارتان دون أن تُلتقطا هنا — انظر [E1] أعلاه.
            raise
        except UserNotParticipant:
            pass
        except FloodWait as e:
            if e.value >= 10:
                logger.warning("FloodWait %ds in %s", e.value, fn.__name__)
            await asyncio.sleep(min(e.value, 5))
        except Exception:
            logger.exception("Unhandled error in %s", fn.__name__)
    return wrapper
