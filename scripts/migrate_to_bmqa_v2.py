#!/usr/bin/env python3
"""
migrate_to_bmqa_v2.py
======================
سكربت تحقّق وترحيل يُشغَّل مرة واحدة، من قاعدة الإنتاج الحالية (مشروع
Anokdbdvoloo / bmqa القديم) إلى bmqa-v2 (المشروع الجديد).

النتيجة المهمة من الفحص: بنية المفاتيح (key schema) في Redis متطابقة
حرفياً بين المشروعين لكل البيانات الحساسة (الرتب، الأقفال، الفلاتر،
الإعدادات، أرصدة البنك/الفلوس/الزرف، الهمسات، كاش الصوت/اليوتيوب).
لذلك "الترحيل" هنا هو نَسخ آمن يحافظ على TTL، وليس تحويل/إعادة تسمية
مفاتيح. راجع القسم "MANUAL_NOTES" بالأسفل لفروقات بسيطة غير حرجة.

الاستخدام:
    python3 migrate_to_bmqa_v2.py --dry-run          # فحص فقط، لا كتابة
    python3 migrate_to_bmqa_v2.py --apply            # التنفيذ الفعلي
    python3 migrate_to_bmqa_v2.py --apply --chat-id -1001234567890  # قروب واحد فقط (تجربة)

المتطلبات:
    pip install redis --break-system-packages
"""

import argparse
import shutil
import sys
from pathlib import Path

import redis

# ------------------------------------------------------------------
# إعدادات الاتصال — عدّلها حسب بيئتك الفعلية
# ------------------------------------------------------------------
SOURCE_REDIS = dict(host="localhost", port=6379, db=0, password=None)  # Anokdbdvoloo (القديم/الإنتاج)
TARGET_REDIS = dict(host="localhost", port=6379, db=0, password=None)  # bmqa-v2 (الجديد)
# ملاحظة: لو الاثنان على نفس Redis instance / نفس db، فهما فعلياً نفس
# البيانات أصلاً ولا حاجة لنسخ Redis إطلاقاً — فقط شغّل --dry-run للتأكد.

SOURCE_KVSQLITE_DIR = Path("./old_bot_data")   # مكان ytdb.sqlite / sounddb.sqlite / wsdb.sqlite بالإنتاج
TARGET_KVSQLITE_DIR = Path("./bmqa-v2")        # جذر مشروع bmqa-v2 (حيث تُقرأ المسارات من config.py)

KVSQLITE_FILES = ["ytdb.sqlite", "sounddb.sqlite", "wsdb.sqlite"]

# فروقات معروفة غير حرجة (كاش قابل لإعادة التوليد) — لا تُنسخ عمداً
SKIP_KEY_PREFIXES_EXACT = {
    "BankTopLast", "BankTopLastZrf",  # كاش لوحة صدارة قديم — bmqa-v2 يستخدم BankTop/BankTopZRF بدلاً منه
}


def connect(cfg):
    return redis.Redis(decode_responses=False, **cfg)  # bytes عشان DUMP/RESTORE


def migrate_redis(src: redis.Redis, dst: redis.Redis, chat_filter: str | None, apply: bool):
    """ينسخ كل مفتاح عبر DUMP/RESTORE (يحافظ على النوع + TTL تلقائياً)."""
    total, copied, skipped, errors = 0, 0, 0, 0
    cursor = 0
    while True:
        cursor, keys = src.scan(cursor=cursor, count=500)
        for raw_key in keys:
            total += 1
            key = raw_key.decode("utf-8", "ignore")

            if key in SKIP_KEY_PREFIXES_EXACT:
                skipped += 1
                continue
            if chat_filter and chat_filter not in key:
                skipped += 1
                continue

            try:
                dumped = src.dump(raw_key)
                if dumped is None:
                    continue
                ttl_ms = src.pttl(raw_key)
                ttl_ms = ttl_ms if ttl_ms and ttl_ms > 0 else 0
                if apply:
                    dst.restore(raw_key, ttl_ms, dumped, replace=True)
                copied += 1
            except Exception as e:
                errors += 1
                print(f"  [ERROR] {key}: {e}", file=sys.stderr)

        if cursor == 0:
            break

    print(f"Redis → total={total} copied={copied} skipped={skipped} errors={errors}")


def migrate_kvsqlite(apply: bool):
    """ينسخ ملفات kvsqlite (ytdb/sounddb/wsdb) كاملة — أبسط وأضمن من إعادة
    كتابتها سطر بسطر، لأن بنية الملف الداخلية لـ kvsqlite واحدة أصلاً."""
    for fname in KVSQLITE_FILES:
        src_path = SOURCE_KVSQLITE_DIR / fname
        dst_path = TARGET_KVSQLITE_DIR / fname
        if not src_path.exists():
            print(f"  [WARN] غير موجود: {src_path}")
            continue
        print(f"  {src_path} → {dst_path} ({'سيُنسخ' if apply else 'محاكاة فقط'})")
        if apply:
            if dst_path.exists():
                backup = dst_path.with_suffix(dst_path.suffix + ".bak")
                shutil.copy2(dst_path, backup)
                print(f"    نسخة احتياطية من الهدف القديم: {backup}")
            shutil.copy2(src_path, dst_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="نفّذ فعلياً (بدون هذا الخيار = محاكاة فقط)")
    ap.add_argument("--dry-run", action="store_true", help="فحص فقط (نفس السلوك الافتراضي)")
    ap.add_argument("--chat-id", type=str, default=None,
                     help="قصر الترحيل على قروب واحد فقط (للتجربة قبل التبديل الكامل)")
    ap.add_argument("--skip-kvsqlite", action="store_true", help="لا تنسخ ملفات ytdb/sounddb/wsdb")
    args = ap.parse_args()

    apply = args.apply
    print(f"وضع التشغيل: {'تنفيذ فعلي' if apply else 'محاكاة (dry-run)'}")
    if args.chat_id:
        print(f"مقصور على القروب: {args.chat_id}")

    print("\n== Redis ==")
    src = connect(SOURCE_REDIS)
    dst = connect(TARGET_REDIS)
    try:
        src.ping()
        dst.ping()
    except Exception as e:
        sys.exit(f"فشل الاتصال بـ Redis: {e}")
    migrate_redis(src, dst, args.chat_id, apply)

    if not args.skip_kvsqlite and not args.chat_id:
        print("\n== kvsqlite (ytdb / sounddb / wsdb) ==")
        migrate_kvsqlite(apply)

    print("\nتم. راجع الفروقات اليدوية في تعليق أعلى الملف (MANUAL_NOTES) قبل الاعتماد النهائي.")


# ------------------------------------------------------------------
# MANUAL_NOTES — فروقات لن يحلّها هذا السكربت تلقائياً:
#
# 1) كاش لوحة الصدارة (BankTopLast/BankTopLastZrf في القديم مقابل
#    BankTop/BankTopZRF بـ TTL=300s في bmqa-v2): كاش نصّي فقط يُعاد توليده
#    تلقائياً عند أول استخدام لأمر "توب". تم استبعاده عمداً من النسخ،
#    لا فعل مطلوب.
#
# 2) الهمسة (اهمس/wsdb): كود bmqa-v2 (core/db.py + all_moderation_1.py)
#    موثّق فيه أن wsdb.setex غير مدعومة حالياً، واستُبدلت بـ wsdb.set بدون
#    انتهاء صلاحية (1 ساعة كانت بالإنتاج القديم). أي همسات قديمة منسوخة
#    ستبقى للأبد في bmqa-v2 حتى يُضاف دعم TTL فعلي لـ KVSqliteDB، أو تُضاف
#    مهمة تنظيف دورية (cron) تحذف المفاتيح الأقدم من ساعة. يُنصح بحل هذه
#    النقطة في core/db.py قبل الاعتماد النهائي، وليس تجاهلها.
#
# 3) توكن البوت مكتوب صراحة بـ Anokdbdvoloo/bmqa/config.py — لازم يُلغى
#    (Revoke) عبر BotFather ويُستبدل بتوكن جديد يُقرأ من متغير بيئة BOT_TOKEN
#    فقط (bmqa-v2 جاهز لهذا أصلاً)، بعد اكتمال الترحيل مباشرة.
# ------------------------------------------------------------------


if __name__ == "__main__":
    main()
