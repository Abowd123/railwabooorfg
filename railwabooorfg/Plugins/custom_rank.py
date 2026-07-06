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
مُعاد تسميته: customRank.py → custom_rank.py
مُنقول من bmqa/Plugins/customRank.py → bmqa-v2/Plugins/custom_rank.py

الأوامر/المعالجات (group=35، text & group):
  - تغيير رتبه | تغيير رتبة  : يطلب اسم الرتبة الأصلية ثم الجديدة
  - مسح رتبه  | مسح رتبة     : يطلب اسم الرتبة ليحذف اسمها المخصص
  - مسح الرتب                 : مسح كل أسماء الرتب المخصصة
  - قائمه الرتب | قائمة الرتب : عرض قائمة الأسماء المخصصة للرتب
  - الغاء                     : إلغاء خطوة تغيير/مسح رتبة جارية

التحويلات:
  - customRank.py (الأصل الـQديم sync) → custom_rank.py async
  - Thread(target=customRankFunc, ...).start() → await customRankFunc(...)
  - r.<op>(...) → await rdb.<op>(...)
  - من helpers.Ranks → من helpers.ranks (حروف صغيرة)
  - أُضيف @register("custom_rank") و @safe_handler للتسجيل والحماية
"""

import re
from pyrogram import Client, filters
from pyrogram.enums import *
from pyrogram.types import *
from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from helpers.ranks import admin_pls, mod_pls, isLockCommand


@register("custom_rank")
@Client.on_message(filters.text & filters.group, group=35)
@safe_handler
async def customrankHandler(c, m):
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

    if text == 'الغاء':
        if (await rdb.get(f'{m.from_user.id}:addRank2:{m.chat.id}{Dev_Zaid}')
                or await rdb.get(f'{m.from_user.id}:addRank:{m.chat.id}{Dev_Zaid}')
                or await rdb.get(f'{m.from_user.id}:delRank:{m.chat.id}{Dev_Zaid}')):
            await m.reply(f'{k} من عيوني لغيت كل شي يخص الرتب')
            await rdb.delete(f'{m.from_user.id}:addRank:{m.chat.id}{Dev_Zaid}')
            await rdb.delete(f'{m.from_user.id}:delRank:{m.chat.id}{Dev_Zaid}')
            await rdb.delete(f'{m.from_user.id}:addRank2:{m.chat.id}{Dev_Zaid}')

    if await rdb.get(f'{m.from_user.id}:addRank2:{m.chat.id}{Dev_Zaid}') and await mod_pls(m.from_user.id, m.chat.id) and len(m.text) <= 20:
        rank = await rdb.get(f'{m.from_user.id}:addRank2:{m.chat.id}{Dev_Zaid}')
        await rdb.delete(f'{m.from_user.id}:addRank2:{m.chat.id}{Dev_Zaid}')
        if rank == 'مالك اساسي':
            if await rdb.get(f'{m.chat.id}:RankGowner:{Dev_Zaid}'):
                rrr = await rdb.get(f'{m.chat.id}:RankGowner:{Dev_Zaid}')
                await rdb.srem(f'{m.chat.id}:ranklist:{Dev_Zaid}', f'{rank}&&newr={rrr}')
                await rdb.delete(f'{m.chat.id}:RankGowner:{Dev_Zaid}')
            await rdb.set(f'{m.chat.id}:RankGowner:{Dev_Zaid}', m.text)
        if rank == 'مالك':
            if await rdb.get(f'{m.chat.id}:RankOwner:{Dev_Zaid}'):
                rrr = await rdb.get(f'{m.chat.id}:RankOwner:{Dev_Zaid}')
                await rdb.srem(f'{m.chat.id}:ranklist:{Dev_Zaid}', f'{rank}&&newr={rrr}')
                await rdb.delete(f'{m.chat.id}:RankOwner:{Dev_Zaid}')
            await rdb.set(f'{m.chat.id}:RankOwner:{Dev_Zaid}', m.text)
        if rank == 'مدير':
            if await rdb.get(f'{m.chat.id}:RankMod:{Dev_Zaid}'):
                rrr = await rdb.get(f'{m.chat.id}:RankMod:{Dev_Zaid}')
                await rdb.srem(f'{m.chat.id}:ranklist:{Dev_Zaid}', f'{rank}&&newr={rrr}')
                await rdb.delete(f'{m.chat.id}:RankMod:{Dev_Zaid}')
            await rdb.set(f'{m.chat.id}:RankMod:{Dev_Zaid}', m.text)
        if rank == 'ادمن':
            if await rdb.get(f'{m.chat.id}:RankAdm:{Dev_Zaid}'):
                rrr = await rdb.get(f'{m.chat.id}:RankAdm:{Dev_Zaid}')
                await rdb.srem(f'{m.chat.id}:ranklist:{Dev_Zaid}', f'{rank}&&newr={rrr}')
                await rdb.delete(f'{m.chat.id}:RankAdm:{Dev_Zaid}')
            await rdb.set(f'{m.chat.id}:RankAdm:{Dev_Zaid}', m.text)
        if rank == 'مميز':
            if await rdb.get(f'{m.chat.id}:RankPre:{Dev_Zaid}'):
                rrr = await rdb.get(f'{m.chat.id}:RankPre:{Dev_Zaid}')
                await rdb.srem(f'{m.chat.id}:ranklist:{Dev_Zaid}', f'{rank}&&newr={rrr}')
                await rdb.delete(f'{m.chat.id}:RankPre:{Dev_Zaid}')
            await rdb.set(f'{m.chat.id}:RankPre:{Dev_Zaid}', m.text)
        if rank == 'عضو':
            if await rdb.get(f'{m.chat.id}:RankMem:{Dev_Zaid}'):
                rrr = await rdb.get(f'{m.chat.id}:RankMem:{Dev_Zaid}')
                await rdb.srem(f'{m.chat.id}:ranklist:{Dev_Zaid}', f'{rank}&&newr={rrr}')
                await rdb.delete(f'{m.chat.id}:RankMem:{Dev_Zaid}')
            await rdb.set(f'{m.chat.id}:RankMem:{Dev_Zaid}', m.text)
        await rdb.sadd(f'{m.chat.id}:ranklist:{Dev_Zaid}', f'{rank}&&newr={m.text}')
        return await m.reply(f'{k} تم غيرت الرتبه الى ( {m.text} )')

    if await rdb.get(f'{m.from_user.id}:addRank:{m.chat.id}{Dev_Zaid}') and await mod_pls(m.from_user.id, m.chat.id):
        await rdb.delete(f'{m.from_user.id}:addRank:{m.chat.id}{Dev_Zaid}')
        if m.text not in ['مالك اساسي', 'مالك', 'مدير', 'ادمن', 'مميز', 'عضو']:
            return await m.reply(f'{k} ركز! الرتبه اللي كتبتها مو موجوده')
        else:
            await rdb.set(f'{m.from_user.id}:addRank2:{m.chat.id}{Dev_Zaid}', m.text, ex=600)
            return await m.reply(f'{k} حلو الحين ارسل الرتبه الجديدة')

    if await rdb.get(f'{m.from_user.id}:delRank:{m.chat.id}{Dev_Zaid}') and await mod_pls(m.from_user.id, m.chat.id):
        await rdb.delete(f'{m.from_user.id}:delRank:{m.chat.id}{Dev_Zaid}')
        if m.text not in ['مالك اساسي', 'مالك', 'مدير', 'ادمن', 'مميز', 'عضو']:
            return await m.reply(f'{k} مافي رتبه زي كذا لازم تكتب الرتبه الاساسيه مثال مالك اساسي مو {m.text[:20]}')
        else:
            rank = m.text
            rank2 = None
            if rank == 'مالك اساسي':
                rank2 = await rdb.get(f'{m.chat.id}:RankGowner:{Dev_Zaid}')
                await rdb.delete(f'{m.chat.id}:RankGowner:{Dev_Zaid}')
            if rank == 'مالك':
                rank2 = await rdb.get(f'{m.chat.id}:RankOwner:{Dev_Zaid}')
                await rdb.delete(f'{m.chat.id}:RankOwner:{Dev_Zaid}')
            if rank == 'مدير':
                rank2 = await rdb.get(f'{m.chat.id}:RankMod:{Dev_Zaid}')
                await rdb.delete(f'{m.chat.id}:RankMod:{Dev_Zaid}')
            if rank == 'ادمن':
                rank2 = await rdb.get(f'{m.chat.id}:RankAdm:{Dev_Zaid}')
                await rdb.delete(f'{m.chat.id}:RankAdm:{Dev_Zaid}')
            if rank == 'مميز':
                rank2 = await rdb.get(f'{m.chat.id}:RankPre:{Dev_Zaid}')
                await rdb.delete(f'{m.chat.id}:RankPre:{Dev_Zaid}')
            if rank == 'عضو':
                rank2 = await rdb.get(f'{m.chat.id}:RankMem:{Dev_Zaid}')
                await rdb.delete(f'{m.chat.id}:RankMem:{Dev_Zaid}')
            await rdb.srem(f'{m.chat.id}:ranklist:{Dev_Zaid}', f'{rank}&&newr={rank2}')
            return await m.reply(f'{k} مسحت رتبه ( {rank2} )')

    if text == 'مسح الرتب':
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الأمر يخص ( المدير وفوق ) بس')
        else:
            if not await rdb.smembers(f'{m.chat.id}:ranklist:{Dev_Zaid}'):
                return await m.reply(f'{k} مافيه رتب مضافة')
            else:
                await m.reply(f'{k} مسحت كل الرتب المضافة')
                await rdb.delete(f'{m.chat.id}:RankGowner:{Dev_Zaid}')
                await rdb.delete(f'{m.chat.id}:RankOwner:{Dev_Zaid}')
                await rdb.delete(f'{m.chat.id}:RankMod:{Dev_Zaid}')
                await rdb.delete(f'{m.chat.id}:RankAdm:{Dev_Zaid}')
                await rdb.delete(f'{m.chat.id}:RankPre:{Dev_Zaid}')
                await rdb.delete(f'{m.chat.id}:RankMem:{Dev_Zaid}')
                return await rdb.delete(f'{m.chat.id}:ranklist:{Dev_Zaid}')

    if text == 'قائمه الرتب' or text == 'قائمة الرتب':
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الأمر يخص ( المدير وفوق ) بس')
        else:
            if not await rdb.smembers(f'{m.chat.id}:ranklist:{Dev_Zaid}'):
                return await m.reply(f'{k} مافيه رتب مضافة')
            else:
                txt = 'قائمة الرتب:\n'
                count = 1
                for rrr in await rdb.smembers(f'{m.chat.id}:ranklist:{Dev_Zaid}'):
                    rank = rrr.split('&&newr=')
                    txt += f'{count}) {rank[0]} ~ ( {rank[1]} )\n'
                    count += 1
                txt += '\n☆'
                return await m.reply(txt, disable_web_page_preview=True)

    if text == 'مسح رتبه' or text == 'مسح رتبة':
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الأمر يخص ( المدير وفوق ) بس')
        else:
            await rdb.set(f'{m.from_user.id}:delRank:{m.chat.id}{Dev_Zaid}', 1, ex=600)
            return await m.reply(f'{k} ارسل اسم الرتبه اللي تبي تمسحها الحين')

    if text == 'تغيير رتبه' or text == 'تغيير رتبة':
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الأمر يخص ( المدير وفوق ) بس')
        else:
            await rdb.set(f'{m.from_user.id}:addRank:{m.chat.id}{Dev_Zaid}', 1, ex=600)
            return await m.reply(f'''
{k} ارسل الرتبه اللي تبي تغييرها

{k} مالك اساسي
{k} مالك
{k} مدير
{k} ادمن
{k} مميز
{k} عضو
☆''')
