"""
all_moderation_2.py
منقول من bmqa/Plugins/all.py (guardCommands — سطر 3451 → 3838 تقريباً)
الفئة: العمليات الإدارية المتقدمة (رفع/إلغاء الحظر، رفع القيود، كشف البوتات،
       مين ضافني، مسح الرسائل، تنزيل/رفع مشرف، مسح قائمة التثبيت، الاوامر)

⚠️ ملاحظة نطاق (تداخل مع all_moderation_1.py):
   أمر "طرد" (رد) (all.py سطر 3451-3470) **لم يُنقل هنا** لأنه مهاجَر مسبقاً
   ضمن all_moderation_1.py (راجع "20. طرد (رد)" في ذلك الملف، الذي يوثّق
   صراحة أن نطاقه ينتهي عند "نهاية كتلة طرد (رد) (سطر 3470)"). حد النطاق
   الفعلي المطلوب (3451) يقع تحديداً داخل تلك الكتلة المنقولة مسبقاً، لذلك
   بدأ النقل هنا فعلياً من أول أمر جديد بعدها: "رفع الحظر" (سطر 3472)، وحتى
   نهاية كتلة "الاوامر" (سطر 3838) — آخر سطر قبل الهاندلر التالي
   (@Client.on_callback_query في سطر 3841).
   الترقيم أدناه يكمل تسلسل all_moderation_1.py (الذي انتهى عند البند 20)
   ابتداءً من 21، تسهيلاً لمطابقة السطور الأصلية بين الملفين.

التحويلات المطبّقة:
  - بوابة الأهلية + تطبيع النص لم تُكرَّر محلياً؛ اسْتُوردت من
    all_helpers.resolve_guard_text (نفس ما فعله all_moderation_1.py).
  - mod_pls / owner_pls / admin_pls من helpers.ranks (async في bmqa-v2) →
    await قبل كل استدعاء، دون أي تغيير منطقي. (ملاحظة: لا يستخدم أي أمر في
    هذا النطاق تحديداً pre_pls أو get_rank، على عكس all_moderation_1.py).
  - r.get/set/delete/sadd/srem → await rdb.get/set/delete/sadd/srem (لا يوجد
    kvsqlite/wsdb في هذا النطاق أصلاً).
  - time.sleep غير موجود في هذا النطاق (لا يوجد استبدال مطلوب هنا فعلياً).
  - m.chat.get_member(...) / m.chat.ban_member(...) / m.chat.unban_member(...)
    → await (نفس الدالة تماماً، فقط إضافة await).
  - m.chat.get_members(filter=...) → async for (بقيت عبر m.chat وليس
    c.get_chat_members لأن هذا ما استخدمه الأصل حرفياً في "كشف البوتات"
    تحديداً؛ راجع ملاحظة الأصل نفسه الذي مزج بين الاثنين).
  - c.restrict_chat_member / c.promote_chat_member / c.set_administrator_title
    / c.unpin_all_chat_messages / m.reply_to_message.delete() / m.delete() →
    await.
  - for msg in range(...): c.delete_messages(...) → await c.delete_messages(...)
    (الحلقة نفسها بقيت for عادية لأنها على range() وليست على استعلام I/O).

كل نصوص الرسائل المرسلة للمستخدم (بما فيها التناقضات المحفوظة من الأصل بين
نص رسالة الصلاحية والدالة الفعلية المُستخدَمة للتحقق، وأي كود ميت/متكرر)
نُقلت حرفياً دون أي تعديل.

سلوكيات غامضة موثّقة في قسم AMBIGUOUS آخر الملف.
"""

import logging
import re

from pyrogram import Client, ContinuePropagation, filters
from pyrogram.enums import ChatMemberStatus, ChatMembersFilter, ParseMode
from pyrogram.types import (
    ChatPermissions,
    ChatPrivileges,
    ForceReply,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from config import Dev_Zaid, botUsername
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from helpers.ranks import mod_pls, owner_pls, admin_pls
from Plugins.all_helpers import resolve_guard_text


# ══════════════════════════════════════════════════════════════════════════════
# الهاندلر الرئيسي — group=28 (نفس الأصل ونفس بقية ملفات guardCommands)
#
# كل الأوامر أدناه مسجَّلة أيضاً بجدول core/dispatcher.py (COMMAND_HANDLERS)
# بنفس نص الأمر بالضبط كما في الأصل، بما في ذلك كل صيغة بديلة. التسجيل هنا
# هو فهرسة/مرجع فقط (راجع ملاحظة [B3] في all_moderation_1.py — نفس الوضع
# ينطبق هنا: core.dispatcher.dispatch() غير مُستدعاة فعلياً من التوجيه
# الحالي، الذي يعمل عبر Client.on_message + سلسلة if الداخلية).
#
# ⚠️ راجع أيضاً AMBIGUOUS [C4] بالأسفل بخصوص group=28 المشترك بين 8 ملفات.
# ══════════════════════════════════════════════════════════════════════════════

@register("رفع الحظر ")   # startswith + هدف (id/username)
@register("الغاء الحظر ")
@register("رفع الحظر")    # رد مباشر بلا هدف نصي
@register("الغاء الحظر")
@register("رفع القيود ")
@register("رفع القيود")
@register("كشف البوتات")
@register("مين ضافني")
@register("بايو عشوائي")
@register("مسح")          # رد مباشر (حذف رسالة واحدة)
@register("مسح ")         # startswith + عدد (حذف جماعي)
@register("تنزيل مشرف")
@register("رفع مشرف")
@register("مسح قائمة التثبيت")
@register("الاوامر")
@register("/commands")
@register(f"/commands@{botUsername}")
@Client.on_message(filters.group & filters.text, group=28)
@safe_handler
async def moderationHandler2(c, m) -> None:
    """
    يعالج أوامر رفع/إلغاء الحظر، رفع القيود، كشف البوتات، مين ضافني، مسح
    الرسائل، تنزيل/رفع مشرف، مسح قائمة التثبيت، وقائمة الاوامر.
    يُشغَّل على group=28 بعد الفلاتر الأخرى، بنفس نمط بقية ملفات guardCommands
    المنقولة (all_settings.py، all_voice_and_blocklist.py، all_protection.py،
    all_features_toggle.py، all_locks_1.py، all_locks_2.py، all_moderation_1.py).
    """

    text = await resolve_guard_text(m)
    if text is None:
        return

    k = await rdb.get(f"{Dev_Zaid}:botkey")
    channel = await rdb.get(f"{Dev_Zaid}:BotChannel") or "YQYQY6"

    # ══════════════════════════════════════════════════════════════════════
    # 21. رفع الحظر / الغاء الحظر <id/username>            (all.py سطر 3472)
    #     ⚠️ راجع AMBIGUOUS [C1] — شرط أسبقية معامِلات محفوظ من الأصل حرفياً
    # ══════════════════════════════════════════════════════════════════════
    if (
        text.startswith("رفع الحظر ")
        or text.startswith("الغاء الحظر ")
        and len(text.split()) == 3
    ):
        if not "@" in text and not re.findall("[0-9]+", text):
            return
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( المدير وفوق ) بس")
        else:
            try:
                user = int(text.split()[2])
            except Exception as e:
                logging.exception(e)
                user = text.split()[2].replace("@", "")
            try:
                get = await m.chat.get_member(user)
                if not get.status == ChatMemberStatus.BANNED:
                    return await m.reply(f"「 {get.user.mention} 」 \n{k} مو محظور من قبل\n☆")
            except Exception as e:
                logging.exception(e)
                return await m.reply(f"{k} مافي عضو بهذا اليوزر")
            await m.chat.unban_member(get.user.id)
            return await m.reply(f"「 {get.user.mention} 」 \n{k} ابشر الغيت حظره\n☆")

    # ══════════════════════════════════════════════════════════════════════
    # 22. رفع الحظر / الغاء الحظر (رد)                     (all.py سطر 3495)
    #     ⚠️ راجع AMBIGUOUS [C2] — نفس نوع شرط الأسبقية، وأثره أخطر هنا (قد
    #     يحاول الوصول إلى m.reply_to_message.from_user وهو None)
    # ══════════════════════════════════════════════════════════════════════
    if (
        text == "رفع الحظر"
        or text == "الغاء الحظر"
        and m.reply_to_message
        and m.reply_to_message.from_user
    ):
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( المدير وفوق ) بس")
        else:
            try:
                get = await m.chat.get_member(m.reply_to_message.from_user.id)
                if not get.status == ChatMemberStatus.BANNED:
                    return await m.reply(
                        f"「 {m.reply_to_message.from_user.mention} 」 \n{k} مو محظور من قبل\n☆"
                    )
                await m.chat.unban_member(m.reply_to_message.from_user.id)
                return await m.reply(
                    f"「 {m.reply_to_message.from_user.mention} 」 \n{k} ابشر الغيت حظره\n☆"
                )
            except Exception as e:
                logging.exception(e)
                return await m.reply(f"{k} العضو مو بالمجموعة")

    # ══════════════════════════════════════════════════════════════════════
    # 23. رفع القيود <id/username>                          (all.py سطر 3517)
    #     ⚠️ راجع AMBIGUOUS [C3] — كود ميت بعد try/except (محفوظ حرفياً)
    # ══════════════════════════════════════════════════════════════════════
    if text.startswith("رفع القيود ") and len(text.split()) == 3:
        if not "@" in text and not re.findall("[0-9]+", text):
            return
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( المدير وفوق ) بس")
        else:
            try:
                user = int(text.split()[2])
            except Exception as e:
                logging.exception(e)
                user = text.split()[2].replace("@", "")
            co = 0
            text = ""
            try:
                get = await m.chat.get_member(user)
                if get.status == ChatMemberStatus.BANNED:
                    await m.chat.unban_member(get.user.id)
                    text += "حظر\n"
                    co += 1
                if get.status == ChatMemberStatus.RESTRICTED:
                    await c.restrict_chat_member(
                        m.chat.id,
                        get.user.id,
                        ChatPermissions(
                            can_send_messages=True,
                            can_send_media_messages=True,
                            can_send_other_messages=True,
                            can_send_polls=True,
                            can_invite_users=True,
                            can_add_web_page_previews=True,
                            can_change_info=True,
                            can_pin_messages=True,
                        ),
                    )
                    text += "تقييد\n"
                    co += 1
                if await rdb.get(f"{get.user.id}:mute:{m.chat.id}{Dev_Zaid}"):
                    await rdb.delete(f"{get.user.id}:mute:{m.chat.id}{Dev_Zaid}")
                    await rdb.srem(f"{m.chat.id}:listMUTE:{Dev_Zaid}", get.user.id)
                    text += "كتم\n"
                    co += 1
                if co > 0:
                    return await m.reply(f"{k} فكيت عنه القيود التاليه:\n{text}\n☆")
                else:
                    return await m.reply(f"「 {get.user.mention} 」\n{k} ماله قيود من قبل\n☆")

            except Exception as e:
                logging.exception(e)
                return await m.reply(f"{k} مافي عضو بهذا اليوزر")
            # ⚠️ كود ميت — راجع AMBIGUOUS [C3]: لا يُنفَّذ أبداً لأن كل مسارات
            # try أعلاه تُنهي التنفيذ بـ return قبل الوصول لهذين السطرين.
            await m.chat.unban_member(get.user.id)
            return await m.reply(f"「 {get.user.mention} 」 \n{k} ابشر الغيت حظره\n☆")

    # ══════════════════════════════════════════════════════════════════════
    # 24. رفع القيود (رد)                                   (all.py سطر 3567)
    # ══════════════════════════════════════════════════════════════════════
    if text == "رفع القيود" and m.reply_to_message and m.reply_to_message.from_user:
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( المدير وفوق ) بس")
        else:
            try:
                text = ""
                co = 0
                get = await m.chat.get_member(m.reply_to_message.from_user.id)
                if get.status == ChatMemberStatus.BANNED:
                    await m.chat.unban_member(get.user.id)
                    text += "حظر\n"
                    co += 1
                if get.status == ChatMemberStatus.RESTRICTED:
                    await c.restrict_chat_member(
                        m.chat.id,
                        get.user.id,
                        ChatPermissions(
                            can_send_messages=True,
                            can_send_media_messages=True,
                            can_send_other_messages=True,
                            can_send_polls=True,
                            can_invite_users=True,
                            can_add_web_page_previews=True,
                            can_change_info=True,
                            can_pin_messages=True,
                        ),
                    )
                    text += "تقييد\n"
                    co += 1
                if await rdb.get(f"{get.user.id}:mute:{m.chat.id}{Dev_Zaid}"):
                    await rdb.delete(f"{get.user.id}:mute:{m.chat.id}{Dev_Zaid}")
                    await rdb.srem(f"{m.chat.id}:listMUTE:{Dev_Zaid}", get.user.id)
                    text += "كتم\n"
                    co += 1
                if co > 0:
                    return await m.reply(f"{k} فكيت عنه القيود التاليه:\n{text}\n☆")
                else:
                    return await m.reply(f"「 {get.user.mention} 」\n{k} ماله قيود من قبل\n☆")
            except Exception as e:
                logging.exception(e)
                return await m.reply(f"{k} العضو مو بالمجموعة")

    # ══════════════════════════════════════════════════════════════════════
    # 25. كشف البوتات                                       (all.py سطر 3608)
    # ══════════════════════════════════════════════════════════════════════
    if text == "كشف البوتات":
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( المدير وفوق ) بس")
        else:
            co = 0
            text = "بوتات المجموعة:\n\n"
            cc = 1
            async for mm in m.chat.get_members(filter=ChatMembersFilter.BOTS):
                if co == 100:
                    break
                text += f"{cc}) {mm.user.mention}"
                # 👑 دلالة ثابتة: يُضاف حصرًا لتمييز البوتات ذات صلاحيات الإشراف (Administrator) داخل قائمة "كشف البوتات"
                if mm.status == ChatMemberStatus.ADMINISTRATOR:
                    text += "👑"
                text += "\n"
                cc += 1
                co += 1
            text += "☆"
            if co == 0:
                return await m.reply(f"{k} مافيه بوتات")
            else:
                return await m.reply(text)

    # ══════════════════════════════════════════════════════════════════════
    # 26. مين ضافني                                         (all.py سطر 3630)
    # ══════════════════════════════════════════════════════════════════════
    if text == "مين ضافني":
        get = (await m.chat.get_member(m.from_user.id)).invited_by
        if not get:
            return await m.reply(f"{k} محد ضافك")
        else:
            return await m.reply(f"「 {get.mention} 」")

    # ══════════════════════════════════════════════════════════════════════
    # 27. بايو عشوائي                                       (all.py سطر 3637)
    # ══════════════════════════════════════════════════════════════════════
    if text == "بايو عشوائي":
        return await m.reply(f"{k} تحت الصيانة")

    # ══════════════════════════════════════════════════════════════════════
    # 28. مسح (رد)                                          (all.py سطر 3640)
    #     ⚠️ لا يوجد return في الأصل — التنفيذ يتابع للكتل التالية (محفوظ)
    # ══════════════════════════════════════════════════════════════════════
    if text == "مسح" and m.reply_to_message:
        if await mod_pls(m.from_user.id, m.chat.id):
            # ⚠️ راجع AMBIGUOUS [B2]/نمط مشابه: الأصل يستخدم admin_pls هنا
            # حرفياً (راجع AMBIGUOUS [C5] بالأسفل لتفصيل هذه النقطة تحديداً).
            await m.reply_to_message.delete()
            await m.delete()
        else:
            await m.delete()

    # ══════════════════════════════════════════════════════════════════════
    # 29. مسح <عدد>                                         (all.py سطر 3647)
    #     ⚠️ لا يوجد return نهائي في الأصل — التنفيذ يتابع للكتل التالية
    #     (محفوظ)؛ راجع أيضاً AMBIGUOUS [C5] بخصوص admin_pls
    # ══════════════════════════════════════════════════════════════════════
    if (
        text.startswith("مسح ")
        and len(text.split()) == 2
        and re.findall("[0-9]+", text)
    ):
        count = int(re.findall("[0-9]+", text)[0])
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.delete()
        else:
            if count > 400:
                return await m.reply(f"{k} اختار من 1 الى 400")
            else:
                for msg in range(m.id, m.id - count, -1):
                    try:
                        await c.delete_messages(m.chat.id, msg)
                    except Exception as e:
                        logging.exception(e)
                        pass

    # ══════════════════════════════════════════════════════════════════════
    # 30. تنزيل مشرف (رد)                                   (all.py سطر 3665)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تنزيل مشرف" and m.reply_to_message and m.reply_to_message.from_user:
        if not await owner_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( المالك وفوق ) بس")
        else:
            try:
                await c.promote_chat_member(
                    m.chat.id,
                    m.reply_to_message.from_user.id,
                    privileges=ChatPrivileges(
                        can_manage_chat=False,
                        can_delete_messages=False,
                        can_manage_video_chats=False,
                        can_restrict_members=False,
                        can_promote_members=False,
                        can_pin_messages=False,
                        can_change_info=False,
                        can_invite_users=False,
                    ),
                )
                return await m.reply(
                    f"「 {m.reply_to_message.from_user.mention} 」\n{k} نزلته من الاشراف\n☆"
                )
            except Exception as e:
                logging.exception(e)
                return await m.reply(
                    f"「 {m.reply_to_message.from_user.mention} 」\n{k} مو انا الي رفعته او ماعندي صلاحيات"
                )

    # ══════════════════════════════════════════════════════════════════════
    # 31. رفع مشرف (رد) — بدء تدفّق الحالة                  (all.py سطر 3692)
    # ══════════════════════════════════════════════════════════════════════
    if text == "رفع مشرف" and m.reply_to_message and m.reply_to_message.from_user:
        if not await owner_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( المالك وفوق ) بس")
        else:
            get = await m.chat.get_member(c.me.id)
            priv = get.privileges
            if (
                not priv.can_manage_chat
                or not priv.can_delete_messages
                or not priv.can_restrict_members
                or not priv.can_pin_messages
                or not priv.can_invite_users
                or not priv.can_change_info
                or not priv.can_promote_members
            ):
                return await m.reply(f"{k} كمل كل الصلاحيات والا لا تسولف")
            else:
                await rdb.set(
                    f"{m.from_user.id}:promote:{m.chat.id}",
                    m.reply_to_message.from_user.id,
                    ex=600,
                )
                return await m.reply(
                    f"""
{k} ⇜ حلو الحين ارسل صلاحيات المشرف

* ⇠ لرفع كل الصلاحيات ما عدا رفع المشرفين
** ⇠ لرفع كل الصلاحيات مع رفع المشرفين

⇜ يمديك تختار الصلاحيات وتعيين لقب للمشرف في سطر واحد

مثال: ** الهطف
☆""",
                    reply_markup=ForceReply(selective=True),
                    parse_mode=ParseMode.HTML,
                )

    # ══════════════════════════════════════════════════════════════════════
    # 32. تأكيد رفع مشرف — حالة معلّقة (all.py سطر 3729)
    #     ⚠️ راجع AMBIGUOUS [C6] — أمر غير ثابت النص، مُفعَّل فقط عبر حالة
    #     Redis معلّقة + شرط startswith("*") على أي نص لاحق من نفس المستخدم.
    # ══════════════════════════════════════════════════════════════════════
    if await rdb.get(f"{m.from_user.id}:promote:{m.chat.id}") and await owner_pls(
        m.from_user.id, m.chat.id
    ):
        id = int(await rdb.get(f"{m.from_user.id}:promote:{m.chat.id}"))
        if text.startswith("*"):
            await rdb.delete(f"{m.from_user.id}:promote:{m.chat.id}")
            if text.startswith("**"):
                can_promote_members = True
                type = 1
            else:
                can_promote_members = False
                type = 0
            if len(text.split()) > 1:
                title = text.split(None, 1)[1][:15:]
            else:
                title = None
            await c.promote_chat_member(
                m.chat.id,
                id,
                privileges=ChatPrivileges(
                    can_manage_chat=True,
                    can_delete_messages=True,
                    can_manage_video_chats=True,
                    can_restrict_members=True,
                    can_promote_members=can_promote_members,
                    can_change_info=True,
                    can_invite_users=True,
                    can_pin_messages=True,
                ),
            )
            if title:
                try:
                    await c.set_administrator_title(m.chat.id, id, title)
                except Exception as e:
                    logging.exception(e)
                    pass
            get = await m.chat.get_member(id)
            if type == 1:
                # ⚠️ راجع AMBIGUOUS [C7] — نفس مفتاح rankADMIN يُضبط في كلا
                # الفرعين (type == 1 وelse) رغم اختلاف الصلاحيات الفعلية.
                await rdb.set(f"{m.chat.id}:rankADMIN:{get.user.id}{Dev_Zaid}", 1)
                await rdb.sadd(f"{m.chat.id}:listADMIN:{Dev_Zaid}", get.user.id)
                return await m.reply(
                    f"{k} الحلو 「 {get.user.mention} 」 رفعته 〖 مشرف 〗 بكل صلاحيات\n☆"
                )
            else:
                await rdb.set(f"{m.chat.id}:rankADMIN:{get.user.id}{Dev_Zaid}", 1)
                await rdb.sadd(f"{m.chat.id}:listADMIN:{Dev_Zaid}", get.user.id)
                return await m.reply(
                    f"{k} الحلو 「 {get.user.mention} 」 رفعته 〖 مشرف 〗 بكل الصلاحيات عدا رفع المشرفين\n☆"
                )

    # ══════════════════════════════════════════════════════════════════════
    # 33. مسح قائمة التثبيت                                 (all.py سطر 3778)
    # ══════════════════════════════════════════════════════════════════════
    if text == "مسح قائمة التثبيت":
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( المدير وفوق ) بس")
        else:
            await c.unpin_all_chat_messages(m.chat.id)
            return await m.reply(f"{k} ابشر مسحت قائمة التثبيت\n☆")

    # ══════════════════════════════════════════════════════════════════════
    # 34. الاوامر / /commands / /commands@<username>        (all.py سطر 3785)
    # ══════════════════════════════════════════════════════════════════════
    if (
        text == "الاوامر"
        or text.lower() == "/commands"
        or text.lower() == f"/commands@{botUsername.lower()}"
    ):
        if await admin_pls(m.from_user.id, m.chat.id):
            channel = await rdb.get(f"{Dev_Zaid}:BotChannel") or "YQYQY6"
            return await m.reply(
                f"{k} اهلين فيك باوامر البوت\n\nللاستفسار - @{channel}",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "م1", callback_data=f"commands1:{m.from_user.id}"
                            ),
                            InlineKeyboardButton(
                                "م2", callback_data=f"commands2:{m.from_user.id}"
                            ),
                        ],
                        [
                            InlineKeyboardButton(
                                "م3", callback_data=f"commands3:{m.from_user.id}"
                            ),
                        ],
                        [
                            InlineKeyboardButton(
                                "الالعاب", callback_data=f"commands4:{m.from_user.id}"
                            ),
                            InlineKeyboardButton(
                                "التسليه", callback_data=f"commands5:{m.from_user.id}"
                            ),
                        ],
                        [
                            InlineKeyboardButton(
                                "اليوتيوب", callback_data=f"commands6:{m.from_user.id}"
                            ),
                        ],
                        [
                            InlineKeyboardButton(
                                "البنك", callback_data=f"commands7:{m.from_user.id}"
                            ),
                            InlineKeyboardButton(
                                "زواج", callback_data=f"commands8:{m.from_user.id}"
                            ),
                        ],
                    ]
                ),
            )
        else:
            return await m.reply(f"{k} هذا الأمر يخص ( الادمن وفوق ) بس")

    # لا يوجد أمر مطابق في هذا الملف — لم يُرسَل أي رد فعلي للمستخدم في هذا
    # المسار، لذا نُمرِّر المعالجة لبقية handlers group=28 (كانت هذه بالذات
    # نقطة النهاية الموصوفة في [C4] بالأسفل — أول ملف أبجدياً كان يوقف كل
    # ما بعده؛ الآن جميع الملفات الثمانية ترفع ContinuePropagation هنا).
    raise ContinuePropagation()


# ══════════════════════════════════════════════════════════════════════════════
# AMBIGUOUS — سلوكيات غامضة تحتاج مراجعة
# ══════════════════════════════════════════════════════════════════════════════
#
# [C1] "رفع الحظر / الغاء الحظر <هدف>" (البند 21، all.py سطر 3472-3476):
#      نفس فخ أسبقية المعامِلات الموثّق في all_moderation_1.py [A1]:
#          text.startswith("رفع الحظر ")
#          or text.startswith("الغاء الحظر ") and len(text.split()) == 3
#      يُقرأ فعلياً: startswith("رفع الحظر ") OR (startswith("الغاء الحظر ")
#      AND len==3). أي أن "رفع الحظر" وحدها (بأي عدد كلمات) تُفعِّل الكتلة
#      حتى لو لم يكن هناك 3 كلمات بالضبط، بعكس "الغاء الحظر" التي تتطلب
#      العدد بالضبط. محفوظ حرفياً كما في الأصل.
#
# [C2] "رفع الحظر / الغاء الحظر" (رد) (البند 22، all.py سطر 3495-3499):
#      نفس نوع الفخ:
#          text == "رفع الحظر"
#          or text == "الغاء الحظر" and m.reply_to_message and m.reply_to_message.from_user
#      يُقرأ: (text == "رفع الحظر") OR (text == "الغاء الحظر" AND رد AND
#      رد.from_user). كتابة "رفع الحظر" فقط (بلا أي رد على رسالة) تُفعِّل
#      الكتلة كاملة، وسيرفع m.chat.get_member(m.reply_to_message.from_user.id)
#      استثناء AttributeError لأن m.reply_to_message = None في هذه الحالة —
#      لكنه محاط بـ try/except عام هنا (على عكس [A2] في الملف السابق)
#      فسيُطبع "العضو مو بالمجموعة" رغم أن السبب الفعلي مختلف تماماً (لا يوجد
#      رد أصلاً). محفوظ حرفياً كما في الأصل.
#
# [C3] "رفع القيود <هدف>" (البند 23، all.py سطر 3517-3565):
#      السطران الأخيران بعد كتلة try/except (m.chat.unban_member(get.user.id)
#      ثم m.reply(...)) كود ميت 100% في الأصل: كل مسار داخل try (النجاح أو
#      عدم وجود قيود) يُنهي التنفيذ بـ return قبل الوصول إليهما، وexcept
#      يُنهي بـ return أيضاً. لا توجد أي حالة تصل لهذين السطرين فعلياً.
#      نُقلا حرفياً (كما يطلب عدم تغيير أي منطق) مع تعليق توضيحي فقط.
#
# [C4] (تم الإصلاح) group=28 مشترك بين 8 ملفات (all_settings،
#      all_voice_and_blocklist، all_protection، all_features_toggle،
#      all_locks_1، all_locks_2، all_moderation_1، all_moderation_2) —
#      جميعها تستخدم نفس الفلتر الواسع (filters.group & filters.text) في
#      نفس المجموعة الرقمية. سابقاً لم يكن أي منها يستدعي
#      pyrogram.ContinuePropagation() عند عدم مطابقة أي أمر داخلي، فكان أول
#      handler يُسجَّل (أبجدياً: all_features_toggle.py) يُوقف الانتقال لبقية
#      الـ8 ملفات بمجرد أن يُستدعى وينتهي طبيعياً، بغض النظر عن نتيجته
#      الداخلية — مما يعني أن أوامر الملفات السبعة الأخرى لم تكن تُنفَّذ
#      عملياً إطلاقاً.
#
#      الإصلاح المطبَّق الآن في الملفات الثمانية جميعاً:
#        1) كل مسار "لم يتطابق شيء" (نهاية سلسلة if/elif دون أي رد فعلي
#           للمستخدم) يرفع الآن raise ContinuePropagation() صراحة، بدل
#           الانتهاء الضمني بـ return None.
#        2) core/errors.py (safe_handler) عُدِّل ليُعيد رفع
#           ContinuePropagation/StopPropagation صراحةً قبل `except
#           Exception:` العام — بدونه كانت هذه الكتلة العامة ستلتقط
#           الإشارة بصمت (لأنها استثناءات من فئة Exception كأي استثناء آخر)
#           وتُسجّلها كخطأ غير معالَج بدل تمريرها فعلياً لموزّع pyrogram.
#           هذا التعديل الثاني ضروري وإلا فالإصلاح الأول عديم الأثر تماماً
#           رغم ظهوره صحيحاً في القراءة الأولى للكود. (تنبيه توافقي إضافي:
#           تأكَّد أن هذين الصنفين في نسخة kurigram المُثبَّتة ليسا مبنيين
#           مباشرة على StopIteration — رفع StopIteration من داخل
#           `async def` يُحوَّل تلقائياً بواسطة بايثون (PEP 479) إلى
#           RuntimeError، مما يُبطل الآلية كلياً. راجع
#           tests/test_group28_continue_propagation.py.)
#      مسارات "الأهلية" المبكرة (enable/mute/addCustom/delCustom/isLockCommand)
#      في بداية كل دالة تركت كما هي (لا تزال return عادي) لأنها خارج نطاق
#      هذا الإصلاح المطلوب تحديداً (مطابقة/عدم مطابقة الأوامر)، وتغييرها قد
#      يُبدّل دلالة "تعطيل هذا الملف بالكامل لهذه المحادثة" — قرار منفصل.
#
# [C5] "مسح" و"مسح <عدد>" (البندان 28 و29، all.py سطر 3640 وسطر 3647):
#      الأصل يستخدم admin_pls للتحقق من الصلاحية في كلا الأمرين (وليس mod_pls
#      أو owner_pls كما في أوامر حذف أخرى بنفس الملف السابق) — محفوظ حرفياً.
#      كما أن كلا الأمرين لا يملك return نهائي بعد تنفيذه بنجاح (فقط عند فشل
#      الصلاحية أو تجاوز الحد)، لذا التنفيذ يتابع نظرياً لبقية كتل if في نفس
#      الدالة بعد نجاح الحذف — لا يوجد أي أمر لاحق سيطابق نفس النص، فالأثر
#      عملياً معدوم، لكنه محفوظ لمطابقة الأصل تماماً.
#
# [C6] "تأكيد رفع مشرف" (البند 32، all.py سطر 3729-3776):
#      هذا **ليس أمراً بنص ثابت** — بل استمرارية حالة معلّقة في Redis
#      (`{uid}:promote:{cid}`) ضُبطت مسبقاً بواسطة أمر "رفع مشرف" (البند 31).
#      الشرط الفعلي: إن وُجدت الحالة المعلّقة + owner_pls(uid,cid) صحيح، تُفحص
#      **أي رسالة نصية لاحقة** من نفس المستخدم في نفس المجموعة: إن بدأت بـ"*"
#      تُنفَّذ عملية الترقية والحالة تُحذف، وإلا (لا تبدأ بـ"*") **لا يحدث شيء
#      إطلاقاً** (لا رد، لا حذف للحالة) والتنفيذ يتابع لبقية الكتل. لم أفهم
#      بوضوح تام سبب عدم وجود رسالة خطأ أو مهلة انتهاء صريحة غير TTL الـ600
#      ثانية على مفتاح Redis نفسه (`ex=600`) — أي أن المستخدم لديه 10 دقائق
#      فقط لإرسال نص يبدأ بـ"*" وإلا تنتهي الحالة صامتة دون أي إشعار له.
#      لا يمكن تسجيل هذا "كنص أمر" حقيقي في core/dispatcher.py لأنه ليس نصاً
#      ثابتاً (أي نص يبدأ بـ"*" من مستخدم معيّن في حالة معيّنة يُطابقه)؛ سجّلته
#      أعلاه كتعليق فقط ضمن التوثيق، ولم أُضِف مفتاحاً وهمياً في COMMAND_HANDLERS
#      تفادياً لتضليل أي قارئ للجدول لاحقاً.
#
# [C7] "تأكيد رفع مشرف" — مفتاح rankADMIN مكرر (البند 32، all.py سطر 3766-3776):
#      كلا الفرعين (type == 1: رفع كامل مع صلاحية ترقية غيره، وelse: رفع كامل
#      بدون تلك الصلاحية) يضبطان **نفس** المفتاح `rankADMIN` بنفس القيمة (1)
#      ويضيفان لنفس المجموعة `listADMIN` — رغم أن can_promote_members يختلف
#      فعلياً بين الحالتين على مستوى تليجرام نفسه. أي أن نظام الرتب الداخلي
#      (get_rank/admin_pls في helpers/ranks.py) لا يُفرّق إطلاقاً بين "أدمن
#      بصلاحية ترقية" و"أدمن بدونها" — كلاهما يُعتبر نفس الرتبة "ادمن" لاحقاً.
#      هذا يبدو خطأ أصلي (ربما كان يُفترض مفتاح مختلف مثل rankADMIN2 للحالة
#      type==1) لكنني لم أُغيّره لأنه سلوك محفوظ من الأصل وليس نص رسالة فقط.

