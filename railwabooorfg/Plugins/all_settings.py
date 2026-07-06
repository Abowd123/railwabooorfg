"""
all_settings.py
منقول من bmqa/Plugins/all.py (guardCommands — سطر 1124 → 1550)
الفئة: الإعدادات العامة والترحيب والمنشن

التحويلات المطبّقة:
  - r.<op>                        → await rdb.<op>
  - time.sleep(n)                 → await asyncio.sleep(n)
  - m.chat.get_members(...)       → async for mm in c.get_chat_members(m.chat.id, ...)
  - c.get_chat(id).invite_link    → (await c.get_chat(id)).invite_link
  - r.ttl(key)                    → await rdb.ttl(key)
  - m.reply / m.reply_photo       → await m.reply / await m.reply_photo
  - Thread(target=guardCommands)  → هاندلر async مباشر (بلا Thread)
  - isLockCommand / mod_pls / ...  → await (كلها async في bmqa-v2)

ملاحظات سلوك غامض — راجع قسم "AMBIGUOUS" في نهاية الملف.
"""

import logging
import asyncio
import time as _time

import pytz
from datetime import datetime
from hijri_converter import Hijri, Gregorian

from pyrogram import Client, ContinuePropagation, filters
from pyrogram.enums import ChatMembersFilter, ChatMemberStatus, ChatAction
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import Dev_Zaid
from core.db import rdb
from core.cache import members_cache
from core.errors import safe_handler
from core.dispatcher import register
from helpers.ranks import admin_pls, mod_pls, pre_pls, isLockCommand


# ══════════════════════════════════════════════════════════════════════════════
# دالة مساعدة: بناء نص الأمر بعد تطبيق اسم البوت + الأسماء المخصصة
# (مُستخلصة من بداية guardCommands — سطر 1081-1088)
# ══════════════════════════════════════════════════════════════════════════════

async def _resolve_text(m) -> str:
    text = m.text or ""
    name = await rdb.get(f"{Dev_Zaid}:BotName") or "ليو"
    if text.startswith(f"{name} "):
        text = text.replace(f"{name} ", "", 1)
    custom = await rdb.get(f"{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}")
    if custom:
        text = custom
    global_custom = await rdb.get(f"Custom:{Dev_Zaid}&text={text}")
    if global_custom:
        text = global_custom
    return text


# ══════════════════════════════════════════════════════════════════════════════
# الهاندلر الرئيسي — group=28 (نفس الأصل)
# ══════════════════════════════════════════════════════════════════════════════

@register("settings_commands")
@Client.on_message(filters.group & filters.text, group=28)
@safe_handler
async def guardCommandsHandler(c, m) -> None:
    """
    يعالج أوامر الإعدادات العامة والترحيب والمنشن.
    يُشغَّل على group=28 بعد الفلاتر الأخرى.
    """

    # ── فحوصات الأهلية (مُطابقة للأصل سطر 1063-1080) ─────────────────────
    if not await rdb.get(f"{m.chat.id}:enable:{Dev_Zaid}"):
        return
    if await rdb.get(f"{m.chat.id}:mute:{Dev_Zaid}") and not await admin_pls(
        m.from_user.id, m.chat.id
    ):
        return
    if await rdb.get(f"{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}"):
        return
    if await rdb.get(f"{m.from_user.id}:mute:{Dev_Zaid}"):
        return
    if await rdb.get(f"{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}"):
        return
    if await rdb.get(f"{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}"):
        return
    if await rdb.get(f"{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}") or await rdb.get(
        f"{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}"
    ):
        return

    text = await _resolve_text(m)

    if await isLockCommand(m.from_user.id, m.chat.id, text):
        return

    uid = m.from_user.id
    cid = m.chat.id
    mention = m.from_user.mention
    k = await rdb.get(f"{Dev_Zaid}:botkey")
    channel = await rdb.get(f"{Dev_Zaid}:BotChannel") or "YQYQY6"

    # ══════════════════════════════════════════════════════════════════════
    # 1. الاعدادات                                      (all.py سطر 1124)
    # ══════════════════════════════════════════════════════════════════════
    if text == "الاعدادات":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")

        x1  = "مقفول" if await rdb.get(f"{cid}:lockAudios:{Dev_Zaid}")      else "مفتوح"
        x2  = "مقفول" if await rdb.get(f"{cid}:lockVideo:{Dev_Zaid}")       else "مفتوح"
        x3  = "مقفول" if await rdb.get(f"{cid}:lockVoice:{Dev_Zaid}")       else "مفتوح"
        x4  = "مقفول" if await rdb.get(f"{cid}:lockPhoto:{Dev_Zaid}")       else "مفتوح"
        x5  = "مقفول" if await rdb.get(f"{cid}:mute:{Dev_Zaid}")            else "مفتوح"
        x6  = "مقفول" if await rdb.get(f"{cid}:lockInline:{Dev_Zaid}")      else "مفتوح"
        x7  = "مقفول" if await rdb.get(f"{cid}:lockForward:{Dev_Zaid}")     else "مفتوح"
        x8  = "مقفول" if await rdb.get(f"{cid}:lockHashtags:{Dev_Zaid}")    else "مفتوح"
        x9  = "مقفول" if await rdb.get(f"{cid}:lockEdit:{Dev_Zaid}")        else "مفتوح"
        x10 = "مقفول" if await rdb.get(f"{cid}:lockStickers:{Dev_Zaid}")    else "مفتوح"
        x11 = "مقفول" if await rdb.get(f"{cid}:lockFiles:{Dev_Zaid}")       else "مفتوح"
        x12 = "مقفول" if await rdb.get(f"{cid}:lockAnimations:{Dev_Zaid}")  else "مفتوح"
        x13 = "مقفول" if await rdb.get(f"{cid}:lockUrls:{Dev_Zaid}")        else "مفتوح"
        x14 = "مقفول" if await rdb.get(f"{cid}:lockBots:{Dev_Zaid}")        else "مفتوح"
        x15 = "مقفول" if await rdb.get(f"{cid}:lockTags:{Dev_Zaid}")        else "مفتوح"
        x16 = "مقفول" if await rdb.get(f"{cid}:lockNot:{Dev_Zaid}")         else "مفتوح"
        x17 = "مقفول" if await rdb.get(f"{cid}:lockaddContacts:{Dev_Zaid}") else "مفتوح"
        x18 = "مقفول" if await rdb.get(f"{cid}:lockMessages:{Dev_Zaid}")    else "مفتوح"
        x19 = "مقفول" if await rdb.get(f"{cid}:lockSHTM:{Dev_Zaid}")        else "مفتوح"
        x20 = "مقفول" if await rdb.get(f"{cid}:lockSpam:{Dev_Zaid}")        else "مفتوح"
        x21 = "مقفول" if await rdb.get(f"{cid}:lockChannels:{Dev_Zaid}")    else "مفتوح"
        x22 = "مقفول" if await rdb.get(f"{cid}:lockEditM:{Dev_Zaid}")       else "مفتوح"
        x23 = "مقفول" if await rdb.get(f"{cid}:lockJoin:{Dev_Zaid}")        else "مفتوح"
        x24 = "مقفول" if await rdb.get(f"{cid}:lockPersian:{Dev_Zaid}")     else "مفتوح"
        x25 = "مقفول" if await rdb.get(f"{cid}:lockJoinPersian:{Dev_Zaid}") else "مفتوح"
        x26 = "مقفول" if await rdb.get(f"{cid}:lockNSFW:{Dev_Zaid}")        else "مفتوح"

        return await m.reply(f"""
اعدادات المجموعة :

{k} الملفات الصوتية ⇠ ( {x1} )
{k} الفيديو ⇠ ( {x2} )
{k} الفويس ⇠ ( {x3} )
{k} الصور ⇠ ( {x4} )

{k} الدردشة ⇠ ( {x5} )
{k} الانلاين ⇠ ( {x6} )
{k} التوجيه ⇠ ( {x7} )
{k} الهشتاق ⇠ ( {x8} )
{k} التعديل ⇠ ( {x9} )
{k} الستيكرات ⇠ ( {x10} )

{k} الملفات ⇠ ( {x11} )
{k} المتحركات ⇠ ( {x12} )
{k} الروابط ⇠ ( {x13} )
{k} البوتات ⇠ ( {x14} )
{k} اليوزرات ⇠ ( {x15} )

{k} الاشعارات ⇠ ( {x16} )
{k} الاضافة ⇠ ( {x17} )

{k} الكلام الكثير ⇠ ( {x18} )
{k} السب ⇠ ( {x19} )
{k} التكرار ⇠ ( {x20} )
{k} القنوات ⇠ ( {x21} )
{k} تعديل الميديا ⇠ ( {x22} )

{k} الدخول ⇠ ( {x23} )
{k} الفارسية ⇠ ( {x24} )
{k} دخول الإيراني ⇠ ( {x25} )
{k} الإباحي ⇠ ( {x26} )

~ @{channel}""")

    # ══════════════════════════════════════════════════════════════════════
    # 2. الساعه / الساعة / الوقت                        (all.py سطر 1197)
    # ══════════════════════════════════════════════════════════════════════
    if text in ("الساعه", "الساعة", "الوقت"):
        TIME_ZONE = "Asia/Riyadh"
        ZONE = pytz.timezone(TIME_ZONE)
        TIME = datetime.now(ZONE)
        clock = TIME.strftime("%I:%M %p")
        return await m.reply(f"{k} الساعة ( {clock} )")

    # ══════════════════════════════════════════════════════════════════════
    # 3. القوانين                                        (all.py سطر 1204)
    # ══════════════════════════════════════════════════════════════════════
    if text == "القوانين":
        rules = await rdb.get(f"{cid}:CustomRules:{Dev_Zaid}")
        if not rules:
            rules = (
                f"{k} ممنوع نشر الروابط\n"
                f"{k} ممنوع التكلم او نشر صور اباحيه\n"
                f"{k} ممنوع اعاده توجيه\n"
                f"{k} ممنوع العنصرية بكل انواعها\n"
                f"{k} الرجاء احترام المدراء والادمنيه"
            )
        return await m.reply(rules, disable_web_page_preview=True)

    # ══════════════════════════════════════════════════════════════════════
    # 4. التاريخ                                         (all.py سطر 1215)
    # ══════════════════════════════════════════════════════════════════════
    if text == "التاريخ":
        b = Hijri.today().isoformat()
        a = b.split("-")
        hijri = Hijri(int(a[0]), int(a[1]), int(a[2]))
        hijri_date = b.replace("-", "/")
        hijri_month = hijri.month_name("ar")

        b2 = Gregorian.today().isoformat()
        a2 = b2.split("-")
        geo = Gregorian(int(a2[0]), int(a2[1]), int(a2[2]))
        geo_date = b2.replace("-", "/")
        geo_month = geo.month_name("en")[:3]

        return await m.reply(f"""
التاريخ:
{k} هجري ↢ {hijri_date} {hijri_month}
{k} ميلادي ↢ {geo_date} {geo_month}
""")

    # ══════════════════════════════════════════════════════════════════════
    # 5. المالك                                          (all.py سطر 1240)
    # ══════════════════════════════════════════════════════════════════════
    if text == "المالك":
        owner = None
        admins = await members_cache.get_admins(c, cid, ChatMembersFilter.ADMINISTRATORS)
        for mm in admins:
            if mm.status == ChatMemberStatus.OWNER:
                owner = mm.user
                break
        if owner:
            if owner.is_deleted:
                await m.reply("حساب المالك محذوف")
            else:
                owner_username = owner.username if owner.username else owner.id
                caption = f"• Owner ☆ ↦ {owner.mention}\n\n"
                caption += f"• Owner User ↦ @{owner_username}"
                button = InlineKeyboardMarkup(
                    [[InlineKeyboardButton(owner.first_name, user_id=owner.id)]]
                )
                if owner.photo:
                    file_id = owner.photo.big_file_id
                    photo_path = await c.download_media(file_id)
                    await m.reply_photo(
                        photo=photo_path, caption=caption, reply_markup=button
                    )
                    import os; os.remove(photo_path)
                else:
                    await m.reply(caption, reply_markup=button)

    # ══════════════════════════════════════════════════════════════════════
    # 6. اطردني                                          (all.py سطر 1269)
    #    time.sleep(0.5) → await asyncio.sleep(0.5)
    #    c.get_chat(...).invite_link → (await c.get_chat(...)).invite_link
    # ══════════════════════════════════════════════════════════════════════
    if text == "اطردني":
        if await rdb.get(f"{cid}:enableKickMe:{Dev_Zaid}"):
            get = await c.get_chat_member(cid, uid)
            if get.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
                return await m.reply(f"{k} ممنوع طرد الحلوين")
            if await admin_pls(uid, cid):
                return await m.reply(f"{k} ممنوع طرد الحلوين")
            await m.reply(
                f"{k} طردتك يانفسية ، وبعتلك الرابط بالخاص ترجع فيه وقت ماتبي"
            )
            await m.chat.ban_member(uid)
            await asyncio.sleep(0.5)
            await c.unban_chat_member(cid, uid)
            chat = await c.get_chat(cid)
            link = chat.invite_link
            try:
                await c.send_message(
                    uid,
                    f"{k} حبيبي النفسية رابط القروب الي طردتك منه: {link}",
                )
            except Exception as e:
                logging.exception(e)
                pass
            return

    # ══════════════════════════════════════════════════════════════════════
    # 7. الرابط                                          (all.py سطر 1293)
    # ══════════════════════════════════════════════════════════════════════
    if text == "الرابط":
        if not await rdb.get(f"{cid}:disableLINK:{Dev_Zaid}"):
            chat = await c.get_chat(cid)
            link = chat.invite_link
            return await m.reply(
                f"[{m.chat.title}]({link})", disable_web_page_preview=True
            )

    # ══════════════════════════════════════════════════════════════════════
    # 8. انشاء رابط                                      (all.py سطر 1298)
    # ══════════════════════════════════════════════════════════════════════
    if text == "انشاء رابط":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        chat = await c.get_chat(cid)
        link = chat.invite_link
        await c.revoke_chat_invite_link(cid, link)
        return await m.reply(f'{k} ابشر سويت رابط جديد ارسل "الرابط"')

    # ══════════════════════════════════════════════════════════════════════
    # 9. @all  (منشن الكل)                               (all.py سطر 1305)
    #    r.ttl → await rdb.ttl
    #    time.strftime بقيت sync (لا I/O)
    #    get_members → async for mm in c.get_chat_members(...)
    #    إرسال الرسائل داخل الحلقة → await c.send_message(...)
    # ══════════════════════════════════════════════════════════════════════
    if text.startswith("@all"):
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if await rdb.get(f"{cid}:disableALL:{Dev_Zaid}"):
            return await m.reply(f"{k} خاصية المنشن موقوفه حالياً")
        if await rdb.get(f"{cid}:inMention:{Dev_Zaid}"):
            return
        if await rdb.get(f"{cid}:inMentionWAIT:{Dev_Zaid}"):
            ttl = await rdb.ttl(f"{cid}:inMentionWAIT:{Dev_Zaid}")
            tm = _time.strftime("%M:%S", _time.gmtime(ttl))
            return await m.reply(f"{k} سويت منشن من شوي تعال بعد {tm}")

        reason = text.split(None, 1)[1] if len(text.split()) > 1 else ""
        users_list = []
        await rdb.set(f"{cid}:inMention:{Dev_Zaid}", 1)
        await m.reply(
            f"{k} بسوي منشن يحلو ، اذا تبي توقفه ارسل `/Cancel` او `ايقاف`"
        )
        async for mm in c.get_chat_members(cid, limit=150):
            if mm.user and not mm.user.is_deleted and not mm.user.is_bot:
                users_list.append(mm.user.mention)

        final_list = [users_list[x: x + 5] for x in range(0, len(users_list), 5)]
        ftext = f"{reason}\n\n"
        for batch in final_list:
            for user_mention in batch:
                if not await rdb.get(f"{cid}:inMention:{Dev_Zaid}"):
                    return
                ftext += f"{user_mention} , "
            await c.send_message(cid, ftext)
            ftext = f"{reason}\n\n"

        await rdb.delete(f"{cid}:inMention:{Dev_Zaid}")
        await rdb.set(f"{cid}:inMentionWAIT:{Dev_Zaid}", 1, ex=1200)

    # ══════════════════════════════════════════════════════════════════════
    # 10. /cancel  /  ايقاف                              (all.py سطر 1339)
    #     text.lower() == "/cancel" محفوظ بالضبط
    # ══════════════════════════════════════════════════════════════════════
    if text.lower() == "/cancel" or text == "ايقاف":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if not await rdb.get(f"{cid}:inMention:{Dev_Zaid}"):
            return await m.reply(f"{k} مو قاعده اسوي منشن ركز")
        await rdb.delete(f"{cid}:inMention:{Dev_Zaid}")
        return await m.reply(f"{k} تمام أوقفت المنشن")

    # ══════════════════════════════════════════════════════════════════════
    # 11. منشن                                           (all.py سطر 1349)
    # ══════════════════════════════════════════════════════════════════════
    if text == "منشن":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        return await m.reply(f"{k} لازم تكتب أمر\n@all مع النص اللي تبيه")

    # ══════════════════════════════════════════════════════════════════════
    # 12. تعطيل المنشن                                   (all.py سطر 1354)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تعطيل المنشن":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if await rdb.get(f"{cid}:disableALL:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} المشن معطل من قبل\n☆"
            )
        await rdb.set(f"{cid}:disableALL:{Dev_Zaid}", 1)
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر عطلت المنشن\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 13. تفعيل المنشن                                   (all.py سطر 1368)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تفعيل المنشن":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if not await rdb.get(f"{cid}:disableALL:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} المنشن مفعل من قبل\n☆"
            )
        await rdb.delete(f"{cid}:disableALL:{Dev_Zaid}")
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر فعلت المنشن\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 14. تعطيل الترحيب                                  (all.py سطر 1382)
    #     ⚠️  لا يوجد "تفعيل الترحيب" في الأصل — راجع قسم AMBIGUOUS
    # ══════════════════════════════════════════════════════════════════════
    if text == "تعطيل الترحيب":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if await rdb.get(f"{cid}:disableWelcome:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} الترحيب معطل من قبل\n☆"
            )
        await rdb.set(f"{cid}:disableWelcome:{Dev_Zaid}", 1)
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر عطلت الترحيب\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 15. تعطيل الترحيب بالصورة / بالصوره               (all.py سطر 1396)
    # ══════════════════════════════════════════════════════════════════════
    if text in ("تعطيل الترحيب بالصورة", "تعطيل الترحيب بالصوره"):
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if await rdb.get(f"{cid}:disableWelcomep:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} الترحيب بالصورة من قبل\n☆"
            )
        await rdb.set(f"{cid}:disableWelcomep:{Dev_Zaid}", 1)
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر عطلت الترحيب بالصورة\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 16. تفعيل الترحيب بالصورة / بالصوره               (all.py سطر 1410)
    # ══════════════════════════════════════════════════════════════════════
    if text in ("تفعيل الترحيب بالصورة", "تفعيل الترحيب بالصوره"):
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if not await rdb.get(f"{cid}:disableWelcomep:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} الترحيب بالصورة مفعل من قبل\n☆"
            )
        await rdb.delete(f"{cid}:disableWelcomep:{Dev_Zaid}")
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر فعلت الترحيب بالصورة\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 17. تعطيل الرابط                                   (all.py سطر 1424)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تعطيل الرابط":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if await rdb.get(f"{cid}:disableLINK:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} الرابط معطل من قبل\n☆"
            )
        await rdb.set(f"{cid}:disableLINK:{Dev_Zaid}", 1)
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر عطلت الرابط\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 18. تفعيل الرابط                                   (all.py سطر 1438)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تفعيل الرابط":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if not await rdb.get(f"{cid}:disableLINK:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} الرابط مفعل من قبل\n☆"
            )
        await rdb.delete(f"{cid}:disableLINK:{Dev_Zaid}")
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر فعلت الرابط\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 19. تعطيل البايو                                   (all.py سطر 1452)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تعطيل البايو":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if await rdb.get(f"{cid}:disableBio:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} البايو معطل من قبل\n☆"
            )
        await rdb.set(f"{cid}:disableBio:{Dev_Zaid}", 1)
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر عطلت البايو\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 20. تفعيل البايو                                   (all.py سطر 1466)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تفعيل البايو":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if not await rdb.get(f"{cid}:disableBio:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} البايو مفعل من قبل\n☆"
            )
        await rdb.delete(f"{cid}:disableBio:{Dev_Zaid}")
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر فعلت البايو\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 21. تعطيل اطردني                                   (all.py سطر 1480)
    #     المفتاح: enableKickMe (يُعطَّل بحذفه وليس بـ set 0)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تعطيل اطردني":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if not await rdb.get(f"{cid}:enableKickMe:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} اطردني معطل من قبل\n☆"
            )
        await rdb.delete(f"{cid}:enableKickMe:{Dev_Zaid}")
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر عطلت اطردني\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 22. تفعيل اطردني                                   (all.py سطر 1494)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تفعيل اطردني":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if await rdb.get(f"{cid}:enableKickMe:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} اطردني مفعل من قبل\n☆"
            )
        await rdb.set(f"{cid}:enableKickMe:{Dev_Zaid}", 1)
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر فعلت اطردني\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 23. تعطيل التحقق                                   (all.py سطر 1508)
    #     المفتاح: enableVerify (يُعطَّل بحذفه)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تعطيل التحقق":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if not await rdb.get(f"{cid}:enableVerify:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} التحقق معطل من قبل\n☆"
            )
        await rdb.delete(f"{cid}:enableVerify:{Dev_Zaid}")
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر عطلت التحقق\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 24. تفعيل التحقق                                   (all.py سطر 1522)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تفعيل التحقق":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if await rdb.get(f"{cid}:enableVerify:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} التحقق مفعل من قبل\n☆"
            )
        await rdb.set(f"{cid}:enableVerify:{Dev_Zaid}", 1)
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر فعلت التحقق\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 25. تعطيل انطقي / تعطيل انطق                       (all.py سطر 1536)
    # ══════════════════════════════════════════════════════════════════════
    if text in ("تعطيل انطقي", "تعطيل انطق"):
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if await rdb.get(f"{cid}:disableSay:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} انطقي معطل من قبل\n☆"
            )
        await rdb.set(f"{cid}:disableSay:{Dev_Zaid}", 1)
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر عطلت انطقي\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 26. تفعيل انطقي / تفعيل انطق                       (all.py سطر 1550)
    # ══════════════════════════════════════════════════════════════════════
    if text in ("تفعيل انطقي", "تفعيل انطق"):
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if not await rdb.get(f"{cid}:disableSay:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} انطقي مفعل من قبل\n☆"
            )
        await rdb.delete(f"{cid}:disableSay:{Dev_Zaid}")
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر فعلت انطقي\n☆"
        )

    # لا يوجد أمر من الأوامر الـ26 أعلاه يطابق النص — لم يُرسَل أي رد فعلي
    # للمستخدم في هذا المسار، لذا نُمرِّر المعالجة لبقية handlers group=28
    # (راجع [C4] في all_moderation_2.py لشرح المشكلة الأصلية).
    raise ContinuePropagation()


# ══════════════════════════════════════════════════════════════════════════════
# AMBIGUOUS — سلوكيات غامضة أو ناقصة في الأصل
# ══════════════════════════════════════════════════════════════════════════════
#
# [A1] "تفعيل الترحيب" — MISSING في الأصل
#      يوجد "تعطيل الترحيب" (سطر 1382) يضع disableWelcome:1
#      لكن لا يوجد مقابله "تفعيل الترحيب" أبداً في الملف.
#      إذا كان هذا مقصوداً فلا مشكلة، وإذا كان سهواً فيجب إضافة:
#
#      if text == "تفعيل الترحيب":
#          if not await mod_pls(uid, cid): ...
#          if not await rdb.get(f"{cid}:disableWelcome:{Dev_Zaid}"): ...  # مفعل من قبل
#          await rdb.delete(f"{cid}:disableWelcome:{Dev_Zaid}")
#          return await m.reply(f"{k} من「 {mention} 」\n{k} ابشر فعلت الترحيب\n☆")
#
# [A2] أمر "@all" — يجمع الأعضاء أولاً ثم يُرسل الدفعات
#      في الأصل الحلقة تتحقق أثناء الإرسال من وجود "inMention" لإمكانية الإلغاء.
#      في النسخة async هذا محفوظ بنفس المنطق (await rdb.get داخل الحلقة).
#      لكن: get_chat_members يُعيد async generator — لو قُطعت الاتصال أثناء
#      الجلب، الأعضاء الجزئيون سيُرسَلون. هذا سلوك مطابق للأصل.
#
# [A3] أمر "المالك" — لا يُعيد (return) بعد إرسال الصورة أو الرسالة،
#      بل يكمل تنفيذ الدالة. هذا سلوك محفوظ من الأصل (لا تغيير).
#
# [A4] أمر "اطردني" — يحاول إرسال رسالة خاصة للمستخدم (send_message uid)
#      قد يُخفق إن لم يبدأ المستخدم محادثة مع البوت. الأصل يبتلع الخطأ
#      بـ try/except بلا معالجة — محفوظ كما هو.
#
# [A5] "الرابط" و"انشاء رابط" — يعتمدان على chat.invite_link المُخزَّن
#      في كائن Chat، وقد يكون None إن لم يُنشأ رابط بعد.
#      الأصل لا يتحقق من ذلك — محفوظ كما هو.
