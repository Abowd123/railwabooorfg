'''


██████╗░██████╗░██████╗░
██╔══██╗╚════██╗██╔══██╗
██████╔╝░█████╔╝██║░░██║
██╔══██╗░╚═══██╗██║░░██║
██║░░██║██████╔╝██████╔╝
╚═╝░░╚═╝╚═════╝░╚═════╝░


[ = This plugin is a part from R3D Source code = ]
{"Developer":"https://t.me/yqyqy66"}

'''

"""
مُنقول من bmqa/Plugins/fun.py (819 سطر) → bmqa-v2/Plugins/fun.py

═══════════════════════════════════════════════════════════════════
التحويلات المطبّقة على كامل الملف:
  - Thread(target=funFunc, args=(c, m, k, channel)).start() → await
    fun_animals(c, m, k) مباشرة (كل الهاندلرز async الآن).
  - كل نداء r.<op>(...) → await rdb.<op>(...) (core/db.py، نفس أسماء
    العمليات تماماً كما في الأصل: get/set/delete/sadd/srem/smembers/
    sismember).
  - @register + @safe_handler مُضافان فوق الهاندلر (نفس نمط
    group_update.py وglobal_filters.py المنقولين مسبقاً).
  - from config import * / from helpers.Ranks import * → استيراد صريح
    ومحدد (Dev_Zaid, admin_pls, isLockCommand).
  - helpers.Ranks → helpers.ranks (حروف صغيرة، كما في بقية bmqa-v2).

  ملاحظة عن import random, re, time في الأصل (السطر 17):
  الملف الأصلي يستورد `random` و`re` و`time` لكنه **لا يستخدم أياً
  منها فعلياً** في أي مكان من الجسم (لا يوجد أي `random.`، ولا أي
  `re.`، ولا أي `time.sleep` في كامل الملف الـ819 سطر — تم التحقق
  بالبحث الشامل). لذلك:
    * لا يوجد ولا موضع واحد لاستبدال time.sleep بـ asyncio.sleep هنا
      (خلافاً لملف group_update.py الذي كان يحتوي 7 مواضع).
    * حُذفت استيرادات random/re/time لأنها غير مستخدمة (dead imports).

  ملاحظة عن الاعتماد على helpers/memes.py:
  فحصت الملف الأصلي بالكامل ولا يوجد فيه أي استخدام لـ memes_eg /
  memes_sy / memes_sa / memes_ae / memes_us / memes_iq ولا أي استيراد
  من helpers/memes.py إطلاقاً. هذا الملف (fun.py) مختص فقط بألعاب
  "رفع/تنزيل/قائمة/مسح" النصية (كيك، عسل، نصاب، حمار، بقرة، كلب، قرد،
  تيس، ثور، هكر×2، دجاجة، ملكة، صياد، خروف) وردّي "رفع/تنزيل لقلبي" —
  لا صوتيات ولا ميمزات صوتية. **لا يوجد أي اعتماد على helpers/memes.py
  في هذا الملف تحديداً** (رغم أن هذا الاعتماد موجود في ملفات أخرى منقولة
  سابقاً مثل group_update.py الذي يستورد memes_sy/eg/sa/ae/us/iq فعلاً).

  ملاحظة عن متغيّر channel: كان يُحسب في funHandler الأصلي
  (r.get(...BotChannel...) أو 'yqyqy66') ويُمرَّر إلى funFunc كباراميتر
  لكنه **غير مستخدم إطلاقاً** داخل جسم funFunc الأصلي (كود ميت). حُذف
  هنا لعدم وجود أي استخدام فعلي له.

  ملاحظة عن تكرار "رفع هكر"/"تنزيل هكر" (بگ أصلي محفوظ كما هو):
  يوجد قسمان منفصلان في الأصل (B3S بالسطر ~504 وTEZ بالسطر ~754) كلاهما
  يستخدم نفس نصوص الأوامر بالحرف "رفع هكر" و"تنزيل هكر". بما أن قسم B3S
  يأتي أولاً وأوامره تُطابق وتُنفَّذ (return) قبل الوصول لقسم TEZ، فإن
  أوامر "رفع هكر"/"تنزيل هكر" الخاصة بـ TEZ ميتة فعلياً (لا تُنفَّذ أبداً)
  — فقط أمر "قائمة هكر"/"قائمه هكر" (بدون "ال") الخاص بـ TEZ يبقى قابلاً
  للوصول لأن نصه مختلف عن "قائمة الهكر"/"قائمه الهكر" الخاص بـ B3S. أُبقي
  هذا السلوك حرفياً دون أي إصلاح صامت.
═══════════════════════════════════════════════════════════════════
"""

from pyrogram import Client, filters

from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from helpers.ranks import admin_pls, isLockCommand


async def fun_animals(c, m, k: str) -> None:
    text = m.text
    name = await rdb.get(f'{Dev_Zaid}:BotName') if await rdb.get(f'{Dev_Zaid}:BotName') else 'رعد'
    if text.startswith(f'{name} '):
        text = text.replace(f'{name} ', '')
    if await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}'):
        text = await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}')
    if await rdb.get(f'Custom:{Dev_Zaid}&text={text}'):
        text = await rdb.get(f'Custom:{Dev_Zaid}&text={text}')
    if await isLockCommand(m.from_user.id, m.chat.id, text):
        return

    ################# CAKE #################
    if text == 'رفع كيك' or text == 'رفع كيكه' or text == 'رفع كيكة':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if await rdb.sismember(f'{Dev_Zaid}:CakeList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} كيكه من قبل\n☆')
            else:
                await rdb.sadd(f'{Dev_Zaid}:CakeList:{m.chat.id}', id)
                await rdb.set(f'{Dev_Zaid}:CakeName:{id}', mention)
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر رفعته كيكه 🍰\n☆')

    if text == 'تنزيل كيك' or text == 'تنزيل كيكه' or text == 'تنزيل كيكة':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if not await rdb.sismember(f'{Dev_Zaid}:CakeList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} مو كيكه من قبل\n☆')
            else:
                await rdb.srem(f'{Dev_Zaid}:CakeList:{m.chat.id}', id)
                await rdb.delete(f'{Dev_Zaid}:CakeName:{id}')
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر نزلته من كيكه\n☆')

    if text == 'قائمه الكيك' or text == 'قائمة الكيك':
        members = await rdb.smembers(f'{Dev_Zaid}:CakeList:{m.chat.id}')
        if not members:
            return await m.reply(f'{k} قائمة الكيك فاضية')
        else:
            txt = '- قائمة الكيك 🍰\n'
            count = 1
            for cake in members:
                mention = await rdb.get(f'{Dev_Zaid}:CakeName:{cake}')
                txt += f'{count} ➣ ⁪⁬⁪⁬{mention} ࿓ ( `{cake}` )\n'
                count += 1
            txt += '\n☆'
            return await m.reply(txt, disable_web_page_preview=True)

    if text == 'مسح قائمة الكيك' or text == 'مسح قائمه الكيك':
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
        else:
            members = await rdb.smembers(f'{Dev_Zaid}:CakeList:{m.chat.id}')
            if not members:
                return await m.reply(f'{k} قائمة الكيك فاضية')
            else:
                await m.reply(f'{k} ابشر مسحت قائمة الكيك')
                for cake in members:
                    await rdb.srem(f'{Dev_Zaid}:CakeList:{m.chat.id}', int(cake))
                    await rdb.delete(f'{Dev_Zaid}:CakeName:{cake}')

    ################# CAKE #################

    ################# 3SL #################
    if text == 'رفع عسل':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if await rdb.sismember(f'{Dev_Zaid}:3SLList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} عسل من قبل\n☆')
            else:
                await rdb.sadd(f'{Dev_Zaid}:3SLList:{m.chat.id}', id)
                await rdb.set(f'{Dev_Zaid}:3SLName:{id}', mention)
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر رفعته عسل 🍯\n☆')

    if text == 'تنزيل عسل':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if not await rdb.sismember(f'{Dev_Zaid}:3SLList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} مو عسل من قبل\n☆')
            else:
                await rdb.srem(f'{Dev_Zaid}:3SLList:{m.chat.id}', id)
                await rdb.delete(f'{Dev_Zaid}:3SLName:{id}')
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر نزلته من عسل\n☆')

    if text == 'قائمه العسل' or text == 'قائمة العسل':
        members = await rdb.smembers(f'{Dev_Zaid}:3SLList:{m.chat.id}')
        if not members:
            return await m.reply(f'{k} قائمة العسل فاضية')
        else:
            txt = '- قائمة العسل 🍯\n'
            count = 1
            for cake in members:
                mention = await rdb.get(f'{Dev_Zaid}:3SLName:{cake}')
                txt += f'{count} ➣ ⁪⁬⁪⁬{mention} ࿓ ( `{cake}` )\n'
                count += 1
            txt += '\n☆'
            return await m.reply(txt, disable_web_page_preview=True)

    if text == 'مسح قائمة العسل' or text == 'مسح قائمه العسل':
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
        else:
            members = await rdb.smembers(f'{Dev_Zaid}:3SLList:{m.chat.id}')
            if not members:
                return await m.reply(f'{k} قائمة العسل فاضية')
            else:
                await m.reply(f'{k} ابشر مسحت قائمة العسل')
                for cake in members:
                    await rdb.srem(f'{Dev_Zaid}:3SLList:{m.chat.id}', int(cake))
                    await rdb.delete(f'{Dev_Zaid}:3SLName:{cake}')

    ################# 3SL #################

    ################# ZQ #################
    if text == 'رفع نصاب':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if await rdb.sismember(f'{Dev_Zaid}:ZQList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} نصاب من قبل\n☆')
            else:
                await rdb.sadd(f'{Dev_Zaid}:ZQList:{m.chat.id}', id)
                await rdb.set(f'{Dev_Zaid}:ZQName:{id}', mention)
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر رفعته نصاب 💩\n☆')

    if text == 'تنزيل نصاب':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if not await rdb.sismember(f'{Dev_Zaid}:ZQList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} مو نصاب من قبل\n☆')
            else:
                await rdb.srem(f'{Dev_Zaid}:ZQList:{m.chat.id}', id)
                await rdb.delete(f'{Dev_Zaid}:ZQName:{id}')
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر نزلته من نصاب\n☆')

    if text == 'قائمه النصابين' or text == 'قائمة النصابين':
        members = await rdb.smembers(f'{Dev_Zaid}:ZQList:{m.chat.id}')
        if not members:
            return await m.reply(f'{k} قائمة النصابين فاضية')
        else:
            txt = '- قائمة النصابين 💩\n'
            count = 1
            for cake in members:
                mention = await rdb.get(f'{Dev_Zaid}:ZQName:{cake}')
                txt += f'{count} ➣ ⁪⁬⁪⁬{mention} ࿓ ( `{cake}` )\n'
                count += 1
            txt += '\n☆'
            return await m.reply(txt, disable_web_page_preview=True)

    if text == 'مسح قائمة النصابين' or text == 'مسح قائمه النصابين':
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
        else:
            members = await rdb.smembers(f'{Dev_Zaid}:ZQList:{m.chat.id}')
            if not members:
                return await m.reply(f'{k} قائمة النصابين فاضية')
            else:
                await m.reply(f'{k} ابشر مسحت قائمة النصابين')
                for cake in members:
                    await rdb.srem(f'{Dev_Zaid}:ZQList:{m.chat.id}', int(cake))
                    await rdb.delete(f'{Dev_Zaid}:ZQName:{cake}')

    ################# ZQ #################

    ################# 7MR #################
    if text == 'رفع حمار':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if await rdb.sismember(f'{Dev_Zaid}:7MRList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} حمار من قبل\n☆')
            else:
                await rdb.sadd(f'{Dev_Zaid}:7MRList:{m.chat.id}', id)
                await rdb.set(f'{Dev_Zaid}:7MRName:{id}', mention)
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر رفعته حمار 🦓\n☆')

    if text == 'تنزيل حمار':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if not await rdb.sismember(f'{Dev_Zaid}:7MRList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} مو حمار من قبل\n☆')
            else:
                await rdb.srem(f'{Dev_Zaid}:7MRList:{m.chat.id}', id)
                await rdb.delete(f'{Dev_Zaid}:7MRName:{id}')
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر نزلته من حمار\n☆')

    if text == 'قائمه الحمير' or text == 'قائمة الحمير':
        members = await rdb.smembers(f'{Dev_Zaid}:7MRList:{m.chat.id}')
        if not members:
            return await m.reply(f'{k} قائمة الحمير فاضية')
        else:
            txt = '- قائمة الحمير 🦓\n'
            count = 1
            for cake in members:
                mention = await rdb.get(f'{Dev_Zaid}:7MRName:{cake}')
                txt += f'{count} ➣ ⁪⁬⁪⁬{mention} ࿓ ( `{cake}` )\n'
                count += 1
            txt += '\n☆'
            return await m.reply(txt, disable_web_page_preview=True)

    if text == 'مسح قائمة الحمير' or text == 'مسح قائمه الحمير':
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
        else:
            members = await rdb.smembers(f'{Dev_Zaid}:7MRList:{m.chat.id}')
            if not members:
                return await m.reply(f'{k} قائمة الحمير فاضية')
            else:
                await m.reply(f'{k} ابشر مسحت قائمة الحمير')
                for cake in members:
                    await rdb.srem(f'{Dev_Zaid}:7MRList:{m.chat.id}', int(cake))
                    await rdb.delete(f'{Dev_Zaid}:7MRName:{cake}')

    ################# 7MR #################

    ################# COW #################
    if text == 'رفع بقرة' or text == 'رفع بقره':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if await rdb.sismember(f'{Dev_Zaid}:COWList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} بقرة من قبل\n☆')
            else:
                await rdb.sadd(f'{Dev_Zaid}:COWList:{m.chat.id}', id)
                await rdb.set(f'{Dev_Zaid}:COWName:{id}', mention)
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر رفعته بقرة 🐄\n☆')

    if text == 'تنزيل بقرة' or text == 'تنزيل بقره':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if not await rdb.sismember(f'{Dev_Zaid}:COWList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} مو بقرة من قبل\n☆')
            else:
                await rdb.srem(f'{Dev_Zaid}:COWList:{m.chat.id}', id)
                await rdb.delete(f'{Dev_Zaid}:COWName:{id}')
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر نزلته من بقرة\n☆')

    if text == 'قائمه البقر' or text == 'قائمة البقر':
        members = await rdb.smembers(f'{Dev_Zaid}:COWList:{m.chat.id}')
        if not members:
            return await m.reply(f'{k} قائمة البقر فاضية')
        else:
            txt = '- قائمة البقر 🐄\n'
            count = 1
            for cake in members:
                mention = await rdb.get(f'{Dev_Zaid}:COWName:{cake}')
                txt += f'{count} ➣ ⁪⁬⁪⁬{mention} ࿓ ( `{cake}` )\n'
                count += 1
            txt += '\n☆'
            return await m.reply(txt, disable_web_page_preview=True)

    if text == 'مسح قائمة البقر' or text == 'مسح قائمه البقر':
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
        else:
            members = await rdb.smembers(f'{Dev_Zaid}:COWList:{m.chat.id}')
            if not members:
                return await m.reply(f'{k} قائمة البقر فاضية')
            else:
                await m.reply(f'{k} ابشر مسحت قائمة البقر')
                for cake in members:
                    await rdb.srem(f'{Dev_Zaid}:COWList:{m.chat.id}', int(cake))
                    await rdb.delete(f'{Dev_Zaid}:COWName:{cake}')

    ################# COW #################

    ################# DOG #################
    if text == 'رفع كلب':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if await rdb.sismember(f'{Dev_Zaid}:DOGList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} كلب من قبل\n☆')
            else:
                await rdb.sadd(f'{Dev_Zaid}:DOGList:{m.chat.id}', id)
                await rdb.set(f'{Dev_Zaid}:DOGName:{id}', mention)
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر رفعته كلب 🐩\n☆')

    if text == 'تنزيل كلب':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if not await rdb.sismember(f'{Dev_Zaid}:DOGList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} مو كلب من قبل\n☆')
            else:
                await rdb.srem(f'{Dev_Zaid}:DOGList:{m.chat.id}', id)
                await rdb.delete(f'{Dev_Zaid}:DOGName:{id}')
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر نزلته من كلب\n☆')

    if text == 'قائمه الكلاب' or text == 'قائمة الكلاب':
        members = await rdb.smembers(f'{Dev_Zaid}:DOGList:{m.chat.id}')
        if not members:
            return await m.reply(f'{k} قائمة الكلاب فاضية')
        else:
            txt = '- قائمة الكلاب 🐩\n'
            count = 1
            for cake in members:
                mention = await rdb.get(f'{Dev_Zaid}:DOGName:{cake}')
                txt += f'{count} ➣ ⁪⁬⁪⁬{mention} ࿓ ( `{cake}` )\n'
                count += 1
            txt += '\n☆'
            return await m.reply(txt, disable_web_page_preview=True)

    if text == 'مسح قائمة الكلاب' or text == 'مسح قائمه الكلاب':
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
        else:
            members = await rdb.smembers(f'{Dev_Zaid}:DOGList:{m.chat.id}')
            if not members:
                return await m.reply(f'{k} قائمة الكلاب فاضية')
            else:
                await m.reply(f'{k} ابشر مسحت قائمة الكلاب')
                for cake in members:
                    await rdb.srem(f'{Dev_Zaid}:DOGList:{m.chat.id}', int(cake))
                    await rdb.delete(f'{Dev_Zaid}:DOGName:{cake}')

    ################# DOG #################

    ################# MON #################
    if text == 'رفع قرد':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if await rdb.sismember(f'{Dev_Zaid}:MONList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} قرد من قبل\n☆')
            else:
                await rdb.sadd(f'{Dev_Zaid}:MONList:{m.chat.id}', id)
                await rdb.set(f'{Dev_Zaid}:MONName:{id}', mention)
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر رفعته قرد 🐒\n☆')

    if text == 'تنزيل قرد':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if not await rdb.sismember(f'{Dev_Zaid}:MONList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} مو قرد من قبل\n☆')
            else:
                await rdb.srem(f'{Dev_Zaid}:MONList:{m.chat.id}', id)
                await rdb.delete(f'{Dev_Zaid}:MONName:{id}')
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر نزلته من قرد\n☆')

    if text == 'قائمه القرود' or text == 'قائمة القرود':
        members = await rdb.smembers(f'{Dev_Zaid}:MONList:{m.chat.id}')
        if not members:
            return await m.reply(f'{k} قائمة القرود فاضية')
        else:
            txt = '- قائمة القرود 🐒\n'
            count = 1
            for cake in members:
                mention = await rdb.get(f'{Dev_Zaid}:MONName:{cake}')
                txt += f'{count} ➣ ⁪⁬⁪⁬{mention} ࿓ ( `{cake}` )\n'
                count += 1
            txt += '\n☆'
            return await m.reply(txt, disable_web_page_preview=True)

    if text == 'مسح قائمة القرود' or text == 'مسح قائمه القرود':
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
        else:
            members = await rdb.smembers(f'{Dev_Zaid}:MONList:{m.chat.id}')
            if not members:
                return await m.reply(f'{k} قائمة القرود فاضية')
            else:
                await m.reply(f'{k} ابشر مسحت قائمة القرود')
                for cake in members:
                    await rdb.srem(f'{Dev_Zaid}:MONList:{m.chat.id}', int(cake))
                    await rdb.delete(f'{Dev_Zaid}:MONName:{cake}')

    ################# MON #################

    ################# TES #################
    if text == 'رفع تيس':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if await rdb.sismember(f'{Dev_Zaid}:TESList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} تيس من قبل\n☆')
            else:
                await rdb.sadd(f'{Dev_Zaid}:TESList:{m.chat.id}', id)
                await rdb.set(f'{Dev_Zaid}:TESName:{id}', mention)
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر رفعته تيس 🐐\n☆')

    if text == 'تنزيل تيس':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if not await rdb.sismember(f'{Dev_Zaid}:TESList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} مو تيس من قبل\n☆')
            else:
                await rdb.srem(f'{Dev_Zaid}:TESList:{m.chat.id}', id)
                await rdb.delete(f'{Dev_Zaid}:TESName:{id}')
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر نزلته من تيس\n☆')

    if text == 'قائمه التيس' or text == 'قائمة التيس':
        members = await rdb.smembers(f'{Dev_Zaid}:TESList:{m.chat.id}')
        if not members:
            return await m.reply(f'{k} قائمة التيوس فاضية')
        else:
            txt = '- قائمة التيوس 🐐\n'
            count = 1
            for cake in members:
                mention = await rdb.get(f'{Dev_Zaid}:TESName:{cake}')
                txt += f'{count} ➣ ⁪⁬⁪⁬{mention} ࿓ ( `{cake}` )\n'
                count += 1
            txt += '\n☆'
            return await m.reply(txt, disable_web_page_preview=True)

    if text == 'مسح قائمة التيس' or text == 'مسح قائمه التيس':
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
        else:
            members = await rdb.smembers(f'{Dev_Zaid}:TESList:{m.chat.id}')
            if not members:
                return await m.reply(f'{k} قائمة التيوس فاضية')
            else:
                await m.reply(f'{k} ابشر مسحت قائمة التيوس')
                for cake in members:
                    await rdb.srem(f'{Dev_Zaid}:TESList:{m.chat.id}', int(cake))
                    await rdb.delete(f'{Dev_Zaid}:TESName:{cake}')

    ################# TES #################

    ################# TOR #################
    if text == 'رفع ثور':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if await rdb.sismember(f'{Dev_Zaid}:TORList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ثور من قبل\n☆')
            else:
                await rdb.sadd(f'{Dev_Zaid}:TORList:{m.chat.id}', id)
                await rdb.set(f'{Dev_Zaid}:TORName:{id}', mention)
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر رفعته ثور 🐂\n☆')

    if text == 'تنزيل ثور':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if not await rdb.sismember(f'{Dev_Zaid}:TORList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} مو ثور من قبل\n☆')
            else:
                await rdb.srem(f'{Dev_Zaid}:TORList:{m.chat.id}', id)
                await rdb.delete(f'{Dev_Zaid}:TORName:{id}')
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر نزلته من ثور\n༄')

    if text == 'قائمه الثور' or text == 'قائمة الثور':
        members = await rdb.smembers(f'{Dev_Zaid}:TORList:{m.chat.id}')
        if not members:
            return await m.reply(f'{k} قائمة الثور فاضية')
        else:
            txt = '- قائمة الثور 🐂\n'
            count = 1
            for cake in members:
                mention = await rdb.get(f'{Dev_Zaid}:TORName:{cake}')
                txt += f'{count} ➣ ⁪⁬⁪⁬{mention} ࿓ ( `{cake}` )\n'
                count += 1
            txt += '\n☆'
            return await m.reply(txt, disable_web_page_preview=True)

    if text == 'مسح قائمة الثور' or text == 'مسح قائمه الثور':
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
        else:
            members = await rdb.smembers(f'{Dev_Zaid}:TORList:{m.chat.id}')
            if not members:
                return await m.reply(f'{k} قائمة الثور فاضية')
            else:
                await m.reply(f'{k} ابشر مسحت قائمة الثور')
                for cake in members:
                    await rdb.srem(f'{Dev_Zaid}:TORList:{m.chat.id}', int(cake))
                    await rdb.delete(f'{Dev_Zaid}:TORName:{cake}')

    ################# TOR #################

    ################# B3S #################
    if text == 'رفع هكر':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if await rdb.sismember(f'{Dev_Zaid}:B3SList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} هكر من قبل\n☆')
            else:
                await rdb.sadd(f'{Dev_Zaid}:B3SList:{m.chat.id}', id)
                await rdb.set(f'{Dev_Zaid}:B3SName:{id}', mention)
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر رفعته هكر 🏅\n☆')

    if text == 'تنزيل هكر':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if not await rdb.sismember(f'{Dev_Zaid}:B3SList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} مو هكر من قبل\n☆')
            else:
                await rdb.srem(f'{Dev_Zaid}:B3SList:{m.chat.id}', id)
                await rdb.delete(f'{Dev_Zaid}:B3SName:{id}')
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر نزلته من هكر\n☆')

    if text == 'قائمه الهكر' or text == 'قائمة الهكر':
        members = await rdb.smembers(f'{Dev_Zaid}:B3SList:{m.chat.id}')
        if not members:
            return await m.reply(f'{k} قائمة الهكر فاضية')
        else:
            txt = '- قائمة الهكر 🏅\n'
            count = 1
            for cake in members:
                mention = await rdb.get(f'{Dev_Zaid}:B3SName:{cake}')
                txt += f'{count} ➣ ⁪⁬⁪⁬{mention} ࿓ ( `{cake}` )\n'
                count += 1
            txt += '\n☆'
            return await m.reply(txt, disable_web_page_preview=True)

    if text == 'مسح قائمة الهكر' or text == 'مسح قائمه الهكر':
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
        else:
            members = await rdb.smembers(f'{Dev_Zaid}:B3SList:{m.chat.id}')
            if not members:
                return await m.reply(f'{k} قائمة الهكر فاضية')
            else:
                await m.reply(f'{k} ابشر مسحت قائمة الهكر')
                for cake in members:
                    await rdb.srem(f'{Dev_Zaid}:B3SList:{m.chat.id}', int(cake))
                    await rdb.delete(f'{Dev_Zaid}:B3SName:{cake}')

    ################# B3S #################

    ################# DJJ #################
    if text == 'رفع دجاجه' or text == 'رفع دجاجة':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if await rdb.sismember(f'{Dev_Zaid}:DJJList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} دجاجه من قبل\n☆')
            else:
                await rdb.sadd(f'{Dev_Zaid}:DJJList:{m.chat.id}', id)
                await rdb.set(f'{Dev_Zaid}:DJJName:{id}', mention)
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر رفعته دجاجه 🐓\n☆')

    if text == 'تنزيل دجاجه' or text == 'تنزيل دجاجة':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if not await rdb.sismember(f'{Dev_Zaid}:DJJList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} مو دجاجه من قبل\n☆')
            else:
                await rdb.srem(f'{Dev_Zaid}:DJJList:{m.chat.id}', id)
                await rdb.delete(f'{Dev_Zaid}:DJJName:{id}')
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر نزلته من دجاجه\n☆')

    if text == 'قائمه الدجاج' or text == 'قائمة الدجاج':
        members = await rdb.smembers(f'{Dev_Zaid}:DJJList:{m.chat.id}')
        if not members:
            return await m.reply(f'{k} قائمة الدجاج فاضية')
        else:
            txt = '- قائمة الدجاج 🐓\n'
            count = 1
            for cake in members:
                mention = await rdb.get(f'{Dev_Zaid}:DJJName:{cake}')
                txt += f'{count} ➣ ⁪⁬⁪⁬{mention} ࿓ ( `{cake}` )\n'
                count += 1
            txt += '\n☆'
            return await m.reply(txt, disable_web_page_preview=True)

    if text == 'مسح قائمة الدجاج' or text == 'مسح قائمه الدجاج':
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
        else:
            members = await rdb.smembers(f'{Dev_Zaid}:DJJList:{m.chat.id}')
            if not members:
                return await m.reply(f'{k} قائمة الدجاج فاضية')
            else:
                await m.reply(f'{k} ابشر مسحت قائمة الدجاج')
                for cake in members:
                    await rdb.srem(f'{Dev_Zaid}:DJJList:{m.chat.id}', int(cake))
                    await rdb.delete(f'{Dev_Zaid}:DJJName:{cake}')

    ################# DJJ #################

    ################# HTF #################
    if text == 'رفع ملكه':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if await rdb.sismember(f'{Dev_Zaid}:HTFList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ملكه من قبل\n☆')
            else:
                await rdb.sadd(f'{Dev_Zaid}:HTFList:{m.chat.id}', id)
                await rdb.set(f'{Dev_Zaid}:HTFName:{id}', mention)
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر رفعته ملكه 🧱\n☆')

    if text == 'تنزيل ملكه':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if not await rdb.sismember(f'{Dev_Zaid}:HTFList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} مو ملكه من قبل\n☆')
            else:
                await rdb.srem(f'{Dev_Zaid}:HTFList:{m.chat.id}', id)
                await rdb.delete(f'{Dev_Zaid}:HTFName:{id}')
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر نزلته من ملكه\n☆')

    if text == 'قائمه الهطوف' or text == 'قائمة الهطوف':
        members = await rdb.smembers(f'{Dev_Zaid}:HTFList:{m.chat.id}')
        if not members:
            return await m.reply(f'{k} قائمة الهطوف فاضية')
        else:
            txt = '- قائمة الهطوف 🧱\n'
            count = 1
            for cake in members:
                mention = await rdb.get(f'{Dev_Zaid}:HTFName:{cake}')
                txt += f'{count} ➣ ⁪⁬⁪⁬{mention} ࿓ ( `{cake}` )\n'
                count += 1
            txt += '\n☆'
            return await m.reply(txt, disable_web_page_preview=True)

    if text == 'مسح قائمة الهطوف' or text == 'مسح قائمه الهطوف':
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
        else:
            members = await rdb.smembers(f'{Dev_Zaid}:HTFList:{m.chat.id}')
            if not members:
                return await m.reply(f'{k} قائمة الهطوف فاضية')
            else:
                await m.reply(f'{k} ابشر مسحت قائمة الهطوف')
                for cake in members:
                    await rdb.srem(f'{Dev_Zaid}:HTFList:{m.chat.id}', int(cake))
                    await rdb.delete(f'{Dev_Zaid}:HTFName:{cake}')

    ################# HTF #################

    ################# SYD #################
    if text == 'رفع صياد':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if await rdb.sismember(f'{Dev_Zaid}:SYDList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} صياد من قبل\n☆')
            else:
                await rdb.sadd(f'{Dev_Zaid}:SYDList:{m.chat.id}', id)
                await rdb.set(f'{Dev_Zaid}:SYDName:{id}', mention)
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر رفعته صياد 🔫\n☆')

    if text == 'تنزيل صياد':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if not await rdb.sismember(f'{Dev_Zaid}:SYDList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} مو صياد من قبل\n☆')
            else:
                await rdb.srem(f'{Dev_Zaid}:SYDList:{m.chat.id}', id)
                await rdb.delete(f'{Dev_Zaid}:SYDName:{id}')
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر نزلته من صياد\n☆')

    if text == 'قائمه الصيادين' or text == 'قائمة الصيادين':
        members = await rdb.smembers(f'{Dev_Zaid}:SYDList:{m.chat.id}')
        if not members:
            return await m.reply(f'{k} قائمة الصيادين فاضية')
        else:
            txt = '- قائمة الصيادين 🔫\n'
            count = 1
            for cake in members:
                mention = await rdb.get(f'{Dev_Zaid}:SYDName:{cake}')
                txt += f'{count} ➣ ⁪⁬⁪⁬{mention} ࿓ ( `{cake}` )\n'
                count += 1
            txt += '\n☆'
            return await m.reply(txt, disable_web_page_preview=True)

    if text == 'مسح قائمة الصيادين' or text == 'مسح قائمه الصيادين':
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
        else:
            members = await rdb.smembers(f'{Dev_Zaid}:SYDList:{m.chat.id}')
            if not members:
                return await m.reply(f'{k} قائمة الصيادين فاضية')
            else:
                await m.reply(f'{k} ابشر مسحت قائمة الصيادين')
                for cake in members:
                    await rdb.srem(f'{Dev_Zaid}:SYDList:{m.chat.id}', int(cake))
                    await rdb.delete(f'{Dev_Zaid}:SYDName:{cake}')

    ################# SYD #################

    ################# 5RF #################
    if text == 'رفع خروف':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if await rdb.sismember(f'{Dev_Zaid}:5RFList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} خروف من قبل\n☆')
            else:
                await rdb.sadd(f'{Dev_Zaid}:5RFList:{m.chat.id}', id)
                await rdb.set(f'{Dev_Zaid}:5RFName:{id}', mention)
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر رفعته خروف 🐏\n☆')

    if text == 'تنزيل خروف':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if not await rdb.sismember(f'{Dev_Zaid}:5RFList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} مو خروف من قبل\n☆')
            else:
                await rdb.srem(f'{Dev_Zaid}:5RFList:{m.chat.id}', id)
                await rdb.delete(f'{Dev_Zaid}:5RFName:{id}')
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر نزلته من خروف\n☆')

    if text == 'قائمه الخرفان' or text == 'قائمة الخرفان':
        members = await rdb.smembers(f'{Dev_Zaid}:5RFList:{m.chat.id}')
        if not members:
            return await m.reply(f'{k} قائمة الخرفان فاضية')
        else:
            txt = '- قائمة الخرفان 🐏\n'
            count = 1
            for cake in members:
                mention = await rdb.get(f'{Dev_Zaid}:5RFName:{cake}')
                txt += f'{count} ➣ ⁪⁬⁪⁬{mention} ࿓ ( `{cake}` )\n'
                count += 1
            txt += '\n☆'
            return await m.reply(txt, disable_web_page_preview=True)

    if text == 'مسح قائمة الخرفان' or text == 'مسح قائمه الخرفان':
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
        else:
            members = await rdb.smembers(f'{Dev_Zaid}:5RFList:{m.chat.id}')
            if not members:
                return await m.reply(f'{k} قائمة الخرفان فاضية')
            else:
                await m.reply(f'{k} ابشر مسحت قائمة الخرفان')
                for cake in members:
                    await rdb.srem(f'{Dev_Zaid}:5RFList:{m.chat.id}', int(cake))
                    await rdb.delete(f'{Dev_Zaid}:5RFName:{cake}')

    ################# 5RF #################

    ################# TEZ #################
    if text == 'رفع هكر':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if await rdb.sismember(f'{Dev_Zaid}:TEZList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} هكر من قبل\n☆')
            else:
                await rdb.sadd(f'{Dev_Zaid}:TEZList:{m.chat.id}', id)
                await rdb.set(f'{Dev_Zaid}:TEZName:{id}', mention)
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر رفعته هكر ♕\n☆')

    if text == 'تنزيل هكر':
        if m.reply_to_message and m.reply_to_message.from_user:
            mention = m.reply_to_message.from_user.mention
            id = m.reply_to_message.from_user.id
            if not await rdb.sismember(f'{Dev_Zaid}:TEZList:{m.chat.id}', id):
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} مو هكر من قبل\n☆')
            else:
                await rdb.srem(f'{Dev_Zaid}:TEZList:{m.chat.id}', id)
                await rdb.delete(f'{Dev_Zaid}:TEZName:{id}')
                return await m.reply(f'「 ⁪⁬⁪⁬{mention} 」\n{k} ابشر نزلته من هكر\n☆')

    if text == 'قائمه هكر' or text == 'قائمة هكر':
        members = await rdb.smembers(f'{Dev_Zaid}:TEZList:{m.chat.id}')
        if not members:
            return await m.reply(f'{k} قائمة هكر فاضية')
        else:
            txt = '- قائمة هكر ♕\n'
            count = 1
            for cake in members:
                mention = await rdb.get(f'{Dev_Zaid}:TEZName:{cake}')
                txt += f'{count} ➣ ⁪⁬⁪⁬{mention} ࿓ ( `{cake}` )\n'
                count += 1
            txt += '\n☆'
            return await m.reply(txt, disable_web_page_preview=True)

    if text == 'مسح قائمة هكر' or text == 'مسح قائمه هكر':
        if not await admin_pls(m.from_user.id, m.chat.id):
            return await m.reply(f'{k} هذا الامر يخص ( الادمن وفوق ) بس')
        else:
            members = await rdb.smembers(f'{Dev_Zaid}:TEZList:{m.chat.id}')
            if not members:
                return await m.reply(f'{k} قائمة هكر فاضية')
            else:
                await m.reply(f'{k} ابشر مسحت قائمة هكر')
                for cake in members:
                    await rdb.srem(f'{Dev_Zaid}:TEZList:{m.chat.id}', int(cake))
                    await rdb.delete(f'{Dev_Zaid}:TEZName:{cake}')

    ################# TEZ #################

    ################# 🔮 #################

    if text == 'رفع لقلبي' and m.reply_to_message:
        return await m.reply('{} رفعته لقلبك\n{} اللهم حسد 😔'.format(k, k))

    if text == 'تنزيل من قلبي' and m.reply_to_message:
        return await m.reply('اح اح ماتوصل')

    ################# 🔮 #################


@register("fun_animals")
@Client.on_message(filters.text & filters.group, group=34)
@safe_handler
async def fun_handler(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')
    if await rdb.get(f'{m.chat.id}:disableFun:{Dev_Zaid}'):
        return
    if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}') or await rdb.get(f'{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not await admin_pls(m.from_user.id, m.chat.id):
        return
    if await rdb.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}'):
        return
    await fun_animals(c, m, k)
