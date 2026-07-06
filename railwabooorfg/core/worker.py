"""
core/worker.py — bmqa-v2

طابور مهام خلفية (python-arq) لكل عملية ثقيلة في Plugins/downloader.py:
تحميل يوتيوب (صوت/فيديو)، تيك توك، ساوند كلاود (صوت/بصمة صوتية عبر ffmpeg)،
والتعرف على المقاطع عبر Shazam.

لماذا؟
  كل هذه العمليات تشمل تحميل ملف من الإنترنت و/أو استدعاء ffmpeg، وهذا قد
  يأخذ من ثانيتين إلى دقائق. تنفيذها مباشرة داخل on_message handler يجمّد
  event loop الخاص بـ Pyrogram (أو يحجز Thread طويلاً في النسخة القديمة)
  ويمنع البوت من الرد على أي مستخدم آخر أثناء التحميل. الحل: الـ handler
  يرسل المهمة فوراً لطابور Redis (arq) ويرد "جاري التنفيذ..." خلال أجزاء من
  الثانية، وعملية worker منفصلة (تعمل بأمر مستقل، راجع README) هي من تُنفّذ
  التحميل الفعلي ثم تُحدّث/تحذف رسالة الحالة وترسل النتيجة عند الانتهاء.

الاستخدام من داخل Plugins (لإرسال مهمة للطابور):
    from core.worker import enqueue
    await enqueue("task_youtube_audio", chat_id=m.chat.id, ...)

تشغيل الـ worker نفسه (عملية منفصلة عن البوت):
    arq core.worker.WorkerSettings
(راجع README.md لتفاصيل التشغيل الكامل مع البوت جنباً إلى جنب.)
"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import tempfile
import time
from typing import Any, Optional

import yt_dlp
from arq import create_pool
from arq.connections import RedisSettings
from pyrogram import Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import config
from core.db import rdb, ytdb, sounddb

logger = logging.getLogger("bmqa.worker")

# ============================================================
# إعدادات عامة
# ============================================================
DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

MAX_DURATION_SECONDS = 25 * 60  # 25 دقيقة — نفس الحد الأصلي في downloader.py

REDIS_SETTINGS = RedisSettings(
    host=config.redis_host,
    port=config.redis_port,
    database=config.redis_db,
    password=config.redis_password,
)


# ============================================================
# مُنسّق (enqueue) — يُستدعى من داخل عملية البوت (Plugins/downloader.py)
# ============================================================
_arq_pool = None
_arq_pool_lock = asyncio.Lock()


async def get_arq_pool():
    """يُنشئ (أو يعيد استخدام) اتصال Redis الخاص بطابور arq. Singleton لكل عملية."""
    global _arq_pool
    if _arq_pool is None:
        async with _arq_pool_lock:
            if _arq_pool is None:
                _arq_pool = await create_pool(REDIS_SETTINGS)
    return _arq_pool


async def enqueue(job_name: str, **kwargs: Any):
    """يرسل مهمة لطابور arq فوراً (بدون انتظار تنفيذها) ويُعيد كائن Job."""
    pool = await get_arq_pool()
    job = await pool.enqueue_job(job_name, **kwargs)
    logger.info("تم إرسال مهمة '%s' للطابور (job_id=%s)", job_name, getattr(job, "job_id", None))
    return job


# ============================================================
# دوال مساعدة مشتركة للـ worker
# ============================================================
def _channel_button(channel: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🧚‍♀️", url=f"https://t.me/{channel}")]])


async def _safe_edit(bot: Client, chat_id: int, message_id: Optional[int], text: str) -> None:
    """يعدّل رسالة الحالة، ويتجاهل بهدوء لو حُذفت مسبقاً أو لم تُعطَ."""
    if not message_id:
        return
    try:
        await bot.edit_message_text(chat_id, message_id, text)
    except Exception:
        logger.debug("تعذّر تعديل رسالة الحالة %s في %s", message_id, chat_id, exc_info=True)


async def _safe_delete(bot: Client, chat_id: int, message_id: Optional[int]) -> None:
    if not message_id:
        return
    try:
        await bot.delete_messages(chat_id, message_id)
    except Exception:
        logger.debug("تعذّر حذف رسالة الحالة %s في %s", message_id, chat_id, exc_info=True)


def _yt_extract(url: str, ydl_opts: dict, download: bool):
    """استدعاء yt_dlp المتزامن (blocking) — يُشغَّل دائماً عبر asyncio.to_thread."""
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=download)
        filename = ydl.prepare_filename(info) if download else None
    return info, filename


async def _run_ffmpeg(*args: str) -> None:
    """
    بديل os.system("ffmpeg ...") الآمن وغير المُجمِّد لبقية البوت.

    الفرق الجوهري:
      - os.system(...) القديم كان يبني سطر أوامر واحد كنص (shell string)،
        وهو عرضة لمشاكل الـ shell injection لو دخلت أي قيمة من مستخدم ضمن
        السطر، ويحجب (blocking) العملية بالكامل بلا تحكم.
      - asyncio.create_subprocess_exec يستقبل كل وسيط (argument) منفصلاً
        بدون المرور عبر /bin/sh إطلاقاً، وهو async بالكامل (لا يجمّد شيئاً)،
        ونلتقط هنا stdout/stderr ونتحقق من returncode بدل تجاهل نتيجة التنفيذ.
    """
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg فشل (code={proc.returncode}): {stderr.decode(errors='ignore')[-500:]}"
        )


async def _download_thumb(url: Optional[str], dest_path: str) -> Optional[str]:
    """تحميل صورة مصغّرة (best-effort) — فشلها لا يوقف المهمة الأساسية."""
    if not url:
        return None
    try:
        from helpers.utils import http
        resp = await http.get(url, timeout=15)
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(resp.content)
        return dest_path
    except Exception:
        return None


# ============================================================
# المهام (arq tasks) — كل دالة هنا تُسجَّل في WorkerSettings.functions
# ============================================================

async def task_youtube_audio(
    ctx: dict, *, chat_id: int, status_message_id: int, reply_to_message_id: int,
    url: str, vid_id: str, channel: str,
) -> None:
    bot: Client = ctx["bot"]
    job_dir = tempfile.mkdtemp(prefix="ytaudio_", dir=DOWNLOAD_DIR)
    try:
        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": f"{job_dir}/%(id)s.%(ext)s",
            "noplaylist": True,
            "quiet": True,
        }
        info, filename = await asyncio.to_thread(_yt_extract, url, ydl_opts, True)
        duration = int(info.get("duration") or 0)
        if duration > MAX_DURATION_SECONDS:
            await _safe_edit(bot, chat_id, status_message_id, "صوت فوق 25 دقيقة ما اقدر انزله")
            return

        mp3_path = os.path.join(job_dir, f"{info['id']}.mp3")
        await _run_ffmpeg("-i", filename, "-vn", "-ab", "192k", mp3_path)

        thumb_path = await _download_thumb(info.get("thumbnail"), os.path.join(job_dir, "thumb.jpg"))
        duration_string = time.strftime("%M:%S", time.gmtime(duration))

        sent = await bot.send_audio(
            chat_id,
            mp3_path,
            title=info.get("title"),
            performer=info.get("uploader"),
            duration=duration,
            thumb=thumb_path,
            caption=f"@{channel} ~ {duration_string} ⏳",
            reply_markup=_channel_button(channel),
            reply_to_message_id=reply_to_message_id,
        )
        await ytdb.set(
            f"ytvideo{vid_id}",
            {"type": "audio", "audio": sent.audio.file_id, "duration": sent.audio.duration},
        )
        await _safe_delete(bot, chat_id, status_message_id)
    except Exception:
        logger.exception("task_youtube_audio فشلت (vid_id=%s)", vid_id)
        await _safe_edit(bot, chat_id, status_message_id, "❌ فشل تحميل المقطع، حاول مرة أخرى.")
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


async def task_youtube_video(
    ctx: dict, *, chat_id: int, status_message_id: int, reply_to_message_id: int,
    url: str, vid_id: str, channel: str,
) -> None:
    bot: Client = ctx["bot"]
    job_dir = tempfile.mkdtemp(prefix="ytvideo_", dir=DOWNLOAD_DIR)
    try:
        ydl_opts = {
            "format": "best",
            "outtmpl": f"{job_dir}/%(id)s.%(ext)s",
            "noplaylist": True,
            "quiet": True,
            "geo_bypass": True,
        }
        info, filename = await asyncio.to_thread(_yt_extract, url, ydl_opts, True)
        duration = int(info.get("duration") or 0)
        if duration > MAX_DURATION_SECONDS:
            await _safe_edit(bot, chat_id, status_message_id, "فيديو اكثر من 25 دقيقة مقدر انزله")
            return

        duration_string = time.strftime("%M:%S", time.gmtime(duration))
        sent = await bot.send_video(
            chat_id,
            filename,
            duration=duration,
            caption=f"@{channel} ~ {duration_string} ⏳",
            reply_markup=_channel_button(channel),
            reply_to_message_id=reply_to_message_id,
        )
        await ytdb.set(
            f"ytvideoV{vid_id}",
            {"type": "video", "video": sent.video.file_id, "duration": sent.video.duration},
        )
        await _safe_delete(bot, chat_id, status_message_id)
    except Exception:
        logger.exception("task_youtube_video فشلت (vid_id=%s)", vid_id)
        await _safe_edit(bot, chat_id, status_message_id, "❌ فشل تحميل الفيديو، حاول مرة أخرى.")
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


async def task_tiktok_download(
    ctx: dict, *, chat_id: int, status_message_id: int, reply_to_message_id: int,
    url: str, channel: str,
) -> None:
    bot: Client = ctx["bot"]
    job_dir = tempfile.mkdtemp(prefix="tiktok_", dir=DOWNLOAD_DIR)
    try:
        ydl_opts = {
            "format": "best",
            "outtmpl": f"{job_dir}/%(id)s.%(ext)s",
            "quiet": True,
        }
        info, filename = await asyncio.to_thread(_yt_extract, url, ydl_opts, True)
        duration = int(info.get("duration") or 0)
        duration_string = time.strftime("%M:%S", time.gmtime(duration))
        title = info.get("fulltitle") or info.get("title") or ""
        uploader = info.get("uploader") or ""
        likes = info.get("like_count") or 0
        comments = info.get("comment_count") or 0
        views = info.get("view_count") or 0
        caption = (
            f"`{title}`\n{channel} طول المقطع : {duration_string}\n"
            f"👁 المشاهدات : {views:,}\n❤️ اللايكات : {likes:,}\n💬 الكومنت : {comments:,}\n\n"
            f"~ @{channel}"
        )
        uploader_url = info.get("uploader_url") or info.get("webpage_url") or url
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(f"@{uploader}", url=uploader_url)]])
        await bot.send_video(
            chat_id, filename, caption=caption, reply_markup=reply_markup,
            reply_to_message_id=reply_to_message_id,
        )
        await _safe_delete(bot, chat_id, status_message_id)
    except Exception:
        logger.exception("task_tiktok_download فشلت (url=%s)", url)
        await _safe_edit(bot, chat_id, status_message_id, "❌ فشل تحميل المقطع، تأكد من الرابط.")
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


async def task_soundcloud_audio(
    ctx: dict, *, chat_id: int, status_message_id: int, reply_to_message_id: int,
    url: str, channel: str, track_key: str,
) -> None:
    bot: Client = ctx["bot"]
    job_dir = tempfile.mkdtemp(prefix="sc_audio_", dir=DOWNLOAD_DIR)
    try:
        ydl_opts = {"outtmpl": f"{job_dir}/%(id)s.%(ext)s", "quiet": True}
        info, filename = await asyncio.to_thread(_yt_extract, url, ydl_opts, True)
        duration = int(info.get("duration") or 0)
        if duration > MAX_DURATION_SECONDS:
            await _safe_edit(bot, chat_id, status_message_id, "مقطع اكثر من ٢٥ دقيقة مقدر انزله")
            return
        sent = await bot.send_audio(
            chat_id, filename, title=info.get("title"), performer=f"@{channel}",
            duration=duration, reply_to_message_id=reply_to_message_id,
        )
        await sounddb.set(f"{track_key}:sound", sent.audio.file_id)
        await _safe_delete(bot, chat_id, status_message_id)
    except Exception:
        logger.exception("task_soundcloud_audio فشلت (url=%s)", url)
        await _safe_edit(bot, chat_id, status_message_id, "❌ فشل تحميل الصوت، حاول مرة أخرى.")
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


async def task_soundcloud_voice(
    ctx: dict, *, chat_id: int, status_message_id: int, reply_to_message_id: int,
    url: str, channel: str, track_key: str,
) -> None:
    """يحمّل من ساوند كلاود ثم يحوّل لصيغة voice (ogg/opus) عبر ffmpeg.

    هذه هي نقطة الاستبدال الأساسية لِـ:
        os.system(f'ffmpeg -i {mp3} -ac 1 -strict -2 -codec:a libopus -b:a 128k -vbr off -ar 24000 {ogg}')
    بواسطة asyncio.create_subprocess_exec عبر _run_ffmpeg (بنفس الوسائط تماماً).
    """
    bot: Client = ctx["bot"]
    job_dir = tempfile.mkdtemp(prefix="sc_voice_", dir=DOWNLOAD_DIR)
    try:
        ydl_opts = {"outtmpl": f"{job_dir}/%(id)s.%(ext)s", "quiet": True}
        info, filename = await asyncio.to_thread(_yt_extract, url, ydl_opts, True)
        duration = int(info.get("duration") or 0)
        if duration > MAX_DURATION_SECONDS:
            await _safe_edit(bot, chat_id, status_message_id, "مقطع اكثر من ٢٥ دقيقة مقدر انزله")
            return

        ogg_path = os.path.join(job_dir, f"{info['id']}.ogg")
        await _run_ffmpeg(
            "-i", filename,
            "-ac", "1", "-strict", "-2",
            "-codec:a", "libopus", "-b:a", "128k", "-vbr", "off", "-ar", "24000",
            ogg_path,
        )
        sent = await bot.send_voice(chat_id, ogg_path, reply_to_message_id=reply_to_message_id)
        await sounddb.set(f"{track_key}:soundVoice", sent.voice.file_id)
        await _safe_delete(bot, chat_id, status_message_id)
    except Exception:
        logger.exception("task_soundcloud_voice فشلت (url=%s)", url)
        await _safe_edit(bot, chat_id, status_message_id, "❌ فشل تحويل المقطع، حاول مرة أخرى.")
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


async def task_shazam_recognize(
    ctx: dict, *, chat_id: int, status_message_id: int, reply_to_message_id: int,
    file_id: str, channel: str,
) -> None:
    bot: Client = ctx["bot"]
    job_dir = tempfile.mkdtemp(prefix="shazam_", dir=DOWNLOAD_DIR)
    try:
        from shazamio import Shazam
        audio_path = os.path.join(job_dir, "audio.ogg")
        await bot.download_media(file_id, file_name=audio_path)

        shazam = Shazam()
        out = await shazam.recognize_song(audio_path)

        if not out.get("matches"):
            await _safe_edit(bot, chat_id, status_message_id, "فشل بالتعرف على الصوت")
            return

        title = out["track"]["title"]
        author = out["track"]["subtitle"]
        track_url = out["track"]["url"]
        try:
            photo = out["track"]["images"]["background"]
        except Exception:
            photo = "https://telegra.ph/file/49ace69e7c43c0041fb63.jpg"

        k = await rdb.get(f"{config.Dev_Zaid}:botkey") or "🧚‍♀️"
        text = f"{k} اسم الصوت ( [{title}]({track_url}) )\n{k} اسم الفنان : {author}"
        await bot.send_photo(
            chat_id, photo, caption=text, reply_markup=_channel_button(channel),
            reply_to_message_id=reply_to_message_id,
        )
        await _safe_delete(bot, chat_id, status_message_id)
    except Exception:
        logger.exception("task_shazam_recognize فشلت")
        await _safe_edit(bot, chat_id, status_message_id, "❌ فشل التعرف على الصوت.")
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


# ============================================================
# دورة حياة الـ worker (عميل Pyrogram مستقل خاص بإرسال/تعديل الرسائل)
# ============================================================
async def _on_startup(ctx: dict) -> None:
    bot = Client(
        name=f"{config.Dev_Zaid}worker",
        api_id=config.api_id,
        api_hash=config.api_hash,
        bot_token=config.token,
        in_memory=True,
    )
    await bot.start()
    ctx["bot"] = bot
    logger.info("Worker: تم تشغيل عميل Pyrogram الخاص بالمهام الخلفية.")


async def _on_shutdown(ctx: dict) -> None:
    bot: Optional[Client] = ctx.get("bot")
    if bot is not None:
        await bot.stop()
    logger.info("Worker: تم إيقاف عميل Pyrogram الخاص بالمهام الخلفية.")


class WorkerSettings:
    """إعدادات arq — تُشغَّل عبر: arq core.worker.WorkerSettings"""
    functions = [
        task_youtube_audio,
        task_youtube_video,
        task_tiktok_download,
        task_soundcloud_audio,
        task_soundcloud_voice,
        task_shazam_recognize,
    ]
    on_startup = _on_startup
    on_shutdown = _on_shutdown
    redis_settings = REDIS_SETTINGS
    max_jobs = 5
    job_timeout = 600  # 10 دقائق كحد أقصى لأي مهمة تحميل/تحويل
    keep_result = 300
