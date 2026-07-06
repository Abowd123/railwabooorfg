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
Plugins/ranks/set_promote.py — مُقتطع من bmqa/Plugins/set_ranks.py (الجزء الأول)
مسؤول عن أوامر الرفع (group=7).

الأوامر:
  - تعطيل الرفع / تفعيل الرفع              (owner_pls)
  - رفع Dev  [reply | @user | ID]          (devp_pls)
  - رفع MY   [reply | @user | ID]          (dev2_pls)
  - رفع مالك اساسي [reply | @user | ID]    (gowner_pls)
  - رفع مالك       [reply | @user | ID]    (gowner_pls)
  - رفع مدير       [reply | @user | ID]    (owner_pls)
  - رفع ادمن       [reply | @user | ID]    (mod_pls)
  - رفع مميز       [reply | @user | ID]    (admin_pls)

التحويلات: sync→async، Thread→await، r.<op>→await rdb.<op>،
            c.get_chat→await c.get_chat، @register + @safe_handler.
resolve_target (helpers.ranks) يوحّد نمط حل @user/ID المكرر 14 مرة.
"""

import re
from pyrogram import Client, filters
from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from helpers.ranks import (
    admin_pls, mod_pls, owner_pls, gowner_pls,
    dev2_pls, devp_pls,
    get_rank, isLockCommand, resolve_target,
)


async def _common_guards(m, k) -> bool:
    """يعيد True إذا يجب إيقاف المعالجة (حارس مشترك لكلا الـhandler)."""
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
    """يحسب النص بعد استبدال الأوامر المخصصة والتحقق من اسم البوت."""
    text = m.text
    name = await rdb.get(f'{Dev_Zaid}:BotName') or 'رعد'
    if text.startswith(f'{name} '):
        text = text.replace(f'{name} ', '')
    if await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}'):
        text = await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}')
    if await rdb.get(f'Custom:{Dev_Zaid}&text={text}'):
        text = await rdb.get(f'Custom:{Dev_Zaid}&text={text}')
    return text


async def _unmute_after_promote(m, uid: int):
    """يرفع الكتم العام والمحلي عن عضو تمت ترقيته."""
    if await rdb.get(f'{uid}:mute:{Dev_Zaid}'):
        await rdb.delete(f'{uid}:mute:{Dev_Zaid}')
        await rdb.srem(f'listMUTE:{Dev_Zaid}', uid)
    if await rdb.get(f'{uid}:mute:{m.chat.id}{Dev_Zaid}'):
        await rdb.delete(f'{uid}:mute:{m.chat.id}{Dev_Zaid}')
        await rdb.srem(f'{m.chat.id}:listMUTE:{Dev_Zaid}', uid)


@register("set_promote")
@Client.on_message(filters.text & filters.group, group=7)
@safe_handler
async def ranksCommandsHandler(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')
    if await _common_guards(m, k):
        return

    text = await _resolve_text(m)
    if await isLockCommand(m.from_user.id, m.chat.id, text):
        return

    cid = m.chat.id
    rank = await get_rank(m.from_user.id, cid)

    if text == 'تعطيل الرفع':
        if not await owner_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( المالك وفوق ) بس')
        if await rdb.get(f'{cid}:disableRanks:{Dev_Zaid}'):
            return await m.reply(f'{k} من「 {m.from_user.mention} 」\n{k} الرفع معطل من قبل\n☆')
        await rdb.set(f'{cid}:disableRanks:{Dev_Zaid}', 1)
        return await m.reply(f'{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت الرفع\n☆')

    if text == 'تفعيل الرفع':
        if not await owner_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( المالك وفوق ) بس')
        if not await rdb.get(f'{cid}:disableRanks:{Dev_Zaid}'):
            return await m.reply(f'「 {m.from_user.mention} 」\n{k} الرفع مفعل من قبل\n☆')
        await rdb.delete(f'{cid}:disableRanks:{Dev_Zaid}')
        return await m.reply(f'{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت الرفع\n☆')

    if await rdb.get(f'{cid}:disableRanks:{Dev_Zaid}'):
        return

    # ─── رفع Dev ───────────────────────────────────────────────────────────
    if text.startswith('رفع Dev ') and ('@' in text or re.findall('[0-9]+', text)):
        if not await devp_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( Dev🎖️) بس')
        result = await resolve_target(c, m, k, text, word_index=2)
        if result is None:
            return
        uid, mention = result
        if uid == m.from_user.id:
            return await m.reply('هطف تبي ترفع نفسك؟')
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف ارفع نفسي')
        if await rdb.get(f'{uid}:rankDEV2:{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} 〖 Dev²🎖 〗 من قبل\n☆')
        await rdb.set(f'{uid}:rankDEV2:{Dev_Zaid}', 1)
        await rdb.sadd(f'{Dev_Zaid}DEV2', uid)
        return await m.reply(f'{k} الحلو 「 {mention} 」\n{k} رفعته صار 〖 Dev²🎖 〗\n☆')

    if text == 'رفع Dev' and m.reply_to_message and m.reply_to_message.from_user:
        if not await devp_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( Dev🎖️) بس')
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if uid == m.from_user.id:
            return await m.reply('ليش تبي ترفع نفسك انت؟')
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف ارفع نفسي')
        if await rdb.get(f'{uid}:rankDEV2:{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} 〖 Dev²🎖 〗 من قبل\n☆')
        await rdb.set(f'{uid}:rankDEV2:{Dev_Zaid}', 1)
        await rdb.sadd(f'{Dev_Zaid}DEV2', uid)
        return await m.reply(f'{k} الحلو 「 {mention} 」\n{k} رفعته صار 〖 Dev²🎖 〗\n☆')

    # ─── رفع MY ────────────────────────────────────────────────────────────
    if text.startswith('رفع MY ') and ('@' in text or re.findall('[0-9]+', text)):
        if not await dev2_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( Dev²🎖️ وفوق ) بس')
        result = await resolve_target(c, m, k, text, word_index=2)
        if result is None:
            return
        uid, mention = result
        if uid == m.from_user.id:
            return await m.reply('شكلك تبي ترفع نفسك، ما يصير كذا')
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف ارفع نفسي')
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if await rdb.get(f'{uid}:rankDEV:{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} 〖 Myth🎖️ 〗 من قبل\n☆')
        await rdb.set(f'{uid}:rankDEV:{Dev_Zaid}', 1)
        await rdb.sadd(f'{Dev_Zaid}DEV', uid)
        await m.reply(f'{k} الحلو 「 {mention} 」\n{k} رفعته صار 〖 Myth🎖️ 〗\n☆')
        await _unmute_after_promote(m, uid)
        return

    if text == 'رفع MY' and m.reply_to_message and m.reply_to_message.from_user:
        if not await dev2_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( Dev²🎖️ وفوق ) بس')
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if uid == m.from_user.id:
            return await m.reply('كيف بترفع نفسك بنفسك؟')
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف ارفع نفسي')
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if await rdb.get(f'{uid}:rankDEV:{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} 〖 Myth🎖️ 〗 من قبل\n☆')
        await rdb.set(f'{uid}:rankDEV:{Dev_Zaid}', 1)
        await rdb.sadd(f'{Dev_Zaid}DEV', uid)
        await m.reply(f'{k} الحلو 「 {mention} 」\n{k} رفعته صار 〖 Myth🎖️ 〗\n☆')
        await _unmute_after_promote(m, uid)
        return

    # ─── رفع مالك اساسي ───────────────────────────────────────────────────
    if text.startswith('رفع مالك اساسي ') and ('@' in text or re.findall('[0-9]+', text)):
        if not await gowner_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( المالك الاساسي وفوق ) بس')
        result = await resolve_target(c, m, k, text, word_index=3)
        if result is None:
            return
        uid, mention = result
        if uid == m.from_user.id:
            return await m.reply('يا هذا تبي ترفع نفسك؟ ما تصير')
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف ارفع نفسي')
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if await rdb.get(f'{cid}:rankGOWNER:{uid}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} 〖 مالك اساسي 〗 من قبل\n☆')
        await rdb.set(f'{cid}:rankGOWNER:{uid}{Dev_Zaid}', 1)
        await rdb.sadd(f'{cid}:listGOWNER:{Dev_Zaid}', uid)
        await m.reply(f'{k} الحلو 「 {mention} 」\n{k} رفعته صار 〖 مالك اساسي 〗\n☆')
        await _unmute_after_promote(m, uid)
        return

    if text == 'رفع مالك اساسي' and m.reply_to_message and m.reply_to_message.from_user:
        if not await gowner_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص (المالك الاساسي وفوق) بس')
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if uid == m.from_user.id:
            return await m.reply('استغرب كيف تبي ترفع نفسك')
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف ارفع نفسي')
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if await rdb.get(f'{cid}:rankGOWNER:{uid}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} 〖 مالك اساسي 〗 من قبل\n☆')
        await rdb.set(f'{cid}:rankGOWNER:{uid}{Dev_Zaid}', 1)
        await rdb.sadd(f'{cid}:listGOWNER:{Dev_Zaid}', uid)
        await m.reply(f'{k} الحلو 「 {mention} 」\n{k} رفعته صار 〖 مالك اساسي 〗\n☆')
        await _unmute_after_promote(m, uid)
        return

    # ─── رفع مالك ─────────────────────────────────────────────────────────
    if text.startswith('رفع مالك ') and ('@' in text or re.findall('[0-9]+', text)):
        if not await gowner_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( المالك الاساسي ) بس')
        result = await resolve_target(c, m, k, text, word_index=2)
        if result is None:
            return
        uid, mention = result
        if uid == m.from_user.id:
            return await m.reply('هطف تبي ترفع نفسك؟')
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف ارفع نفسي')
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if await rdb.get(f'{cid}:rankOWNER:{uid}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} 〖 مالك 〗 من قبل\n☆')
        await rdb.set(f'{cid}:rankOWNER:{uid}{Dev_Zaid}', 1)
        await rdb.sadd(f'{cid}:listOWNER:{Dev_Zaid}', uid)
        await m.reply(f'{k} الحلو 「 {mention} 」\n{k} رفعته صار 〖 مالك 〗\n☆')
        if await rdb.get(f'{uid}:mute:{m.chat.id}{Dev_Zaid}'):
            await rdb.delete(f'{uid}:mute:{m.chat.id}{Dev_Zaid}')
            await rdb.srem(f'{m.chat.id}:listMUTE:{Dev_Zaid}', uid)
        return

    if text == 'رفع مالك' and m.reply_to_message and m.reply_to_message.from_user:
        if not await gowner_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( المالك الاساسي ) بس')
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if uid == m.from_user.id:
            return await m.reply('ليش تبي ترفع نفسك انت؟')
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف ارفع نفسي')
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if await rdb.get(f'{cid}:rankOWNER:{uid}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} 〖 مالك 〗 من قبل\n☆')
        await rdb.set(f'{cid}:rankOWNER:{uid}{Dev_Zaid}', 1)
        await rdb.sadd(f'{cid}:listOWNER:{Dev_Zaid}', uid)
        await m.reply(f'{k} الحلو 「 {mention} 」\n{k} رفعته صار 〖 مالك 〗\n☆')
        if await rdb.get(f'{uid}:mute:{m.chat.id}{Dev_Zaid}'):
            await rdb.delete(f'{uid}:mute:{m.chat.id}{Dev_Zaid}')
            await rdb.srem(f'{m.chat.id}:listMUTE:{Dev_Zaid}', uid)
        return

    # ─── رفع مدير ─────────────────────────────────────────────────────────
    if text.startswith('رفع مدير ') and ('@' in text or re.findall('[0-9]+', text)):
        if not await owner_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( المالك وفوق ) بس')
        result = await resolve_target(c, m, k, text, word_index=2)
        if result is None:
            return
        uid, mention = result
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف ارفع نفسي')
        if uid == m.from_user.id:
            return await m.reply('شكلك تبي ترفع نفسك، ما يصير كذا')
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if await rdb.get(f'{cid}:rankMOD:{uid}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} 〖 مدير 〗 من قبل\n☆')
        await rdb.set(f'{cid}:rankMOD:{uid}{Dev_Zaid}', 1)
        await rdb.sadd(f'{cid}:listMOD:{Dev_Zaid}', uid)
        await m.reply(f'{k} الحلو 「 {mention} 」\n{k} رفعته صار 〖 مدير 〗\n☆')
        if await rdb.get(f'{uid}:mute:{m.chat.id}{Dev_Zaid}'):
            await rdb.delete(f'{uid}:mute:{m.chat.id}{Dev_Zaid}')
            await rdb.srem(f'{m.chat.id}:listMUTE:{Dev_Zaid}', uid)
        return

    if text == 'رفع مدير' and m.reply_to_message and m.reply_to_message.from_user:
        if not await owner_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( المالك وفوق ) بس')
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف ارفع نفسي')
        if uid == m.from_user.id:
            return await m.reply('كيف بترفع نفسك بنفسك؟')
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if await rdb.get(f'{cid}:rankMOD:{uid}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} 〖 مدير 〗 من قبل\n☆')
        await rdb.set(f'{cid}:rankMOD:{uid}{Dev_Zaid}', 1)
        await rdb.sadd(f'{cid}:listMOD:{Dev_Zaid}', uid)
        await m.reply(f'{k} الحلو 「 {mention} 」\n{k} رفعته صار 〖 مدير 〗\n☆')
        if await rdb.get(f'{uid}:mute:{m.chat.id}{Dev_Zaid}'):
            await rdb.delete(f'{uid}:mute:{m.chat.id}{Dev_Zaid}')
            await rdb.srem(f'{m.chat.id}:listMUTE:{Dev_Zaid}', uid)
        return

    # ─── رفع ادمن ─────────────────────────────────────────────────────────
    if text.startswith('رفع ادمن ') and ('@' in text or re.findall('[0-9]+', text)):
        if not await mod_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( المدير وفوق ) بس')
        result = await resolve_target(c, m, k, text, word_index=2)
        if result is None:
            return
        uid, mention = result
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف ارفع نفسي')
        if uid == m.from_user.id:
            return await m.reply('يا هذا تبي ترفع نفسك؟ ما تصير')
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if await rdb.get(f'{cid}:rankADMIN:{uid}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} 〖 ادمن 〗 من قبل\n☆')
        await rdb.set(f'{cid}:rankADMIN:{uid}{Dev_Zaid}', 1)
        await rdb.sadd(f'{cid}:listADMIN:{Dev_Zaid}', uid)
        await m.reply(f'{k} الحلو 「 {mention} 」\n{k} رفعته صار 〖 ادمن 〗\n☆')
        if await rdb.get(f'{uid}:mute:{m.chat.id}{Dev_Zaid}'):
            await rdb.delete(f'{uid}:mute:{m.chat.id}{Dev_Zaid}')
            await rdb.srem(f'{m.chat.id}:listMUTE:{Dev_Zaid}', uid)
        return

    if text == 'رفع ادمن' and m.reply_to_message and m.reply_to_message.from_user:
        if not await mod_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( المدير وفوق ) بس')
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف ارفع نفسي')
        if uid == m.from_user.id:
            return await m.reply('استغرب كيف تبي ترفع نفسك')
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if await rdb.get(f'{cid}:rankADMIN:{uid}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} 〖 ادمن 〗 من قبل\n☆')
        await rdb.set(f'{cid}:rankADMIN:{uid}{Dev_Zaid}', 1)
        await rdb.sadd(f'{cid}:listADMIN:{Dev_Zaid}', uid)
        await m.reply(f'{k} الحلو 「 {mention} 」\n{k} رفعته صار 〖 ادمن 〗\n☆')
        if await rdb.get(f'{uid}:mute:{m.chat.id}{Dev_Zaid}'):
            await rdb.delete(f'{uid}:mute:{m.chat.id}{Dev_Zaid}')
            await rdb.srem(f'{m.chat.id}:listMUTE:{Dev_Zaid}', uid)
        return

    # ─── رفع مميز ─────────────────────────────────────────────────────────
    if text.startswith('رفع مميز ') and ('@' in text or re.findall('[0-9]+', text)):
        if not await admin_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
        result = await resolve_target(c, m, k, text, word_index=2)
        if result is None:
            return
        uid, mention = result
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف ارفع نفسي')
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if uid == m.from_user.id:
            return await m.reply('هطف تبي ترفع نفسك؟')
        if await rdb.get(f'{cid}:rankPRE:{uid}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} 〖 مميز 〗 من قبل\n☆')
        await rdb.set(f'{cid}:rankPRE:{uid}{Dev_Zaid}', 1)
        await rdb.sadd(f'{cid}:listPRE:{Dev_Zaid}', uid)
        await m.reply(f'{k} الحلو 「 {mention} 」\n{k} رفعته صار 〖 مميز 〗\n☆')
        if await rdb.get(f'{uid}:mute:{m.chat.id}{Dev_Zaid}'):
            await rdb.delete(f'{uid}:mute:{m.chat.id}{Dev_Zaid}')
            await rdb.srem(f'{m.chat.id}:listMUTE:{Dev_Zaid}', uid)
        return

    if text == 'رفع مميز' and m.reply_to_message and m.reply_to_message.from_user:
        if not await admin_pls(m.from_user.id, cid):
            return await m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if uid == int(Dev_Zaid):
            return await m.reply('ركز حبيبي كيف ارفع نفسي')
        if uid == m.from_user.id:
            return await m.reply('ليش تبي ترفع نفسك انت؟')
        if rank == await get_rank(uid, cid):
            return await m.reply('نفس رتبتك ترا')
        if await rdb.get(f'{cid}:rankPRE:{uid}{Dev_Zaid}'):
            return await m.reply(f'「 {mention} 」\n{k} 〖 مميز 〗 من قبل\n☆')
        await rdb.set(f'{cid}:rankPRE:{uid}{Dev_Zaid}', 1)
        await rdb.sadd(f'{cid}:listPRE:{Dev_Zaid}', uid)
        await m.reply(f'{k} الحلو 「 {mention} 」\n{k} رفعته صار 〖 مميز 〗\n☆')
        if await rdb.get(f'{uid}:mute:{m.chat.id}{Dev_Zaid}'):
            await rdb.delete(f'{uid}:mute:{m.chat.id}{Dev_Zaid}')
            await rdb.srem(f'{m.chat.id}:listMUTE:{Dev_Zaid}', uid)
        return
