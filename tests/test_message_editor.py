"""
tests/test_message_editor.py — bmqa-v2

اختبار بسيط ومستقل (script منفصل، وليس pytest — بنفس نمط
tests/test_group28_continue_propagation.py وtests/test_chat_members_cache.py)
لطبقة core/messages.py وميزة Plugins/message_editor.py.

الاعتماديات الخارجية غير المتاحة في بيئة الاختبار (pyrogram/kurigram
الحقيقية، redis) مُستبدَلة بوحدات وهمية بسيطة قبل الاستيراد، تماماً كما في
tests/test_group28_continue_propagation.py — core/messages.py وhelpers/ranks.py
وPlugins/message_editor.py نفسها تُستورَد وتُنفَّذ حرفياً من المشروع الحقيقي
دون أي تعديل أو نسخ.

نقطة مهمة عن اختبار TTL (البند 5): بدل الانتظار الفعلي 5 دقائق، FakeRedis هنا
تستخدم "ساعة" وهمية (FakeClock) بدل time.time() الحقيقي، بحيث يمكن تقديم
الوقت فوراً (clock.advance(301)) لإثبات أن المفتاح ينتهي فعلياً بعد TTL=300
بالضبط، دون إبطاء الاختبار.

يغطي هذا الملف:
  1. get_message() يرجع النص الافتراضي عند عدم وجود override.
  2. get_message() يرجع النص المخصّص بعد set_message_override().
  3. set_message_override() يرفض placeholder غير معروف ولا يحفظ شيئاً.
  4. reset_message() يعيد النص للافتراضي فعلياً.
  5. حالة "بانتظار تعديل" تنتهي تلقائياً بعد TTL=300 ثانية بالضبط ولا تُقبل
     رسائل بعده (تُعامَل كأنه لا توجد حالة نشطة إطلاقاً).
  6. مستخدم بدون صلاحية Developer يُرفض عند أي محاولة استخدام لأي أمر من
     أوامر Plugins/message_editor.py (الأوامر الست المحمية).

يُشغَّل مباشرة: python3 tests/test_message_editor.py
(أو عبر pytest إن كان متاحاً: pytest tests/test_message_editor.py)
"""

from __future__ import annotations

import asyncio
import fnmatch
import os
import sys
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ══════════════════════════════════════════════════════════════════════════════
# 1) وحدات وهمية للاعتماديات الخارجية غير المثبَّتة (pyrogram وما يتفرّع عنه)
# ══════════════════════════════════════════════════════════════════════════════

def _install_fake_pyrogram() -> dict:
    """يُسجِّل pyrogram وهمية (Client/filters/ContinuePropagation/StopPropagation
    + الأنواع المستخدَمة في Plugins/message_editor.py) في sys.modules، بنفس
    أسلوب tests/test_group28_continue_propagation.py."""

    class ContinuePropagation(Exception):
        pass

    class StopPropagation(Exception):
        pass

    handler_registry: dict[int, list] = {}

    class _AnyFilter:
        def __and__(self, other):
            return self

        def __or__(self, other):
            return self

    def _regex(*a, **k):
        return _AnyFilter()

    fake_filters = types.SimpleNamespace(
        text=_AnyFilter(), group=_AnyFilter(), regex=_regex
    )

    class FakeClient:
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

    enums_mod = types.ModuleType("pyrogram.enums")
    for _enum_name, _members in {
        "ChatMemberStatus": ["BANNED", "RESTRICTED", "OWNER", "ADMINISTRATOR", "MEMBER"],
        "ChatMembersFilter": ["ADMINISTRATORS", "BANNED", "BOTS", "RESTRICTED"],
        "ParseMode": ["HTML", "MARKDOWN", "DISABLED"],
        "ChatAction": ["RECORD_AUDIO", "UPLOAD_AUDIO", "TYPING"],
    }.items():
        ns = types.SimpleNamespace(**{m: m for m in _members})
        setattr(enums_mod, _enum_name, ns)

    types_mod = types.ModuleType("pyrogram.types")

    class _StubType:
        def __init__(self, *a, **k):
            self.args = a
            self.kwargs = k

    for _name in (
        "ChatPermissions", "ChatPrivileges", "ForceReply",
        "InlineKeyboardMarkup", "InlineKeyboardButton",
    ):
        setattr(types_mod, _name, type(_name, (_StubType,), {}))

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

    return {
        "ContinuePropagation": ContinuePropagation,
        "StopPropagation": StopPropagation,
        "handler_registry": handler_registry,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 2) core.db وهمي — FakeRedis بساعة وهمية (FakeClock) لمحاكاة TTL دون انتظار
#    حقيقي، + دعم .keys(pattern) المستخدَم في أمر "تصدير_الردود".
# ══════════════════════════════════════════════════════════════════════════════

class FakeClock:
    """ساعة وهمية بسيطة يمكن تقديمها يدوياً؛ تُستخدَم بدل time.time() الحقيقي
    داخل FakeRedis حتى يمكن اختبار انتهاء TTL فوراً دون إبطاء الاختبار."""

    def __init__(self) -> None:
        self.now: float = 1_000_000.0

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeRedis:
    """مخزن مفاتيح/قيم بالذاكرة يحاكي واجهة redis.asyncio المستخدمة فعلياً في
    core/messages.py وPlugins/message_editor.py وhelpers/ranks.py:
    get/set(ex=)/delete/exists/keys(pattern)."""

    def __init__(self, clock: FakeClock) -> None:
        self.clock = clock
        # key -> (value: str, expire_at: float | None)
        self._kv: dict[str, tuple[str, float | None]] = {}

    async def get(self, key):
        item = self._kv.get(key)
        if item is None:
            return None
        value, expire_at = item
        if expire_at is not None and self.clock.now >= expire_at:
            self._kv.pop(key, None)
            return None
        return value

    async def set(self, key, value, ex=None):
        expire_at = (self.clock.now + ex) if ex else None
        self._kv[key] = (str(value), expire_at)
        return True

    async def delete(self, key):
        self._kv.pop(key, None)
        return True

    async def exists(self, key):
        return (await self.get(key)) is not None

    async def keys(self, pattern):
        alive_keys = [k for k in list(self._kv.keys()) if await self.get(k) is not None]
        return [k for k in alive_keys if fnmatch.fnmatch(k, pattern)]


def _install_fake_core_db_and_config() -> tuple[FakeRedis, FakeClock]:
    """يضبط متغيرات البيئة المطلوبة إلزامياً بواسطة config.py، ثم يستبدل
    core.db بوحدة وهمية (rdb فقط) بدل استيراد redis.asyncio/kvsqlite
    الحقيقيين غير المتاحين في بيئة الاختبار — نفس أسلوب
    tests/test_group28_continue_propagation.py."""

    os.environ.setdefault("BOT_TOKEN", "123456:FAKE-TEST-TOKEN")
    os.environ.setdefault("SUDO_ID", "111111")
    os.environ.setdefault("API_ID", "12345")
    os.environ.setdefault("API_HASH", "fakehash")

    clock = FakeClock()
    rdb = FakeRedis(clock)

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

    return rdb, clock


def _run_async(coro):
    return asyncio.run(coro)


# ══════════════════════════════════════════════════════════════════════════════
# 3) تجهيز البيئة واستيراد الوحدات الحقيقية (مرة واحدة لكل تشغيل)
# ══════════════════════════════════════════════════════════════════════════════

_fake_refs = _install_fake_pyrogram()
_rdb, _clock = _install_fake_core_db_and_config()

import importlib  # noqa: E402

# core/messages.py وcore/keys.py وhelpers/ranks.py حقيقيون 100% — يُستورَدون
# الآن بعد تجهيز pyrogram/core.db الوهميين، دون أي تعديل أو نسخ.
core_messages = importlib.import_module("core.messages")
core_keys = importlib.import_module("core.keys")
ranks_mod = importlib.import_module("helpers.ranks")

DEFAULT_MESSAGES = core_messages.DEFAULT_MESSAGES
get_message = core_messages.get_message
set_message_override = core_messages.set_message_override
reset_message = core_messages.reset_message
list_message_ids = core_messages.list_message_ids
message_override_key = core_keys.message_override_key

import core.dispatcher as core_dispatcher  # noqa: E402
import core.callback_dispatcher as core_callback_dispatcher  # noqa: E402
import core.errors as core_errors  # noqa: E402

message_editor = importlib.import_module("Plugins.message_editor")

from config import Dev_Zaid  # noqa: E402


# ══════════════════════════════════════════════════════════════════════════════
# 4) كائنات رسالة/مستخدم وهمية بسيطة — لاستدعاء handlers الأمر الحقيقية مباشرة
# ══════════════════════════════════════════════════════════════════════════════

class FakeUser:
    def __init__(self, uid: int, mention: str = "TestUser"):
        self.id = uid
        self.mention = mention


class FakeMessage:
    def __init__(self, uid: int, cid: int, text: str, reply_to_message=None):
        self.from_user = FakeUser(uid)
        self.chat = types.SimpleNamespace(id=cid)
        self.text = text
        self.reply_to_message = reply_to_message
        self.replies: list[str] = []

    async def reply(self, text=None, quote=None, reply_markup=None, **kwargs):
        self.replies.append(text)
        return types.SimpleNamespace(text=text)


class FakeC:
    pass


TEST_MESSAGE_ID = "lock_chat"  # موجود فعلياً ضمن DEFAULT_MESSAGES (المرحلة A)


def _reset_message_state():
    """يمسح أي override لِـ TEST_MESSAGE_ID قبل كل اختبار لعزل الحالات."""
    _rdb._kv.pop(message_override_key(TEST_MESSAGE_ID), None)


# ══════════════════════════════════════════════════════════════════════════════
# 5) الاختبارات
# ══════════════════════════════════════════════════════════════════════════════

async def test_get_message_returns_default_without_override():
    print("1) get_message() يرجع النص الافتراضي عند عدم وجود override ... ", end="")
    _reset_message_state()

    rendered = await get_message(TEST_MESSAGE_ID, botkey="🔥", mention="أحمد", feature="الشات")
    expected = DEFAULT_MESSAGES[TEST_MESSAGE_ID].format(botkey="🔥", mention="أحمد", feature="الشات")

    assert rendered == expected, f"النص غير مطابق للافتراضي: {rendered!r} != {expected!r}"
    print("OK")


async def test_get_message_returns_custom_after_override():
    print("2) get_message() يرجع النص المخصّص بعد set_message_override() ... ", end="")
    _reset_message_state()

    custom = "{botkey} تم قفل {feature} بواسطة {mention} ✅"
    await set_message_override(TEST_MESSAGE_ID, custom)

    rendered = await get_message(TEST_MESSAGE_ID, botkey="🔥", mention="أحمد", feature="الشات")
    expected = custom.format(botkey="🔥", mention="أحمد", feature="الشات")

    assert rendered == expected, f"النص المخصّص لم يُستخدَم: {rendered!r} != {expected!r}"
    _reset_message_state()
    print("OK")


async def test_set_message_override_rejects_unknown_placeholder():
    print("3) set_message_override() يرفض placeholder غير معروف ولا يحفظ شيئاً ... ", end="")
    _reset_message_state()

    bad_text = "{botkey} {mention} {feature} {hacker_injected_field}"
    raised = False
    try:
        await set_message_override(TEST_MESSAGE_ID, bad_text)
    except ValueError:
        raised = True

    assert raised, "توقعنا ValueError عند placeholder غير معروف، لم يُرفَع شيء"

    stored = await _rdb.get(message_override_key(TEST_MESSAGE_ID))
    assert stored is None, f"لم يكن يجب حفظ أي شيء، لكن وُجد: {stored!r}"
    print("OK")


async def test_reset_message_restores_default():
    print("4) reset_message() يعيد النص للافتراضي فعلياً ... ", end="")
    _reset_message_state()

    await set_message_override(TEST_MESSAGE_ID, "{botkey} نص مخصّص مؤقت {mention} {feature}")
    customized = await get_message(TEST_MESSAGE_ID, botkey="🔥", mention="أحمد", feature="الشات")
    default_rendered = DEFAULT_MESSAGES[TEST_MESSAGE_ID].format(botkey="🔥", mention="أحمد", feature="الشات")
    assert customized != default_rendered, "الخطوة التحضيرية فشلت: التخصيص لم يُطبَّق أصلاً"

    await reset_message(TEST_MESSAGE_ID)

    after_reset = await get_message(TEST_MESSAGE_ID, botkey="🔥", mention="أحمد", feature="الشات")
    assert after_reset == default_rendered, (
        f"لم يعد النص للافتراضي بعد reset_message(): {after_reset!r} != {default_rendered!r}"
    )
    print("OK")


async def test_pending_edit_expires_after_ttl_and_rejects_messages():
    print("5) حالة \"بانتظار تعديل\" تنتهي فعلياً بعد TTL=300 ثانية ... ", end="")

    DEV_UID = 700000001
    CID = -100700000001

    # يمنح DEV_UID صلاحية devp_pls عبر آلية botowner الحقيقية في Redis.
    await _rdb.set(f"{Dev_Zaid}botowner", str(DEV_UID))

    edit_cmd = FakeMessage(DEV_UID, CID, f"تعديل_رد {TEST_MESSAGE_ID}")
    await message_editor.editMessageHandler(FakeC(), edit_cmd)
    assert len(edit_cmd.replies) == 1, "يُتوقَّع رد واحد يبدأ تدفق التعديل"

    pending = await message_editor._get_pending(DEV_UID, CID)
    assert pending == TEST_MESSAGE_ID, f"يُتوقَّع حالة معلَّقة لـ {TEST_MESSAGE_ID}، وُجد {pending!r}"

    # لا يزال داخل نافذة TTL (300 ث بالضبط) — الحالة يجب أن تبقى نشطة.
    _clock.advance(299)
    still_pending = await message_editor._get_pending(DEV_UID, CID)
    assert still_pending == TEST_MESSAGE_ID, "انتهت الحالة قبل اكتمال TTL فعلياً!"

    # تجاوزنا الـ 300 ثانية بالضبط — يجب أن تنتهي الحالة فعلياً الآن.
    _clock.advance(2)
    expired_pending = await message_editor._get_pending(DEV_UID, CID)
    assert expired_pending is None, "الحالة لم تنتهِ بعد تجاوز TTL=300 ثانية"

    # رسالة نصية عادية بعد انتهاء TTL يجب أن تُعامَل كأنه لا توجد حالة نشطة
    # إطلاقاً → raise ContinuePropagation فوراً (بوابة group=17)، وليس محاولة
    # معالجتها كنص تعديل.
    followup = FakeMessage(DEV_UID, CID, "[اسم_البوت] [الشخص] [الميزة]")
    continued = False
    try:
        await message_editor.pendingEditGateHandler(FakeC(), followup)
    except _fake_refs["ContinuePropagation"]:
        continued = True

    assert continued, "توقعنا ContinuePropagation بعد انتهاء TTL، لكن الرسالة عولجت كتعديل نشط"
    assert followup.replies == [], f"لم يكن يجب أي رد بعد انتهاء TTL، وُجد: {followup.replies}"

    print("OK")


async def test_non_developer_is_rejected_on_all_commands():
    print("6) مستخدم بدون صلاحية Developer يُرفض في كل أوامر الميزة ... ", end="")

    NON_DEV_UID = 800000002
    CID = -100800000002

    # نتأكد أن هذا المستخدم ليس مطوّراً بأي طريقة (لا botowner، لا rankDEV*).
    assert not await ranks_mod.dev_pls(NON_DEV_UID, CID)
    assert not await ranks_mod.devp_pls(NON_DEV_UID, CID)

    async def _assert_rejected(coro_factory, label: str):
        msg = FakeMessage(NON_DEV_UID, CID, label)
        await coro_factory(msg)
        assert len(msg.replies) == 1, f"[{label}] يُتوقَّع رد رفض واحد فقط، وُجد {len(msg.replies)}"
        assert message_editor._DEV_PERM in msg.replies[0], (
            f"[{label}] الرد لا يحتوي رسالة الرفض المتوقَّعة: {msg.replies[0]!r}"
        )
        # تأكيد إضافي: لا شيء تغيّر فعلياً (لا حالة معلَّقة، لا override جديد)
        assert await message_editor._get_pending(NON_DEV_UID, CID) is None

    await _assert_rejected(
        lambda m: message_editor.listMessagesHandler(FakeC(), m), "قائمة_الردود"
    )
    await _assert_rejected(
        lambda m: message_editor.viewMessageHandler(FakeC(), m), f"عرض_رد {TEST_MESSAGE_ID}"
    )
    await _assert_rejected(
        lambda m: message_editor.editMessageHandler(FakeC(), m), f"تعديل_رد {TEST_MESSAGE_ID}"
    )
    await _assert_rejected(
        lambda m: message_editor.resetMessageHandler(FakeC(), m), f"استرجاع_رد {TEST_MESSAGE_ID}"
    )
    await _assert_rejected(
        lambda m: message_editor.exportMessagesHandler(FakeC(), m), "تصدير_الردود"
    )
    await _assert_rejected(
        lambda m: message_editor.importMessagesHandler(FakeC(), m), "استيراد_الردود"
    )

    print("OK")


# ══════════════════════════════════════════════════════════════════════════════
# 6) نقطة الدخول
# ══════════════════════════════════════════════════════════════════════════════

async def _run_all() -> None:
    await test_get_message_returns_default_without_override()
    await test_get_message_returns_custom_after_override()
    await test_set_message_override_rejects_unknown_placeholder()
    await test_reset_message_restores_default()
    await test_pending_edit_expires_after_ttl_and_rejects_messages()
    await test_non_developer_is_rejected_on_all_commands()
    print("\nكل الاختبارات نجحت ✅")


def test_message_editor_full_suite():
    """نقطة دخول بصيغة يتعرّف عليها pytest تلقائياً (لو كان مثبَّتاً)."""
    asyncio.run(_run_all())


if __name__ == "__main__":
    asyncio.run(_run_all())
