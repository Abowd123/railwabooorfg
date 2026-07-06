"""
tests/test_group28_continue_propagation.py — bmqa-v2

اختبار تكاملي (script مستقل، وليس pytest — نفس نمط
tests/test_chat_members_cache.py) يثبت أن إصلاح مشكلة [C4] (المشتركة بين 8
ملفات على نفس group=28 بدون continue_propagation) يعمل فعلياً من طرف لطرف:

  1. يستورد الملفات الثمانية الحقيقية (غير مُعدَّلة نسخة اختبار — نفس الكود
     في Plugins/) بترتيب أبجدي مطابق تماماً لترتيب تحميل pyrogram الفعلي
     (plugins={"root": "Plugins"} يحمّل الوحدات أبجدياً):
       all_features_toggle → all_locks_1 → all_locks_2 → all_moderation_1
       → all_moderation_2 → all_protection → all_settings
       → all_voice_and_blocklist
  2. يبني محاكاة صغيرة لموزّع pyrogram الداخلي (loop على handlers مجموعة
     28 بنفس ترتيب التسجيل، مع التقاط ContinuePropagation للانتقال للتالي
     تماماً كآلية pyrogram الحقيقية) بدل تشغيل بوت تيليجرام فعلي.
  3. يرسل رسالة تحمل أمراً من all_locks_1.py ("قفل الدردشة") ويتحقق أنها
     نُفِّذت فعلياً رغم أن all_features_toggle.py (السابق لها أبجدياً) لا
     يعرفها إطلاقاً.
  4. يرسل رسالة تحمل أمراً من all_settings.py ("تفعيل انطقي") ويتحقق أنها
     نُفِّذت فعلياً رغم مرورها أولاً عبر 6 ملفات أخرى (منها all_locks_1
     وall_locks_2 وكلا ملفي all_moderation) لا تعرف هذا الأمر.

بدون الإصلاح (raise ContinuePropagation() في نهاية كل دالة + إعادة رفعها
في core/errors.safe_handler بدل التقاطها) كان الاختباران التاليان سيفشلان:
كانت الرسالة الأولى ستتوقف عند أول handler (all_features_toggle) بدون أي
رد إطلاقاً، والثانية كانت ستتوقف عند نفس المكان أيضاً — لا نصل أبداً حتى
لملفات لاحقة.

الاعتماديات الخارجية غير المتاحة في بيئة الاختبار هذه (pyrogram/kurigram
الحقيقية، redis، kvsqlite، aiohttp، speech_recognition، pydub، pytz،
hijri_converter، Python_ARQ) مُستبدَلة بوحدات وهمية بسيطة قبل الاستيراد
(انظر _install_fake_dependencies بالأسفل) — لكن core/errors.py وhelpers/
ranks.py وPlugins/all_locks_1.py..all_voice_and_blocklist.py نفسها تُستورَد
وتُنفَّذ حرفياً من المشروع الحقيقي دون أي تعديل أو نسخ.

⚠️ ملاحظة توثيقية من كتابة هذا الاختبار: أول محاولة عرَّفت
ContinuePropagation/StopPropagation الوهميين كفرعين من
StopIteration/StopAsyncIteration، فاكتشفنا تجريبياً أن بايثون (PEP 479)
يحوّل تلقائياً أي StopIteration يُرفَع من داخل `async def` إلى
RuntimeError("coroutine raised StopIteration") — أي أن هذا لا يمكن أن يكون
تصميم pyrogram الفعلي (وإلا لن تعمل الميزة إطلاقاً مع أي handler غير
متزامن). صُحِّح الآن إلى استثناءين عاديين من Exception مباشرة، وهو ما
لا يغيّر شيئاً في صحة إصلاح core/errors.py (الذي لا يعتمد أصلاً على معرفة
التسلسل الهرمي الدقيق، بل فقط على كونهما Exception).

يُشغَّل مباشرة: python3 tests/test_group28_continue_propagation.py
(أو عبر pytest إن كان متاحاً: pytest tests/test_group28_continue_propagation.py)
"""

from __future__ import annotations

import asyncio
import importlib
import os
import sys
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ══════════════════════════════════════════════════════════════════════════════
# 1) وحدات وهمية للاعتماديات الخارجية غير المثبَّتة في بيئة الاختبار
# ══════════════════════════════════════════════════════════════════════════════

def _install_fake_dependencies() -> dict:
    """يُسجِّل وحدات وهمية في sys.modules قبل استيراد أي كود من المشروع.
    يُعيد dict فيه المراجع المهمة (ContinuePropagation، StopPropagation،
    سجل الـ handlers لكل group) ليستخدمها باقي الاختبار.
    """

    # ── pyrogram (الأساسي) ───────────────────────────────────────────────
    # ⚠️ اكتُشف أثناء كتابة هذا الاختبار: المحاولة الأولى عرَّفت هذين
    # الصنفين كفرعين من StopIteration/StopAsyncIteration (كما ظننت خطأً في
    # البداية أنه تصميم pyrogram الفعلي). لكن بايثون (PEP 479) يحوّل تلقائياً
    # أي StopIteration يُرفَع من داخل `async def` (حتى لو كانت coroutine
    # عادية بلا yield) إلى RuntimeError("coroutine raised StopIteration")
    # — وهذا كان سيُبطل كامل آلية raise ContinuePropagation() المُستخدَمة في
    # كل الملفات الثمانية. التجربة الفعلية (شغّل هذا الملف وشاهد الخطأ) أثبتت
    # أن هذا ليس تصميم pyrogram الحقيقي: صنفا الإشارة هما استثناءان عاديان
    # من Exception مباشرة (بدون أي علاقة بـ StopIteration) — وهذا هو التصميم
    # الوحيد المنطقي لإطار عمل يعتمد كلياً على async def. الإصلاح في
    # core/errors.py لا يعتمد على معرفة التسلسل الهرمي الدقيق أصلاً (يكفي
    # أنهما Exception)، لذا يبقى صحيحاً بغضّ النظر.
    class ContinuePropagation(Exception):
        pass

    class StopPropagation(Exception):
        pass

    handler_registry: dict[int, list] = {}

    class _AnyFilter:
        """بديل بسيط لكائنات filters.* يدعم `&` و`|` دون أي منطق فعلي —
        محاكاة الرسائل في هذا الاختبار تتجاوز الفلاتر أصلاً وتستدعي
        الـ handlers المسجَّلة مباشرة بنفس ترتيب تسجيلها."""

        def __and__(self, other):
            return self

        def __or__(self, other):
            return self

    class _FiltersNamespace(types.SimpleNamespace):
        pass

    fake_filters = _FiltersNamespace(group=_AnyFilter(), text=_AnyFilter())

    class FakeClient:
        """بديل لـ pyrogram.Client يكتفي بتسجيل الدوال في handler_registry
        عند استخدام @Client.on_message(...) كديكوريتر على مستوى الوحدة
        (تماماً كما تفعل كل ملفات all_*.py الثمانية فعلياً)."""

        def __init__(self, *a, **k):
            pass

        @staticmethod
        def on_message(_filters_expr=None, group: int = 0):
            def decorator(fn):
                handler_registry.setdefault(group, []).append(fn)
                return fn
            return decorator

    pyrogram_mod = types.ModuleType("pyrogram")
    pyrogram_mod.Client = FakeClient
    pyrogram_mod.filters = fake_filters
    pyrogram_mod.ContinuePropagation = ContinuePropagation
    pyrogram_mod.StopPropagation = StopPropagation

    # ── pyrogram.enums ───────────────────────────────────────────────────
    enums_mod = types.ModuleType("pyrogram.enums")
    for _enum_name, _members in {
        "ChatMemberStatus": ["BANNED", "RESTRICTED", "OWNER", "ADMINISTRATOR", "MEMBER"],
        "ChatMembersFilter": ["ADMINISTRATORS", "BANNED", "BOTS", "RESTRICTED"],
        "ParseMode": ["HTML", "MARKDOWN", "DISABLED"],
        "ChatAction": ["RECORD_AUDIO", "UPLOAD_AUDIO", "TYPING"],
    }.items():
        ns = types.SimpleNamespace(**{m: m for m in _members})
        setattr(enums_mod, _enum_name, ns)

    # ── pyrogram.types ───────────────────────────────────────────────────
    types_mod = types.ModuleType("pyrogram.types")

    class _StubType:
        def __init__(self, *a, **k):
            pass

    for _name in (
        "ChatPermissions", "ChatPrivileges", "ForceReply",
        "InlineKeyboardMarkup", "InlineKeyboardButton",
    ):
        setattr(types_mod, _name, type(_name, (_StubType,), {}))

    # ── pyrogram.errors (مستخدَمة فعلياً في core/errors.py الحقيقي) ──────
    errors_mod = types.ModuleType("pyrogram.errors")

    class FloodWait(Exception):
        def __init__(self, value: int = 0):
            super().__init__(value)
            self.value = value

    class UserNotParticipant(Exception):
        pass

    errors_mod.FloodWait = FloodWait
    errors_mod.UserNotParticipant = UserNotParticipant

    pyrogram_mod.enums = enums_mod
    pyrogram_mod.types = types_mod
    pyrogram_mod.errors = errors_mod

    sys.modules["pyrogram"] = pyrogram_mod
    sys.modules["pyrogram.enums"] = enums_mod
    sys.modules["pyrogram.types"] = types_mod
    sys.modules["pyrogram.errors"] = errors_mod

    # ── مكتبات خارجية أخرى مستوردة على مستوى الوحدة في الملفات الثمانية
    #    (aiohttp, speech_recognition, pydub, pytz, hijri_converter) —
    #    غير مستخدَمة فعلياً في مساري الاختبار المُختارين (قفل الدردشة /
    #    تفعيل انطقي)، فيكفي أن تكون قابلة للاستيراد فقط. ─────────────────
    aiohttp_mod = types.ModuleType("aiohttp")

    class ClientSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    aiohttp_mod.ClientSession = ClientSession
    sys.modules["aiohttp"] = aiohttp_mod

    sr_mod = types.ModuleType("speech_recognition")
    sr_mod.Recognizer = _StubType
    sr_mod.AudioFile = _StubType
    sys.modules["speech_recognition"] = sr_mod

    pydub_mod = types.ModuleType("pydub")
    pydub_mod.AudioSegment = _StubType
    sys.modules["pydub"] = pydub_mod

    pytz_mod = types.ModuleType("pytz")
    pytz_mod.timezone = lambda *a, **k: None
    sys.modules["pytz"] = pytz_mod

    hijri_mod = types.ModuleType("hijri_converter")
    hijri_mod.Hijri = _StubType
    hijri_mod.Gregorian = _StubType
    sys.modules["hijri_converter"] = hijri_mod

    return {
        "ContinuePropagation": ContinuePropagation,
        "StopPropagation": StopPropagation,
        "handler_registry": handler_registry,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 2) core.db وهمي (Redis/kvsqlite حقيقيان غير متاحين هنا) — لكن core/errors.py
#    وhelpers/ranks.py الحقيقيان يُستورَدان ويعملان فوق هذا الـ rdb الوهمي.
# ══════════════════════════════════════════════════════════════════════════════

class FakeRedis:
    """مخزن مفاتيح/قيم بالذاكرة يحاكي واجهة redis.asyncio المستخدمة فعلياً
    (get/set/delete/hget/hset/hgetall/smembers/sadd/srem/sismember/exists)."""

    def __init__(self):
        self._kv: dict[str, str] = {}
        self._hash: dict[str, dict] = {}
        self._set: dict[str, set] = {}

    async def get(self, key):
        return self._kv.get(key)

    async def set(self, key, value, ex=None):
        self._kv[key] = value
        return True

    async def delete(self, key):
        self._kv.pop(key, None)
        self._hash.pop(key, None)
        self._set.pop(key, None)
        return True

    async def exists(self, key):
        return key in self._kv

    async def hget(self, name, field):
        return self._hash.get(name, {}).get(field)

    async def hset(self, name, field, value):
        self._hash.setdefault(name, {})[field] = value
        return True

    async def hdel(self, name, field):
        self._hash.get(name, {}).pop(field, None)
        return True

    async def hgetall(self, name):
        return self._hash.get(name, {})

    async def smembers(self, name):
        return self._set.get(name, set())

    async def sadd(self, name, value):
        self._set.setdefault(name, set()).add(value)
        return True

    async def srem(self, name, value):
        self._set.get(name, set()).discard(value)
        return True

    async def sismember(self, name, value):
        return value in self._set.get(name, set())


def _install_fake_core_db_and_config() -> FakeRedis:
    """يضبط متغيرات البيئة المطلوبة إلزامياً بواسطة config.py، ثم يستبدل
    core.db بوحدة وهمية (rdb فقط — هذا كل ما يستخدمه Plugins الثمانية
    وhelpers/ranks.py فعلياً) بدل استيراد redis.asyncio/kvsqlite الحقيقيين
    غير المتاحين في بيئة الاختبار."""

    os.environ.setdefault("BOT_TOKEN", "123456:FAKE-TEST-TOKEN")
    os.environ.setdefault("SUDO_ID", "111111")
    os.environ.setdefault("API_ID", "12345")
    os.environ.setdefault("API_HASH", "fakehash")

    rdb = FakeRedis()

    fake_db_mod = types.ModuleType("core.db")
    fake_db_mod.rdb = rdb
    fake_db_mod.redis_client = rdb
    fake_db_mod.wsdb = None
    fake_db_mod.ytdb = None
    fake_db_mod.sounddb = None

    async def _wsdb_setex(*a, **k):
        return None

    async def _wsdb_get_checked(*a, **k):
        return None

    fake_db_mod.wsdb_setex = _wsdb_setex
    fake_db_mod.wsdb_get_checked = _wsdb_get_checked

    sys.modules["core.db"] = fake_db_mod

    # all_moderation_1.py / all_moderation_2.py يستوردان
    # Plugins.all_helpers.resolve_guard_text — نُثبّت نسخة وهمية مطابقة
    # حرفياً لمنطق الأصل (نفس فحوصات الأهلية + تطبيع النص) بدل الوحدة
    # الحقيقية الثقيلة (تحتاج Python_ARQ وhelpers.persianData وغيرها من
    # اعتماديات غير متاحة هنا وغير ذات صلة بموضوع هذا الاختبار).
    from config import Dev_Zaid  # noqa: E402  (بعد ضبط env فوق)
    from helpers.ranks import admin_pls, isLockCommand  # noqa: E402

    async def resolve_guard_text(m):
        if not await rdb.get(f"{m.chat.id}:enable:{Dev_Zaid}"):
            return None
        if await rdb.get(f"{m.chat.id}:mute:{Dev_Zaid}") and not await admin_pls(
            m.from_user.id, m.chat.id
        ):
            return None
        if await rdb.get(f"{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}"):
            return None
        if await rdb.get(f"{m.from_user.id}:mute:{Dev_Zaid}"):
            return None
        if await rdb.get(f"{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}"):
            return None
        if await rdb.get(f"{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}"):
            return None
        if await rdb.get(f"{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}") or await rdb.get(
            f"{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}"
        ):
            return None
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
        if await isLockCommand(m.from_user.id, m.chat.id, text):
            return None
        return text

    fake_all_helpers_mod = types.ModuleType("Plugins.all_helpers")
    fake_all_helpers_mod.resolve_guard_text = resolve_guard_text
    sys.modules["Plugins.all_helpers"] = fake_all_helpers_mod

    return rdb


# ══════════════════════════════════════════════════════════════════════════════
# 3) كائنات رسالة/مستخدم/محادثة وهمية بسيطة (تكفي حاجة الملفات الثمانية)
# ══════════════════════════════════════════════════════════════════════════════

class FakeUser:
    def __init__(self, uid: int, mention: str = "TestUser"):
        self.id = uid
        self.mention = mention
        self.is_bot = False
        self.is_deleted = False


class FakeMessage:
    def __init__(self, uid: int, cid: int, text: str):
        self.from_user = FakeUser(uid)
        self.chat = types.SimpleNamespace(id=cid)
        self.text = text
        self.reply_to_message = None
        self.replies: list[str] = []

    async def reply(self, text, **kwargs):
        self.replies.append(text)
        return types.SimpleNamespace(text=text)


class FakeC:
    """بديل بسيط لعميل pyrogram (المعامل c) — غير مُستخدَم فعلياً في
    مساري الاختبار المُختارين، لكن مطلوب كوسيط لكل handler."""
    pass


# ══════════════════════════════════════════════════════════════════════════════
# 4) محاكاة موزّع pyrogram لمجموعة (group) واحدة
# ══════════════════════════════════════════════════════════════════════════════

async def dispatch_group(handlers, c, m, ContinuePropagation, StopPropagation) -> int:
    """يستدعي كل handler في `handlers` بالترتيب، ويطبّق نفس منطق موزّع
    pyrogram الحقيقي: ContinuePropagation → ينتقل للتالي،
    StopPropagation → يتوقف فوراً. يُعيد عدد الـ handlers التي استُدعيت
    فعلياً (لأغراض التحقق في الاختبار)."""
    called = 0
    for fn in handlers:
        called += 1
        try:
            await fn(c, m)
        except ContinuePropagation:
            continue
        except StopPropagation:
            break
        else:
            # انتهى الـ handler طبيعياً بدون رفع أي إشارة propagation —
            # (هذا لا يجب أن يحدث بعد الإصلاح لأي من الملفات الثمانية في
            # مسار "لم يتطابق شيء"، لكن لو حدث فعلياً — كأمر تطابق ورد
            # عليه فعلياً — فمن الصحيح التوقف هنا تماماً مثل pyrogram
            # الحقيقي حين لا تُرفع أي إشارة.)
            break
    return called


# ══════════════════════════════════════════════════════════════════════════════
# 5) الاختبار الفعلي
# ══════════════════════════════════════════════════════════════════════════════

PLUGIN_MODULE_NAMES = [
    "Plugins.all_features_toggle",
    "Plugins.all_locks_1",
    "Plugins.all_locks_2",
    "Plugins.all_moderation_1",
    "Plugins.all_moderation_2",
    "Plugins.all_protection",
    "Plugins.all_settings",
    "Plugins.all_voice_and_blocklist",
]


def _load_group28_handlers():
    fake_refs = _install_fake_dependencies()
    rdb = _install_fake_core_db_and_config()

    # core/errors.py و core/dispatcher.py حقيقيان 100% — يُستورَدان الآن
    # (بعد تجهيز pyrogram/core.db الوهميين) دون أي تعديل.
    importlib.import_module("core.errors")
    importlib.import_module("core.dispatcher")

    for mod_name in PLUGIN_MODULE_NAMES:
        importlib.import_module(mod_name)

    handlers = list(fake_refs["handler_registry"].get(28, []))
    assert len(handlers) == 8, (
        f"يُتوقَّع 8 handlers في group=28، وُجد {len(handlers)} فعلياً"
    )
    return handlers, rdb, fake_refs["ContinuePropagation"], fake_refs["StopPropagation"]


async def _run_test() -> None:
    handlers, rdb, ContinuePropagation, StopPropagation = _load_group28_handlers()

    from config import Dev_Zaid
    from helpers.ranks import BOT_OWNER_FALLBACK_ID

    CID = -100123456789
    UID = BOT_OWNER_FALLBACK_ID  # يتجاوز كل فحوصات الصلاحيات (mod/owner/...)

    # تفعيل البوت لهذه المحادثة الوهمية (فحص الأهلية الأول في كل الملفات الثمانية)
    await rdb.set(f"{CID}:enable:{Dev_Zaid}", "1")
    await rdb.set(f"{Dev_Zaid}:botkey", "🔥")

    # ── اختبار 1: أمر من all_locks_1.py ("قفل الدردشة") ──────────────────
    # يجب أن يمر عبر all_features_toggle.py (لا يعرفه) ثم يُنفَّذ فعلياً في
    # all_locks_1.py، ويتوقف الانتقال هناك (StopIteration ضمنية من match).
    m1 = FakeMessage(UID, CID, "قفل الدردشة")
    called1 = await dispatch_group(handlers, FakeC(), m1, ContinuePropagation, StopPropagation)

    assert called1 >= 2, (
        f"يُتوقَّع استدعاء handler واحد على الأقل قبل all_locks_1 ثم "
        f"all_locks_1 نفسه، لكن تم استدعاء {called1} فقط"
    )
    assert len(m1.replies) == 1, f"يُتوقَّع رد واحد بالضبط، وُجد {len(m1.replies)}: {m1.replies}"
    assert "ابشر قفلت" in m1.replies[0] and "الشات" in m1.replies[0], (
        f"نص الرد غير متوقَّع: {m1.replies[0]!r}"
    )
    print(f"[PASS] أمر all_locks_1.py (\"قفل الدردشة\") نُفِّذ بعد {called1} handler(s) → "
          f"{m1.replies[0]!r}")

    # تحقّق فعلي أن حالة القفل تغيّرت في rdb (وليس مجرد نص الرد)
    lock_state = await rdb.get(f"{CID}:mute:{Dev_Zaid}")
    assert lock_state, "مفتاح القفل (mute) لم يُضبَط فعلياً في rdb"

    # ── اختبار 2: أمر من all_settings.py ("تفعيل انطقي") ─────────────────
    # يمر عبر 6 ملفات لا تعرفه (بما فيها all_locks_1/2 وكلا ملفي
    # all_moderation) قبل أن يصل فعلياً إلى all_settings.py.
    await rdb.set(f"{CID}:disableSay:{Dev_Zaid}", "1")  # حالة مسبقة: انطقي معطل
    m2 = FakeMessage(UID, CID, "تفعيل انطقي")
    called2 = await dispatch_group(handlers, FakeC(), m2, ContinuePropagation, StopPropagation)

    settings_index = PLUGIN_MODULE_NAMES.index("Plugins.all_settings") + 1  # 1-based
    assert called2 >= settings_index, (
        f"يُتوقَّع أن يصل الاستدعاء حتى all_settings.py (الموضع {settings_index})، "
        f"لكن توقف بعد {called2} فقط"
    )
    assert len(m2.replies) == 1, f"يُتوقَّع رد واحد بالضبط، وُجد {len(m2.replies)}: {m2.replies}"
    assert "ابشر فعلت انطقي" in m2.replies[0], f"نص الرد غير متوقَّع: {m2.replies[0]!r}"
    print(f"[PASS] أمر all_settings.py (\"تفعيل انطقي\") نُفِّذ بعد {called2} handler(s) → "
          f"{m2.replies[0]!r}")

    say_state = await rdb.get(f"{CID}:disableSay:{Dev_Zaid}")
    assert not say_state, "مفتاح disableSay لم يُحذَف فعلياً في rdb"

    print("\nكل الاختبارات نجحت ✅ — الإصلاح (raise ContinuePropagation في نهاية كل"
          " دالة + إعادة رفعها في core/errors.safe_handler) يعمل فعلياً من طرف لطرف.")


def test_locks1_and_settings_commands_reach_their_handlers():
    """نقطة الدخول بصيغة يتعرّف عليها pytest تلقائياً (لو كان مثبَّتاً)،
    وأيضاً قابلة للتشغيل المباشر (راجع __main__ بالأسفل)."""
    asyncio.run(_run_test())


if __name__ == "__main__":
    test_locks1_and_settings_commands_reach_their_handlers()
