"""
Plugins/id.py — bmqa-v2

مُنقول من bmqa/Plugins/id.py (1026 سطر) → bmqa-v2/Plugins/id.py

الأوامر/المعالجات:
  - addmsgCount        (group=9,  filters.group)             — عدّاد رسائل كل عضو
  - addeditedmsgCount  (group=10, on_edited_message)          — عدّاد التعديلات
  - rankGetHandler     (group=11, filters.text & filters.group) — يستدعي get_my_rank مباشرة
      get_my_rank يغطي (نفس ترتيب/نص الأصل تماماً):
      مجموعاتي، انشائي/الانشاء/انشائه، اسمي، معلوماتي، بايو، المجموعه/المجموعة،
      جهاتي، افتاري/افتار (+رد+بالآيدي/اليوزر)، ايديي، رتبتي،
      مسح رسائلي/رسايلي، مسح تكليجاتي، تكليجاتي/تعديلاتي، رسايلي/رسائلي،
      رسايله/رسائلة (رد)، رتبته (رد)، نقل ملكية/ملكيه، مسح المتفاعلين/تصفير المتفاعلين،
      مسح القروبات/تصفير القروبات، ترتيبي/تفاعلي، المتفاعلين/توب المتفاعلين،
      القروبات/توب القروبات، كشف (رد / منشن / آيدي-يوزر)، صلاحياته (رد)/صلاحياتي،
      تدفقات تعيين/مسح/تفعيل/تعطيل الايدي (عادي وعام)، لقبي، ايدي/ id/ا (رد وبدون رد)
  - addContact         (group=1, filters.new_chat_members)   — عدّاد جهات الاتصال

ملاحظة: كتلة setIDHandler/set_id في الأصل (نهاية الملف، أسطر ~1002-1022) كانت
مُعطَّلة فعلياً في الكود الأصلي (محاطة بالكامل داخل triple-quoted string، أي
سلسلة نصية غير مُنفَّذة، وليست docstring توثيقي فقط) — لذلك لم تُنقل هنا، بما
أن الهدف هو نقل السلوك الفعلي فقط دون إضافة كود لم يكن يعمل أصلاً.

التحويلات المطبّقة:
  - `r.<op>` (Redis متزامن) -> `await rdb.<op>` (core/db.py)
  - `Thread(target=get_my_rank,...).start()` -> `await get_my_rank(c, m, k)` مباشرة
  - كل نداءات pyrogram المتزامنة (c.get_chat, c.get_chat_photos, c.invoke,
    m.chat.get_member, m.reply*, c.send_message, c.download_media, c.resolve_peer,
    c.stream_media) -> await / async for حسب الحالة
  - `m.chat.get_members(filter=ChatMembersFilter.ADMINISTRATORS)` في "نقل ملكية"
    -> `await members_cache.get_admins(...)` (core/cache.py) بدل نداء تيليجرام
    مباشر في كل مرة — هذا هو استدعاء قائمة الأعضاء/الأدمنية الوحيد في هذا
    الملف الذي يطابق شكل الكاش الحالي (مفتاحه (chat_id, filter)؛ راجع
    core/cache.py وPlugins/get_ranks.py لنفس النمط).
  - "كشف" (نسخة الرد على رسالة): الأصل كان يستدعي m.chat.get_member لنفس
    العضو مرتين متتاليتين (سطر 474 وسطر 486 في المصدر) للحصول على نفس
    النتيجة بالضبط — هنا استُدعيت مرة واحدة وأعيد استخدام النتيجة، فقط لتفادي
    نداء تيليجرام مكرر بلا داعٍ لنفس الطلب؛ core/cache.py نفسه لا يغطي هذه
    الحالة لأنه مخصص لقوائم get_chat_members فقط وليس get_member لعضو مفرد.
  - `from .games import get_emoji_bank` غير متاح بعد (games.py لم يُنقل إلى
    bmqa-v2 حتى الآن) — أُضيفت نسخة محلية مطابقة تماماً للأصل (_get_emoji_bank)
    في هذا الملف؛ يمكن حذفها والاستيراد من helpers لاحقاً عند نقل games.py.
  - @register + @safe_handler على الـ4 handlers الرئيسية (addmsgCount,
    addeditedmsgCount, rankGetHandler, addContact).

⚠️ حُفظت كل شروط الصلاحيات ونصوص الرسائل والمنطق المتسلسل (بما في ذلك
"علّة" حساب tfa3l بدون elif، المختلفة قليلاً بين "معلوماتي" و"ايدي") كما هي
تماماً في الأصل دون أي "تصحيح".
"""

import logging
import os
import random
import re
from io import BytesIO

from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus, ChatMembersFilter
from pyrogram.file_id import FileId, FileType, ThumbnailSource
from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.raw.functions.users import GetFullUser

from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from core.cache import members_cache
from helpers.get_create import get_creation_date
from helpers.ranks import (
    admin_pls,
    mod_pls,
    owner_pls,
    dev_pls,
    dev2_pls,
    devp_pls,
    get_rank,
    isLockCommand,
)


def get_top(users):
    users = [tuple(i.items()) for i in users]
    top = sorted(users, key=lambda i: i[-1][-1], reverse=True)
    top = [dict(i) for i in top]
    return top


def _get_emoji_bank(count):
    if count == 1:
        return '🥇 ) '
    if count == 2:
        return '🥈 ) '
    if count == 3:
        return '🥉 ) '
    else:
        return f' {count}  ) '


custom_ids = ['''
- ᴜѕᴇʀɴᴀᴍᴇ ➣ {اليوزر} .
- ᴍѕɢѕ ➣ {الرسائل} .
- ѕᴛᴀᴛѕ ➣ {الرتبه} .
- ʏᴏᴜʀ ɪᴅ ➣ {الايدي} .
- ᴇᴅɪᴛ ᴍsɢ ➣ {التعديل} .
- ᴅᴇᴛᴀɪʟs ➣ {التفاعل} .
-  ɢᴀᴍᴇ ➣ {المجوهرات} .
{البايو}
''', '''
• USE 𖦹 {اليوزر}
• MSG 𖥳 {الرسائل}
• STA 𖦹 {الرتبه}
• iD 𖥳 {الايدي}
{البايو}
''', '''
➞: 𝒔𝒕𝒂𓂅 {اليوزر} 𓍯
➞: 𝒖𝒔𝒆𝒓𓂅 {المعرف} 𓍯
➞: 𝒎𝒔𝒈𝒆𓂅 {الرسائل} 𓍯
➞: 𝒊𝒅 𓂅 {الايدي} 𓍯
{البايو}
''', '''
♡ : 𝐼𝐷 𖠀 {الايدي} .
♡ : 𝑈𝑆𝐸𝑅 𖠀 {اليوزر} .
♡ : 𝑀𝑆𝐺𝑆 𖠀 {الرسائل} .
♡ : 𝑆𝑇𝐴𝑇𝑆 𖠀 {الرتبه} .
♡ : 𝐸𝐷𝐼𝑇  𖠀 {التعديل} .
{البايو}
''', '''
- الايـدي || {الايدي}.
• الاسـم  || {الاسم}.
• المُعرف || {اليوزر}.
• الرُتبـه || {الرتبه}.
• الرسائل || {الرسائل}.
{البايو}
''', '''
⌁ NaMe ⇨ {الاسم}
⌁ Use ⇨ {اليوزر}
⌁ Msg ⇨ {الرسائل}
⌁ Sta ⇨ {الرتبه}
⌁ iD ⇨ {الايدي}
{البايو}
''', '''
📋¦ ɴᴀᴍᴇ ➺ {الاسم}
🗞¦ ʏᴏᴜʀ ɪᴅ ➺ {الايدي}
🔦¦ ᴜѕᴇʀɴᴀᴍᴇ ➺ {اليوزر}
🕹¦ ѕᴛᴀᴛѕ ➺ {الرتبه}
🔭¦ ᴅᴇᴛᴀɪʟs ➺ {التفاعل}
📨¦  ᴍѕɢѕ ➺ {الرسائل}
🎰¦ ɢᴀᴍᴇ ➺ {المجوهرات}
{البايو}
''', '''
✾ 𝐔𝐒𝐄 ⤷ {اليوزر}
✾ 𝐌𝐒𝐆 ⤷ {الرسائل}
✾ 𝐒𝐓𝐀 ⤷ {الرتبه}
✾ 𝐈𝐃 ⤷ {الايدي}
✾ 𝐁𝐈𝐎 ⤷ {البايو}
''', '''
𓆰 𝑼𝑬𝑺 : {اليوزر}
𓆰 𝑺𝑻𝑨 : {الرتبه}
𓆰 𝑰𝑫 : {الايدي}
𓆰 𝑴𝑺𝑮 : {الرسائل}
{البايو}''']


comments = [
    'تيكفه لاتكتب ايدي',
    'يع',
    'جبر',
    'احلى من يكتب ايدي',
    'افخم ايدي',
    'لحد يرسل ايدي من بعده',
    'يلبييه اطلق ايدي',
    'ازق ايدي',
    'لعد تكتب ايدي',
    'للاسف ايديك تلوث بصري ):',
    'جابك الله انت وأيديك على شكل جبر خاطر لقلبّي'
]


@register("id_addmsg_count")
@Client.on_message(filters.group, group=9)
@safe_handler
async def addmsgCount(c, m):
    if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):
        return
    if not await rdb.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.from_user.id}'):
        await rdb.set(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.from_user.id}', 1)
    else:
        get = int(await rdb.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.from_user.id}'))
        await rdb.set(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.from_user.id}', get + 1)
    await rdb.set(f"{m.from_user.id}:bankName", m.from_user.first_name[:25])


@register("id_addeditedmsg_count")
@Client.on_edited_message(filters.group, group=10)
@safe_handler
async def addeditedmsgCount(c, m):
    if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):
        return
    if not await rdb.get(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}'):
        await rdb.set(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}', 1)
    else:
        get = int(await rdb.get(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}'))
        await rdb.set(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}', get + 1)


@register("id_rank_get")
@Client.on_message(filters.text & filters.group, group=11)
@safe_handler
async def rankGetHandler(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')
    await get_my_rank(c, m, k)


async def get_my_rank(c, m, k):
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

    if text == 'مجموعاتي':
        if not await rdb.smembers(f'{m.from_user.id}:groups'):
            return await m.reply(f'{k} ماعندك مجموعات')
        else:
            groups = len(await rdb.smembers(f'{m.from_user.id}:groups'))
            return await m.reply(f'{k} عدد مجموعاتك ↼ ( {groups} )')

    if text == 'انشائي':
        create_date = await get_creation_date(m.from_user.id)
        return await m.reply(f'{k} الانشاء ( {create_date} )')

    if text == 'الانشاء' and not m.reply_to_message:
        create_date = await get_creation_date(m.from_user.id)
        return await m.reply(f'{k} الانشاء ( {create_date} )')

    if (text == 'الانشاء' or text == 'انشائه') and m.reply_to_message:
        create_date = await get_creation_date(m.reply_to_message.from_user.id)
        return await m.reply(f'{k} الانشاء ( {create_date} )')

    if text == 'اسمي':
        return await m.reply(m.from_user.first_name, disable_web_page_preview=True)

    if text == 'معلوماتي':
        msgs = int(await rdb.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.from_user.id}'))
        if msgs > 50:
            tfa3l = 'شد حيلك'
        if msgs > 500:
            tfa3l = 'يجي منك'
        if msgs > 750:
            tfa3l = 'تفاعل متوسط'
        if msgs > 2500:
            tfa3l = 'متفاعل'
        if msgs > 5000:
            tfa3l = 'اسطورة التفاعل'
        if msgs > 10000:
            tfa3l = 'كنق التلي'
        else:
            tfa3l = 'تفاعل صفر'
        if not await rdb.get(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}'):
            edits = 0
        else:
            edits = int(await rdb.get(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}'))
        if not await rdb.get(f'{m.chat.id}TotalContacts{m.from_user.id}{Dev_Zaid}'):
            contacts = 0
        else:
            contacts = int(await rdb.get(f'{m.chat.id}TotalContacts{m.from_user.id}{Dev_Zaid}'))
        if m.from_user.username:
            username = f'@{m.from_user.username}'
        if m.from_user.usernames:
            username = ''
            for i in m.from_user.usernames:
                username += f"@{i.username} "
        else:
            username = 'مافي يوزر'
        rank = await get_rank(m.from_user.id, m.chat.id)
        text = f'''
المعلومات
الاسم ↼ {m.from_user.mention}
اليوزر ↼ {username}
الايدي  ↼ ( `{m.from_user.id}` )
الرتبه ↼ {rank}
┄─┅═ـ═┅─┄
احصائيات الرسايل
الرسايل ↼ ( {msgs} )
التعديل ↼ ( {edits} )
التفاعل ↼ {tfa3l}
'''
        return await m.reply(text)

    if text == 'بايو' and m.reply_to_message and m.reply_to_message.from_user:
        if await rdb.get(f'{m.chat.id}:disableBio:{Dev_Zaid}'):
            return
        get = await c.get_chat(m.reply_to_message.from_user.id)
        if not get.bio:
            return await m.reply(f'{k} ماعنده بايو')
        else:
            return await m.reply(f'`{get.bio}`')

    if text == 'بايو' and not m.reply_to_message:
        if await rdb.get(f'{m.chat.id}:disableBio:{Dev_Zaid}'):
            return
        get = await c.get_chat(m.from_user.id)
        if not get.bio:
            return await m.reply(f'{k} ماعندك بايو')
        else:
            return await m.reply(f'`{get.bio}`')

    if text == 'المجموعه' or text == 'المجموعة':
        get = await c.invoke(GetFullChannel(channel=await c.resolve_peer(m.chat.id)))
        if get.full_chat.exported_invite:
            link = get.full_chat.exported_invite.link
        else:
            link = 'مافي رابط'
        admins = get.full_chat.admins_count
        kicked = get.full_chat.kicked_count
        count = get.full_chat.participants_count
        if m.chat.photo:
            type = 'photo'
            if m.chat.username:
                photo = f'https://t.me/{m.chat.username}'
            else:
                photo = await c.download_media(m.chat.photo.big_file_id)
        else:
            type = 'text'
        text = f'معلومات المجموعة:\n\n{k} الاسم ↢ {m.chat.title}\n{k} الايدي ↢ ( `{m.chat.id}` )\n{k} عدد الاعضاء ↢ ( {count} )\n{k} عدد المشرفين ↢ ( {admins} )\n{k} عدد المحظورين ↢ ( {kicked} )\n{k} الرابط ↢ {link} '
        if type == 'photo':
            await m.reply_photo(photo, caption=text)
            try:
                os.remove(photo)
            except Exception as e:
                logging.exception(e)
                pass
            return
        else:
            return await m.reply(text, disable_web_page_preview=True)

    if text == 'جهاتي':
        if not await rdb.get(f'{m.chat.id}TotalContacts{m.from_user.id}{Dev_Zaid}'):
            contacts = 0
        else:
            contacts = int(await rdb.get(f'{m.chat.id}TotalContacts{m.from_user.id}{Dev_Zaid}'))
        return await m.reply(f'{k} عدد جهاتك ↢ ( {contacts} )')

    if text == 'افتاري':
        if await rdb.get(f'{m.chat.id}:disableAV:{Dev_Zaid}'):
            return False
        if not m.from_user.photo:
            return await m.reply(f'{k} ماقدر اجيب افتارك ارسل نقطه خاص وارجع جرب')
        else:
            if m.from_user.username:
                photo = f'http://t.me/{m.from_user.username}'
            else:
                async for p in c.get_chat_photos(m.from_user.id, limit=1):
                    photo = p.file_id
            get_chat = await c.get_chat(m.from_user.id)
            get_bio = get_chat.bio
            if not get_bio:
                caption = None
            else:
                caption = f'`{get_bio}`'
            return await m.reply_photo(photo, caption=caption)

    if text == 'افتار' and m.reply_to_message and m.reply_to_message.from_user:
        if await rdb.get(f'{m.chat.id}:disableAV:{Dev_Zaid}'):
            return False
        if not m.reply_to_message.from_user.photo:
            return await m.reply(f'{k} مقدر اجيب افتاره يمكن حاظرني')
        else:
            if m.reply_to_message.from_user.username:
                photo = f'http://t.me/{m.reply_to_message.from_user.username}'
            else:
                async for p in c.get_chat_photos(m.reply_to_message.from_user.id, limit=1):
                    photo = p.file_id
            get_chat = await c.get_chat(m.reply_to_message.from_user.id)
            get_bio = get_chat.bio
            if not get_bio:
                caption = None
            else:
                caption = f'`{get_bio}`'
            return await m.reply_photo(photo, caption=caption)

    if text == 'ايديي':
        return await m.reply(f'( `{m.from_user.id}` )')

    if text.startswith('افتار') and len(text.split()) == 2:
        if await rdb.get(f'{m.chat.id}:disableAV:{Dev_Zaid}'):
            return False
        try:
            user = int(text.split()[1])
        except Exception as e:
            logging.exception(e)
            user = text.split()[1]
        try:
            get = await c.get_chat(user)
            if get.photo:
                async for p in c.get_chat_photos(get.id, limit=1):
                    photo = p.file_id
                if get.bio:
                    caption = f'`{get.bio}`'
                else:
                    caption = None
                return await m.reply_photo(photo, caption=caption)
        except Exception as e:
            logging.exception(e)
            print(e)
            return

    if text == 'رتبتي':
        rank = await get_rank(m.from_user.id, m.chat.id)
        await m.reply(f'{k} رتبتك ↢ {rank}')

    if text == 'مسح رسائلي' or text == 'مسح رسايلي':
        msgs = int(await rdb.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.from_user.id}'))
        await rdb.delete(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.from_user.id}')
        return await m.reply(f'{k} ابشر مسحت ( {msgs} ) من رسائلك')

    if text == 'مسح تكليجاتي':
        if not await rdb.get(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}'):
            return await m.reply(f'{k} عدد تكليجاتك ↢ ( 0 )')
        msgs = int(await rdb.get(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}'))
        await rdb.delete(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}')
        return await m.reply(f'{k} ابشر مسحت ( {msgs} ) من تكليجاتك')

    if text == 'تكليجاتي' or text == 'تعديلاتي':
        if not await rdb.get(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}'):
            return await m.reply(f'{k} عدد تكليجاتك ↢ ( 0 )')
        msgs = int(await rdb.get(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}'))
        return await m.reply(f'{k} عدد تكليجاتك ↢ ( {msgs} )')

    if text == 'رسايلي' or text == 'رسائلي':
        msgs = int(await rdb.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.from_user.id}'))
        return await m.reply(f'{k} عدد رسايلك ↢ ( {msgs} )')

    if (text == 'رسايله' or text == 'رسائلة') and m.reply_to_message and m.reply_to_message.from_user:
        msgs = int(await rdb.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.reply_to_message.from_user.id}'))
        return await m.reply(f'{k} عدد رسايله ↢ ( {msgs} )')

    if text == 'رتبته' and m.reply_to_message and m.reply_to_message.from_user:
        rank = await get_rank(m.reply_to_message.from_user.id, m.chat.id)
        member = await m.chat.get_member(m.reply_to_message.from_user.id)
        status = member.status
        if status == ChatMemberStatus.OWNER:
            rank2 = 'المالك'
        if status == ChatMemberStatus.ADMINISTRATOR:
            rank2 = 'مشرف'
        if status == ChatMemberStatus.RESTRICTED:
            rank2 = 'مقيد'
        if status == ChatMemberStatus.LEFT:
            rank2 = 'طالع'
        if status == ChatMemberStatus.MEMBER:
            rank2 = 'عضو'
        if status == ChatMemberStatus.BANNED:
            rank2 = 'لاقم حظر'
        await m.reply(f'رتبته:\n{k} في البوت ( {rank} )\n{k} في المجموعة ( {rank2} )\n-')

    if text == 'نقل ملكية' or text == 'نقل ملكيه':
        if await rdb.get(f'{m.chat.id}:rankGOWNER:{m.from_user.id}{Dev_Zaid}'):
            caller = await m.chat.get_member(m.from_user.id)
            status = caller.status
            if status == ChatMemberStatus.OWNER:
                return await m.reply(f'{k} انت مالك القروب')
            else:
                admins = await members_cache.get_admins(c, m.chat.id, ChatMembersFilter.ADMINISTRATORS)
                for member in admins:
                    if member.status == ChatMemberStatus.OWNER:
                        if member.user.is_deleted:
                            return await m.reply(f'{k} حساب المالك محذوف')
                        else:
                            await rdb.delete(f'{m.chat.id}:rankGOWNER:{m.from_user.id}{Dev_Zaid}')
                            await rdb.srem(f'{m.chat.id}:listGOWNER:{Dev_Zaid}', m.from_user.id)
                            await rdb.set(f'{m.chat.id}:rankGOWNER:{member.user.id}{Dev_Zaid}', 1)
                            await rdb.sadd(f'{m.chat.id}:listGOWNER:{Dev_Zaid}', member.user.id)
                            members_cache.invalidate_chat(m.chat.id)
                            return await m.reply(f'「 {member.user.mention} 」\n{k} نقلت له ملكية المجموعة')

    if text == "مسح المتفاعلين" or text == "تصفير المتفاعلين":
        if not await owner_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} عذراً الامر يخص ↤〖 المالك 〗فقط .')
        else:
            keys = await rdb.keys(f"{Dev_Zaid}{m.chat.id}:TotalMsgs:*")
            for _ in keys:
                await rdb.delete(_)
            return await m.reply(f"{k} ابشر مسحت كل المتفاعلين")

    if text == "مسح القروبات" or text == "تصفير القروبات":
        if not await devp_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} عذراً الامر يخص ↤〖 Dev🎖️ 〗فقط .')
        else:
            keys = await rdb.keys(f"{Dev_Zaid}:TotalGroupMsgs:*")
            for _ in keys:
                await rdb.delete(_)
            return await m.reply(f"{k} ابشر مسحت توب القروبات")

    if text == "ترتيبي" or text == "تفاعلي":
        users = await rdb.keys(f"{Dev_Zaid}{m.chat.id}:TotalMsgs:*")
        jj = []
        for user in users:
            try:
                id = int(user.split("TotalMsgs:")[1])
                msgs = await rdb.get(user)
                jj.append({"id": id, "msgs": int(msgs)})
            except Exception as e:
                logging.exception(e)
                pass
        top = get_top(jj)
        ids = [i["id"] for i in top]
        rank = ids.index(m.from_user.id) + 1
        msgs = int(await rdb.get(f"{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.from_user.id}"))
        return await m.reply(f"{k} ترتيبك بالمتفاعلين ↢ ( {rank} )\n{k} رسائلك بالتفاعل ↢ ( {msgs:,} )\n-")

    if text == "المتفاعلين" or text == "توب المتفاعلين":
        users = await rdb.keys(f"{Dev_Zaid}{m.chat.id}:TotalMsgs:*")
        jj = []
        for user in users:
            try:
                id = int(user.split("TotalMsgs:")[1])
                msgs = await rdb.get(user)
                name = await rdb.get(f"{id}:bankName") or str(id)
                jj.append({"name": name, "id": id, "msgs": int(msgs)})
            except Exception as e:
                logging.exception(e)
                pass
        top = get_top(jj)
        text = "- توب اكثر 20 متفاعل :\n━━━━━━━━━\n"
        count = 1
        for i in top:
            if count == 21:
                break
            emoji = _get_emoji_bank(count)
            text += f"{emoji}{i['msgs']:,} l [{i['name']}](tg://user?id={i['id']})\n"
            count += 1
        return await c.send_message(m.chat.id, text, disable_web_page_preview=True, reply_to_message_id=m.id)

    if text == "القروبات" or text == "توب القروبات":
        groups = await rdb.keys(f"{Dev_Zaid}:TotalGroupMsgs:*")
        result = []

        for group in groups:
            try:
                chat_id = int(group.split("TotalGroupMsgs:")[1])
                msgs = await rdb.get(group)
                group_chat = await c.get_chat(chat_id)
                group_title = group_chat.title
                result.append({"group_title": group_title, "chat_id": chat_id, "msgs": int(msgs)})
            except Exception as e:
                logging.exception(e)
                pass

        top_groups = get_top(result)
        response_text = "- توب اكثر 20 قروب متفاعل:\n━━━━━━━━━\n"
        count = 1

        for group in top_groups:
            if count == 21:
                break
            emoji = _get_emoji_bank(count)
            response_text += f"{emoji}{group['msgs']:,} l {group['group_title']}\n"
            count += 1

        return await c.send_message(m.chat.id, response_text, disable_web_page_preview=True, reply_to_message_id=m.id)

    if text == 'كشف' and m.reply_to_message and m.reply_to_message.from_user:
        try:
            get = await m.chat.get_member(m.reply_to_message.from_user.id)
            rank = await get_rank(m.reply_to_message.from_user.id, m.chat.id)
            name = m.reply_to_message.from_user.first_name
            msgs = int(await rdb.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.reply_to_message.from_user.id}'))
            id = m.reply_to_message.from_user.id
            if m.reply_to_message.from_user.username:
                username = f'@{m.reply_to_message.from_user.username}'
            elif m.reply_to_message.from_user.usernames:
                username = ''
                for i in m.reply_to_message.from_user.usernames:
                    username += f"@{i.username} "
            else:
                username = 'مافي يوزر'
            status = get.status
            if status == ChatMemberStatus.OWNER:
                rank2 = 'المالك'
            if status == ChatMemberStatus.ADMINISTRATOR:
                rank2 = 'مشرف'
            if status == ChatMemberStatus.RESTRICTED:
                rank2 = 'مقيد'
            if status == ChatMemberStatus.LEFT:
                rank2 = 'طالع'
            if status == ChatMemberStatus.MEMBER:
                rank2 = 'عضو'
            if status == ChatMemberStatus.BANNED:
                rank2 = 'لاقم حظر'
            text = f'''
{k} الاسم ↢ {name}
{k} الايدي ↢ ( `{id}` )
{k} اليوزر ↢ ( {username} )
{k} الرتبه ↢ ( {rank} )
{k} الرسائل ↢ ( {msgs} )
{k} بالمجموعة ↢ ( {rank2} )
{k} نوع الكشف ↢ بالرد
-
'''
            return await m.reply(text, disable_web_page_preview=True)
        except Exception as e:
            logging.exception(e)
            return await m.reply(f'{k} العضو مو بالمجموعة')

    if text.startswith('كشف') and len(text.split()) > 1 and 'tg://user?id=' in m.text.html:
        print(m.text.html)
        user = int(re.search(r'href="([^"]+)', m.text.html).group(1).split('=')[1])
        ks = 'بالمنشن'
        try:
            get = await m.chat.get_member(user)
            name = get.user.first_name
            id = get.user.id
            msgs = int(await rdb.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{get.user.id}'))
            if get.user.username:
                username = f'@{get.user.username}'
            elif get.user.usernames:
                username = ""
                for i in get.user.usernames:
                    username += f"@{i.username} "
            else:
                username = 'ماعنده يوزر'
            status = get.status
            if status == ChatMemberStatus.OWNER:
                rank = 'المالك'
            if status == ChatMemberStatus.ADMINISTRATOR:
                rank = 'مشرف'
            if status == ChatMemberStatus.RESTRICTED:
                rank = 'مقيد'
            if status == ChatMemberStatus.LEFT:
                rank = 'طالع'
            if status == ChatMemberStatus.MEMBER:
                rank = 'عضو'
            if status == ChatMemberStatus.BANNED:
                rank = 'لاقم حظر'
        except Exception as e:
            logging.exception(e)
            rank = 'طالع'
            try:
                get = await c.get_chat(user)
                name = get.first_name
                id = get.id
                msgs = int(await rdb.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{get.id}'))
                if get.user.username:
                    username = f'@{get.user.username}'
                if get.user.usernames:
                    username = ""
                    for i in get.user.usernames:
                        username += f"@{i.username} "
                else:
                    username = 'ماعنده يوزر'
            except Exception as e:
                logging.exception(e)
                print(e)
                return
        rank2 = await get_rank(id, m.chat.id)
        text = f'''
{k} الاسم ↢ {name}
{k} الايدي ↢ ( `{id}` )
{k} اليوزر ↢ ( {username} )
{k} الرتبه ↢ ( {rank2} )
{k} الرسائل ↢ ( {msgs} )
{k} بالمجموعة ↢ ( {rank} )
{k} نوع الكشف ↢ {ks}
-
        '''
        return await m.reply(text, disable_web_page_preview=True)

    if text.startswith('كشف') and len(text.split()) == 2:
        try:
            user = int(text.split()[1])
            ks = 'بالايدي'
        except Exception as e:
            logging.exception(e)
            user = text.split()[1].replace('@', '')
            ks = 'باليوزر'
        try:
            get = await m.chat.get_member(user)
            name = get.user.first_name
            id = get.user.id
            msgs = int(await rdb.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{get.user.id}'))
            if get.user.username:
                username = f'@{get.user.username}'
            elif get.user.usernames:
                username = ""
                for i in get.user.usernames:
                    username += f"@{i.username} "
            else:
                username = 'ماعنده يوزر'
            status = get.status
            if status == ChatMemberStatus.OWNER:
                rank = 'المالك'
            if status == ChatMemberStatus.ADMINISTRATOR:
                rank = 'مشرف'
            if status == ChatMemberStatus.RESTRICTED:
                rank = 'مقيد'
            if status == ChatMemberStatus.LEFT:
                rank = 'طالع'
            if status == ChatMemberStatus.MEMBER:
                rank = 'عضو'
            if status == ChatMemberStatus.BANNED:
                rank = 'لاقم حظر'
        except Exception as e:
            logging.exception(e)
            rank = 'طالع'
            try:
                get = await c.get_chat(user)
                name = get.first_name
                id = get.id
                msgs = int(await rdb.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{get.id}'))
                if get.user.username:
                    username = f'@{get.user.username}'
                if get.user.usernames:
                    username = ""
                    for i in get.user.usernames:
                        username += f"@{i.username} "
                else:
                    username = 'ماعنده يوزر'
            except Exception as e:
                logging.exception(e)
                print(e)
                return
        rank2 = await get_rank(id, m.chat.id)
        text = f'''
{k} الاسم ↢ {name}
{k} الايدي ↢ ( `{id}` )
{k} اليوزر ↢ ( {username} )
{k} الرتبه ↢ ( {rank2} )
{k} الرسائل ↢ ( {msgs} )
{k} بالمجموعة ↢ ( {rank} )
{k} نوع الكشف ↢ {ks}
-
        '''
        return await m.reply(text, disable_web_page_preview=True)

    if text == 'صلاحياته' and m.reply_to_message and m.reply_to_message.from_user:
        get = await m.chat.get_member(m.reply_to_message.from_user.id)
        if get.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return await m.reply(f'{k} هو العضو وما عنده صلاحيات')
        if get.status == ChatMemberStatus.OWNER:
            return await m.reply(f'{k} هو المالك وعنده كل الصلاحيات')
        if get.status == ChatMemberStatus.ADMINISTRATOR:
            p = get.privileges
            p1 = "✔️" if p.can_manage_chat else "✖️"
            p2 = "✔️" if p.can_delete_messages else "✖️"
            p3 = "✔️" if p.can_manage_video_chats else "✖️"
            p4 = "✔️" if p.can_restrict_members else "✖️"
            p5 = "✔️" if p.can_promote_members else "✖️"
            p6 = "✔️" if p.can_change_info else "✖️"
            p7 = "✔️" if p.can_pin_messages else "✖️"
            text = f'''
{k} هو مشرف وهذي صلاحياته :

1) - ادارة المجموعة ↼ ( {p1} )
2) - مسح الرسائل ↼ ( {p2} )
3) - ادارة مكالمات ↼ ( {p3} )
4) - تقييد الأعضاء وحظرهم ↼ ( {p4} )
5) - رفع المشرفين ↼ ( {p5} )
6) - تعديل معلومات المجموعة ↼ ( {p6} )
7) - تثبيت الرسايل ↼ ( {p7} )


'''
            return await m.reply(text)

    if text == 'صلاحياتي':
        get = await m.chat.get_member(m.from_user.id)
        if get.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return await m.reply(f'{k} انت العضو وماعندك صلاحيات')
        if get.status == ChatMemberStatus.OWNER:
            return await m.reply(f'{k} انت المالك وعندك كل الصلاحيات')
        if get.status == ChatMemberStatus.ADMINISTRATOR:
            p = get.privileges
            p1 = "✔️" if p.can_manage_chat else "✖️"
            p2 = "✔️" if p.can_delete_messages else "✖️"
            p3 = "✔️" if p.can_manage_video_chats else "✖️"
            p4 = "✔️" if p.can_restrict_members else "✖️"
            p5 = "✔️" if p.can_promote_members else "✖️"
            p6 = "✔️" if p.can_change_info else "✖️"
            p7 = "✔️" if p.can_pin_messages else "✖️"
            text = f'''
{k} انت مشرف وهذي صلاحياتك :

1) - ادارة المجموعة ↼ ( {p1} )
2) - مسح الرسائل ↼ ( {p2} )
3) - ادارة مكالمات ↼ ( {p3} )
4) - تقييد الأعضاء وحظرهم ↼ ( {p4} )
5) - رفع المشرفين ↼ ( {p5} )
6) - تعديل معلومات المجموعة ↼ ( {p6} )
7) - تثبيت الرسايل ↼ ( {p7} )


'''
            return await m.reply(text)

    if await rdb.get(f'{m.chat.id}:addCustomID:{m.from_user.id}{Dev_Zaid}') and text == 'الغاء':
        await rdb.delete(f'{m.chat.id}:addCustomID:{m.from_user.id}{Dev_Zaid}')
        await m.reply(f'{k} ابشر تم الغاء تعيين الايدي ')
        return

    if await rdb.get(f'{m.chat.id}:addCustomIDG:{m.from_user.id}{Dev_Zaid}') and text == 'الغاء':
        await rdb.delete(f'{m.chat.id}:addCustomIDG:{m.from_user.id}{Dev_Zaid}')
        await m.reply(f'{k} ابشر تم الغاء تعيين الايدي عام')
        return

    if await rdb.get(f'{m.chat.id}:addCustomIDG:{m.from_user.id}{Dev_Zaid}') and await dev_pls(m.from_user.id, m.chat.id):
        await rdb.set(f'customID:{Dev_Zaid}', m.text)
        await m.reply(f'{k} وسوينا الايدي العام\n{k} يمديك تجرب شكل الايدي الجديد الحين')
        await rdb.delete(f'{m.chat.id}:addCustomIDG:{m.from_user.id}{Dev_Zaid}')
        return

    if await rdb.get(f'{m.chat.id}:addCustomID:{m.from_user.id}{Dev_Zaid}') and await mod_pls(m.from_user.id, m.chat.id):
        await rdb.set(f'{m.chat.id}:customID:{Dev_Zaid}', m.text)
        await m.reply(f'{k} وسوينا الايدي\n{k} يمديك تجرب شكل الايدي الجديد الحين')
        await rdb.delete(f'{m.chat.id}:addCustomID:{m.from_user.id}{Dev_Zaid}')
        return

    if text == 'مسح الايدي':
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} عذراً الامر يخص ↤〖 المدير 〗فقط .')
        if not await rdb.get(f'{m.chat.id}:customID:{Dev_Zaid}'):
            return await m.reply(f'{k} الايدي مو معدل')
        else:
            await m.reply(f'{k} ابشر مسحت الايدي')
            await rdb.delete(f'{m.chat.id}:customID:{Dev_Zaid}')
            return

    if text == 'مسح الايدي العام' or text == 'مسح الايدي عام':
        if not await dev2_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} عذراً الامر يخص ↤〖 Dev²🎖 〗فقط .')
        if not await rdb.get(f'customID:{Dev_Zaid}'):
            return await m.reply(f'{k} الايدي العام مو معدل')
        else:
            await m.reply(f'{k} ابشر مسحت الايدي العام')
            await rdb.delete(f'customID:{Dev_Zaid}')

    if text == 'الايدي':
        if not await mod_pls(m.from_user.id, m.chat.id):
            return
        if not await rdb.get(f'{m.chat.id}:customID:{Dev_Zaid}'):
            return await m.reply(f'{k} الايدي مو معدل')
        else:
            id = await rdb.get(f'{m.chat.id}:customID:{Dev_Zaid}')
            return await m.reply(f'`{id}`')

    if text == 'الايدي العام':
        if not await dev2_pls(m.from_user.id, m.chat.id):
            return
        if not await rdb.get(f'customID:{Dev_Zaid}'):
            return await m.reply(f'{k} الايدي العام مو معدل')
        else:
            id = await rdb.get(f'customID:{Dev_Zaid}')
            return await m.reply(f'`{id}`')

    if text == 'تغيير الايدي':
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} عذراً الامر يخص ↤〖 المدير 〗فقط .')
        else:
            id = random.choice(custom_ids)
            await rdb.set(f'{m.chat.id}:customID:{Dev_Zaid}', id)
            await m.reply(f'{k} وسوينا الايدي\n{k} يمديك تجرب شكل الايدي الجديد الحين')

    if text == 'تعيين الايدي':
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} عذراً الامر يخص ↤〖 المدير 〗فقط .')
        reply = '''
تمام , الحين ارسل شكل الايدي الجديد

- الاختصارات:

{الاسم} ↼ يطلع اسم الشخص
{الايدي} ↼ يطلع ايدي الشخص
{اليوزر} ↼ يطلع يوزر الشخص
{الرتبه} ↼ يطلع رتبته الشخص
{التفاعل} ↼ يطلع تفاعل الشخص
{الرسائل} ↼ يطلع كم رسالة عند الشخص
{التعديل} ↼ يطلع كم مره عدل الشخص
{البايو} ↼ يطلع البايو اللي كاتبه
{تعليق} ↼ يطلع تعليق عشوائي
{الانشاء} ↼ يطلع انشاء الحساب

قناة اشكال الايدي https://t.me/EFFB0T/187

'''
        await m.reply(reply)
        await rdb.set(f'{m.chat.id}:addCustomID:{m.from_user.id}{Dev_Zaid}', 1)
        return
    if text == 'تعيين الايدي عام':
        if not await dev2_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} عذراً الامر يخص ↤〖 Dev²🎖 〗فقط .')
        reply = '''
تمام , الحين ارسل شكل الايدي الجديد

- الاختصارات:

{الاسم} ↼ يطلع اسم الشخص
{الايدي} ↼ يطلع ايدي الشخص
{اليوزر} ↼ يطلع يوزر الشخص
{الرتبه} ↼ يطلع رتبته الشخص
{التفاعل} ↼ يطلع تفاعل الشخص
{الرسائل} ↼ يطلع كم رسالة عند الشخص
{التعديل} ↼ يطلع كم مره عدل الشخص
{البايو} ↼ يطلع البايو اللي كاتبه
{تعليق} ↼ يطلع تعليق عشوائي
{الانشاء} ↼ يطلع انشاء الحساب

قناة اشكال الايدي https://t.me/EFFB0T/187
'''
        await m.reply(reply)
        await rdb.set(f'{m.chat.id}:addCustomIDG:{m.from_user.id}{Dev_Zaid}', 1)
        return True

    if text == 'تفعيل الايدي':
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} عذراً الامر يخص ↤〖 الادمن 〗فقط .')
        else:
            if not await rdb.get(f'{m.chat.id}:disableID:{Dev_Zaid}'):
                return await m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} الايدي مفعل من قبل')
            else:
                await rdb.delete(f'{m.chat.id}:disableID:{Dev_Zaid}')
                return await m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} ابشر فعلت الايدي')

    if text == 'تعطيل الايدي':
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} عذراً الامر يخص ↤〖 الادمن 〗فقط .')
        else:
            if await rdb.get(f'{m.chat.id}:disableID:{Dev_Zaid}'):
                return await m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} الايدي معطل من قبل')
            else:
                await rdb.set(f'{m.chat.id}:disableID:{Dev_Zaid}', 1)
                return await m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} ابشر عطلت الايدي')

    if text == 'تفعيل افتاري':
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} عذراً الامر يخص ↤〖 الادمن 〗فقط .')
        else:
            if not await rdb.get(f'{m.chat.id}:disableAV:{Dev_Zaid}'):
                return await m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} افتار مفعل من قبل')
            else:
                await rdb.delete(f'{m.chat.id}:disableAV:{Dev_Zaid}')
                return await m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} ابشر فعلت افتار')

    if text == 'تعطيل افتاري':
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} عذراً الامر يخص ↤〖 الادمن 〗فقط .')
        else:
            if await rdb.get(f'{m.chat.id}:disableAV:{Dev_Zaid}'):
                return await m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} افتار معطل من قبل')
            else:
                await rdb.set(f'{m.chat.id}:disableAV:{Dev_Zaid}', 1)
                return await m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} ابشر عطلت افتار')

    if text == 'تعطيل الايدي بالصوره':
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} عذراً الامر يخص ↤〖 الادمن 〗فقط .')
        else:
            if await rdb.get(f'{m.chat.id}:disableIDPHOTO:{Dev_Zaid}'):
                return await m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} الايدي بالصوره معطل من قبل')
            else:
                await rdb.set(f'{m.chat.id}:disableIDPHOTO:{Dev_Zaid}', 1)
                return await m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} ابشر عطلت الايدي بالصوره')

    if text == 'تفعيل الايدي بالصوره':
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} عذراً الامر يخص ↤〖 الادمن 〗فقط .')
        else:
            if not await rdb.get(f'{m.chat.id}:disableIDPHOTO:{Dev_Zaid}'):
                return await m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} الايدي بالصوره مفعل من قبل')
            else:
                await rdb.delete(f'{m.chat.id}:disableIDPHOTO:{Dev_Zaid}')
                return await m.reply(f'{k} بواسطة ↤ {m.from_user.mention}\n{k} ابشر فعلت الايدي بالصوره')

    if text == "لقبي":
        member = await m.chat.get_member(m.from_user.id)
        title = member.custom_title
        if not title:
            return await m.reply(f"{k} ماعندك لقب")
        else:
            return await m.reply(f"{k} لقبك ↢ ( {title} )")

    if (text == 'ايدي' or text.lower() == 'ا') and m.reply_to_message and m.reply_to_message.from_user:
        return await m.reply(f'الايدي ↢ ( `{m.reply_to_message.from_user.id}` )')

    if (text == 'ايدي' or text.lower() == 'id') and not m.reply_to_message:
        if await rdb.get(f'{m.chat.id}:disableID:{Dev_Zaid}'):
            return
        if await rdb.get(f'{m.chat.id}:customID:{Dev_Zaid}'):
            id = await rdb.get(f'{m.chat.id}:customID:{Dev_Zaid}')
        else:
            if await rdb.get(f'customID:{Dev_Zaid}'):
                id = await rdb.get(f'customID:{Dev_Zaid}')
            else:
                id = '''
𖡋 𝐔𝐒𝐄 ⌯  {اليوزر}
𖡋 𝐌𝐒𝐆 ⌯  {الرسائل}
𖡋 𝐒𝐓𝐀 ⌯  {الرتبه}
𖡋 𝐈𝐃 ⌯  {الايدي}
𖡋 𝐄𝐃𝐈𝐓 ⌯  {التعديل}
𖡋 𝐂𝐑  ⌯  {الانشاء}
{البايو}'''
        if m.from_user.usernames:
            username = ''
            for i in m.from_user.usernames:
                username += f"@{i.username} "
        elif m.from_user.username:
            username = f'@{m.from_user.username}'
        else:
            username = 'مافي يوزر'
        rank = await get_rank(m.from_user.id, m.chat.id)
        msg = int(await rdb.get(f'{Dev_Zaid}{m.chat.id}:TotalMsgs:{m.from_user.id}'))
        msgs = f"{msg}"
        iD = f'`{m.from_user.id}`'
        if not await rdb.get(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}'):
            edits = 0
        else:
            edit = int(await rdb.get(f'{m.chat.id}:TotalEDMsgs:{m.from_user.id}{Dev_Zaid}'))
            edits = f"{edit}"
        name = m.from_user.first_name
        create = await get_creation_date(m.from_user.id)
        get_chat = await c.get_chat(m.from_user.id)
        if get_chat.bio:
            bio = get_chat.bio
        else:
            bio = 'مافي بايو'
        if msg > 50:
            tfa3l = 'شد حيلك'
        if msg > 500:
            tfa3l = 'يجي منك'
        if msg > 750:
            tfa3l = 'تفاعل متوسط'
        if msg > 2500:
            tfa3l = 'متفاعل'
        if msg > 5000:
            tfa3l = 'اسطورة التفاعل'
        if msg > 10000:
            tfa3l = 'اسطورة التلي'
        else:
            tfa3l = 'تفاعل صفر'
        comment = random.choice(comments)
        text = id.replace('{الاسم}', name).replace('{اليوزر}', username).replace('{الرسائل}', str(msgs)).replace('{التعديل}', str(edits)).replace('{الانشاء}', create).replace('{البايو}', f'{bio}').replace('{الايدي}', iD).replace('{الرتبه}', rank).replace('{التفاعل}', tfa3l).replace('{تعليق}', comment)
        if await rdb.get(f'{m.chat.id}:disableIDPHOTO:{Dev_Zaid}'):
            return await m.reply(text, disable_web_page_preview=True)
        else:
            if m.from_user.photo:
                get_user = await c.invoke(GetFullUser(id=(await c.resolve_peer(m.from_user.id))))
                photo = get_user.full_user.profile_photo
                video = photo.video_sizes
                if video:
                    if len(video) == 3:
                        video = video[-2]
                    else:
                        video = video[-1]
                if video:
                    file = BytesIO()
                    hash = photo.access_hash
                    if await rdb.get(f"{hash}:{m.from_user.id}"):
                        return await m.reply_animation(await rdb.get(f"{hash}:{m.from_user.id}"), caption=text)
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
                    file.name = f'{m.from_user.id}vid{m.chat.id}.mp4'
                    send = await m.reply_animation(file, caption=text)
                    await rdb.set(f"{hash}:{m.from_user.id}", send.animation.file_id, ex=3600)
                    return True
                else:
                    file_id = FileId(
                        file_type=FileType.PHOTO,
                        dc_id=photo.dc_id,
                        media_id=photo.id,
                        access_hash=photo.access_hash,
                        file_reference=photo.file_reference,
                        thumbnail_source=ThumbnailSource.THUMBNAIL,
                        thumbnail_file_type=FileType.PHOTO,
                        thumbnail_size=photo.sizes[0].type,
                        volume_id=0,
                        local_id=0
                    ).encode()
                    return await m.reply_photo(file_id, caption=text)
            else:
                return await m.reply(text, disable_web_page_preview=True)


@register("id_add_contact")
@Client.on_message(filters.new_chat_members, group=1)
@safe_handler
async def addContact(c, m):
    for me in m.new_chat_members:
        if not m.from_user.id == me.id:
            if not await rdb.get(f'{m.chat.id}TotalContacts{m.from_user.id}{Dev_Zaid}'):
                await rdb.set(f'{m.chat.id}TotalContacts{m.from_user.id}{Dev_Zaid}', 1)
            else:
                co = int(await rdb.get(f'{m.chat.id}TotalContacts{m.from_user.id}{Dev_Zaid}'))
                await rdb.set(f'{m.chat.id}TotalContacts{m.from_user.id}{Dev_Zaid}', co + 1)
