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
مُنقول من bmqa/Plugins/globalFilters.py → bmqa-v2/Plugins/global_filters.py

═══════════════════════════════════════════════════════════════════
الهاندلرز (2) — group=25 كان موجوداً في الأصل داخل docstring (معطّل):

group=24 — addCustomReplyG  (filters.group)
  إدارة الفلاتر العامة (على مستوى البوت كله، بدون cid في مفاتيح Redis):
    • اضف رد عام / مسح رد عام
    • الردود العامه / مسح الردود العامه
    • تعطيل ردود المطور / تفعيل ردود المطور
    • يستقبل كذلك الوسائط (photo/video/animation/audio/voice/doc/sticker)
      لحفظها كفلاتر عامة.
  ← pipeline: set×3 + sadd + delete في رحلة شبكة واحدة.

group=26 — addCustomReplyRandomG  (filters.group & filters.text)
  فلاتر الردود المتعددة العامة:
    • اضف رد متعدد عام / مسح رد متعدد عام
    • الردود المتعدده العامه / مسح الردود المتعدده العامه

═══════════════════════════════════════════════════════════════════
تحليل التداخل/التعارض مع custom_filter.py (ملخص):

✅ لا تعارض في أسماء الأوامر:
  global           ↔  local (custom_filter.py)
  ────────────────────────────────────────────────
  اضف رد عام      ↔  اضف رد
  مسح رد عام      ↔  مسح رد
  الردود العامه    ↔  الردود
  اضف رد متعدد عام ↔ اضف رد مميز
  مسح رد متعدد عام ↔ مسح رد مميز
  الردود المتعدده العامه ↔ الردود المميزه
  مسح الردود المتعدده العامه ↔ مسح الردود المميزه
  مسح الردود العامه ↔ مسح الردود

✅ لا تصادم في مفاتيح Redis:
  global: {text}:filter:{Dev_Zaid}           (بدون cid — عالمي)
  local:  {text}:filter:{Dev_Zaid}{cid}      (cid مُضمَّن بالنهاية)
  → سلاسل مختلفة، لا تداخل إطلاقاً.
  نفس المنطق ينطبق على filtertype / filterInfo / FiltersList /
  RFiltersList / randomfilter / randomFilter.

⚠ مفاتيح حالة (state) متشابهة الشكل لكن بلاحقات مميزة:
  global: addFilterG / addFilter2GG / delFilterG / addFilterRG / addFilterRG2 / delFilterRG
  local:  addFilter / addFilter2 / delFilter / addFilterR / addFilterR2 / delFilterR
  → مختلفة، لا تصادم.

✅ group=25 (addCustomReplyDoneG) كان معطّلاً في الأصل (ضمن docstring).
   تم حذفه بالكامل هنا لأنه لم يكن نشطاً.

═══════════════════════════════════════════════════════════════════
التحويلات:
  - Thread → await مباشر
  - r.<op> → await rdb.<op>
  - rep.decode("utf-8") → غير ضروري (decode_responses=True في RedisDB)
  - حفظ الفلتر العام (5 عمليات متتالية) → async with rdb.pipeline()
  - helpers.Ranks → helpers.ranks (حروف صغيرة)
  - @register + @safe_handler مُضافان
  - import محدّد بدل wildcard
"""

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from helpers.ranks import admin_pls, owner_pls, dev2_pls, isLockCommand


# ─── دوال مساعدة مشتركة ────────────────────────────────────────────────────

async def _resolve_text(m):
    """يحوّل نص الرسالة بعد استبدال اسم البوت والأوامر المخصصة."""
    text = m.text or ''
    name = await rdb.get(f'{Dev_Zaid}:BotName') or 'رعد'
    if text.startswith(f'{name} '):
        text = text.replace(f'{name} ', '')
    if await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}'):
        text = await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}')
    if await rdb.get(f'Custom:{Dev_Zaid}&text={text}'):
        text = await rdb.get(f'Custom:{Dev_Zaid}&text={text}')
    return text


async def _save_global_filter(text: str, payload: str, ftype: str, by: int, cid: int, uid: int):
    """يحفظ فلتراً عاماً في Redis بـ pipeline واحدة (5 عمليات).
    لاحظ: المفاتيح العامة ليس فيها cid — هذا هو الفرق الجوهري عن الفلاتر المحلية.
    """
    state_key = f'{cid}:addFilter2GG:{uid}{Dev_Zaid}'
    async with rdb.pipeline(transaction=False) as pipe:
        pipe.set(f'{text}:filter:{Dev_Zaid}', payload)
        pipe.set(f'{text}:filtertype:{Dev_Zaid}', ftype)
        pipe.set(f'{text}:filterInfo:{Dev_Zaid}', f'by={by}')
        pipe.sadd(f'FiltersList:{Dev_Zaid}', text)
        pipe.delete(state_key)
        await pipe.execute()


# ═══════════════════════════════════════════════════════════════════════════
# group=24 — إدارة الفلاتر العامة + استقبال الوسائط
# ═══════════════════════════════════════════════════════════════════════════

@register("global_filter_manage")
@Client.on_message(filters.group, group=24)
@safe_handler
async def addCustomReplyG(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')

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

    uid = m.from_user.id
    cid = m.chat.id
    state_key = f'{cid}:addFilter2GG:{uid}{Dev_Zaid}'

    # ─── معالجة النصوص ─────────────────────────────────────────────────────
    if m.text:
        text = await _resolve_text(m)

        # إلغاء جلسات الإضافة/الحذف الجارية
        if await rdb.get(f'{cid}:addFilterG:{uid}{Dev_Zaid}') and text == 'الغاء':
            await rdb.delete(f'{cid}:addFilterG:{uid}{Dev_Zaid}')
            return await m.reply(f'{k} من عيوني لغيت اضافة الرد العام')

        if await rdb.get(f'{cid}:delFilterG:{uid}{Dev_Zaid}') and text == 'الغاء':
            await rdb.delete(f'{cid}:delFilterG:{uid}{Dev_Zaid}')
            return await m.reply(f'{k} من عيوني لغيت مسح الرد العام')

        if m.text == 'الغاء' and await rdb.get(state_key):
            await rdb.delete(state_key)
            return await m.reply(f'{k} من عيوني لغيت اضافة الرد العام')

        # حذف فلتر عام (بعد إرسال اسمه)
        if await rdb.get(f'{cid}:delFilterG:{uid}{Dev_Zaid}') and await dev2_pls(uid, cid):
            if not await rdb.get(f'{m.text}:filterInfo:{Dev_Zaid}'):
                await rdb.delete(f'{cid}:delFilterG:{uid}{Dev_Zaid}')
                return await m.reply(f'{k} هذا الرد مو مضاف في قائمة الردود العامه')
            async with rdb.pipeline(transaction=False) as pipe:
                pipe.delete(f'{m.text}:filter:{Dev_Zaid}')
                pipe.delete(f'{m.text}:filtertype:{Dev_Zaid}')
                pipe.delete(f'{m.text}:filterInfo:{Dev_Zaid}')
                pipe.srem(f'FiltersList:{Dev_Zaid}', m.text)
                pipe.delete(f'{cid}:delFilterG:{uid}{Dev_Zaid}')
                await pipe.execute()
            return await m.reply(f'( {m.text} )\n{k} وحذفنا الرد ياحلو')

        # تعطيل/تفعيل ردود المطور
        if text == 'تعطيل ردود المطور':
            if not await owner_pls(uid, cid):
                return await m.reply(f'{k} هذا الأمر يخص ( المالك وفوق ) بس')
            if await rdb.get(f'{cid}:lock_global:{Dev_Zaid}'):
                return await m.reply(
                    f'{k} من「 {m.from_user.mention} 」\n{k} ردود المطور معطله من قبل\n☆',
                    parse_mode=ParseMode.HTML,
                )
            await rdb.set(f'{cid}:lock_global:{Dev_Zaid}', 1)
            return await m.reply(
                f'{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت ردود المطور\n☆',
                parse_mode=ParseMode.HTML,
            )

        if text == 'تفعيل ردود المطور':
            if not await owner_pls(uid, cid):
                return await m.reply(f'{k} هذا الأمر يخص ( المالك وفوق ) بس')
            if not await rdb.get(f'{cid}:lock_global:{Dev_Zaid}'):
                return await m.reply(
                    f'{k} من「 {m.from_user.mention} 」\n{k} ردود المطور مفعله من قبل\n☆',
                    parse_mode=ParseMode.HTML,
                )
            await rdb.delete(f'{cid}:lock_global:{Dev_Zaid}')
            return await m.reply(
                f'{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت ردود المطور\n☆',
                parse_mode=ParseMode.HTML,
            )

        # الردود العامه — قائمة
        if text == 'الردود العامه':
            if not await dev2_pls(uid, cid):
                return await m.reply(f'{k} هذا الأمر يخص ( Dev²🎖️ وفوق ) بس')
            glist = await rdb.smembers(f'FiltersList:{Dev_Zaid}')
            if not glist:
                return await m.reply(f'{k} مافيه ردود عامه مضافه')
            lines = 'ردود البوت:\n'
            count = 1
            for rep in glist:
                ftype = await rdb.get(f'{rep}:filtertype:{Dev_Zaid}')
                lines += f'\n{count} - ( {rep} ) ࿓ ( {ftype} )'
                count += 1
            lines += '\n☆'
            return await m.reply(lines, disable_web_page_preview=True, parse_mode=ParseMode.HTML)

        # مسح الردود العامه
        if text == 'مسح الردود العامه':
            if not await dev2_pls(uid, cid):
                return await m.reply(f'{k} هذا الأمر يخص ( Dev²🎖️ وفوق ) بس')
            glist = await rdb.smembers(f'FiltersList:{Dev_Zaid}')
            if not glist:
                return await m.reply(f'{k} مافيه ردود عامه مضافه')
            total = 0
            for rep in list(glist):
                async with rdb.pipeline(transaction=False) as pipe:
                    pipe.delete(f'{rep}:filter:{Dev_Zaid}')
                    pipe.delete(f'{rep}:filtertype:{Dev_Zaid}')
                    pipe.delete(f'{rep}:filterInfo:{Dev_Zaid}')
                    pipe.srem(f'FiltersList:{Dev_Zaid}', rep)
                    await pipe.execute()
                total += 1
            return await m.reply(f'{k} ابشر مسحت ( `{total}` ) من الردود العامه')

        # مسح رد عام (يبدأ جلسة الحذف)
        if text == 'مسح رد عام':
            if not await rdb.get(f'{cid}:delFilterG:{uid}{Dev_Zaid}'):
                if not await dev2_pls(uid, cid):
                    return await m.reply(f'{k} هذا الأمر يخص ( Dev²🎖️ وفوق ) بس')
                await rdb.set(f'{cid}:delFilterG:{uid}{Dev_Zaid}', 1)
                return await m.reply(
                    f'{k} تمام عيني\n{k} الحين ارسل الرد عشان امسحه\n☆',
                    parse_mode=ParseMode.HTML,
                )

        # اضف رد عام (يبدأ جلسة الإضافة)
        if text == 'اضف رد عام':
            if not await rdb.get(f'{cid}:addFilterG:{uid}{Dev_Zaid}'):
                if not await dev2_pls(uid, cid):
                    return await m.reply(f'{k} هذا الأمر يخص ( Dev²🎖️ وفوق ) بس')
                await rdb.set(f'{cid}:addFilterG:{uid}{Dev_Zaid}', 1)
                return await m.reply(f'{k} حلو ، الحين ارسل الكلمة اللي تبيها')

        # حفظ نص الرد العام
        if await rdb.get(state_key) and await dev2_pls(uid, cid):
            filter_name = await rdb.get(state_key)
            payload = f'type=text&text={m.text.html}'
            await _save_global_filter(filter_name, payload, 'نص', uid, cid, uid)
            return await m.reply(f'{k} ( {filter_name} )\nضفنا الرد العام يا حلو\n☆', parse_mode=ParseMode.HTML)

        # انتقال: أرسل كلمة الفلتر → انتظر الرد
        if await rdb.get(f'{cid}:addFilterG:{uid}{Dev_Zaid}') and await dev2_pls(uid, cid):
            await rdb.set(state_key, m.text)
            await rdb.delete(f'{cid}:addFilterG:{uid}{Dev_Zaid}')
            return await m.reply(
                f'{k} حلو الحين ارسل جواب الرد\n'
                f'{k} ( نص,صوره,فيديو,متحركه,بصمه,صوت,ملف )\n'
                'ـــــــــــــــــــــــــــــــــــــــــ\n'
                '`<USER_ID>` › آيدي المستخدم\n'
                '`<USER_NAME>` › اسم المستخدم\n'
                '`<USER_USERNAME>` › يوزر المستخدم\n'
                '`<USER_MENTION>` › رابط حساب المستخدم\n'
                '༄',
                parse_mode=ParseMode.MARKDOWN,
            )
        return  # لا شيء آخر للنصوص

    # ─── استقبال الوسائط لحفظها كفلتر عام ─────────────────────────────────

    # صورة
    if m.photo and await rdb.get(state_key) and await dev2_pls(uid, cid):
        filter_name = await rdb.get(state_key)
        caption = m.caption.html if m.caption else 'None'
        payload = f'type=photo&photo={m.photo.file_id}&caption={caption}'
        await _save_global_filter(filter_name, payload, 'صوره', uid, cid, uid)
        return await m.reply(f'{k} ( {filter_name} )\nضفنا الرد العام يا حلو\n☆', parse_mode=ParseMode.HTML)

    # فيديو
    if m.video and await rdb.get(state_key) and await dev2_pls(uid, cid):
        filter_name = await rdb.get(state_key)
        caption = m.caption.html if m.caption else 'None'
        payload = f'type=video&video={m.video.file_id}&caption={caption}'
        await _save_global_filter(filter_name, payload, 'فيديو', uid, cid, uid)
        return await m.reply(f'{k} ( {filter_name} )\nضفنا الرد العام يا حلو\n☆', parse_mode=ParseMode.HTML)

    # متحركة
    if m.animation and await rdb.get(state_key) and await dev2_pls(uid, cid):
        filter_name = await rdb.get(state_key)
        caption = m.caption.html if m.caption else 'None'
        payload = f'type=animation&animation={m.animation.file_id}&caption={caption}'
        await _save_global_filter(filter_name, payload, 'متحركه', uid, cid, uid)
        return await m.reply(f'{k} ( {filter_name} )\nضفنا الرد العام يا حلو\n☆', parse_mode=ParseMode.HTML)

    # صوت
    if m.audio and await rdb.get(state_key) and await dev2_pls(uid, cid):
        filter_name = await rdb.get(state_key)
        caption = m.caption.html if m.caption else 'None'
        payload = f'type=audio&audio={m.audio.file_id}&caption={caption}'
        await _save_global_filter(filter_name, payload, 'صوت', uid, cid, uid)
        return await m.reply(f'{k} ( {filter_name} )\nضفنا الرد العام يا حلو\n☆', parse_mode=ParseMode.HTML)

    # بصمة
    if m.voice and await rdb.get(state_key) and await dev2_pls(uid, cid):
        filter_name = await rdb.get(state_key)
        caption = m.caption.html if m.caption else 'None'
        payload = f'type=voice&voice={m.voice.file_id}&caption={caption}'
        await _save_global_filter(filter_name, payload, 'بصمه', uid, cid, uid)
        return await m.reply(f'{k} ( {filter_name} )\nضفنا الرد العام يا حلو\n☆', parse_mode=ParseMode.HTML)

    # ملف
    if m.document and await rdb.get(state_key) and await dev2_pls(uid, cid):
        filter_name = await rdb.get(state_key)
        caption = m.caption.html if m.caption else 'None'
        payload = f'type=doc&doc={m.document.file_id}&caption={caption}'
        await _save_global_filter(filter_name, payload, 'ملف', uid, cid, uid)
        return await m.reply(f'{k} ( {filter_name} )\nضفنا الرد العام يا حلو\n☆', parse_mode=ParseMode.HTML)

    # ستيكر
    if m.sticker and await rdb.get(state_key) and await dev2_pls(uid, cid):
        filter_name = await rdb.get(state_key)
        payload = f'type=sticker&sticker={m.sticker.file_id}'
        await _save_global_filter(filter_name, payload, 'ملصق', uid, cid, uid)
        return await m.reply(f'{k} ( {filter_name} )\nضفنا الرد العام يا حلو\n☆', parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════════════════════════════════
# group=26 — فلاتر الردود المتعددة العامة
# ═══════════════════════════════════════════════════════════════════════════

@register("global_filter_random")
@Client.on_message(filters.group & filters.text, group=26)
@safe_handler
async def addCustomReplyRandomG(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')

    if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not await admin_pls(m.from_user.id, m.chat.id):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}') or await rdb.get(f'{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}'):
        return

    text = await _resolve_text(m)

    uid = m.from_user.id
    cid = m.chat.id

    # ─── إلغاء جلسات الردود المتعددة العامة ────────────────────────────────
    if await rdb.get(f'{cid}:addFilterRG:{uid}{Dev_Zaid}') and text == 'الغاء':
        await rdb.delete(f'{cid}:addFilterRG:{uid}{Dev_Zaid}')
        return await m.reply(f'{k} من عيوني لغيت اضافة الرد المتعدد عام')

    if await rdb.get(f'{cid}:addFilterRG2:{uid}{Dev_Zaid}') and text == 'الغاء':
        rep = await rdb.get(f'{cid}:addFilterRG2:{uid}{Dev_Zaid}')
        async with rdb.pipeline(transaction=False) as pipe:
            pipe.delete(f'{cid}:addFilterRG2:{uid}{Dev_Zaid}')
            pipe.delete(f'{rep}:randomfilter:{Dev_Zaid}')
            await pipe.execute()
        return await m.reply(f'{k} من عيوني لغيت اضافه الرد المتعدد عام')

    if await rdb.get(f'{cid}:delFilterRG:{uid}{Dev_Zaid}') and text == 'الغاء':
        await rdb.delete(f'{cid}:delFilterRG:{uid}{Dev_Zaid}')
        return await m.reply(f'{k} من عيوني لغيت مسح الرد المتعدد العام')

    # ─── تم — حفظ الرد المتعدد العام ──────────────────────────────────────
    if await rdb.get(f'{cid}:addFilterRG2:{uid}{Dev_Zaid}') and text == 'تم':
        filter_name = await rdb.get(f'{cid}:addFilterRG2:{uid}{Dev_Zaid}')
        count = len(await rdb.smembers(f'{filter_name}:randomfilter:{Dev_Zaid}'))
        async with rdb.pipeline(transaction=False) as pipe:
            pipe.set(f'{filter_name}:randomFilter:{Dev_Zaid}', 1)
            pipe.sadd(f'RFiltersList:{Dev_Zaid}', filter_name)
            pipe.delete(f'{cid}:addFilterRG2:{uid}{Dev_Zaid}')
            await pipe.execute()
        return await m.reply(
            f'{k} تم اضافه الرد المتعدد ( {filter_name} )\n{k} بـ ( `{count}` ) جواب رد\n☆',
            parse_mode=ParseMode.HTML,
        )

    # ─── حذف رد متعدد عام (بعد إرسال اسمه) ───────────────────────────────
    if await rdb.get(f'{cid}:delFilterRG:{uid}{Dev_Zaid}') and await dev2_pls(uid, cid):
        if not await rdb.get(f'{m.text}:randomFilter:{Dev_Zaid}'):
            await rdb.delete(f'{cid}:delFilterRG:{uid}{Dev_Zaid}')
            return await m.reply(f'{k} هذا الرد مو مضاف في قائمة الردود')
        async with rdb.pipeline(transaction=False) as pipe:
            pipe.delete(f'{m.text}:randomFilter:{Dev_Zaid}')
            pipe.delete(f'{m.text}:randomfilter:{Dev_Zaid}')
            pipe.delete(f'{cid}:delFilterRG:{uid}{Dev_Zaid}')
            pipe.srem(f'RFiltersList:{Dev_Zaid}', m.text)
            await pipe.execute()
        return await m.reply(f'{k} ابشر مسحت الرد المتعدد ')

    # ─── انتقال: أرسل اسم الفلتر → ابدأ تجميع الأجوبة ────────────────────
    if await rdb.get(f'{cid}:addFilterRG:{uid}{Dev_Zaid}') and await dev2_pls(uid, cid):
        async with rdb.pipeline(transaction=False) as pipe:
            pipe.delete(f'{cid}:addFilterRG:{uid}{Dev_Zaid}')
            pipe.set(f'{cid}:addFilterRG2:{uid}{Dev_Zaid}', m.text)
            await pipe.execute()
        return await m.reply(
            f'{k} حلو الحين ارسل اجوبة الرد\n'
            f'{k} بس تخلص ارسل تم\n'
            'ـــــــــــــــــــــــــــــــــــــــــ\n'
            '`<USER_ID>` › آيدي المستخدم\n'
            '`<USER_NAME>` › اسم المستخدم\n'
            '`<USER_USERNAME>` › يوزر المستخدم\n'
            '`<USER_MENTION>` › رابط حساب المستخدم\n'
            '༄',
            parse_mode=ParseMode.MARKDOWN,
        )

    # ─── تجميع الأجوبة (كل رسالة = جواب واحد) ─────────────────────────────
    if await rdb.get(f'{cid}:addFilterRG2:{uid}{Dev_Zaid}') and await dev2_pls(uid, cid):
        filter_name = await rdb.get(f'{cid}:addFilterRG2:{uid}{Dev_Zaid}')
        await rdb.sadd(f'{filter_name}:randomfilter:{Dev_Zaid}', m.text.html)
        return await m.reply(
            f'{k} حلو ضفت هذا الرد\n'
            f'{k} بس تخلص ارسل تم\n'
            'ـــــــــــــــــــــــــــــــــــــــــ\n'
            '`<USER_ID>` › آيدي المستخدم\n'
            '`<USER_NAME>` › اسم المستخدم\n'
            '`<USER_USERNAME>` › يوزر المستخدم\n'
            '`<USER_MENTION>` › رابط حساب المستخدم\n'
            '༄',
            parse_mode=ParseMode.MARKDOWN,
        )

    # ─── الردود المتعدده العامه — قائمة ────────────────────────────────────
    if text == 'الردود المتعدده العامه':
        if not await dev2_pls(uid, cid):
            return await m.reply(f'{k} هذا الأمر يخص ( Dev²🎖️ وفوق ) بس')
        rfilters = await rdb.smembers(f'RFiltersList:{Dev_Zaid}')
        if not rfilters:
            return await m.reply(f'{k} مافيه ردود عشوائيه عامة')
        lines = 'الردود المتعدده:\n'
        count = 1
        for rep in rfilters:
            ttt = len(await rdb.smembers(f'{rep}:randomfilter:{Dev_Zaid}'))
            lines += f'\n{count} - ( {rep} ) ࿓ ( {ttt} )'
            count += 1
        lines += '\n☆'
        return await m.reply(lines, disable_web_page_preview=True, parse_mode=ParseMode.HTML)

    # ─── مسح الردود المتعدده العامه ────────────────────────────────────────
    if text == 'مسح الردود المتعدده العامه':
        if not await dev2_pls(uid, cid):
            return await m.reply(f'{k} هذا الأمر يخص ( Dev²🎖️ وفوق ) بس')
        rfilters = await rdb.smembers(f'RFiltersList:{Dev_Zaid}')
        if not rfilters:
            return await m.reply(f'{k} مافيه ردود عشوائيه عامة')
        count = 0
        for rep in list(rfilters):
            async with rdb.pipeline(transaction=False) as pipe:
                pipe.delete(f'{rep}:randomfilter:{Dev_Zaid}')
                pipe.srem(f'RFiltersList:{Dev_Zaid}', rep)
                pipe.delete(f'{rep}:randomFilter:{Dev_Zaid}')
                await pipe.execute()
            count += 1
        return await m.reply(f'{k} ابشر مسحت ( `{count}` ) رد متعدد ')

    # ─── اضف رد متعدد عام (يبدأ جلسة الإضافة) ────────────────────────────
    if (text == 'اضف رد متعدد عام'
            and not await rdb.get(f'{cid}:addFilterRG:{uid}{Dev_Zaid}')
            and not await rdb.get(f'{cid}:addFilterRG2:{uid}{Dev_Zaid}')):
        if not await dev2_pls(uid, cid):
            return await m.reply(f'{k} هذا الأمر يخص ( Dev²🎖️ وفوق ) بس')
        await rdb.set(f'{cid}:addFilterRG:{uid}{Dev_Zaid}', 1)
        return await m.reply(f'{k} حلو ، ارسل الحين الكلمة الي تبيها')

    # ─── مسح رد متعدد عام (يبدأ جلسة الحذف) ─────────────────────────────
    if text == 'مسح رد متعدد عام' and not await rdb.get(f'{cid}:addFilterRG:{uid}{Dev_Zaid}'):
        if not await dev2_pls(uid, cid):
            return await m.reply(f'{k} هذا الأمر يخص ( Dev²🎖️ وفوق ) بس')
        await rdb.set(f'{cid}:delFilterRG:{uid}{Dev_Zaid}', 1)
        return await m.reply(
            f'{k} تمام عيني\n{k} الحين ارسل الرد عشان امسحه\n☆',
            parse_mode=ParseMode.HTML,
        )
