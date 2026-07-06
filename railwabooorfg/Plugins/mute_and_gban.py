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
مُنقول من bmqa/Plugins/mute_and_gban.py → bmqa-v2/Plugins/mute_and_gban.py

التحويلات:
  - Thread(target=mute_func, args=(c, m, k)).start() → await مباشر لدالة
    async واحدة (mute_func أصبحت async def)، بنفس فكرة تحويل Thread المتّبعة
    في كل الملفات المنقولة سابقاً (راجع global_filters.py).
  - نفس الشيء لـ mutesHandlerG → mute_funcg، وmuteResponse → del_formutes.
  - كل r.<op> → await rdb.<op> (راجع core/db.py).
  - admin_pls/mod_pls/pre_pls/dev_pls/isLockCommand/get_rank من helpers.Ranks
    (متزامنة في الأصل) → من helpers.ranks، وأصبحت async فأُضيف await قبل كل
    استدعاء لها (بدون أي تغيير في القيمة المُعادة أو منطق المقارنة).
  - time.sleep(x.value) في del_formutes (بند صريح من الطلب) → asyncio.sleep(x.value).
  - c.get_chat(...) → await c.get_chat(...)، m.reply(...) → await m.reply(...)،
    m.chat.ban_member(...) → await m.chat.ban_member(...)، m.delete() → await m.delete().
  - @register + @safe_handler مُضافان فوق الثلاث handlers الرئيسية
    (مثل كل Plugin آخر منقول)؛ safe_handler طبقة حماية إضافية خارجية فقط —
    لا تُغيّر السلوك الداخلي لـ del_formutes الذي يمسك FloodWait بنفسه صراحة
    عند m.delete() (نفس try/except الأصلي بالضبط، فقط time.sleep → asyncio.sleep).
  - import محدّد بدل wildcard.

⚠️ كل شروط التحقق من الصلاحيات (admin_pls / mod_pls / pre_pls / dev_pls) وكل
النصوص المُرسلة للمستخدم (بما فيها الاختلافات الطفيفة الأصلية بين الرسائل،
مثل "هذا الامر يخص" مقابل "هذا الأمر يخص"، واختلاف الرتبة المطلوبة بين أمر
وآخر حتى لو بدت متشابهة) نُقلت حرفياً دون أي تعديل أو "تصحيح" — فقط إضافة
await حيث يلزم.
"""

import logging
import asyncio
import re

from pyrogram import Client, filters
from pyrogram.errors import FloodWait

from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from helpers.ranks import admin_pls, mod_pls, pre_pls, dev_pls, get_rank, isLockCommand


@register("mute_and_gban_text")
@Client.on_message(filters.text & filters.group, group=14)
@safe_handler
async def mutesHandler(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')
    await mute_func(c, m, k)


async def mute_func(c, m, k):
    if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not await admin_pls(m.from_user.id, m.chat.id):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}'):
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

    if await isLockCommand(m.from_user.id, m.chat.id, text):
        return

    if text == 'كتم' and m.reply_to_message and m.reply_to_message.from_user:
        id = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( المدير وفوق ) بس')
        if id == m.from_user.id:
            return await m.reply('شفيك تبي تنزل نفسك')
        if await pre_pls(id, m.chat.id):
            rank = await get_rank(id, m.chat.id)
            return await m.reply(f'{k} هييه مايمديك تكتم {rank} يورع!')
        if await rdb.get(f'{id}:mute:{m.chat.id}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مكتوم من قبل\n☆')
        else:
            await rdb.set(f'{id}:mute:{m.chat.id}{Dev_Zaid}', 1)
            await rdb.sadd(f'{m.chat.id}:listMUTE:{Dev_Zaid}', id)
            return await m.reply(f'「 {mention} 」\n{k} كتمته\n☆')

    if re.match("^كتم عام (.*?)$", text) and len(text.split()) == 3:
        if not '@' in text and not re.findall('[0-9]+', text):
            return
        if not await dev_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( المطور وفوق ) بس')
        user = text.split()[2]
        try:
            id = int(user)
        except Exception as e:
            logging.exception(e)
            id = user.replace('@', '')
        try:
            get = await c.get_chat(user)
            mention = f'[{get.first_name}](tg://user?id={get.id})'
            id = get.id
        except Exception as e:
            logging.exception(e)
            return await m.reply(f'{k} مافيه يوزر كذا')
        if await dev_pls(id, m.chat.id):
            rank = await get_rank(id, m.chat.id)
            return await m.reply(f'{k} هييه مايمديك تكتم {rank} يورع!')
        if await rdb.get(f'{id}:mute:{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مكتوم عام من قبل\n☆')
        else:
            await rdb.set(f'{id}:mute:{Dev_Zaid}', 1)
            await rdb.sadd(f'listMUTE:{Dev_Zaid}', id)
            return await m.reply(f'「 {mention} 」\n{k} كتمته عام\n☆')

    if re.match("^كتم (.*?)$", text) and len(text.split()) == 2:
        if not '@' in text and not re.findall('[0-9]+', text):
            return
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
        user = text.split()[1]
        try:
            id = int(user)
        except Exception as e:
            logging.exception(e)
            id = user.replace('@', '')
        try:
            get = await c.get_chat(user)
            mention = f'[{get.first_name}](tg://user?id={get.id})'
            id = get.id
        except Exception as e:
            logging.exception(e)
            return await m.reply(f'{k} مافيه يوزر كذا')
        if id == m.from_user.id:
            return await m.reply('شفيك تبي تنزل نفسك')
        if await rdb.get(f'{id}:mute:{m.chat.id}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مكتوم من قبل\n☆')
        if await pre_pls(id, m.chat.id):
            rank = await get_rank(id, m.chat.id)
            return await m.reply(f'{k} هييه مايمديك تكتم {rank} يورع!')
        await rdb.set(f'{id}:mute:{m.chat.id}{Dev_Zaid}', 1)
        await rdb.sadd(f'{m.chat.id}:listMUTE:{Dev_Zaid}', id)
        return await m.reply(f'「 {mention} 」\n{k} كتمته\n☆')

    if text == 'الغاء الكتم' and m.reply_to_message and m.reply_to_message.from_user:
        id = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
        if not await rdb.get(f'{id}:mute:{m.chat.id}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مو مكتوم قبل\n☆')
        else:
            await rdb.delete(f'{id}:mute:{m.chat.id}{Dev_Zaid}')
            await rdb.srem(f'{m.chat.id}:listMUTE:{Dev_Zaid}', id)
            return await m.reply(f'「 {mention} 」\n{k} ابشر الغيت كتمه\n༄')

    if re.match("^الغاء الكتم العام (.*?)$", text) and len(text.split()) == 4:
        if not '@' in text and not re.findall('[0-9]+', text):
            return
        if not await dev_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الأمر يخص ( Dev²🎖️ وفوق ) بس')
        user = text.split()[3]
        try:
            id = int(user)
        except Exception as e:
            logging.exception(e)
            id = user.replace('@', '')
        try:
            get = await c.get_chat(user)
            mention = f'[{get.first_name}](tg://user?id={get.id})'
            id = get.id
        except Exception as e:
            logging.exception(e)
            id = re.findall('[0-9]+', text)[0] if re.findall('[0-9]+', text) else None
            if not id:
                return await m.reply(f"{k} مافيه يوزر كذا")
            mention = f'[{id}](tg://user?id={id})'
        if not await rdb.get(f'{id}:mute:{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مو مكتوم عام من قبل\n☆')
        else:
            await rdb.delete(f'{id}:mute:{Dev_Zaid}')
            await rdb.srem(f'listMUTE:{Dev_Zaid}', id)
            return await m.reply(f'「 {mention} 」\n{k} لغيت كتمته عام\n☆')

    if re.match("^الغاء الكتم (.*?)$", text) and len(text.split()) == 3:
        if not '@' in text and not re.findall('[0-9]+', text):
            return
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( المدير وفوق ) بس')
        user = text.split()[2]
        try:
            id = int(user)
        except Exception as e:
            logging.exception(e)
            id = user.replace('@', '')
        try:
            get = await c.get_chat(user)
            mention = f'[{get.first_name}](tg://user?id={get.id})'
            id = get.id
        except Exception as e:
            logging.exception(e)
            id = re.findall('[0-9]+', text)[0] if re.findall('[0-9]+', text) else None
            if not id:
                return await m.reply(f"{k} مافيه يوزر كذا")
            mention = f'[{id}](tg://user?id={id})'
        if not await rdb.get(f'{id}:mute:{m.chat.id}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مو مكتوم من قبل\n☆')
        await rdb.delete(f'{id}:mute:{m.chat.id}{Dev_Zaid}')
        await rdb.srem(f'{m.chat.id}:listMUTE:{Dev_Zaid}', id)
        return await m.reply(f'「 {mention} 」\n{k} ابشر الغيت كتمه\n☆')

    if re.match("^حظر عام (.*?)$", text) and len(text.split()) == 3:
        if not '@' in text and not re.findall('[0-9]+', text):
            return
        if not await dev_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( المطور وفوق ) بس')
        user = text.split()[2]
        try:
            id = int(user)
        except Exception as e:
            logging.exception(e)
            id = user.replace('@', '')
        try:
            get = await c.get_chat(user)
            mention = f'[{get.first_name}](tg://user?id={get.id})'
            id = get.id
        except Exception as e:
            logging.exception(e)
            return await m.reply(f'{k} مافيه يوزر كذا')
        if await dev_pls(id, m.chat.id):
            rank = await get_rank(id, m.chat.id)
            return await m.reply(f'{k} هييه مايمديك تحظر {rank} يورع!')
        if await rdb.get(f'{id}:gban:{Dev_Zaid}'):
            return await m.reply(f'{k} الحمار「 {mention} 」\n{k} محظور عام من قبل\n☆')
        else:
            await rdb.set(f'{id}:gban:{Dev_Zaid}', 1)
            await rdb.sadd(f'listGBAN:{Dev_Zaid}', id)
            return await m.reply(f'{k} الحمار「 {mention} 」\n{k} حظرته عام\n☆')

    if re.match("^حظر عام من الالعاب (.*?)$", text) and len(text.split()) == 5:
        if not '@' in text and not re.findall('[0-9]+', text):
            return
        if not await dev_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الأمر يخص ( Dev²🎖️ وفوق ) بس')
        user = text.split()[4]
        try:
            id = int(user)
        except Exception as e:
            logging.exception(e)
            id = user.replace('@', '')
        try:
            get = await c.get_chat(user)
            mention = f'[{get.first_name}](tg://user?id={get.id})'
            id = get.id
        except Exception as e:
            logging.exception(e)
            return await m.reply(f'{k} مافيه يوزر كذا')
        if await dev_pls(id, m.chat.id):
            rank = await get_rank(id, m.chat.id)
            return await m.reply(f'{k} هييه مايمديك تحظر {rank} يورع!')
        if await rdb.get(f'{id}:gbangames:{Dev_Zaid}'):
            return await m.reply(f'{k} الحمار「 {mention} 」\n{k} محظور من الالعاب من قبل\n☆')
        else:
            await rdb.set(f'{id}:gbangames:{Dev_Zaid}', 1)
            await rdb.sadd(f'listGBANGAMES:{Dev_Zaid}', id)
            await rdb.delete(f'{id}:Floos')
            await rdb.srem("BankList", id)
            return await m.reply(f'{k} الحمار「 {mention} 」\n{k} حظرته عام من الالعاب\n☆')

    if re.match("^الغاء الحظر العام من الالعاب (.*?)$", text) and len(text.split()) == 6:
        if not '@' in text and not re.findall('[0-9]+', text):
            return
        if not await dev_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الأمر يخص ( Dev²🎖️ وفوق ) بس')
        user = text.split()[5]
        try:
            id = int(user)
        except Exception as e:
            logging.exception(e)
            id = user.replace('@', '')
        try:
            get = await c.get_chat(user)
            mention = f'[{get.first_name}](tg://user?id={get.id})'
            id = get.id
        except Exception as e:
            logging.exception(e)
            id = re.findall('[0-9]+', text)[0] if re.findall('[0-9]+', text) else None
            if not id:
                return await m.reply(f"{k} مافيه يوزر كذا")
            mention = f'[{id}](tg://user?id={id})'
        if not await rdb.get(f'{id}:gbangames:{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مو محظور من الالعاب من قبل\n☆')
        else:
            await rdb.delete(f'{id}:gbangames:{Dev_Zaid}')
            await rdb.srem(f'listGBANGAMES:{Dev_Zaid}', id)
            return await m.reply(f'「 {mention} 」\n{k} لغيت حظره من الالعاب عام\n☆')

    if re.match("^الغاء الحظر العام (.*?)$", text) and len(text.split()) == 4:
        if not '@' in text and not re.findall('[0-9]+', text):
            return
        if not await dev_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الأمر يخص ( Dev²🎖️ وفوق ) بس')
        user = text.split()[3]
        try:
            id = int(user)
        except Exception as e:
            logging.exception(e)
            id = user.replace('@', '')
        try:
            get = await c.get_chat(user)
            mention = f'[{get.first_name}](tg://user?id={get.id})'
            id = get.id
        except Exception as e:
            logging.exception(e)
            id = re.findall('[0-9]+', text)[0] if re.findall('[0-9]+', text) else None
            if not id:
                return await m.reply(f"{k} مافيه يوزر كذا")
            mention = f'[{id}](tg://user?id={id})'
        if not await rdb.get(f'{id}:gban:{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مو محظور عام من قبل\n☆')
        else:
            await rdb.delete(f'{id}:gban:{Dev_Zaid}')
            await rdb.srem(f'listGBAN:{Dev_Zaid}', id)
            return await m.reply(f'「 {mention} 」\n{k} لغيت حظره عام\n☆')


@register("mute_and_gban_cleanup")
@Client.on_message(filters.group, group=15)
@safe_handler
async def muteResponse(c, m):
    await del_formutes(c, m)


async def del_formutes(c, m):
    if await rdb.get(f'{m.from_user.id}:gban:{Dev_Zaid}'):
        try:
            await m.chat.ban_member(m.from_user.id)
        except Exception as e:
            logging.exception(e)
            await m.delete()
    if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}') or await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):
        try:
            await m.delete()
        except FloodWait as x:
            logging.exception(x)
            await asyncio.sleep(x.value)
        except Exception as e:
            logging.exception(e)
            pass


@register("mute_and_gban_reply")
@Client.on_message(filters.text & filters.group, group=16)
@safe_handler
async def mutesHandlerG(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')
    await mute_funcg(c, m, k)


async def mute_funcg(c, m, k):
    if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not await admin_pls(m.from_user.id, m.chat.id):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}'):
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

    if text == 'كتم عام' and m.reply_to_message and m.reply_to_message.from_user:
        if not await dev_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الأمر يخص ( Dev²🎖️ وفوق ) بس')
        id = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if await dev_pls(id, m.chat.id):
            rank = await get_rank(id, m.chat.id)
            return await m.reply(f'{k} هييه مايمديك تكتم {rank} يورع!')
        if await rdb.get(f'{id}:mute:{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مكتوم عام من قبل\n☆')
        else:
            await rdb.set(f'{id}:mute:{Dev_Zaid}', 1)
            await rdb.sadd(f'listMUTE:{Dev_Zaid}', id)
            return await m.reply(f'「 {mention} 」\n{k} كتمته عام\n☆')

    if text == 'حظر عام' and m.reply_to_message and m.reply_to_message.from_user:
        if not await dev_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الأمر يخص ( Dev²🎖️ وفوق ) بس')
        id = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if await dev_pls(id, m.chat.id):
            rank = await get_rank(id, m.chat.id)
            return await m.reply(f'{k} هييه مايمديك تحظر {rank} يورع!')
        if await rdb.get(f'{id}:gban:{Dev_Zaid}'):
            return await m.reply(f'{k} الحمار「 {mention} 」\n{k} محظور عام من قبل\n☆')
        else:
            await rdb.set(f'{id}:gban:{Dev_Zaid}', 1)
            await rdb.sadd(f'listGBAN:{Dev_Zaid}', id)
            return await m.reply(f'{k} الحمار「 {mention} 」\n{k} حظرته عام\n☆')

    if text == 'حظر عام من الالعاب' and m.reply_to_message and m.reply_to_message.from_user:
        if not await dev_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( المطور وفوق ) بس')
        id = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if await dev_pls(id, m.chat.id):
            rank = await get_rank(id, m.chat.id)
            return await m.reply(f'{k} هييه مايمديك تحظر {rank} يورع!')
        if await rdb.get(f'{id}:gbangames:{Dev_Zaid}'):
            return await m.reply(f'{k} الحمار「 {mention} 」\n{k} محظور من الالعاب من قبل\n☆')
        else:
            await rdb.set(f'{id}:gbangames:{Dev_Zaid}', 1)
            await rdb.sadd(f'listGBANGAMES:{Dev_Zaid}', id)
            await rdb.delete(f'{id}:Floos')
            await rdb.srem("BankList", id)
            return await m.reply(f'{k} الحمار「 {mention} 」\n{k} حظرته عام من الالعاب\n☆')

    if text == 'الغاء الكتم العام' and m.reply_to_message and m.reply_to_message.from_user:
        if not await dev_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( المطور وفوق ) بس')
        id = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if await dev_pls(id, m.chat.id):
            rank = await get_rank(id, m.chat.id)
            return await m.reply(f'{k} هييه مايمديك تكتم {rank} يورع!')
        if not await rdb.get(f'{id}:mute:{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مو مكتوم عام من قبل\n☆')
        else:
            await rdb.delete(f'{id}:mute:{Dev_Zaid}')
            await rdb.srem(f'listMUTE:{Dev_Zaid}', id)
            return await m.reply(f'「 {mention} 」\n{k} لغيت كتمته عام\n☆')

    if text == 'الغاء الحظر العام من الالعاب' and m.reply_to_message and m.reply_to_message.from_user:
        if not await dev_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الأمر يخص ( Dev²🎖️ وفوق ) بس')
        id = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if await dev_pls(id, m.chat.id):
            rank = await get_rank(id, m.chat.id)
            return await m.reply(f'{k} هييه مايمديك تكتم {rank} يورع!')
        if not await rdb.get(f'{id}:gbangames:{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مو محظور من الالعاب من قبل\n☆')
        else:
            await rdb.delete(f'{id}:gbangames:{Dev_Zaid}')
            await rdb.srem(f'listGBANGAMES:{Dev_Zaid}', id)
            return await m.reply(f'「 {mention} 」\n{k} لغيت حظره من الالعاب\n☆')

    if text == 'الغاء الحظر العام' and m.reply_to_message and m.reply_to_message.from_user:
        if not await dev_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الأمر يخص ( Dev²🎖️ وفوق ) بس')
        id = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if await dev_pls(id, m.chat.id):
            rank = await get_rank(id, m.chat.id)
            return await m.reply(f'{k} هييه مايمديك تكتم {rank} يورع!')
        if not await rdb.get(f'{id}:gban:{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مو محظور عام من قبل\n☆')
        else:
            await rdb.delete(f'{id}:gban:{Dev_Zaid}')
            await rdb.srem(f'listGBAN:{Dev_Zaid}', id)
            return await m.reply(f'「 {mention} 」\n{k} لغيت حظره عام\n☆')
