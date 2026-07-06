"""
core/youtube_calls.py — bmqa-v2
طبقة يوتيوب الخاصة بالبث في المكالمات الصوتية.

مسؤوليات هذا الملف:
  - البحث عبر yt-dlp (asyncio.to_thread).
  - استخراج video_id من رابط يوتيوب.
  - تنزيل الصوت/الفيديو عبر ArtistBots API مع Round Robin للمفاتيح.
  - تخزين مؤقت بسيط (الملف على القرص).
  - واجهة get_stream_source() لمحرك المكالمات.

لا يُعدّل هذا الملف Plugins/downloader.py ولا يتعارض معه.
كلاهما يستخدم yt-dlp لكن لأغراض مختلفة تماماً.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass

import aiohttp
import yt_dlp

import config

logger = logging.getLogger("bmqa.youtube_calls")

# ─────────────────────────────────────────────────────────────────────────────
# ثوابت
# ─────────────────────────────────────────────────────────────────────────────

_CHUNK_SIZE = 128 * 1024          # 128 KB لكل قطعة عند الكتابة على القرص
_DOWNLOADS_DIR = "downloads"

# Regex مأخوذ حرفياً من anony/core/youtube.py (YouTube class)
_YT_URL_RE = re.compile(
    r"(https?://)?(www\.|m\.|music\.)?"
    r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
    r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
)
# 11 حرفاً بالضبط = video ID خام
_YT_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")


# ─────────────────────────────────────────────────────────────────────────────
# بنية بيانات المقطع (بسيطة — 6 حقول فقط)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(slots=True)
class VideoInfo:
    video_id:      str
    title:         str
    duration:      int          # بالثواني
    thumbnail_url: str
    webpage_url:   str
    uploader:      str


# ─────────────────────────────────────────────────────────────────────────────
# حالة داخلية مشتركة (module-level Singletons — نمط core/db.py)
# ─────────────────────────────────────────────────────────────────────────────

_api_session: aiohttp.ClientSession | None = None
_api_session_lock: asyncio.Lock = asyncio.Lock()

_api_key_index: int = 0
_api_key_lock: asyncio.Lock = asyncio.Lock()


# ─────────────────────────────────────────────────────────────────────────────
# 1) استخراج Video ID
# ─────────────────────────────────────────────────────────────────────────────

def extract_video_id(link_or_query: str) -> str | None:
    """
    يستخرج الـ 11-char video ID من رابط يوتيوب.
    يعيد None إذا كان الإدخال نصاً عادياً لا رابطاً.

    المنطق (مأخوذ من anony/core/youtube.py → _extract_video_id):
      1. ID خام مكوّن من 11 حرفاً.
      2. رابط يحوي v=...
      3. رابط youtu.be/{id} أو shorts/{id}.
    """
    if not link_or_query:
        return None
    s = link_or_query.strip()

    # ID خام
    if _YT_ID_RE.match(s):
        return s

    # رابط مع معامل v=
    if "v=" in s:
        vid = s.split("v=")[-1].split("&")[0]
        if _YT_ID_RE.match(vid):
            return vid

    # /shorts/{id} أو youtu.be/{id}
    last = s.split("/")[-1].split("?")[0]
    if _YT_ID_RE.match(last):
        return last

    return None


# ─────────────────────────────────────────────────────────────────────────────
# 2) البحث عبر yt-dlp
# ─────────────────────────────────────────────────────────────────────────────

async def search(query: str, limit: int = 1) -> list[dict]:
    """
    يبحث في يوتيوب عبر yt-dlp ويعيد قائمة من القواميس.
    يُشغَّل في asyncio.to_thread حتى لا يُجمّد حلقة الأحداث
    (نفس الأسلوب المستخدم في Plugins/downloader.py → _search_youtube).

    الحقول المُعادة لكل نتيجة:
        video_id, title, duration (ثواني), thumbnail_url, webpage_url, uploader
    """

    def _run() -> list[dict]:
        opts = {
            "quiet": True,
            "extract_flat": "in_playlist",
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
        entries = info.get("entries") or []
        results = []
        for e in entries:
            results.append({
                "video_id":      e.get("id") or "",
                "title":         e.get("title") or "",
                "duration":      int(e.get("duration") or 0),
                "thumbnail_url": e.get("thumbnail") or "",
                "webpage_url":   e.get("url") or e.get("webpage_url") or "",
                "uploader":      e.get("uploader") or e.get("channel") or "",
            })
        return results

    try:
        return await asyncio.to_thread(_run)
    except Exception:
        logger.error("yt-dlp search فشل للاستعلام: %r", query, exc_info=True)
        return []


# ─────────────────────────────────────────────────────────────────────────────
# مساعدة داخلية: جلب معلومات مقطع بـ video_id (للتحقق من المدة)
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_info(video_id: str) -> dict | None:
    """يستخرج معلومات مقطع يوتيوب (بلا تحميل) عبر asyncio.to_thread."""
    url = f"https://www.youtube.com/watch?v={video_id}"

    def _run() -> dict | None:
        opts = {"quiet": True, "skip_download": True, "noplaylist": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                return ydl.extract_info(url, download=False)
            except Exception:
                return None

    try:
        return await asyncio.to_thread(_run)
    except Exception:
        logger.warning("_fetch_info فشل لـ %s", video_id, exc_info=True)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 3) طبقة ArtistBots
# ─────────────────────────────────────────────────────────────────────────────

async def _next_api_key() -> str | None:
    """
    Round Robin على config.API_KEYS.
    يعيد None إذا كانت القائمة فارغة.
    """
    keys = config.API_KEYS
    if not keys:
        return None
    global _api_key_index
    async with _api_key_lock:
        key = keys[_api_key_index % len(keys)]
        _api_key_index = (_api_key_index + 1) % len(keys)
        return key


async def _get_api_session() -> aiohttp.ClientSession:
    """
    يعيد ClientSession واحدة تُعاد استخدامها طوال عمر البرنامج.
    يستخدم Double-Checked Locking لمنع إنشاء أكثر من Session.
    (نفس النمط في anony/core/youtube.py → _get_api_session)
    """
    global _api_session
    if _api_session and not _api_session.closed:
        return _api_session
    async with _api_session_lock:
        if _api_session and not _api_session.closed:
            return _api_session
        timeout = aiohttp.ClientTimeout(total=600, sock_connect=20, sock_read=60)
        connector = aiohttp.TCPConnector(
            limit=0, ttl_dns_cache=300, enable_cleanup_closed=True
        )
        _api_session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return _api_session


async def close_api_session() -> None:
    """
    يغلق ClientSession الخاصة بـ ArtistBots عند إيقاف البوت.
    يُستدعى من main.py في finally بعد إيقاف محرك المكالمات والحساب المساعد.
    آمن الاستدعاء حتى لو لم تُنشأ الجلسة أصلاً (لا تزال None).
    """
    global _api_session
    if _api_session and not _api_session.closed:
        await _api_session.close()
        logger.info("ArtistBots ClientSession أُغلقت بنجاح.")
    _api_session = None


async def download_media(video_id: str, video: bool = False) -> str | None:
    """
    ينزّل الصوت أو الفيديو عبر ArtistBots API ويحفظه على القرص.

    Endpoint:
        GET {base_url}/download?url={video_id}&type={audio|video}&api_key={key}

    السلوك:
    - إذا API_URL أو API_KEYS غير مهيأة → تحذير + None فوراً.
    - إذا الملف موجود وحجمه > 0 → يعيد المسار مباشرة (تخزين مؤقت).
    - يُعيد المحاولة مرة واحدة عند الفشل.
    - يعيد None بدل رفع Exception في جميع حالات الفشل.
    """
    base_url = config.VIDEO_API_URL if video else config.API_URL

    if not base_url or not config.API_KEYS:
        logger.warning(
            "ArtistBots غير مهيأ — تحقق من %s و API_KEYS في .env",
            "VIDEO_API_URL" if video else "API_URL",
        )
        return None

    download_type = "video" if video else "audio"
    file_ext = ".mp4" if video else ".mp3"
    out_path = os.path.join(_DOWNLOADS_DIR, f"{video_id}{file_ext}")

    # تخزين مؤقت: إذا الملف موجود وغير فارغ لا نُعيد التنزيل
    os.makedirs(_DOWNLOADS_DIR, exist_ok=True)
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        logger.debug("مخزّن مؤقتاً: %s", out_path)
        return out_path

    api_key = await _next_api_key()
    if not api_key:
        logger.warning("ArtistBots غير مهيأ — لا توجد API_KEYS")
        return None

    params = {"url": video_id, "type": download_type, "api_key": api_key}
    masked = (api_key[:8] + "...") if len(api_key) > 8 else "***"
    endpoint = f"{base_url.rstrip('/')}/download"

    for attempt in range(2):
        try:
            session = await _get_api_session()
            logger.debug(
                "ArtistBots [%s] → %s (%s) محاولة %d",
                masked, endpoint, download_type, attempt + 1,
            )
            async with session.get(
                endpoint,
                params=params,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status != 200:
                    # لا return هنا — نتابع الحلقة للمحاولة التالية
                    logger.warning(
                        "ArtistBots أعاد HTTP %d لـ %s (مفتاح %s)",
                        resp.status, video_id, masked,
                    )
                else:
                    with open(out_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(_CHUNK_SIZE):
                            if chunk:
                                f.write(chunk)

                    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                        logger.info(
                            "تم التنزيل بنجاح عبر ArtistBots: %s (%s)",
                            video_id, download_type,
                        )
                        return out_path

                    # ملف فارغ — أزله ودع الحلقة تُعيد المحاولة
                    if os.path.exists(out_path):
                        os.remove(out_path)
                    logger.warning("ArtistBots أعاد ملفاً فارغاً لـ %s", video_id)

        except asyncio.TimeoutError:
            logger.error("ArtistBots timeout لـ %s (مفتاح %s)", video_id, masked)
        except aiohttp.ClientError as exc:
            logger.error("ArtistBots client error لـ %s: %s", video_id, exc)
        except Exception as exc:
            logger.error(
                "ArtistBots فشل غير متوقع لـ %s: %s: %s",
                video_id, type(exc).__name__, exc,
            )

        if attempt == 0:
            logger.info("إعادة المحاولة لـ ArtistBots: %s ...", video_id)

    return None


# ─────────────────────────────────────────────────────────────────────────────
# 4) واجهة محرك المكالمات
# ─────────────────────────────────────────────────────────────────────────────

async def get_stream_source(video_id: str, audio_only: bool = True) -> str:
    """
    واجهة المحرك الرئيسية — تُستدعى من plugin المكالمات لاحقاً.

    الخطوات:
      1. جلب معلومات المقطع عبر yt-dlp.
      2. التحقق من المدة مقابل config.VC_DURATION_LIMIT_MINUTES.
      3. استدعاء download_media().
      4. إعادة المسار المحلي.

    يرفع ValueError إذا تجاوز المقطع الحد الزمني.
    يرفع RuntimeError إذا فشل التنزيل نهائياً.
    """
    # --- التحقق من المدة ---
    info = await _fetch_info(video_id)
    if info:
        duration_sec: int = int(info.get("duration") or 0)
        limit_sec: int = config.VC_DURATION_LIMIT_MINUTES * 60
        if duration_sec > 0 and duration_sec > limit_sec:
            raise ValueError(
                f"مدة المقطع ({duration_sec // 60} دقيقة) تتجاوز الحد المسموح "
                f"({config.VC_DURATION_LIMIT_MINUTES} دقيقة). "
                f"يمكن تعديل الحد عبر VC_DURATION_LIMIT_MINUTES في .env"
            )

    # --- التنزيل ---
    path = await download_media(video_id, video=not audio_only)
    if path is None:
        raise RuntimeError(
            f"فشل تنزيل المقطع '{video_id}' — "
            "تحقق من إعدادات API_URL وAPI_KEYS في .env"
        )
    return path
