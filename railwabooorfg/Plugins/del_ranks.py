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
مُنقول من bmqa/Plugins/del_ranks.py → bmqa-v2/Plugins/del_ranks.py

الأوامر (handler واحد، group=13، text & group):
  - مسح قائمه Dev       — مسح كل Dev²🎖️             (devp_pls)
  - مسح قائمه MY        — مسح كل Myth🎖️              (dev2_pls)
  - مسح المالكين الاساسيين — مسح كل gowner القروب    (dev_pls)
  - مسح المالكين          — مسح كل owner القروب      (gowner_pls)
  - مسح المدراء           — مسح كل mod القروب        (owner_pls)
  - مسح الادمنيه | مسح الادمن — مسح كل admin القروب  (mod_pls)
  - مسح المميزين          — مسح كل pre القروب        (mod_pls)
  - مسح المكتومين         — مسح كل muted القروب      (mod_pls)
  - مسح المكتومين عام     — مسح كل muted عام         (dev_pls)
  - مسح المحظورين عام     — مسح كل gban عام          (dev_pls)

التحويلات:
  - Thread → await مباشر
  - r.<op> → await rdb.<op>
  - get_rank → await get_rank
  - @register + @safe_handler مُضافان
  - demoted template string محفوظة بالضبط كما في الأصل
"""

import logging
from pyrogram import Client, filters
from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from helpers.ranks import (
    admin_pls, mod_pls, get_rank,
    dev_pls, dev2_pls, devp_pls, gowner_pls, owner_pls,
    isLockCommand,
)

_DEMOTED_TPL = """{} ابشر عيني {}
{} مسحت ( {} ) من {} 
☆
"""


@register("del_ranks")
@Client.on_message(filters.text & filters.group, group=13)
@safe_handler
async def delRanksHandler(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')

    if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
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
    name = await rdb.get(f'{Dev_Zaid}:BotName') or 'رعد'
    if text.startswith(f'{name} '):
        text = text.replace(f'{name} ', '')
    if await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}'):
        text = await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}')
    if await rdb.get(f'Custom:{Dev_Zaid}&text={text}'):
        text = await rdb.get(f'Custom:{Dev_Zaid}&text={text}')
    if await isLockCommand(m.from_user.id, m.chat.id, text):
        return

    uid = m.from_user.id
    cid = m.chat.id

    if text == 'مسح قائمه Dev':
        if not await devp_pls(uid, cid):
            return await m.reply(f'{k} هذا الامر يخص ( Dev🎖️) بس')
        members = await rdb.smembers(f'{Dev_Zaid}DEV2')
        if not members:
            return await m.reply(f'{k} مافيه قائمة Dev²🎖')
        count = 0
        for dev2 in list(members):
            await rdb.srem(f'{Dev_Zaid}DEV2', int(dev2))
            await rdb.delete(f'{int(dev2)}:rankDEV2:{Dev_Zaid}')
            count += 1
        await m.reply(_DEMOTED_TPL.format(k, await get_rank(uid, cid), k, count, 'قائمة Dev'))

    if text == 'مسح قائمه MY':
        if not await dev2_pls(uid, cid):
            return await m.reply(f'{k} هذا الأمر يخص ( Dev²🎖️ وفوق ) بس')
        members = await rdb.smembers(f'{Dev_Zaid}DEV')
        if not members:
            return await m.reply(f'{k} مافيه قائمة Myth🎖️')
        count = 0
        for dev in list(members):
            await rdb.srem(f'{Dev_Zaid}DEV', int(dev))
            await rdb.delete(f'{int(dev)}:rankDEV:{Dev_Zaid}')
            count += 1
        await m.reply(_DEMOTED_TPL.format(k, await get_rank(uid, cid), k, count, 'قائمة MY'))

    if text == 'مسح المالكين الاساسيين':
        if not await dev_pls(uid, cid):
            return await m.reply(f'{k} هذا الامر يخص ( Myth🎖️ مالك القروب وفوق) بس')
        members = await rdb.smembers(f'{cid}:listGOWNER:{Dev_Zaid}')
        if not members:
            return await m.reply(f'{k} مافيه مالكين اساسيين')
        count = 0
        for gowner in list(members):
            await rdb.srem(f'{cid}:listGOWNER:{Dev_Zaid}', int(gowner))
            await rdb.delete(f'{cid}:rankGOWNER:{int(gowner)}{Dev_Zaid}')
            count += 1
        await m.reply(_DEMOTED_TPL.format(k, await get_rank(uid, cid), k, count, 'المالكين الاساسيين'))

    if text == 'مسح المالكين':
        if not await gowner_pls(uid, cid):
            return await m.reply(f'{k} هذا الأمر يخص ( المالك الاساسي وفوق ) بس')
        members = await rdb.smembers(f'{cid}:listOWNER:{Dev_Zaid}')
        if not members:
            return await m.reply(f'{k} مافيه مالكين ')
        count = 0
        for owner in list(members):
            await rdb.srem(f'{cid}:listOWNER:{Dev_Zaid}', int(owner))
            await rdb.delete(f'{cid}:rankOWNER:{int(owner)}{Dev_Zaid}')
            count += 1
        await m.reply(_DEMOTED_TPL.format(k, await get_rank(uid, cid), k, count, 'المالكين'))

    if text == 'مسح المدراء':
        if not await owner_pls(uid, cid):
            return await m.reply(f'{k} هذا الأمر يخص ( المالك وفوق ) بس')
        members = await rdb.smembers(f'{cid}:listMOD:{Dev_Zaid}')
        if not members:
            return await m.reply(f'{k} مافيه مدراء')
        count = 0
        for MOD in list(members):
            await rdb.srem(f'{cid}:listMOD:{Dev_Zaid}', int(MOD))
            await rdb.delete(f'{cid}:rankMOD:{int(MOD)}{Dev_Zaid}')
            count += 1
        await m.reply(_DEMOTED_TPL.format(k, await get_rank(uid, cid), k, count, 'المدراء'))

    if text == 'مسح الادمنيه' or text == 'مسح الادمن':
        if not await mod_pls(uid, cid):
            return await m.reply(f'{k} هذا الأمر يخص ( المدير وفوق ) بس')
        members = await rdb.smembers(f'{cid}:listADMIN:{Dev_Zaid}')
        if not members:
            return await m.reply(f'{k} مافيه ادمن')
        count = 0
        for ADM in list(members):
            await rdb.srem(f'{cid}:listADMIN:{Dev_Zaid}', int(ADM))
            await rdb.delete(f'{cid}:rankADMIN:{int(ADM)}{Dev_Zaid}')
            count += 1
        await m.reply(_DEMOTED_TPL.format(k, await get_rank(uid, cid), k, count, 'الادمن'))

    if text == 'مسح المميزين':
        if not await mod_pls(uid, cid):
            return await m.reply(f'{k} هذا الأمر يخص ( المدير وفوق ) بس')
        members = await rdb.smembers(f'{cid}:listPRE:{Dev_Zaid}')
        if not members:
            return await m.reply(f'{k} مافيه مميزين')
        count = 0
        for PRE in list(members):
            await rdb.srem(f'{cid}:listPRE:{Dev_Zaid}', int(PRE))
            await rdb.delete(f'{cid}:rankPRE:{int(PRE)}{Dev_Zaid}')
            count += 1
        await m.reply(_DEMOTED_TPL.format(k, await get_rank(uid, cid), k, count, 'المميزين'))

    if text == 'مسح المكتومين':
        if not await mod_pls(uid, cid):
            return await m.reply(f'{k} هذا الأمر يخص ( المدير وفوق ) بس')
        members = await rdb.smembers(f'{cid}:listMUTE:{Dev_Zaid}')
        if not members:
            return await m.reply(f'{k} مافيه مكتومين')
        count = 0
        for MOD in list(members):
            try:
                mod = int(MOD)
            except Exception as e:
                logging.exception(e)
                mod = MOD
            await rdb.srem(f'{cid}:listMUTE:{Dev_Zaid}', mod)
            await rdb.delete(f'{mod}:mute:{cid}{Dev_Zaid}')
            count += 1
        await m.reply(_DEMOTED_TPL.format(k, await get_rank(uid, cid), k, count, 'المكتومين'))

    if text == 'مسح المكتومين عام':
        if not await dev_pls(uid, cid):
            return await m.reply(f'{k} هذا الامر يخص ( Myth🎖️ وفوق ) بس')
        members = await rdb.smembers(f'listMUTE:{Dev_Zaid}')
        if not members:
            return await m.reply(f'{k} مافيه مكتومين عام')
        count = 0
        for MOD in list(members):
            await rdb.srem(f'listMUTE:{Dev_Zaid}', int(MOD))
            await rdb.delete(f'{int(MOD)}:mute:{Dev_Zaid}')
            count += 1
        await m.reply(_DEMOTED_TPL.format(k, await get_rank(uid, cid), k, count, 'المكتومين عام'))

    if text == 'مسح المحظورين عام':
        if not await dev_pls(uid, cid):
            return await m.reply(f'{k} هذا الامر يخص ( Myth🎖️ وفوق ) بس')
        members = await rdb.smembers(f'listGBAN:{Dev_Zaid}')
        if not members:
            return await m.reply(f'{k} مافيه حمير محظورين')
        count = 0
        for MOD in list(members):
            await rdb.srem(f'listGBAN:{Dev_Zaid}', int(MOD))
            await rdb.delete(f'{int(MOD)}:gban:{Dev_Zaid}')
            count += 1
        await m.reply(_DEMOTED_TPL.format(k, await get_rank(uid, cid), k, count, 'الحمير المحظورين عام'))
