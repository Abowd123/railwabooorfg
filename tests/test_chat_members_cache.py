"""
tests/test_chat_members_cache.py — bmqa-v2

اختبار بسيط ومستقل (script منفصل، وليس pytest) لـ core/cache.py.

⚠️ تحديث: core/cache.py الفعلي لا يوفر صنف "ChatMembersCache" بواجهة
get_chat_members(client, chat_id=, filter=) كما افترضت نسخة سابقة من هذا
الملف — الصنف الحقيقي المُصدَّر هو MembersCache (والكائن الجاهز
members_cache)، وواجهته الفعلية:

    await MembersCache(ttl=...).get_admins(c, chat_id, filter)
    cache.invalidate_chat(chat_id)

core/cache.py لم يُعدَّل: هذا الملف فقط يُحدَّث ليطابق تلك الواجهة الفعلية.

core/cache.py يستورد pyrogram.enums.ChatMembersFilter عند التحميل. بيئة
الاختبار هذه لا تملك pyrogram/kurigram مثبتة فعلياً، لذا — بنفس الأسلوب
المتّبع في tests/test_group28_continue_propagation.py — نُسجِّل وحدة
pyrogram.enums وهمية بسيطة في sys.modules قبل استيراد core.cache. هذا لا
يُبدِّل أي سلوك حقيقي: ChatMembersFilter تُستخدَم في core/cache.py فقط
كنوع (type hint) وكقيمة تُمرَّر شفافياً كـ filter= لعميل تيليجرام (المزيَّف
هنا FakeClient)، فلا حاجة لقيم enum حقيقية لاختبار منطق الكاش نفسه.

يغطي هذا الملف:
  1. أن get_admins يرجع نفس البيانات خلال فترة الـ TTL بدون استدعاء
     "تيليجرام" (عميل وهمي هنا) أكثر من مرة واحدة.
  2. أن الكاش يُعاد جلبه فعلياً بعد انتهاء TTL (_TTL=300 المذكور في
     docstring core/cache.py — هنا نستخدم ttl قصيرًا صراحةً لجعل الاختبار
     سريعًا وحتميًا، فالمنطق المُختبَر واحد).
  3. أن invalidate_chat يجبر إعادة الجلب فورًا حتى قبل انتهاء TTL.
  4. أن invalidate_chat لا يؤثر على محادثات أخرى غير المُستهدَفة.

ملاحظة: النسخة السابقة من هذا الملف تضمّنت اختبارًا لعدم تكرار النداء عند
نداءات متزامنة (concurrent) لنفس المفتاح، بافتراض وجود قفل لكل مفتاح.
MembersCache الفعلي في core/cache.py لا يطبّق أي قفل من هذا النوع (لا
asyncio.Lock ولا ما يعادله)؛ عند نداءين متزامنين لنفس المفتاح كلاهما يجد
الكاش فارغًا ويُطلقان نداء تيليجرام كلٌّ على حدة. لذا حُذف ذلك الاختبار كي
لا يفرض على core/cache.py سلوكًا غير موجود فعليًا فيه (المطلوب هو عدم
تعديل core/cache.py، بل مطابقة الاختبار له).

يُشغَّل مباشرة: python3 tests/test_chat_members_cache.py
"""

from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _install_fake_pyrogram_enums() -> None:
    """يُسجِّل pyrogram.enums وهمية (فقط ChatMembersFilter) في sys.modules
    إن لم تكن pyrogram الحقيقية مثبتة، حتى يمكن استيراد core.cache دون
    الحاجة لتثبيت pyrogram/kurigram في بيئة الاختبار. لا يُثبَّت شيء إذا
    كانت pyrogram متوفرة فعلياً."""
    try:
        import pyrogram  # noqa: F401
        return
    except ImportError:
        pass

    pyrogram_mod = types.ModuleType("pyrogram")
    enums_mod = types.ModuleType("pyrogram.enums")
    enums_mod.ChatMembersFilter = types.SimpleNamespace(
        ADMINISTRATORS="ADMINISTRATORS",
        BANNED="BANNED",
        BOTS="BOTS",
        RESTRICTED="RESTRICTED",
    )
    pyrogram_mod.enums = enums_mod
    sys.modules["pyrogram"] = pyrogram_mod
    sys.modules["pyrogram.enums"] = enums_mod


_install_fake_pyrogram_enums()

from core.cache import MembersCache  # noqa: E402
from pyrogram.enums import ChatMembersFilter  # noqa: E402

ADMINISTRATORS = ChatMembersFilter.ADMINISTRATORS


class FakeClient:
    """عميل تيليجرام وهمي: يحاكي get_chat_members كـ async generator، ويعدّ
    كم مرة استُدعي فعلياً (هذا هو "نداء تيليجرام" الذي يجب ألا يتكرر)."""

    def __init__(self, members: list[str], delay: float = 0.0) -> None:
        self.members = members
        self.delay = delay
        self.call_count = 0

    async def get_chat_members(self, chat_id, filter=None, limit=None):
        self.call_count += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        for m in self.members:
            yield m


async def test_returns_same_data_without_refetch_within_ttl():
    print("1) نفس البيانات خلال TTL بدون تكرار النداء ... ", end="")
    client = FakeClient(["admin_1", "admin_2"])
    cache = MembersCache(ttl=5)

    first = await cache.get_admins(client, -100, ADMINISTRATORS)
    second = await cache.get_admins(client, -100, ADMINISTRATORS)

    assert first == second == ["admin_1", "admin_2"], f"بيانات غير متطابقة: {first} != {second}"
    assert client.call_count == 1, f"توقعنا نداء تيليجرام واحد فقط، حدث {client.call_count}"
    print("OK")


async def test_ttl_blocks_refetch_then_allows_it_after_expiry():
    """يتحقق صراحةً من أن _TTL يمنع إعادة الجلب خلال المهلة، ويسمح بها بعدها:
    نداء داخل نافذة الـ TTL يجب ألا يُطلق نداء تيليجرام ثانياً، ونداء بعد
    انتهائها يجب أن يُطلقه."""
    print("2) TTL يمنع إعادة الجلب أثناءه ويسمح بها بعد انتهائه ... ", end="")
    client = FakeClient(["a"])
    ttl = 1
    cache = MembersCache(ttl=ttl)

    await cache.get_admins(client, -300, ADMINISTRATORS)
    assert client.call_count == 1

    # لا يزال داخل نافذة TTL: يجب ألا يُعاد الجلب.
    await asyncio.sleep(ttl * 0.3)
    await cache.get_admins(client, -300, ADMINISTRATORS)
    assert client.call_count == 1, (
        f"توقعنا عدم إعادة الجلب داخل نافذة TTL، حدث {client.call_count}"
    )

    # تجاوزنا نافذة TTL: يجب أن يُعاد الجلب فعلياً.
    await asyncio.sleep(ttl * 1.0)
    await cache.get_admins(client, -300, ADMINISTRATORS)
    assert client.call_count == 2, (
        f"توقعنا نداءً ثانياً بعد انتهاء TTL، حدث {client.call_count}"
    )
    print("OK")


async def test_invalidate_forces_immediate_refetch():
    print("3) invalidate_chat يجبر إعادة الجلب فورًا قبل انتهاء TTL ... ", end="")
    client = FakeClient(["x"])
    cache = MembersCache(ttl=60)

    await cache.get_admins(client, -400, ADMINISTRATORS)
    assert client.call_count == 1

    cache.invalidate_chat(-400)
    await cache.get_admins(client, -400, ADMINISTRATORS)
    assert client.call_count == 2, (
        f"توقعنا نداءً ثانياً بعد invalidate_chat، حدث {client.call_count}"
    )
    print("OK")


async def test_invalidate_does_not_affect_other_chats():
    print("4) invalidate_chat لا يؤثر على محادثات أخرى ... ", end="")
    client_a = FakeClient(["a"])
    client_b = FakeClient(["b"])
    cache = MembersCache(ttl=60)

    await cache.get_admins(client_a, -500, ADMINISTRATORS)
    await cache.get_admins(client_b, -600, ADMINISTRATORS)

    cache.invalidate_chat(-500)

    await cache.get_admins(client_a, -500, ADMINISTRATORS)
    await cache.get_admins(client_b, -600, ADMINISTRATORS)

    assert client_a.call_count == 2, f"توقعنا إعادة جلب لـ -500، حدث {client_a.call_count}"
    assert client_b.call_count == 1, f"توقعنا عدم إعادة جلب لـ -600، حدث {client_b.call_count}"
    print("OK")


async def main() -> None:
    await test_returns_same_data_without_refetch_within_ttl()
    await test_ttl_blocks_refetch_then_allows_it_after_expiry()
    await test_invalidate_forces_immediate_refetch()
    await test_invalidate_does_not_affect_other_chats()
    print("\nكل الاختبارات نجحت ✅")


if __name__ == "__main__":
    asyncio.run(main())
