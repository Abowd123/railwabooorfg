"""
core/callback_dispatcher.py — bmqa-v2
جدول التوجيه المركزي لـ CallbackQuery.

كيفية التسجيل من داخل الـ Plugins:
    from core.callback_dispatcher import register_callback

    @register_callback("delAdminMSG")
    async def _del_admin_msg(c, m): ...

    @register_callback("RPS:rock++")        # بادئة (بدون uid)
    async def _rps_rock(c, m): ...

جدول المُوجِّهات الكاملة (نص بيانات callback → الملف المسؤول):
┌─────────────────────────────────┬─────────────────────────────────────────┐
│ نمط m.data                      │ الملف                                   │
├─────────────────────────────────┼─────────────────────────────────────────┤
│ commands1:{uid}  …  commands8:{uid} │ Plugins/all_callback_help_menus.py  │
│ delAdminMSG                     │ Plugins/all_callback_help_menus.py      │
│ yes:{uid}                       │ Plugins/all_callback_help_menus.py      │
│ no:{uid}                        │ Plugins/all_callback_help_menus.py      │
│ yesVER:{uid}                    │ Plugins/all_callback_help_menus.py      │
│ noVER:{uid}                     │ Plugins/all_callback_help_menus.py      │
│ yes:del:bank                    │ Plugins/all_callback_help_menus.py      │
│ no:del:bank                     │ Plugins/all_callback_help_menus.py      │
│ topfloos:{uid}                  │ Plugins/all_callback_help_menus.py      │
│ topzrf:{uid}                    │ Plugins/all_callback_help_menus.py      │
│ gowner+{uid}                    │ Plugins/all_callback_help_menus.py      │
│ owner+{uid}                     │ Plugins/all_callback_help_menus.py      │
│ mod+{uid}                       │ Plugins/all_callback_help_menus.py      │
│ admin+{uid}                     │ Plugins/all_callback_help_menus.py      │
│ pre+{uid}                       │ Plugins/all_callback_help_menus.py      │
│ RPS:rock++{uid}                 │ Plugins/all_callback_games.py           │
│ RPS:paper++{uid}                │ Plugins/all_callback_games.py           │
│ RPS:scissors++{uid}             │ Plugins/all_callback_games.py           │
│ None                            │ — (تجاهل صامت في dispatch)              │
└─────────────────────────────────┴─────────────────────────────────────────┘
"""
from __future__ import annotations

from typing import Any, Callable

CALLBACK_HANDLERS: dict[str, Callable] = {}


def register_callback(prefix: str) -> Callable:
    """
    يسجّل معالج callback تحت بادئة معيّنة.

    المفتاح المُسجَّل هو البادئة (قبل uid المتغيّر):
      "commands1:"  ← يتطابق مع "commands1:123456"
      "delAdminMSG" ← مطابقة دقيقة
      "RPS:rock++"  ← يتطابق مع "RPS:rock++123456"
      "yes:"        ← يتطابق مع "yes:123456"
    """
    def decorator(fn: Callable) -> Callable:
        CALLBACK_HANDLERS[prefix] = fn
        return fn
    return decorator


async def dispatch_callback(data: str, c: Any, m: Any) -> bool:
    """
    يوجّه callback بحسب m.data.

    منطق البحث:
      1. مطابقة دقيقة:  data == prefix
      2. مطابقة بادئة:  data.startswith(prefix)

    Returns:
        True  — وُجد معالج.
        False — لا معالج (يتجاهل الـ CallbackQueryHandler).
    """
    if data == "None":
        return True

    if data in CALLBACK_HANDLERS:
        await CALLBACK_HANDLERS[data](c, m)
        return True

    for prefix, handler in CALLBACK_HANDLERS.items():
        if data.startswith(prefix):
            await handler(c, m)
            return True

    return False
