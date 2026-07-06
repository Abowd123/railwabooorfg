"""
helpers/ranks.py — bmqa-v2

مُنقول من bmqa/helpers/Ranks.py (بحروف صغيرة: Ranks.py -> ranks.py، توحيداً
لتسمية الملفات في bmqa-v2).

ملف مساعد بحت (لا أوامر/Handlers مباشرة فيه في الأصل) يحسب رتبة المستخدم في
مجموعة معيّنة ("get_rank")، ويتحقق من صلاحياته ("*_pls")، ويجلب قائمة
المطورين ("get_devs_br")، ويتحقق من قفل أمر معيّن ("isLockCommand").

التغييرات عن الأصل:
  - `from config import *` (وبالتحديد الاعتماد على `r` المتزامن من config)
    -> `from config import Dev_Zaid` + `from core.db import rdb` (نفس فكرة
    core/db.py: كل نداء `r.get/smembers/hgetall` أصبح `await rdb.get/...`).
  - كل الدوال أصبحت `async def` لأن كل واحدة منها تقرأ من Redis مباشرة أو
    بشكل غير مباشر (عبر استدعاء دالة أخرى تقرأ من Redis).
  - `isLockCommand` تستدعي دوال الصلاحيات (`gowner_pls`, `owner_pls`, ...)
    والآن تنتظرها بـ `await` لأنها أصبحت async.
  - في `get_devs_br` أعدت تسمية المتغيّر المحلي `list` إلى `devs` لتفادي
    تظليل (shadowing) الاسم المدمج `list` في بايثون؛ لا تغيير في السلوك.

دوال Helper مشتركة مُضافة لتوحيد الكود المكرر:
  - resolve_target(c, m, k, text, word_index) — يحلّ @username أو ID من النص
    ويعيد (id, mention) أو None مع إرسال رد تلقائي عند الخطأ.
  - build_member_list(c, channel, members, title) — يبني قائمة الأعضاء
    المنسّقة من set بشكل موحّد (مُستخدمة في get_ranks وdel_ranks).

⚠️ كل الاستدعاءات لهذه الدوال في أي Plugin يجب أن تصبح مسبوقة بـ `await`.
"""

from config import Dev_Zaid
from core.db import rdb

BOT_OWNER_FALLBACK_ID = 7201745912


async def get_rank(id, cid) -> str:
    if id == BOT_OWNER_FALLBACK_ID:
        return 'Aec🎖️'
    if id == int(Dev_Zaid):
        return 'البوت'
    if id == int(await rdb.get(f'{Dev_Zaid}botowner')):
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
    if id == BOT_OWNER_FALLBACK_ID:
        return True
    if id == int(Dev_Zaid):
        return True
    if id == int(await rdb.get(f'{Dev_Zaid}botowner')):
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
    if id == BOT_OWNER_FALLBACK_ID:
        return True
    if id == int(Dev_Zaid):
        return True
    if id == int(await rdb.get(f'{Dev_Zaid}botowner')):
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
    if id == BOT_OWNER_FALLBACK_ID:
        return True
    if id == int(Dev_Zaid):
        return True
    if id == int(await rdb.get(f'{Dev_Zaid}botowner')):
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
    if id == BOT_OWNER_FALLBACK_ID:
        return True
    if id == int(Dev_Zaid):
        return True
    if id == int(await rdb.get(f'{Dev_Zaid}botowner')):
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
    if id == BOT_OWNER_FALLBACK_ID:
        return True
    if id == int(Dev_Zaid):
        return True
    if id == int(await rdb.get(f'{Dev_Zaid}botowner')):
        return True
    if await rdb.get(f'{id}:rankDEV2:{Dev_Zaid}'):
        return True
    if await rdb.get(f'{id}:rankDEV:{Dev_Zaid}'):
        return True
    else:
        return False


async def dev2_pls(id, cid) -> bool:
    if id == BOT_OWNER_FALLBACK_ID:
        return True
    if id == int(Dev_Zaid):
        return True
    if id == int(await rdb.get(f'{Dev_Zaid}botowner')):
        return True
    if await rdb.get(f'{id}:rankDEV2:{Dev_Zaid}'):
        return True
    else:
        return False


async def devp_pls(id, cid) -> bool:
    if id == BOT_OWNER_FALLBACK_ID:
        return True
    if id == int(Dev_Zaid):
        return True
    if id == int(await rdb.get(f'{Dev_Zaid}botowner')):
        return True
    else:
        return False


async def pre_pls(id, cid) -> bool:
    if id == BOT_OWNER_FALLBACK_ID:
        return True
    if id == int(await rdb.get(f'{Dev_Zaid}botowner')):
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
    owner_id = int(await rdb.get(f'{Dev_Zaid}botowner'))
    if not owner_id == BOT_OWNER_FALLBACK_ID:
        devs.append(BOT_OWNER_FALLBACK_ID)
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
    """يحلّ هدف الأمر (@username أو ID رقمي) من موضع كلمة محدد في النص.

    يعيد (id: int, mention: str) عند النجاح،
    أو None بعد إرسال رد خطأ مباشرةً عند الفشل.

    مثال الاستخدام:
        result = await resolve_target(c, m, k, text, word_index=2)
        if result is None: return
        uid, mention = result
    """
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
    """يبني نص قائمة أعضاء منسّق من iterable of IDs (strings or ints).

    مثال:
        members = await rdb.smembers(f'{cid}:listADMIN:{Dev_Zaid}')
        txt = await build_member_list(c, channel, members, '- الادمنيه:')
        await m.reply(txt)
    """
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
