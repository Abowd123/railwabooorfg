"""
all_callback_akinator.py — bmqa-v2
═══════════════════════════════════════════════════════════════════════════════
منقول من bmqa/Plugins/games.py (سطر 1678–1778) — akinatorHandler

m.data المُعالَجة:
  - start_aki:{uid}      → بدء لعبة الأكيناتور
  - aki_c:n++{uid}       → إجابة "لا"
  - aki_c:y++{uid}       → إجابة "اي"
  - aki_c:p++{uid}       → إجابة "ممكن"

التحويلات:
  - @Client.on_callback_query(filters.regex('aki')) → async def
  - users_demon مشترك مع all_games.py عبر core.state
  - time.sleep → asyncio.sleep (غير موجود في الأصل لكن aki blocking → run_in_executor)
  - c.send_photo / c.send_message / m.edit_message_text → await
  - akinator استدعاءات blocking تُشغَّل في thread pool (run_in_executor) لتفادي حجب
    event loop أثناء طلبات الشبكة لـ akinator API

سلوكيات غامضة محفوظة:
  [B1] progression >= 65 → win() ثم first_guess: محفوظ حرفياً.
  [B1] print(str_to_send): محفوظ (debug log الأصل).
"""

import logging
import asyncio

import akinator as aki_lib

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.state import users_demon


def _make_answer_markup(uid):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton('لا', callback_data=f'aki_c:n++{uid}'),
                InlineKeyboardButton('اي', callback_data=f'aki_c:y++{uid}'),
            ],
            [
                InlineKeyboardButton('ممكن', callback_data=f'aki_c:p++{uid}')
            ]
        ]
    )


async def _check_win_and_send(c, m, uid, channel):
    aki = users_demon[uid][0]
    if aki.progression >= 65:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, aki.win)
        str_to_send = aki.first_guess
        print(str_to_send)
        await m.message.delete()
        rep = InlineKeyboardMarkup(
            [[InlineKeyboardButton('🧚‍♀️', url=f't.me/{channel}')]]
        )
        try:
            await c.send_photo(
                m.message.chat.id,
                str_to_send['absolute_picture_path'],
                caption=f"{str_to_send['name']} - {str_to_send['description']}",
                reply_markup=rep
            )
        except Exception as e:
            logging.exception(e)
            await c.send_message(
                m.message.chat.id,
                f"{str_to_send['name']} - {str_to_send['description']}",
                reply_markup=rep
            )
        del users_demon[uid]
        return True
    return False


@Client.on_callback_query(filters.regex('aki'))
@safe_handler
async def akinatorHandler(c, m):
    channel = await rdb.get(f'{Dev_Zaid}:BotChannel') or 'yqyqy66'
    uid = m.from_user.id

    if m.data == f'start_aki:{uid}':
        rep = InlineKeyboardMarkup(
            [[InlineKeyboardButton('🧚‍♀️', url=f't.me/{channel}')]]
        )
        await m.edit_message_text('⇜ جاري بدء اللعبة...', reply_markup=rep)
        loop = asyncio.get_event_loop()
        aki = aki_lib.Akinator()
        q = await loop.run_in_executor(None, lambda: aki.start_game(language='ar'))
        users_demon.update({uid: [aki, q]})
        return await m.edit_message_text(
            users_demon[uid][1],
            reply_markup=_make_answer_markup(uid)
        )

    if m.data == f'aki_c:n++{uid}':
        if uid not in users_demon:
            return
        loop = asyncio.get_event_loop()
        users_demon[uid][1] = await loop.run_in_executor(
            None, lambda: users_demon[uid][0].answer('n')
        )
        if await _check_win_and_send(c, m, uid, channel):
            return
        return await m.edit_message_text(
            users_demon[uid][1],
            reply_markup=_make_answer_markup(uid)
        )

    if m.data == f'aki_c:y++{uid}':
        if uid not in users_demon:
            return
        loop = asyncio.get_event_loop()
        users_demon[uid][1] = await loop.run_in_executor(
            None, lambda: users_demon[uid][0].answer('y')
        )
        if await _check_win_and_send(c, m, uid, channel):
            return
        return await m.edit_message_text(
            users_demon[uid][1],
            reply_markup=_make_answer_markup(uid)
        )

    if m.data == f'aki_c:p++{uid}':
        if uid not in users_demon:
            return
        loop = asyncio.get_event_loop()
        users_demon[uid][1] = await loop.run_in_executor(
            None, lambda: users_demon[uid][0].answer('p')
        )
        if await _check_win_and_send(c, m, uid, channel):
            return
        return await m.edit_message_text(
            users_demon[uid][1],
            reply_markup=_make_answer_markup(uid)
        )
