"""
all_voice_and_blocklist.py
منقول من bmqa/Plugins/all.py (guardCommands — سطر 1564 → 1881)
الفئة: التحكم بالصوت/انطقي ومنع الكلمات والميديا

التحويلات المطبّقة:
  - r.<op>                    → await rdb.<op>
  - r.sismember/sadd/srem     → await rdb.sismember/sadd/srem
  - r.smembers                → await rdb.smembers
  - requests.get(url)         → aiohttp async GET
  - os.system("ffmpeg ...")   → await asyncio.create_subprocess_exec(...)
  - c.send_chat_action(...)   → await c.send_chat_action(...)
  - m.reply_voice(...)        → await m.reply_voice(...)
  - m.reply_to_message.download() → await m.reply_to_message.download()
  - sr.Recognizer (CPU-bound) → asyncio.to_thread
  - Thread(target=guardCommands) → هاندلر async مباشر (بلا Thread)

ملاحظات محفوظة:
  - بناء الـ file_id للفيديو يأخذ rep.photo.file_id بدل rep.video.file_id
    (خطأ موجود في الأصل — محفوظ كما هو)
  - الكود المعلَّق (docstrings داخل الدالة) حُذف للتنظيف
  - أمر "zaid"/"زوز" مقيّد بـ user_id ثابت (6168217372) — محفوظ
"""

import logging
import asyncio
import os
import random

import speech_recognition as sr
from aiohttp import ClientSession
from pydub import AudioSegment

from pyrogram import Client, ContinuePropagation, filters
from pyrogram.enums import ChatAction

from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from helpers.ranks import admin_pls, mod_pls, pre_pls, isLockCommand


# ══════════════════════════════════════════════════════════════════════════════
# دالة مساعدة: بناء نص الأمر (مشتركة مع all_settings.py)
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
# دالة مساعدة: TTS — تنزيل صوت وتحويله بـ ffmpeg وإرساله
# تُستخدم من أوامر "انطق " و"انطقي "
# ══════════════════════════════════════════════════════════════════════════════

async def _tts_and_reply(c, m, txt: str, api_url: str) -> None:
    """
    تنزّل صوتاً من api_url وتحوّله إلى ogg بـ ffmpeg ثم تردّ به كـ voice.
    """
    rand_id = random.randint(999, 10_000)
    mp3_path = f"zaid{rand_id}.mp3"
    ogg_path = f"zaid{rand_id}.ogg"

    # ── تنزيل الصوت من الـ API ─────────────────────────────────────────────
    async with ClientSession() as session:
        async with session.get(api_url) as resp:
            content = await resp.read()

    with open(mp3_path, "wb") as f:
        f.write(content)

    # ── إشعار "يسجّل صوتاً" ────────────────────────────────────────────────
    try:
        await c.send_chat_action(m.chat.id, ChatAction.RECORD_AUDIO)
    except Exception as e:
        logging.exception(e)
        pass

    # ── تحويل mp3 → ogg بـ ffmpeg (async subprocess) ──────────────────────
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-i", mp3_path,
        "-ac", "1",
        "-strict", "-2",
        "-codec:a", "libopus",
        "-b:a", "128k",
        "-vbr", "off",
        "-ar", "24000",
        ogg_path,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()

    # ── إشعار "يرفع صوتاً" ─────────────────────────────────────────────────
    try:
        await c.send_chat_action(m.chat.id, ChatAction.UPLOAD_AUDIO)
    except Exception as e:
        logging.exception(e)
        pass

    # ── إرسال الصوت والتنظيف ──────────────────────────────────────────────
    await m.reply_voice(ogg_path, caption=f"الكلمة: {txt}")
    if os.path.exists(ogg_path):
        os.remove(ogg_path)
    if os.path.exists(mp3_path):
        os.remove(mp3_path)


# ══════════════════════════════════════════════════════════════════════════════
# دالة مساعدة: التعرف على الكلام (speech-to-text) — CPU-bound → to_thread
# ══════════════════════════════════════════════════════════════════════════════

def _speech_to_text(wav_path: str, language: str) -> str:
    """تحوّل ملف wav إلى نص. تُشغَّل في thread منفصل لأنها عملية blocking."""
    s = sr.Recognizer()
    sound = AudioSegment.from_ogg(wav_path)
    sound.export(wav_path, format="wav")
    with sr.AudioFile(wav_path) as src:
        audio_source = s.record(src)
    return s.recognize_google(audio_source, language=language)


# ══════════════════════════════════════════════════════════════════════════════
# الهاندلر الرئيسي — group=28 (نفس الأصل)
# ══════════════════════════════════════════════════════════════════════════════

@register("voice_and_blocklist_commands")
@Client.on_message(filters.group & filters.text, group=28)
@safe_handler
async def voiceAndBlocklistHandler(c, m) -> None:
    """
    يعالج أوامر انطق/انطقي والتعرف على الكلام وقوائم المنع.
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
    k = await rdb.get(f"{Dev_Zaid}:botkey")

    # ══════════════════════════════════════════════════════════════════════
    # 1. انطق <نص>                                       (all.py سطر 1564)
    #    API: eduardo-tate.com/AI/voice.php?text=…&model=3
    #    os.system → asyncio.create_subprocess_exec
    #    requests.get → aiohttp async
    # ══════════════════════════════════════════════════════════════════════
    if text.startswith("انطق "):
        if not await rdb.get(f"{cid}:disableSay:{Dev_Zaid}"):
            txt = text.split(None, 1)[1]
            if len(txt) > 500:
                return await m.reply(f"{k} حبيبي ماينفع تتجاوز ٥٠٠ حرف بالنطق")
            api_url = f"https://eduardo-tate.com/AI/voice.php?text={txt}&model=3"
            await _tts_and_reply(c, m, txt, api_url)
            return

    # ══════════════════════════════════════════════════════════════════════
    # 2. انطقي <نص>                                      (all.py سطر 1624)
    #    API: eduardo-tate.com/AI/voice.php?text=…  (بدون model=3)
    # ══════════════════════════════════════════════════════════════════════
    if text.startswith("انطقي "):
        if not await rdb.get(f"{cid}:disableSay:{Dev_Zaid}"):
            txt = text.split(None, 1)[1]
            if len(txt) > 500:
                return await m.reply(f"{k} حبيبي ماينفع تتجاوز ٥٠٠ حرف بالنطق")
            api_url = f"https://eduardo-tate.com/AI/voice.php?text={txt}"
            await _tts_and_reply(c, m, txt, api_url)
            return

    # ══════════════════════════════════════════════════════════════════════
    # 3. وش يقول / وش تقول؟  (رد على رسالة صوتية)        (all.py سطر 1684)
    #    التعرف على الكلام بالعربية
    #    sr.Recognizer (blocking) → asyncio.to_thread
    # ══════════════════════════════════════════════════════════════════════
    if (
        (text == "وش يقول" or text == "وش تقول؟")
        and m.reply_to_message
        and m.reply_to_message.voice
    ):
        if m.reply_to_message.voice.file_size > 20_971_520:
            return await m.reply(f"{k} عيني حجم المقطع أكبر من ٢٠ ميجابايت")
        rand_id = random.randint(99, 1000)
        wav_path = f"./zaid{rand_id}.wav"
        wav_path = await m.reply_to_message.download(wav_path)
        try:
            result = await asyncio.to_thread(_speech_to_text, wav_path, "ar-SA")
        except Exception as e:
            logging.exception(e)
            print(e)
            if os.path.exists(wav_path):
                os.remove(wav_path)
            return await m.reply(f"{k} ما قدرت افهم وش يقول")
        if os.path.exists(wav_path):
            os.remove(wav_path)
        return await m.reply(f"يقول : {result}")

    # ══════════════════════════════════════════════════════════════════════
    # 4. zaid / زوز  (رد على رسالة صوتية — user_id ثابت)  (all.py سطر 1707)
    #    التعرف على الكلام بالإنجليزية — مقيّد بـ uid=6168217372
    # ══════════════════════════════════════════════════════════════════════
    if (
        (text == "zaid" or text == "زوز")
        and m.reply_to_message
        and m.reply_to_message.voice
        and uid == 6168217372
    ):
        if m.reply_to_message.voice.file_size > 20_971_520:
            return await m.reply(f"{k} عيني حجم المقطع أكبر من ٢٠ ميجابايت")
        rand_id = random.randint(99, 1000)
        wav_path = f"./zaid{rand_id}.wav"
        wav_path = await m.reply_to_message.download(wav_path)
        try:
            result = await asyncio.to_thread(_speech_to_text, wav_path, "en-US")
        except Exception as e:
            logging.exception(e)
            print(e)
            if os.path.exists(wav_path):
                os.remove(wav_path)
            return await m.reply(f"{k} ما قدرت افهم وش يقول")
        if os.path.exists(wav_path):
            os.remove(wav_path)
        return await m.reply(f"يقول : {result}")

    # ══════════════════════════════════════════════════════════════════════
    # 5. منع <كلمة>  (بلوك نص)                           (all.py سطر 1731)
    #    r.sismember → await rdb.sismember
    #    r.sadd      → await rdb.sadd
    # ══════════════════════════════════════════════════════════════════════
    if text.startswith("منع "):
        if await mod_pls(uid, cid):
            noice = text.split(None, 1)[1]
            if await rdb.sismember(f"{cid}:NotAllowedListText:{Dev_Zaid}", noice):
                return await m.reply(
                    f"{k} الكلمة ( {noice} ) موجودة بقائمة المنع",
                    disable_web_page_preview=True,
                )
            await rdb.sadd(f"{cid}:NotAllowedListText:{Dev_Zaid}", noice)
            return await m.reply(
                f"{k} الكلمة ( {noice} ) اضفتها الى قائمة المنع",
                disable_web_page_preview=True,
            )

    # ══════════════════════════════════════════════════════════════════════
    # 6. الغاء منع <كلمة>  (رفع بلوك نص)                 (all.py سطر 1746)
    #    r.sismember → await rdb.sismember
    #    r.srem      → await rdb.srem
    # ══════════════════════════════════════════════════════════════════════
    if text.startswith("الغاء منع ") and len(text.split()) > 2:
        if await mod_pls(uid, cid):
            noice = text.split(None, 2)[2]
            if not await rdb.sismember(f"{cid}:NotAllowedListText:{Dev_Zaid}", noice):
                return await m.reply(
                    f"{k} الكلمة ( {noice} ) مو مضافة بقائمة المنع",
                    disable_web_page_preview=True,
                )
            await rdb.srem(f"{cid}:NotAllowedListText:{Dev_Zaid}", noice)
            return await m.reply(
                f"{k} ابشر مسحت ( {noice} ) من قائمة المنع",
                disable_web_page_preview=True,
            )

    # ══════════════════════════════════════════════════════════════════════
    # 7. منع  (رد على وسيط — بلوك ميديا)                 (all.py سطر 1761)
    #    ملاحظة: rep.video → file_id = rep.photo.file_id
    #    هذا خطأ موجود في الأصل — محفوظ كما هو
    # ══════════════════════════════════════════════════════════════════════
    if text == "منع" and m.reply_to_message and m.reply_to_message.media:
        if await mod_pls(uid, cid):
            rep = m.reply_to_message
            file_id = None
            media_type = None
            if rep.sticker:
                file_id = rep.sticker.file_id
                media_type = "sticker"
            if rep.animation:
                file_id = rep.animation.file_id
                media_type = "animation"
            if rep.photo:
                file_id = rep.photo.file_id
                media_type = "photo"
            if rep.video:
                file_id = rep.photo.file_id    # ⚠️ خطأ من الأصل — rep.photo بدل rep.video
                media_type = "video"
            if rep.voice:
                file_id = rep.voice.file_id
                media_type = "voice"
            if rep.audio:
                file_id = rep.audio.file_id
                media_type = "audio"
            if rep.document:
                file_id = rep.document.file_id
                media_type = "document"

            if file_id is None:
                return

            short_id = file_id[-6:]
            if await rdb.get(f"{short_id}:NotAllow:{cid}{Dev_Zaid}"):
                return await m.reply(f"{k} موجودة بقائمة المنع")
            await rdb.set(f"{short_id}:NotAllow:{cid}{Dev_Zaid}", 1)
            await rdb.sadd(
                f"{cid}:NotAllowedList:{Dev_Zaid}",
                f"file={short_id}&by={uid}&type={media_type}&file_id={file_id}",
            )
            return await m.reply(f"{k} واضفناها لقائمة المنع")

    # ══════════════════════════════════════════════════════════════════════
    # 8. الغاء منع  (رد على وسيط — رفع بلوك ميديا)       (all.py سطر 1797)
    #    نفس ملاحظة خطأ الفيديو من الأصل — محفوظ
    # ══════════════════════════════════════════════════════════════════════
    if text == "الغاء منع" and m.reply_to_message and m.reply_to_message.media:
        if await mod_pls(uid, cid):
            rep = m.reply_to_message
            file_id = None
            media_type = None
            if rep.sticker:
                file_id = rep.sticker.file_id
                media_type = "sticker"
            if rep.animation:
                file_id = rep.animation.file_id
                media_type = "animation"
            if rep.photo:
                file_id = rep.photo.file_id
                media_type = "photo"
            if rep.video:
                file_id = rep.photo.file_id    # ⚠️ خطأ من الأصل — rep.photo بدل rep.video
                media_type = "video"
            if rep.voice:
                file_id = rep.voice.file_id
                media_type = "voice"
            if rep.audio:
                file_id = rep.audio.file_id
                media_type = "audio"
            if rep.document:
                file_id = rep.document.file_id
                media_type = "document"

            if file_id is None:
                return

            short_id = file_id[-6:]
            if not await rdb.get(f"{short_id}:NotAllow:{cid}{Dev_Zaid}"):
                return await m.reply(f"{k} مو موجودة بقائمة المنع")
            await rdb.delete(f"{short_id}:NotAllow:{cid}{Dev_Zaid}")
            await rdb.srem(
                f"{cid}:NotAllowedList:{Dev_Zaid}",
                f"file={short_id}&by={uid}&type={media_type}&file_id={file_id}",
            )
            return await m.reply(f"{k} ابشر شلتها من قائمه المنع")

    # ══════════════════════════════════════════════════════════════════════
    # 9. منع  (رد على رسالة غير وسيط — رسالة خطأ)        (all.py سطر 1833)
    # ══════════════════════════════════════════════════════════════════════
    if text == "منع" and m.reply_to_message and not m.reply_to_message.media:
        if await mod_pls(uid, cid):
            return await m.reply(f"{k} المنع بالرد فقط للوسائط")

    # ══════════════════════════════════════════════════════════════════════
    # 10. قائمه المنع / قائمة المنع                       (all.py سطر 1837)
    #     r.smembers → await rdb.smembers
    # ══════════════════════════════════════════════════════════════════════
    if text in ("قائمه المنع", "قائمة المنع"):
        if await mod_pls(uid, cid):
            text_list = await rdb.smembers(f"{cid}:NotAllowedListText:{Dev_Zaid}")
            media_list = await rdb.smembers(f"{cid}:NotAllowedList:{Dev_Zaid}")

            if not text_list and not media_list:
                return await m.reply(f"{k} مافي شي ممنوع")

            text1 = "الكلمات الممنوعة:\n"
            if not text_list:
                text1 += "لايوجد"
            else:
                for count, word in enumerate(text_list, start=1):
                    text1 += f"{count} - {word}\n"

            text2 = "الوسائط الممنوعة:\n"
            if not media_list:
                text2 += "لايوجد"
            else:
                for count2, entry in enumerate(media_list, start=1):
                    short_id   = entry.split("file=")[1].split("&")[0]
                    by_uid     = entry.split("by=")[1].split("&")[0]
                    entry_type = entry.split("type=")[1].split("&")[0]
                    text2 += (
                        f"{count2} - (`{short_id}`) ࿓ "
                        f"( [{entry_type}](tg://user?id={by_uid}) )\n"
                    )

            return await m.reply(f"{text1}\n{text2}", disable_web_page_preview=True)

    # ══════════════════════════════════════════════════════════════════════
    # 11. مسح قائمه المنع / مسح قائمة المنع               (all.py سطر 1867)
    #     يمسح مفاتيح file_id الفردية قبل مسح القائمة الرئيسية
    # ══════════════════════════════════════════════════════════════════════
    if text in ("مسح قائمه المنع", "مسح قائمة المنع"):
        if await mod_pls(uid, cid):
            text_list = await rdb.smembers(f"{cid}:NotAllowedListText:{Dev_Zaid}")
            media_list = await rdb.smembers(f"{cid}:NotAllowedList:{Dev_Zaid}")

            if not text_list and not media_list:
                return await m.reply(f"{k} مافي شي ممنوع")

            if text_list:
                await rdb.delete(f"{cid}:NotAllowedListText:{Dev_Zaid}")

            if media_list:
                for entry in media_list:
                    short_id = entry.split("file=")[1].split("&by=")[0]
                    await rdb.delete(f"{short_id}:NotAllow:{cid}{Dev_Zaid}")
                await rdb.delete(f"{cid}:NotAllowedList:{Dev_Zaid}")

            return await m.reply(f"{k} ابشر مسحت قائمة المنع")

    # لا يوجد أمر من الأوامر أعلاه يطابق النص — لم يُرسَل أي رد فعلي
    # للمستخدم في هذا المسار، لذا نُمرِّر المعالجة لبقية handlers group=28
    # (راجع [C4] في all_moderation_2.py لشرح المشكلة الأصلية).
    raise ContinuePropagation()
