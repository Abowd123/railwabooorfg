"""
core/db.py — bmqa-v2
عملاء قواعد البيانات غير المتزامنة (async).

المُصدَّرات:
  rdb          — عميل Redis غير متزامن (redis.asyncio)
  wsdb         — قاعدة بيانات SQLite للهمسات (kvsqlite)
  ytdb         — قاعدة بيانات SQLite لليوتيوب (kvsqlite)
  sounddb      — قاعدة بيانات SQLite للساوند (kvsqlite)
  redis_client — نفس rdb (اسم بديل لـ main.py)

التحويل عن النسخة الأصلية (all.py المتزامن):
  r.get(key)           → await rdb.get(key)          — يُعيد str | None
  r.set(key, val)      → await rdb.set(key, val)
  r.set(key, val, ex=) → await rdb.set(key, val, ex=)
  r.delete(key)        → await rdb.delete(key)
  r.sismember(s, v)    → await rdb.sismember(s, v)
  r.sadd(s, v)         → await rdb.sadd(s, v)
  r.srem(s, v)         → await rdb.srem(s, v)
  r.smembers(s)        → await rdb.smembers(s)
  r.hget(h, f)         → await rdb.hget(h, f)
  r.hset(h, f, v)      → await rdb.hset(h, f, v)
  r.hdel(h, f)         → await rdb.hdel(h, f)
  r.hgetall(h)         → await rdb.hgetall(h)
  r.ttl(key)           → await rdb.ttl(key)
  r.exists(key)        → await rdb.exists(key)
  r.keys(pattern)      → await rdb.keys(pattern)
  r.scan_iter(pattern) → rdb.scan_iter(pattern)  [async generator]

ملاحظة: كل القيم المُعادة من rdb هي str (كما في redis-py الأصلي مع decode_responses=True).
"""

import redis.asyncio as aioredis
from kvsqlite import Client as KVSqliteDB

from config import (
    redis_host, redis_port, redis_db, redis_password,
    WSDB_PATH, YTDB_PATH, SOUNDDB_PATH,
)

rdb: aioredis.Redis = aioredis.Redis(
    host=redis_host,
    port=redis_port,
    db=redis_db,
    password=redis_password,
    decode_responses=True,
)

redis_client = rdb

wsdb: KVSqliteDB = KVSqliteDB(WSDB_PATH)
ytdb: KVSqliteDB = KVSqliteDB(YTDB_PATH)
sounddb: KVSqliteDB = KVSqliteDB(SOUNDDB_PATH)


# ============================================================
# TTL حقيقي فوق wsdb (kvsqlite لا يوفّر setex)
# ============================================================
# إصلاح لملاحظة AMBIGUOUS [B1] في Plugins/all_moderation_1.py: النسخة
# الأصلية المتزامنة كانت تستخدم wsdb.setex(key=id, ttl=3600, value=data)
# لأمر "اهمس" (تنتهي صلاحية رابط الهمسة المبدئي بعد ساعة). KVSqliteDB
# الحالية لا تدعم TTL فعلياً، فنحاكيه هنا بمؤشر انتهاء بسيط في Redis
# (الذي يدعم TTL أصلاً) بدون أي تغيير على شكل البيانات المخزّنة بـ wsdb.
async def wsdb_setex(key: str, value, ttl: int) -> None:
    """يخزّن قيمة في wsdb مع صلاحية TTL حقيقية (يُستخدم فقط لمفاتيح
    "اهمس" المؤقتة — لا تستخدمه لمفاتيح wsdb الدائمة الأخرى مثل
    hms-*/hmsa-* التي لم تكن تملك TTL أصلاً بالنسخة الأصلية)."""
    await wsdb.set(key, value)
    await rdb.set(f"_wsdb_ttl:{key}", 1, ex=ttl)


async def wsdb_get_checked(key: str):
    """يقرأ مفتاحاً خُزِّن عبر wsdb_setex، ويحترم انتهاء صلاحيته: لو
    انتهت الصلاحية (أو لم تُخزَّن أصلاً بهذا الأسلوب) يحذف القيمة من
    wsdb ويُرجع None، بدل ما تبقى محفوظة للأبد."""
    value = await wsdb.get(key)
    if value is None:
        return None
    if not await rdb.exists(f"_wsdb_ttl:{key}"):
        await wsdb.delete(key)
        return None
    return value
