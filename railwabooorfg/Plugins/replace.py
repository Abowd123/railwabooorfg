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
مُنقول من bmqa/Plugins/replace.py → bmqa-v2/Plugins/replace.py

الأوامر/المعالجات:
  - استبدال كلمه | استبدال كلمة  (group=36, text & group)
    سير العمل متعدد الخطوات: الكلمة القديمة → الكلمة الجديدة → اسم الملف
    ثم تعديل الملف وإعادة تشغيل البوت.
  - الغاء  (أثناء أي مرحلة من مراحل الاستبدال)

التحويلات: sync→async، Thread→await مباشر، r.<op>→await rdb.<op>
"""

import os
import sys
from pyrogram import Client, filters
from pyrogram.enums import *
from pyrogram.types import *
from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from helpers.ranks import admin_pls, devp_pls


@register("replace")
@Client.on_message(filters.text & filters.group, group=36)
@safe_handler
async def replaceCode(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')
    channel = await rdb.get(f'{Dev_Zaid}:BotChannel') or 'yqyqy66'
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

    if (
        await rdb.get(f'{m.chat.id}:replace:{m.from_user.id}{Dev_Zaid}')
        or await rdb.get(f'{m.chat.id}:replace2:{m.from_user.id}{Dev_Zaid}')
        or await rdb.get(f'{m.chat.id}:replace3:{m.from_user.id}{Dev_Zaid}')
    ):
        if text == 'الغاء':
            await rdb.delete(f'{m.chat.id}:replace:{m.from_user.id}{Dev_Zaid}')
            await rdb.delete(f'{m.chat.id}:replace2:{m.from_user.id}{Dev_Zaid}')
            await rdb.delete(f'{m.chat.id}:replace3:{m.from_user.id}{Dev_Zaid}')
            return await m.reply(f'{k} من عيوني لغيت استبدال كلمة ')

    if text == 'استبدال كلمه' or text == 'استبدال كلمة':
        if not await devp_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الأمر يخص ( مبرمج السورس ) بس')
        else:
            await rdb.set(f'{m.chat.id}:replace:{m.from_user.id}{Dev_Zaid}', 1, ex=600)
            return await m.reply(f'{k} ارسل الكلمة القديمة الآن')

    if await rdb.get(f'{m.chat.id}:replace:{m.from_user.id}{Dev_Zaid}') and await devp_pls(m.from_user.id, m.chat.id):
        await rdb.set(f'{m.chat.id}:replace2:{m.from_user.id}{Dev_Zaid}', m.text, ex=600)
        await rdb.delete(f'{m.chat.id}:replace:{m.from_user.id}{Dev_Zaid}')
        return await m.reply(f'{k} ارسل الكلمة الجديدة الحين')

    if await rdb.get(f'{m.chat.id}:replace2:{m.from_user.id}{Dev_Zaid}') and await devp_pls(m.from_user.id, m.chat.id):
        txt = await rdb.get(f'{m.chat.id}:replace2:{m.from_user.id}{Dev_Zaid}')
        await rdb.delete(f'{m.chat.id}:replace2:{m.from_user.id}{Dev_Zaid}')
        await rdb.set(f'{m.chat.id}:replace3:{m.from_user.id}{Dev_Zaid}', f'{txt}&&new&&{m.text}', ex=600)
        a = os.listdir('Plugins')
        a.sort()
        txt2 = f'{k} ارسل اسم الملف الي تبي تعدل فيه الحين:'
        count = 1
        txt2 += '\n\n——— ملفات السورس ———'
        for file in a:
            if file.endswith('.py'):
                txt2 += f'\n{count}) `{file}`'
                count += 1
        txt2 += f'\n——— @{channel} ———'
        return await m.reply(txt2)

    if (
        await rdb.get(f'{m.chat.id}:replace3:{m.from_user.id}{Dev_Zaid}')
        and await devp_pls(m.from_user.id, m.chat.id)
        and m.text in os.listdir('Plugins')
    ):
        mm = await m.reply(f'{k} جاريع تعديل الملف')
        get = await rdb.get(f'{m.chat.id}:replace3:{m.from_user.id}{Dev_Zaid}')
        old = get.split('&&new&&')[0]
        new = get.split('&&new&&')[1]
        await rdb.delete(f'{m.chat.id}:replace3:{m.from_user.id}{Dev_Zaid}')
        with open(f'Plugins/{m.text}', 'r') as Read:
            old_confing = Read.read()
            await mm.edit(f'{k} تم فتح الملف وقرائته')
        with open(f'Plugins/{m.text}', 'w+') as Write:
            await mm.edit(f'{k} تم فتح الملف جاري كتابة الكود مع استبدال الكلمة')
            Write.write(old_confing.replace(old, new))
        await mm.edit(
            f'{k} تم فتح الملف `{m.text}` وتعديله\n'
            f'{k} تم استبدال الكلمة القديمة ( {old} ) بالكلمة الجديدة ( {new} )'
        )
        python = sys.executable
        os.execl(python, python, *sys.argv)
