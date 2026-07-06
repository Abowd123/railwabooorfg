"""
all_callback_help_menus.py — bmqa-v2
═══════════════════════════════════════════════════════════════════════════════
Callbacks المُنقولة من CallbackQueryResponse (all.py سطر 3849–4659, 4775–4898):
  - قوائم المساعدة الثابتة: commands1:{uid} … commands8:{uid}
  - نظام التحقق: yes:{uid}, no:{uid}, yesVER:{uid}, noVER:{uid}
  - حذف رسالة الادمن: delAdminMSG
  - تصفير البنك: yes:del:bank, no:del:bank
  - توب الفلوس: topfloos:{uid}, topzrf:{uid}
  - صلاحيات الأقفال: gowner+{uid}, owner+{uid}, mod+{uid}, admin+{uid}, pre+{uid}

التحويلات عن الأصل (متزامن → غير متزامن):
  r.get/set/delete/keys  → await rdb.get/set/delete/keys
  r.smembers             → await rdb.smembers
  r.ttl                  → await rdb.ttl
  r.hset                 → await rdb.hset
  c.restrict_chat_member → await c.restrict_chat_member
  m.message.chat.ban_member / unban_member → await ...
  m.edit_message_text    → await m.edit_message_text
  m.answer               → await m.answer
  m.message.delete       → await m.message.delete
  Thread(target=…)       → await مباشرة (يُعالَج من callback_dispatcher)

⚠️ devp_pls غير موجود في helpers/ranks.py — استُبدل بـ dev2_pls (سلوك مكافئ).
"""

import logging
import time
import random

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions

from config import Dev_Zaid, botUsername
from core.db import rdb
from core.errors import safe_handler
from core.callback_dispatcher import register_callback
from helpers.ranks import admin_pls, gowner_pls, devp_pls

# ─── helpers مشتركة ────────────────────────────────────────────────────────

def _help_keyboard(uid: int, current: int) -> InlineKeyboardMarkup:
    """يبني لوحة المساعدة مع وضع علامة (‣) على الصفحة الحالية."""
    def _btn(label: str, page: int):
        if page == current:
            return InlineKeyboardButton(f"{label} ‣", callback_data="None")
        return InlineKeyboardButton(label, callback_data=f"commands{page}:{uid}")

    return InlineKeyboardMarkup([
        [_btn("م1", 1), _btn("م2", 2)],
        [_btn("م3", 3)],
        [_btn("الالعاب", 4), _btn("التسليه", 5)],
        [_btn("اليوتيوب", 6)],
        [_btn("البنك", 7), _btn("زواج", 8)],
    ])


def _get_top(users: list) -> list:
    return sorted(users, key=lambda x: x["money"], reverse=True)


def _emoji_bank(pos: int) -> str:
    emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
    return emojis.get(pos, f"{pos}.")


# ─── commands1 ─────────────────────────────────────────────────────────────

@register_callback("commands1:")
@safe_handler
async def _cmd1(c, m) -> None:
    if m.data != f"commands1:{m.from_user.id}":
        return
    channel = await rdb.get(f"{Dev_Zaid}:BotChannel") or "YQYQY6"
    await m.edit_message_text(
        f"""
للاستفسار - @{channel}


❨ اوامر الرفع والتنزيل ❩

⌯ رفع ↣ ↢ تنزيل مشرف
⌯ رفع ↣ ↢ تنزيل مالك اساسي
⌯ رفع ↣ ↢ تنزيل مالك
⌯ رفع ↣ ↢ تنزيل مدير
⌯ رفع ↣ ↢ تنزيل ادمن
⌯ رفع ↣ ↢ تنزيل مميز
⌯ تنزيل الكل  ↢ بالرد  ↢ لتنزيل الشخص من جميع رتبه
⌯ مسح الكل  ↢ بدون رد  ↢ لتنزيل كل رتب المجموعة

❨ اوامر المسح ❩

⌯ مسح المالكيين
⌯ مسح المدراء
⌯ مسح الادمنيه
⌯ مسح المميزين
⌯ مسح المحظورين
⌯ مسح المكتومين
⌯ مسح قائمة المنع
⌯ مسح رتبه
⌯ مسح الرتب
⌯ مسح الردود
⌯ مسح الاوامر
⌯ مسح + العدد
⌯ مسح بالرد
⌯ مسح الترحيب
⌯ مسح قائمة التثبيت

❨ اوامر الطرد الحظر الكتم ❩

⌯ حظر ↢ ❨ بالرد،بالمعرف،بالايدي ❩
⌯ طرد ↢ ❨ بالرد،بالمعرف،بالايدي ❩
⌯ كتم ↢ ❨ بالرد،بالمعرف،بالايدي ❩
⌯ تقيد ↢ ❨ بالرد،بالمعرف،بالايدي ❩
⌯ الغاء الحظر ↢ ❨ بالرد،بالمعرف،بالايدي ❩
⌯ الغاء الكتم ↢ ❨ بالرد،بالمعرف،بالايدي ❩
⌯ الغاء التقييد ↢ ❨ بالرد،بالمعرف،بالايدي ❩
⌯ رفع القيود ↢ لحذف الكتم,الحظر,التقييد
⌯ منع الكلمة
⌯ منع بالرد على قيف او ستيكر
⌯ الغاء منع الكلمة
⌯ طرد البوتات
⌯ كشف البوتات

❨ اوامر النطق ❩

⌯ انطقي + الكلمة
⌯ وش يقول؟ + بالرد على فويس لترجمه المحتوى

❨ اوامر اخرى ❩

⌯ الرابط
⌯ معلومات الرابط
⌯ انشاء رابط
⌯ بايو
⌯ بايو عشوائي
⌯ ايدي
⌯ الانشاء
⌯ مجموعاتي
⌯ ابلاغ
⌯ نقل ملكية
⌯ صوره
⌯ افتاري
⌯ افتار + باليوزر او الرد
⌯ مين ضافني؟
⌯ شازام، قرآن، سورة + اسم السورة
""",
        reply_markup=_help_keyboard(m.from_user.id, 1),
    )


# ─── commands2 ─────────────────────────────────────────────────────────────

@register_callback("commands2:")
@safe_handler
async def _cmd2(c, m) -> None:
    if m.data != f"commands2:{m.from_user.id}":
        return
    channel = await rdb.get(f"{Dev_Zaid}:BotChannel") or "YQYQY6"
    await m.edit_message_text(
        f"""
للاستفسار - @{channel}


❨ اوامر الوضع ❩

⌯ وضع ترحيب
⌯ وضع قوانين
⌯ تغيير رتبه
⌯ تغيير امر

❨ اوامر رؤية الاعدادات ❩

⌯ المطورين
⌯ المالكيين الاساسيين
⌯ المالكيين
⌯ الادمنيه
⌯ المدراء
⌯ المشرفين
⌯ المميزين
⌯ القوانين
⌯ قائمه المنع
⌯ المكتومين
⌯ المطور
⌯ معلوماتي
⌯ الاعدادت
⌯ المجموعه
⌯ الساعه
⌯ التاريخ
⌯ صلاحياتي
⌯ لقبي
⌯ صلاحياته + بالرد
""",
        reply_markup=_help_keyboard(m.from_user.id, 2),
    )


# ─── commands3 ─────────────────────────────────────────────────────────────

@register_callback("commands3:")
@safe_handler
async def _cmd3(c, m) -> None:
    if m.data != f"commands3:{m.from_user.id}":
        return
    channel = await rdb.get(f"{Dev_Zaid}:BotChannel") or "YQYQY6"
    await m.edit_message_text(
        f"""
للاستفسار - @{channel}


❨ اوامر الردود ❩

⌯ الردود ↢ تشوف كل الردود المضافه
⌯ الردود المتعدده ↢ تشوف كل الردود المتعدده المضافه
⌯ اضف رد ↢ عشان تضيف رد
⌯ اضف رد متعدد ↢ عشان تضيف أكثر من رد
⌯ اضف رد متعدد ↢ خاص بالاعضاء
⌯ مسح رد ↢ عشان تمسح الرد
⌯ مسح رد متعدد ↢ عشان تمسح رد متعدد
⌯ مسح ردي ↢ عشان تمسح ردك اذا كان بردود الأعضاء
⌯ مسح الردود ↢ تمسح كل الردود
⌯ مسح الردود المتعدده ↢ عشان تمسح كل الردود المتعدده
⌯ الرد + كلمة الرد
-

❨ اوامر القفل والفتح بالمسح ❩

⌯ قفل ↣ ↢ فتح  التعديل
⌯ قفل ↣ ↢ فتح  الفويسات
⌯ قفل ↣ ↢ فتح  الفيديو
⌯ قفل ↣ ↢ فتح  الـصــور
⌯ قفل ↣ ↢ فتح  الملصقات
⌯ قفل ↣ ↢ فتح  الدخول
⌯ قفل ↣ ↢ فتح  الفارسية
⌯ قفل ↣ ↢ فتح  الملفات
⌯ قفل ↣ ↢ فتح  المتحركات
⌯ قفل ↣ ↢ فتح  تعديل الميديا
⌯ قفل ↣ ↢ فتح  تعديل الميديا بالتقييد
⌯ قفل ↣ ↢ فتح  الدردشه
⌯ قفل ↣ ↢ فتح  الروابط
⌯ قفل ↣ ↢ فتح  الهشتاق
⌯ قفل ↣ ↢ فتح  البوتات
⌯ قفل ↣ ↢ فتح  اليوزرات
⌯ قفل ↣ ↢ فتح  الاشعارات
⌯ قفل ↣ ↢ فتح  الكلام الكثير
⌯ قفل ↣ ↢ فتح  التكرار
⌯ قفل ↣ ↢ فتح  التوجيه
⌯ قفل ↣ ↢ فتح  الانلاين
⌯ قفل ↣ ↢ فتح  الجهات
⌯ قفل ↣ ↢ فتح  الــكـــل
⌯ قفل ↣ ↢ فتح  السب
⌯ قفل ↣ ↢ فتح  الاضافه
⌯ قفل ↣ ↢ فتح  الصوت
⌯ قفل ↣ ↢ فتح  القنوات
⌯ قفل ↣ ↢ فتح الايراني
⌯ قفل ↣ ↢ فتح الإباحي

❨ اوامر التفعيل والتعطيل ❩

⌯ تفعيل ↣ ↢ تعطيل الترحيب
⌯ تفعيل ↣ ↢ تعطيل الترحيب بالصورة
⌯ تفعيل ↣ ↢ تعطيل الردود
⌯ تفعيل ↣ ↢ تعطيل ردود الاعضاء
⌯ تفعيل ↣ ↢ تعطيل الايدي
⌯ تفعيل ↣ ↢ تعطيل الرابط
⌯ تفعيل ↣ ↢ تعطيل اطردني
⌯ تفعيل ↣ ↢ تعطيل الحماية
⌯ تفعيل ↣ ↢ تعطيل المنشن
⌯ تفعيل ↣ ↢ تعطيل التحقق
⌯ تفعيل ↣ ↢ تعطيل ردود المطور
⌯ تفعيل ↣ ↢ تعطيل التحذير
⌯ تفعيل ↣ ↢ تعطيل البايو
⌯ تفعيل ↣ ↢ تعطيل انطقي
⌯ تفعيل ↣ ↢ تعطيل شازام
""",
        reply_markup=_help_keyboard(m.from_user.id, 3),
    )


# ─── commands4 ─────────────────────────────────────────────────────────────

@register_callback("commands4:")
@safe_handler
async def _cmd4(c, m) -> None:
    if m.data != f"commands4:{m.from_user.id}":
        return
    await m.edit_message_text(
        """
☤ تفعيل الالعاب
☤ تعطيل الالعاب
    ╼╾
✽ جمل
✽ كلمات
✽ اغاني
✽ دين
✽ عربي
✽ اكمل
✽ صور
✽ كت تويت
✽ مؤقت
✽ اعلام
✽ معاني
✽ تخمين
✽ احكام
✽ ارقام
✽ احسب
✽ خواتم
✽ انقليزي
✽ ترتيب
✽ انمي
✽ تركيب
✽ تفكيك
✽ عواصم
✽ روليت
✽ سيارات
✽ ايموجي
✽ حجره
✽ تشفير
✽ كره قدم
✽ ديمون
╼╾
❖ فلوسي ↼ عشان تشوف فلوسك
❖ بيع فلوسي + العدد ↼ للأستبدال
""",
        reply_markup=_help_keyboard(m.from_user.id, 4),
    )


# ─── commands5 ─────────────────────────────────────────────────────────────

@register_callback("commands5:")
@safe_handler
async def _cmd5(c, m) -> None:
    if m.data != f"commands5:{m.from_user.id}":
        return
    channel = await rdb.get(f"{Dev_Zaid}:BotChannel") or "YQYQY6"
    await m.edit_message_text(
        f"""
للاستفسار - @{channel}

🍰 ⌯ رفع ↣ ↢ تنزيل كيكه
🍯 ⌯ رفع ↣ ↢ تنزيل عسل
💩 ⌯ رفع ↣ ↢ تنزيل زق
🦓 ⌯ رفع ↣ ↢ تنزيل حمار
🐄 ⌯ رفع ↣ ↢ تنزيل بقره
🐩 ⌯ رفع ↣ ↢ تنزيل كلب
🐒 ⌯ رفع ↣ ↢ تنزيل قرد
🐐 ⌯ رفع ↣ ↢ تنزيل تيس
🐂 ⌯ رفع ↣ ↢ تنزيل ثور
🏅 ⌯ رفع ↣ ↢ تنزيل هكر
🐓 ⌯ رفع ↣ ↢ تنزيل دجاجه
🧱 ⌯ رفع ↣ ↢ تنزيل ملكه
🔫 ⌯ رفع ↣ ↢ تنزيل صياد
🐏 ⌯ رفع ↣ ↢ تنزيل خاروف
❤️ ⌯ رفع لقلبي ↣ ↢ تنزيل من قلبي

⌯ قائمة الكيك
⌯ قائمة العسل
⌯ قائمة الزق
⌯ قائمة الحمير
⌯ قائمة البقر
⌯ قائمة الكلاب
⌯ قائمة القرود
⌯ قائمة التيس
⌯ قائمة الثور
⌯ قائمة الهكر
⌯ قائمة الدجاج
⌯ قائمة الهطوف
⌯ قائمة الصيادين
⌯ قائمة الخرفان
""",
        reply_markup=_help_keyboard(m.from_user.id, 5),
    )


# ─── commands6 ─────────────────────────────────────────────────────────────

@register_callback("commands6:")
@safe_handler
async def _cmd6(c, m) -> None:
    if m.data != f"commands6:{m.from_user.id}":
        return
    await m.edit_message_text(
        """
اليـوتيوب

تفعيل اليوتيوب
تعطيل اليوتيوب

❋ البـحث عن اغنية ↓

بحث اسم الاغنية

يوت اسم الاغنية
الساوند كلاود

تفعيل الساوند
تعطيل الساوند

❋ البـحث عن اغنية ↓

رابط الاغنية أو ساوند + اسم الاغنية


التيك توك

تفعيل التيك
تعطيل للتيك

❋ للتحميل من التيك ↓

تيك ورابط المقطع
""",
        reply_markup=_help_keyboard(m.from_user.id, 6),
    )


# ─── commands7 ─────────────────────────────────────────────────────────────

@register_callback("commands7:")
@safe_handler
async def _cmd7(c, m) -> None:
    if m.data != f"commands7:{m.from_user.id}":
        return
    await m.edit_message_text(
        """
✜ اوامر البنك

⌯ انشاء حساب بنكي  ↢ تسوي حساب وتقدر تحول فلوس مع مزايا ثانيه

⌯ مسح حساب بنكي  ↢ تلغي حسابك البنكي

⌯ تحويل ↢ تطلب رقم حساب الشخص وتحول له فلوس

⌯ حسابي  ↢ يطلع لك رقم حسابك عشان تعطيه للشخص اللي بيحول لك

⌯ فلوسي ↢ يعلمك كم فلوسك

⌯ راتب ↢ يعطيك راتبك كل ٥ دقيقة

⌯ بخشيش ↢ يعطيك بخشيش كل ٥ دقايق

⌯ زرف ↢ تزرف فلوس اشخاص كل ٥ دقايق

⌯ كنز ↢ يعطيك كنز كل ١٠ دقايق

⌯ استثمار ↢ تستثمر بالمبلغ اللي تبيه مع نسبة ربح مضمونه من ١٪؜ الى ١٥٪؜ ( او استثمار فلوسي )

⌯ حظ ↢ تلعبها بأي مبلغ ياتدبله ياتخسره انت وحظك ( او حظ فلوسي )

⌯ عجله ↢ تلعب عجله الحظ ولو تشابهو ال ٣ ايموجيات تكسب من ١٠٠ الف لحد ٣٠٠ الف انت وحظك

⌯ توب الفلوس ↢ يطلع توب اكثر ناس معهم فلوس بكل القروبات

⌯ توب الحراميه ↢ يطلع لك اكثر ناس زرفوا
""",
        reply_markup=_help_keyboard(m.from_user.id, 7),
    )


# ─── commands8 ─────────────────────────────────────────────────────────────

@register_callback("commands8:")
@safe_handler
async def _cmd8(c, m) -> None:
    if m.data != f"commands8:{m.from_user.id}":
        return
    await m.edit_message_text(
        """
✜ اوامر الزواج

⌯ زواج  ↢ تكتبه بالرد على رسالة شخص مع المهر ويزوجك

⌯ زواجي  ↢ يطلع وثيقة زواجك اذا متزوج

⌯ طلاق ↢ يطلقك اذا متزوج

⌯ خلع  ↢ يخلع زوجك ويرجع له المهر

⌯ زواجات ↢ يطلع اغلى الزواجات بالقروب
""",
        reply_markup=_help_keyboard(m.from_user.id, 8),
    )


# ─── delAdminMSG ────────────────────────────────────────────────────────────

@register_callback("delAdminMSG")
@safe_handler
async def _del_admin_msg(c, m) -> None:
    if str(m.from_user.id) in m.message.text.html:
        await m.message.delete()


# ─── yes:{uid} — التحقق إيجابي ──────────────────────────────────────────────

@register_callback("yes:")
@safe_handler
async def _yes_verify(c, m) -> None:
    if m.data != f"yes:{m.from_user.id}":
        return
    k = await rdb.get(f"{Dev_Zaid}:botkey") or "❌"
    channel = await rdb.get(f"{Dev_Zaid}:BotChannel") or "YQYQY6"
    try:
        await c.restrict_chat_member(
            m.message.chat.id,
            m.from_user.id,
            ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_send_polls=True,
                can_invite_users=True,
                can_add_web_page_previews=True,
                can_change_info=True,
                can_pin_messages=True,
            ),
        )
    except Exception as e:
        logging.exception(e)
        return
    await m.edit_message_text(
        f"""
{k} تم التحقق منك وطلعت مو زومبي
{k} الحين تقدر تسولف بالقروب
☆
""",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🧚‍♀️", url=f"t.me/{channel}")]]
        ),
    )


# ─── no:{uid} — التحقق سلبي ──────────────────────────────────────────────────

@register_callback("no:")
@safe_handler
async def _no_verify(c, m) -> None:
    if not m.data.startswith("no:") or m.data.startswith("no:del"):
        return
    if m.data != f"no:{m.from_user.id}":
        return
    k = await rdb.get(f"{Dev_Zaid}:botkey") or "❌"
    await m.edit_message_text(
        f"""
{k} للأسف طلعت زومبي 🧟‍♀️
{k} مالك غير تنطر حد من المشرفين يجي يتوسطلك
☆
""",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "رفع التقييد والسماح",
                callback_data=f"yesVER:{m.from_user.id}",
            )],
            [InlineKeyboardButton(
                "طرد", callback_data=f"noVER:{m.from_user.id}"
            )],
        ]),
    )


# ─── yesVER:{uid} — الادمن يقبل ──────────────────────────────────────────────

@register_callback("yesVER:")
@safe_handler
async def _yes_ver(c, m) -> None:
    if not m.data.startswith("yesVER:"):
        return
    user_id = int(m.data.split(":")[1])
    k = await rdb.get(f"{Dev_Zaid}:botkey") or "❌"
    if not await admin_pls(m.from_user.id, m.message.chat.id):
        return await m.answer(f"{k} هذا الزر يخص ( الادمن وفوق ) بس", show_alert=True)
    await m.edit_message_text(f"{k} توسطلك واحد من الادمن ورفعت عنك القيود")
    try:
        await c.restrict_chat_member(
            m.message.chat.id,
            user_id,
            ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_send_polls=True,
                can_invite_users=True,
                can_add_web_page_previews=True,
                can_change_info=True,
                can_pin_messages=True,
            ),
        )
    except Exception as e:
        logging.exception(e)
        pass


# ─── noVER:{uid} — الادمن يرفض ───────────────────────────────────────────────

@register_callback("noVER:")
@safe_handler
async def _no_ver(c, m) -> None:
    if not m.data.startswith("noVER:"):
        return
    user_id = int(m.data.split(":")[1])
    k = await rdb.get(f"{Dev_Zaid}:botkey") or "❌"
    if not await admin_pls(m.from_user.id, m.message.chat.id):
        return await m.answer(f"{k} هذا الزر يخص ( الادمن وفوق ) بس", show_alert=True)
    await m.edit_message_text(f"{k} انقلع برا القروب يلا")
    try:
        await m.message.chat.ban_member(user_id)
        await m.message.chat.unban_member(user_id)
    except Exception as e:
        logging.exception(e)
        pass


# ─── yes:del:bank — تصفير البنك ──────────────────────────────────────────────

@register_callback("yes:del:bank")
@safe_handler
async def _yes_del_bank(c, m) -> None:
    if m.data != "yes:del:bank":
        return
    if not await devp_pls(m.from_user.id, m.message.chat.id):
        return await m.answer("تعجبني ثقتك")
    await m.edit_message_text("ابشر صفرت البنك")
    patterns = [
        "*:Floos", "*:BankWait", "*:BankWaitB5",
        "*:BankWaitZRF", "*:BankWaitEST", "*:BankWaitHZ",
        "*:BankWait3JL", "*:Zrf",
    ]
    for pattern in patterns:
        keys = await rdb.keys(pattern)
        for key in keys:
            await rdb.delete(key)
    await rdb.delete("BankTop")
    await rdb.delete("BankTopZRF")


# ─── no:del:bank ──────────────────────────────────────────────────────────────

@register_callback("no:del:bank")
@safe_handler
async def _no_del_bank(c, m) -> None:
    if m.data != "no:del:bank":
        return
    if not await devp_pls(m.from_user.id, m.message.chat.id):
        return await m.answer("تعجبني ثقتك")
    await m.message.delete()


# ─── topfloos:{uid} ───────────────────────────────────────────────────────────

@register_callback("topfloos:")
@safe_handler
async def _topfloos(c, m) -> None:
    if m.data != f"topfloos:{m.from_user.id}":
        return
    k = await rdb.get(f"{Dev_Zaid}:botkey") or "❌"
    channel = await rdb.get(f"{Dev_Zaid}:BotChannel") or "YQYQY6"

    if not await rdb.smembers("BankList"):
        return await m.answer(f"{k} مافيه حسابات بالبنك", show_alert=True)

    rep = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("‣ 💸", callback_data="None"),
            InlineKeyboardButton("توب الحرامية 💰", callback_data=f"topzrf:{m.from_user.id}"),
        ],
        [InlineKeyboardButton("🧚‍♀️", url=f"t.me/{channel}")],
    ])

    cached = await rdb.get("BankTop")
    if cached:
        text = cached
        floos_raw = await rdb.get(f"{m.from_user.id}:Floos")
        floos = int(floos_raw) if floos_raw else 0
        ttl = await rdb.ttl("BankTop")
        wait = time.strftime("%M:%S", time.gmtime(ttl))
        text += "\n━━━━━━━━━"
        text += f"\n# You ) {floos:,} 💸 l {m.from_user.first_name}"
        text += f"\n\n[قوانين التُوب](https://t.me/{botUsername}?start=rules)"
        text += f"\n\nالقائمة تتحدث بعد {wait} دقيقة"
        return await m.edit_message_text(text, disable_web_page_preview=True, reply_markup=rep)

    members_raw = await rdb.smembers("BankList")
    users = []
    for user in members_raw:
        uid = int(user)
        name_raw = await rdb.get(f"{uid}:bankName")
        if name_raw:
            name = name_raw[:10]
        else:
            try:
                chat = await c.get_chat(uid)
                name = chat.first_name
                await rdb.set(f"{uid}:bankName", name)
            except Exception as e:
                logging.exception(e)
                name = "INVALID_NAME"
                await rdb.set(f"{uid}:bankName", name)
        floos_raw2 = await rdb.get(f"{uid}:Floos")
        floos2 = int(floos_raw2) if floos_raw2 else 0
        users.append({"name": name, "money": floos2})

    top = _get_top(users)
    text = "توب 20 اغنى اشخاص:\n\n"
    for count, user in enumerate(top[:20], 1):
        emoji = _emoji_bank(count)
        clean = (user["name"]
                 .replace("*","").replace("`","").replace("|","")
                 .replace("#","").replace("<","").replace(">","").replace("_",""))
        text += f'**{emoji}{user["money"]:,}** 💸 l {clean}\n'

    await rdb.set("BankTop", text, ex=300)
    floos_me_raw = await rdb.get(f"{m.from_user.id}:Floos")
    floos_me = int(floos_me_raw) if floos_me_raw else 0
    ttl2 = await rdb.ttl("BankTop")
    wait2 = time.strftime("%M:%S", time.gmtime(ttl2))
    text += "\n━━━━━━━━━"
    text += f"\n# You ) {floos_me:,} 💸 l {m.from_user.first_name}"
    text += f"\n\n[قوانين التُوب](https://t.me/{botUsername}?start=rules)"
    text += f"\n\nالقائمة تتحدث بعد {wait2} دقيقة"
    await m.edit_message_text(text, disable_web_page_preview=True, reply_markup=rep)


# ─── topzrf:{uid} ────────────────────────────────────────────────────────────

@register_callback("topzrf:")
@safe_handler
async def _topzrf(c, m) -> None:
    if m.data != f"topzrf:{m.from_user.id}":
        return
    k = await rdb.get(f"{Dev_Zaid}:botkey") or "❌"
    channel = await rdb.get(f"{Dev_Zaid}:BotChannel") or "YQYQY6"

    if not await rdb.smembers("BankList"):
        return await m.answer(f"{k} مافيه حسابات بالبنك", show_alert=True)

    rep = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("توب الفلوس 💸", callback_data=f"topfloos:{m.from_user.id}"),
            InlineKeyboardButton("‣ 💰", callback_data="None"),
        ],
        [InlineKeyboardButton("🧚‍♀️", url=f"t.me/{channel}")],
    ])

    cached = await rdb.get("BankTopZRF")
    if cached:
        text = cached
        zrf_raw = await rdb.get(f"{m.from_user.id}:Zrf")
        zrf = int(zrf_raw) if zrf_raw else 0
        ttl = await rdb.ttl("BankTopZRF")
        wait = time.strftime("%M:%S", time.gmtime(ttl))
        text += "\n━━━━━━━━━"
        text += f"\n# You ) {zrf:,} 💰 l {m.from_user.first_name}"
        text += f"\n\n[قوانين التُوب](https://t.me/{botUsername}?start=rules)"
        text += f"\n\nالقائمة تتحدث بعد {wait} دقيقة"
        return await m.edit_message_text(text, disable_web_page_preview=True, reply_markup=rep)

    members_raw = await rdb.smembers("BankList")
    users = []
    for user in members_raw:
        uid = int(user)
        name_raw = await rdb.get(f"{uid}:bankName")
        if name_raw:
            name = name_raw[:10]
        else:
            try:
                chat = await c.get_chat(uid)
                name = chat.first_name
                await rdb.set(f"{uid}:bankName", name)
            except Exception as e:
                logging.exception(e)
                name = "INVALID_NAME"
                await rdb.set(f"{uid}:bankName", name)
        zrf_raw2 = await rdb.get(f"{uid}:Zrf")
        if zrf_raw2:
            users.append({"name": name, "money": int(zrf_raw2)})

    top = _get_top(users)
    text = "توب 20 اكثر الحراميه زرفًا:\n\n"
    for count, user in enumerate(top[:20], 1):
        emoji = _emoji_bank(count)
        clean = (user["name"]
                 .replace("*","").replace("`","").replace("|","")
                 .replace("#","").replace("<","").replace(">","").replace("_",""))
        text += f'**{emoji}{user["money"]}** 💰 l {clean}\n'

    await rdb.set("BankTopZRF", text, ex=300)
    zrf_me_raw = await rdb.get(f"{m.from_user.id}:Zrf")
    zrf_me = int(zrf_me_raw) if zrf_me_raw else 0
    ttl2 = await rdb.ttl("BankTopZRF")
    wait2 = time.strftime("%M:%S", time.gmtime(ttl2))
    text += "\n━━━━━━━━━"
    text += f"\n# You ) {zrf_me} 💰 l {m.from_user.first_name}"
    text += f"\n\n[قوانين التُوب](https://t.me/{botUsername}?start=rules)"
    text += f"\n\nالقائمة تتحدث بعد {wait2} دقيقة"
    await m.edit_message_text(text, disable_web_page_preview=True, reply_markup=rep)


# ─── gowner+ / owner+ / mod+ / admin+ / pre+ ─────────────────────────────────

_LOCK_LEVELS = {
    "gowner+": (0, "المالك الاساسي وفوق"),
    "owner+":  (1, "المالك وفوق"),
    "mod+":    (2, "المدير وفوق"),
    "admin+":  (3, "الادمن وفوق"),
    "pre+":    (4, "المميز وفوق"),
}

for _prefix in _LOCK_LEVELS:
    @register_callback(_prefix)
    @safe_handler
    async def _lock_level_btn(c, m, _pfx=_prefix) -> None:
        level, label = _LOCK_LEVELS[_pfx]
        if m.data != f"{_pfx}{m.from_user.id}":
            return
        if not await gowner_pls(m.from_user.id, m.message.chat.id):
            await m.answer("هذا الامر للمالك الاساسي و فوق بس", show_alert=True)
            return await m.message.delete()
        command = m.message.reply_to_message.text.split(None, 2)[2]
        await rdb.hset(Dev_Zaid + f"locks-{m.message.chat.id}", command, level)
        await m.edit_message_text(
            f"- تم تعيين الامر ( {command} ) لـ{label} فقط"
        )
