"""
all_locks_1.py
منقول من bmqa/Plugins/all.py (guardCommands — سطر 2107 → 2406)
الفئة: الأقفال التفصيلية — دفعة 1 (15 زوج قفل/فتح = 30 أمر)

النمط الموحّد:
  - كل زوج (قفل X / فتح X) يُمرَّر لـ _lock_toggle(...)
  - الهاندلر مُوجَّه بجدول _LOCK_TABLE_1 (لا تكرار منطق)
  - _lock_toggle مُصدَّرة لـ all_locks_2.py

التحويلات المطبّقة:
  - r.get/set/delete → await rdb.*
  - m.reply(...)     → await m.reply(...)
  - return False     → return

السلوكيات الغامضة موثّقة في قسم AMBIGUOUS.
"""

from pyrogram import Client, ContinuePropagation, filters

from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from core.messages import get_message
from helpers.ranks import admin_pls, mod_pls, owner_pls, isLockCommand


# ══════════════════════════════════════════════════════════════════════════════
# Templates — منقولة من all_protection.py (معرَّفة هنا أيضاً لاستقلالية الملف)
#
# ⚠️ ملاحظة: قالبَي lock وOpen (الرسالتان الفعليتان عند نجاح القفل/الفتح) لم
# تعودا تُستخدَمان مباشرة داخل _lock_toggle() بالأسفل — تم استبدال استخدامهما
# هناك بـ await get_message("locks.chat_locked" / "locks.chat_opened", ...)
# من core/messages.py، ليصبح بالإمكان تخصيصهما عبر لوحة تحكم المطوّرين
# (Plugins/message_editor.py) دون المساس بهذا الملف مستقبلاً.
# نصّا locks.chat_locked/locks.chat_opened في core/messages.py مطابقان حرفياً
# لنصّي lock وOpen أدناه، لذا الرسالة النهائية للمستخدمين تبقى متطابقة حرفياً
# بالضبط طالما لا يوجد override محفوظ في Redis.
#
# القوالب الستة أدناه (بما فيها lock وOpen) بقيت مُعرَّفة كما هي بلا أي حذف أو
# تعديل، لأن Plugins/all_locks_2.py يستوردها مباشرة (lock, lockn, locknn,
# Open, Openn, Openn2) ويستخدم Open/Openn مباشرة لحالة "فتح الإباحي" الخاصة،
# بمعزل عن _lock_toggle — إزالتها كانت ستكسر ذلك الملف رغم عدم لمسه.
# ══════════════════════════════════════════════════════════════════════════════

Open = """
{} من 「 {} 」
{} ابشر فتحت {}
☆
"""

Openn = """
{} من 「 {} 」
{} {} مفتوح من قبل
☆
"""

Openn2 = """
{} من 「 {} 」
{} {} مفتوحه من قبل
☆
"""

lock = """
{} من 「 {} 」
{} ابشر قفلت {}
☆
"""

lockn = """
{} من 「 {} 」
{} {} مقفل من قبل
☆
"""

locknn = """
{} من 「 {} 」
{} {} مقفله من قبل
☆
"""


# ══════════════════════════════════════════════════════════════════════════════
# الدالة العامة (Generic Toggle Handler)
# مُصدَّرة → تُستورَد في all_locks_2.py
#
# المعاملات:
#   m          — كائن الرسالة
#   k          — مفتاح البوت (botkey)
#   redis_key  — اسم المفتاح في Redis بدون cid أو Dev_Zaid
#   display    — النص الذي يظهر في الرسالة ("الشات"، "الفيديو"...)
#   rank_fn    — دالة التحقق من الصلاحية (mod_pls / owner_pls)
#   perm_msg   — رسالة رفض الصلاحية
#   gender     — "m" مذكر → lockn/Openn  |  "f" مؤنث → locknn/Openn2
#   is_locking — True=قفل، False=فتح
# ══════════════════════════════════════════════════════════════════════════════

async def _lock_toggle(
    m,
    k: str,
    redis_key: str,
    display: str,
    rank_fn,
    perm_msg: str,
    gender: str,
    is_locking: bool,
) -> None:
    if not await rank_fn(m.from_user.id, m.chat.id):
        return await m.reply(perm_msg)

    cid = m.chat.id
    mention = m.from_user.mention
    state = await rdb.get(f"{cid}:{redis_key}:{Dev_Zaid}")

    if is_locking:
        if state:
            tmpl = locknn if gender == "f" else lockn
            return await m.reply(tmpl.format(k, mention, k, display))
        await rdb.set(f"{cid}:{redis_key}:{Dev_Zaid}", 1)
        text = await get_message("locks.chat_locked", botkey=k, mention=mention, feature=display)
        return await m.reply(text)
    else:
        if not state:
            tmpl = Openn2 if gender == "f" else Openn
            return await m.reply(tmpl.format(k, mention, k, display))
        await rdb.delete(f"{cid}:{redis_key}:{Dev_Zaid}")
        text = await get_message("locks.chat_opened", botkey=k, mention=mention, feature=display)
        return await m.reply(text)


# ══════════════════════════════════════════════════════════════════════════════
# جدول الأقفال — دفعة 1 (سطر 2107-2406)
#
# الحقول: (texts_lock, texts_unlock, redis_key, display, gender, rank_fn, perm_msg)
#   gender: "m"=مذكر (lockn/Openn)، "f"=مؤنث (locknn/Openn2)
#   perm_msg: رسالة الرفض الحرفية من الأصل (لم تُغيَّر)
# ══════════════════════════════════════════════════════════════════════════════

_MOD_PERM  = "هذا الامر يخص ( المدير وفوق ) بس"

_LOCK_TABLE_1 = [
    # ── زوج 1: الدردشة (سطر 2107-2125) ──────────────────────────────────
    (
        ("قفل الدردشة", "قفل الدردشه", "قفل الشات"),
        ("فتح الدردشة", "فتح الدردشه", "فتح الشات"),
        "mute", "الشات", "m", mod_pls, _MOD_PERM,
    ),
    # ── زوج 2: التعديل (سطر 2127-2145) ──────────────────────────────────
    (
        ("قفل التعديل",),
        ("فتح التعديل",),
        "lockEdit", "التعديل", "m", mod_pls, _MOD_PERM,
    ),
    # ── زوج 3: تعديل الميديا (سطر 2147-2165) ────────────────────────────
    (
        ("قفل تعديل الميديا",),
        ("فتح تعديل الميديا",),
        "lockEditM", "تعديل الميديا", "m", mod_pls, _MOD_PERM,
    ),
    # ── زوج 4: الفويسات/البصمات (سطر 2167-2185) ─────────────────────────
    (
        ("قفل الفويسات", "قفل البصمات"),
        ("فتح الفويسات", "فتح البصمات"),
        "lockVoice", "الفويس", "m", mod_pls, _MOD_PERM,
    ),
    # ── زوج 5: الفيديو (سطر 2187-2205) ──────────────────────────────────
    (
        ("قفل الفيديو", "قفل الفيديوهات"),
        ("فتح الفيديو", "فتح الفيديوهات"),
        "lockVideo", "الفيديو", "m", mod_pls, _MOD_PERM,
    ),
    # ── زوج 6: الاشعارات (سطر 2207-2225) — مؤنث ─────────────────────────
    (
        ("قفل الاشعارات",),
        ("فتح الاشعارات",),
        "lockNot", "الاشعارات", "f", mod_pls, _MOD_PERM,
    ),
    # ── زوج 7: الصور (سطر 2227-2245) — مؤنث ─────────────────────────────
    (
        ("قفل الصور",),
        ("فتح الصور",),
        "lockPhoto", "الصور", "f", mod_pls, _MOD_PERM,
    ),
    # ── زوج 8: الملصقات (سطر 2247-2265) — مؤنث ──────────────────────────
    (
        ("قفل الملصقات",),
        ("فتح الملصقات",),
        "lockStickers", "الملصقات", "f", mod_pls, _MOD_PERM,
    ),
    # ── زوج 9: الفارسيه (سطر 2267-2285) — مؤنث ──────────────────────────
    (
        ("قفل الفارسيه",),
        ("فتح الفارسيه",),
        "lockPersian", "الفارسيه", "f", mod_pls, _MOD_PERM,
    ),
    # ── زوج 10: الملفات (سطر 2287-2305) — مؤنث ──────────────────────────
    (
        ("قفل الملفات",),
        ("فتح الملفات",),
        "lockFiles", "الملفات", "f", mod_pls, _MOD_PERM,
    ),
    # ── زوج 11: المتحركات (سطر 2307-2325) — مؤنث ────────────────────────
    (
        ("قفل المتحركات", "قفل المتحركه"),
        ("فتح المتحركات", "فتح المتحركه"),
        "lockAnimations", "المتحركات", "f", mod_pls, _MOD_PERM,
    ),
    # ── زوج 12: الروابط (سطر 2327-2345) — مؤنث ──────────────────────────
    (
        ("قفل الروابط",),
        ("فتح الروابط",),
        "lockUrls", "الروابط", "f", mod_pls, _MOD_PERM,
    ),
    # ── زوج 13: الهشتاق (سطر 2347-2365) — مذكر ──────────────────────────
    (
        ("قفل الهشتاق", "قفل الهاشتاق"),
        ("فتح الهشتاق", "فتح الهاشتاق"),
        "lockHashtags", "الهاشتاق", "m", mod_pls, _MOD_PERM,
    ),
    # ── زوج 14: البوتات (سطر 2367-2385) — مؤنث ──────────────────────────
    (
        ("قفل البوتات",),
        ("فتح البوتات",),
        "lockBots", "البوتات", "f", mod_pls, _MOD_PERM,
    ),
    # ── زوج 15: اليوزرات/المنشن (سطر 2387-2405) — مؤنث ──────────────────
    (
        ("قفل اليوزرات", "قفل المنشن"),
        ("فتح اليوزرات", "فتح المنشن"),
        "lockTags", "اليوزرات", "f", mod_pls, _MOD_PERM,
    ),
]

# فهرس سريع: text → (entry_index, is_locking)
_TEXT_MAP_1: dict = {}
for _entry in _LOCK_TABLE_1:
    _ltexts, _utexts, _key, _disp, _g, _rank, _perm = _entry
    for _t in _ltexts:
        _TEXT_MAP_1[_t] = (_entry, True)
    for _t in _utexts:
        _TEXT_MAP_1[_t] = (_entry, False)


# ══════════════════════════════════════════════════════════════════════════════
# دالة مساعدة: بناء نص الأمر
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
# الهاندلر الرئيسي — group=28
# ══════════════════════════════════════════════════════════════════════════════

@register("locks_1_commands")
@Client.on_message(filters.group & filters.text, group=28)
@safe_handler
async def locks1Handler(c, m) -> None:
    """
    يعالج 30 أمر قفل/فتح (دفعة 1) عبر جدول _LOCK_TABLE_1.
    """

    # ── فحوصات الأهلية ──────────────────────────────────────────────────
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

    k = await rdb.get(f"{Dev_Zaid}:botkey")

    # ── البحث في جدول الأقفال ───────────────────────────────────────────
    match = _TEXT_MAP_1.get(text)
    if match:
        entry, is_locking = match
        _, _, redis_key, display, gender, rank_fn, perm_msg = entry
        return await _lock_toggle(
            m, k, redis_key, display, rank_fn,
            f"{k} {perm_msg}", gender, is_locking
        )

    # لا يوجد أمر مطابق ضمن جدول هذا الملف (_LOCK_TABLE_1) — لم يُرسَل أي رد
    # فعلي للمستخدم في هذا المسار، لذا نُمرِّر المعالجة لبقية handlers
    # group=28 (راجع [C4] في all_moderation_2.py لشرح المشكلة الأصلية).
    raise ContinuePropagation()


# ══════════════════════════════════════════════════════════════════════════════
# AMBIGUOUS — سلوكيات غامضة
# ══════════════════════════════════════════════════════════════════════════════
#
# [A1] قفل الدردشة → redis_key = "mute" (نفس مفتاح الصمت الكلي للمجموعة)
#      أي أن "قفل الدردشة" و"كتم" يتشاركان المفتاح ذاته.
#      إذا كان هناك هاندلر كتم منفصل يستخدم نفس المفتاح، فهذا تداخل مقصود.
#
# [A2] قفل التعديل (lockEdit) ≠ قفل تعديل الميديا (lockEditM):
#      مفتاحان منفصلان رغم التشابه في الاسم. lockEditM يُفعَّل أيضاً
#      في "تفعيل الحماية" لكن "تعطيل الحماية" لا يُلغيه.
#      انظر AMBIGUOUS [A3] في all_protection.py.
#
# [A3] gender="m" للفويسات/البصمات:
#      النص في الرسالة "الفويس" (مذكر) وليس "الفويسات" (جمع مؤنث).
#      هذا اختيار مقصود في الأصل — محفوظ.
#
# [A4] فتح الاشعارات → Openn2 (مؤنث): "مفتوحه"
#      لكن قفل الاشعارات → lock (بدون جنس): "ابشر قفلت"
#      ثم رسالة "مقفله" (locknn) — مؤنث. متسق.
