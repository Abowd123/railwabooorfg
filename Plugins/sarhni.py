'''


██████╗░██████╗░██████╗░
██╔══██╗╚════██╗██╔══██╗
██████╔╝░█████╔╝██║░░██║
██╔══██╗░╚═══██╗██║░░██║
██║░░██║██████╔╝██████╔╝
╚═╝░░╚═╝╚═════╝░╚═════╝░


[ = This plugin is a part from R3D Source code = ]
{"Developer":"https://t.me/yqyqy66"}

'''

"""
مُنقول من bmqa/Plugins/sarhni.py → bmqa-v2/Plugins/sarhni.py

الأوامر/المعالجات:
  - صارحني  (group=37, text & group)
    يُرجع رابط صارحني الخاص بالمستخدم.
  - معالج الرسائل الخاصة (group=2, private)
    • /start sarhni<id> : يبدأ جلسة صارحني
    • أي رسالة أثناء الجلسة: تُحوَّل مجهولة الهوية إلى صاحب الرابط
  - callback_query (regex "sarhni")
    • sarhni:bye : إنهاء الجلسة
    • sarhni+rep<user_id> : الرد على رسالة مجهولة

التحويلات: sync→async، Thread→await مباشر، r.<op>→await rdb.<op>،
            c.get_chat/send_message/m.copy/a.pin → كلها await
"""

import logging
import random
import string
import pytz
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.enums import *
from pyrogram.types import *
from config import Dev_Zaid, botUsername
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from helpers.ranks import admin_pls
from helpers.ranks import isLockCommand


def get_sarhni_id():
    rndm = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(10)])
    return rndm


@register("sarhni_group")
@Client.on_message(filters.text & filters.group, group=37)
@safe_handler
async def sarhniHandler(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')
    if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}') or await rdb.get(f'{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not await admin_pls(m.from_user.id, m.chat.id):
        return
    if await rdb.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}'):
        return
    text = m.text
    name = await rdb.get(f'{Dev_Zaid}:BotName') or 'رعد'
    if text.startswith(f'{name} '):
        text = text.replace(f'{name} ', '')
    if await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}'):
        text = await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}')
    if await rdb.get(f'Custom:{Dev_Zaid}&text={text}'):
        text = await rdb.get(f'Custom:{Dev_Zaid}&text={text}')
    if await isLockCommand(m.from_user.id, m.chat.id, text):
        return

    if text == 'صارحني':
        if not await rdb.get(f'{m.from_user.id}:sar7ni:{Dev_Zaid}'):
            id = get_sarhni_id()
            await rdb.set(f'{m.from_user.id}:sar7ni:{Dev_Zaid}', id)
            await rdb.set(f'{id}:sarhni:{Dev_Zaid}', m.from_user.id)
        else:
            id = await rdb.get(f'{m.from_user.id}:sar7ni:{Dev_Zaid}')
        await rdb.set(f'{m.from_user.id}:sarhniname', m.from_user.first_name)
        return await m.reply(
            f'{k} أهلين عيني「 ⁪⁬⁪⁬{m.from_user.mention} 」\n{k} هذا رابط صارحني الخاص فيك',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('📩', url=f't.me/{botUsername}?start=sarhni{id}')
            ]])
        )


@register("sarhni_private")
@Client.on_message(filters.private, group=2)
@safe_handler
async def sarhniHandlerP(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')
    channel = await rdb.get(f'{Dev_Zaid}:BotChannel') or 'yqyqy66'

    if m.text:
        text = m.text
        if text.startswith('/start sarhni'):
            id = text.split('sarhni')[1]
            if not await rdb.get(f'{id}:sarhni:{Dev_Zaid}'):
                return await m.reply(f'{k} رابط صارحني غلط')
            else:
                user_id = int(await rdb.get(f'{id}:sarhni:{Dev_Zaid}'))
                if m.from_user.id == user_id:
                    return await m.reply('انت هطف تدخل رابط صراحة حقك؟')
                get = await c.get_chat(user_id)
                await rdb.set(f'{m.from_user.id}:sarhni', get.id, ex=300)
                a = await m.reply(
                    f'{k} دخلت الحين رابط صارحني مع 「 ⁪⁬⁪⁬{get.first_name} 」\n'
                    f'{k} اي رسالة ترسلها لي راح احولها له بسرية تامة بدون مايعرفك\n༄',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton('الغاء', callback_data='sarhni:bye')
                    ], [
                        InlineKeyboardButton('🧚‍♀️', url=f't.me/{channel}')
                    ]]),
                    quote=True
                )
                return await a.pin(both_sides=True)

        if await rdb.get(f'{m.from_user.id}:sarhni') and len(text) < 1000:
            user_id = int(await rdb.get(f'{m.from_user.id}:sarhni'))
            name = await rdb.get(f'{user_id}:sarhniname')
            TIME_ZONE = "Asia/Riyadh"
            ZONE = pytz.timezone(TIME_ZONE)
            TIME = datetime.now(ZONE)
            clock = TIME.strftime("%I:%M %p")
            date = TIME.strftime("%d/%m/%Y")
            txt = (
                f'{k} وصلتك رسالة مصارحة جديدة\n{k} التاريخ : {date}\n'
                f'{k} الساعة : {clock}\n\n{k} الرسالة :\n\n{text}\n☆'
            )
            try:
                await c.send_message(
                    user_id, txt,
                    disable_web_page_preview=True,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton('رد', callback_data=f'sarhni+rep{m.from_user.id}'),
                    ], [
                        InlineKeyboardButton('🧚‍♀️', url=f't.me/{channel}')
                    ]])
                )
                return await m.reply(f'{k} ابشر ارسلت رسالتك بسرية تامة لـ {name}', quote=True)
            except Exception as e:
                logging.exception(e)
                return await m.reply('مقدر ارسله شيء يمكن حاظرني', quote=True)

    if await rdb.get(f'{m.from_user.id}:sarhni'):
        user_id = int(await rdb.get(f'{m.from_user.id}:sarhni'))
        name = await rdb.get(f'{user_id}:sarhniname')
        TIME_ZONE = "Asia/Riyadh"
        ZONE = pytz.timezone(TIME_ZONE)
        TIME = datetime.now(ZONE)
        clock = TIME.strftime("%I:%M %p")
        date = TIME.strftime("%d/%m/%Y")
        txt = (
            f'{k} وصلتك رسالة مصارحة جديدة\n{k} التاريخ : {date}\n'
            f'{k} الساعة : {clock}\n\n{k} الرسالة :'
        )
        try:
            await c.send_message(user_id, txt, disable_web_page_preview=True)
            await m.copy(
                user_id,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton('رد', callback_data=f'sarhni+rep{m.from_user.id}'),
                ], [
                    InlineKeyboardButton('🧚‍♀️', url=f't.me/{channel}')
                ]])
            )
            return await m.reply(f'{k} ابشر ارسلت رسالتك بسرية تامة لـ {name}', quote=True)
        except Exception as e:
            logging.exception(e)
            return await m.reply('مقدر ارسله شيء يمكن حاظرني', quote=True)

    if await rdb.get(f'{m.from_user.id}:sarhnirep'):
        user_id = int(await rdb.get(f'{m.from_user.id}:sarhnirep'))
        await rdb.delete(f'{m.from_user.id}:sarhnirep')
        await m.reply(f'{k} ابشر ارسلت له ردك', quote=True)
        return await m.copy(user_id)


@Client.on_callback_query(filters.regex('sarhni'))
@safe_handler
async def sarhni_callback(c, m):
    if m.data == 'sarhni:bye':
        await rdb.delete(f'{m.from_user.id}:sarhni')
        await m.message.delete()
        return await m.answer('ابشر طلعتك من كل جلسة صارحني', show_alert=True)

    if m.data.startswith('sarhni+rep'):
        user_id = int(m.data.split('rep')[1])
        if not await rdb.get(f'{user_id}:sarhni'):
            return await m.answer('مايمدي ترد عليه لأنه طلع من جلسة صارحني', show_alert=True)
        if not int(await rdb.get(f'{user_id}:sarhni')) == m.from_user.id:
            return await m.answer('مايمدي ترد عليه لأنه طلع من جلسة صارحني', show_alert=True)
        else:
            await rdb.set(f'{m.from_user.id}:sarhnirep', user_id, ex=300)
            return await c.send_message(m.from_user.id, 'ارسل الرد الحين')
