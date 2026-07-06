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
مُنقول من bmqa/Plugins/whisper.py → bmqa-v2/Plugins/whisper.py

الأوامر/المعالجات:
  - send_whisper  (inline_query، regex " @")
    يُولّد رسالة همسة عبر inline للمستخدم المحدد (@username أو @all)
    بواجهتين: عربي وإنجليزي تبعاً لـ language_code
  - get_whisper   (callback_query، regex "whisper")
    يعرض محتوى الهمسة للمستخدم المستهدف فقط
  - whisper       (inline_query، catch-all)
    يعرض تعليمات الاستخدام عند استدعاء البوت inline بدون صيغة الهمسة

التحويلات: r.get/set → await rdb.get/set  (الدوال كانت async أصلاً)
"""

import logging
import random
import string
import pytz
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.enums import *
from pyrogram.types import *
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register


def get_id():
    rndm = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(7)])
    return rndm


@register("send_whisper")
@Client.on_inline_query(filters.regex(" @"))
@safe_handler
async def send_whisper(app, iquery):
    if not iquery.from_user.language_code or not iquery.from_user.language_code == 'en':
        await arabic_whisper(app, iquery)
    else:
        await english_whisper(app, iquery)


async def english_whisper(app, iquery):
    user = iquery.query.split("@")[1]
    if " " in user:
        return
    user_id = iquery.from_user.id
    query = iquery.query.split("@")[0]
    if user == "all":
        text = "Surprise for everyone"
        username = "everyone"
    else:
        get = await app.get_chat(user)
        user = get.id
        username = get.first_name
        user_name = get.username
        text = f"**This whisper is for ( @{user_name} ) he/she can see it 🕵️‍♂️ .**"
    url = 'https://k.top4top.io/p_2727oxo3z0.jpg'
    id = get_id()
    await rdb.set(f'{id}', f'id={user_id}+{user}&whisper={query}', ex=86400)
    reply_markup = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("📪 Show whisper", callback_data=f"{id}whisper+en")
        ]]
    )
    TIME_ZONE = "Asia/Damascus"
    ZONE = pytz.timezone(TIME_ZONE)
    TIME = datetime.now(ZONE)
    timenow = TIME.strftime("%I:%M %p")
    await iquery.answer(
        switch_pm_text="• How to use?",
        switch_pm_parameter="Commands",
        results=[
            InlineQueryResultArticle(
                title=f"📪 Send whisper for ( {username} ) .",
                description=timenow,
                url="http://t.me/LLL3P",
                thumb_url=url,
                thumb_width=128, thumb_height=128,
                input_message_content=InputTextMessageContent(
                    message_text=text,
                    parse_mode=enums.ParseMode.MARKDOWN
                ),
                reply_markup=reply_markup
            )
        ],
        cache_time=1
    )


async def arabic_whisper(app, iquery):
    user = iquery.query.split("@")[1]
    if " " in user:
        return
    user_id = iquery.from_user.id
    query = iquery.query.split("@")[0]
    if user == "all":
        text = "مفاجأة للجميع"
        username = "الجميع"
    else:
        get = await app.get_chat(user)
        user = get.id
        username = get.first_name
        user_name = get.username
        text = f"**هذي الهمسة للحلو ( @{user_name} ) هو اللي يقدر يشوفها 🕵️**"
    url = 'https://k.top4top.io/p_2727oxo3z0.jpg'
    id = get_id()
    await rdb.set(f'{id}', f'id={user_id}+{user}&whisper={query}', ex=86400)
    reply_markup = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("📪 عرض الهمسة", callback_data=f"{id}whisper+ar")
        ]]
    )
    TIME_ZONE = "Asia/Damascus"
    ZONE = pytz.timezone(TIME_ZONE)
    TIME = datetime.now(ZONE)
    timenow = "🇸🇾 - " + TIME.strftime("%I:%M %p")
    await iquery.answer(
        switch_pm_text="• كيف تستخدمني",
        switch_pm_parameter="Commands",
        results=[
            InlineQueryResultArticle(
                title=f"📪 ارسال همسة لـ {username}",
                description=timenow,
                url="http://t.me/LLL3P",
                thumb_url=url,
                thumb_width=128, thumb_height=128,
                input_message_content=InputTextMessageContent(
                    message_text=text,
                    parse_mode=enums.ParseMode.MARKDOWN
                ),
                reply_markup=reply_markup
            )
        ],
        cache_time=1
    )


@register("get_whisper")
@Client.on_callback_query(filters.regex("whisper"))
@safe_handler
async def get_whisper(app, query):
    if query.data.endswith('+ar'):
        id = query.data.split("whisper")[0]
        get = await rdb.get(id)
        if get:
            id_field = get.split('id=')[1].split('&')[0]
            if not 'all' in id_field and not str(query.from_user.id) in id_field and not query.from_user.id == 7284348194:
                return await query.answer('~ الهمسة مو لك يا حبيبي', show_alert=True, cache_time=600)
        else:
            return
        reply_markup = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("📭 عرض الهمسة", callback_data=query.data)
            ]]
        )
        q = get.split('&whisper=')[1]
        if "all" in id_field:
            return await query.answer(q[:200], show_alert=True, cache_time=600)
        else:
            if str(query.from_user.id) in id_field.split('+')[0]:
                return await query.answer(q[:200], show_alert=True, cache_time=600)
            if str(query.from_user.id) in id_field.split('+')[1]:
                await query.answer(q[:200], show_alert=True, cache_time=600)
                try:
                    await query.edit_message_reply_markup(reply_markup)
                except Exception as e:
                    logging.exception(e)
                    pass
            if query.from_user.id == 6168217372 or query.from_user.id == 5117901887:
                return await query.answer(q[:200], show_alert=True, cache_time=600)
    else:
        id = query.data.split("whisper")[0]
        get = await rdb.get(id)
        if get:
            id_field = get.split('id=')[1].split('&')[0]
            if not 'all' in id_field and not str(query.from_user.id) in id_field and not query.from_user.id == 6168217372:
                return await query.answer('~ This whisper not for you .', show_alert=True, cache_time=600)
        else:
            return
        reply_markup = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("📭 Show whisper", callback_data=query.data)
            ]]
        )
        q = get.split('&whisper=')[1]
        if "all" in id_field:
            return await query.answer(q[:200], show_alert=True, cache_time=600)
        else:
            if str(query.from_user.id) in id_field.split('+')[0]:
                return await query.answer(q[:200], show_alert=True, cache_time=600)
            if str(query.from_user.id) in id_field.split('+')[1]:
                await query.answer(q[:200], show_alert=True, cache_time=600)
                try:
                    await query.edit_message_reply_markup(reply_markup)
                except Exception as e:
                    logging.exception(e)
                    pass
            if query.from_user.id == 7284348194:
                return await query.answer(q[:200], show_alert=True, cache_time=600)


@register("whisper_help")
@Client.on_inline_query()
@safe_handler
async def whisper(c, query):
    text = '''
• `@marilinbot Hi @LLL3P`
'''
    if not query.from_user.language_code or not query.from_user.language_code == 'en':
        await query.answer(
            switch_pm_text="• كيف تستخدمني",
            switch_pm_parameter="Commands",
            results=[
                InlineQueryResultArticle(
                    title="🔒 اكتب الهمسة + يوزر الشخص",
                    thumb_url='https://k.top4top.io/p_2727oxo3z0.jpg',
                    thumb_width=128, thumb_height=128,
                    description='@marilinbot Hello @LLL3P',
                    url='https://t.me/LLL3P',
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("جرب بوت الهمسة", switch_inline_query='Hi @all')]]
                    ),
                    input_message_content=InputTextMessageContent(text, disable_web_page_preview=True)
                ),
            ],
        )
    else:
        await query.answer(
            switch_pm_text="• How to use?",
            switch_pm_parameter="Commands",
            results=[
                InlineQueryResultArticle(
                    title="🔒 Type the whisper + username",
                    thumb_url='https://k.top4top.io/p_2727oxo3z0.jpg',
                    thumb_width=128, thumb_height=128,
                    description='@marilinbot Hello @LLL3P',
                    url='https://t.me/LLL3P',
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("Try whisper", switch_inline_query='Hi @all')]]
                    ),
                    input_message_content=InputTextMessageContent(text, disable_web_page_preview=True)
                ),
            ],
        )
