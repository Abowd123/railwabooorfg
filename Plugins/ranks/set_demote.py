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
Plugins/ranks/set_demote.py — مُقتطع من bmqa/Plugins/set_ranks.py (الجزء الثاني)
مسؤول عن أوامر التنزيل (group=8).

الأوامر:
  - تنزيل Dev  [reply | @user | ID]          (devp_pls)
  - تنزيل MY   [reply | @user | ID]          (dev2_pls)
  - تنزيل مالك اساسي [reply | @user | ID]    (gowner_pls)
  - تنزيل مالك       [reply | @user | ID]    (gowner_pls)
  - تنزيل مدير       [reply | @user | ID]    (owner_pls)
  - تنزيل ادمن       [reply | @user | ID]    (mod_pls)
  - تنزيل مميز       [reply | @user | ID]    (admin_pls)
  - تنزيل الكل [reply | @user | ID]          (mod_pls+ بحسب رتبة المستدعي)
  - تنزيل             (reply فقط)            (mod_pls+ بحسب رتبة المستدعي)

التحويلات: sync→async، Thread→await، r.<op>→await rdb.<op>،
            c.get_chat→await c.get_chat، @register + @safe_handler.
resolve_target (helpers.ranks) يوحّد نمط حل @user/ID المكرر 10+ مرات.
"""

import re
from pyrogram import Client, filters
from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from helpers.ranks import (
    admin_pls, mod_pls, owner_pls, gowner_pls,
    dev_pls, dev2_pls, devp_pls,
    get_rank, isLockCommand, resolve_target,
)

_PROTECTED_IDS = [6168217372, 5117901887]


async def _common_guards(m) -> bool:
    if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
        return True
    if await rdb.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not await admin_pls(m.from_user.id, m.chat.id):
        return True
    if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):
        return True
    if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):
        return True
    if await rdb.get(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}'):
        return True
    if await rdb.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}'):
        return True
    if await rdb.get(f'{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}') or await rdb.get(f'{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}'):
        return True
    return False


async def _resolve_text(m):
    text = m.text
    name = await rdb.get(f'{Dev_Zaid}:BotName') or 'رعد'
    if text.startswith(f'{name} '):
        text = text.replace(f'{name} ', '')
    if await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}'):
        text = await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}')
    if await rdb.get(f'Custom:{Dev_Zaid}&text={text}'):
        text = await rdb.get(f'Custom:{Dev_Zaid}&text={text}')
    return text


async def _clear_all_local_ranks(cid: int, uid: int):
    """يمسح كل رتب عضو في القروب المحلي."""
    await rdb.delete(f'{cid}:rankGOWNER:{uid}{Dev_Zaid}')
    await rdb.srem(f'{cid}:listGOWNER:{Dev_Zaid}', uid)
    await rdb.delete(f'{cid}:rankOWNER:{uid}{Dev_Zaid}')
    await rdb.srem(f'{cid}:listOWNER:{Dev_Zaid}', uid)
    await rdb.delete(f'{cid}:rankMOD:{uid}{Dev_Zaid}')
    await rdb.srem(f'{cid}:listMOD:{Dev_Zaid}', uid)
    await rdb.delete(f'{cid}:rankADMIN:{uid}{Dev_Zaid}')
    await rdb.srem(f'{cid}:listADMIN:{Dev_Zaid}', uid)
    await rdb.delete(f'{cid}:rankPRE:{uid}{Dev_Zaid}')
    await rdb.srem(f'{cid}:listPRE:{Dev_Zaid}', uid)


@register("set_demote")
@Client.on_message(filters.text & filters.group, group=8)
@safe_handler
async def ranksCommandsHandlerDemote(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')
    if await _common_guards(m):
        return

    text = await _resolve_text(m)
    if await isLockCommand(m.from_user.id, m.chat.id, text):
        return

    rank = await get_rank(m.from_user.id, m.chat.id)
    cid = m.chat.id

    # ─── تنزيل Dev ────────────────────────────────────────────────────────
    if text == 'تنزيل Dev' and m.reply_to_message and m.reply_to_message.from_user:
        if not await devp_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( Dev🎖️) بس')
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف انزل نفسي')
        if not await rdb.get(f'{uid}:rankDEV2:{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مو 〖 Dev²🎖 〗\n☆')
        await rdb.delete(f'{uid}:rankDEV2:{Dev_Zaid}')
        await rdb.srem(f'{Dev_Zaid}DEV2', uid)
        return await m.reply(f'「 {mention} 」\n{k} نزلته من 〖 Dev²🎖 〗\n☆')

    if text.startswith('تنزيل Dev ') and ('@' in text or re.findall('[0-9]+', text)):
        if not await devp_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( Dev🎖️) بس')
        result = await resolve_target(c, m, k, text, word_index=2)
        if result is None:
            return
        uid, mention = result
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف انزل نفسي')
        if not await rdb.get(f'{uid}:rankDEV2:{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مو 〖 Dev²🎖 〗\n☆')
        await rdb.delete(f'{uid}:rankDEV2:{Dev_Zaid}')
        await rdb.srem(f'{Dev_Zaid}DEV2', uid)
        return await m.reply(f'「 {mention} 」\n{k} نزلته من 〖 Dev²🎖 〗\n☆')

    # ─── تنزيل MY ─────────────────────────────────────────────────────────
    if text == 'تنزيل MY' and m.reply_to_message and m.reply_to_message.from_user:
        if not await dev2_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( Dev²🎖️ وفوق ) بس')
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف انزل نفسي')
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if not await rdb.get(f'{uid}:rankDEV:{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مو 〖 Myth🎖️ 〗 من قبل\n☆')
        await rdb.delete(f'{uid}:rankDEV:{Dev_Zaid}')
        await rdb.srem(f'{Dev_Zaid}DEV', uid)
        return await m.reply(f'「 {mention} 」\n{k} نزلته من 〖 Myth🎖️ 〗\n☆')

    if text.startswith('تنزيل MY ') and ('@' in text or re.findall('[0-9]+', text)):
        if not await dev2_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( Dev²🎖️ وفوق ) بس')
        result = await resolve_target(c, m, k, text, word_index=2)
        if result is None:
            return
        uid, mention = result
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف انزل نفسي')
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if not await rdb.get(f'{uid}:rankDEV:{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مو 〖 Myth🎖️ 〗 من قبل\n☆')
        await rdb.delete(f'{uid}:rankDEV:{Dev_Zaid}')
        await rdb.srem(f'{Dev_Zaid}DEV', uid)
        return await m.reply(f'「 {mention} 」\n{k} نزلته من 〖 Myth🎖️ 〗\n☆')

    # ─── تنزيل مالك اساسي ─────────────────────────────────────────────────
    if text == 'تنزيل مالك اساسي' and m.reply_to_message and m.reply_to_message.from_user:
        if not await gowner_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص (المالك الاساسي وفوق) بس')
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف انزل نفسي')
        if not await rdb.get(f'{cid}:rankGOWNER:{uid}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مو 〖 مالك اساسي 〗\n☆')
        await rdb.delete(f'{cid}:rankGOWNER:{uid}{Dev_Zaid}')
        await rdb.srem(f'{cid}:listGOWNER:{Dev_Zaid}', uid)
        return await m.reply(f'「 {mention} 」\n{k} نزلته من 〖 المالك الاساسي 〗\n☆')

    if text.startswith('تنزيل مالك اساسي ') and ('@' in text or re.findall('[0-9]+', text)):
        if not await gowner_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص (المالك الاساسي وفوق) بس')
        result = await resolve_target(c, m, k, text, word_index=3)
        if result is None:
            return
        uid, mention = result
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف انزل نفسي')
        if not await rdb.get(f'{cid}:rankGOWNER:{uid}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مو 〖 مالك اساسي 〗\n☆')
        await rdb.delete(f'{cid}:rankGOWNER:{uid}{Dev_Zaid}')
        await rdb.srem(f'{cid}:listGOWNER:{Dev_Zaid}', uid)
        return await m.reply(f'「 {mention} 」\n{k} نزلته من 〖 المالك الاساسي 〗\n☆')

    # ─── تنزيل مالك ───────────────────────────────────────────────────────
    if text == 'تنزيل مالك' and m.reply_to_message and m.reply_to_message.from_user:
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف انزل نفسي')
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if not await rdb.get(f'{cid}:rankOWNER:{uid}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مو 〖 مالك 〗 من قبل\n☆')
        await rdb.delete(f'{cid}:rankOWNER:{uid}{Dev_Zaid}')
        await rdb.srem(f'{cid}:listOWNER:{Dev_Zaid}', uid)
        return await m.reply(f'「 {mention} 」\n{k} نزلته من 〖 المالك 〗 \n☆')

    if text.startswith('تنزيل مالك ') and ('@' in text or re.findall('[0-9]+', text)):
        if not await gowner_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( المالك الاساسي ) بس')
        result = await resolve_target(c, m, k, text, word_index=2)
        if result is None:
            return
        uid, mention = result
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف انزل نفسي')
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if not await rdb.get(f'{cid}:rankOWNER:{uid}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مو 〖 مالك 〗 من قبل\n☆')
        await rdb.delete(f'{cid}:rankOWNER:{uid}{Dev_Zaid}')
        await rdb.srem(f'{cid}:listOWNER:{Dev_Zaid}', uid)
        return await m.reply(f'「 {mention} 」\n{k} نزلته من 〖 المالك 〗 \n☆')

    # ─── تنزيل مدير ───────────────────────────────────────────────────────
    if text == 'تنزيل مدير' and m.reply_to_message and m.reply_to_message.from_user:
        if not await owner_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( المالك وفوق ) بس')
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف انزل نفسي')
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if not await rdb.get(f'{cid}:rankMOD:{uid}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مو 〖 مدير 〗 من قبل\n☆')
        await rdb.delete(f'{cid}:rankMOD:{uid}{Dev_Zaid}')
        await rdb.srem(f'{cid}:listMOD:{Dev_Zaid}', uid)
        return await m.reply(f'「 {mention} 」\n{k} نزلته من 〖 رتبة المدير 〗 \n☆')

    if text.startswith('تنزيل مدير ') and ('@' in text or re.findall('[0-9]+', text)):
        if not await owner_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( المالك وفوق ) بس')
        result = await resolve_target(c, m, k, text, word_index=2)
        if result is None:
            return
        uid, mention = result
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف انزل نفسي')
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if not await rdb.get(f'{cid}:rankMOD:{uid}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مو 〖 مدير 〗 من قبل\n☆')
        await rdb.delete(f'{cid}:rankMOD:{uid}{Dev_Zaid}')
        await rdb.srem(f'{cid}:listMOD:{Dev_Zaid}', uid)
        return await m.reply(f'「 {mention} 」\n{k} نزلته من 〖 رتبة المدير 〗 \n☆')

    # ─── تنزيل ادمن ───────────────────────────────────────────────────────
    if text == 'تنزيل ادمن' and m.reply_to_message and m.reply_to_message.from_user:
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف انزل نفسي')
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if not await rdb.get(f'{cid}:rankADMIN:{uid}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مو 〖 ادمن 〗 من قبل\n☆')
        await rdb.delete(f'{cid}:rankADMIN:{uid}{Dev_Zaid}')
        await rdb.srem(f'{cid}:listADMIN:{Dev_Zaid}', uid)
        return await m.reply(f'「 {mention} 」\n{k} نزلته من 〖 رتبة الادمن 〗 \n☆')

    if text.startswith('تنزيل ادمن ') and ('@' in text or re.findall('[0-9]+', text)):
        if not await mod_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( المدير وفوق ) بس')
        result = await resolve_target(c, m, k, text, word_index=2)
        if result is None:
            return
        uid, mention = result
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف انزل نفسي')
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if not await rdb.get(f'{cid}:rankADMIN:{uid}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مو 〖 ادمن 〗 من قبل\n☆')
        await rdb.delete(f'{cid}:rankADMIN:{uid}{Dev_Zaid}')
        await rdb.srem(f'{cid}:listADMIN:{Dev_Zaid}', uid)
        return await m.reply(f'「 {mention} 」\n{k} نزلته من 〖 رتبة الادمن 〗 \n☆')

    # ─── تنزيل مميز ───────────────────────────────────────────────────────
    if text == 'تنزيل مميز' and m.reply_to_message and m.reply_to_message.from_user:
        if not await admin_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف انزل نفسي')
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if not await rdb.get(f'{cid}:rankPRE:{uid}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مو 〖 مميز 〗 من قبل\n☆')
        await rdb.delete(f'{cid}:rankPRE:{uid}{Dev_Zaid}')
        await rdb.srem(f'{cid}:listPRE:{Dev_Zaid}', uid)
        return await m.reply(f'「 {mention} 」\n{k} نزلته من 〖 المميزين 〗 \n☆')

    if text.startswith('تنزيل مميز ') and ('@' in text or re.findall('[0-9]+', text)):
        if not await admin_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
        result = await resolve_target(c, m, k, text, word_index=2)
        if result is None:
            return
        uid, mention = result
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف انزل نفسي')
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if not await rdb.get(f'{cid}:rankPRE:{uid}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} مو 〖 مميز 〗 من قبل\n☆')
        await rdb.delete(f'{cid}:rankPRE:{uid}{Dev_Zaid}')
        await rdb.srem(f'{cid}:listPRE:{Dev_Zaid}', uid)
        return await m.reply(f'「 {mention} 」\n{k} نزلته من 〖 المميزين 〗 \n☆')

    # ─── تنزيل الكل ───────────────────────────────────────────────────────
    async def _do_demote_all(uid: int, mention: str):
        """تنزيل الكل بحسب رتبة المستدعي — نفس منطق الأصل."""
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف انزل نفسي')

        if await devp_pls(m.from_user.id, cid):
            caller_rank = await get_rank(uid, cid)
            if uid == m.from_user.id:
                return await m.reply(f'{k} مافيك تنزل نفسك')
            if caller_rank != 'عضو' and uid not in _PROTECTED_IDS:
                await m.reply(f'「 {mention} 」\n{k} نزلته من {caller_rank} \n☆')
                await rdb.delete(f'{uid}:rankDEV2:{Dev_Zaid}')
                await rdb.srem(f'{Dev_Zaid}DEV2', uid)
                await rdb.delete(f'{uid}:rankDEV:{Dev_Zaid}')
                await rdb.srem(f'{Dev_Zaid}DEV', uid)
                await _clear_all_local_ranks(cid, uid)
                return
            if uid in _PROTECTED_IDS:
                return await m.reply(f'{k} مايمديك تستخدم الأمر على مبرمج السورس')
            return await m.reply(f'{k} ماله رتبة')

        owner_id = int(await rdb.get(f'{Dev_Zaid}botowner'))

        if await dev2_pls(m.from_user.id, cid):
            caller_rank = await get_rank(uid, cid)
            if caller_rank != 'عضو' and uid != owner_id and uid not in _PROTECTED_IDS:
                await m.reply(f'「 {mention} 」\n{k} نزلته من {caller_rank} \n☆')
                await rdb.delete(f'{uid}:rankDEV:{Dev_Zaid}')
                await rdb.srem(f'{Dev_Zaid}DEV', uid)
                await _clear_all_local_ranks(cid, uid)
                return
            if uid in _PROTECTED_IDS or uid == owner_id:
                return await m.reply(f'{k} رتبته اعلى منك')
            return await m.reply(f'{k} ماله رتبة')

        if await dev_pls(m.from_user.id, cid):
            caller_rank = await get_rank(uid, cid)
            if (caller_rank != 'عضو' and uid != owner_id and uid not in _PROTECTED_IDS
                    and not await rdb.get(f'{uid}:rankDEV2:{Dev_Zaid}')):
                await m.reply(f'「 {mention} 」\n{k} نزلته من {caller_rank} \n☆')
                await _clear_all_local_ranks(cid, uid)
                return
            return await m.reply(f'{k} رتبته اعلى منك')

        if await gowner_pls(m.from_user.id, cid):
            caller_rank = await get_rank(uid, cid)
            if (caller_rank != 'عضو' and uid != owner_id and uid not in _PROTECTED_IDS
                    and not await rdb.get(f'{uid}:rankDEV2:{Dev_Zaid}')
                    and not await rdb.get(f'{uid}:rankDEV:{Dev_Zaid}')):
                await m.reply(f'「 {mention} 」\n{k} نزلته من {caller_rank} \n☆')
                await rdb.delete(f'{cid}:rankOWNER:{uid}{Dev_Zaid}')
                await rdb.srem(f'{cid}:listOWNER:{Dev_Zaid}', uid)
                await rdb.delete(f'{cid}:rankMOD:{uid}{Dev_Zaid}')
                await rdb.srem(f'{cid}:listMOD:{Dev_Zaid}', uid)
                await rdb.delete(f'{cid}:rankADMIN:{uid}{Dev_Zaid}')
                await rdb.srem(f'{cid}:listADMIN:{Dev_Zaid}', uid)
                await rdb.delete(f'{cid}:rankPRE:{uid}{Dev_Zaid}')
                await rdb.srem(f'{cid}:listPRE:{Dev_Zaid}', uid)
                return
            return await m.reply(f'{k} رتبته اعلى منك')

        if await owner_pls(m.from_user.id, cid):
            caller_rank = await get_rank(uid, cid)
            if (caller_rank != 'عضو' and uid != owner_id and uid not in _PROTECTED_IDS
                    and not await rdb.get(f'{uid}:rankDEV2:{Dev_Zaid}')
                    and not await rdb.get(f'{uid}:rankDEV:{Dev_Zaid}')
                    and not await rdb.get(f'{cid}:rankGOWNER:{uid}{Dev_Zaid}')):
                await m.reply(f'「 {mention} 」\n{k} نزلته من {caller_rank} \n☆')
                await rdb.delete(f'{cid}:rankMOD:{uid}{Dev_Zaid}')
                await rdb.srem(f'{cid}:listMOD:{Dev_Zaid}', uid)
                await rdb.delete(f'{cid}:rankADMIN:{uid}{Dev_Zaid}')
                await rdb.srem(f'{cid}:listADMIN:{Dev_Zaid}', uid)
                await rdb.delete(f'{cid}:rankPRE:{uid}{Dev_Zaid}')
                await rdb.srem(f'{cid}:listPRE:{Dev_Zaid}', uid)
                return
            return await m.reply(f'{k} رتبته اعلى منك')

        if await mod_pls(m.from_user.id, cid):
            caller_rank = await get_rank(uid, cid)
            if (caller_rank != 'عضو' and uid != owner_id and uid not in _PROTECTED_IDS
                    and not await rdb.get(f'{uid}:rankDEV2:{Dev_Zaid}')
                    and not await rdb.get(f'{uid}:rankDEV:{Dev_Zaid}')
                    and not await rdb.get(f'{cid}:rankGOWNER:{uid}{Dev_Zaid}')
                    and not await rdb.get(f'{cid}:rankOWNER:{uid}{Dev_Zaid}')):
                await m.reply(f'「 {mention} 」\n{k} نزلته من {caller_rank} \n☆')
                await rdb.delete(f'{cid}:rankADMIN:{uid}{Dev_Zaid}')
                await rdb.srem(f'{cid}:listADMIN:{Dev_Zaid}', uid)
                await rdb.delete(f'{cid}:rankPRE:{uid}{Dev_Zaid}')
                await rdb.srem(f'{cid}:listPRE:{Dev_Zaid}', uid)
                return
            return await m.reply(f'{k} رتبته اعلى منك')

        if await admin_pls(m.from_user.id, cid):
            caller_rank = await get_rank(uid, cid)
            if (caller_rank != 'عضو' and uid != owner_id and uid not in _PROTECTED_IDS
                    and not await rdb.get(f'{uid}:rankDEV2:{Dev_Zaid}')
                    and not await rdb.get(f'{uid}:rankDEV:{Dev_Zaid}')
                    and not await rdb.get(f'{cid}:rankGOWNER:{uid}{Dev_Zaid}')
                    and not await rdb.get(f'{cid}:rankOWNER:{uid}{Dev_Zaid}')
                    and not await rdb.get(f'{cid}:rankMOD:{uid}{Dev_Zaid}')):
                await m.reply(f'「 {mention} 」\n{k} نزلته من {caller_rank} \n☆')
                await rdb.delete(f'{cid}:rankPRE:{uid}{Dev_Zaid}')
                await rdb.srem(f'{cid}:listPRE:{Dev_Zaid}', uid)
                return
            return await m.reply(f'{k} رتبته اعلى منك')

        return await m.reply(f'{k} ماله رتبة')

    if text.startswith('تنزيل الكل ') and ('@' in text or re.findall('[0-9]+', text)):
        if not await mod_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( المدير وفوق ) بس')
        result = await resolve_target(c, m, k, text, word_index=2)
        if result is None:
            return
        uid, mention = result
        return await _do_demote_all(uid, mention)

    if text == 'تنزيل الكل' and m.reply_to_message and m.reply_to_message.from_user:
        if not await owner_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( المالك وفوق ) بس')
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        return await _do_demote_all(uid, mention)

    # ─── تنزيل (reply — smart demote) ────────────────────────────────────
    if text == 'تنزيل' and m.reply_to_message and m.reply_to_message.from_user:
        if not await mod_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( المدير وفوق ) بس')
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        return await _do_demote_all(uid, mention)
