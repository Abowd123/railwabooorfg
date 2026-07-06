"""
core/calls_engine.py — bmqa-v2
محرك المكالمات الصوتية.

يربط:
  - PyTgCalls  (تشغيل الصوت/الفيديو في المكالمات)
  - core.youtube_calls → get_stream_source()  (تنزيل المقاطع)
  - core.calls_db  (حفظ الحالة وقائمة الانتظار في Redis)
  - core.assistant  (الحساب المساعد المطلوب للانضمام)
"""

from __future__ import annotations

import logging
import os

import config
from core import calls_db
from core.youtube_calls import get_stream_source

from pytgcalls import PyTgCalls, exceptions
from pytgcalls.types import (
    AudioQuality,
    GroupCallConfig,
    MediaStream,
    StreamEnded,
    VideoQuality,
)

# استيراد استثناءات ntgcalls مع fallback آمن لتجنب الفشل عند الاستيراد
try:
    from ntgcalls import ConnectionNotFound, RTMPStreamingUnsupported, TelegramServerError
    from ntgcalls import ConnectionError as NtgConnectionError
except ImportError:
    ConnectionNotFound = Exception          # type: ignore[assignment,misc]
    RTMPStreamingUnsupported = Exception    # type: ignore[assignment,misc]
    TelegramServerError = Exception         # type: ignore[assignment,misc]
    NtgConnectionError = Exception          # type: ignore[assignment,misc]

logger = logging.getLogger("bmqa.calls_engine")


class VoiceCallEngine(PyTgCalls):
    """
    محرك المكالمات الصوتية — Singleton يُهيَّأ في start().
    """

    def __init__(self) -> None:
        self._engine_started: bool = False

    # ──────────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """
        يُهيّئ PyTgCalls بالحساب المساعد ثم يبدأ التشغيل.
        """
        from core.assistant import assistant as _assistant

        if _assistant is None:
            raise RuntimeError(
                "الحساب المساعد غير متاح — تأكد من ضبط ASSISTANT_SESSION في .env"
            )

        super().__init__(_assistant)
        await super().start()

        # تسجيل معالج StreamEnded
        self._register_handlers()

        self._engine_started = True
        logger.info("VoiceCallEngine بدأ التشغيل بنجاح.")

    async def stop_engine(self) -> None:
        if not self._engine_started:
            return
        try:
            _stop = getattr(super(), "stop", None)
            if callable(_stop):
                await _stop()
        except Exception:
            pass
        finally:
            self._engine_started = False
            logger.info("VoiceCallEngine توقف.")

    # ──────────────────────────────────────────────────────────────────────────
    # معالج أحداث نهاية التشغيل
    # ──────────────────────────────────────────────────────────────────────────

    def _register_handlers(self) -> None:
        @self.on_update()
        async def _on_stream_ended(_, update) -> None:
            if isinstance(update, StreamEnded):
                if update.stream_type == StreamEnded.Type.AUDIO:
                    logger.debug(
                        "StreamEnded في chat_id=%d — تشغيل التالي.", update.chat_id
                    )
                    await self.play_next(update.chat_id)

    # ──────────────────────────────────────────────────────────────────────────
    # التشغيل
    # ──────────────────────────────────────────────────────────────────────────

    async def join_and_play(
        self,
        chat_id: int,
        video_id: str,
        requested_by_message,       # pyrogram.types.Message | None
        audio_only: bool = True,
    ) -> None:
        """
        يُنزّل المقطع عبر ArtistBots API ثم يشغّله بشكل ديناميكي بالاعتماد على مسار الملف الراجع.
        """
        # ── 1. تنزيل الملف واعتماد المسار الحقيقي الحقيقي الراجع من الـ API ──
        try:
            file_path = await get_stream_source(video_id, audio_only=audio_only)
            
            # حماية إضافية: التحقق من وجود الملف فعلياً على السيرفر قبل التمرير لـ pytgcalls
            if not file_path or not os.path.exists(file_path):
                raise RuntimeError(f"الملف المحمل غير موجود في المسار المتوقع: {file_path}")
                
        except ValueError:
            raise
        except RuntimeError:
            raise

        # ── 2. تحديد نوع البث ────────────────────────────────────────────────
        use_video = (not audio_only) and config.VC_VIDEO_ENABLED

        # ── 3. بناء MediaStream بالاعتماد على file_path الديناميكي ─────────────
        stream = MediaStream(
            media_path=file_path,
            audio_parameters=AudioQuality.HIGH,
            video_parameters=VideoQuality.HD_720p,
            audio_flags=MediaStream.Flags.REQUIRED,
            video_flags=(
                MediaStream.Flags.AUTO_DETECT
                if use_video
                else MediaStream.Flags.IGNORE
            ),
        )

        # ── 4. التشغيل مع معالجة الأخطاء المتوافقة مع PyTgCalls v2+ ──────────
        try:
            await self.play(
                chat_id=chat_id,
                stream=stream,
                config=GroupCallConfig(auto_start=False),
            )
        except exceptions.NoActiveGroupCall:
            logger.warning("join_and_play [%d]: لا توجد مكالمة صوتية نشطة.", chat_id)
            raise RuntimeError("لا توجد مكالمة صوتية نشطة في المجموعة.")
        except (exceptions.AlreadyJoined, AttributeError, Exception) as e:
            # تم صيد AlreadyJoined بشكل متوافق وفي حال تغير الاسم نلتقط الاستثناء بمرونة
            if "AlreadyJoined" in type(e).__name__ or "already" in str(e).lower():
                logger.warning("join_and_play [%d]: الحساب المساعد منضم مسبقاً.", chat_id)
                raise RuntimeError("الحساب المساعد منضم للمكالمة مسبقاً.")
            
            if isinstance(e, (NtgConnectionError, ConnectionNotFound, TelegramServerError)):
                logger.error("join_and_play [%d]: خطأ في الاتصال بخوادم تيليغرام.", chat_id)
                raise RuntimeError("فشل الاتصال بخوادم تيليغرام أثناء التشغيل.")
            
            if "RTMPStreamingUnsupported" in type(e).__name__:
                logger.error("join_and_play [%d]: RTMP غير مدعوم.", chat_id)
                raise RuntimeError("نوع المكالمة غير مدعوم (RTMP).")
                
            logger.error("خطأ غير متوقع أثناء تشغيل المكالمة: %s", e, exc_info=True)
            raise RuntimeError(f"فشل تشغيل الصوت داخل المكالمة: {e}")

        # ── 5. تحديث Redis ───────────────────────────────────────────────────
        await calls_db.set_active_call(chat_id, video=use_video)
        logger.info(
            "join_and_play ✓ chat_id=%d video_id=%s video=%s",
            chat_id, video_id, use_video,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # التحكم في التشغيل
    # ──────────────────────────────────────────────────────────────────────────

    async def pause(self, chat_id: int) -> None:  # type: ignore[override]
        try:
            await super().pause(chat_id)
            await calls_db.set_paused(chat_id, True)
            logger.debug("pause ✓ chat_id=%d", chat_id)
        except exceptions.NoActiveGroupCall:
            logger.warning("pause [%d]: لا توجد مكالمة نشطة.", chat_id)
        except Exception:
            logger.error("pause [%d]: خطأ غير متوقع.", chat_id)

    async def resume(self, chat_id: int) -> None:  # type: ignore[override]
        try:
            await super().resume(chat_id)
            await calls_db.set_paused(chat_id, False)
            logger.debug("resume ✓ chat_id=%d", chat_id)
        except exceptions.NoActiveGroupCall:
            logger.warning("resume [%d]: لا توجد مكالمة نشطة.", chat_id)
        except Exception:
            logger.error("resume [%d]: خطأ غير متوقع.", chat_id)

    async def stop(self, chat_id: int) -> None:  # type: ignore[override]
        await calls_db.remove_active_call(chat_id)
        try:
            await self.leave_call(chat_id)
            logger.debug("stop ✓ chat_id=%d", chat_id)
        except exceptions.NoActiveGroupCall:
            logger.debug("stop [%d]: لم تكن هناك مكالمة نشطة.", chat_id)
        except Exception:
            logger.error("stop [%d]: خطأ أثناء المغادرة.", chat_id)

    # ──────────────────────────────────────────────────────────────────────────
    # قائمة الانتظار
    # ──────────────────────────────────────────────────────────────────────────

    async def play_next(self, chat_id: int) -> None:
        item = await calls_db.queue_pop_next(chat_id)

        if item is None:
            logger.info("play_next [%d]: قائمة فارغة، مغادرة المكالمة.", chat_id)
            await self.stop(chat_id)
            return

        video_id   = item.get("video_id", "")
        audio_only = not item.get("video", False)

        if not video_id:
            logger.warning("play_next [%d]: عنصر بدون video_id، تخطّي.", chat_id)
            await self.play_next(chat_id)
            return

        try:
            await self.join_and_play(chat_id, video_id, None, audio_only=audio_only)
        except Exception:
            logger.error(
                "play_next [%d]: فشل تشغيل '%s' — إيقاف المكالمة.",
                chat_id, video_id,
            )
            await self.stop(chat_id)


# ─────────────────────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────────────────────
engine = VoiceCallEngine()
