"""
all_index.py
═══════════════════════════════════════════════════════════════════════════════
فهرس هجرة bmqa → bmqa-v2
المصدر: bmqa/Plugins/all.py  (5002 سطر)
الهدف: bmqa-v2/Plugins/all_*.py

كيفية التشغيل:
  استورد هذا الملف في __init__.py أو main.py للبوت كالتالي:

      from Plugins import (
          all_helpers,
          all_settings,
          all_voice_and_blocklist,
          all_protection,
          all_features_toggle,
      )

  أو الأفضل: ضع كل ملف في مجلد Plugins/ وسيُحمَّل تلقائياً عبر
  pyrogram plugin loader إن كان مُفعَّلاً.

الملفات المُنتَجة:
  1. all_helpers.py               — دوال مساعدة وهاندلرات قاعدية
  2. all_settings.py              — إعدادات المجموعة والترحيب والمنشن
  3. all_voice_and_blocklist.py   — انطق/انطقي + قوائم المنع
  4. all_protection.py            — قفل/فتح الكل + تفعيل/تعطيل الحماية
  5. all_features_toggle.py       — تفعيل/تعطيل الميزات + الترجمة + ابلاغ
═══════════════════════════════════════════════════════════════════════════════
"""

# ═══════════════════════════════════════════════════════════════════════════
# الملف 1: all_helpers.py
# المصدر: all.py سطر 1–1062 (دوال مساعدة وهاندلرات عامة)
# ═══════════════════════════════════════════════════════════════════════════
#
# الدوال المساعدة:
#   - Find(c, m, text)                → يبحث عن مستخدم بـ username/id/رد
#   - get_for_verify(c, cid, uid)     → يجلب بيانات التحقق من Redis
#   - scan4(c, m, key_prefix)         → يمسح مفاتيح Redis بنمط
#   - scanR(c, m, pattern)            → يمسح مفاتيح بـ SCAN (دون KEYS)
#   - guardResponseFunction(c, m)     → هاندلر ردود الحراسة (guards)
#   - guardResponseFunction2(c, m)    → نسخة ثانية من هاندلر الردود
#   - guardLocksResponse(c, m)        → هاندلر مخالفات الأقفال
#   - guardLocksResponse2(c, m)       → نسخة ثانية لمخالفات الأقفال
#   - antiPersian(c, m)               → فلتر الحسابات الفارسية عند الدخول
#
# التحويلات:
#   r.* → await rdb.*  |  time.sleep → asyncio.sleep
#   Thread(target=…) → await مباشر  |  get_members → async for

# ═══════════════════════════════════════════════════════════════════════════
# الملف 2: all_settings.py
# المصدر: all.py سطر 1124–1562 (guardCommands — الإعدادات والمنشن والترحيب)
# ═══════════════════════════════════════════════════════════════════════════
#
#  #   نص الأمر                   الصيغ البديلة              الصلاحية    مفتاح Redis
#  1   الاعدادات                  —                          mod+        26 مفتاح قراءة
#  2   الساعه                     الساعة، الوقت              الجميع      —
#  3   القوانين                   —                          الجميع      CustomRules
#  4   التاريخ                    —                          الجميع      —
#  5   المالك                     —                          الجميع      —
#  6   اطردني                     —                          الجميع      enableKickMe
#  7   الرابط                     —                          الجميع      disableLINK
#  8   انشاء رابط                 —                          mod+        —
#  9   @all …                     startswith                 mod+        inMention، inMentionWAIT
# 10   /cancel                    ايقاف                      mod+        inMention
# 11   منشن                       —                          mod+        —
# 12   تعطيل المنشن               —                          mod+        disableALL
# 13   تفعيل المنشن               —                          mod+        disableALL
# 14   تعطيل الترحيب              —                          mod+        disableWelcome
# 15   تعطيل الترحيب بالصورة      تعطيل الترحيب بالصوره      mod+        disableWelcomep
# 16   تفعيل الترحيب بالصورة      تفعيل الترحيب بالصوره      mod+        disableWelcomep
# 17   تعطيل الرابط               —                          mod+        disableLINK
# 18   تفعيل الرابط               —                          mod+        disableLINK
# 19   تعطيل البايو               —                          mod+        disableBio
# 20   تفعيل البايو               —                          mod+        disableBio
# 21   تعطيل اطردني               —                          mod+        enableKickMe
# 22   تفعيل اطردني               —                          mod+        enableKickMe
# 23   تعطيل التحقق               —                          mod+        enableVerify
# 24   تفعيل التحقق               —                          mod+        enableVerify
# 25   تعطيل انطقي                تعطيل انطق                 mod+        disableSay
# 26   تفعيل انطقي                تفعيل انطق                 mod+        disableSay
#
# ⚠️ AMBIGUOUS [A1]: "تفعيل الترحيب" غائب من الأصل تماماً.

# ═══════════════════════════════════════════════════════════════════════════
# الملف 3: all_voice_and_blocklist.py
# المصدر: all.py سطر 1564–1881
# ═══════════════════════════════════════════════════════════════════════════
#
#  #   نص الأمر               الشرط              الصلاحية   التحويل الرئيسي
#  1   انطق <نص>              startswith         الجميع     requests→aiohttp، os.system→asyncio.create_subprocess_exec
#  2   انطقي <نص>             startswith         الجميع     نفس #1، API بدون &model=3
#  3   وش يقول / وش تقول؟    رد على voice       الجميع     download→await، sr.Recognizer→asyncio.to_thread (ar-SA)
#  4   zaid / زوز             رد على voice+uid   uid ثابت   نفس #3 (en-US)
#  5   منع <كلمة>             startswith         mod+       r.sismember/sadd → await rdb.*
#  6   الغاء منع <كلمة>       startswith+len>2   mod+       r.sismember/srem → await rdb.*
#  7   منع                    رد على وسيط        mod+       r.get/set/sadd → await rdb.*
#  8   الغاء منع              رد على وسيط        mod+       r.get/delete/srem → await rdb.*
#  9   منع                    رد على نص          mod+       رسالة خطأ فقط
# 10   قائمه المنع            قائمة المنع        mod+       r.smembers → await rdb.smembers
# 11   مسح قائمه المنع        مسح قائمة المنع    mod+       حذف file_id keys + القائمتين
#
# ⚠️ AMBIGUOUS: rep.video → file_id = rep.photo.file_id (خطأ محفوظ من الأصل)

# ═══════════════════════════════════════════════════════════════════════════
# الملف 4: all_protection.py
# المصدر: all.py سطر 1883–2105
# ═══════════════════════════════════════════════════════════════════════════
#
#  #   نص الأمر               الصيغ البديلة          الصلاحية   المفاتيح
#  1   قفل الكل               —                      mod+       25 مفتاح set
#  2   فتح الكل               —                      mod+       26 مفتاح delete (+lockKFR)
#  3   تفعيل الحماية          تفعيل الحمايه           owner      16 مفتاح set + حذف disableWarn
#  4   تعطيل الحماية          تعطيل الحمايه           owner      15 مفتاح delete (lockEditM يبقى)
#
# ⚠️ AMBIGUOUS:
#   - فتح الكل يحذف lockKFR رغم أن قفل الكل لا يضبطه
#   - تعطيل الحماية لا يحذف lockEditM — مقصود في الأصل
#   - شرط "معطّلة من قبل": lockEditM=1 AND كل الآخرين=0

# ═══════════════════════════════════════════════════════════════════════════
# الملف 5: all_features_toggle.py
# المصدر: all.py سطر 2649–3058
# ═══════════════════════════════════════════════════════════════════════════
#
#  #   نص الأمر                   الصيغ البديلة          الصلاحية   مفتاح Redis
#  1   تعطيل التحذير              —                      mod+       disableWarn
#  2   تفعيل التحذير              —                      mod+       disableWarn
#  3   تعطيل اليوتيوب             —                      mod+       disableYT
#  4   تفعيل اليوتيوب             —                      mod+       disableYT
#  5   تعطيل الساوند              —                      mod+       disableSound
#  6   تفعيل الساوند              —                      mod+       disableSound
#  7   تعطيل الانستا              —                      mod+       disableINSTA
#  8   تفعيل الانستا              —                      mod+       disableINSTA
#  9   تعطيل اهمس                 —                      mod+       disableWHISPER
# 10   تفعيل اهمس                 —                      mod+       disableWHISPER
# 11   تعطيل التيك                —                      mod+       disableTik
# 12   تفعيل التيك                —                      mod+       disableTik
# 13   تعطيل شازام                —                      mod+       disableShazam
# 14   تفعيل شازام                —                      mod+       disableShazam
# 15   تعطيل الالعاب              —                      mod+       disableGames
# 16   تفعيل الالعاب              —                      mod+       disableGames
# 17   تعطيل الترجمة              تعطيل الترجمه           mod+       disableTrans
# 18   تفعيل الترجمة              تفعيل الترجمه           mod+       disableTrans
# 19   تعطيل التسلية              تعطيل التسليه           mod+       disableFun
# 20   تفعيل التسلية              تفعيل التسليه           mod+       disableFun
# 21   تعطيل الاشتراك             —                      dev2       disableSubscribe (GLOBAL)
# 22   قناة الاشتراك              —                      dev2       forceChannel (GLOBAL)
# 23   وضع قناة @<username>       startswith             dev2       forceChannel (GLOBAL)
# 24   تفعيل الاشتراك             —                      dev2       disableSubscribe (GLOBAL)
# 25   /ar                        رد على رسالة           الجميع     disableTrans (check)
# 26   /en                        رد على رسالة           الجميع     disableTrans (check)
# 27   ترجمه                      رد على رسالة           الجميع     7 طلبات API متوازية
# 28   ترجمه <lang>               startswith+رد          الجميع     طلب API واحد
# 29   ابلاغ                      رد على رسالة           الجميع     يمنشن كل الإداريين
#
# ⚠️ AMBIGUOUS:
#   - أوامر الاشتراك (21،22،23،24): مفاتيح عالمية بلا chat_id
#   - ترجمه: يجلب en و ar لكن لا يعرضهما في الرد (محفوظ)
#   - ابلاغ: أي عضو يستطيع الإبلاغ (لا قيد صلاحية)

# ═══════════════════════════════════════════════════════════════════════════
# ملخص التحويلات العامة عبر كل الملفات
# ═══════════════════════════════════════════════════════════════════════════
#
#  البنية الأصلية (sync)        →   البنية الجديدة (async)
#  ────────────────────────────────────────────────────────
#  r.get/set/delete             →   await rdb.get/set/delete
#  r.sismember/sadd/srem        →   await rdb.sismember/sadd/srem
#  r.smembers                   →   await rdb.smembers
#  r.ttl(key)                   →   await rdb.ttl(key)
#  time.sleep(n)                →   await asyncio.sleep(n)
#  Thread(target=fn)            →   await fn(c, m) مباشرة
#  for mm in m.chat.get_members →   async for mm in c.get_chat_members(cid)
#  c.get_chat(id).invite_link   →   (await c.get_chat(id)).invite_link
#  m.reply(...)                 →   await m.reply(...)
#  requests.get(url)            →   aiohttp.ClientSession async GET
#  os.system("ffmpeg ...")      →   await asyncio.create_subprocess_exec(...)
#  sr.Recognizer (blocking)     →   await asyncio.to_thread(fn, ...)
#  return False                 →   return

# ═══════════════════════════════════════════════════════════════════════════
# الأوامر غير المُهجَّرة بعد (خارج النطاق المطلوب)
# ═══════════════════════════════════════════════════════════════════════════
#
#  السطر      الأمر/الميزة
#  ──────────────────────────────────────────────────────────────────────
#  2107-2648  أوامر الأقفال الفردية (قفل/فتح الدردشة، الفويس، الفيديو…)
#  3060-3085  المقيدين / مسح المقيدين
#  3087+      باقي guardCommands (حذف الإداريين، الكتم، رفع الحظر…)
#  3100+      بقية all.py (هاندلرات أخرى خارج guardCommands)
