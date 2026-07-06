"""
Plugins/private_and_sudos.py — bmqa-v2

مُنقول من bmqa/Plugins/private&sudos.py (909/910 سطر) → bmqa-v2/Plugins/private_and_sudos.py
(أعيدت تسمية الملف لأن "&" في اسم الملف غير مدعوم بشكل موثوق كوحدة import في بايثون).

الأوامر/المعالجات — مُقسَّمة حسب نطاق العمل (خاص فقط / خاص وقروبات):

  ── خاص فقط (filters.private) ──────────────────────────────────────────
  - pv_open_hms      (group=1999) — فتح رابط همسة "/start openhms<id>" (نظام wsdb القديم، منفصل عن whisper.py)
  - pv_to_send       (group=-2016) — يلتقط "/start hmsa..."، إذاعة الخاص/القروبات المُجدولة، استقبال الهمسة المُرسَلة
  - pv_private_panel (group=1) — لوحة التحكم: /start، /start Commands، /start rules، لوحة أزرار المطور، وجسر "." لِـ gptzaid

  ── خاص وقروبات معاً (بدون قيد نوع محادثة — كما في الأصل تماماً) ────────
  - sudos_commands (group=30, filters.text) — كل أوامر الإدارة/التحكم بالبوت:
    الاحصائيات، تفعيل/تعطيل البوت الخدمي، تفعيل/تعطيل التحميل واليوتيوب،
    الردود العامه (فرعها الداخلي private فقط)، المحظورين عام/من الالعاب،
    المجموعات المحظورة، رمز/قناة/اسم السورس، مجموعة المطور (فرعها الداخلي
    private فقط)، تعيين/مسح/وضع كل القيم أعلاه، تغيير المطور الاساسي،
    تحديث (إعادة تشغيل)، الملفات (sudo_id فقط)، اذاعة بالخاص/بالقروبات
    (تفعيل وضع الإذاعة فقط — التنفيذ الفعلي في pv_to_send لأنه لا يعمل إلا
    بالخاص أصلاً)، السيرفر، جلب نسخة القروبات/المستخدمين، المكتومين عام،
    "رابط <آيدي>"
  - sudo_eval      (filters.command("eval") & filters.user(sudo_id)) — تنفيذ كود بايثون
  - sudo_tio_exec  (filters.command("exec") & filters.user(sudo_id)) — تنفيذ كود بأي لغة عبر Tio
  - sudo_cmd       (filters.command("cmd") & filters.user(sudo_id)) — تنفيذ أمر شل
  - sudo_print     (filters.command("print") & filters.user(sudo_id)) — meval سريع
  - sudo_screenshot(filters.command(["sc","webs","ss"]) & filters.user(sudo_id)) — سكرين‌شوت موقع

كل هذه الأوامر الخمسة الأخيرة (sudo_*) مقيدة بـ filters.user(sudo_id) فقط، أي
أنها تعمل بالخاص والقروبات معاً بدون فرق — تماماً كما في الأصل — لأن صاحب
sudo_id هو نفسه في كل مكان.

التحويلات المطبّقة:
  - `r.<op>` -> `await rdb.<op>` (core/db.py)
  - `wsdb.get/set/delete` (كان sync عبر kvsqlite.sync) -> `await wsdb.<op>` (core/db.py، نفس الاسم)
  - `Thread(target=...).start()` (delRanksHandler->private_func، sudosCommandsHandler->SudosCommandsFunc)
    -> استدعاء مباشر `await` لنفس الدالة (async الآن) من داخل المعالج نفسه
  - `requests.get(...)` في جسر "." -> `httpx.AsyncClient` (نفس مثيل helpers/utils.py المستخدم أصلاً لـ cssworker_url)
  - كل نداءات pyrogram المتزامنة (m.reply, m.reply_chat_action, msg.edit, c.get_users,
    c.get_chat, c.send_message, m.copy, m.reply_document) -> await
  - dev_pls/dev2_pls/devp_pls/admin_pls/get_rank/get_devs_br -> await (async في helpers/ranks.py)
  - @register + @safe_handler على كل الـ8 handlers الحقيقية أعلاه.

⚠️ حُفظت شروط الصلاحيات حرفياً دون أي تغيير، بما في ذلك:
  - جسر "." (gptzaid) لا يتحقق من أي صلاحية إطلاقاً في الأصل — بقي كذلك هنا.
  - "السيرفر" يستخدم `lsb_release.get_distro_information()` رغم أن `lsb_release`
    غير مستورد في أي مكان بالمشروع الأصلي بالكامل (تحقّقت بالبحث) — هذه علّة
    NameError موجودة أصلاً في الكود المصدر (لم تُصلَح هنا حفاظاً على مطابقة
    السلوك تماماً؛ safe_handler سيلتقطها ويسجّلها بدل تعطّل غير متحكَّم به).
  - "جلب نسخة القروبات/المستخدمين" و"تحديث" (إعادة تشغيل البوت بالكامل)
    و"الملفات" (sudo_id فقط) بقيت بصلاحياتها الأصلية دون أي تعديل.
"""

import logging
import asyncio
import html
import json
import os
import platform
import random
import re
import sys
import time
import traceback
import uuid
from datetime import datetime
from io import StringIO

import httpx
import psutil
from meval import meval
from pytio import Tio, TioRequest

from pyrogram import Client, filters
from pyrogram.enums import ChatAction, ChatType
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from config import Dev_Zaid, botUsername, sudo_id
from core.db import rdb, wsdb, wsdb_get_checked
from core.dispatcher import register
from core.errors import safe_handler
from helpers.ranks import admin_pls, dev2_pls, dev_pls, devp_pls, get_devs_br, get_rank
from helpers.utils import cssworker_url, shell_exec


def get_size(bytes, suffix="B"):
    """
    Scale bytes to its proper format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor


async def on_send_hmsa(c: Client, m):
    """يُستدعى يدوياً من pv_to_send (وليس handler مستقل — نفس الأصل الذي كان
    الديكوريتر الخاص به مُعلَّقاً بـ '#' وكانت الدالة تُستدعى يدوياً)."""
    id = m.text.split("hmsa")[1]
    # مفتاح "اهمس" المبدئي هذا فقط هو من يملك TTL=1 ساعة (راجع
    # core/db.wsdb_setex + all_moderation_1.py). لهذا نقرأه هنا عبر
    # wsdb_get_checked بدل wsdb.get العادي، حتى تنتهي صلاحيته فعلياً.
    get = await wsdb_get_checked(id)
    if not get:
        return await m.reply("رابط الهمسة غلط")
    else:
        if m.from_user.id != get["from"]:
            return await m.reply("انت لم ترسل اهمس بالقروب")
        else:
            getUser = await c.get_users(get["to"])
            await wsdb.set(f"hmsa-{m.from_user.id}", get)
            return await m.reply(f"ارسل همستك الموجهة الى 「 {getUser.mention} 」 ")


@register("pv_open_hms")
@Client.on_message(filters.regex("^/start openhms") & filters.private, group=1999)
@safe_handler
async def open_hms(c: Client, m):
    id = m.text.split("openhms")[1]
    if not await wsdb.get(f"hms-{id}"):
        return await m.reply("رابط الهمسة غلط")
    else:
        data = await wsdb.get(f"hms-{id}")
        caption = data.get("caption", None)
        file = data.get("file", None)
        to = data["to"]
        if m.from_user.id != to and m.from_user.id != data["from"] and m.from_user.id != sudo_id:
            return await m.reply("☆ الهمسة غير موجهة لك يا عزيزي")
        else:
            if file:
                return await c.send_message(m.chat.id, "لقد ارسل لك ميديا والميديا ممنوعة في هذه الفترة لأنها تحت الصيانة اخبره بذالك", protect_content=True)
            else:
                return await c.send_message(
                    m.chat.id,
                    data["text"],
                    protect_content=True
                )


async def sleep_and_delete(client, chat_id, message):
    await asyncio.sleep(60)
    await client.delete_messages(chat_id, message_ids=message.message_id)


@register("pv_to_send")
@Client.on_message(filters.private, group=-2016)
@safe_handler
async def to_send(c: Client, m):
    if m.text and re.match("^/start hmsa", m.text):
        return await on_send_hmsa(c, m)
    k = await rdb.get(f'{Dev_Zaid}:botkey')
    if await rdb.get(f'{m.chat.id}:pvBroadcast:{m.from_user.id}{Dev_Zaid}') and await dev2_pls(m.from_user.id, m.chat.id):
        await rdb.delete(f'{m.chat.id}:pvBroadcast:{m.from_user.id}{Dev_Zaid}')
        if m.text and m.text == 'الغاء':
            return await m.reply(f"{k} ابشر الغيت كل شي")
        users = await rdb.smembers(f'{Dev_Zaid}:UsersList')
        count = 0
        failed = 0
        rep = await m.reply("جار الاذاعة..")
        for user in users:
            try:
                await m.copy(int(user))
                count += 1
            except FloodWait as f:
                logging.exception(f)
                await asyncio.sleep(f.value)
            except Exception as e:
                logging.exception(e)
                failed += 1
                pass
        return await rep.edit(f"{k} اذاعة ناجحة {count}")

    k = await rdb.get(f'{Dev_Zaid}:botkey')
    if await rdb.get(f'{m.chat.id}:gpBroadcast:{m.from_user.id}{Dev_Zaid}') and await dev2_pls(m.from_user.id, m.chat.id):
        await rdb.delete(f'{m.chat.id}:gpBroadcast:{m.from_user.id}{Dev_Zaid}')
        if m.text and m.text == 'الغاء':
            return await m.reply(f"{k} ابشر الغيت كل شي")
        chats = await rdb.smembers(f'enablelist:{Dev_Zaid}')
        count = 0
        failed = 0
        rep = await m.reply("جار الاذاعة..")
        for chat in chats:
            try:
                await m.copy(int(chat))
                count += 1
            except FloodWait as f:
                logging.exception(f)
                await asyncio.sleep(f.value)
            except Exception as e:
                logging.exception(e)
                failed += 1
                pass
        return await rep.edit(f"{k} اذاعة ناجحة {count}")

    get = await wsdb.get(f"hmsa-{m.from_user.id}")
    if get:
        await wsdb.delete(f"hmsa-{m.from_user.id}")
        to = get["to"]
        chat = get["chat"]
        id = get["id"]
        data = {}
        if m.media:
            if m.photo:
                file_id = m.photo.file_id
            elif m.video:
                file_id = m.video.file_id
            elif m.animation:
                file_id = m.animation.file_id
            elif m.audio:
                file_id = m.audio.file_id
            elif m.voice:
                file_id = m.voice.file_id
            elif m.sticker:
                file_id = m.sticker.file_id
            elif m.document:
                file_id = m.document.file_id
            caption = m.caption
            data["caption"] = caption
            data["file"] = file_id
        elif m.text:
            data["text"] = m.text.html

        id = str(uuid.uuid4())[:6]
        data["to"] = to
        data["from"] = m.from_user.id
        await wsdb.set(f"hms-{id}", data)
        url = f"https://t.me/{c.me.username}?start=openhms{id}"
        getUser = await c.get_users(to)
        await m.reply(f"تم ارسال همستك بنجاح الى {getUser.mention}")
        await c.send_message(
            chat_id=chat,
            text=f"☆ همسة سرية من < {m.from_user.mention} >\n☆ موجة الى < {getUser.mention} >",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="لعرض الهمسة",
                            url=url
                        )
                    ]
                ]
            )
        )
        return await c.delete_messages(chat, get["id"])


@register("pv_private_panel")
@Client.on_message(filters.text & filters.private, group=1)
@safe_handler
async def delRanksHandler(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')
    await private_func(c, m, k)


async def private_func(c, m, k):
    if await rdb.get(f'{m.from_user.id}:sarhni'):
        return
    text = m.text
    name = await rdb.get(f'{Dev_Zaid}:BotName') if await rdb.get(f'{Dev_Zaid}:BotName') else 'رعد'
    channel = await rdb.get(f'{Dev_Zaid}:BotChannel') if await rdb.get(f'{Dev_Zaid}:BotChannel') else 'yqyqy66'
    if text == '/start' and not await dev_pls(m.from_user.id, m.chat.id):
        await m.reply(text=f'''
اهلين انا ،{name} 🧚

↞ اختصاصي ادارة المجموعات من السبام والخ..
↞ كت تويت, يوتيوب, ساوند , واشياء كثير ..
↞ عشان تفعلني ارفعني اشراف وارسل تفعيل.
''', reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('ضيفني لـ مجموعتك 🧚‍♀️', url=f'https://t.me/{botUsername}?startgroup=Commands&admin=ban_users+restrict_members+delete_messages+add_admins+change_info+invite_users+pin_messages+manage_call+manage_chat+manage_video_chats+promote_members')],
            [InlineKeyboardButton(f'تحديثات {name} 🍻', url=f'https://t.me/{channel}')]
        ]))
        if not await rdb.sismember(f'{Dev_Zaid}:UsersList', m.from_user.id):
            await rdb.sadd(f'{Dev_Zaid}:UsersList', m.from_user.id)
            if m.from_user.username:
                username = f'@{m.from_user.username}'
            else:
                username = 'ماعنده يوزر'
            text = '''
☆ شخص جديد دخل للبوت
☆ اسمه : {}
☆ ايديه : `{}`
☆ معرفه : {}

☆ عدد المستخدمين صار {}
'''.format(m.from_user.mention, m.from_user.id, username, len(await rdb.smembers(f'{Dev_Zaid}:UsersList')))
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(m.from_user.first_name, user_id=m.from_user.id)]])
            if await rdb.get(f'DevGroup:{Dev_Zaid}'):
                await c.send_message(
                    int(await rdb.get(f'DevGroup:{Dev_Zaid}')),
                    text, reply_markup=reply_markup)
            else:
                for dev in await get_devs_br():
                    try:
                        await c.send_message(int(dev), text, disable_web_page_preview=True)
                    except Exception as e:
                        logging.exception(e)
                        pass

    if text == '/start Commands':
        return await m.reply(text=f'{k} اهلين فيك باوامر البوت\n\nللاستفسار - @{channel}',
                              reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton('م1', callback_data=f'commands1:{m.from_user.id}'),
                    InlineKeyboardButton('م2', callback_data=f'commands2:{m.from_user.id}')
                ],
                [
                    InlineKeyboardButton('م3', callback_data=f'commands3:{m.from_user.id}'),
                ],
                [
                    InlineKeyboardButton('الالعاب', callback_data=f'commands4:{m.from_user.id}'),
                    InlineKeyboardButton('التسليه', callback_data=f'commands5:{m.from_user.id}'),
                ],
                [
                    InlineKeyboardButton('اليوتيوب', callback_data=f'commands6:{m.from_user.id}'),
                ],
            ]
        )
        )

    if text == '/start rules':
        await m.reply(text='''
• القوانين

- ممنوع استخدام الثغرات
- ممنوع وضع اسماء مُخالفة
- ١٠ حروف مسموحه في اسمك اذا كنت بالتوب الباقي ماراح يطلع
- في حال انك بالتوب واسمك مزخرف راح يصفيه البوت تلقائي''', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"تحديثات {name} 🍻", url=f't.me/{channel}')]]))

    if text == '/start' and await dev_pls(m.from_user.id, m.chat.id):
        reply_markup = ReplyKeyboardMarkup(
            [
                [('الاحصائيات')],
                [('تغيير المطور الاساسي')],
                [("جلب نسخة القروبات"), ("جلب نسخة المستخدمين")],
                [('تفعيل البوت الخدمي'), ('تعطيل البوت الخدمي')],
                [('تفعيل التحميل واليوتيوب'), ('تعطيل التحميل واليوتيوب')],
                [('الردود العامه'), ('الاوامر العامه')],
                [('المحظورين عام'), ('المجموعات المحظورة')],
                [('اذاعة بالخاص'), ('بالمجموعات اذاعة')],
                [("المكتومين عام"), ("المحظورين من الالعاب")],
                [('اذاعة بالخاص'), ('اذاعة بالخاص تثبيت')],
                [('اذاعة بالمجموعات'), ('اذاعه بالمجموعات بالتثبيت')],
                [('رمز السورس'), ('قناة السورس'), ('اسم البوت')],
                [('مسح اسم البوت'), ('تعيين اسم البوت')],
                [('مسح رمز السورس'), ('وضع رمز السورس')],
                [('مسح قناة السورس'), ('وضع قناة السورس')],
                [("السيرفر"), ("الملفات"), ("/eval")],
                [('مجموعة المطور')],
                [('وضع مجموعة المطور'), ('مسح مجموعة المطور')],
                [('الغاء')]
            ],
            resize_keyboard=True,
            placeholder='@anas5 - @eFFb0t 🧚‍♀️'
        )
        if m.from_user.id == sudo_id:
            rank = 'تاج راسي ☆'
        else:
            rank = await get_rank(m.from_user.id, m.from_user.id)
        return await m.reply(quote=True, text=f'{k} الحلو {rank}\n{k} قدامك لوحة التحكم ', reply_markup=reply_markup)
    if text.startswith(". "):
        text = text.split(None, 1)[1]
        msg = await m.reply("...", quote=True)
        try:
            await m.reply_chat_action(ChatAction.TYPING)
        except Exception as e:
            logging.exception(e)
            print(e)
            pass
        async with httpx.AsyncClient() as _client:
            resp = await _client.get(f"https://gptzaid.zaidbot.repl.co/1/text={text}")
            rep = resp.text
        try:
            await m.reply_chat_action(ChatAction.TYPING)
        except Exception as e:
            logging.exception(e)
            print(e)
            pass
        await msg.edit(rep)


@register("sudos_commands")
@Client.on_message(filters.text, group=30)
@safe_handler
async def sudosCommandsHandler(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')
    channel = await rdb.get(f'{Dev_Zaid}:BotChannel') if await rdb.get(f'{Dev_Zaid}:BotChannel') else 'yqyqy66'
    await SudosCommandsFunc(c, m, k, channel)


async def SudosCommandsFunc(c, m, k, channel):
    if not m.from_user:
        return
    if not m.chat.type == ChatType.PRIVATE:
        if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
            return
    else:
        if await rdb.get(f'{m.from_user.id}:sarhni'):
            return
    if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not await admin_pls(m.from_user.id, m.chat.id):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):
        return

    if await rdb.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}') or await rdb.get(f'{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}'):
        return
    text = m.text
    name = await rdb.get(f'{Dev_Zaid}:BotName') if await rdb.get(f'{Dev_Zaid}:BotName') else 'رعد'
    if text.startswith(f'{name} '):
        text = text.replace(f'{name} ', '')
    if await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}'):
        text = await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}')
    if await rdb.get(f'Custom:{Dev_Zaid}&text={text}'):
        text = await rdb.get(f'Custom:{Dev_Zaid}&text={text}')

    if (await rdb.get(f'{m.chat.id}:setBotName:{m.from_user.id}{Dev_Zaid}') or await rdb.get(f'{m.chat.id}:setBotChannel:{m.from_user.id}{Dev_Zaid}') or await rdb.get(f'{m.chat.id}:setBotKey:{m.from_user.id}{Dev_Zaid}') or await rdb.get(f'{m.chat.id}:setDevGroup:{m.from_user.id}{Dev_Zaid}') or await rdb.get(f'{m.chat.id}:setBotowmer:{m.from_user.id}{Dev_Zaid}')) and text == 'الغاء':
        await m.reply(quote=True, text=f'{k} من عيوني لغيت كل شي')
        await rdb.delete(f'{m.chat.id}:setBotName:{m.from_user.id}{Dev_Zaid}')
        await rdb.delete(f'{m.chat.id}:setBotChannel:{m.from_user.id}{Dev_Zaid}')
        await rdb.delete(f'{m.chat.id}:setBotKey:{m.from_user.id}{Dev_Zaid}')
        await rdb.delete(f'{m.chat.id}:setDevGroup:{m.from_user.id}{Dev_Zaid}')
        return await rdb.delete(f'{m.chat.id}:setBotowmer:{m.from_user.id}{Dev_Zaid}')

    if await rdb.get(f'{m.chat.id}:setBotName:{m.from_user.id}{Dev_Zaid}') and await dev2_pls(m.from_user.id, m.chat.id):
        await rdb.delete(f'{m.chat.id}:setBotName:{m.from_user.id}{Dev_Zaid}')
        await rdb.set(f'{Dev_Zaid}:BotName', m.text)
        return await m.reply(quote=True, text=f'{k} ابشر عيني المطور غيرت اسمي لـ {m.text}')

    if await rdb.get(f'{m.chat.id}:setBotChannel:{m.from_user.id}{Dev_Zaid}') and await dev2_pls(m.from_user.id, m.chat.id):
        await rdb.delete(f'{m.chat.id}:setBotChannel:{m.from_user.id}{Dev_Zaid}')
        await rdb.set(f'{Dev_Zaid}:BotChannel', m.text.replace('@', ''))
        return await m.reply(quote=True, text=f'{k} ابشر عيني غيرت قناة السورس لـ {m.text}')

    if await rdb.get(f'{m.chat.id}:setBotKey:{m.from_user.id}{Dev_Zaid}') and await dev2_pls(m.from_user.id, m.chat.id):
        await rdb.delete(f'{m.chat.id}:setBotKey:{m.from_user.id}{Dev_Zaid}')
        await rdb.set(f'{Dev_Zaid}:botkey', m.text)
        return await m.reply(quote=True, text=f'{k} ابشر عيني غيرت رمز السورس لـ {m.text}')

    if await rdb.get(f'{m.chat.id}:setDevGroup:{m.from_user.id}{Dev_Zaid}') and await devp_pls(m.from_user.id, m.chat.id):
        await rdb.delete(f'{m.chat.id}:setDevGroup:{m.from_user.id}{Dev_Zaid}')
        try:
            id = int(m.text)
        except Exception as e:
            logging.exception(e)
            return await m.reply(quote=True, text=f'{k} الايدي غلط!')
        await rdb.set(f'DevGroup:{Dev_Zaid}', int(m.text))
        return await m.reply(quote=True, text=f'{k} ابشر عيني قروب المطور لـ {m.text}')

    if await rdb.get(f'{m.chat.id}:setBotowmer:{m.from_user.id}{Dev_Zaid}') and await devp_pls(m.from_user.id, m.chat.id):
        await rdb.delete(f'{m.chat.id}:setBotowmer:{m.from_user.id}{Dev_Zaid}')
        try:
            get = await c.get_chat(m.text.replace('@', ''))
        except Exception as e:
            logging.exception(e)
            return await m.reply(quote=True, text=f'{k} اليوزر غلط!')
        await rdb.set(f'{Dev_Zaid}botowner', get.id)
        await m.reply(quote=True, text=f'{k} ابشر نقلت ملكية البوت لـ {m.text}')
        with open('information.py', 'w+') as www:
            info_text = 'token = "{}"\nowner_id = {}'
            www.write(info_text.format(c.bot_token, get.id))

    if text == 'الاحصائيات':
        if not await dev2_pls(m.from_user.id, m.chat.id):
            return
        if not await rdb.smembers(f'{Dev_Zaid}:UsersList'):
            users = 0
        else:
            users = len(await rdb.smembers(f'{Dev_Zaid}:UsersList'))
        if not await rdb.smembers(f'enablelist:{Dev_Zaid}'):
            chats = 0
        else:
            chats = len(await rdb.smembers(f'enablelist:{Dev_Zaid}'))
        return await m.reply(quote=True, text=f'{k} الحلو مطوري\n{k} المستخدمين ~ {users}\n{k} المجموعات ~ {chats}')

    if text == 'تفعيل البوت الخدمي':
        if not await dev2_pls(m.from_user.id, m.chat.id):
            return
        if not await rdb.get(f'DisableBot:{Dev_Zaid}'):
            return await m.reply(quote=True, text=f'{k} البوت الخدمي مفعل من قبل')
        else:
            await rdb.delete(f'DisableBot:{Dev_Zaid}')
            return await m.reply(quote=True, text=f'{k} ابشر فعلت البوت الخدمي')

    if text == 'تعطيل البوت الخدمي':
        if not await dev2_pls(m.from_user.id, m.chat.id):
            return
        if await rdb.get(f'DisableBot:{Dev_Zaid}'):
            return await m.reply(quote=True, text=f'{k} البوت الخدمي معطل من قبل')
        else:
            await rdb.set(f'DisableBot:{Dev_Zaid}', 1)
            return await m.reply(quote=True, text=f'{k} ابشر عطلت البوت الخدمي')

    if text == 'تفعيل التحميل واليوتيوب':
        if not await dev2_pls(m.from_user.id, m.chat.id):
            return
        if not await rdb.get(f':disableYT:{Dev_Zaid}'):
            return await m.reply(quote=True, text=f'{k} التحميل مفعل من قبل')
        else:
            await rdb.delete(f':disableYT:{Dev_Zaid}')
            return await m.reply(quote=True, text=f'{k} ابشر فعلت التحميل')

    if text == 'تعطيل التحميل واليوتيوب':
        if not await dev2_pls(m.from_user.id, m.chat.id):
            return
        if await rdb.get(f':disableYT:{Dev_Zaid}'):
            return await m.reply(quote=True, text=f'{k} التحميل معطل من قبل')
        else:
            await rdb.set(f':disableYT:{Dev_Zaid}', 1)
            return await m.reply(quote=True, text=f'{k} ابشر عطلت التحميل')

    if text == 'الردود العامه' and m.chat.type == ChatType.PRIVATE:
        if not await dev2_pls(m.from_user.id, m.chat.id):
            return
        else:
            if not await rdb.smembers(f'FiltersList:{Dev_Zaid}'):
                return await m.reply(quote=True, text=f'{k} مافيه ردود عامه مضافه')
            else:
                text = 'ردود البوت:\n'
                count = 1
                for reply in await rdb.smembers(f'FiltersList:{Dev_Zaid}'):
                    rep = reply
                    type = await rdb.get(f'{rep}:filtertype:{Dev_Zaid}')
                    text += f'\n{count} - ( {rep} ) ࿓ ( {type} )'
                    count += 1
                text += '\n☆'
                return await m.reply(quote=True, text=text, disable_web_page_preview=True)

    if text == 'المستخدمين المحظورين' or text == 'المحظورين عام':
        if not await dev_pls(m.from_user.id, m.chat.id):
            return await m.reply(quote=True, text=f'{k} هذا الأمر يخص ( المطور وفوق ) بس')
        else:
            if not await rdb.smembers(f'listGBAN:{Dev_Zaid}'):
                return await m.reply(quote=True, text=f'{k} مافيه حمير محظورين')
            else:
                text = 'الحمير المحظورين عام:\n'
                count = 1
                for user in await rdb.smembers(f'listGBAN:{Dev_Zaid}'):
                    try:
                        get = await c.get_users(int(user))
                        mention = '@' + get.username if get.username else get.mention
                        id = get.id
                    except Exception as e:
                        logging.exception(e)
                        mention = f'[{int(user)}](tg://user?id={int(user)})'
                        id = int(user)
                    text += f'{count}) {mention} ~ ( `{id}` )\n'
                    count += 1
                return await m.reply(quote=True, text=text)

    if text == 'المحظورين من الالعاب':
        if not await dev_pls(m.from_user.id, m.chat.id):
            return await m.reply(quote=True, text=f'{k} هذا الأمر يخص ( المطور وفوق ) بس')
        else:
            if not await rdb.smembers(f'listGBANGAMES:{Dev_Zaid}'):
                return await m.reply(quote=True, text=f'{k} مافيه حمير محظورين من الالعاب')
            else:
                text = 'الحمير المحظورين عام من الالعاب:\n'
                count = 1
                for user in await rdb.smembers(f'listGBANGAMES:{Dev_Zaid}'):
                    try:
                        get = await c.get_users(int(user))
                        mention = '@' + get.username if get.username else get.mention
                        id = get.id
                    except Exception as e:
                        logging.exception(e)
                        mention = f'[{int(user)}](tg://user?id={int(user)})'
                        id = int(user)
                    text += f'{count}) {mention} ~ ( `{id}` )\n'
                    count += 1
                return await m.reply(quote=True, text=text)

    if text == 'المجموعات المحظورة':
        if not await dev2_pls(m.from_user.id, m.chat.id):
            return
        else:
            if not await rdb.smembers(f':BannedChats:{Dev_Zaid}'):
                return await m.reply(quote=True, text=f'{k} مافي قروب محظور عام')
            else:
                text = 'المجموعات المحظورة عام:\n'
                count = 1
                for user in await rdb.smembers(f':BannedChats:{Dev_Zaid}'):
                    text += f'{count}) {user}\n'
                    count += 1
                return await m.reply(quote=True, text=text)

    if text == 'رمز السورس':
        if not await dev2_pls(m.from_user.id, m.chat.id):
            return
        return await m.reply(quote=True, text=f'`{k}`')

    if text == 'قناة السورس':
        if not await dev2_pls(m.from_user.id, m.chat.id):
            return
        if not await rdb.get(f'{Dev_Zaid}:BotChannel'):
            return await m.reply(quote=True, text=f'{k} قناة السورس مو معينة')
        else:
            cha = await rdb.get(f'{Dev_Zaid}:BotChannel')
            return await m.reply(quote=True, text=f'@{cha}')

    if text == 'اسم البوت':
        if not await dev2_pls(m.from_user.id, m.chat.id):
            return
        if not await rdb.get(f'{Dev_Zaid}:BotName'):
            return await m.reply(quote=True, text=f'{k} مافي اسم للبوت')
        else:
            name = await rdb.get(f'{Dev_Zaid}:BotName')
            return await m.reply(quote=True, text=name)

    if text == 'مجموعة المطور' and m.chat.type == ChatType.PRIVATE:
        if not await dev_pls(m.from_user.id, m.chat.id):
            return
        else:
            if not await rdb.get(f'DevGroup:{Dev_Zaid}'):
                return await m.reply(quote=True, text=f'{k} مجموعة المطور مو معينة')
            else:
                id = int(await rdb.get(f'DevGroup:{Dev_Zaid}'))
                chat = await c.get_chat(id)
                link = chat.invite_link
                return await m.reply(quote=True, text=link, protect_content=True)

    if text == 'تعيين اسم البوت':
        if not await dev2_pls(m.from_user.id, m.chat.id):
            return
        await rdb.set(f'{m.chat.id}:setBotName:{m.from_user.id}{Dev_Zaid}', 1, ex=600)
        return await m.reply(quote=True, text=f'{k} حبيبي مطوري ارسل اسمي الجديد الحين')

    if text == 'مسح اسم البوت':
        if not await dev2_pls(m.from_user.id, m.chat.id):
            return
        await rdb.delete(f'{Dev_Zaid}:BotName')
        return await m.reply(quote=True, text=f'{k} ابشر مسحت اسم البوت')

    if text == 'وضع قناة السورس':
        if not await dev2_pls(m.from_user.id, m.chat.id):
            return
        await rdb.set(f'{m.chat.id}:setBotChannel:{m.from_user.id}{Dev_Zaid}', 1, ex=600)
        return await m.reply(quote=True, text=f'{k} حبيبي مطوري ارسل قناة السورس الحين')

    if text == 'مسح قناة السورس':
        if not await dev2_pls(m.from_user.id, m.chat.id):
            return
        await rdb.delete(f'{Dev_Zaid}:BotChannel')
        return await m.reply(quote=True, text=f'{k} ابشر مسحت قناة السورس')

    if text == 'وضع رمز السورس':
        if not await dev2_pls(m.from_user.id, m.chat.id):
            return
        await rdb.set(f'{m.chat.id}:setBotKey:{m.from_user.id}{Dev_Zaid}', 1, ex=600)
        return await m.reply(quote=True, text=f'{k} حبيبي مطوري ارسل رمز السورس الحين')

    if text == 'مسح رمز السورس':
        if not await dev2_pls(m.from_user.id, m.chat.id):
            return
        await rdb.set(f'{Dev_Zaid}:botkey', '⇜')
        return await m.reply(quote=True, text=f'{k} ابشر مسحت رمز السورس')

    if text == 'وضع مجموعة المطور':
        if not await dev2_pls(m.from_user.id, m.chat.id):
            return
        await rdb.set(f'{m.chat.id}:setDevGroup:{m.from_user.id}{Dev_Zaid}', 1, ex=600)
        return await m.reply(quote=True, text=f'{k} حبيبي مطوري ارسل ايدي القروب الحين')

    if text == 'مسح مجموعة المطور':
        if not await devp_pls(m.from_user.id, m.chat.id):
            return
        await rdb.delete(f'DevGroup:{Dev_Zaid}')
        return await m.reply(quote=True, text=f'{k} ابشر مسحت مجموعة المطور')

    if text == 'تغيير المطور الاساسي':
        if not await devp_pls(m.from_user.id, m.chat.id):
            return
        else:
            await rdb.set(f'{m.chat.id}:setBotowmer:{m.from_user.id}{Dev_Zaid}', 1, ex=600)
            return await m.reply(quote=True, text=f'{k} ارسل يوزر المطور الجديد الحين')

    if text == 'تحديث':
        if await devp_pls(m.from_user.id, m.chat.id):
            await m.reply(quote=True, text=f'{k} تم تحديث الملفات')
            python = sys.executable
            os.execl(python, python, *sys.argv)

    if text == 'الملفات':
        if m.from_user.id == sudo_id:
            text = '——— ملفات السورس ———'
            a = os.listdir('Plugins')
            a.sort()
            count = 1
            for file in a:
                if file.endswith('.py'):
                    text += f'\n{count}) `{file}`'
                    count += 1
            text += f'\n——— @{channel} ———'
            return await m.reply(quote=True, text=text, disable_web_page_preview=True)

    if text == 'اذاعة بالخاص':
        if not await dev2_pls(m.from_user.id, m.chat.id):
            return
        await rdb.set(f'{m.chat.id}:pvBroadcast:{m.from_user.id}{Dev_Zaid}', 1, ex=300)
        return await m.reply(f"{k} ارسل الاذاعة الحين")

    if text == 'اذاعة بالقروبات':
        if not await dev2_pls(m.from_user.id, m.chat.id):
            return
        await rdb.set(f'{m.chat.id}:gpBroadcast:{m.from_user.id}{Dev_Zaid}', 1, ex=300)
        return await m.reply(f"{k} ارسل الاذاعة الحين")

    if text == 'السيرفر' or text == 'معلومات السيرفر':
        if await devp_pls(m.from_user.id, m.chat.id):
            text = '——— SYSTEM INFO ———'
            uname = platform.uname()
            # ⚠️ preserved bug: lsb_release غير مستورد في أي مكان من المشروع
            # الأصلي — سيرفع NameError هنا تماماً كما في الأصل، ويلتقطه
            # safe_handler ويسجّله بدل تعطّل غير متحكَّم به.
            version = lsb_release.get_distro_information()['DESCRIPTION']
            text += f"\n{k} النظام : {uname.system}"
            text += f"\n{k} الاصدار: `{version}`"
            text += '\n——— R.A.M INFO ———'
            svmem = psutil.virtual_memory()
            text += f"\n{k} رامات السيرفر: ` {get_size(svmem.total)}`"
            text += f"\n{k} المستهلك: ` {get_size(svmem.used)}/{get_size(svmem.available)}`"
            text += f"\n{k} نسبة الاستهلاك: `{svmem.percent}%`"
            text += '\n——— HARD DISK ———'
            hard = psutil.disk_partitions()[0]
            usage = psutil.disk_usage(hard.mountpoint)
            text += f"\n{k} ذاكرة التخزين: `{get_size(usage.total)}`"
            text += f"\n{k} المستهلك: `{get_size(usage.used)}`"
            text += f"\n{k} نسبة الاستهلاك: `{usage.percent}%`"
            text += '\n——— U.P T.I.M.E ———'
            uptime = time.strftime('%dD - %HH - %MM - %Ss', time.gmtime(time.time() - psutil.boot_time()))
            text += f'\n{uptime}'
            text += '\n\n༄'
            return await m.reply(quote=True, text=text, disable_web_page_preview=True)

    if text == 'جلب نسخة القروبات' and await devp_pls(m.from_user.id, m.chat.id):
        list_ = []
        date = datetime.now()
        for chat in await rdb.smembers(f'enablelist:{Dev_Zaid}'):
            list_.append(int(chat))
        with open(f'{date}.json', 'w+') as w:
            w.write(json.dumps({"botUsername": botUsername, "botID": c.me.id, "Chats": list_}, indent=4, ensure_ascii=False))
        await m.reply_document(f'{date}.json', quote=True)
        os.remove(f'{date}.json')

    if text == 'جلب نسخة المستخدمين' and await devp_pls(m.from_user.id, m.chat.id):
        list_ = []
        date = datetime.now()
        for chat in await rdb.smembers(f'{Dev_Zaid}:UsersList'):
            list_.append(int(chat))
        with open(f'{date}.json', 'w+') as w:
            w.write(json.dumps({"botUsername": botUsername, "botID": c.me.id, "Users": list_}, indent=4, ensure_ascii=False))
        await m.reply_document(f'{date}.json', quote=True)
        os.remove(f'{date}.json')

    if text == 'المكتومين عام':
        if not await dev_pls(m.from_user.id, m.chat.id):
            return await m.reply(quote=True, text=f'{k} هذا الأمر يخص ( Dev²🎖️ وفوق ) بس')
        else:
            if not await rdb.smembers(f'listMUTE:{Dev_Zaid}'):
                return await m.reply(quote=True, text=f'{k} مافيه مكتومين عام')
            else:
                text = '- المكتومين عام:\n\n'
                count = 1
                for PRE in await rdb.smembers(f'listMUTE:{Dev_Zaid}'):
                    if count == 101:
                        break
                    try:
                        user = await c.get_users(int(PRE))
                        mention = user.mention
                        id = user.id
                        username = user.username
                        if user.username:
                            text += f'{count} ➣ @{username} ࿓ ( `{id}` )\n'
                        else:
                            text += f'{count} ➣ {mention} ࿓ ( `{id}` )\n'
                        count += 1
                    except Exception as e:
                        logging.exception(e)
                        mention = f'[@{channel}](tg://user?id={int(PRE)})'
                        id = int(PRE)
                        text += f'{count} ➣ {mention} ࿓ ( `{id}` )\n'
                        count += 1
                text += '\n☆'
                await m.reply(quote=True, text=text)

    if text.startswith('رابط ') and await dev2_pls(m.from_user.id, m.chat.id):
        try:
            id = int(text.split()[1])
            gg = await c.get_chat(id)
            await m.reply(quote=True, text=f'[{gg.title}]({gg.invite_link})', disable_web_page_preview=True)
        except Exception as e:
            logging.exception(e)
            print(e)


async def aexec(code, client, message):
    exec(
        "async def __aexec(client, message): "
        + "".join(f"\n {a}" for a in code.split("\n"))
    )
    return await locals()["__aexec"](client, message)


@register("sudo_eval")
@Client.on_message(filters.command("eval") & filters.user(sudo_id))
@safe_handler
async def executor(client, message):
    if len(message.command) < 2 and not message.reply_to_message:
        return await message.reply("» هات أمر عشان انفذ !")
    if len(message.command) >= 2:
        cmd = message.text.split(None, 1)[1]
    else:
        cmd = message.reply_to_message.text
    old_stderr = sys.stderr
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    redirected_error = sys.stderr = StringIO()
    stdout, stderr, exc = None, None, None
    try:
        await aexec(cmd, client, message)
    except Exception:
        exc = traceback.format_exc()
    stdout = redirected_output.getvalue()
    stderr = redirected_error.getvalue()
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    evaluation = ""
    if exc:
        evaluation = exc
    elif stderr:
        evaluation = stderr
    elif stdout:
        evaluation = stdout
    else:
        evaluation = "SUCCESS"
    final_output = f"`OUTPUT:`\n\n```{evaluation.strip()}```"
    if len(final_output) > 4096:
        filename = "output.txt"
        with open(filename, "w+", encoding="utf8") as out_file:
            out_file.write(str(evaluation.strip()))

        await message.reply_document(
            document=filename,
            caption=f"`INPUT:`\n`{cmd[0:980]}`\n\n`OUTPUT:`\n`attached document`",
            quote=False
        )
        await message.delete()
        os.remove(filename)
    else:
        await message.reply(final_output)


tio = Tio()
langslist = tio.query_languages()
langs_list_link = "https://amanoteam.com/etc/langs.html"

strings_tio = {
    "code_exec_tio_res_string_no_err": "<b>Language:</b> <code>{langformat}</code>\n\n<b>Code:</b>\n<code>{codeformat}</code>\n\n<b>Results:</b>\n<code>{resformat}</code>\n\n<b>Stats:</b><code>{statsformat}</code>",
    "code_exec_tio_res_string_err": "<b>Language:</b> <code>{langformat}</code>\n\n<b>Code:</b>\n<code>{codeformat}</code>\n\n<b>Results:</b>\n<code>{resformat}</code>\n\n<b>Errors:</b>\n<code>{errformat}</code>",
    "code_exec_err_string": "Error: The language <b>{langformat}</b> was not found. Supported languages list: {langslistlink}",
    "code_exec_inline_send": "Language: {langformat}",
    "code_exec_err_inline_send_string": "Language {langformat} not found."
}


@register("sudo_tio_exec")
@Client.on_message(filters.command("exec") & filters.user(sudo_id))
@safe_handler
async def exec_tio_run_code(c: Client, m):
    execlanguage = m.command[1]
    codetoexec = m.text.split(None, 2)[2]
    if execlanguage in langslist:
        tioreq = TioRequest(lang=execlanguage, code=codetoexec)
        loop = asyncio.get_event_loop()
        sendtioreq = await loop.run_in_executor(None, tio.send, tioreq)
        tioerrres = sendtioreq.error or "None"
        tiores = sendtioreq.result or "None"
        tioresstats = sendtioreq.debug.decode() or "None"
        if sendtioreq.error is None:
            await m.reply_text(
                strings_tio["code_exec_tio_res_string_no_err"].format(
                    langformat=execlanguage,
                    codeformat=html.escape(codetoexec),
                    resformat=html.escape(tiores),
                    statsformat=tioresstats,
                )
            )
        else:
            await m.reply_text(
                strings_tio["code_exec_tio_res_string_err"].format(
                    langformat=execlanguage,
                    codeformat=html.escape(codetoexec),
                    resformat=html.escape(tiores),
                    errformat=html.escape(tioerrres),
                )
            )
    else:
        await m.reply_text(
            strings_tio["code_exec_err_string"].format(
                langformat=execlanguage, langslistlink=langs_list_link
            )
        )


@register("sudo_cmd")
@Client.on_message(filters.command("cmd") & filters.user(sudo_id))
@safe_handler
async def run_cmd(c: Client, m):
    cmd = m.text.split(None, 1)[1]
    if re.match("(?i)poweroff|halt|shutdown|reboot", cmd):
        res = "You can't use this command"
    else:
        stdout, stderr = await shell_exec(cmd)

        res = (
            f"<b>Output:</b>\n<code>{html.escape(stdout)}</code>" if stdout else ""
        ) + (f"\n<b>Errors:</b>\n<code>{stderr}</code>" if stderr else "")
    await m.reply_text(res)


@register("sudo_print")
@Client.on_message(filters.command("print") & filters.user(sudo_id))
@safe_handler
async def printSS(c: Client, m):
    text = m.text.split()[1]
    try:
        res = await meval(text, globals(), **locals())
    except BaseException:
        ev = traceback.format_exc()
        await m.reply_text(f"<code>{html.escape(ev)}</code>")
    else:
        try:
            await m.reply_text(f"<code>{html.escape(str(res))}</code>")
        except BaseException as e:
            logging.exception(e)
            await m.reply_text(str(e))


strings_print = {
    "print_description": "Take a screenshot of the specified website.",
    "print_usage": "<b>Usage:</b> <code>/print https://example.com</code> - Take a screenshot of the specified website.",
    "taking_screenshot": "Taking screenshot..."
}


@register("sudo_screenshot")
@Client.on_message(filters.command(["sc", "webs", "ss"]) & filters.user(sudo_id))
@safe_handler
async def printsSites(c: Client, message):
    msg = message.text
    the_url = msg.split(" ", 1)
    wrong = False

    if len(the_url) == 1:
        if message.reply_to_message:
            the_url = message.reply_to_message.text
            if len(the_url) == 1:
                wrong = True
            else:
                the_url = the_url[1]
        else:
            wrong = True
    else:
        the_url = the_url[1]

    if wrong:
        await message.reply_text(strings_print["print_usage"])
        return

    try:
        sent = await message.reply_text(strings_print["taking_screenshot"])
        res_json = await cssworker_url(target_url=the_url)
    except BaseException as e:
        logging.exception(e)
        await message.reply(f"<b>Failed due to:</b> <code>{e}</code>")
        return

    if res_json:
        image_url = res_json["url"]
        if image_url:
            try:
                await message.reply_photo(image_url)
                await sent.delete()
            except BaseException as e:
                logging.exception(e)
                return
        else:
            await message.reply(
                "Couldn't get url value, most probably API is not accessible."
            )
    else:
        await message.reply("Failed because API is not responding, try again later.")
