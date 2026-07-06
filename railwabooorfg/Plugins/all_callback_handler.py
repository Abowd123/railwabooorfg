"""
all_callback_handler.py — bmqa-v2
═══════════════════════════════════════════════════════════════════════════════
يحلّ محلّ CallbackQueryHandler الأصلي (all.py سطر 3841–3847).

الأصل:
    @Client.on_callback_query(group=1)
    def CallbackQueryHandler(c, m):
        channel = r.get(...)
        Thread(target=CallbackQueryResponse, args=(c, m, channel)).start()

النسخة الجديدة:
  - تشغيل async مباشر بدل Thread.
  - التوجيه عبر core.callback_dispatcher.dispatch_callback() بدل
    استدعاء CallbackQueryResponse المونوليثية مباشرةً.
  - كل بيانات channel/k تُقرأ مباشرة من داخل كل معالج بدل تمريرها كـ arg.

⚠️ تأكد أن ملفات all_callback_help_menus.py و all_callback_games.py
   محمّلة قبل هذا الملف (يعتمد على تسجيلاتها في CALLBACK_HANDLERS).
   في Pyrogram هذا يحدث تلقائياً عند تحميل كل Plugins/ بالترتيب الأبجدي.
"""

from pyrogram import Client
from pyrogram.types import CallbackQuery

from core.errors import safe_handler
import core.callback_dispatcher as cb_dispatcher

import Plugins.all_callback_help_menus  # noqa: F401 — يسجّل معالجات قوائم المساعدة
import Plugins.all_callback_games       # noqa: F401 — يسجّل معالجات لعبة RPS


@Client.on_callback_query(group=1)
@safe_handler
async def callbackQueryHandler(c: Client, m: CallbackQuery) -> None:
    """
    بوابة كل الـ CallbackQuery.
    يوجّه m.data عبر CALLBACK_HANDLERS المسجَّل في core/callback_dispatcher.py.
    """
    if not m.data:
        return

    await cb_dispatcher.dispatch_callback(m.data, c, m)
