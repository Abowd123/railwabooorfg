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
مُنقول من bmqa/Plugins/group_update.py (892 سطر) → bmqa-v2/Plugins/group_update.py

═══════════════════════════════════════════════════════════════════
التحويلات المطبّقة على كامل الملف:
  - Thread(target=X, args=(c, m)).start() → await X(c, m) مباشرة
    (كل الهاندلرز أصبحت async def، لا حاجة لـ Thread لأن Pyrogram
    (وbmqa-v2 كله) يعمل بالكامل async الآن — راجع main.py/core/db.py).
  - كل نداء r.<op>(...) → await rdb.<op>(...) (core/db.py، نفس أسماء
    العمليات تماماً كما في الأصل: get/set/delete/incr/sadd/srem/smembers).
  - كل نداء Pyrogram متزامن (c.get_chat, c.invoke, c.stream_media,
    c.get_chat_photos, c.send_message, m.chat.get_member,
    m.chat.get_members, c.leave_chat, m.reply/reply_photo/...) أصبح
    مُنتظراً بـ await (Pyrogram async client لا يدعم النداء المتزامن).
  - time.sleep(N) → await asyncio.sleep(N) في **كل** المواضع السبعة من
    الأصل (كانت بالأسطر 59, 636, 674, 707, 756, 820, 852 في bmqa الأصلي):
      1) داخل kick_from_group (docstring معطّل بالأصل — كود ميت لم يكن
         يُنفَّذ أصلاً؛ أُبقي معطّلاً هنا بنفس الشكل، لكن استُبدل النص
         الداخلي أيضاً لتطابق العدد المطلوب في المهمة تحديداً).
      2) kick_from_gp (on_message filters.left_chat_member)
      3-5) get_bot_status (on_chat_member_updated) — ثلاث حلقات إرسال
         منفصلة لإشعار المطورين (تعطيل تلقائي / تعديل صلاحية / تفعيل تلقائي)
      6-7) EnableAndDisablegroup (أمر "تفعيل") و(أمر "تعطيل")
    ملاحظة: كانت هناك حلقة سابعة مطابقة داخل "اطلعي/اطلع" في الأصل بدون
    time.sleep على الإطلاق (لا تُحسب ضمن السبعة المطلوبة).
  - @register + @safe_handler مُضافان فوق كل هاندلر حقيقي (نفس نمط
    global_filters.py وcustom_filter.py المنقولين مسبقاً). safe_handler
    (core/errors.py) يتكفّل بمعالجة FloodWait + تسجيل أي خطأ آخر بدل
    print/pass الصامتة في الأصل.
  - from config import * / from helpers.Ranks import * → استيراد صريح
    ومحدد (Dev_Zaid, botUsername, admin_pls, owner_pls, get_devs_br, ...).
  - helpers.Ranks → helpers.ranks (حروف صغيرة، كما في بقية bmqa-v2).
  - `from .all import list_UwU` (كان يُستخدم فقط داخل كتلة triple-quote
    معطّلة بالكامل في get_rngp) — لا يوجد ملف all.py مكافئ في bmqa-v2
    (globalFilters/customFilter/... نُقلت كل واحدة لملفها الخاص)، وبما
    أن الاستخدام الوحيد كان كوداً ميتاً (docstring) فقد حُذف الاستيراد
    وأُبقيت الكتلة المعطّلة كتعليق فقط دون list_UwU.
  - متغيّرا `bot_r` و`bot_name` (يُستخدَمان في "بوت" و`text == name`) غير
    مُعرَّفين في الملف الأصلي إطلاقاً ولا في أي ملف آخر من bmqa الأصلي —
    هذا خطأ/كود ميت أصلي (NameError كامن لا يُشغَّل إلا لو طابق النص أحد
    هذين الشرطين). أُبقي على نفس السلوك هنا حرفياً (لا يوجد أي تخمين أو
    إصلاح صامت لمنطق لم يُطلب تعديله) — إن رغبتم بتفعيل هاتين الرسالتين
    فعلاً، ستحتاجون لتزويدي بمصدر القوائم بوت_r / بوت_name.
  - Thread import حُذف (غير مستخدم بعد التحويل الكامل لـ async).
═══════════════════════════════════════════════════════════════════
"""

import logging
import asyncio
import random
import re
from io import BytesIO

from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus, ChatMembersFilter
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaAudio,
)
from pyrogram.raw.functions.users import GetFullUser
from pyrogram.file_id import FileId, FileType, ThumbnailSource

from config import Dev_Zaid, botUsername
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from helpers.ranks import admin_pls, owner_pls, get_devs_br
from helpers.quran import TheHolyQuran, MaherAlmaikulai
from helpers.memes import memes_sy, memes_eg, memes_sa, memes_ae, memes_us, memes_iq

###########################################################################
###########################################################################
'''
@Client.on_raw_update(group=0)
async def kick_from_group(app: Client, m, _, __):
   try:
      name = re.search(r"first_name='([^']+)'", str(_)).group(1)
      title = re.search(r"title='([^']+)'", str(__)).group(1)
      if 'types.ChannelParticipantBanned' in str(m) and '"is_self": true' in str(m):
        await rdb.delete(f'{m.chat.id}:enable:{Dev_Zaid}', int(f'-100{m.channel_id}'))
        await rdb.srem(f'enablelist:{Dev_Zaid}', int(f'-100{m.channel_id}'))
      else:
        return False
      text = '{k} تم طرد البوت من مجموعة:\n\n'
      text += f'{k} اسم الي طردني : [{name}](tg://user?id={m.new_participant.kicked_by})\n'
      text += f'{k} ايدي الي طردني : {m.new_participant.kicked_by}\n'
      text += f'\n{k} معلومات المجموعة: \n'
      text += f'\n{k} ايدي المجموعة: `-100{m.channel_id}`'
      text += f'\n{k} اسم المجموعه: {title}'
      text += '\n{k} تم مسح جميع بيانات المجموعة'
      text += '\n\n༄'
      if await rdb.get(f'DevGroup:{Dev_Zaid}'):
        await app.send_message(int(await rdb.get(f'DevGroup:{Dev_Zaid}')),text,disable_web_page_preview=True)
      else:
        for dev in await get_devs_br():
          try:
            await app.send_message(int(dev), text, disable_web_page_preview=True)
            await asyncio.sleep(3)
          except Exception as e:
            logging.exception(e)
            pass
   except Exception as e:
     logging.exception(e)
     print (e)
'''
## الردود


async def _resolve_text(c, m):
    text = m.text
    name = await rdb.get(f'{Dev_Zaid}:BotName') if await rdb.get(f'{Dev_Zaid}:BotName') else 'رعد'
    if text.startswith(f'{name} '):
        text = text.replace(f'{name} ', '')
    return text, name


@register("global_handler")
@Client.on_message(filters.text & filters.group, group=1)
@safe_handler
async def globalHandler(c, m):
    if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'): return
    if await rdb.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not await admin_pls(m.from_user.id, m.chat.id): return
    if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'): return
    if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'): return
    if await rdb.get(f'{m.chat.id}:lock_global:{Dev_Zaid}'): return
    if await rdb.get(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}'): return
    if await rdb.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}'): return
    if await rdb.get(f'{m.chat.id}:addFilterG:{m.from_user.id}{Dev_Zaid}'): return
    if await rdb.get(f'{m.chat.id}:delFilterG:{m.from_user.id}{Dev_Zaid}'): return
    if await rdb.get(f'{m.chat.id}:addFilter2GG:{m.from_user.id}{Dev_Zaid}'): return

    text, name = await _resolve_text(c, m)
    get = await rdb.get(f'{text}:filter:{Dev_Zaid}')
    if get:
        type = re.search(r'type=([^&]+)', get).group(1)
        userID = str(m.from_user.id)
        userNAME = str(m.from_user.first_name)
        userUSERNAME = "@" + m.from_user.username if m.from_user.username else "مافي يوزر"
        userMENTION = m.from_user.mention(userNAME[:25])
        if type == 'text':
            return await m.reply(get.split('&text=')[1].replace("<USER_ID>", userID).replace("<USER_NAME>", userNAME).replace("<USER_USERNAME>", userUSERNAME).replace("<USER_MENTION>", userMENTION), disable_web_page_preview=True)

        if type == 'photo':
            photo = re.search(r'photo=([^&]+)', get).group(1)
            caption = get.split('&caption=')[1].replace("<USER_ID>", userID).replace("<USER_NAME>", userNAME).replace("<USER_USERNAME>", userUSERNAME).replace("<USER_MENTION>", userMENTION)
            cpt = None if caption == 'None' else caption
            return await m.reply_photo(photo, caption=cpt)

        if type == 'video':
            video = re.search(r'video=([^&]+)', get).group(1)
            caption = get.split('&caption=')[1].replace("<USER_ID>", userID).replace("<USER_NAME>", userNAME).replace("<USER_USERNAME>", userUSERNAME).replace("<USER_MENTION>", userMENTION)
            cpt = None if caption == 'None' else caption
            return await m.reply_video(video, caption=cpt)

        if type == 'voice':
            voice = re.search(r'voice=([^&]+)', get).group(1)
            caption = get.split('&caption=')[1].replace("<USER_ID>", userID).replace("<USER_NAME>", userNAME).replace("<USER_USERNAME>", userUSERNAME).replace("<USER_MENTION>", userMENTION)
            cpt = None if caption == 'None' else caption
            return await m.reply_voice(voice, caption=cpt)

        if type == 'animation':
            animation = re.search(r'animation=([^&]+)', get).group(1)
            caption = get.split('&caption=')[1].replace("<USER_ID>", userID).replace("<USER_NAME>", userNAME).replace("<USER_USERNAME>", userUSERNAME).replace("<USER_MENTION>", userMENTION)
            cpt = None if caption == 'None' else caption
            return await m.reply_animation(animation, caption=cpt)

        if type == 'audio':
            audio = re.search(r'audio=([^&]+)', get).group(1)
            caption = get.split('&caption=')[1].replace("<USER_ID>", userID).replace("<USER_NAME>", userNAME).replace("<USER_USERNAME>", userUSERNAME).replace("<USER_MENTION>", userMENTION)
            cpt = None if caption == 'None' else caption
            return await m.reply_audio(audio, caption=cpt)

        if type == 'doc':
            doc = re.search(r'doc=([^&]+)', get).group(1)
            caption = get.split('&caption=')[1].replace("<USER_ID>", userID).replace("<USER_NAME>", userNAME).replace("<USER_USERNAME>", userUSERNAME).replace("<USER_MENTION>", userMENTION)
            cpt = None if caption == 'None' else caption
            return await m.reply_document(doc, caption=cpt)

        if type == 'sticker':
            return await m.reply_sticker(get.split('&sticker=')[1])

    if text == 'المطور':
        id = int(await rdb.get(f'{Dev_Zaid}botowner'))
        get = await c.get_chat(id)
        bio = get.bio if get.bio else None
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(get.first_name, user_id=id)]])
        if not get.photo:
            return await m.reply_animation('https://telegra.ph/file/d9127c65922817d127f04.mp4', caption=bio, reply_markup=reply_markup)
        else:
            get_user = await c.invoke(GetFullUser(id=(await c.resolve_peer(id))))
            photo = get_user.full_user.profile_photo
            video = photo.video_sizes[0] if photo.video_sizes else None
            if video:
                file = BytesIO()
                async for byte in c.stream_media(
                    message=FileId(
                        file_type=FileType.PHOTO,
                        dc_id=photo.dc_id, media_id=photo.id,
                        access_hash=photo.access_hash,
                        file_reference=photo.file_reference,
                        thumbnail_source=ThumbnailSource.THUMBNAIL,
                        thumbnail_file_type=FileType.PHOTO,
                        thumbnail_size=video.type,
                        volume_id=0, local_id=0
                    ).encode()
                ):
                    file.write(byte)
                file.name = f'{id}vid.mp4'
                return await m.reply_animation(file, caption=bio, reply_markup=reply_markup)
            else:
                async for photo in c.get_chat_photos(id, limit=1):
                    return await m.reply_photo(photo.file_id, caption=bio, reply_markup=reply_markup)


@register("filters_handler")
@Client.on_message(filters.text & filters.group, group=2)
@safe_handler
async def filtersHandler(c, m):
    if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'): return
    if await rdb.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not await admin_pls(m.from_user.id, m.chat.id): return
    if await rdb.get(f'{m.chat.id}:addFilter:{m.from_user.id}{Dev_Zaid}'): return
    if await rdb.get(f'{m.chat.id}:delFilter:{m.from_user.id}{Dev_Zaid}'): return
    if await rdb.get(f'{m.chat.id}:addFilter2:{m.from_user.id}{Dev_Zaid}'): return
    if await rdb.get(f'{m.chat.id}:lock_filter:{Dev_Zaid}'): return
    if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'): return
    if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'): return
    if await rdb.get(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}'): return
    if await rdb.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}'): return

    text, name = await _resolve_text(c, m)
    get = await rdb.get(f'{text}:filter:{Dev_Zaid}{m.chat.id}')
    if get:
        type = re.search(r'type=([^&]+)', get).group(1)
        userID = str(m.from_user.id)
        userNAME = str(m.from_user.first_name)
        userUSERNAME = "@" + m.from_user.username if m.from_user.username else "مافي يوزر"
        userMENTION = m.from_user.mention(userNAME[:25])
        if type == 'text':
            await m.reply(get.split('&text=')[1].replace("<USER_ID>", userID).replace("<USER_NAME>", userNAME).replace("<USER_USERNAME>", userUSERNAME).replace("<USER_MENTION>", userMENTION), disable_web_page_preview=True)

        if type == 'photo':
            photo = re.search(r'photo=([^&]+)', get).group(1)
            caption = get.split('&caption=')[1].replace("<USER_ID>", userID).replace("<USER_NAME>", userNAME).replace("<USER_USERNAME>", userUSERNAME).replace("<USER_MENTION>", userMENTION)
            cpt = None if caption == 'None' else caption
            await m.reply_photo(photo, caption=cpt)

        if type == 'video':
            video = re.search(r'video=([^&]+)', get).group(1)
            caption = get.split('&caption=')[1].replace("<USER_ID>", userID).replace("<USER_NAME>", userNAME).replace("<USER_USERNAME>", userUSERNAME).replace("<USER_MENTION>", userMENTION)
            cpt = None if caption == 'None' else caption
            await m.reply_video(video, caption=cpt)

        if type == 'voice':
            voice = re.search(r'voice=([^&]+)', get).group(1)
            caption = get.split('&caption=')[1].replace("<USER_ID>", userID).replace("<USER_NAME>", userNAME).replace("<USER_USERNAME>", userUSERNAME).replace("<USER_MENTION>", userMENTION)
            cpt = None if caption == 'None' else caption
            await m.reply_voice(voice, caption=cpt)

        if type == 'animation':
            animation = re.search(r'animation=([^&]+)', get).group(1)
            caption = get.split('&caption=')[1].replace("<USER_ID>", userID).replace("<USER_NAME>", userNAME).replace("<USER_USERNAME>", userUSERNAME).replace("<USER_MENTION>", userMENTION)
            cpt = None if caption == 'None' else caption
            await m.reply_animation(animation, caption=cpt)

        if type == 'audio':
            audio = re.search(r'audio=([^&]+)', get).group(1)
            caption = get.split('&caption=')[1].replace("<USER_ID>", userID).replace("<USER_NAME>", userNAME).replace("<USER_USERNAME>", userUSERNAME).replace("<USER_MENTION>", userMENTION)
            cpt = None if caption == 'None' else caption
            await m.reply_audio(audio, caption=cpt)

        if type == 'doc':
            doc = re.search(r'doc=([^&]+)', get).group(1)
            caption = get.split('&caption=')[1].replace("<USER_ID>", userID).replace("<USER_NAME>", userNAME).replace("<USER_USERNAME>", userUSERNAME).replace("<USER_MENTION>", userMENTION)
            cpt = None if caption == 'None' else caption
            await m.reply_document(doc, caption=cpt)

        if type == 'sticker':
            await m.reply_sticker(get.split('&sticker=')[1])

    filterMEM_key = f'{text}:filterMEM:{Dev_Zaid}{m.chat.id}'
    if await rdb.get(filterMEM_key) and not await rdb.get(f'{m.chat.id}:lock_filterMEM:{Dev_Zaid}'):
        id = int(await rdb.get(filterMEM_key))
        get = await c.get_chat(id)
        cap = f"𖡋 𝐍𝐀𝐌𝐄 ⌯ [{get.first_name}](tg://user?id={get.id})\n𖡋 𝐈𝐃 ⌯ `{get.id}`"
        if get.bio:
            cap += f"\n`{get.bio}`"
        if get.username:
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(get.first_name, user_id=id)]])
        else:
            reply_markup = None
        if not get.photo:
            return await m.reply(cap, reply_markup=reply_markup)
        else:
            get_user = await c.invoke(GetFullUser(id=(await c.resolve_peer(id))))
            photo = get_user.full_user.profile_photo
            hash = photo.access_hash
            cached = await rdb.get(f"{hash}:{id}")
            if cached:
                return await m.reply_animation(cached, caption=cap, reply_markup=reply_markup)
            video = photo.video_sizes[0] if photo.video_sizes else None
            if video:
                file = BytesIO()
                async for byte in c.stream_media(
                    message=FileId(
                        file_type=FileType.PHOTO,
                        dc_id=photo.dc_id, media_id=photo.id,
                        access_hash=photo.access_hash,
                        file_reference=photo.file_reference,
                        thumbnail_source=ThumbnailSource.THUMBNAIL,
                        thumbnail_file_type=FileType.PHOTO,
                        thumbnail_size=video.type,
                        volume_id=0, local_id=0
                    ).encode()
                ):
                    file.write(byte)
                file.name = f'{id}vid.mp4'
                a = await m.reply_animation(file, caption=cap, reply_markup=reply_markup)
                return await rdb.set(f"{hash}:{id}", a.animation.file_id, ex=120)
            else:
                async for photo in c.get_chat_photos(id, limit=1):
                    return await m.reply_photo(photo.file_id, caption=cap, reply_markup=reply_markup)


@register("global_random_update")
@Client.on_message(filters.text & filters.group, group=3)
@safe_handler
async def globalRandomupdate(c, m):
    if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'): return
    if await rdb.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not await admin_pls(m.from_user.id, m.chat.id): return
    if await rdb.get(f'{m.chat.id}:lock_global:{Dev_Zaid}'): return

    if m.from_user:
        if await rdb.get(f'{m.chat.id}:addFilterRG:{m.from_user.id}{Dev_Zaid}') or await rdb.get(f'{m.chat.id}:delFilterRG:{m.from_user.id}{Dev_Zaid}'): return
        if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'): return
        if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'): return

    text, name = await _resolve_text(c, m)
    userID = str(m.from_user.id)
    userNAME = str(m.from_user.first_name)
    userUSERNAME = "@" + m.from_user.username if m.from_user.username else "مافي يوزر"
    userMENTION = m.from_user.mention(userNAME[:25])
    if await rdb.get(f'{text}:randomFilter:{Dev_Zaid}'):
        rlist = await rdb.smembers(f'{text}:randomfilter:{Dev_Zaid}')
        if rlist:
            return await m.reply(random.sample(list(rlist), 1)[0].replace('{اسم_البوت}', name).replace("<USER_ID>", userID).replace("<USER_NAME>", userNAME).replace("<USER_USERNAME>", userUSERNAME).replace("<USER_MENTION>", userMENTION), disable_web_page_preview=True)

    sb = [
        "عييييييييب", "عيب", "ياكلب عيب", "يا قليل التربيه", "يا قليل الادب", "؟؟؟؟؟؟", "ياليت تتأدب", "بقص لسانك", "حاضر", "ياخي عيب", "؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟", "استغفر الله",
    ]
    lovem = [
        "يلبيييه", "اكثر", "يعمري", "اعشقك", "بدينا كذب", "احلى من يحبني", "يحظي والله", "اكثر اكثر اكثرر", "يروحي", "اموت فيك", ]
    zg = [
        "عييييييييب", "عيب", "زق بوجهك", "يا قليل التربيه", "يا قليل الادب", "؟؟؟؟؟؟", "ياليت تتأدب", "بقص لسانك", "حاضر", "ياخي عيب", "؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟؟", ]
    mm = [
        "ابركها من ساعة", "احبك", "اكثر", "ترا ازعجتنا", "انقلع", "طيب", "مو اكثر مني", "وبعدين ؟", "جت من الله", "بس كذا يا حلو"]

    # ملاحظة: bot_r/bot_name غير معرَّفَين في الأصل (كود ميت/خطأ كامن أصلي) — أُبقيا كما هما.
    if text == 'بوت':
        await m.reply(random.choice(bot_r))

    if text == name:
        await m.reply(random.choice(bot_name))

    '''
    if text in list_UwU:
      await m.reply(random.choice(sb))
    '''

    if text == 'احبك':
        await m.reply(random.choice(lovem))

    if text == 'اكرهك':
        await m.reply(random.choice(mm))

    if text == 'كليزق' or text == 'كلزق':
        await m.reply(random.choice(zg))

    if text.startswith('سورة ') or text.startswith('سوره '):
        soura = text.split(None, 1)[1].replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ٰ', '').replace('ة', 'ه')
        if f'سورة {soura}' in TheHolyQuran:
            title = random.choice(["﴿ سَبِّحِ اسمَ رَبِّكَ الأَعلَى ﴾", "﴿ وَلَلآخِرَةُ خَيرٌ لَكَ مِنَ الأولى ﴾", "﴿ وَكانَ ذلِكَ عَلَى اللَّهِ يَسيرًا ﴾", "﴿ لِمَن شاءَ مِنكُم أَن يَتَقَدَّمَ أَو يَتَأَخَّرَ ﴾", "﴿ فَمَن عَفا وَأَصلَحَ فَأَجرُهُ عَلَى اللَّهِ ﴾", "﴿ هُوَ أَهلُ التَّقوى وَأَهلُ المَغفِرَةِ ﴾", "﴿ هَل جَزاءُ الإِحسانِ إِلَّا الإِحسانُ ﴾", "﴿ وَلا يَظلِمُ رَبُّكَ أَحَدًا ﴾", "﴿ وَمَن يُؤمِن بِاللَّهِ يَهدِ قَلبَهُ ﴾", "﴿ وَكانَ رَبُّكَ قَديرًا ﴾", "﴿ وَتَطمَئِنُّ قُلوبُهُم بِذِكرِ اللَّهِ ﴾", "﴿ سَيَهديهِم وَيُصلِحُ بالَهُم ﴾", "﴿ وَوَجَدَكَ ضالًّا فَهَدى ﴾", "﴿ فَاسعَوا إِلى ذِكرِ اللَّهِ ﴾", "( إِنّ السّاعَةَ آتِيَةٌ أَكَادُ أُخْفِيهَا )", "﴿وَلا تَكونوا كَالَّذينَ نَسُوا اللَّهَ فَأَنساهُم أَنفُسَهُم﴾.", " ‏﴿أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ﴾ ", "﴿ وَقُلْ رَبِّ ارْحَمْهُمَا كَمَا رَبَّيَانِي صَغِيرًا ﴾♡.", "‏{وَعَسَىٰ أَن تَكْرَهُوا شَيْئًا وَهُوَ خَيْرٌ لَّكُمْ}", "{ لاتحزَن إِنَّ الله مَعَنا }"])
            return await m.reply_audio(
                MaherAlmaikulai[f"سورة {soura}"],
                caption=f'سورة {soura}',
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton(title, url='t.me/P_V_R')],
                        [InlineKeyboardButton('بصوت سعد الغامدي', callback_data=f'{m.from_user.id}quSaad={MaherAlmaikulai[f"سورة {soura}"].split("MaherSounds/")[1]}')],
                        [InlineKeyboardButton('بصوت عبد الباسط عبد الصمد', callback_data=f'{m.from_user.id}quBaset={MaherAlmaikulai[f"سورة {soura}"].split("MaherSounds/")[1]}')],
                        [InlineKeyboardButton('بصوت مشاري راشد العفاسي', callback_data=f'{m.from_user.id}qu3fasy={MaherAlmaikulai[f"سورة {soura}"].split("MaherSounds/")[1]}')]
                    ]
                )
            )

    if text == 'ميمز':
        randomMeme = random.choice(memes_sa)
        return await m.reply_audio(
            randomMeme["url"], caption=randomMeme["title"],
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton('🇸🇾', callback_data=f'{m.from_user.id}memes_sy'), InlineKeyboardButton('🇪🇬', callback_data=f'{m.from_user.id}memes_eg')],
                    [InlineKeyboardButton('🇸🇦', callback_data=f'{m.from_user.id}memes_sa'), InlineKeyboardButton('🇦🇪', callback_data=f'{m.from_user.id}memes_ae')],
                    [InlineKeyboardButton('🇺🇸', callback_data=f'{m.from_user.id}memes_us'), InlineKeyboardButton('🇮🇶', callback_data=f'{m.from_user.id}memes_iq'), ],
                    [InlineKeyboardButton('🧚‍♀️', url='t.me/P_V_R')],
                ]
            )
        )
    # https://raw.githubusercontent.com/maknon/Quran/main/pages-douri/604.png
    if (text.startswith('قرآن ') or text.startswith('قران ')) and re.findall('[0-9]+', text):
        page = int(re.findall('[0-9]+', text)[0])
        if page <= 604:
            title = random.choice(["﴿ سَبِّحِ اسمَ رَبِّكَ الأَعلَى ﴾", "﴿ وَلَلآخِرَةُ خَيرٌ لَكَ مِنَ الأولى ﴾", "﴿ وَكانَ ذلِكَ عَلَى اللَّهِ يَسيرًا ﴾", "﴿ لِمَن شاءَ مِنكُم أَن يَتَقَدَّمَ أَو يَتَأَخَّرَ ﴾", "﴿ فَمَن عَفا وَأَصلَحَ فَأَجرُهُ عَلَى اللَّهِ ﴾", "﴿ هُوَ أَهلُ التَّقوى وَأَهلُ المَغفِرَةِ ﴾", "﴿ هَل جَزاءُ الإِحسانِ إِلَّا الإِحسانُ ﴾", "﴿ وَلا يَظلِمُ رَبُّكَ أَحَدًا ﴾", "﴿ وَمَن يُؤمِن بِاللَّهِ يَهدِ قَلبَهُ ﴾", "﴿ وَكانَ رَبُّكَ قَديرًا ﴾", "﴿ وَتَطمَئِنُّ قُلوبُهُم بِذِكرِ اللَّهِ ﴾", "﴿ سَيَهديهِم وَيُصلِحُ بالَهُم ﴾", "﴿ وَوَجَدَكَ ضالًّا فَهَدى ﴾", "﴿ فَاسعَوا إِلى ذِكرِ اللَّهِ ﴾", "( إِنّ السّاعَةَ آتِيَةٌ أَكَادُ أُخْفِيهَا )", "﴿وَلا تَكونوا كَالَّذينَ نَسُوا اللَّهَ فَأَنساهُم أَنفُسَهُم﴾.", " ‏﴿أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ﴾ ", "﴿ وَقُلْ رَبِّ ارْحَمْهُمَا كَمَا رَبَّيَانِي صَغِيرًا ﴾♡.", "‏{وَعَسَىٰ أَن تَكْرَهُوا شَيْئًا وَهُوَ خَيْرٌ لَّكُمْ}", "{ لاتحزَن إِنَّ الله مَعَنا }"])
            return await m.reply_photo(f'https://raw.githubusercontent.com/maknon/Quran/main/pages-douri/{page}.png', reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton(title, url='t.me/P_V_R')
                ]]
            ))


@register("memes_callback")
@Client.on_callback_query(filters.regex('memes'))
@safe_handler
async def memes(c, m):
    if str(m.from_user.id) in m.data:
        list = None
        if m.data.endswith('sy'):
            list = memes_sy
        if m.data.endswith('eg'):
            list = memes_eg
        if m.data.endswith('sa'):
            list = memes_sa
        if m.data.endswith('ae'):
            list = memes_ae
        if m.data.endswith('us'):
            list = memes_us
        if m.data.endswith('iq'):
            list = memes_iq
        randomMeme = random.choice(list)
        try:
            return await m.edit_message_media(media=InputMediaAudio(media=randomMeme["url"], caption=randomMeme["title"], ),
                                               reply_markup=m.message.reply_markup)
        except Exception as e:
            logging.exception(e)
            await m.message.reply_to_message.reply_audio(randomMeme["url"], caption=randomMeme["title"], reply_markup=m.message.reply_markup)
            return await m.message.delete()


@register("qu_saad_callback")
@Client.on_callback_query(filters.regex('quSaad'))
@safe_handler
async def quSaad(c, m):
    if m.data.startswith(f'{m.from_user.id}quSaad'):
        soura = m.data.split('=')[1]
        title = random.choice(["﴿ سَبِّحِ اسمَ رَبِّكَ الأَعلَى ﴾", "﴿ وَلَلآخِرَةُ خَيرٌ لَكَ مِنَ الأولى ﴾", "﴿ وَكانَ ذلِكَ عَلَى اللَّهِ يَسيرًا ﴾", "﴿ لِمَن شاءَ مِنكُم أَن يَتَقَدَّمَ أَو يَتَأَخَّرَ ﴾", "﴿ فَمَن عَفا وَأَصلَحَ فَأَجرُهُ عَلَى اللَّهِ ﴾", "﴿ هُوَ أَهلُ التَّقوى وَأَهلُ المَغفِرَةِ ﴾", "﴿ هَل جَزاءُ الإِحسانِ إِلَّا الإِحسانُ ﴾", "﴿ وَلا يَظلِمُ رَبُّكَ أَحَدًا ﴾", "﴿ وَمَن يُؤمِن بِاللَّهِ يَهدِ قَلبَهُ ﴾", "﴿ وَكانَ رَبُّكَ قَديرًا ﴾", "﴿ وَتَطمَئِنُّ قُلوبُهُم بِذِكرِ اللَّهِ ﴾", "﴿ سَيَهديهِم وَيُصلِحُ بالَهُم ﴾", "﴿ وَوَجَدَكَ ضالًّا فَهَدى ﴾", "﴿ فَاسعَوا إِلى ذِكرِ اللَّهِ ﴾", "( إِنّ السّاعَةَ آتِيَةٌ أَكَادُ أُخْفِيهَا )", "﴿وَلا تَكونوا كَالَّذينَ نَسُوا اللَّهَ فَأَنساهُم أَنفُسَهُم﴾.", " ‏﴿أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ﴾ ", "﴿ وَقُلْ رَبِّ ارْحَمْهُمَا كَمَا رَبَّيَانِي صَغِيرًا ﴾♡.", "‏{وَعَسَىٰ أَن تَكْرَهُوا شَيْئًا وَهُوَ خَيْرٌ لَّكُمْ}", "{ لاتحزَن إِنَّ الله مَعَنا }"])
        return await m.edit_message_media(
            media=InputMediaAudio(
                media=f'https://t.me/SaadSounds/{soura}',
                caption=m.message.caption
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(title, url='t.me/P_V_R')],
                    [InlineKeyboardButton('بصوت ماهر المعيقلي', callback_data=f'{m.from_user.id}quMaher={soura}')],
                    [InlineKeyboardButton('بصوت عبد الباسط عبد الصمد', callback_data=f'{m.from_user.id}quBaset={soura}')],
                    [InlineKeyboardButton('بصوت مشاري راشد العفاسي', callback_data=f'{m.from_user.id}qu3fasy={soura}')]
                ]
            )
        )


@register("qu_maher_callback")
@Client.on_callback_query(filters.regex('quMaher'))
@safe_handler
async def quMaher(c, m):
    if m.data.startswith(f'{m.from_user.id}quMaher'):
        soura = m.data.split('=')[1]
        title = random.choice(["﴿ سَبِّحِ اسمَ رَبِّكَ الأَعلَى ﴾", "﴿ وَلَلآخِرَةُ خَيرٌ لَكَ مِنَ الأولى ﴾", "﴿ وَكانَ ذلِكَ عَلَى اللَّهِ يَسيرًا ﴾", "﴿ لِمَن شاءَ مِنكُم أَن يَتَقَدَّمَ أَو يَتَأَخَّرَ ﴾", "﴿ فَمَن عَفا وَأَصلَحَ فَأَجرُهُ عَلَى اللَّهِ ﴾", "﴿ هُوَ أَهلُ التَّقوى وَأَهلُ المَغفِرَةِ ﴾", "﴿ هَل جَزاءُ الإِحسانِ إِلَّا الإِحسانُ ﴾", "﴿ وَلا يَظلِمُ رَبُّكَ أَحَدًا ﴾", "﴿ وَمَن يُؤمِن بِاللَّهِ يَهدِ قَلبَهُ ﴾", "﴿ وَكانَ رَبُّكَ قَديرًا ﴾", "﴿ وَتَطمَئِنُّ قُلوبُهُم بِذِكرِ اللَّهِ ﴾", "﴿ سَيَهديهِم وَيُصلِحُ بالَهُم ﴾", "﴿ وَوَجَدَكَ ضالًّا فَهَدى ﴾", "﴿ فَاسعَوا إِلى ذِكرِ اللَّهِ ﴾", "( إِنّ السّاعَةَ آتِيَةٌ أَكَادُ أُخْفِيهَا )", "﴿وَلا تَكونوا كَالَّذينَ نَسُوا اللَّهَ فَأَنساهُم أَنفُسَهُم﴾.", " ‏﴿أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ﴾ ", "﴿ وَقُلْ رَبِّ ارْحَمْهُمَا كَمَا رَبَّيَانِي صَغِيرًا ﴾♡.", "‏{وَعَسَىٰ أَن تَكْرَهُوا شَيْئًا وَهُوَ خَيْرٌ لَّكُمْ}", "{ لاتحزَن إِنَّ الله مَعَنا }"])
        return await m.edit_message_media(
            media=InputMediaAudio(
                media=f'https://t.me/MaherSounds/{soura}',
                caption=m.message.caption
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(title, url='t.me/yqyqy66')],
                    [InlineKeyboardButton('بصوت سعد الغامدي', callback_data=f'{m.from_user.id}quSaad={soura}')],
                    [InlineKeyboardButton('بصوت عبد الباسط عبد الصمد', callback_data=f'{m.from_user.id}quBaset={soura}')],
                    [InlineKeyboardButton('بصوت مشاري راشد العفاسي', callback_data=f'{m.from_user.id}qu3fasy={soura}')]
                ]
            )
        )


@register("qu_3fasy_callback")
@Client.on_callback_query(filters.regex('qu3fasy'))
@safe_handler
async def qu3fasy(c, m):
    if m.data.startswith(f'{m.from_user.id}qu3fasy'):
        soura = m.data.split('=')[1]
        title = random.choice(["﴿ سَبِّحِ اسمَ رَبِّكَ الأَعلَى ﴾", "﴿ وَلَلآخِرَةُ خَيرٌ لَكَ مِنَ الأولى ﴾", "﴿ وَكانَ ذلِكَ عَلَى اللَّهِ يَسيرًا ﴾", "﴿ لِمَن شاءَ مِنكُم أَن يَتَقَدَّمَ أَو يَتَأَخَّرَ ﴾", "﴿ فَمَن عَفا وَأَصلَحَ فَأَجرُهُ عَلَى اللَّهِ ﴾", "﴿ هُوَ أَهلُ التَّقوى وَأَهلُ المَغفِرَةِ ﴾", "﴿ هَل جَزاءُ الإِحسانِ إِلَّا الإِحسانُ ﴾", "﴿ وَلا يَظلِمُ رَبُّكَ أَحَدًا ﴾", "﴿ وَمَن يُؤمِن بِاللَّهِ يَهدِ قَلبَهُ ﴾", "﴿ وَكانَ رَبُّكَ قَديرًا ﴾", "﴿ وَتَطمَئِنُّ قُلوبُهُم بِذِكرِ اللَّهِ ﴾", "﴿ سَيَهديهِم وَيُصلِحُ بالَهُم ﴾", "﴿ وَوَجَدَكَ ضالًّا فَهَدى ﴾", "﴿ فَاسعَوا إِلى ذِكرِ اللَّهِ ﴾", "( إِنّ السّاعَةَ آتِيَةٌ أَكَادُ أُخْفِيهَا )", "﴿وَلا تَكونوا كَالَّذينَ نَسُوا اللَّهَ فَأَنساهُم أَنفُسَهُم﴾.", " ‏﴿أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ﴾ ", "﴿ وَقُلْ رَبِّ ارْحَمْهُمَا كَمَا رَبَّيَانِي صَغِيرًا ﴾♡.", "‏{وَعَسَىٰ أَن تَكْرَهُوا شَيْئًا وَهُوَ خَيْرٌ لَّكُمْ}", "{ لاتحزَن إِنَّ الله مَعَنا }"])
        return await m.edit_message_media(
            media=InputMediaAudio(
                media=f'https://t.me/Al3afasy/{soura}',
                caption=m.message.caption
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(title, url='t.me/yqyqy66')],
                    [InlineKeyboardButton('بصوت سعد الغامدي', callback_data=f'{m.from_user.id}quSaad={soura}')],
                    [InlineKeyboardButton('بصوت عبد الباسط عبد الصمد', callback_data=f'{m.from_user.id}quBaset={soura}')],
                    [InlineKeyboardButton('بصوت ماهر المعيقلي', callback_data=f'{m.from_user.id}quMaher={soura}')]
                ]
            )
        )


@register("qu_baset_callback")
@Client.on_callback_query(filters.regex('quBaset'))
@safe_handler
async def quBaset(c, m):
    if m.data.startswith(f'{m.from_user.id}quBaset'):
        soura = m.data.split('=')[1]
        title = random.choice(["﴿ سَبِّحِ اسمَ رَبِّكَ الأَعلَى ﴾", "﴿ وَلَلآخِرَةُ خَيرٌ لَكَ مِنَ الأولى ﴾", "﴿ وَكانَ ذلِكَ عَلَى اللَّهِ يَسيرًا ﴾", "﴿ لِمَن شاءَ مِنكُم أَن يَتَقَدَّمَ أَو يَتَأَخَّرَ ﴾", "﴿ فَمَن عَفا وَأَصلَحَ فَأَجرُهُ عَلَى اللَّهِ ﴾", "﴿ هُوَ أَهلُ التَّقوى وَأَهلُ المَغفِرَةِ ﴾", "﴿ هَل جَزاءُ الإِحسانِ إِلَّا الإِحسانُ ﴾", "﴿ وَلا يَظلِمُ رَبُّكَ أَحَدًا ﴾", "﴿ وَمَن يُؤمِن بِاللَّهِ يَهدِ قَلبَهُ ﴾", "﴿ وَكانَ رَبُّكَ قَديرًا ﴾", "﴿ وَتَطمَئِنُّ قُلوبُهُم بِذِكرِ اللَّهِ ﴾", "﴿ سَيَهديهِم وَيُصلِحُ بالَهُم ﴾", "﴿ وَوَجَدَكَ ضالًّا فَهَدى ﴾", "﴿ فَاسعَوا إِلى ذِكرِ اللَّهِ ﴾", "( إِنّ السّاعَةَ آتِيَةٌ أَكَادُ أُخْفِيهَا )", "﴿وَلا تَكونوا كَالَّذينَ نَسُوا اللَّهَ فَأَنساهُم أَنفُسَهُم﴾.", " ‏﴿أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ﴾ ", "﴿ وَقُلْ رَبِّ ارْحَمْهُمَا كَمَا رَبَّيَانِي صَغِيرًا ﴾♡.", "‏{وَعَسَىٰ أَن تَكْرَهُوا شَيْئًا وَهُوَ خَيْرٌ لَّكُمْ}", "{ لاتحزَن إِنَّ الله مَعَنا }"])
        return await m.edit_message_media(
            media=InputMediaAudio(
                media=f'https://t.me/AbdAlbasetS/{soura}',
                caption=m.message.caption
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(title, url='t.me/yqyqy66')],
                    [InlineKeyboardButton('بصوت سعد الغامدي', callback_data=f'{m.from_user.id}quSaad={soura}')],
                    [InlineKeyboardButton('بصوت مشاري راشد العفاسي', callback_data=f'{m.from_user.id}qu3fasy={soura}')],
                    [InlineKeyboardButton('بصوت ماهر المعيقلي', callback_data=f'{m.from_user.id}quMaher={soura}')]
                ]
            )
        )


@register("random_filters_handler")
@Client.on_message(filters.text & filters.group, group=4)
@safe_handler
async def randomfiltersHandler(c, m):
    if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'): return
    if await rdb.get(f'{m.chat.id}:lock_filter:{Dev_Zaid}'): return
    if await rdb.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not await admin_pls(m.from_user.id, m.chat.id): return
    if m.from_user:
        if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'): return
        if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'): return
        if await rdb.get(f'{m.chat.id}:addFilter:{m.from_user.id}{Dev_Zaid}'): return
        if await rdb.get(f'{m.chat.id}:delFilter:{m.from_user.id}{Dev_Zaid}'): return
        if await rdb.get(f'{m.chat.id}:addFilter2:{m.from_user.id}{Dev_Zaid}'): return
        if await rdb.get(f'{m.chat.id}:delFilterR:{m.from_user.id}{Dev_Zaid}') or await rdb.get(f'{m.chat.id}:addFilterR:{m.from_user.id}{Dev_Zaid}') or await rdb.get(f'{m.chat.id}:addFilterR2:{m.from_user.id}{Dev_Zaid}'): return

    text = m.text
    name = await rdb.get(f'{Dev_Zaid}:BotName') if await rdb.get(f'{Dev_Zaid}:BotName') else 'رعد'
    userID = str(m.from_user.id)
    userNAME = str(m.from_user.first_name)
    userUSERNAME = "@" + m.from_user.username if m.from_user.username else "مافي يوزر"
    userMENTION = m.from_user.mention(userNAME[:25])
    if text.startswith(f'{name} '):
        text = text.replace(f'{name} ', '')
    if await rdb.get(f'{text}:randomFilter:{m.chat.id}{Dev_Zaid}'):
        rlist = await rdb.smembers(f'{text}:randomfilter:{m.chat.id}{Dev_Zaid}')
        if rlist:
            return await m.reply(random.sample(list(rlist), 1)[0].replace("<USER_ID>", userID).replace("<USER_NAME>", userNAME).replace("<USER_USERNAME>", userUSERNAME).replace("<USER_MENTION>", userMENTION), disable_web_page_preview=True)


@register("kick_from_gp")
@Client.on_message(filters.left_chat_member)
@safe_handler
async def kick_from_gp(c, m):
    if m.left_chat_member.id == int(Dev_Zaid):
        k = await rdb.get(f'{Dev_Zaid}:botkey')
        text = f'{k} من「 {m.from_user.mention} 」\n'
        usrr = '@' + m.from_user.username if m.from_user.username else 'مافيه'
        text += f'{k} يوزره : {usrr}\n'
        text += f'{k} ايديه : `{m.from_user.id}`\n'
        text += f'\n{k} قام بطرد البوت من المجموعة :\n\n'
        text += f'{k} اسم المجموعة : {m.chat.title}\n'
        chatusr = '@' + m.chat.username if m.chat.username else 'مافيه'
        text += f'{k} يوزر المجموعة : {chatusr}\n'
        text += f'{k} ايدي المجموعة : `{m.chat.id}`'
        await rdb.srem(f'enablelist:{Dev_Zaid}', m.chat.id)
        await rdb.delete(f'{m.chat.id}:enable:{Dev_Zaid}')
        enablelist = await rdb.smembers(f'enablelist:{Dev_Zaid}')
        if enablelist:
            text += f'\n{k} عدد المجموعات الآن : {len(enablelist)}\n'
        text += f'\n{k} تم مسح جميع بيانات المجموعة'
        text += '\n\n☆'
        dev_group = await rdb.get(f'DevGroup:{Dev_Zaid}')
        if dev_group:
            await c.send_message(int(dev_group), text, disable_web_page_preview=True)
        else:
            for dev in await get_devs_br():
                try:
                    await c.send_message(int(dev), text, disable_web_page_preview=True)
                    await asyncio.sleep(3)
                except Exception as e:
                    logging.exception(e)
                    pass


@register("chat_member_update")
@Client.on_chat_member_updated(filters.group, group=5)
@safe_handler
async def ChatMemberUpdate(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')
    await get_bot_status(c, m, k)


async def get_bot_status(c, m, k):
    try:
        if m.new_chat_member.status == ChatMemberStatus.MEMBER:
            if m.new_chat_member.user.id == c.me.id:
                if await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
                    text = f'{k} من「 {m.from_user.mention} 」\n'
                    text += f'{k} تم تعطيل المجموعة تلقائياً\n☆'
                    await c.send_message(m.chat.id, text)
                    text = f'{k} من「 {m.from_user.mention} 」\n'
                    usrr = '@' + m.from_user.username if m.from_user.username else 'مافيه'
                    text += f'{k} يوزره : {usrr}\n'
                    text += f'{k} ايديه : `{m.from_user.id}`\n'
                    text += f'\n{k} قام بتنزيل البوت من الأدمن :\n\n'
                    text += f'{k} اسم المجموعة : {m.chat.title}\n'
                    chatusr = '@' + m.chat.username if m.chat.username else 'مافيه'
                    text += f'{k} يوزر المجموعة : {chatusr}\n'
                    text += f'{k} ايدي المجموعة : `{m.chat.id}`'
                    await rdb.srem(f'enablelist:{Dev_Zaid}', m.chat.id)
                    await rdb.delete(f'{m.chat.id}:enable:{Dev_Zaid}')
                    enablelist = await rdb.smembers(f'enablelist:{Dev_Zaid}')
                    if enablelist:
                        text += f'\n{k} عدد المجموعات الآن : {len(enablelist)}\n'
                    text += f'\n{k} تم مسح جميع بيانات المجموعة'
                    text += '\n\n☆'
                    dev_group = await rdb.get(f'DevGroup:{Dev_Zaid}')
                    if dev_group:
                        await c.send_message(int(dev_group), text)
                    else:
                        for dev in await get_devs_br():
                            try:
                                await c.send_message(int(dev), text, disable_web_page_preview=True)
                                await asyncio.sleep(3)
                            except Exception as e:
                                logging.exception(e)
                                pass

        if m.new_chat_member.status == ChatMemberStatus.ADMINISTRATOR:
            if m.new_chat_member.user.id == c.me.id:
                if await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
                    priv = m.new_chat_member.privileges
                    if not priv.can_manage_chat or not priv.can_delete_messages or not priv.can_restrict_members or not priv.can_pin_messages or not priv.can_invite_users:
                        text = f'{k} من「 {m.from_user.mention} 」\n'
                        text += f'{k} تم تعطيل المجموعة تلقائياً\n☆'
                        await c.send_message(m.chat.id, text)
                        await rdb.delete(f'{m.chat.id}:enable:{Dev_Zaid}')
                        text = f'{k} من「 {m.from_user.mention} 」\n'
                        usrr = '@' + m.from_user.username if m.from_user.username else 'مافيه'
                        text += f'{k} يوزره : {usrr}\n'
                        text += f'{k} ايديه : `{m.from_user.id}`\n'
                        text += f'\n{k} قام بتعديل صلاحية البوت بمجموعة :\n\n'
                        text += f'{k} اسم المجموعة : {m.chat.title}\n'
                        chatusr = '@' + m.chat.username if m.chat.username else 'مافيه'
                        text += f'{k} يوزر المجموعة : {chatusr}\n'
                        text += f'{k} ايدي المجموعة : `{m.chat.id}`'
                        enablelist = await rdb.smembers(f'enablelist:{Dev_Zaid}')
                        if enablelist:
                            text += f'\n{k} عدد المجموعات الآن : {len(enablelist)}\n'
                        text += f'\n{k} تم مسح جميع بيانات المجموعة'
                        text += '\n\n☆'
                        dev_group = await rdb.get(f'DevGroup:{Dev_Zaid}')
                        if dev_group:
                            await c.send_message(int(dev_group), text, disable_web_page_preview=True)
                        else:
                            for dev in await get_devs_br():
                                try:
                                    await c.send_message(int(dev), text, disable_web_page_preview=True)
                                    await asyncio.sleep(3)
                                except Exception as e:
                                    logging.exception(e)
                                    pass
                        return True

                if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
                    if await rdb.get(f'DisableBot:{Dev_Zaid}'):
                        return await c.send_message(m.chat.id, f'{k} تم تعطيل البوت الخدمي من المطور')
                    priv = m.new_chat_member.privileges
                    if priv.can_manage_chat and priv.can_delete_messages and priv.can_restrict_members and priv.can_pin_messages and priv.can_invite_users:
                        text = f'{k} من「 {m.from_user.mention} 」\n'
                        text += f'{k} تم تفعيل المجموعة تلقائياً\n☆'
                        await c.send_message(m.chat.id, text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Commands', url=f'https://t.me/{botUsername}?start=Commands')]]))
                        await rdb.set(f'{m.chat.id}:enable:{Dev_Zaid}', 1)
                        await rdb.sadd(f'enablelist:{Dev_Zaid}', m.chat.id)
                        await rdb.set(f'{m.chat.id}:rankOWNER:{m.from_user.id}{Dev_Zaid}', 1)
                        await rdb.sadd(f'{m.chat.id}:listOWNER:{Dev_Zaid}', m.from_user.id)
                        async for member in m.chat.get_members(filter=ChatMembersFilter.ADMINISTRATORS):
                            if not member.user.is_bot and not member.user.is_deleted:
                                if member.status == ChatMemberStatus.OWNER:
                                    await rdb.set(f'{m.chat.id}:rankGOWNER:{member.user.id}{Dev_Zaid}', 1)
                                    await rdb.sadd(f'{m.chat.id}:listGOWNER:{Dev_Zaid}', member.user.id)
                                    await rdb.sadd(f'{member.user.id}:groups', m.chat.id)
                                if member.status == ChatMemberStatus.ADMINISTRATOR:
                                    await rdb.set(f'{m.chat.id}:rankADMIN:{member.user.id}{Dev_Zaid}', 1)
                                    await rdb.sadd(f'{m.chat.id}:listADMIN:{Dev_Zaid}', member.user.id)
                        get = await c.get_chat(m.chat.id)
                        text = f'{k} من「 {m.from_user.mention} 」\n'
                        usrr = '@' + m.from_user.username if m.from_user.username else 'مافيه'
                        text += f'{k} يوزره : {usrr}\n'
                        text += f'{k} ايديه : `{m.from_user.id}`\n'
                        text += f'\n{k} تم تفعيل البوت بمجموعة جديدة :\n\n'
                        text += f'{k} اسم المجموعة : {m.chat.title}\n'
                        chatusr = '@' + m.chat.username if m.chat.username else 'مافيه'
                        text += f'{k} يوزر المجموعة : {chatusr}\n'
                        text += f'{k} ايدي المجموعة : `{m.chat.id}`'
                        if get.invite_link:
                            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(m.chat.title, url=get.invite_link)]])
                        else:
                            reply_markup = None
                        enablelist = await rdb.smembers(f'enablelist:{Dev_Zaid}')
                        if enablelist:
                            text += f'\n{k} عدد المجموعات الآن : {len(enablelist)}\n'
                        text += '\n\n☆'
                        dev_group = await rdb.get(f'DevGroup:{Dev_Zaid}')
                        if dev_group:
                            await c.send_message(int(dev_group), text, reply_markup=reply_markup, disable_web_page_preview=True)
                        else:
                            for dev in await get_devs_br():
                                try:
                                    await c.send_message(int(dev), text, disable_web_page_preview=True, reply_markup=reply_markup)
                                    await asyncio.sleep(3)
                                except Exception as e:
                                    logging.exception(e)
                                    pass
    except Exception as e:
        logging.exception(e)
        pass


@register("enable_disable_group")
@Client.on_message(filters.text & filters.group, group=6)
@safe_handler
async def EnableAndDisablegroup(c, m):
    text = m.text
    k = await rdb.get(f'{Dev_Zaid}:botkey')
    if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'): return

    if text == 'تفعيل':
        member = await m.chat.get_member(m.from_user.id)
        if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR] and not await owner_pls(m.from_user.id, m.chat.id):
            return await m.reply('ادري حلم الاعضاء تفعيل البوتات بس اسف')
        if await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
            return await m.reply(f'{k} المجموعة مفعلة من قبل يا حلو')
        if await rdb.get(f'DisableBot:{Dev_Zaid}'):
            return await c.send_message(m.chat.id, f'{k} تم تعطيل البوت الخدمي من المطور')
        get = await c.get_chat_member(m.chat.id, c.me.id)
        priv = get.privileges
        if not priv.can_manage_chat or not priv.can_delete_messages or not priv.can_pin_messages or not priv.can_invite_users:
            return await m.reply(f'{k} عطيني كل الصلاحيات بعدين ارسل تفعيل')
        else:
            await rdb.set(f'{m.chat.id}:enable:{Dev_Zaid}', 1)
            await rdb.sadd(f'enablelist:{Dev_Zaid}', m.chat.id)
            await rdb.set(f'{m.chat.id}:rankOWNER:{m.from_user.id}{Dev_Zaid}', 1)
            await rdb.sadd(f'{m.chat.id}:listOWNER:{Dev_Zaid}', m.from_user.id)
            await m.reply(f'{k} من「 {m.from_user.mention} 」\n{k} ابشر تم تفعيل المجموعة ورفعت كل الادمن\n☆', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Commands', url=f'https://t.me/{botUsername}?start=Commands')]]))
            async for member in m.chat.get_members(filter=ChatMembersFilter.ADMINISTRATORS):
                if not member.user.is_bot and not member.user.is_deleted:
                    if member.status == ChatMemberStatus.OWNER:
                        await rdb.set(f'{m.chat.id}:rankGOWNER:{member.user.id}{Dev_Zaid}', 1)
                        await rdb.sadd(f'{m.chat.id}:listGOWNER:{Dev_Zaid}', member.user.id)
                        await rdb.sadd(f'{member.user.id}:groups', m.chat.id)
                    if member.status == ChatMemberStatus.ADMINISTRATOR:
                        await rdb.set(f'{m.chat.id}:rankADMIN:{member.user.id}{Dev_Zaid}', 1)
                        await rdb.sadd(f'{m.chat.id}:listADMIN:{Dev_Zaid}', member.user.id)
            get = await c.get_chat(m.chat.id)
            text = f'{k} من「 {m.from_user.mention} 」\n'
            usrr = '@' + m.from_user.username if m.from_user.username else 'مافيه'
            text += f'{k} يوزره : {usrr}\n'
            text += f'{k} ايديه : `{m.from_user.id}`\n'
            text += f'\n{k} تم تفعيل البوت بمجموعة جديدة :\n\n'
            text += f'{k} اسم المجموعة : {m.chat.title}\n'
            chatusr = '@' + m.chat.username if m.chat.username else 'مافيه'
            text += f'{k} يوزر المجموعة : {chatusr}\n'
            text += f'{k} ايدي المجموعة : `{m.chat.id}`'
            enablelist = await rdb.smembers(f'enablelist:{Dev_Zaid}')
            if enablelist:
                text += f'\n{k} عدد المجموعات الآن : {len(enablelist)}\n'
            text += '\n\n☆'
            if get.invite_link:
                reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(m.chat.title, url=get.invite_link)]])
            else:
                reply_markup = None
            dev_group = await rdb.get(f'DevGroup:{Dev_Zaid}')
            if dev_group:
                await c.send_message(int(dev_group), text, reply_markup=reply_markup, disable_web_page_preview=True)
            else:
                for dev in await get_devs_br():
                    try:
                        await c.send_message(int(dev), text, disable_web_page_preview=True, reply_markup=reply_markup)
                        await asyncio.sleep(3)
                    except Exception as e:
                        logging.exception(e)
                        pass

    if text == 'تعطيل':
        member = await m.chat.get_member(m.from_user.id)
        if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR] and not await owner_pls(m.from_user.id, m.chat.id):
            return await m.reply('ادري حلم الاعضاء تعطيل البوتات بس اسف')
        else:
            if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
                return False
            else:
                await rdb.delete(f'{m.chat.id}:enable:{Dev_Zaid}', 1)
                await rdb.srem(f'enablelist:{Dev_Zaid}', m.chat.id)
                await m.reply(f'{k} من「 {m.from_user.mention} 」\n{k} تم تعطيل المجموعة\n☆')
                text = f'{k} من「 {m.from_user.mention} 」\n'
                usrr = '@' + m.from_user.username if m.from_user.username else 'مافيه'
                text += f'{k} يوزره : {usrr}\n'
                text += f'{k} ايديه : `{m.from_user.id}`\n'
                text += f'\n{k} تم تعطيل البوت بمجموعة جديدة :\n\n'
                text += f'{k} اسم المجموعة : {m.chat.title}\n'
                chatusr = '@' + m.chat.username if m.chat.username else 'مافيه'
                text += f'{k} يوزر المجموعة : {chatusr}\n'
                text += f'{k} ايدي المجموعة : `{m.chat.id}`'
                enablelist = await rdb.smembers(f'enablelist:{Dev_Zaid}')
                if enablelist:
                    text += f'\n{k} عدد المجموعات الآن : {len(enablelist)}\n'
                text += '\n\n☆'
                dev_group = await rdb.get(f'DevGroup:{Dev_Zaid}')
                if dev_group:
                    await c.send_message(int(dev_group), text)
                else:
                    for dev in await get_devs_br():
                        try:
                            await c.send_message(int(dev), text, disable_web_page_preview=True)
                            await asyncio.sleep(3)
                        except Exception as e:
                            logging.exception(e)
                            pass

    name = await rdb.get(f'{Dev_Zaid}:BotName') if await rdb.get(f'{Dev_Zaid}:BotName') else 'رعد'
    if text == f'{name} اطلعي' or text == f'{name} اطلع':
        leave_vids = [
            {'vid': 'https://t.me/D7BotResources/154', 'caption': 'غدرتو فيني'},
            {'vid': 'https://t.me/D7BotResources/155', 'caption': ':('},
            {'vid': 'https://t.me/D7BotResources/156', 'caption': 'يلا خلي البوتات الثانيه تدلعكم'},
            {'vid': 'https://t.me/D7BotResources/157', 'caption': 'اسف لي'},
            {'vid': 'https://t.me/D7BotResources/158', 'caption': 'قلي منهو لجل عينه تغيرت'},
            {'vid': 'https://t.me/D7BotResources/159', 'caption': 'واخيرا برتاح منكم يا نشبه العمر'}, ]
        if await owner_pls(m.from_user.id, m.chat.id):
            await rdb.delete(f'{m.chat.id}:enable:{Dev_Zaid}', 1)
            await rdb.srem(f'enablelist:{Dev_Zaid}', m.chat.id)
            vid = random.choice(leave_vids)
            await m.reply_video(vid['vid'], caption=vid['caption'])
            text = f'{k} من「 {m.from_user.mention} 」\n'
            usrr = '@' + m.from_user.username if m.from_user.username else 'مافيه'
            text += f'{k} يوزره : {usrr}\n'
            text += f'{k} ايديه : `{m.from_user.id}`\n'
            text += f'\n{k} طلعت من المجموعة بأمر منه :\n\n'
            text += f'{k} اسم المجموعة : {m.chat.title}\n'
            chatusr = '@' + m.chat.username if m.chat.username else 'مافيه'
            text += f'{k} يوزر المجموعة : {chatusr}\n'
            text += f'{k} ايدي المجموعة : `{m.chat.id}`'
            enablelist = await rdb.smembers(f'enablelist:{Dev_Zaid}')
            if enablelist:
                text += f'\n{k} عدد المجموعات الآن : {len(enablelist)}\n'
            text += '\n\n☆'
            await c.leave_chat(m.chat.id)
            dev_group = await rdb.get(f'DevGroup:{Dev_Zaid}')
            if dev_group:
                await c.send_message(int(dev_group), text)
            else:
                for dev in await get_devs_br():
                    try:
                        await c.send_message(int(dev), text, disable_web_page_preview=True)
                    except Exception as e:
                        logging.exception(e)
                        pass
