"""
set_ranks.py — تم تقسيم هذا الملف إلى ملفين منطقيين تحت Plugins/ranks/:

  Plugins/ranks/set_promote.py  — أوامر الرفع  (group=7)
  Plugins/ranks/set_demote.py   — أوامر التنزيل (group=8)

سبب التقسيم: الملف الأصلي (1263 سطر) يحتوي على handler رفع (group=7)
وهاندلر تنزيل (group=8) لا يشتركان في أي منطق مباشر مع بعض. فصلهما
يُقلل حجم كل ملف إلى ~400 سطر ويجعل الصيانة أوضح.

يستورد هذا الملف من الملفين الفرعيين ليُبقى التحميل التلقائي للبوت
يعمل لو كان يبحث عن set_ranks.py تحديداً.
"""

from Plugins.ranks.set_promote import ranksCommandsHandler
from Plugins.ranks.set_demote import ranksCommandsHandlerDemote

__all__ = ['ranksCommandsHandler', 'ranksCommandsHandlerDemote']
