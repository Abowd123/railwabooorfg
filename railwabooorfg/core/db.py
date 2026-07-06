"""
core/db.py — bmqa-v2
عملاء قواعد البيانات غير المتزامنة (async).
"""

import redis.asyncio as aioredis
from kvsqlite import Client as KVSqliteDB

from config import (
    redis_host, redis_port, redis_db, redis_password,
    WSDB_PATH, YTDB_PATH, SOUNDDB_PATH,
)

# 1. تعريف المتغيرات كـ None في البداية لتأجيل ربطها بالـ Loop
rdb: aioredis.Redis = None
redis_client: aioredis.Redis = None

wsdb: KVSqliteDB = None
ytdb: KVSqliteDB = None
sounddb: KVSqliteDB = None


async def init_databases() -> None:
    """تهيئة الاتصالات بالقواعد داخل الـ Event Loop النشط لمنع تضارب الـ Loops."""
    global rdb, redis_client, wsdb, ytdb, sounddb

    # تهيئة Redis التزامني
    rdb = aioredis.Redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        password=redis_password,
        decode_responses=True,
    )
    redis_client = rdb

    # تهيئة قواعد kvsqlite بمساراتها من الـ config
    wsdb = KVSqliteDB(WSDB_PATH)
    ytdb = KVSqliteDB(YTDB_PATH)
    sounddb = KVSqliteDB(SOUNDDB_PATH)


# ============================================================
# TTL حقيقي فوق wsdb (kvsqlite لا يوفّر setex)
# ============================================================
async def wsdb_setex(key: str, value, ttl: int) -> None:
    """يخزّن قيمة في wsdb مع صلاحية TTL حقيقية."""
    await wsdb.set(key, value)
    await rdb.set(f"_wsdb_ttl:{key}", 1, ex=ttl)


async def wsdb_get_checked(key: str):
    """يقرأ مفتاحاً خُزِّن عبر wsdb_setex، ويحترم انتهاء صلاحيته."""
    value = await wsdb.get(key)
    if value is None:
        return None
    if not await rdb.exists(f"_wsdb_ttl:{key}"):
        await wsdb.delete(key)
        return None
    return value
