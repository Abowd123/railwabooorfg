"""
Plugins/downloader.py — bmqa-v2

مُنقول من bmqa/Plugins/downloader.py (النسخة الأصلية المتزامنة، مبنية على
Thread + os.system) إلى نسخة async بالكامل تعتمد على core/worker.py (arq)
لكل عملية ثقيلة (تحميل يوتيوب/تيك توك/ساوند كلاود، وتحويل ffmpeg، والتعرف
عبر Shazam).

الفرق الجوهري عن الأصل:
  - القديم: Thread(target=..., args=...).start() ثم تنفيذ التحميل مباشرة
    داخل نفس عملية البوت (يحجب أي عملية I/O أخرى فعلياً رغم استخدام Thread،
    ولا توجد طريقة لإعادة المحاولة أو مراقبة المهام).
  - الجديد: الـ handler يتحقق من القيود (قفل/كتم/تعطيل) بسرعة، يرد فوراً
    برسالة "⏳ جاري التنفيذ..."، ثم يرسل المهمة إلى طابور arq عبر
    core.worker.enqueue() ويعود فوراً. عملية worker منفصلة (راجع README)
    هي من تُنفّذ التحميل/التحويل الفعلي وتُحدّث رسالة الحالة عند الانتهاء.
  - os.system("ffmpeg ...") لتحويل الصوت لبصمة صوتية (voice) انتقل بالكامل
    إلى core.worker._run_ffmpeg (asyncio.create_subprocess_exec)، ولم يعد
    يوجد أي os.system في هذا الملف.
  - pytube (مكتبة غير مُحدَّثة بشكل جيد وتتعطل كثيراً) استُبدلت بـ yt_dlp فقط
    لكل من البحث السريع واستخراج المعلومات، توحيداً للاعتماديات.

ملاحظة: البحث عن نتائج يوتيوب (يوت/بحث) ومعاينة العنوان/الصورة المصغّرة
(GET callback) عمليات خفيفة نسبياً (شبكة فقط، بلا ffmpeg ولا تحميل ملف
كامل) فتبقى داخل نفس handler لكن عبر asyncio.to_thread لعدم تجميد الحلقة.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time

import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import Dev_Zaid
from core.db import rdb, ytdb, sounddb
from core.dispatcher import register
from core.errors import safe_handler
from core.rate_limit import rate_limited
from core.worker import enqueue
from helpers.ranks import isLockCommand

logger = logging.getLogger("bmqa.downloader")

_URL_RE = re.compile(
    r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)"
    r"(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+"
    r"(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s!()\[\]{};:'\".,<>?]))"
)


def find_urls(text: str) -> list[str]:
    return [m[0] for m in _URL_RE.findall(text)]


async def _channel(rdb_client) -> str:
    return await rdb_client.get(f"{Dev_Zaid}:BotChannel") or "w7G_BoT"


def _channel_button(channel: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🧚‍♀️", url=f"https://t.me/{channel}")]])


async def _search_youtube(query: str, max_results: int = 1) -> list[dict]:
    """بحث سريع (شبكة فقط) عبر yt_dlp، يُشغَّل في Thread منفصل حتى لا يجمّد الحلقة."""

    def _search():
        opts = {"quiet": True, "extract_flat": "in_playlist", "noplaylist": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
        return info.get("entries") or []

    return await asyncio.to_thread(_search)


# ============================================================
# يوت <بحث> — قائمة نتائج (خفيف: بحث فقط، بلا تحميل)
# ============================================================
@register("يوت ")
@Client.on_message(filters.text & filters.group & filters.regex(r"^يوت "), group=32)
@safe_handler
async def yt_search_list(c: Client, m) -> None:
    if not await rdb.get(f"{m.chat.id}:enable:{Dev_Zaid}"):
        return
    if await rdb.get(f"{m.chat.id}:disableYT:{Dev_Zaid}") or await rdb.get(f":disableYT:{Dev_Zaid}"):
        return
    if await isLockCommand(m.from_user.id, m.chat.id, m.text):
        return

    k = await rdb.get(f"{Dev_Zaid}:botkey") or "🧚‍♀️"
    query = m.text.split(None, 1)[1]

    results = await _search_youtube(query, max_results=4)
    if not results:
        await m.reply(f"{k} لا نتائج لـ ~ {query}")
        return

    keyboard = [
        [InlineKeyboardButton(res.get("title", "?")[:60], callback_data=f"{m.from_user.id}GET{res['id']}")]
        for res in results
    ]
    status = await m.reply(
        f"{k} البحث ~ {query}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True,
    )
    await rdb.set(f"{status.id}:one_minute:{m.from_user.id}", 1, ex=60)


# ============================================================
# بحث <اسم>/yt <اسم> — تحميل صوت مباشر (ثقيل → طابور)
# ============================================================
@register("yt_audio_search")
@Client.on_message(filters.text & filters.group & filters.regex(r"^(?:بحث|yt) "), group=32)
@safe_handler
@rate_limited(rdb, "yt_audio_search", max_commands=3, window_seconds=60)
async def yt_audio_search(c: Client, m) -> None:
    if not await rdb.get(f"{m.chat.id}:enable:{Dev_Zaid}"):
        return
    if await rdb.get(f"{m.chat.id}:disableYT:{Dev_Zaid}") or await rdb.get(f":disableYT:{Dev_Zaid}"):
        return
    if await isLockCommand(m.from_user.id, m.chat.id, m.text):
        return

    k = await rdb.get(f"{Dev_Zaid}:botkey") or "🧚‍♀️"
    channel = await _channel(rdb)
    query = m.text.split(None, 1)[1]

    results = await _search_youtube(query, max_results=1)
    if not results:
        await m.reply(f"{k} لا نتائج لـ ~ {query}")
        return
    res = results[0]
    vid_id = res["id"]

    cached = await ytdb.get(f"ytvideo{vid_id}")
    if cached:
        duration_string = time.strftime("%M:%S", time.gmtime(cached["duration"]))
        await m.reply_audio(
            cached["audio"],
            caption=f"@{channel} ~ {duration_string} ⏳",
            reply_markup=_channel_button(channel),
        )
        return

    status = await m.reply("⏳ جاري التنفيذ...")
    await enqueue(
        "task_youtube_audio",
        chat_id=m.chat.id,
        status_message_id=status.id,
        reply_to_message_id=m.id,
        url=f"https://youtu.be/{vid_id}",
        vid_id=vid_id,
        channel=channel,
    )


# ============================================================
# تيك <رابط> — تحميل فيديو تيك توك (ثقيل → طابور)
# ============================================================
@register("تيك ")
@Client.on_message(filters.text & filters.group & filters.regex(r"^تيك "), group=32)
@safe_handler
@rate_limited(rdb, "tiktok_download", max_commands=3, window_seconds=60)
async def tiktok_download(c: Client, m) -> None:
    if await rdb.get(f"{m.chat.id}:disableTik:{Dev_Zaid}") or await rdb.get(f":disableYT:{Dev_Zaid}"):
        return
    if await isLockCommand(m.from_user.id, m.chat.id, m.text):
        return

    urls = find_urls(m.text)
    if not urls:
        return
    channel = await _channel(rdb)

    status = await m.reply("⏳ جاري التنفيذ...")
    await enqueue(
        "task_tiktok_download",
        chat_id=m.chat.id,
        status_message_id=status.id,
        reply_to_message_id=m.id,
        url=urls[0],
        channel=channel,
    )


# ============================================================
# <رابط ساوند كلاود> #AUDIO / #VOICE (ثقيل → طابور، #VOICE يستخدم ffmpeg)
# ============================================================
@register("soundcloud_audio_voice")
@Client.on_message(
    filters.text & filters.group & (filters.regex(r"#AUDIO$") | filters.regex(r"#VOICE$")),
    group=32,
)
@safe_handler
@rate_limited(rdb, "soundcloud_download", max_commands=3, window_seconds=60)
async def soundcloud_audio_or_voice(c: Client, m) -> None:
    if await rdb.get(f"{m.chat.id}:disableSound:{Dev_Zaid}") or await rdb.get(f":disableYT:{Dev_Zaid}"):
        return

    urls = find_urls(m.text)
    if not urls or "soundcloud" not in urls[0]:
        return
    url = urls[0]
    track_key = url.split("soundcloud.com/")[-1].split("soundcloud.com")[-1]
    channel = await _channel(rdb)
    is_voice = m.text.rstrip().endswith("#VOICE")

    if is_voice:
        cached = await sounddb.get(f"{track_key}:soundVoice")
        if cached:
            await m.reply_voice(cached)
            return
        status = await m.reply("⏳ جاري التنفيذ...")
        await enqueue(
            "task_soundcloud_voice",
            chat_id=m.chat.id, status_message_id=status.id, reply_to_message_id=m.id,
            url=url, channel=channel, track_key=track_key,
        )
    else:
        cached = await sounddb.get(f"{track_key}:sound")
        if cached:
            await m.reply_audio(cached)
            return
        status = await m.reply("⏳ جاري التنفيذ...")
        await enqueue(
            "task_soundcloud_audio",
            chat_id=m.chat.id, status_message_id=status.id, reply_to_message_id=m.id,
            url=url, channel=channel, track_key=track_key,
        )


# ============================================================
# شازام — تعرّف على صوت (ثقيل: تحميل + تعرف → طابور)
# ============================================================
@register("شازام")
@Client.on_message(filters.regex("^شازام$") & filters.group)
@safe_handler
@rate_limited(rdb, "shazam_recognize", max_commands=3, window_seconds=60)
async def shazam_recognize(c: Client, m) -> None:
    if await rdb.get(f"{m.chat.id}:disableShazam:{Dev_Zaid}"):
        return
    rep = m.reply_to_message
    if not rep or not (rep.audio or rep.voice or rep.video):
        return

    media = rep.audio or rep.voice or rep.video
    duration = media.duration or 301
    file_size = media.file_size or 0
    if duration > 300:
        await m.reply("مدة المقطع أكثر من 5 دقايق ..")
        return
    if file_size > 26214400:
        await m.reply("حجم المقطع أكثر من 25 ميجابايت ..")
        return

    channel = await _channel(rdb)
    status = await m.reply("⏳ جاري التنفيذ...")
    await enqueue(
        "task_shazam_recognize",
        chat_id=m.chat.id,
        status_message_id=status.id,
        reply_to_message_id=m.id,
        file_id=media.file_id,
        channel=channel,
    )


@register("شازام_بحث")
@Client.on_message(filters.regex("^شازام ") & filters.group)
@safe_handler
async def shazam_lyrics_search(c: Client, m) -> None:
    """بحث نصي فقط عبر Shazam (بلا تحميل ملف) — خفيف، يبقى داخل الـ handler مباشرة."""
    if await rdb.get(f"{m.chat.id}:disableShazam:{Dev_Zaid}"):
        return
    query = m.text.split(None, 1)[1]

    from shazamio import Shazam
    shazam = Shazam()
    out = await shazam.search_track(query=query, limit=1)
    if not out or not out.get("tracks", {}).get("hits"):
        await m.reply("فشل العثور")
        return
    try:
        hit = out["tracks"]["hits"][0]
        key = int(hit["key"])
        title = hit["heading"]["title"][:35]
        author = hit["heading"]["subtitle"]
        url = hit["url"]
        about_track = await shazam.track_about(track_id=key)
        text_sections = about_track["sections"][1]["text"]
        lyrics = "\n".join(text_sections)
        await m.reply(
            lyrics[:4096],
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"{title} - {author}", url=url)]]),
        )
    except Exception:
        logger.exception("shazam_lyrics_search فشلت")
        await m.reply("فشل العثور")


# ============================================================
# GET / AUDIO / VIDEO callbacks (من قائمة "يوت" السابقة)
# ============================================================
@register("yt_get_callback")
@Client.on_callback_query(filters.regex(r"^\d+GET"))
@safe_handler
async def yt_get_callback(c: Client, query) -> None:
    user_id, vid_id = query.data.split("GET", 1)
    if query.from_user.id != int(user_id):
        await query.answer()
        return
    if not await rdb.get(f"{query.message.id}:one_minute:{user_id}"):
        k = await rdb.get(f"{Dev_Zaid}:botkey") or "🧚‍♀️"
        await query.answer(f"{k} مر على البحث اكثر من دقيقة ابحث مرة ثانية", show_alert=True)
        await query.message.delete()
        return
    if await rdb.get(f"{query.message.chat.id}:disableYT:{Dev_Zaid}") or await rdb.get(f":disableYT:{Dev_Zaid}"):
        return

    await query.message.delete()
    channel = await _channel(rdb)
    url = f"https://youtu.be/{vid_id}"
    photo = f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"
    reply_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("♫ ملف صوتي", callback_data=f"{user_id}AUDIO{vid_id}"),
                InlineKeyboardButton("❖ فيديو", callback_data=f"{user_id}VIDEO{vid_id}"),
            ],
            [InlineKeyboardButton("🧚‍♀️", url=f"https://t.me/{channel}")],
        ]
    )
    await query.message.reply_to_message.reply_photo(
        photo, caption=f"@{channel} ~ {url}", reply_markup=reply_markup,
    )


@register("yt_audio_callback")
@Client.on_callback_query(filters.regex(r"^\d+AUDIO"))
@safe_handler
async def yt_audio_callback(c: Client, query) -> None:
    user_id, vid_id = query.data.split("AUDIO", 1)
    if query.from_user.id != int(user_id):
        await query.answer()
        return
    if await rdb.get(f"{query.message.chat.id}:disableYT:{Dev_Zaid}") or await rdb.get(f":disableYT:{Dev_Zaid}"):
        return
    channel = await _channel(rdb)

    cached = await ytdb.get(f"ytvideo{vid_id}")
    if cached:
        duration_string = time.strftime("%M:%S", time.gmtime(cached["duration"]))
        await query.edit_message_caption(f"@{channel} :)", reply_markup=_channel_button(channel))
        await query.message.reply_audio(cached["audio"], caption=f"@{channel} ~ ⏳ {duration_string}")
        return

    await query.edit_message_caption("⏳ جاري التنفيذ...", reply_markup=_channel_button(channel))
    await enqueue(
        "task_youtube_audio",
        chat_id=query.message.chat.id,
        status_message_id=query.message.id,
        reply_to_message_id=query.message.id,
        url=f"https://youtu.be/{vid_id}",
        vid_id=vid_id,
        channel=channel,
    )


@register("yt_video_callback")
@Client.on_callback_query(filters.regex(r"^\d+VIDEO"))
@safe_handler
async def yt_video_callback(c: Client, query) -> None:
    user_id, vid_id = query.data.split("VIDEO", 1)
    if query.from_user.id != int(user_id):
        await query.answer()
        return
    if await rdb.get(f"{query.message.chat.id}:disableYT:{Dev_Zaid}") or await rdb.get(f":disableYT:{Dev_Zaid}"):
        return
    channel = await _channel(rdb)

    cached = await ytdb.get(f"ytvideoV{vid_id}")
    if cached:
        duration_string = time.strftime("%M:%S", time.gmtime(cached["duration"]))
        await query.edit_message_caption(f"@{channel} :)", reply_markup=_channel_button(channel))
        await query.message.reply_video(cached["video"], caption=f"@{channel} ~ ⏳ {duration_string}")
        return

    await query.edit_message_caption("⏳ جاري التنفيذ...", reply_markup=_channel_button(channel))
    await enqueue(
        "task_youtube_video",
        chat_id=query.message.chat.id,
        status_message_id=query.message.id,
        reply_to_message_id=query.message.id,
        url=f"https://youtu.be/{vid_id}",
        vid_id=vid_id,
        channel=channel,
    )
