"""
core/cache.py — bmqa-v2
ذاكرة تخزين مؤقت لأعضاء المجموعات (admins / members).

المُصدَّرات:
  members_cache — كائن MembersCache جاهز للاستخدام

الاستخدام النموذجي:
    admins = await members_cache.get_admins(c, chat_id, ChatMembersFilter.ADMINISTRATORS)
    members_cache.invalidate_chat(chat_id)
"""
from __future__ import annotations

import time
from typing import Any

from pyrogram.enums import ChatMembersFilter

_TTL = 300


class MembersCache:
    def __init__(self, ttl: int = _TTL):
        self._ttl = ttl
        self._store: dict[tuple, tuple[list, float]] = {}

    async def get_admins(
        self, c: Any, chat_id: int, filter: ChatMembersFilter
    ) -> list:
        key = (chat_id, filter)
        cached = self._store.get(key)
        if cached and (time.monotonic() - cached[1]) < self._ttl:
            return cached[0]
        members = [m async for m in c.get_chat_members(chat_id, filter=filter)]
        self._store[key] = (members, time.monotonic())
        return members

    def invalidate_chat(self, chat_id: int) -> None:
        to_del = [k for k in self._store if k[0] == chat_id]
        for k in to_del:
            del self._store[k]


members_cache = MembersCache()
