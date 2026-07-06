"""
all_moderation_1.py
منقول من bmqa/Plugins/all.py (guardCommands — سطر 3060 → 3470 تقريباً)
الفئة: الإدارة والتقييد (تقييد/إلغاء تقييد، حظر/إلغاء حظر، طرد، تثبيت،
       اهمس، تفعيل/تعطيل التنظيف الدوري)

⚠️ ملاحظة نطاق: أمر "ابلاغ" (all.py سطر 3042) لم يُنقل هنا لأنه مهاجَر
مسبقاً ضمن all_features_toggle.py (راجع "29. ابلاغ" في ذلك الملف). النطاق
الفعلي المنقول في هذا الملف يبدأ من "المقيدين" (سطر 3060) وينتهي عند نهاية
كتلة "طرد" (رد) (سطر 3470)، وهي أقرب حد طبيعي لنهاية كتلة متجانسة ضمن
النطاق التقريبي المطلوب (حتى 3451).

التحويلات المطبّقة:
  - بوابة الأهلية + تطبيع النص (فحص enable/mute/addCustom/delCustom + دمج
    اسم البوت المخصص والأوامر المخصصة + isLockCommand) لم تُكرَّر محلياً؛
    اسْتُوردت من all_helpers.resolve_guard_text (دالة أُضيفت هناك خصيصاً
    لهذا الغرض بدل تكرار "_resolve_text" كما في الملفات الأربعة السابقة).
  - mod_pls / owner_pls / gowner_pls / pre_pls / get_rank من helpers.ranks
    (أصبحت async في bmqa-v2) → await قبل كل استدعاء، دون أي تغيير منطقي.
  - r.hget/hset/hdel(Dev_Zaid + str(cid), ...) → await rdb.hget/hset/hdel(...)
  - m.chat.get_member(...) → await m.chat.get_member(...) [نفس الدالة تماماً،
    فقط إضافة await، بنفس نمط bmqa-v2/Plugins/id.py و/group_update.py]
  - c.restrict_chat_member/m.chat.ban_member/m.chat.unban_member(...) → await
  - for mm in c.get_chat_members(...) / m.chat.get_members(...) →
    async for mm in c.get_chat_members(...)
  - m.reply_to_message.pin()/.unpin() → await
  - time.sleep غير موجود في هذا النطاق (لا يوجد استبدال مطلوب هنا فعلياً)
  - wsdb.setex(key=id, ttl=3600, value=data) → راجع AMBIGUOUS [B1] بالأسفل:
    core/db.py الحالي لا يوفّر setex على KVSqliteDB، فاستُخدم wsdb.set بدل
    ذلك (فقدان انتهاء الصلاحية التلقائي بعد ساعة — سلوك تقريبي وليس مطابقاً).
  - `import uuid` المحلي داخل كتلة "اهمس" رُفع لأعلى الملف (لا تغيير سلوك).

كل نصوص الرسائل المرسلة للمستخدم (بما فيها الرتب المطلوبة المختلفة بين
أمر وآخر حتى لو بدت متكررة، وأي تناقضات محفوظة من الأصل بين نص رسالة
الصلاحية والدالة الفعلية المُستخدَمة للتحقق) نُقلت حرفياً دون أي تعديل.

سلوكيات غامضة موثّقة في قسم AMBIGUOUS آخر الملف.
"""

import logging
import re
import uuid

from pyrogram import Client, ContinuePropagation, filters
from pyrogram.enums import ChatMemberStatus, ChatMembersFilter
from pyrogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton

from config import Dev_Zaid
from core.db import rdb, wsdb, wsdb_setex
from core.cache import members_cache
from core.errors import safe_handler
from core.dispatcher import register
from helpers.ranks import mod_pls, owner_pls, gowner_pls, pre_pls, get_rank
from Plugins.all_helpers import resolve_guard_text


# ══════════════════════════════════════════════════════════════════════════════
# الهاندلر الرئيسي — group=28 (نفس الأصل ونفس بقية ملفات guardCommands)
#
# كل الأوامر أدناه مسجَّلة أيضاً بجدول core/dispatcher.py (COMMAND_HANDLERS)
# بنفس نص الأمر بالضبط كما في الأصل، بما في ذلك كل صيغة بديلة (مثل
# "الغاء تقييد" مقابل "الغاء التقييد"). التسجيل هنا هو فهرسة/مرجع فقط —
# التوجيه الفعلي لكل رسالة يتم عبر Client.on_message + سلسلة if الداخلية
# تماماً كما في بقية ملفات all_*.py المنقولة سابقاً، وليس عبر core.dispatcher
# .dispatch() (غير مُستخدَمة فعلياً في أي Plugin منقول حتى الآن).
# ══════════════════════════════════════════════════════════════════════════════

@register("المقيدين")
@register("مسح المقيدين")
@register("تثبيت")
@register("الغاء التثبيت")
@register("تقييد ")  # startswith + هدف (id/username)
@register("تقييد")  # رد مباشر بلا هدف نصي
@register("الغاء تقييد ")
@register("الغاء التقييد ")
@register("الغاء تقييد")
@register("الغاء التقييد")
@register("المحظورين")
@register("مسح المحظورين")
@register("حظر ")
@register("حظر")
@register("طرد البوتات")
@register("طرد ")
@register("اهمس")
@register("تعطيل التنظيف")
@register("تفعيل التنظيف")
@register("وضع وقت التنظيف")
@register("وقت التنظيف")
@register("طرد")
@Client.on_message(filters.group & filters.text, group=28)
@safe_handler
async def moderationHandler1(c, m) -> None:
    """
    يعالج أوامر التقييد/الحظر/الطرد/التثبيت/اهمس/التنظيف الدوري.
    يُشغَّل على group=28 بعد الفلاتر الأخرى، بنفس نمط بقية ملفات guardCommands
    المنقولة (all_settings.py، all_voice_and_blocklist.py، all_protection.py،
    all_features_toggle.py).
    """

    text = await resolve_guard_text(m)
    if text is None:
        return

    k = await rdb.get(f"{Dev_Zaid}:botkey")
    channel = await rdb.get(f"{Dev_Zaid}:BotChannel") or "YQYQY6"

    # ══════════════════════════════════════════════════════════════════════
    # 1. المقيدين                                         (all.py سطر 3060)
    # ══════════════════════════════════════════════════════════════════════
    if text == "المقيدين":
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( المدير وفوق ) بس")
        else:
            co = 0
            cc = 1
            list_text = "المقيدين:\n\n"
            restricted = await members_cache.get_admins(
                c, m.chat.id, ChatMembersFilter.RESTRICTED
            )
            for mm in restricted:
                if co == 100:
                    break
                if not mm.user.is_deleted:
                    co += 1
                    user = (
                        f"@{mm.user.username}"
                        if mm.user.username
                        else f"[@{channel}](tg://user?id={mm.user.id})"
                    )
                    list_text += f"{cc} ➣ {user} ☆ ( `{mm.user.id}` )\n"
                    cc += 1
            list_text += "☆"
            if co == 0:
                return await m.reply(f"{k} مافيه مقيدين")
            else:
                return await m.reply(list_text)

    # ══════════════════════════════════════════════════════════════════════
    # 2. مسح المقيدين                                     (all.py سطر 3087)
    # ══════════════════════════════════════════════════════════════════════
    if text == "مسح المقيدين":
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( المدير وفوق ) بس")
        else:
            co = 0
            restricted = await members_cache.get_admins(
                c, m.chat.id, ChatMembersFilter.RESTRICTED
            )
            for mm in restricted:
                co += 1
                await c.restrict_chat_member(
                    m.chat.id,
                    mm.user.id,
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
            if co > 0:
                # يجب إبطال الكاش هنا: هذا الأمر أصلاً يُغيّر حالة "المقيدين"
                # (يرفع التقييد عن الجميع)، فإن بقيت القائمة القديمة مخزَّنة
                # سيُظهر أمر "المقيدين" لاحقاً (أو أي استدعاء آخر لنفس المفتاح)
                # مستخدمين تم رفع التقييد عنهم فعلاً حتى تنتهي مهلة TTL.
                members_cache.invalidate_chat(m.chat.id)
            if co == 0:
                return await m.reply(f"{k} مافيه مقيدين")
            else:
                return await m.reply(f"{k} ابشر مسحت ( {co} ) من المقيدين\n☆")

    # ══════════════════════════════════════════════════════════════════════
    # 3. تثبيت (رد)                                       (all.py سطر 3115)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تثبيت" and m.reply_to_message:
        if await mod_pls(m.from_user.id, m.chat.id):
            await m.reply_to_message.pin(disable_notification=False)
            await m.reply(f"{k} ابشر ثبتت الرسالة\n☆")

    # ══════════════════════════════════════════════════════════════════════
    # 4. الغاء التثبيت (رد)                                (all.py سطر 3120)
    # ══════════════════════════════════════════════════════════════════════
    if text == "الغاء التثبيت" and m.reply_to_message:
        if await mod_pls(m.from_user.id, m.chat.id):
            await m.reply_to_message.unpin()
            await m.reply(f"{k} ابشر لغيت تثبيت الرسالة\n☆")

    # ══════════════════════════════════════════════════════════════════════
    # 5. تقييد <id/username>                              (all.py سطر 3125)
    # ══════════════════════════════════════════════════════════════════════
    if text.startswith("تقييد ") and len(text.split()) == 2:
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( المدير وفوق ) بس")
        else:
            try:
                user = int(text.split()[1])
            except Exception as e:
                logging.exception(e)
                user = text.split()[1].replace("@", "")
            try:
                get = await m.chat.get_member(user)
                if m.from_user.id == get.user.id:
                    return await m.reply("شفيك تبي تنزل نفسك")
                if await pre_pls(get.user.id, m.chat.id):
                    rank = await get_rank(get.user.id, m.chat.id)
                    return await m.reply(f"{k} هييه مايمديك تقييد {rank} ياورع!")
                if get.status == ChatMemberStatus.RESTRICTED:
                    return await m.reply(f"「 {get.user.mention} 」 \n{k} مقيد من قبل\n☆")
            except Exception as e:
                logging.exception(e)
                return await m.reply(f"{k} مافي عضو بهذا اليوزر")
            await c.restrict_chat_member(
                m.chat.id, get.user.id, ChatPermissions(can_send_messages=False)
            )
            return await m.reply(f"「 {get.user.mention} 」 \n{k} قييدته\n☆")

    # ══════════════════════════════════════════════════════════════════════
    # 6. تقييد (رد)                                        (all.py سطر 3149)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تقييد" and m.reply_to_message and m.reply_to_message.from_user:
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( المدير وفوق ) بس")
        else:
            if m.from_user.id == m.reply_to_message.from_user.id:
                return await m.reply("شفيك تبي تنزل نفسك")
            get = await m.chat.get_member(m.reply_to_message.from_user.id)
            if await pre_pls(m.reply_to_message.from_user.id, m.chat.id):
                rank = await get_rank(m.reply_to_message.from_user.id, m.chat.id)
                return await m.reply(f"{k} هييه مايمديك تقييد {rank} ياورع!")
            if get.status == ChatMemberStatus.RESTRICTED:
                return await m.reply(
                    f"「 {m.reply_to_message.from_user.mention} 」 \n{k} مقيد من قبل\n☆"
                )
            await c.restrict_chat_member(
                m.chat.id,
                m.reply_to_message.from_user.id,
                ChatPermissions(can_send_messages=False),
            )
            return await m.reply(
                f"「 {m.reply_to_message.from_user.mention} 」 \n{k} قييدته\n☆"
            )

    # ══════════════════════════════════════════════════════════════════════
    # 7. الغاء تقييد / الغاء التقييد <id/username>         (all.py سطر 3172)
    #    ⚠️ راجع AMBIGUOUS [A1] — شرط أسبقية معامِلات محفوظ من الأصل حرفياً
    # ══════════════════════════════════════════════════════════════════════
    if (
        text.startswith("الغاء تقييد ")
        or text.startswith("الغاء التقييد ")
        and len(text.split()) == 3
    ):
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( الادمن وفوق ) بس")
        else:
            try:
                user = int(text.split()[2])
            except Exception as e:
                logging.exception(e)
                user = text.split()[2].replace("@", "")
            try:
                get = await m.chat.get_member(user)
                if not get.status == ChatMemberStatus.RESTRICTED:
                    return await m.reply(f"「 {get.user.mention} 」 \n{k} مو مقيد من قبل\n☆")
            except Exception as e:
                logging.exception(e)
                return await m.reply(f"{k} مافي عضو بهذا اليوزر")
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
            return await m.reply(f"「 {get.user.mention} 」 \n{k} ابشر الغيت تقييده\n☆")

    # ══════════════════════════════════════════════════════════════════════
    # 8. الغاء تقييد / الغاء التقييد (رد)                  (all.py سطر 3206)
    #    ⚠️ راجع AMBIGUOUS [A2] — نفس نوع شرط الأسبقية، لكن هنا أثره أخطر
    #    (قد يحاول الوصول إلى m.reply_to_message.from_user وهو None)
    # ══════════════════════════════════════════════════════════════════════
    if (
        text == "الغاء تقييد"
        or text == "الغاء التقييد"
        and m.reply_to_message
        and m.reply_to_message.from_user
    ):
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( الادمن وفوق ) بس")
        else:
            get = await m.chat.get_member(m.reply_to_message.from_user.id)
            if not get.status == ChatMemberStatus.RESTRICTED:
                return await m.reply(
                    f"「 {m.reply_to_message.from_user.mention} 」 \n{k} مو مقيد من قبل\n☆"
                )
            await c.restrict_chat_member(
                m.chat.id,
                m.reply_to_message.from_user.id,
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
            return await m.reply(
                f"「 {m.reply_to_message.from_user.mention} 」 \n{k} ابشر الغيت تقييده\n☆"
            )

    # ══════════════════════════════════════════════════════════════════════
    # 9. المحظورين                                        (all.py سطر 3238)
    # ══════════════════════════════════════════════════════════════════════
    if text == "المحظورين":
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( المدير وفوق ) بس")
        else:
            co = 0
            cc = 1
            list_text = "المحظورين:\n\n"
            async for mm in c.get_chat_members(m.chat.id, filter=ChatMembersFilter.BANNED):
                if co == 100:
                    break
                if mm.user:
                    if not mm.user.is_deleted:
                        co += 1
                        user = (
                            f"@{mm.user.username}"
                            if mm.user.username
                            else f"[@{channel}](tg://user?id={mm.user.id})"
                        )
                        list_text += f"{cc} ➣ {user} ☆ ( `{mm.user.id}` )\n"
                        cc += 1
                if mm.chat:
                    co += 1
                    user = f"@{mm.chat.username}"
                    list_text += f"{cc} ➣ {user} ☆ (`{mm.chat.id}`)\n"
                    cc += 1
            list_text += "☆"
            if co == 0:
                return await m.reply(f"{k} مافيه محظورين")
            else:
                return await m.reply(list_text)

    # ══════════════════════════════════════════════════════════════════════
    # 10. مسح المحظورين                                   (all.py سطر 3269)
    # ══════════════════════════════════════════════════════════════════════
    if text == "مسح المحظورين":
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( الادمن وفوق ) بس")
        else:
            co = 0
            async for mm in c.get_chat_members(m.chat.id, filter=ChatMembersFilter.BANNED):
                if mm.user:
                    co += 1
                    await c.unban_chat_member(m.chat.id, mm.user.id)
                if mm.chat:
                    co += 1
                    await c.unban_chat_member(m.chat.id, mm.chat.id)
            if co == 0:
                return await m.reply(f"{k} مافيه محظورين")
            else:
                return await m.reply(f"{k} ابشر مسحت ( {co} ) من المحظورين\n☆")

    # ══════════════════════════════════════════════════════════════════════
    # 11. حظر <id/username>                                (all.py سطر 3286)
    # ══════════════════════════════════════════════════════════════════════
    if text.startswith("حظر ") and len(text.split()) == 2:
        if "@" not in text and not re.findall("[0-9]+", text):
            return
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( المدير وفوق ) بس")
        else:
            try:
                user = int(text.split()[1])
            except Exception as e:
                logging.exception(e)
                user = text.split()[1].replace("@", "")
            try:
                get = await m.chat.get_member(user)
                if m.from_user.id == get.user.id:
                    return await m.reply("شفيك تبي تنزل نفسك")
                if await pre_pls(get.user.id, m.chat.id):
                    rank = await get_rank(get.user.id, m.chat.id)
                    return await m.reply(f"{k} هييه مايمديك تحظر {rank} ياورع!")
                if get.status == ChatMemberStatus.BANNED:
                    return await m.reply(f"「 {get.user.mention} 」 \n{k} محظور من قبل\n☆")
            except Exception as e:
                logging.exception(e)
                return await m.reply(f"{k} مافي عضو بهذا اليوزر")
            await m.chat.ban_member(get.user.id)
            return await m.reply(f"「 {get.user.mention} 」 \n{k} حظرته\n☆")

    # ══════════════════════════════════════════════════════════════════════
    # 12. حظر (رد)                                         (all.py سطر 3310)
    # ══════════════════════════════════════════════════════════════════════
    if text == "حظر" and m.reply_to_message and m.reply_to_message.from_user:
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( المدير وفوق ) بس")
        else:
            if m.from_user.id == m.reply_to_message.from_user.id:
                return await m.reply("شفيك تبي تنزل نفسك")
            get = await m.chat.get_member(m.reply_to_message.from_user.id)
            if await pre_pls(m.reply_to_message.from_user.id, m.chat.id):
                rank = await get_rank(m.reply_to_message.from_user.id, m.chat.id)
                return await m.reply(f"{k} هييه مايمديك تحظر {rank} ياورع!")
            if get.status == ChatMemberStatus.BANNED:
                return await m.reply(
                    f"「 {m.reply_to_message.from_user.mention} 」 \n{k} محظور من قبل\n☆"
                )
            await m.chat.ban_member(m.reply_to_message.from_user.id)
            return await m.reply(
                f"「 {m.reply_to_message.from_user.mention} 」 \n{k} حظرته\n☆"
            )

    # ══════════════════════════════════════════════════════════════════════
    # 13. طرد البوتات                                      (all.py سطر 3329)
    # ══════════════════════════════════════════════════════════════════════
    if text == "طرد البوتات":
        if not await owner_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( المالك وفوق ) بس")
        else:
            co = 0
            async for mm in c.get_chat_members(m.chat.id, filter=ChatMembersFilter.BOTS):
                try:
                    await m.chat.ban_member(mm.user.id)
                    co += 1
                except Exception as e:
                    logging.exception(e)
                    pass
            if co == 0:
                return await m.reply(f"{k} مافيه بوتات")
            else:
                return await m.reply(f"{k} ابشر حظر ( {co} ) بوت\n☆")

    # ══════════════════════════════════════════════════════════════════════
    # 14. طرد <id/username>                                (all.py سطر 3345)
    # ══════════════════════════════════════════════════════════════════════
    if text.startswith("طرد ") and len(text.split()) == 2:
        if "@" not in text and not re.findall("[0-9]+", text):
            return
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( الادمن وفوق ) بس")
        else:
            try:
                user = int(text.split()[1])
            except Exception as e:
                logging.exception(e)
                user = text.split()[1].replace("@", "")
            try:
                get = await m.chat.get_member(user)
                if m.from_user.id == get.user.id:
                    return await m.reply("شفيك تبي تنزل نفسك")
                if await pre_pls(get.user.id, m.chat.id):
                    rank = await get_rank(get.user.id, m.chat.id)
                    return await m.reply(f"{k} هييه مايمديك تطرد {rank} ياورع!")
                if get.status == ChatMemberStatus.BANNED:
                    return await m.reply(f"「 {get.user.mention} 」 \n{k} مطرود من قبل\n☆")
            except Exception as e:
                logging.exception(e)
                return await m.reply(f"{k} مافي عضو بهذا اليوزر")
            await m.chat.ban_member(get.user.id)
            await m.chat.unban_member(get.user.id)
            return await m.reply(f"「 {get.user.mention} 」 \n{k} طردته\n☆")

    # ══════════════════════════════════════════════════════════════════════
    # 15. اهمس (رد)                                        (all.py سطر 3370)
    #    ⚠️ راجع AMBIGUOUS [B1] — wsdb.setex غير مدعومة حالياً في core/db.py
    # ══════════════════════════════════════════════════════════════════════
    if text == "اهمس" and m.reply_to_message and m.reply_to_message.from_user:
        if await rdb.get(f"{m.chat.id}:disableWHISPER:{Dev_Zaid}"):
            return await m.reply(f"{k} امر اهمس معطل")
        user_id = m.reply_to_message.from_user.id
        if user_id == m.from_user.id:
            return await m.reply(f"{k} مافيك تهمس لنفسك ياغبي")
        else:
            id = str(uuid.uuid4())[:6]
            a = await m.reply(
                f"{k} تم تحديد الهمسة الى 「 {m.reply_to_message.from_user.mention} 」",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                f"اهمس الى [ {m.reply_to_message.from_user.first_name[:25]} ]",
                                url=f"t.me/{c.me.username}?start=hmsa{id}",
                            )
                        ]
                    ]
                ),
            )
            data = {
                "from": m.from_user.id,
                "to": user_id,
                "chat": m.chat.id,
                "id": a.id,
            }
            # wsdb.set(str(id), data)
            # ── تم إصلاح AMBIGUOUS [B1]: صلاحية 1 ساعة حقيقية الآن عبر
            #    core/db.wsdb_setex بدل wsdb.set العادي (راجع core/db.py).
            await wsdb_setex(id, data, 3600)
            return True

    # ══════════════════════════════════════════════════════════════════════
    # 16. تعطيل التنظيف                                    (all.py سطر 3403)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تعطيل التنظيف":
        if not await gowner_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( المالك الاساسي وفوق ) بس")
        else:
            if not await rdb.hget(Dev_Zaid + str(m.chat.id), "ena-clean"):
                return await m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} التنظيف معطل من قبل\n☆"
                )
            else:
                await rdb.hdel(Dev_Zaid + str(m.chat.id), "ena-clean")
                return await m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت التنظيف\n☆"
                )

    # ══════════════════════════════════════════════════════════════════════
    # 17. تفعيل التنظيف                                    (all.py سطر 3417)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تفعيل التنظيف":
        if not await gowner_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( المالك الاساسي وفوق ) بس")
        else:
            if await rdb.hget(Dev_Zaid + str(m.chat.id), "ena-clean"):
                return await m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} التنظيف مفعل من قبل\n☆"
                )
            else:
                await rdb.hset(Dev_Zaid + str(m.chat.id), "ena-clean", 1)
                return await m.reply(
                    f"{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت التنظيف\n☆"
                )

    # ══════════════════════════════════════════════════════════════════════
    # 18. وضع وقت التنظيف <ثواني>                          (all.py سطر 3431)
    # ══════════════════════════════════════════════════════════════════════
    if re.search("^وضع وقت التنظيف [0-9]+$", text):
        if not await gowner_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( المالك الاساسي وفوق ) بس")
        else:
            secs = int(text.split()[3])
            if secs > 3600 or secs < 60:
                return await m.reply(
                    f"{k} عليك تحديد وقت التنظيف بالثواني من 60 الى 3600 ثانية"
                )
            else:
                await rdb.hset(Dev_Zaid + str(m.chat.id), "clean-secs", secs)
                return await m.reply(f"{k} ابشر وضعت وقت التنظيف ( {secs} ) ثانية\n☆")

    # ══════════════════════════════════════════════════════════════════════
    # 19. وقت التنظيف                                      (all.py سطر 3444)
    # ══════════════════════════════════════════════════════════════════════
    if text == "وقت التنظيف":
        if not await gowner_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( المالك الاساسي وفوق ) بس")
        else:
            secs = await rdb.hget(Dev_Zaid + str(m.chat.id), "clean-secs") or "60"
            return await m.reply(f"{k} وقت التنظيف الحالي ( {secs} ) ثانية")

    # ══════════════════════════════════════════════════════════════════════
    # 20. طرد (رد)                                         (all.py سطر 3451)
    # ══════════════════════════════════════════════════════════════════════
    if text == "طرد" and m.reply_to_message and m.reply_to_message.from_user:
        if not await mod_pls(m.from_user.id, m.chat.id):
            return await m.reply(f"{k} هذا الأمر يخص ( المدير وفوق ) بس")
        else:
            try:
                if m.from_user.id == m.reply_to_message.from_user.id:
                    return await m.reply("شفيك تبي تنزل نفسك")
                get = await m.chat.get_member(m.reply_to_message.from_user.id)
                if await pre_pls(m.reply_to_message.from_user.id, m.chat.id):
                    rank = await get_rank(m.reply_to_message.from_user.id, m.chat.id)
                    return await m.reply(f"{k} هييه مايمديك تطرد {rank} ياورع!")
                if get.status == ChatMemberStatus.BANNED:
                    return await m.reply(
                        f"「 {m.reply_to_message.from_user.mention} 」 \n{k} مطرود من قبل\n☆"
                    )
                await m.chat.ban_member(m.reply_to_message.from_user.id)
                await m.reply(f"「 {m.reply_to_message.from_user.mention} 」 \n{k} طردته\n☆")
                return await m.chat.unban_member(m.reply_to_message.from_user.id)
            except Exception as e:
                logging.exception(e)
                return await m.reply(f"{k} العضو مو بالمجموعة")

    # لا يوجد أمر من الأوامر الـ20 أعلاه يطابق النص — لم يُرسَل أي رد فعلي
    # للمستخدم في هذا المسار، لذا نُمرِّر المعالجة لبقية handlers group=28
    # (راجع [C4] في all_moderation_2.py لشرح المشكلة الأصلية).
    raise ContinuePropagation()


# ══════════════════════════════════════════════════════════════════════════════
# AMBIGUOUS — سلوكيات غامضة تحتاج مراجعة
# ══════════════════════════════════════════════════════════════════════════════
#
# [A1] "الغاء تقييد / الغاء التقييد <هدف>" (البند 7، all.py سطر 3172-3176):
#      الشرط الأصلي مكتوب:
#          text.startswith("الغاء تقييد ")
#          or text.startswith("الغاء التقييد ") and len(text.split()) == 3
#      بسبب أسبقية عوامل بايثون (and أقوى من or)، هذا يُقرأ فعلياً:
#          startswith("الغاء تقييد ")
#          OR (startswith("الغاء التقييد ") AND len(text.split()) == 3)
#      أي أن شرط len==3 لا ينطبق إطلاقاً على الصيغة الأولى "الغاء تقييد ".
#      رسالة المصدر ("الأمر يخص الادمن وفوق") تُستخدم بغض النظر عن عدد
#      الكلمات لتلك الصيغة تحديداً. محفوظ حرفياً كما في الأصل (لم أُصلحه).
#
# [A2] "الغاء تقييد / الغاء التقييد" (رد) (البند 8، all.py سطر 3206-3211):
#      نفس نوع الشرط:
#          text == "الغاء تقييد"
#          or text == "الغاء التقييد" and m.reply_to_message and m.reply_to_message.from_user
#      يُقرأ: (text == "الغاء تقييد") OR (text == "الغاء التقييد" AND رد AND
#      رد.from_user). هذا يعني أن كتابة "الغاء تقييد" فقط (نص مطابق تماماً،
#      بدون أي رسالة مردود عليها) تُفعِّل الكتلة بالكامل، وحين تصل الشيفرة
#      إلى `m.reply_to_message.from_user.id` بلا رد فعلي سيرفع ذلك استثناءً
#      (AttributeError) لا يُمسكه أي try/except داخل هذه الكتلة تحديداً — لكنه
#      سيُمسك ويُسجَّل عبر safe_handler (طبقة الحماية الخارجية) بدل أن يُسقط
#      العملية بصمت كما كان يحدث في الأصل (حيث كان الخطأ يُطبع/يُهمل حسب آلية
#      التعامل مع الأخطاء في bmqa الأصلي على مستوى الـ Thread). لم أُضِف أي
#      فحص إضافي لتفادي هذا لأن ذلك سيُغيّر المنطق الأصلي؛ فقط أنقله كما هو.
#
# [B1] "اهمس" — wsdb.setex(key=id, ttl=3600, value=data) (all.py سطر 3400):
#      هذا الاستدعاء الوحيد في كل الكود الأصلي الذي يستخدم .setex() على
#      wsdb (كل الاستخدامات الأخرى في bmqa الأصلي وفي bmqa-v2/Plugins/
#      private_and_sudos.py تستخدم فقط get/set/delete). كائن KVSqliteDB في
#      core/db.py الحالي لا يوفّر setex أصلاً (فقط get/set/delete/connect)،
#      ولا يمكنني التأكد من أن حزمة kvsqlite.asyncio الفعلية توفّر setex
#      بنفس توقيع/دلالة sync الأصلية دون تثبيتها والاطلاع على مصدرها.
#      لذلك استخدمتُ `await wsdb.set(id, data)` كبديل آمن متاح فعلاً في
#      core/db.py — لكن هذا يعني فقدان انتهاء الصلاحية التلقائي بعد 3600
#      ثانية (جلسة "اهمس" الآن تبقى مخزَّنة إلى أن تُحذف صراحة، بدل أن
#      تنتهي صلاحيتها تلقائياً بعد ساعة كما في الأصل). هذا تغيير سلوك فعلي
#      (ليس نص رسالة) يحتاج قراراً منك: إمّا إضافة setex حقيقية إلى
#      KVSqliteDB (إن كانت الحزمة تدعمها) أو قبول فقدان انتهاء الصلاحية.
#
# [B2] "مسح المحظورين" و"طرد <هدف>" (البندان 10 و14):
#      رسالة الصلاحية تقول "هذا الأمر يخص ( الادمن وفوق )" لكن الفحص الفعلي
#      المُستخدَم هو mod_pls (مدير) لا admin_pls (أدمن) — تناقض نصي/منطقي
#      محفوظ من الأصل حرفياً بين ما تقوله الرسالة وما يُطبَّق فعلياً.
#
# [B3] تسجيل core/dispatcher.py لهذه الأوامر يستخدم النص الأساسي مباشرة
#      (مثلاً "تقييد " بمسافة للصيغة ذات الهدف، و"تقييد" بلا مسافة لصيغة
#      الرد). دالة register() الحالية تُسجِّل مفتاحاً واحداً في القاموس
#      يُشير لكامل دالة الهاندلر (moderationHandler1) — تماماً كما تفعل كل
#      ملفات all_*.py السابقة (مفتاح واحد لكل ملف مثل "protection_commands").
#      طبّقتُ هنا تسجيلاً بعدد أكبر (مفتاح لكل نص أمر بالضبط) تلبيةً لطلبك
#      الصريح، لكن هذا يختلف عن نمط الملفات الأربعة السابقة. بما أن
#      core.dispatcher.dispatch() غير مُستدعاة فعلياً من أي مكان في التوجيه
#      الحالي (routing يتم عبر Client.on_message + سلسلة if فقط)، فهذا
#      التسجيل الإضافي فهرسة/مرجع بلا أثر وظيفي — أخبرني إن كنت تريد توحيد
#      الأسلوب مع الملفات السابقة (مفتاح واحد بدل عشرين).
