"""
all_helpers.py
منقول من bmqa/Plugins/all.py → bmqa-v2/Plugins/all_helpers.py

التحويلات المطبّقة:
  - r.<op>                   → await rdb.<op>             (core.db)
  - Thread(target=f, args=x) → await f(*x)
  - time.sleep(n)            → await asyncio.sleep(n)
  - كل دالة sync تلمس Redis  → async def
  - m.delete() / m.reply()   → await m.delete() / await m.reply()
  - c.ban_chat_member(...)   → await c.ban_chat_member(...)
  - دوال نقية (Find, get_for_verify) → تبقى sync لأنها لا تلمس I/O
"""

import re
import os
import random
import asyncio

from aiohttp import ClientSession
from Python_ARQ import ARQ
from pyrogram import Client, filters
from pyrogram.types import (
    ChatPermissions,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from helpers.ranks import admin_pls, pre_pls, isLockCommand
from helpers.persianData import persianInformation

ARQ_API_KEY = "OZJRWV-SAURXD-PMBUKF-GMVSNS-ARQ"
ARQ_API_URL = "https://arq.hamker.dev"


# ══════════════════════════════════════════════════════════════════════════════
# 0.  resolve_guard_text                         (all.py سطر 1062-1090، guardCommands)
#     مُضافة حديثاً لتوحيد بوابة الأهلية + تطبيع النص التي كانت (ولا تزال في
#     all_settings.py / all_voice_and_blocklist.py / all_protection.py /
#     all_features_toggle.py) مُكرَّرة محلياً باسم "_resolve_text" + كتلة فحوص
#     منفصلة في كل ملف. أي ملف جديد يُقتطع من guardCommands (كـ
#     all_moderation_1.py) يجب أن يستورد هذه الدالة بدل تكرار نفس الكتلة.
#     — لم تُعدَّل الملفات الأربعة القديمة هنا تفادياً لأي أثر جانبي غير مطلوب.
# ══════════════════════════════════════════════════════════════════════════════

async def resolve_guard_text(m):
    """يُطبّق فحوصات الأهلية القياسية لأول guardCommands (كتم/تعديل قيد
    التنفيذ) ثم يُعيد نص الأمر بعد تطبيق اسم البوت المخصص والأوامر المخصصة
    (Custom)، أو يُعيد None إذا وجب تجاهل الرسالة بالكامل (نفس الأصل
    سطراً بسطر، بما فيه فحص isLockCommand في النهاية).
    """
    if not await rdb.get(f"{m.chat.id}:enable:{Dev_Zaid}"):
        return None
    if await rdb.get(f"{m.chat.id}:mute:{Dev_Zaid}") and not await admin_pls(
        m.from_user.id, m.chat.id
    ):
        return None
    if await rdb.get(f"{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}"):
        return None
    if await rdb.get(f"{m.from_user.id}:mute:{Dev_Zaid}"):
        return None
    if await rdb.get(f"{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}"):
        return None
    if await rdb.get(f"{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}"):
        return None
    if await rdb.get(f"{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}") or await rdb.get(
        f"{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}"
    ):
        return None
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
    if await isLockCommand(m.from_user.id, m.chat.id, text):
        return None
    return text


# ══════════════════════════════════════════════════════════════════════════════
# 1.  Find                                       (all.py سطر 150)
#     دالة نقية — regex فقط، لا Redis — تبقى sync
# ══════════════════════════════════════════════════════════════════════════════

def Find(text: str) -> list:
    """تستخرج كل الروابط من نص عادي. لا تستدعي أي I/O."""
    pattern = (
        r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)"
        r"(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+"
        r"(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s!()\[\]{};:'\".,<>?«»\u201c\u201d\u2018\u2019]))"
    )
    return [x[0] for x in re.findall(pattern, text)]


# ══════════════════════════════════════════════════════════════════════════════
# 2.  get_for_verify                             (all.py سطر 772)
#     دالة نقية — تبني قائمة أسئلة ثم تختار عشوائياً، لا Redis
# ══════════════════════════════════════════════════════════════════════════════

def get_for_verify(me) -> dict:
    """تُعيد سؤالاً عشوائياً مع لوحة أزرار للتحقق من أن المستخدم حقيقي."""
    for_verify = [
        {
            "question": "ماهو الحيوان الذي ينتهي اسمه بحرف الباء ؟",
            "key": InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("فأر",         callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("وشق",         callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("بشار الأسد",  callback_data=f"no:{me.id}"),
                ],
                [
                    InlineKeyboardButton("حمار",        callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("كلب",         callback_data=f"yes:{me.id}"),
                    InlineKeyboardButton("قطة",         callback_data=f"no:{me.id}"),
                ],
            ]),
        },
        {
            "question": "ماهي عاصمة فرنسا؟",
            "key": InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("دمشق",        callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("الرياض",      callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("باريس",       callback_data=f"yes:{me.id}"),
                ],
                [
                    InlineKeyboardButton("الكويت",      callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("القاهرة",     callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("ماشا والدب",  callback_data=f"no:{me.id}"),
                ],
            ]),
        },
        {
            "question": "نادي يبدأ بحرف الباء :",
            "key": InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("برشلونا",     callback_data=f"yes:{me.id}"),
                    InlineKeyboardButton("الهلال",      callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("النصر",       callback_data=f"no:{me.id}"),
                ],
                [
                    InlineKeyboardButton("الزمالك",     callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("ريال مدريد",  callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("مانشستر",     callback_data=f"no:{me.id}"),
                ],
            ]),
        },
        {
            "question": "دولة يبدأ اسمها بحرف التاء :",
            "key": InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("قطر",         callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("امريكا",      callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("سوريا",       callback_data=f"no:{me.id}"),
                ],
                [
                    InlineKeyboardButton("مصر",         callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("الصين",       callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("تركيا",       callback_data=f"yes:{me.id}"),
                ],
            ]),
        },
        {
            "question": "اختر هذا الايموجي - 🤑 -",
            "key": InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🍭", callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("🤑", callback_data=f"yes:{me.id}"),
                    InlineKeyboardButton("🏆", callback_data=f"no:{me.id}"),
                ],
                [
                    InlineKeyboardButton("🌀", callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("🪨", callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("💎", callback_data=f"no:{me.id}"),
                ],
            ]),
        },
        {
            "question": "اختر هذا الايموجي - 🔓 -",
            "key": InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🏆", callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("💎", callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("🙄", callback_data=f"no:{me.id}"),
                ],
                [
                    InlineKeyboardButton("💸", callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("💣", callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("🔓", callback_data=f"yes:{me.id}"),
                ],
            ]),
        },
        {
            "question": "اختر هذا الايموجي - 🌠 -",
            "key": InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("☄️",    callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("🙈",    callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("🦄",    callback_data=f"no:{me.id}"),
                ],
                [
                    InlineKeyboardButton("🌠",    callback_data=f"yes:{me.id}"),
                    InlineKeyboardButton("🌈",    callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("🧑‍💻",   callback_data=f"no:{me.id}"),
                ],
            ]),
        },
        {
            "question": "ماهي عاصمة سوريا",
            "key": InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("دمشق",       callback_data=f"yes:{me.id}"),
                    InlineKeyboardButton("دير الزور",  callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("ادلب",       callback_data=f"no:{me.id}"),
                ],
                [
                    InlineKeyboardButton("ليو ميسي",   callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("الرياض",     callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("مزة فيلات",  callback_data=f"no:{me.id}"),
                ],
            ]),
        },
        {
            "question": "ماهي عملة الولايات المتحدة الأمريكية",
            "key": InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("الروبية",    callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("الجنيه",     callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("الليرة",     callback_data=f"no:{me.id}"),
                ],
                [
                    InlineKeyboardButton("الدولار",    callback_data=f"yes:{me.id}"),
                    InlineKeyboardButton("الدينار",    callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("الين",       callback_data=f"no:{me.id}"),
                ],
            ]),
        },
        {
            "question": "اسم مذكر يبدأ بحرف ز",
            "key": InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("زيد",        callback_data=f"yes:{me.id}"),
                    InlineKeyboardButton("علي",        callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("محمد",       callback_data=f"no:{me.id}"),
                ],
                [
                    InlineKeyboardButton("عمر",        callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("المريخ",     callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("احمد",       callback_data=f"no:{me.id}"),
                ],
            ]),
        },
        {
            "question": "اسم مؤنث ينتهي بحرف ي",
            "key": InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("لورين",      callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("ماجدة",      callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("علياء",      callback_data=f"no:{me.id}"),
                ],
                [
                    InlineKeyboardButton("أماني",      callback_data=f"yes:{me.id}"),
                    InlineKeyboardButton("فرح",        callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("أمل",        callback_data=f"no:{me.id}"),
                ],
            ]),
        },
        {
            "question": "اسم مؤنث يبدأ بحرف أ",
            "key": InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("لورين",      callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("ماجدة",      callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("علياء",      callback_data=f"no:{me.id}"),
                ],
                [
                    InlineKeyboardButton("أمل",        callback_data=f"yes:{me.id}"),
                    InlineKeyboardButton("فرح",        callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("يمنى",       callback_data=f"no:{me.id}"),
                ],
            ]),
        },
        {
            "question": "الأسبوع كم يوم؟",
            "key": InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("1", callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("2", callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("3", callback_data=f"no:{me.id}"),
                ],
                [
                    InlineKeyboardButton("4", callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("5", callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("6", callback_data=f"no:{me.id}"),
                ],
                [
                    InlineKeyboardButton("7", callback_data=f"yes:{me.id}"),
                    InlineKeyboardButton("8", callback_data=f"no:{me.id}"),
                    InlineKeyboardButton("9", callback_data=f"no:{me.id}"),
                ],
            ]),
        },
    ]
    return random.choice(for_verify)


# ══════════════════════════════════════════════════════════════════════════════
# 3.  scan4                                      (all.py سطر 757)
#     كانت async تستخدم r.get → حُوِّلت إلى await rdb.get
# ══════════════════════════════════════════════════════════════════════════════

async def scan4(c, m, media_id: str, file: str) -> None:
    """تفحص ملفاً بـ ARQ NSFW API وتحذف الرسالة إن كانت إباحية."""
    session = ClientSession()
    try:
        arq = ARQ(ARQ_API_URL, ARQ_API_KEY, session)
        resp = await arq.nsfw_scan(file=file)
        if resp.result.is_nsfw:
            await m.delete()
            k = await rdb.get(f"{Dev_Zaid}:botkey")
            await m.reply(
                f"{k} 「 {m.from_user.mention} 」\n"
                f"حذفت رسالتك لاحتوائها على محتوى إباحي\n☆"
            )
    finally:
        os.remove(file)
        await session.close()


# ══════════════════════════════════════════════════════════════════════════════
# 4.  scanR                                      (all.py سطر 753)
#     كانت sync تستدعي RUN(scan4(...))
#     → أصبحت async تستدعي await scan4(...) مباشرة
# ══════════════════════════════════════════════════════════════════════════════

async def scanR(c, m, media_id: str, file: str) -> None:
    """غلاف async لـ scan4 — يحلّ محلّ Thread(target=scanR, ...) في الهاندلر."""
    await scan4(c, m, media_id, file)


# ══════════════════════════════════════════════════════════════════════════════
# 5.  guardResponseFunction2                     (all.py سطر 284)
#     sync → async  |  r.get/r.set → await rdb.get/rdb.set
# ══════════════════════════════════════════════════════════════════════════════

async def guardResponseFunction2(c, m, k: str, channel: str) -> None:
    """معالج رسائل المجموعة المُعدَّلة — يطبّق قفلَي التعديل وتعديل الميديا."""
    if not await rdb.get(f"{m.chat.id}:enable:{Dev_Zaid}"):
        return

    warner = "{} 「 {} 」 ممنوع {}\n☆\n"

    if m.sender_chat:
        uid = m.sender_chat.id
        mention = f"[{m.sender_chat.title}](t.me/{channel})"
    elif m.from_user:
        uid = m.from_user.id
        mention = m.from_user.mention
    else:
        return

    if (
        await rdb.get(f"{m.chat.id}:lockEdit:{Dev_Zaid}")
        and m.text
        and not await pre_pls(uid, m.chat.id)
    ):
        await m.delete()
        if not await rdb.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not await rdb.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            await rdb.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return await m.reply(
                warner.format(k, mention, "التعديل"), disable_web_page_preview=True
            )

    if (
        await rdb.get(f"{m.chat.id}:lockEditM:{Dev_Zaid}")
        and m.media
        and not await pre_pls(uid, m.chat.id)
    ):
        await m.delete()
        if not await rdb.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not await rdb.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            await rdb.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return await m.reply(
                warner.format(k, mention, "تعديل الميديا"), disable_web_page_preview=True
            )


# ══════════════════════════════════════════════════════════════════════════════
# 6.  guardResponseFunction                      (all.py سطر 335)
#     sync → async  |  r.* → await rdb.*
#     يحتوي منطق كل أقفال المجموعة (mute, spam, nsfw, persian … إلخ)
# ══════════════════════════════════════════════════════════════════════════════

async def guardResponseFunction(c, m, k: str, channel: str) -> None:
    """المعالج الرئيسي لأقفال المجموعة — يُستدعى من guardLocksResponse."""
    if not await rdb.get(f"{m.chat.id}:enable:{Dev_Zaid}"):
        return

    warner = "{} 「 {} 」 ممنوع {}\n☆\n"

    # ── تحديد هوية المُرسِل ────────────────────────────────────────────────
    if m.sender_chat:
        uid = m.sender_chat.id
        mention = f"[{m.sender_chat.title}](t.me/{channel})"
    elif m.from_user:
        uid = m.from_user.id
        mention = m.from_user.mention
    else:
        uid = None
        mention = "مجهول"

    # ── قفل الإشعارات (service messages) ─────────────────────────────────
    if await rdb.get(f"{m.chat.id}:lockNot:{Dev_Zaid}") and m.service:
        await m.delete()

    # ── قفل إضافة جهات الاتصال ────────────────────────────────────────────
    if (
        await rdb.get(f"{m.chat.id}:lockaddContacts:{Dev_Zaid}")
        and m.from_user
        and m.new_chat_members
    ):
        if await pre_pls(m.from_user.id, m.chat.id):
            return
        for me in m.new_chat_members:
            if not me.id == m.from_user.id:
                mention = m.from_user.mention
                await m.chat.ban_member(me.id)
                await m.delete()
                if not await rdb.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}"):
                    return await m.reply(
                        warner.format(k, mention, "تضيف حد هنا"),
                        disable_web_page_preview=True,
                    )

    # ── قفل الوسائط بالـ file_id ──────────────────────────────────────────
    if m.media:
        file_id = None
        if m.sticker:   file_id = m.sticker.file_id
        if m.animation: file_id = m.animation.file_id
        if m.photo:     file_id = m.photo.file_id
        if m.video:     file_id = m.video.file_id
        if m.voice:     file_id = m.voice.file_id
        if m.audio:     file_id = m.audio.file_id
        if m.document:  file_id = m.document.file_id
        if file_id:
            idd = file_id[-6:]
            if await rdb.get(f"{idd}:NotAllow:{m.chat.id}{Dev_Zaid}"):
                if not await admin_pls(uid, m.chat.id):
                    return await m.delete()

    # ── قائمة الكلمات الممنوعة ────────────────────────────────────────────
    if m.text and await rdb.smembers(f"{m.chat.id}:NotAllowedListText:{Dev_Zaid}"):
        if not await admin_pls(uid, m.chat.id):
            for word in await rdb.smembers(f"{m.chat.id}:NotAllowedListText:{Dev_Zaid}"):
                if word in m.text:
                    return await m.delete()

    # ── كتم الشخصي والعام ────────────────────────────────────────────────
    if await rdb.get(f"{uid}:mute:{m.chat.id}{Dev_Zaid}") or await rdb.get(f"{uid}:mute:{Dev_Zaid}"):
        return

    if await rdb.get(f"{m.chat.id}:mute:{Dev_Zaid}") and not await admin_pls(uid, m.chat.id):
        await m.delete()
        return

    if await pre_pls(uid, m.chat.id):
        return

    # ── قفل البوتات ───────────────────────────────────────────────────────
    if await rdb.get(f"{m.chat.id}:lockBots:{Dev_Zaid}") and m.new_chat_members:
        for mem in m.new_chat_members:
            if mem.is_bot:
                return await m.chat.ban_member(mem.id)

    # ── قفل الانضمام ──────────────────────────────────────────────────────
    if await rdb.get(f"{m.chat.id}:lockJoin:{Dev_Zaid}") and m.new_chat_members:
        for mem in m.new_chat_members:
            if not await admin_pls(mem.id, m.chat.id):
                await m.chat.ban_member(mem.id)
                await m.chat.unban_member(mem.id)
                return

    # ── قفل القنوات ───────────────────────────────────────────────────────
    if await rdb.get(f"{m.chat.id}:lockChannels:{Dev_Zaid}") and m.sender_chat:
        if m.sender_chat.id != m.chat.id:
            await m.chat.ban_member(m.sender_chat.id)
            return

    # ── قفل السبام ────────────────────────────────────────────────────────
    if await rdb.get(f"{m.chat.id}:lockSpam:{Dev_Zaid}"):
        spam_key = f"{uid}in_spam:{m.chat.id}{Dev_Zaid}"
        current = await rdb.get(spam_key)
        if not current:
            await rdb.set(spam_key, 1, ex=10)
        else:
            count = int(current)
            if count == 10:
                if m.from_user:
                    await rdb.set(f"{uid}:mute:{m.chat.id}{Dev_Zaid}", 1)
                    await rdb.sadd(f"{m.chat.id}:listMUTE:{Dev_Zaid}", uid)
                    await rdb.delete(spam_key)
                    return await m.reply(
                        f"{k} 「 {mention} 」 كتمتك يالبثر عشان تتعلم تكرر\n☆"
                    )
                if m.sender_chat:
                    await m.chat.ban_member(m.sender_chat.id)
                    return await m.reply(
                        f"{k} 「 {mention} 」 حظرتك يالبثر عشان تتعلم تكرر\n☆"
                    )
            else:
                await rdb.set(spam_key, count + 1, ex=10)

    # ── قفل الانلاين ──────────────────────────────────────────────────────
    if await rdb.get(f"{m.chat.id}:lockInline:{Dev_Zaid}") and m.via_bot:
        await m.delete()
        if not await rdb.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not await rdb.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            await rdb.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return await m.reply(
                warner.format(k, mention, "ترسل انلاين"), disable_web_page_preview=True
            )

    # ── قفل التوجيه ───────────────────────────────────────────────────────
    if await rdb.get(f"{m.chat.id}:lockForward:{Dev_Zaid}") and m.forward_date:
        await m.delete()
        if not await rdb.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not await rdb.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            await rdb.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return await m.reply(
                warner.format(k, mention, "ترسل توجيه"), disable_web_page_preview=True
            )

    # ── قفل الصوت ─────────────────────────────────────────────────────────
    if await rdb.get(f"{m.chat.id}:lockAudios:{Dev_Zaid}") and m.audio:
        await m.delete()
        if not await rdb.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not await rdb.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            await rdb.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return await m.reply(
                warner.format(k, mention, "ترسل صوت"), disable_web_page_preview=True
            )

    # ── قفل الفيديو ───────────────────────────────────────────────────────
    if await rdb.get(f"{m.chat.id}:lockVideo:{Dev_Zaid}") and m.video:
        await m.delete()
        if not await rdb.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not await rdb.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            await rdb.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return await m.reply(
                warner.format(k, mention, "ترسل فيديوهات"), disable_web_page_preview=True
            )

    # ── قفل الصور ─────────────────────────────────────────────────────────
    if await rdb.get(f"{m.chat.id}:lockPhoto:{Dev_Zaid}") and m.photo:
        await m.delete()
        if not await rdb.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not await rdb.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            await rdb.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return await m.reply(
                warner.format(k, mention, "ترسل صور"), disable_web_page_preview=True
            )

    # ── قفل الملصقات ──────────────────────────────────────────────────────
    if await rdb.get(f"{m.chat.id}:lockStickers:{Dev_Zaid}") and m.sticker:
        await m.delete()
        if not await rdb.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not await rdb.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            await rdb.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return await m.reply(
                warner.format(k, mention, "ترسل ملصقات"), disable_web_page_preview=True
            )

    # ── قفل المتحركات ─────────────────────────────────────────────────────
    if await rdb.get(f"{m.chat.id}:lockAnimations:{Dev_Zaid}") and m.animation:
        await m.delete()
        if not await rdb.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not await rdb.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            await rdb.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return await m.reply(
                warner.format(k, mention, "ترسل متحركات"), disable_web_page_preview=True
            )

    # ── قفل الملفات ───────────────────────────────────────────────────────
    if await rdb.get(f"{m.chat.id}:lockFiles:{Dev_Zaid}") and m.document:
        await m.delete()
        if not await rdb.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not await rdb.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            await rdb.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return await m.reply(
                warner.format(k, mention, "ترسل ملفات"), disable_web_page_preview=True
            )

    # ── قفل الفارسي (نص) ──────────────────────────────────────────────────
    if await rdb.get(f"{m.chat.id}:lockPersian:{Dev_Zaid}") and m.text:
        if "ه‍" in m.text or "ی" in m.text or "ک" in m.text or "چ" in m.text:
            await m.delete()
            if not await rdb.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}"):
                return await m.reply(
                    warner.format(k, mention, "ترسل فارسي"), disable_web_page_preview=True
                )

    # ── قفل الفارسي (caption) ─────────────────────────────────────────────
    if await rdb.get(f"{m.chat.id}:lockPersian:{Dev_Zaid}") and m.caption:
        if "ه‍" in m.caption or "ی" in m.caption or "ک" in m.caption or "چ" in m.caption:
            await m.delete()
            if not await rdb.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}"):
                return await m.reply(
                    warner.format(k, mention, "ترسل فارسي"), disable_web_page_preview=True
                )

    # ── قفل الروابط ───────────────────────────────────────────────────────
    if (
        await rdb.get(f"{m.chat.id}:lockUrls:{Dev_Zaid}")
        and m.text
        and len(Find(m.text.html)) > 0
    ):
        await m.delete()
        if not await rdb.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not await rdb.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            await rdb.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return await m.reply(
                warner.format(k, mention, "ترسل روابط"), disable_web_page_preview=True
            )

    # ── قفل الهاشتاق ──────────────────────────────────────────────────────
    if (
        await rdb.get(f"{m.chat.id}:lockHashtags:{Dev_Zaid}")
        and m.text
        and len(re.findall(r"#(\w+)", m.text)) > 0
    ):
        await m.delete()
        if not await rdb.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not await rdb.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            await rdb.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return await m.reply(
                warner.format(k, mention, "ترسل هاشتاق"), disable_web_page_preview=True
            )

    # ── قفل الرسائل الطويلة ───────────────────────────────────────────────
    if await rdb.get(f"{m.chat.id}:lockMessages:{Dev_Zaid}") and m.text and len(m.text) > 150:
        await m.delete()
        if not await rdb.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not await rdb.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            await rdb.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return await m.reply(
                warner.format(k, mention, "ترسل كلام كثير"), disable_web_page_preview=True
            )

    # ── قفل الفويس ────────────────────────────────────────────────────────
    if await rdb.get(f"{m.chat.id}:lockVoice:{Dev_Zaid}") and m.voice:
        await m.delete()
        if not await rdb.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not await rdb.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            await rdb.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return await m.reply(
                warner.format(k, mention, "ترسل فويس"), disable_web_page_preview=True
            )

    # ── قفل المنشنات ──────────────────────────────────────────────────────
    if await rdb.get(
        f"{m.chat.id}:lockTags:{Dev_Zaid}"
    ) and '"type": "MessageEntityType.MENTION"' in str(m):
        await m.delete()
        if not await rdb.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}") and not await rdb.get(
            f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}"
        ):
            await rdb.set(f"{Dev_Zaid}:inWARN:{m.from_user.id}{m.chat.id}", 1, ex=60)
            return await m.reply(
                warner.format(k, mention, "ترسل منشنات"), disable_web_page_preview=True
            )

    # ── قفل الانضمام الإيراني (داخل رسائل المجموعة) ─────────────────────
    if await rdb.get(f"{m.chat.id}:lockJoinPersian:{Dev_Zaid}") and m.new_chat_members:
        for joined in m.new_chat_members:
            if await pre_pls(joined.id, m.chat.id):
                continue
            fn = joined.first_name or ""
            ln = joined.last_name or ""
            persian_chars = ("ه‍", "ی", "ک", "چ", "👙")
            is_persian = (
                any(c in fn for c in persian_chars)
                or fn in persianInformation.get("names", [])
                or joined.id in persianInformation.get("ids", [])
                or any(c in ln for c in persian_chars)
                or ln in persianInformation.get("last_names", [])
            )
            if is_persian:
                if not await rdb.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}"):
                    await m.reply(
                        f"\n「 {joined.mention} 」\n{k} تم حظره لاشتباهه ببوت إيراني\n☆\n"
                    )
                await c.ban_chat_member(m.chat.id, joined.id)
                return

    # ── التحقق من الأعضاء الجدد ───────────────────────────────────────────
    if await rdb.get(f"{m.chat.id}:enableVerify:{Dev_Zaid}") and m.new_chat_members:
        for me in m.new_chat_members:
            if not await pre_pls(me.id, m.chat.id):
                await c.restrict_chat_member(
                    m.chat.id, me.id, ChatPermissions(can_send_messages=False)
                )
                get_random = get_for_verify(me)
                return await m.reply(
                    f"{k} قيدناك عشان نتاكد انك شخص حقيقي مو زومبي\n\n"
                    f"{get_random['question']}",
                    reply_markup=get_random["key"],
                )

    # ── قفل NSFW ──────────────────────────────────────────────────────────
    if m.media and await rdb.get(f"{m.chat.id}:lockNSFW:{Dev_Zaid}"):
        if not await admin_pls(uid, m.chat.id):
            media_file_id = None
            if m.sticker:   media_file_id = m.sticker.thumbs[0].file_id
            if m.photo:     media_file_id = m.photo.file_id
            if m.video:     media_file_id = m.video.thumbs[0].file_id
            if m.animation: media_file_id = m.animation.thumbs[0].file_id
            if media_file_id:
                file = await c.download_media(media_file_id)
                await scanR(c, m, media_file_id, file)


# ══════════════════════════════════════════════════════════════════════════════
# 7.  guardLocksResponse                         (all.py سطر 267)
#     هاندلر on_message — Thread(target=guardResponseFunction) → await
# ══════════════════════════════════════════════════════════════════════════════

@register("guard_locks_response")
@Client.on_message(filters.group, group=27)
@safe_handler
async def guardLocksResponse(c, m) -> None:
    """يستقبل رسائل المجموعة ويُطبّق جميع الأقفال عبر guardResponseFunction."""
    k = await rdb.get(f"{Dev_Zaid}:botkey")
    channel = await rdb.get(f"{Dev_Zaid}:BotChannel") or "YQYQY6"
    await guardResponseFunction(c, m, k, channel)


# ══════════════════════════════════════════════════════════════════════════════
# 8.  guardLocksResponse2                        (all.py سطر 276)
#     هاندلر on_edited_message — Thread → await
# ══════════════════════════════════════════════════════════════════════════════

@register("guard_locks_response2")
@Client.on_edited_message(filters.group, group=27)
@safe_handler
async def guardLocksResponse2(c, m) -> None:
    """يستقبل الرسائل المُعدَّلة ويُطبّق قفلَي التعديل."""
    k = await rdb.get(f"{Dev_Zaid}:botkey")
    channel = await rdb.get(f"{Dev_Zaid}:BotChannel") or "YQYQY6"
    await guardResponseFunction2(c, m, k, channel)


# ══════════════════════════════════════════════════════════════════════════════
# 9.  antiPersian                                (all.py سطر 1005)
#     هاندلر on_chat_join_request — r.get → await rdb.get
#     c.decline/c.send_message → await
# ══════════════════════════════════════════════════════════════════════════════

@register("anti_persian")
@Client.on_chat_join_request(filters.group, group=100)
@safe_handler
async def antiPersian(c, m) -> None:
    """يرفض طلبات انضمام المستخدمين المشتبه بكونهم بوتات إيرانية."""
    if not await rdb.get(f"{m.chat.id}:lockJoinPersian:{Dev_Zaid}"):
        return
    k = await rdb.get(f"{Dev_Zaid}:botkey")
    if await pre_pls(m.from_user.id, m.chat.id):
        return

    warn_msg = (
        f"\n「 {m.from_user.mention} 」\n"
        f"{k} تم رفض طلب انضمامه لاشتباهه ببوت إيراني\n☆\n"
    )
    persian_chars = ("ه‍", "ی", "ک", "چ", "👙")

    def _persian(name: str) -> bool:
        return any(ch in name for ch in persian_chars)

    if m.from_user.first_name:
        fn = m.from_user.first_name
        if (
            fn in persianInformation.get("names", [])
            or m.from_user.id in persianInformation.get("ids", [])
            or _persian(fn)
        ):
            await c.decline_chat_join_request(m.chat.id, m.from_user.id)
            if not await rdb.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}"):
                await c.send_message(m.chat.id, warn_msg)
            return

    if m.from_user.last_name:
        ln = m.from_user.last_name
        if (
            ln in persianInformation.get("last_names", [])
            or m.from_user.id in persianInformation.get("ids", [])
            or _persian(ln)
        ):
            await c.decline_chat_join_request(m.chat.id, m.from_user.id)
            if not await rdb.get(f"{m.chat.id}:disableWarn:{Dev_Zaid}"):
                await c.send_message(m.chat.id, warn_msg)
