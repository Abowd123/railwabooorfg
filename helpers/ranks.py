"""
helpers/ranks.py — bmqa-v2

مُنقول من bmqa/helpers/Ranks.py (بحروف صغيرة: Ranks.py -> ranks.py، توحيداً
لتسمية الملفات in bmqa-v2).

ملف مساعد بحت يحسب رتبة المستخدم، ويتحقق من صلاحياته، ويجلب قائمة المطورين.
تم إصلاح مشكلة TypeError عند عدم تعيين botowner في الـ Redis.
"""

from typing import Optional

from config import Dev_Zaid, extra_owner_id, sudo_id
from core.db import rdb

async def _get_bot_owner() -> Optional[int]:
    """دالة مساعدة لجلب آيدي المالك (botowner) المُخزَّن في Redis بأمان.

    لا يوجد أي fallback ثابت مكتوب في الكود بعد اليوم: لو لم يُضبط botowner في
    Redis، تُعاد None ببساطة (بدل ثابت مخفي كان يُستخدم قبل ضبط أي مالك).
    راجع أيضاً `extra_owner_id` (من config.py) وهو تحقّق منفصل تماماً، اختياري
    وصريح، يضبطه مالك النسخة بنفسه في .env — ولا علاقة له بقيمة Redis هذه.
    """
    owner = await rdb.get(f'{Dev_Zaid}botowner')
    return int(owner) if owner else None


async def get_rank(id, cid) -> str:
    if extra_owner_id is not None and id == extra_owner_id:
        return 'Aec🎖️'
    if id == int(Dev_Zaid):
        return 'البوت'
    if id == await _get_bot_owner():
        return 'Dev🎖️'
    if await rdb.get(f'{id}:rankDEV2:{Dev_Zaid}'):
        return 'Dev²🎖'
    if await rdb.get(f'{id}:rankDEV:{Dev_Zaid}'):
        return 'Myth🎖️'
    if await rdb.get(f'{id}:gban:{Dev_Zaid}'):
        return 'محظور عام'
    if await rdb.get(f'{id}:mute:{Dev_Zaid}'):
        return 'محظور عام'
    if await rdb.get(f'{cid}:rankGOWNER:{id}{Dev_Zaid}'):
        custom = await rdb.get(f'{cid}:RankGowner:{Dev_Zaid}')
        if custom:
            return custom
        return 'المالك الاساسي'
    if await rdb.get(f'{cid}:rankOWNER:{id}{Dev_Zaid}'):
        custom = await rdb.get(f'{cid}:RankOwner:{Dev_Zaid}')
        if custom:
            return custom
        return 'المالك'
    if await rdb.get(f'{cid}:rankMOD:{id}{Dev_Zaid}'):
        custom = await rdb.get(f'{cid}:RankMod:{Dev_Zaid}')
        if custom:
            return custom
        return 'المدير'
    if await rdb.get(f'{cid}:rankADMIN:{id}{Dev_Zaid}'):
        custom = await rdb.get(f'{cid}:RankAdm:{Dev_Zaid}')
        if custom:
            return custom
        return 'ادمن'
    if await rdb.get(f'{cid}:rankPRE:{id}{Dev_Zaid}'):
        custom = await rdb.get(f'{cid}:RankPre:{Dev_Zaid}')
        if custom:
            return custom
        return 'مميز'
    else:
        custom = await rdb.get(f'{cid}:RankMem:{Dev_Zaid}')
        if custom:
            return custom
        return 'عضو'


async def admin_pls(id, cid) -> bool:
    if extra_owner_id is not None and id == extra_owner_id:
        return True
    if id == int(Dev_Zaid):
        return True
    if id == await _get_bot_owner():
        return True
    if await rdb.get(f'{id}:rankDEV2:{Dev_Zaid}'):
        return True
    if await rdb.get(f'{id}:rankDEV:{Dev_Zaid}'):
        return True
    if await rdb.get(f'{cid}:rankGOWNER:{id}{Dev_Zaid}'):
        return True
    if await rdb.get(f'{cid}:rankOWNER:{id}{Dev_Zaid}'):
        return True
    if await rdb.get(f'{cid}:rankMOD:{id}{Dev_Zaid}'):
        return True
    if await rdb.get(f'{cid}:rankADMIN:{id}{Dev_Zaid}'):
        return True
    else:
        return False


async def mod_pls(id, cid) -> bool:
    if extra_owner_id is not None and id == extra_owner_id:
        return True
    if id == int(Dev_Zaid):
        return True
    if id == await _get_bot_owner():
        return True
    if await rdb.get(f'{id}:rankDEV2:{Dev_Zaid}'):
        return True
    if await rdb.get(f'{id}:rankDEV:{Dev_Zaid}'):
        return True
    if await rdb.get(f'{cid}:rankGOWNER:{id}{Dev_Zaid}'):
        return True
    if await rdb.get(f'{cid}:rankOWNER:{id}{Dev_Zaid}'):
        return True
    if await rdb.get(f'{cid}:rankMOD:{id}{Dev_Zaid}'):
        return True
    else:
        return False


async def owner_pls(id, cid) -> bool:
    if extra_owner_id is not None and id == extra_owner_id:
        return True
    if id == int(Dev_Zaid):
        return True
    if id == await _get_bot_owner():
        return True
    if await rdb.get(f'{id}:rankDEV2:{Dev_Zaid}'):
        return True
    if await rdb.get(f'{id}:rankDEV:{Dev_Zaid}'):
        return True
    if await rdb.get(f'{cid}:rankGOWNER:{id}{Dev_Zaid}'):
        return True
    if await rdb.get(f'{cid}:rankOWNER:{id}{Dev_Zaid}'):
        return True
    else:
        return False


async def gowner_pls(id, cid) -> bool:
    if extra_owner_id is not None and id == extra_owner_id:
        return True
    if id == int(Dev_Zaid):
        return True
    if id == await _get_bot_owner():
        return True
    if await rdb.get(f'{id}:rankDEV2:{Dev_Zaid}'):
        return True
    if await rdb.get(f'{id}:rankDEV:{Dev_Zaid}'):
        return True
    if await rdb.get(f'{cid}:rankGOWNER:{id}{Dev_Zaid}'):
        return True
    else:
        return False


async def dev_pls(id, cid) -> bool:
    if id == sudo_id:
        return True
    if extra_owner_id is not None and id == extra_owner_id:
        return True
    if id == int(Dev_Zaid):
        return True
    if id == await _get_bot_owner():
        return True
    if await rdb.get(f'{id}:rankDEV2:{Dev_Zaid}'):
        return True
    if await rdb.get(f'{id}:rankDEV:{Dev_Zaid}'):
        return True
    else:
        return False


async def dev2_pls(id, cid) -> bool:
    if extra_owner_id is not None and id == extra_owner_id:
        return True
    if id == int(Dev_Zaid):
        return True
    if id == await _get_bot_owner():
        return True
    if await rdb.get(f'{id}:rankDEV2:{Dev_Zaid}'):
        return True
    else:
        return False


async def devp_pls(id, cid) -> bool:
    if id == sudo_id:
        return True
    if extra_owner_id is not None and id == extra_owner_id:
        return True
    if id == int(Dev_Zaid):
        return True
    if id == await _get_bot_owner():
        return True
    else:
        return False


async def pre_pls(id, cid) -> bool:
    if extra_owner_id is not None and id == extra_owner_id:
        return True
    if id == await _get_bot_owner():
        return True
    if id == int(Dev_Zaid):
        return True
    if await rdb.get(f'{id}:rankDEV2:{Dev_Zaid}'):
        return True
    if await rdb.get(f'{id}:rankDEV:{Dev_Zaid}'):
        return True
    if await rdb.get(f'{cid}:rankGOWNER:{id}{Dev_Zaid}'):
        return True
    if await rdb.get(f'{cid}:rankOWNER:{id}{Dev_Zaid}'):
        return True
    if await rdb.get(f'{cid}:rankMOD:{id}{Dev_Zaid}'):
        return True
    if await rdb.get(f'{cid}:rankADMIN:{id}{Dev_Zaid}'):
        return True
    if await rdb.get(f'{cid}:rankPRE:{id}{Dev_Zaid}'):
        return True
    else:
        return False


async def get_devs_br():
    devs = []
    owner_id = await _get_bot_owner()
    # extra_owner_id اختياري تماماً (None افتراضياً): لا يُضاف لقائمة المطورين
    # إلا إذا ضبطه مالك هذه النسخة صراحة في .env، وطالما هو مختلف عن botowner
    # الفعلي حتى لا يتكرر في القائمة.
    if extra_owner_id is not None and extra_owner_id != owner_id:
        devs.append(extra_owner_id)
    if owner_id is not None:
        devs.append(owner_id)
    dev2_members = await rdb.smembers(f'{Dev_Zaid}DEV2')
    if dev2_members:
        for dev2 in dev2_members:
            devs.append(int(dev2))
    return devs


async def isLockCommand(fid: int, cid: int, text: str):
    commands = await rdb.hgetall(Dev_Zaid + f"locks-{cid}")
    if not commands:
        return False
    else:
        if text not in commands:
            return False
        for command in commands:
            cc = int(commands[command])
            if command.lower() in text.lower():
                if cc == 0:
                    return not await gowner_pls(fid, cid)
                if cc == 1:
                    return not await owner_pls(fid, cid)
                if cc == 2:
                    return not await mod_pls(fid, cid)
                if cc == 3:
                    return not await admin_pls(fid, cid)
                if cc == 4:
                    return not await pre_pls(fid, cid)


async def resolve_target(c, m, k: str, text: str, word_index: int):
    parts = text.split()
    if word_index >= len(parts):
        return None
    user_token = parts[word_index]
    if user_token.startswith('@'):
        try:
            get = await c.get_chat(user_token)
            return get.id, f'[{get.first_name}](tg://user?id={get.id})'
        except Exception:
            await m.reply(f'{k} مافيه عضو بهذا اليوزر')
            return None
    else:
        try:
            get = await c.get_chat(int(user_token))
            return get.id, f'[{get.first_name}](tg://user?id={get.id})'
        except Exception:
            await m.reply(f'{k} مافيه عضو بهذا الآيدي')
            return None


async def build_member_list(c, channel: str, members, title: str) -> str:
    txt = f'{title}\n\n'
    count = 1
    for member in members:
        if count == 101:
            break
        try:
            user = await c.get_users(int(member))
            if user.username:
                txt += f'{count} ➣ @{user.username} ࿓ ( `{user.id}` )\n'
            else:
                txt += f'{count} ➣ {user.mention} ࿓ ( `{user.id}` )\n'
            count += 1
        except Exception:
            txt += f'{count} ➣ [@{channel}](tg://user?id={int(member)}) ࿓ ( `{int(member)}` )\n'
            count += 1
    txt += '\n☆'
    return txt
