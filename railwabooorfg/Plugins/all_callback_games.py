"""
all_callback_games.py — bmqa-v2
═══════════════════════════════════════════════════════════════════════════════
Callbacks لعبة حجر ورقة مقص (RPS) من CallbackQueryResponse (all.py سطر 4792–5001).

m.data المُعالَجة:
  - RPS:rock++{uid}      → المستخدم اختار 🪨
  - RPS:paper++{uid}     → المستخدم اختار 📃
  - RPS:scissors++{uid}  → المستخدم اختار ✂️

منطق الفوز (محفوظ حرفياً من الأصل):
  المستخدم يفوز → يُضاف له +1 فلوس في rdb (f"{uid}:Floos")
  البوت يفوز   → لا تغيير في الفلوس
  تعادل         → لا تغيير في الفلوس

التحويلات:
  r.get/set → await rdb.get/set
  Thread    → await مباشرة (يُعالَج من callback_dispatcher)
"""

import random

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.callback_dispatcher import register_callback


async def _add_floos(uid: int) -> None:
    """يُضيف +1 فلوس للمستخدم في Redis."""
    raw = await rdb.get(f"{uid}:Floos")
    if raw:
        await rdb.set(f"{uid}:Floos", int(raw) + 1)
    else:
        await rdb.set(f"{uid}:Floos", 1)


def _channel_btn(channel: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🧚‍♀️", url=f"t.me/{channel}")]]
    )


def _clean_name(name: str) -> str:
    for ch in ("*", "`", "|", "#", "<", ">", "_"):
        name = name.replace(ch, "")
    return name


# ─── RPS:rock++ ──────────────────────────────────────────────────────────────

@register_callback("RPS:rock++")
@safe_handler
async def _rps_rock(c, m) -> None:
    if m.data != f"RPS:rock++{m.from_user.id}":
        return
    channel = await rdb.get(f"{Dev_Zaid}:BotChannel") or "YQYQY6"
    bot_name = _clean_name(await rdb.get(f"{Dev_Zaid}:BotName") or "رعد")
    choices = ["paper", "scissors", "rock"]
    kk = random.choice(choices)
    rep = _channel_btn(channel)

    if kk == "scissors":
        await _add_floos(m.from_user.id)
        await m.edit_message_text(
            f"""
أنت: 🪨
أنا: ✂️

النتيجة: ⁪⁬⁪⁬ 🏆 {m.from_user.first_name}
""",
            disable_web_page_preview=True,
            reply_markup=rep,
        )
    elif kk == "paper":
        await m.edit_message_text(
            f"""
أنت: 🪨
أنا: 📃

النتيجة: ⁪⁬⁪⁬ 🏆️ {bot_name}
""",
            disable_web_page_preview=True,
            reply_markup=rep,
        )
    else:
        await m.edit_message_text(
            f"""
أنت: 🪨
أنا: 🪨

النتيجة: ⁪⁬⁪⁬ ⚖️ {bot_name}
""",
            disable_web_page_preview=True,
            reply_markup=rep,
        )


# ─── RPS:paper++ ─────────────────────────────────────────────────────────────

@register_callback("RPS:paper++")
@safe_handler
async def _rps_paper(c, m) -> None:
    if m.data != f"RPS:paper++{m.from_user.id}":
        return
    channel = await rdb.get(f"{Dev_Zaid}:BotChannel") or "YQYQY6"
    bot_name = _clean_name(await rdb.get(f"{Dev_Zaid}:BotName") or "رعد")
    choices = ["paper", "scissors", "rock"]
    kk = random.choice(choices)
    rep = _channel_btn(channel)

    if kk == "rock":
        await _add_floos(m.from_user.id)
        await m.edit_message_text(
            f"""
أنت: 📃
أنا: 🪨

النتيجة: ⁪⁬⁪⁬ 🏆 {m.from_user.first_name}
""",
            disable_web_page_preview=True,
            reply_markup=rep,
        )
    elif kk == "scissors":
        await m.edit_message_text(
            f"""
أنت: 📃
أنا: ✂️

النتيجة: ⁪⁬⁪⁬ 🏆️ {bot_name}
""",
            disable_web_page_preview=True,
            reply_markup=rep,
        )
    else:
        await m.edit_message_text(
            f"""
أنت: 📃
أنا: 📃

النتيجة: ⁪⁬⁪⁬ ⚖️ {bot_name}
""",
            disable_web_page_preview=True,
            reply_markup=rep,
        )


# ─── RPS:scissors++ ──────────────────────────────────────────────────────────

@register_callback("RPS:scissors++")
@safe_handler
async def _rps_scissors(c, m) -> None:
    if m.data != f"RPS:scissors++{m.from_user.id}":
        return
    channel = await rdb.get(f"{Dev_Zaid}:BotChannel") or "YQYQY6"
    bot_name = _clean_name(await rdb.get(f"{Dev_Zaid}:BotName") or "رعد")
    choices = ["paper", "scissors", "rock"]
    kk = random.choice(choices)
    rep = _channel_btn(channel)

    if kk == "paper":
        await _add_floos(m.from_user.id)
        await m.edit_message_text(
            f"""
أنت: ✂️
أنا: 📃

النتيجة: ⁪⁬⁪⁬ 🏆 {m.from_user.first_name}
""",
            disable_web_page_preview=True,
            reply_markup=rep,
        )
    elif kk == "rock":
        await m.edit_message_text(
            f"""
أنت: ✂️
أنا: 🪨

النتيجة: ⁪⁬⁪⁬ 🏆️ {bot_name}
""",
            disable_web_page_preview=True,
            reply_markup=rep,
        )
    else:
        await m.edit_message_text(
            f"""
أنت: ✂️
أنا: ✂️

النتيجة: ⁪⁬⁪⁬ ⚖️ {bot_name}
""",
            disable_web_page_preview=True,
            reply_markup=rep,
        )
