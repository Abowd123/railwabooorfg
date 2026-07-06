"""
all_features_toggle.py
منقول من bmqa/Plugins/all.py (guardCommands — سطر 2649 → 3058)
الفئة: تفعيل/تعطيل الميزات (تحذير، يوتيوب، ساوند، انستا، اهمس، تيك،
       شازام، ألعاب، ترجمة، تسلية، اشتراك إجباري) + أوامر الترجمة + ابلاغ

التحويلات المطبّقة:
  - r.get/set/delete         → await rdb.*
  - requests.get(...)        → aiohttp async (ClientSession)
  - ترجمه (7 طلبات متسلسلة)  → asyncio.gather (طلبات متوازية)
  - c.get_chat(username)      → await c.get_chat(username)
  - c.get_chat_members(...)   → async for mm in c.get_chat_members(...)
  - m.reply(...)              → await m.reply(...)
  - return False              → return

السلوكيات الغامضة موثّقة في قسم AMBIGUOUS آخر الملف.
"""

import logging
import asyncio

from aiohttp import ClientSession
from pyrogram import Client, ContinuePropagation, filters
from pyrogram.enums import ChatMembersFilter
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import Dev_Zaid
from core.db import rdb
from core.cache import members_cache
from core.errors import safe_handler
from core.dispatcher import register
from helpers.ranks import admin_pls, mod_pls, dev2_pls, isLockCommand


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
# دالة مساعدة: ترجمة نص عبر API (aiohttp)
# ══════════════════════════════════════════════════════════════════════════════

async def _translate(session: ClientSession, target: str, text: str) -> str:
    async with session.get(
        f"https://hozory.com/translate/?target={target}&text={text}"
    ) as resp:
        data = await resp.json(content_type=None)
    return data["result"]["translate"]


# ══════════════════════════════════════════════════════════════════════════════
# الهاندلر الرئيسي — group=28 (نفس الأصل)
# ══════════════════════════════════════════════════════════════════════════════

@register("features_toggle_commands")
@Client.on_message(filters.group & filters.text, group=28)
@safe_handler
async def featuresToggleHandler(c, m) -> None:
    """
    يعالج أوامر تفعيل/تعطيل الميزات + الترجمة + الإبلاغ.
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
    # 1. تعطيل التحذير                                   (all.py سطر 2649)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تعطيل التحذير":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if await rdb.get(f"{cid}:disableWarn:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} التحذير معطل من قبل\n☆"
            )
        await rdb.set(f"{cid}:disableWarn:{Dev_Zaid}", 1)
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر عطلت التحذير\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 2. تفعيل التحذير                                   (all.py سطر 2663)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تفعيل التحذير":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if not await rdb.get(f"{cid}:disableWarn:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} التحذير مفعل من قبل\n☆"
            )
        await rdb.delete(f"{cid}:disableWarn:{Dev_Zaid}")
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر فعلت التحذير\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 3. تعطيل اليوتيوب                                  (all.py سطر 2677)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تعطيل اليوتيوب":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if await rdb.get(f"{cid}:disableYT:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} اليوتيوب معطل من قبل\n☆"
            )
        await rdb.set(f"{cid}:disableYT:{Dev_Zaid}", 1)
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر عطلت اليوتيوب\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 4. تفعيل اليوتيوب                                  (all.py سطر 2691)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تفعيل اليوتيوب":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if not await rdb.get(f"{cid}:disableYT:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} اليوتيوب مفعل من قبل\n☆"
            )
        await rdb.delete(f"{cid}:disableYT:{Dev_Zaid}")
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر فعلت اليوتيوب\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 5. تعطيل الساوند                                   (all.py سطر 2705)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تعطيل الساوند":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if await rdb.get(f"{cid}:disableSound:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} الساوند معطل من قبل\n☆"
            )
        await rdb.set(f"{cid}:disableSound:{Dev_Zaid}", 1)
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر عطلت الساوند\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 6. تفعيل الساوند                                   (all.py سطر 2719)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تفعيل الساوند":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if not await rdb.get(f"{cid}:disableSound:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} الساوند مفعل من قبل\n☆"
            )
        await rdb.delete(f"{cid}:disableSound:{Dev_Zaid}")
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر فعلت الساوند\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 7. تعطيل الانستا                                   (all.py سطر 2733)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تعطيل الانستا":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if await rdb.get(f"{cid}:disableINSTA:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} الانستا معطل من قبل\n☆"
            )
        await rdb.set(f"{cid}:disableINSTA:{Dev_Zaid}", 1)
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر عطلت الانستا\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 8. تفعيل الانستا                                   (all.py سطر 2747)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تفعيل الانستا":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if not await rdb.get(f"{cid}:disableINSTA:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} الانستا مفعل من قبل\n☆"
            )
        await rdb.delete(f"{cid}:disableINSTA:{Dev_Zaid}")
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر فعلت الانستا\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 9. تعطيل اهمس                                      (all.py سطر 2761)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تعطيل اهمس":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if await rdb.get(f"{cid}:disableWHISPER:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} اهمس معطل من قبل\n☆"
            )
        await rdb.set(f"{cid}:disableWHISPER:{Dev_Zaid}", 1)
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر عطلت اهمس\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 10. تفعيل اهمس                                     (all.py سطر 2775)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تفعيل اهمس":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if not await rdb.get(f"{cid}:disableWHISPER:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} اهمس مفعل من قبل\n☆"
            )
        await rdb.delete(f"{cid}:disableWHISPER:{Dev_Zaid}")
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر فعلت اهمس\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 11. تعطيل التيك                                    (all.py سطر 2789)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تعطيل التيك":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if await rdb.get(f"{cid}:disableTik:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} التيك معطل من قبل\n☆"
            )
        await rdb.set(f"{cid}:disableTik:{Dev_Zaid}", 1)
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر عطلت التيك\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 12. تفعيل التيك                                    (all.py سطر 2803)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تفعيل التيك":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if not await rdb.get(f"{cid}:disableTik:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} التيك مفعل من قبل\n☆"
            )
        await rdb.delete(f"{cid}:disableTik:{Dev_Zaid}")
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر فعلت التيك\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 13. تعطيل شازام                                    (all.py سطر 2817)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تعطيل شازام":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if await rdb.get(f"{cid}:disableShazam:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} شازام معطل من قبل\n☆"
            )
        await rdb.set(f"{cid}:disableShazam:{Dev_Zaid}", 1)
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر عطلت شازام\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 14. تفعيل شازام                                    (all.py سطر 2831)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تفعيل شازام":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if not await rdb.get(f"{cid}:disableShazam:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} شازام مفعل من قبل\n☆"
            )
        await rdb.delete(f"{cid}:disableShazam:{Dev_Zaid}")
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر فعلت شازام\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 15. تعطيل الالعاب                                  (all.py سطر 2845)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تعطيل الالعاب":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if await rdb.get(f"{cid}:disableGames:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} الالعاب معطله من قبل\n☆"
            )
        await rdb.set(f"{cid}:disableGames:{Dev_Zaid}", 1)
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر عطلت الالعاب\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 16. تفعيل الالعاب                                  (all.py سطر 2859)
    # ══════════════════════════════════════════════════════════════════════
    if text == "تفعيل الالعاب":
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if not await rdb.get(f"{cid}:disableGames:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} الالعاب مفعله من قبل\n☆"
            )
        await rdb.delete(f"{cid}:disableGames:{Dev_Zaid}")
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر فعلت الالعاب\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 17. تعطيل الترجمة / تعطيل الترجمه                 (all.py سطر 2873)
    # ══════════════════════════════════════════════════════════════════════
    if text in ("تعطيل الترجمة", "تعطيل الترجمه"):
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if await rdb.get(f"{cid}:disableTrans:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} الترجمه معطله من قبل\n☆"
            )
        await rdb.set(f"{cid}:disableTrans:{Dev_Zaid}", 1)
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر عطلت الترجمه\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 18. تفعيل الترجمة / تفعيل الترجمه                 (all.py سطر 2887)
    # ══════════════════════════════════════════════════════════════════════
    if text in ("تفعيل الترجمة", "تفعيل الترجمه"):
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if not await rdb.get(f"{cid}:disableTrans:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} الترجمه مفعله من قبل\n☆"
            )
        await rdb.delete(f"{cid}:disableTrans:{Dev_Zaid}")
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر فعلت الترجمه\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 19. تعطيل التسلية / تعطيل التسليه                  (all.py سطر 2901)
    # ══════════════════════════════════════════════════════════════════════
    if text in ("تعطيل التسلية", "تعطيل التسليه"):
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if await rdb.get(f"{cid}:disableFun:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} التسلية معطله من قبل\n☆"
            )
        await rdb.set(f"{cid}:disableFun:{Dev_Zaid}", 1)
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر عطلت التسلية\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 20. تفعيل التسلية / تفعيل التسليه                  (all.py سطر 2915)
    # ══════════════════════════════════════════════════════════════════════
    if text in ("تفعيل التسلية", "تفعيل التسليه"):
        if not await mod_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if not await rdb.get(f"{cid}:disableFun:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} التسلية مفعله من قبل\n☆"
            )
        await rdb.delete(f"{cid}:disableFun:{Dev_Zaid}")
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر فعلت التسلية\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 21. تعطيل الاشتراك                                 (all.py سطر 2929)
    #     صلاحية: dev2_pls
    #     ⚠️ المفتاح بلا {cid} — عالمي لكل المجموعات [A1]
    # ══════════════════════════════════════════════════════════════════════
    if text == "تعطيل الاشتراك":
        if not await dev2_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المطور وفوق ) بس")
        if await rdb.get(f"disableSubscribe:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} الاشتراك الاجباري معطل من قبل\n☆"
            )
        await rdb.set(f"disableSubscribe:{Dev_Zaid}", 1)
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر عطلت الاشتراك الاجباري\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 22. قناة الاشتراك                                  (all.py سطر 2943)
    #     صلاحية: dev2_pls — يعرض القناة الحالية للاشتراك الإجباري
    # ══════════════════════════════════════════════════════════════════════
    if text == "قناة الاشتراك":
        if not await dev2_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المطور وفوق ) بس")
        ch = await rdb.get(f"forceChannel:{Dev_Zaid}") or "مافي قناة"
        return await m.reply(f"{k} قناة الاشتراك هي ( {ch} )")

    # ══════════════════════════════════════════════════════════════════════
    # 23. وضع قناة @<username>                            (all.py سطر 2949)
    #     صلاحية: dev2_pls — يتحقق من وجود القناة ثم يحفظها
    #     ⚠️ المفتاح عالمي بلا {cid} [A1]
    # ══════════════════════════════════════════════════════════════════════
    if text.startswith("وضع قناة @"):
        if not await dev2_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المطور وفوق ) بس")
        username = text.split("@")[1]
        try:
            await c.get_chat(username)
        except Exception as e:
            logging.exception(e)
            return await m.reply(f"{k} حدث خطأ")
        await rdb.set(f"forceChannel:{Dev_Zaid}", "@" + username)
        return await m.reply(f"{k} تم تعيين القناة بنجاح")

    # ══════════════════════════════════════════════════════════════════════
    # 24. تفعيل الاشتراك                                 (all.py سطر 2960)
    #     صلاحية: dev2_pls — عالمي [A1]
    # ══════════════════════════════════════════════════════════════════════
    if text == "تفعيل الاشتراك":
        if not await dev2_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المطور وفوق ) بس")
        if not await rdb.get(f"disableSubscribe:{Dev_Zaid}"):
            return await m.reply(
                f"{k} من「 {mention} 」\n{k} الاشتراك الاجباري مفعل من قبل\n☆"
            )
        await rdb.delete(f"disableSubscribe:{Dev_Zaid}")
        return await m.reply(
            f"{k} من「 {mention} 」\n{k} ابشر فعلت الاشتراك الاجباري\n☆"
        )

    # ══════════════════════════════════════════════════════════════════════
    # 25. /ar  (رد على رسالة — ترجمة للعربية)            (all.py سطر 2974)
    #     requests.get → aiohttp async
    # ══════════════════════════════════════════════════════════════════════
    if (
        text == "/ar"
        and m.reply_to_message
        and (m.reply_to_message.text or m.reply_to_message.caption)
    ):
        if not await rdb.get(f"{cid}:disableTrans:{Dev_Zaid}"):
            src = m.reply_to_message.text or m.reply_to_message.caption
            async with ClientSession() as session:
                translation = await _translate(session, "ar", src)
            return await m.reply(f"`{translation}`")

    # ══════════════════════════════════════════════════════════════════════
    # 26. /en  (رد على رسالة — ترجمة للإنجليزية)         (all.py سطر 2986)
    # ══════════════════════════════════════════════════════════════════════
    if (
        text == "/en"
        and m.reply_to_message
        and (m.reply_to_message.text or m.reply_to_message.caption)
    ):
        if not await rdb.get(f"{cid}:disableTrans:{Dev_Zaid}"):
            src = m.reply_to_message.text or m.reply_to_message.caption
            async with ClientSession() as session:
                translation = await _translate(session, "en", src)
            return await m.reply(f"`{translation}`")

    # ══════════════════════════════════════════════════════════════════════
    # 27. ترجمه  (رد على رسالة — ترجمة لـ 5 لغات)        (all.py سطر 2998)
    #     الأصل يُرسل 7 طلبات متتالية (en, ar, ru, zh, fr, nl, tr)
    #     en و ar مُجلَبان لكن لا يظهران في الرد [A2]
    #     asyncio.gather يُشغّل الـ 7 طلبات بالتوازي
    # ══════════════════════════════════════════════════════════════════════
    if (
        text == "ترجمه"
        and m.reply_to_message
        and (m.reply_to_message.text or m.reply_to_message.caption)
    ):
        if not await rdb.get(f"{cid}:disableTrans:{Dev_Zaid}"):
            src = m.reply_to_message.text or m.reply_to_message.caption
            async with ClientSession() as session:
                # الأصل يجلب en و ar أيضاً رغم عدم استخدامهما — محفوظ [A2]
                results = await asyncio.gather(
                    _translate(session, "en", src),   # [0] غير مُستخدم في الرد
                    _translate(session, "ar", src),   # [1] غير مُستخدم في الرد
                    _translate(session, "ru", src),   # [2]
                    _translate(session, "zh", src),   # [3]
                    _translate(session, "fr", src),   # [4]
                    _translate(session, "nl", src),   # [5] du في الأصل
                    _translate(session, "tr", src),   # [6]
                )
            _en, _ar, ru, zh, fr, du, tr = results
            txt = (
                f"🇷🇺 : \n {ru}\n\n"
                f"🇨🇳 : \n {zh}\n\n"
                f"🇫🇷 :\n {fr}\n\n"
                f"🇩🇪 :\n {du}\n\n"
                f"🇹🇷 : \n{tr}"
            )
            return await m.reply(txt)

    # ══════════════════════════════════════════════════════════════════════
    # 28. ترجمه <lang>  (رد على رسالة — ترجمة بلغة محددة) (all.py سطر 3029)
    #     startswith "ترجمه " مع رد على رسالة
    # ══════════════════════════════════════════════════════════════════════
    if (
        text.startswith("ترجمه ")
        and m.reply_to_message
        and (m.reply_to_message.text or m.reply_to_message.caption)
    ):
        if not await rdb.get(f"{cid}:disableTrans:{Dev_Zaid}"):
            lang = text.split()[1]
            src = m.reply_to_message.text or m.reply_to_message.caption
            async with ClientSession() as session:
                translation = await _translate(session, lang, src)
            return await m.reply(f"`{translation}`")

    # ══════════════════════════════════════════════════════════════════════
    # 29. ابلاغ  (رد على رسالة — منشن كل الإداريين)      (all.py سطر 3042)
    #     c.get_chat_members → members_cache.get_admins(...) (core/cache.py)
    #     ⚠️ لا يتحقق من صلاحية المُرسِل — أي عضو يستطيع الإبلاغ [A3]
    # ══════════════════════════════════════════════════════════════════════
    if text == "ابلاغ" and m.reply_to_message:
        reply_text = f"{k} تم ابلاغ المشرفين"
        cc = 0
        admins = await members_cache.get_admins(c, cid, ChatMembersFilter.ADMINISTRATORS)
        for mm in admins:
            if not mm.user.is_deleted and not mm.user.is_bot:
                cc += 1
                reply_text += f"[⁪⁬⁪⁬⁮⁪⁬⁪⁬⁮](tg://user?id={mm.user.id})"
        if cc == 0:
            return
        return await m.reply(
            reply_text,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⚠️", callback_data="delAdminMSG")]]
            ),
        )

    # لا يوجد أمر من الأوامر الـ29 أعلاه يطابق النص — لم يُرسَل أي رد فعلي
    # للمستخدم في هذا المسار، لذا نُمرِّر المعالجة لبقية handlers group=28
    # (راجع [C4] في all_moderation_2.py لشرح المشكلة الأصلية). هذا الملف هو
    # أول ملف مُسجَّل أبجدياً بنفس group=28، فهو السبب الأصلي في أن بقية
    # الملفات السبعة لم تكن تُنفَّذ فعلياً قبل هذا الإصلاح.
    raise ContinuePropagation()


# ══════════════════════════════════════════════════════════════════════════════
# AMBIGUOUS — سلوكيات غامضة تحتاج مراجعة
# ══════════════════════════════════════════════════════════════════════════════
#
# [A1] مفاتيح "الاشتراك الإجباري" و"وضع قناة" — عالمية بلا {cid}:
#      disableSubscribe:{Dev_Zaid}   (لا يحتوي على chat_id)
#      forceChannel:{Dev_Zaid}       (لا يحتوي على chat_id)
#      هذا يعني أن تفعيل/تعطيل الاشتراك الإجباري يؤثر على كل المجموعات
#      التي يعمل فيها البوت في آنٍ واحد. محفوظ كما في الأصل.
#
# [A2] أمر "ترجمه" — en و ar مُجلَبان لكن غير مُستخدمَين في الرد:
#      الأصل يحسب en و ar (سطر 3005-3009) ثم لا يضعهما في txt (سطر 3026).
#      محفوظ كما هو. لو أردت إزالة طلبَي en و ar وفر رحلتَي شبكة.
#
# [A3] أمر "ابلاغ" — لا يتحقق من صلاحية المُرسِل:
#      في الأصل أي عضو (حتى رتبة 0) يستطيع إرسال "ابلاغ" والإبلاغ للإداريين.
#      محفوظ. لو أردت تقييده لـ admin_pls أو mod_pls أضف الشرط صريحاً.
#
# [A4] أوامر الترجمة (/ar، /en، ترجمه) لا تتحقق من صلاحية المُرسِل:
#      الوحيد الذي يتحقق منه هو تعطيل الترجمة (disableTrans).
#      هذا يسمح لأي عضو باستخدام الترجمة. محفوظ كما هو.
#
# [A5] وضع قناة @<username>:
#      text.split("@")[1] يأخذ كل ما بعد أول @ في النص.
#      لو كانت الرسالة "وضع قناة @ch1 @ch2" فسيُعيَّن "ch1 @ch2" كمعرّف.
#      الأصل لا يتحقق من هذا — محفوظ.
