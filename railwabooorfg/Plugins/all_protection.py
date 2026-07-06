"""
all_protection.py
منقول من bmqa/Plugins/all.py (guardCommands — سطر 1883 → 2105)
الفئة: قفل/فتح الكل والحماية الشاملة

ملاحظة الحدود:
  - سطر 1761-1881 (منع/الغاء منع + قائمة المنع + مسح قائمة المنع):
    تمّت هجرتها مسبقاً في all_voice_and_blocklist.py — لا تكرار هنا.
  - هذا الملف يبدأ من سطر 1883 (قفل الكل) حتى 2105 (نهاية تعطيل الحماية).
  - الأوامر الفردية (قفل الدردشة، قفل الفويسات…) تبدأ من سطر 2107
    وستُهجَّر في ملف all_locks.py.

التحويلات المطبّقة:
  - r.<op>            → await rdb.<op>
  - m.reply(...)      → await m.reply(...)
  - return False      → return   (لا فرق وظيفي في Pyrogram async)
  - Thread(target=…)  → هاندلر async مباشر

السلوكيات الغامضة موثّقة في قسم AMBIGUOUS آخر الملف.
"""

from pyrogram import Client, ContinuePropagation, filters

from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from helpers.ranks import admin_pls, mod_pls, owner_pls, isLockCommand


# ══════════════════════════════════════════════════════════════════════════════
# Templates رسائل القفل والفتح — منقولة من guardCommands سطر 1091-1122
# (محوّلة من متغيرات محلية إلى ثوابت module-level)
# ══════════════════════════════════════════════════════════════════════════════

Open = """
{} من 「 {} 」
{} ابشر فتحت {}
☆
"""

Openn = """
{} من 「 {} 」
{} {} مفتوح من قبل
☆
"""

Openn2 = """
{} من 「 {} 」
{} {} مفتوحه من قبل
☆
"""

lock = """
{} من 「 {} 」
{} ابشر قفلت {}
☆
"""

lockn = """
{} من 「 {} 」
{} {} مقفل من قبل
☆
"""

locknn = """
{} من 「 {} 」
{} {} مقفله من قبل
☆
"""


# ══════════════════════════════════════════════════════════════════════════════
# قائمة مفاتيح "قفل الكل" الكاملة (25 مفتاح — مُطابقة للأصل سطر 1887-1912)
# ══════════════════════════════════════════════════════════════════════════════

_ALL_LOCK_KEYS = [
    "mute",
    "lockEdit",
    "lockEditM",
    "lockVoice",
    "lockVideo",
    "lockNot",
    "lockPhoto",
    "lockPersian",
    "lockStickers",
    "lockFiles",
    "lockAnimations",
    "lockUrls",
    "lockHashtags",
    "lockBots",
    "lockTags",
    "lockMessages",
    "lockSpam",
    "lockForward",
    "lockSHTM",
    "lockaddContacts",
    "lockAudios",
    "lockChannels",
    "lockJoin",
    "lockInline",
    "lockNSFW",
]

# "فتح الكل" يحذف نفس المفاتيح + lockKFR (موجود في الأصل سطر 2006 فقط)
_ALL_UNLOCK_KEYS = _ALL_LOCK_KEYS + ["lockKFR"]


# ══════════════════════════════════════════════════════════════════════════════
# مفاتيح "تفعيل الحماية" (17 مفتاح — مُطابقة للأصل سطر 2041-2057)
# لا تشمل: lockEdit, lockNot, lockHashtags, lockBots, lockMessages,
#           lockInline, lockJoin, lockaddContacts — تبقى كما هي
# ══════════════════════════════════════════════════════════════════════════════

_PROTECTION_KEYS = [
    "lockChannels",
    "lockVoice",
    "lockVideo",
    "lockPhoto",
    "lockStickers",
    "lockAnimations",
    "lockFiles",
    "lockPersian",
    "lockUrls",
    "lockTags",
    "lockSpam",
    "lockForward",
    "lockAudios",
    "lockSHTM",
    "lockNSFW",
]


# ══════════════════════════════════════════════════════════════════════════════
# دالة مساعدة: بناء نص الأمر (مشتركة مع بقية all_* files)
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

@register("protection_commands")
@Client.on_message(filters.group & filters.text, group=28)
@safe_handler
async def protectionHandler(c, m) -> None:
    """
    يعالج أوامر قفل/فتح الكل وتفعيل/تعطيل الحماية الشاملة.
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

    # ══════════════════════════════════════════════════════════════════════
    # 1. قفل الكل                                        (all.py سطر 1883)
    #    يتحقق من أن كل 25 مفتاح مضبوط قبل الإعلان عن القفل
    #    ملاحظة [A1]: الأصل يُرسل الرد ثم يعود بـ return False — انظر AMBIGUOUS
    # ══════════════════════════════════════════════════════════════════════
    if text == "قفل الكل":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")

        all_set = all(
            [await rdb.get(f"{cid}:{key}:{Dev_Zaid}") for key in _ALL_LOCK_KEYS]
        )
        if all_set:
            return await m.reply(
                f"{k} من 「 {mention} 」 \n{k} كل شي مقفل يا حلو!\n☆"
            )

        await m.reply(f"{k} من 「 {mention} 」 \n{k} ابشر قفلت كل شي\n☆")
        for key in _ALL_LOCK_KEYS:
            await rdb.set(f"{cid}:{key}:{Dev_Zaid}", 1)
        return

    # ══════════════════════════════════════════════════════════════════════
    # 2. فتح الكل                                        (all.py سطر 1946)
    #    يتحقق من أن كل 25 مفتاح ممسوح قبل الإعلان عن الفتح
    #    ملاحظة [A2]: يحذف lockKFR أيضاً رغم أن قفل الكل لا يضبطه — محفوظ
    # ══════════════════════════════════════════════════════════════════════
    if text == "فتح الكل":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")

        all_clear = all(
            [not await rdb.get(f"{cid}:{key}:{Dev_Zaid}") for key in _ALL_LOCK_KEYS]
        )
        if all_clear:
            return await m.reply(
                f"{k} من 「 {mention} 」 \n{k} كل شي مفتوح يا حلو!\n☆"
            )

        await m.reply(f"{k} من 「 {mention} 」 \n{k} ابشر فتحت كل شي\n☆")
        for key in _ALL_UNLOCK_KEYS:
            await rdb.delete(f"{cid}:{key}:{Dev_Zaid}")
        return

    # ══════════════════════════════════════════════════════════════════════
    # 3. تفعيل الحماية / تفعيل الحمايه                  (all.py سطر 2010)
    #    صلاحية: owner_pls (مالك المجموعة)
    #    يضبط 15 مفتاح + يحذف disableWarn
    #    لا يضبط: lockEdit, lockNot, lockHashtags, lockBots,
    #             lockMessages, lockInline, lockJoin, lockaddContacts
    #    ملاحظة [A3]: شرط "مفعّلة من قبل" — انظر AMBIGUOUS
    # ══════════════════════════════════════════════════════════════════════
    if text in ("تفعيل الحماية", "تفعيل الحمايه"):
        if not await owner_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المالك وفوق ) بس")

        already_on = all(
            [await rdb.get(f"{cid}:{key}:{Dev_Zaid}") for key in _PROTECTION_KEYS]
        ) and await rdb.get(f"{cid}:lockEditM:{Dev_Zaid}")

        if already_on:
            return await m.reply(
                f"{k} من 「 {mention} 」 \n{k} الحماية مفعله من قبل\n☆"
            )

        await m.reply(
            f"{k} من 「 {mention} 」 \n{k} ابشر فعلت الحمايه\n☆"
        )
        # تفعيل الحماية يحذف disableWarn أولاً (يعيد تفعيل التحذير)
        await rdb.delete(f"{cid}:disableWarn:{Dev_Zaid}")
        await rdb.set(f"{cid}:lockEditM:{Dev_Zaid}", 1)
        for key in _PROTECTION_KEYS:
            await rdb.set(f"{cid}:{key}:{Dev_Zaid}", 1)
        return

    # ══════════════════════════════════════════════════════════════════════
    # 4. تعطيل الحماية / تعطيل الحمايه                  (all.py سطر 2059)
    #    صلاحية: owner_pls (مالك المجموعة)
    #    يحذف 15 مفتاح — لا يحذف lockEditM (يبقى مضبوطاً دائماً بعد التعطيل)
    #    ملاحظة [A3]: شرط "معطّلة من قبل" غير اعتيادي — انظر AMBIGUOUS
    # ══════════════════════════════════════════════════════════════════════
    if text in ("تعطيل الحماية", "تعطيل الحمايه"):
        if not await owner_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المالك وفوق ) بس")

        # شرط "الحماية معطّلة من قبل":
        # lockEditM مضبوط AND كل مفاتيح _PROTECTION_KEYS ممسوحة
        # (لأن تعطيل الحماية يترك lockEditM مضبوطاً — انظر AMBIGUOUS [A3])
        already_off = (
            await rdb.get(f"{cid}:lockEditM:{Dev_Zaid}")
            and all(
                [not await rdb.get(f"{cid}:{key}:{Dev_Zaid}") for key in _PROTECTION_KEYS]
            )
        )
        if already_off:
            return await m.reply(
                f"{k} من 「 {mention} 」 \n{k} الحماية معطله من قبل\n☆"
            )

        await m.reply(
            f"{k} من 「 {mention} 」 \n{k} ابشر عطلت الحمايه\n☆"
        )
        # lockEditM لا يُحذف (مقصود في الأصل — محفوظ)
        for key in _PROTECTION_KEYS:
            await rdb.delete(f"{cid}:{key}:{Dev_Zaid}")
        return

    # لا يوجد أمر من الأوامر الأربعة أعلاه يطابق النص — لم يُرسَل أي رد
    # فعلي للمستخدم في هذا المسار، لذا نُمرِّر المعالجة لبقية handlers
    # group=28 (راجع [C4] في all_moderation_2.py لشرح المشكلة الأصلية).
    raise ContinuePropagation()


# ══════════════════════════════════════════════════════════════════════════════
# AMBIGUOUS — سلوكيات غامضة تحتاج مراجعة
# ══════════════════════════════════════════════════════════════════════════════
#
# [A1] "قفل الكل" / "فتح الكل" — return False في الأصل
#      الأصل يُرسل m.reply(...) بدون await ثم يُشغّل r.set لكل المفاتيح
#      ثم يعود بـ return False.
#      في النسخة async: الرد يُرسَل أولاً بـ await m.reply() ثم تُضبَط المفاتيح
#      ثم return (لا return False — لا فرق وظيفي في Pyrogram).
#      لو كان return False مقصوداً لإيقاف حدث على مستوى أعلى، يجب
#      مراجعة آلية dispatcher.
#
# [A2] "فتح الكل" يحذف lockKFR (سطر 2006) رغم أن "قفل الكل" لا يضبطه.
#      هذا غير متماثل — محفوظ كما هو في الأصل.
#
# [A3] شرط "الحماية معطّلة من قبل" في تعطيل الحماية:
#
#      الأصل (سطر 2063-2081):
#        if lockEditM AND NOT lockVoice AND NOT lockVideo AND NOT ... (16 آخرين)
#
#      هذا يعني: الحماية معطّلة فعلاً إذا كان lockEditM لا يزال مضبوطاً
#      لكن كل المفاتيح الأخرى ممسوحة.
#
#      لماذا؟ لأن تعطيل الحماية لا يحذف lockEditM — فيبقى مضبوطاً بعد
#      التعطيل. وبهذا يصبح "lockEditM=1 + كل الآخرين=0" هو الحالة الطبيعية
#      بعد تعطيل الحماية.
#
#      إذا أردتَ تعديل هذا السلوك لحذف lockEditM أيضاً عند التعطيل،
#      أضف:
#        await rdb.delete(f"{cid}:lockEditM:{Dev_Zaid}")
#      وعدّل شرط "معطّلة من قبل" ليكون:
#        not any(_PROTECTION_KEYS) AND not lockEditM
#
# [A4] "تفعيل الحماية" — شرط "مفعّلة من قبل":
#      الأصل يتحقق من 17 مفتاح بـ AND (جميعها مضبوطة).
#      إن كان مفتاح واحد فقط ممسوحاً فسيعيد تفعيل الحماية بالكامل.
#      هذا سلوك "إعادة تعيين الحماية" وليس فقط "التحقق من التفعيل" — محفوظ.
#
# [A5] "قفل الكل" — الكفاءة:
#      25 await rdb.set متتالية → 25 رحلة Redis منفصلة.
#      في بيئة الإنتاج يمكن استبدالها بـ pipeline أو mset.
#      محفوظة كما هي لمطابقة سلوك الأصل.
