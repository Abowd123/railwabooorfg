"""
core/messages.py — bmqa-v2
طبقة موحّدة لإدارة نصوص ردود البوت مع دعم التخصيص (override) عبر Redis.

الفكرة:
  - كل رسالة لها معرّف ثابت (message_id) ونص افتراضي في DEFAULT_MESSAGES.
  - يمكن لأي مشرف/مطوّر استبدال النص الافتراضي بنص مخصّص يُحفظ في Redis،
    شرط أن يستخدم النص المخصّص نفس أسماء الـ placeholders الأصلية فقط (أو جزءاً منها).
  - get_message تقرأ الـ override إن وُجد وإلا ترجع للنص الافتراضي، ثم تُنسّقه.

هذا الملف يمثّل فقط الطبقة البرمجية الأساسية (core layer) — بلا أي أوامر
Telegram أو Plugins مرتبطة به في هذه المرحلة.
"""

from __future__ import annotations

import string

from core.db import rdb
from core.keys import message_override_key, sent_message_key

# ══════════════════════════════════════════════════════════════════════════════
# DEFAULT_MESSAGES
#
# Placeholders الموحَّدة عبر كل الرسائل:
#   {botkey}      — توقيع/مفتاح البوت (يظهر في أول السطر وقبل الفعل)
#   {mention}     — منشن العضو الذي نفّذ الأمر
#   {feature}     — اسم الميزة المعنيّة ("الشات"، "الفيديو"، ...)
#   {count}       — عدد (أوامر / ردود مسحت)
#   {command}     — نص الأمر المخصص
#   {command_old} — نص الأمر القديم قبل التغيير
#   {command_new} — نص الأمر الجديد بعد التغيير
#   {filter_name} — اسم/كلمة الفلتر أو الرد المخصص
#   {by_id}       — معرّف (ID) صاحب الرد في تاريخ الإضافة
#   {date}        — تاريخ ووقت الإضافة
#   {filter_type} — نوع محتوى الرد (نص / صوره / فيديو / ...)
#
# قواعد تسمية المعرّفات:
#   "اسم_الوحدة.وصف_قصير" — الوحدة هي مصدر الرسالة (locks، custom_command، ...)
#   كل موضع استخدام مستقل منطقياً يأخذ معرّفه الخاص، حتى لو تكرر النص حرفياً.
# ══════════════════════════════════════════════════════════════════════════════

DEFAULT_MESSAGES: dict[str, str] = {

    # ── إرث مرحلة 1 (lock_chat / unlock_chat) — محفوظان للتوافق ─────────────
    # من قالب lock — يُستخدم عند تنفيذ أمر "قفل الشات"
    "lock_chat": """
{botkey} من 「 {mention} 」
{botkey} ابشر قفلت {feature}
☆
""",
    # من قالب Open — يُستخدم عند تنفيذ أمر "فتح الشات"
    "unlock_chat": """
{botkey} من 「 {mention} 」
{botkey} ابشر فتحت {feature}
☆
""",
    # من قالب lock_edit — لمعرّف مستقل (أمر "قفل التعديل")
    "lock_edit": """
{botkey} من 「 {mention} 」
{botkey} ابشر قفلت {feature}
☆
""",

    # ── locks.chat_locked / locks.chat_opened — مربوطان فعلياً في _lock_toggle ─
    # (يُستخدَمان لكل أزواج القفل/الفتح الناجح عبر جداول _LOCK_TABLE_1/2)
    "locks.chat_locked": """
{botkey} من 「 {mention} 」
{botkey} ابشر قفلت {feature}
☆
""",
    "locks.chat_opened": """
{botkey} من 「 {mention} 」
{botkey} ابشر فتحت {feature}
☆
""",

    # ══════════════════════════════════════════════════════════════════════════
    # locks.* — رسائل _lock_toggle (all_locks_1.py + all_locks_2.py)
    # ══════════════════════════════════════════════════════════════════════════

    "locks.perm_mod": "{botkey} هذا الامر يخص ( المدير وفوق ) بس",
    "locks.perm_owner": "{botkey} هذا الامر يخص ( المالك وفوق ) بس",

    "locks.already_locked_m": """
{botkey} من 「 {mention} 」
{botkey} {feature} مقفل من قبل
☆
""",
    "locks.already_locked_f": """
{botkey} من 「 {mention} 」
{botkey} {feature} مقفله من قبل
☆
""",
    "locks.already_unlocked_m": """
{botkey} من 「 {mention} 」
{botkey} {feature} مفتوح من قبل
☆
""",
    "locks.already_unlocked_f": """
{botkey} من 「 {mention} 」
{botkey} {feature} مفتوحه من قبل
☆
""",

    # ── حالات خاصة بـ "فتح الإباحي" في all_locks_2.py (خارج _lock_toggle) ──
    "locks.nsfw_open_perm": "{botkey} هذا الامر يخص ( المالك وفوق ) بس",
    "locks.nsfw_already_unlocked": """
{botkey} من 「 {mention} 」
{botkey} االإباحي مفتوح من قبل
☆
""",
    "locks.nsfw_unlocked": """
{botkey} من 「 {mention} 」
{botkey} ابشر فتحت الإباحي
☆
""",

    # ══════════════════════════════════════════════════════════════════════════
    # protection.* — رسائل all_protection.py
    # ══════════════════════════════════════════════════════════════════════════

    "protection.perm_mod": "{botkey} هذا الامر يخص ( المدير وفوق ) بس",
    "protection.perm_owner": "{botkey} هذا الامر يخص ( المالك وفوق ) بس",
    "protection.lock_all_already": (
        "{botkey} من 「 {mention} 」 \n{botkey} كل شي مقفل يا حلو!\n☆"
    ),
    "protection.lock_all_success": (
        "{botkey} من 「 {mention} 」 \n{botkey} ابشر قفلت كل شي\n☆"
    ),
    "protection.unlock_all_already": (
        "{botkey} من 「 {mention} 」 \n{botkey} كل شي مفتوح يا حلو!\n☆"
    ),
    "protection.unlock_all_success": (
        "{botkey} من 「 {mention} 」 \n{botkey} ابشر فتحت كل شي\n☆"
    ),
    "protection.enable_already": (
        "{botkey} من 「 {mention} 」 \n{botkey} الحماية مفعله من قبل\n☆"
    ),
    "protection.enable_success": (
        "{botkey} من 「 {mention} 」 \n{botkey} ابشر فعلت الحمايه\n☆"
    ),
    "protection.disable_already": (
        "{botkey} من 「 {mention} 」 \n{botkey} الحماية معطله من قبل\n☆"
    ),
    "protection.disable_success": (
        "{botkey} من 「 {mention} 」 \n{botkey} ابشر عطلت الحمايه\n☆"
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # custom_command.* — رسائل Plugins/custom_command.py
    # الأوامر/الفلاتر المخصصة المحلية (داخل المجموعة)
    # ══════════════════════════════════════════════════════════════════════════

    # إلغاء إضافة أمر محلي (حالتا addCustom و addCustom2)
    "custom_command.cancel_add": "{botkey} من عيوني لغيت اضافة امر ",

    # رفض الصلاحية: مستوى المالك — عرض الأوامر المضافة + إضافة أمر
    "custom_command.perm_owner": "{botkey} هذا الامر يخص ( المالك وفوق ) وبس",

    # لا توجد أوامر مضافة — يُستخدم في العرض وفي مسح الكل
    "custom_command.no_commands": "{botkey} مافيه اوامر مضافه",

    # طلب إرسال الأمر القديم (الخطوة الأولى من إضافة/تغيير أمر)
    # مشترك بين المحلي والعام لأن المعنى واحد
    "custom_command.prompt_old_command": "{botkey} تمام عيني ، ارسل الامر القديم عشان اغيره",

    # تأكيد استلام الأمر القديم + طلب الأمر الجديد
    "custom_command.confirm_old_command": (
        "{botkey} حلو عشان تغيير امر ( {command} )\n{botkey} ارسل الامر الجديد الحين\n☆"
    ),

    # نجاح تغيير الأمر (القديم → الجديد)
    "custom_command.success_changed": (
        "{botkey} غيرت الامر القديم {command_old}\n{botkey} الى الامر الجديد ( {command_new} )"
    ),

    # إلغاء حذف أمر محلي
    "custom_command.cancel_del": "{botkey} من عيوني لغيت مسح امر ",

    # رفض الصلاحية: مستوى المدير — مسح الأوامر
    "custom_command.perm_mod": "{botkey} هذا الامر يخص ( المدير وفوق ) وبس",

    # نجاح مسح كل الأوامر المحلية
    "custom_command.success_clear_all": (
        "من「 {mention} 」\n{botkey} ابشر مسحت {count} أمر\n☆"
    ),

    # طلب إرسال الأمر المراد حذفه — مشترك بين المحلي والعام
    "custom_command.prompt_del": "{botkey} ارسل الامر الحين",

    # الأمر غير مضاف — مشترك بين المحلي والعام
    "custom_command.not_added": "{botkey} هذا الأمر مو مضاف",

    # نجاح حذف أمر محلي واحد
    "custom_command.success_del": (
        "{botkey} من「 {mention} 」\n{botkey} ابشر مسحت الأمر\n☆"
    ),

    # ── custom_command_global.* — الأوامر المخصصة العامة (بدون cid) ──────────

    # إلغاء إضافة أمر عام (حالتا addCustomG و addCustom2G)
    "custom_command_global.cancel_add": "{botkey} من عيوني لغيت اضف امر عام",

    # رفض الصلاحية: مستوى المطور — إدارة الأوامر العامة
    "custom_command_global.perm_dev": "{botkey} هذا الامر يخص ( المطور وفوق ) وبس",

    # لا توجد أوامر عامة مضافة
    "custom_command_global.no_commands": "{botkey} مافيه اوامر عامه مضافه",

    # إلغاء حذف أمر عام
    "custom_command_global.cancel_del": "{botkey} من عيوني لغيت مسح امر عام",

    # نجاح مسح كل الأوامر العامة
    "custom_command_global.success_clear_all": (
        "من「 {mention} 」\n{botkey} ابشر مسحت {count} أمر عام\n☆"
    ),

    # نجاح حذف أمر عام واحد
    "custom_command_global.success_del": (
        "{botkey} من「 {mention} 」\n{botkey} ابشر مسحت الأمر العام\n☆"
    ),

    # رفض الصلاحية: مستوى المالك الأساسي — إدارة الأوامر المقفولة
    "custom_command_global.perm_gowner": "{botkey} هذا الامر يخص ( المالك الاساسي وفوق ) وبس",

    # لا توجد أوامر مقفولة — يُستخدم في العرض وفي مسح الكل
    "custom_command_global.no_locked_commands": "{botkey} مافيه اوامر مقفولة",

    # نجاح مسح كل الأوامر المقفولة
    "custom_command_global.success_clear_locked": "{botkey} ابشر مسحت ( `{count}` )",

    # الأمر غير مقفول أصلاً (عند محاولة فتحه)
    "custom_command_global.not_locked": "{botkey} هذا الامر اصلاً مو مقفول",

    # نجاح فتح أمر مقفول
    "custom_command_global.success_unlock": "{botkey} ابشر فتحت الامر",

    # عرض لوحة اختيار الرتبة عند قفل أمر
    "custom_command_global.lock_prompt": (
        "{botkey} حسناً عزيزي اختار نوع الرتبه :\n{botkey} سيتم وضع امر ↤︎( {command} ) له فقط"
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # custom_filter.* — رسائل Plugins/custom_filter.py
    # الفلاتر/الردود المخصصة المحلية (داخل المجموعة)
    # ══════════════════════════════════════════════════════════════════════════

    # ── group=21 — addCustomReplyDone ────────────────────────────────────────

    # إلغاء إضافة رد محلي (نص "الغاء" أثناء انتظار الرد)
    "custom_filter.cancel_add_reply": "{botkey} من عيوني لغيت اضافة الرد",

    # نجاح حفظ رد محلي (لكل أنواع الوسائط: نص/صورة/فيديو/...)
    "custom_filter.reply_added": "{botkey} ( {filter_name} )\nضفنا الرد يا حلو\n☆",

    # ── group=22 — addCustomReply ────────────────────────────────────────────

    # إلغاء حذف رد محلي
    "custom_filter.cancel_del_reply": "{botkey} من عيوني لغيت مسح الرد",

    # الرد غير مضاف في قائمة الردود المحلية (عند محاولة حذفه)
    "custom_filter.not_in_list": "{botkey} هذا الرد مو مضاف في قائمة الردود",

    # نجاح حذف رد محلي واحد
    "custom_filter.reply_deleted": "( {filter_name} )\n{botkey} وحذفنا الرد ياحلو",

    # طلب إرسال محتوى الرد (بعد إرسال كلمة الفلتر) — يشرح أنواع الوسائط والـ placeholders
    "custom_filter.prompt_reply_content": (
        "{botkey} حلو الحين ارسل جواب الرد\n"
        "{botkey} ( نص,صوره,فيديو,متحركه,بصمه,صوت,ملف )\n"
        "ـــــــــــــــــــــــــــــــــــــــــ\n"
        "`<USER_ID>` › آيدي المستخدم\n"
        "`<USER_NAME>` › اسم المستخدم\n"
        "`<USER_USERNAME>` › يوزر المستخدم\n"
        "`<USER_MENTION>` › رابط حساب المستخدم\n"
        "༄"
    ),

    # معلومات رد محدد (كلمة الفلتر + تاريخ الإضافة + نوعه)
    "custom_filter.reply_info": (
        "{botkey} الرد ↢ [{filter_name}](tg://user?id={by_id})\n"
        "{botkey} تاريخ الاضافة ↢\n( {date} )\n"
        "{botkey} نوع الرد {filter_type}\n☆"
    ),

    # رفض الصلاحية: مستوى المدير — مشترك بين كل أوامر الفلاتر المحلية
    "custom_filter.perm_mod": "{botkey} هذا الأمر يخص ( المدير وفوق ) بس",

    # تعطيل الردود المحلية — كانت معطّلة مسبقاً
    "custom_filter.replies_disabled_already": (
        "{botkey} من「 {mention} 」\n{botkey} الردود معطله من قبل\n☆"
    ),

    # تعطيل الردود المحلية — نجاح
    "custom_filter.replies_disabled_success": (
        "{botkey} من「 {mention} 」\n{botkey} ابشر عطلت الردود\n☆"
    ),

    # تفعيل الردود المحلية — كانت مفعّلة مسبقاً
    "custom_filter.replies_enabled_already": (
        "{botkey} من「 {mention} 」\n{botkey} الردود مفعله من قبل\n☆"
    ),

    # تفعيل الردود المحلية — نجاح
    "custom_filter.replies_enabled_success": (
        "{botkey} من「 {mention} 」\n{botkey} ابشر فعلت الردود\n☆"
    ),

    # تعطيل ردود الأعضاء — كانت معطّلة مسبقاً
    "custom_filter.member_replies_disabled_already": (
        "{botkey} من「 {mention} 」\n{botkey} ردود الاعضاء معطله من قبل\n☆"
    ),

    # تعطيل ردود الأعضاء — نجاح
    "custom_filter.member_replies_disabled_success": (
        "{botkey} من「 {mention} 」\n{botkey} ابشر عطلت ردود الاعضاء\n☆"
    ),

    # تفعيل ردود الأعضاء — كانت مفعّلة مسبقاً
    "custom_filter.member_replies_enabled_already": (
        "{botkey} من「 {mention} 」\n{botkey} ردود الاعضاء مفعله من قبل\n☆"
    ),

    # تفعيل ردود الأعضاء — نجاح
    "custom_filter.member_replies_enabled_success": (
        "{botkey} من「 {mention} 」\n{botkey} ابشر فعلت ردود الاعضاء\n☆"
    ),

    # لا توجد ردود أعضاء مضافة — يُستخدم في العرض وفي مسح الكل
    "custom_filter.no_member_replies": "{botkey} مافيه ردود اعضاء مضافه",

    # نجاح مسح كل ردود الأعضاء
    "custom_filter.clear_member_replies_success": (
        "{botkey} ابشر مسحت ( `{count}` ) من ردود الاعضاء"
    ),

    # لا توجد ردود محلية مضافة — يُستخدم في العرض وفي مسح الكل
    "custom_filter.no_replies": "{botkey} مافيه ردود مضافه",

    # نجاح مسح كل الردود المحلية
    "custom_filter.clear_replies_success": (
        "{botkey} ابشر مسحت ( `{count}` ) من الردود"
    ),

    # رد "اضف ردي" عندما تكون ردود الأعضاء معطّلة
    "custom_filter.member_reply_disabled_error": "{botkey} تم تعطيل ردود الأعضاء",

    # العضو لديه رد مضاف مسبقاً
    "custom_filter.member_reply_already_added": (
        "{botkey} عندك رد مضاف من قبل و هو ( {filter_name} )"
    ),

    # طلب إرسال الاسم (بدء جلسة اضف ردي)
    "custom_filter.prompt_member_name": "{botkey} حلو ، الحين ارسل اسمك",

    # إلغاء إضافة رد العضو الخاص
    "custom_filter.cancel_member_add": "{botkey} ابشر لغيت اضافة ردك",

    # الاسم محجوز مسبقاً
    "custom_filter.name_reserved": "{botkey} هذا الإسم محجوز",

    # نجاح إضافة رد العضو الخاص
    "custom_filter.member_reply_added": "{botkey} ابشر ضفت ردك ( {filter_name} )",

    # العضو ليس لديه رد مضاف (مسح ردي)
    "custom_filter.no_own_reply": "{botkey} ماعندك رد",

    # نجاح حذف رد العضو الخاص
    "custom_filter.own_reply_deleted": "{botkey} ابشر مسحت ردك ( {filter_name} )",

    # طلب إرسال كلمة الفلتر (بدء جلسة اضف رد)
    "custom_filter.prompt_add_reply_word": "{botkey} حلو ، الحين ارسل الكلمة اللي تبيها",

    # طلب إرسال اسم الرد المراد حذفه — مشترك بين مسح رد ومسح رد مميز
    "custom_filter.prompt_del_reply": (
        "{botkey} تمام عيني\n{botkey} الحين ارسل الرد عشان امسحه\n☆"
    ),

    # ── group=23 — addCustomReplyRandom ─────────────────────────────────────

    # إلغاء إضافة رد مميز — الحالة الأولى (addFilterR)
    "custom_filter.cancel_add_random": "{botkey} من عيوني لغيت اضافة الرد المميز",

    # إلغاء إضافة رد مميز — الحالة الثانية (addFilterR2، نص أصلي مختلف الإملاء)
    "custom_filter.cancel_add_random_step2": "{botkey} من عيوني لغيت اضافه الرد المميز",

    # إلغاء حذف رد مميز
    "custom_filter.cancel_del_random": "{botkey} من عيوني لغيت مسح الرد المميز",

    # نجاح إضافة رد مميز مع عدد الأجوبة
    "custom_filter.random_reply_added": (
        "{botkey} تم اضافه الرد المميز ( {filter_name} )\n{botkey} بـ ( `{count}` ) جواب رد\n☆"
    ),

    # الرد المميز غير مضاف في القائمة (عند محاولة حذفه)
    "custom_filter.random_not_in_list": "{botkey} هذا الرد مو مضاف في قائمة الردود",

    # نجاح حذف رد مميز
    "custom_filter.random_reply_deleted": "{botkey} ابشر مسحت الرد العشوائي ",

    # طلب إرسال أجوبة الرد المميز (بعد إرسال الكلمة)
    "custom_filter.prompt_random_answers": (
        "{botkey} حلو الحين ارسل اجوبة الرد\n"
        "{botkey} بس تخلص ارسل تم\n"
        "ـــــــــــــــــــــــــــــــــــــــــ\n"
        "`<USER_ID>` › آيدي المستخدم\n"
        "`<USER_NAME>` › اسم المستخدم\n"
        "`<USER_USERNAME>` › يوزر المستخدم\n"
        "`<USER_MENTION>` › رابط حساب المستخدم\n"
        "༄"
    ),

    # تأكيد إضافة جواب واحد مع تذكير بإرسال "تم"
    "custom_filter.random_answer_added": (
        "{botkey} حلو ضفت هذا الرد\n"
        "{botkey} بس تخلص ارسل تم\n"
        "ـــــــــــــــــــــــــــــــــــــــــ\n"
        "`<USER_ID>` › آيدي المستخدم\n"
        "`<USER_NAME>` › اسم المستخدم\n"
        "`<USER_USERNAME>` › يوزر المستخدم\n"
        "`<USER_MENTION>` › رابط حساب المستخدم\n"
        "༄"
    ),

    # لا توجد ردود مميزة مضافة — يُستخدم في العرض وفي مسح الكل
    "custom_filter.no_random_replies": "{botkey} مافيه ردود عشوائيه مضافه",

    # نجاح مسح كل الردود المميزة
    "custom_filter.clear_random_success": (
        "{botkey} ابشر مسحت ( `{count}` ) رد مميز "
    ),

    # طلب إرسال كلمة الرد المميز (بدء جلسة اضف رد مميز)
    "custom_filter.prompt_add_random_word": "{botkey} حلو ، ارسل الحين الكلمة الي تبيها",

    # ══════════════════════════════════════════════════════════════════════════
    # global_filter.* — رسائل Plugins/global_filters.py
    # الفلاتر/الردود العامة (على مستوى البوت كله، بدون cid)
    # ══════════════════════════════════════════════════════════════════════════

    # ── group=24 — addCustomReplyG ───────────────────────────────────────────

    # إلغاء إضافة رد عام (حالتا addFilterG و state_key)
    "global_filter.cancel_add_reply": "{botkey} من عيوني لغيت اضافة الرد العام",

    # إلغاء حذف رد عام
    "global_filter.cancel_del_reply": "{botkey} من عيوني لغيت مسح الرد العام",

    # الرد غير مضاف في قائمة الردود العامة (عند محاولة حذفه)
    "global_filter.not_in_global_list": "{botkey} هذا الرد مو مضاف في قائمة الردود العامه",

    # نجاح حذف رد عام واحد
    "global_filter.reply_deleted": "( {filter_name} )\n{botkey} وحذفنا الرد ياحلو",

    # رفض الصلاحية: مستوى المالك — تعطيل/تفعيل ردود المطور
    "global_filter.perm_owner": "{botkey} هذا الأمر يخص ( المالك وفوق ) بس",

    # تعطيل ردود المطور — كانت معطّلة مسبقاً
    "global_filter.dev_replies_disabled_already": (
        "{botkey} من「 {mention} 」\n{botkey} ردود المطور معطله من قبل\n☆"
    ),

    # تعطيل ردود المطور — نجاح
    "global_filter.dev_replies_disabled_success": (
        "{botkey} من「 {mention} 」\n{botkey} ابشر عطلت ردود المطور\n☆"
    ),

    # تفعيل ردود المطور — كانت مفعّلة مسبقاً
    "global_filter.dev_replies_enabled_already": (
        "{botkey} من「 {mention} 」\n{botkey} ردود المطور مفعله من قبل\n☆"
    ),

    # تفعيل ردود المطور — نجاح
    "global_filter.dev_replies_enabled_success": (
        "{botkey} من「 {mention} 」\n{botkey} ابشر فعلت ردود المطور\n☆"
    ),

    # رفض الصلاحية: مستوى Dev²🎖️ — إدارة الردود العامة
    "global_filter.perm_dev2": "{botkey} هذا الأمر يخص ( Dev²🎖️ وفوق ) بس",

    # لا توجد ردود عامة مضافة — يُستخدم في العرض وفي مسح الكل
    "global_filter.no_global_replies": "{botkey} مافيه ردود عامه مضافه",

    # نجاح مسح كل الردود العامة
    "global_filter.clear_global_replies_success": (
        "{botkey} ابشر مسحت ( `{count}` ) من الردود العامه"
    ),

    # طلب إرسال اسم الرد المراد حذفه — للفلاتر العامة (مسح رد عام)
    "global_filter.prompt_del_reply": (
        "{botkey} تمام عيني\n{botkey} الحين ارسل الرد عشان امسحه\n☆"
    ),

    # طلب إرسال كلمة الفلتر العام (بدء جلسة اضف رد عام)
    "global_filter.prompt_add_reply_word": "{botkey} حلو ، الحين ارسل الكلمة اللي تبيها",

    # نجاح حفظ رد عام (لكل أنواع الوسائط)
    "global_filter.reply_added": "{botkey} ( {filter_name} )\nضفنا الرد العام يا حلو\n☆",

    # طلب إرسال محتوى الرد العام (بعد إرسال كلمة الفلتر)
    "global_filter.prompt_reply_content": (
        "{botkey} حلو الحين ارسل جواب الرد\n"
        "{botkey} ( نص,صوره,فيديو,متحركه,بصمه,صوت,ملف )\n"
        "ـــــــــــــــــــــــــــــــــــــــــ\n"
        "`<USER_ID>` › آيدي المستخدم\n"
        "`<USER_NAME>` › اسم المستخدم\n"
        "`<USER_USERNAME>` › يوزر المستخدم\n"
        "`<USER_MENTION>` › رابط حساب المستخدم\n"
        "༄"
    ),

    # ── group=26 — addCustomReplyRandomG ─────────────────────────────────────

    # إلغاء إضافة رد متعدد عام — الحالة الأولى (addFilterRG)
    "global_filter.cancel_add_random": "{botkey} من عيوني لغيت اضافة الرد المتعدد عام",

    # إلغاء إضافة رد متعدد عام — الحالة الثانية (addFilterRG2، نص أصلي مختلف الإملاء)
    "global_filter.cancel_add_random_step2": "{botkey} من عيوني لغيت اضافه الرد المتعدد عام",

    # إلغاء حذف رد متعدد عام
    "global_filter.cancel_del_random": "{botkey} من عيوني لغيت مسح الرد المتعدد العام",

    # نجاح إضافة رد متعدد عام مع عدد الأجوبة
    "global_filter.random_reply_added": (
        "{botkey} تم اضافه الرد المتعدد ( {filter_name} )\n{botkey} بـ ( `{count}` ) جواب رد\n☆"
    ),

    # الرد المتعدد العام غير مضاف في القائمة
    "global_filter.random_not_in_list": "{botkey} هذا الرد مو مضاف في قائمة الردود",

    # نجاح حذف رد متعدد عام
    "global_filter.random_reply_deleted": "{botkey} ابشر مسحت الرد المتعدد ",

    # طلب إرسال أجوبة الرد المتعدد العام (بعد إرسال الكلمة)
    "global_filter.prompt_random_answers": (
        "{botkey} حلو الحين ارسل اجوبة الرد\n"
        "{botkey} بس تخلص ارسل تم\n"
        "ـــــــــــــــــــــــــــــــــــــــــ\n"
        "`<USER_ID>` › آيدي المستخدم\n"
        "`<USER_NAME>` › اسم المستخدم\n"
        "`<USER_USERNAME>` › يوزر المستخدم\n"
        "`<USER_MENTION>` › رابط حساب المستخدم\n"
        "༄"
    ),

    # تأكيد إضافة جواب متعدد عام مع تذكير بإرسال "تم"
    "global_filter.random_answer_added": (
        "{botkey} حلو ضفت هذا الرد\n"
        "{botkey} بس تخلص ارسل تم\n"
        "ـــــــــــــــــــــــــــــــــــــــــ\n"
        "`<USER_ID>` › آيدي المستخدم\n"
        "`<USER_NAME>` › اسم المستخدم\n"
        "`<USER_USERNAME>` › يوزر المستخدم\n"
        "`<USER_MENTION>` › رابط حساب المستخدم\n"
        "༄"
    ),

    # لا توجد ردود متعددة عامة مضافة — يُستخدم في العرض وفي مسح الكل
    "global_filter.no_random_replies": "{botkey} مافيه ردود عشوائيه عامة",

    # نجاح مسح كل الردود المتعددة العامة
    "global_filter.clear_random_success": (
        "{botkey} ابشر مسحت ( `{count}` ) رد متعدد "
    ),

    # طلب إرسال كلمة الرد المتعدد العام (بدء جلسة اضف رد متعدد عام)
    "global_filter.prompt_add_random_word": "{botkey} حلو ، ارسل الحين الكلمة الي تبيها",

    # طلب إرسال اسم الرد المتعدد المراد حذفه (مسح رد متعدد عام)
    "global_filter.prompt_del_random": (
        "{botkey} تمام عيني\n{botkey} الحين ارسل الرد عشان امسحه\n☆"
    ),

    # ── group_update (تفعيل/تعطيل المجموعات + إشعارات الدخول/الخروج للمطورين) ──

    # للمجموعة: تعطيل تلقائي بسبب سحب صلاحية إدارية أو نقصانها
    "group_update.auto_disabled_group_notice": (
        "{botkey} من 「 {mention} 」\n"
        "{botkey} تم تعطيل خدمتي تلقائياً في هذه المجموعة لأن صلاحياتي كإدمن نقصت أو انسحبت\n"
        "{botkey} أرسل \"تفعيل\" بعد ما تعطيني كل الصلاحيات عشان أرجع أشتغل\n☆"
    ),

    # للمطورين: إشعار بسحب البوت من الإدارة في مجموعة (تعطيل تلقائي)
    "group_update.admin_removed_dev": (
        "{botkey} تم سحب صلاحية الإدمن مني في مجموعة\n"
        "{botkey} بواسطة : {mention} ( {target_username} | {target_id} )\n"
        "{botkey} المجموعة : {chat_title} ( {chat_username} | {chat_id} )\n"
        "{count_line}☆"
    ),

    # للمطورين: إشعار بنقصان صلاحيات الإدمن (تعطيل تلقائي)
    "group_update.admin_privileges_reduced_dev": (
        "{botkey} تم تقليل صلاحياتي الإدارية في مجموعة، عطّلت نفسي تلقائياً\n"
        "{botkey} بواسطة : {mention} ( {target_username} | {target_id} )\n"
        "{botkey} المجموعة : {chat_title} ( {chat_username} | {chat_id} )\n"
        "{count_line}☆"
    ),

    # الخدمة معطّلة عموماً من المطور (Global disable) — تُرسل للمجموعة
    "group_update.service_disabled_by_dev": (
        "{botkey} الخدمة معطّلة حالياً من المطور، حاول لاحقاً\n☆"
    ),

    # للمجموعة: تفعيل تلقائي بعد منح كل الصلاحيات المطلوبة
    "group_update.auto_enabled_group_notice": (
        "{botkey} من 「 {mention} 」\n"
        "{botkey} ابشر تفعّلت الخدمة تلقائياً في هذه المجموعة\n"
        "{botkey} اضغط الزر تحت عشان تشوف الأوامر\n☆"
    ),

    # للمطورين: إشعار بمجموعة جديدة انفعّلت (تلقائياً أو بالأمر)
    "group_update.new_group_enabled_dev": (
        "{botkey} انفعّلت مجموعة جديدة\n"
        "{botkey} بواسطة : {mention} ( {target_username} | {target_id} )\n"
        "{botkey} المجموعة : {chat_title} ( {chat_username} | {chat_id} )\n"
        "{count_line}☆"
    ),

    # رفض أمر "تفعيل" لأن المرسل مو مالك/إدمن ولا عنده صلاحية owner_pls
    "group_update.enable_denied_not_admin": (
        "هذا الأمر يخص ( المالك أو الإدمن ) بس"
    ),

    # المجموعة مفعّلة أصلاً
    "group_update.enable_already": "{botkey} الخدمة مفعّلة أصلاً في هذه المجموعة",

    # صلاحيات البوت ناقصة فما قدر يفعّل الخدمة
    "group_update.enable_missing_permissions": (
        "{botkey} عطني كل الصلاحيات الإدارية أولاً (حذف رسائل، تقييد أعضاء، تثبيت، دعوة) وبعدين أرسل \"تفعيل\""
    ),

    # نجاح تفعيل الخدمة بالأمر يدوياً
    "group_update.enable_success_group_notice": (
        "{botkey} من 「 {mention} 」\n"
        "{botkey} ابشر فعّلت الخدمة في هذه المجموعة\n"
        "{botkey} اضغط الزر تحت عشان تشوف الأوامر\n☆"
    ),

    # رفض أمر "تعطيل" لأن المرسل مو مالك/إدمن ولا عنده صلاحية owner_pls
    "group_update.disable_denied_not_admin": (
        "هذا الأمر يخص ( المالك أو الإدمن ) بس"
    ),

    # نجاح تعطيل الخدمة بالأمر يدوياً
    "group_update.disable_success_group_notice": (
        "{botkey} من 「 {mention} 」\n{botkey} ابشر عطّلت الخدمة في هذه المجموعة\n☆"
    ),

    # للمطورين: إشعار بتعطيل مجموعة بالأمر
    "group_update.group_disabled_dev": (
        "{botkey} تم تعطيل الخدمة في مجموعة\n"
        "{botkey} بواسطة : {mention} ( {target_username} | {target_id} )\n"
        "{botkey} المجموعة : {chat_title} ( {chat_username} | {chat_id} )\n"
        "{count_line}☆"
    ),

    # للمطورين: إشعار بمغادرة البوت مجموعة بأمر "اطلعي/اطلع" من المالك
    "group_update.left_group_by_command_dev": (
        "{botkey} طلعت من مجموعة بأمر من المالك\n"
        "{botkey} بواسطة : {mention} ( {target_username} | {target_id} )\n"
        "{botkey} المجموعة : {chat_title} ( {chat_username} | {chat_id} )\n"
        "{count_line}☆"
    ),

    # للمطورين: إشعار بطرد البوت من مجموعة (كيك)
    "group_update.bot_kicked_dev": (
        "{botkey} تم طردي من مجموعة\n"
        "{botkey} بواسطة : {mention} ( {target_username} | {target_id} )\n"
        "{botkey} المجموعة : {chat_title} ( {chat_username} | {chat_id} )\n"
        "{count_line}☆"
    ),
}


def _placeholders(template: str) -> set[str]:
    """يستخرج أسماء الـ placeholders الموجودة داخل نص .format() معيّن."""
    formatter = string.Formatter()
    return {
        field_name
        for _, field_name, _, _ in formatter.parse(template)
        if field_name
    }


async def get_message(message_id: str, **kwargs) -> str:
    """
    يرجع نص الرسالة الجاهز للاستخدام:
      1. يقرأ override من Redis إن وُجد.
      2. وإلا يستخدم DEFAULT_MESSAGES.
      3. ينسّق النص بالـ kwargs المُمرَّرة.
    """
    if message_id not in DEFAULT_MESSAGES:
        raise ValueError(f"message_id غير معروف: {message_id!r}")

    override = await rdb.get(message_override_key(message_id))
    template = override if override else DEFAULT_MESSAGES[message_id]
    return template.format(**kwargs)


async def set_message_override(message_id: str, new_text: str) -> None:
    """
    يحفظ نصاً مخصّصاً (override) لمعرّف رسالة معيّن في Redis، بعد التحقق أن
    كل الـ placeholders الموجودة في new_text معروفة ضمن القالب الأصلي لنفس
    المعرّف. يرفع ValueError إن وُجد placeholder غير معروف.
    """
    if message_id not in DEFAULT_MESSAGES:
        raise ValueError(f"message_id غير معروف: {message_id!r}")

    original_placeholders = _placeholders(DEFAULT_MESSAGES[message_id])
    new_placeholders = _placeholders(new_text)

    unknown = new_placeholders - original_placeholders
    if unknown:
        raise ValueError(
            f"placeholders غير معروفة لمعرّف {message_id!r}: {sorted(unknown)} "
            f"— المسموح به فقط: {sorted(original_placeholders)}"
        )

    await rdb.set(message_override_key(message_id), new_text)


async def reset_message(message_id: str) -> None:
    """يحذف الـ override الخاص بمعرّف رسالة معيّن من Redis، فيعود للنص الافتراضي."""
    if message_id not in DEFAULT_MESSAGES:
        raise ValueError(f"message_id غير معروف: {message_id!r}")

    await rdb.delete(message_override_key(message_id))


def list_message_ids() -> list[str]:
    """يرجع كل معرّفات الرسائل المتاحة (مفاتيح DEFAULT_MESSAGES)."""
    return list(DEFAULT_MESSAGES.keys())


# ══════════════════════════════════════════════════════════════════════════════
# تتبّع الرسائل المُرسَلة — ربط telegram_message_id بـ message_id
# ══════════════════════════════════════════════════════════════════════════════

async def track_sent_message(
    chat_id: int,
    telegram_message_id: int,
    message_id: str,
    ttl: int = 604800,
) -> None:
    """
    يخزن في Redis الرابط بين رسالة تيليغرام المُرسَلة (telegram_message_id)
    ومعرّف قالبها (message_id)، بمهلة TTL أسبوع (604800 ثانية) افتراضياً.

    المفتاح: sent_message_key(chat_id, telegram_message_id)
    القيمة: message_id  (مثال: "locks.chat_locked")

    الاستخدام:
        sent = await m.reply(text)
        await track_sent_message(m.chat.id, sent.id, "locks.chat_locked")
    """
    key = sent_message_key(chat_id, telegram_message_id)
    await rdb.set(key, message_id, ex=ttl)


async def get_tracked_message_id(
    chat_id: int,
    telegram_message_id: int,
) -> str | None:
    """
    يسترجع message_id المخزون لرسالة تيليغرام مُرسَلة سابقاً.
    يرجع None إن انتهت المهلة أو لم يُتتبَّع المعرّف أصلاً.

    الاستخدام:
        mid = await get_tracked_message_id(chat_id, sent_msg_id)
        # mid == "locks.chat_locked"  أو  None
    """
    key = sent_message_key(chat_id, telegram_message_id)
    return await rdb.get(key)
