"""
config.py — bmqa-v2
كل القيم الحساسة تُقرأ من متغيرات البيئة فقط (os.environ).
لا توجد أي قيمة سرية مكتوبة صراحة داخل هذا الملف.

للتطوير المحلي: أنشئ ملف ".env" (انسخه من ".env.example") وسيتم تحميله
تلقائياً عبر python-dotenv. في بيئة الإنتاج (سيرفر/Docker) اضبط المتغيرات
مباشرة في بيئة التشغيل وليس عبر ملف .env.
"""

import os
import sys

from dotenv import load_dotenv

# يحمّل متغيرات ملف .env إن وجد (للتطوير المحلي فقط).
# لن يستبدل متغيرات بيئة مضبوطة مسبقاً على مستوى النظام/الخدمة.
load_dotenv()


def _require(name: str) -> str:
    """يقرأ متغير بيئة إلزامي، ويوقف التشغيل برسالة واضحة لو كان مفقوداً
    بدل أن يفشل البرنامج لاحقاً بخطأ غامض أو يعمل بقيمة فارغة صامتة."""
    value = os.environ.get(name)
    if not value:
        sys.exit(
            f"[config] متغير البيئة '{name}' غير موجود. "
            f"انسخ .env.example إلى .env واملأ القيمة، أو اضبطه في بيئة التشغيل."
        )
    return value


def _optional(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


# --- Telegram Bot ---
token = _require("BOT_TOKEN")
Dev_Zaid = token.split(":")[0]
sudo_id = int(_require("SUDO_ID"))
botUsername = _optional("BOT_USERNAME")

# --- Pyrogram / Telegram API credentials ---
api_id = int(_require("API_ID"))
api_hash = _require("API_HASH")

# --- Userbot session (اختياري: اتركه فارغاً إن لم تستخدم userbot) ---
userbot_session_string = _optional("USERBOT_SESSION_STRING")

# --- ARQ API ---
arq_api_key = _optional("ARQ_API_KEY")
arq_api_url = _optional("ARQ_API_URL", "https://arq.hamker.dev")

# --- Redis (قيم خام فقط؛ عميل Redis الفعلي async ويُنشأ في core/db.py) ---
redis_host = _optional("REDIS_HOST", "localhost")
redis_port = int(_optional("REDIS_PORT", "6379"))
redis_db = int(_optional("REDIS_DB", "0"))
redis_password = _optional("REDIS_PASSWORD") or None

# --- kvsqlite databases (مسارات فقط؛ العملاء الفعليون async ويُنشأون في core/db.py) ---
YTDB_PATH = _optional("YTDB_PATH", "ytdb.sqlite")
SOUNDDB_PATH = _optional("SOUNDDB_PATH", "sounddb.sqlite")
WSDB_PATH = _optional("WSDB_PATH", "wsdb.sqlite")

# ─────────────────────────────────────────────────────────────────────────────
# --- ميزة الموسيقى / Voice Chat (اختيارية بالكامل) ---
#
# إن تركت ASSISTANT_SESSION أو API_URL فارغَين، تبقى ميزة التشغيل معطّلة
# برسالة واضحة لمن يحاول استخدامها — ولن يتأثر تشغيل البوت الرئيسي بأي شكل.
# ─────────────────────────────────────────────────────────────────────────────


def _parse_vc_api_keys() -> list[str]:
    """
    يحلّل API_KEYS (مفاتيح مفصولة بفواصل، مثال: "key1,key2,key3")
    مع دعم fallback لـ API_KEY المفرد القديم للتوافق مع الإعدادات السابقة.
    يعيد قائمة فارغة إن لم تُضبط أيٌّ منهما — ميزة التشغيل ستُعطَّل لاحقاً.
    """
    raw = os.environ.get("API_KEYS", "").strip()
    keys = [k.strip() for k in raw.split(",") if k.strip()] if raw else []
    if not keys:
        single = os.environ.get("API_KEY", "").strip()
        if single:
            keys = [single]
    return keys


def _optional_int(name: str, default: int) -> int:
    """يقرأ متغير بيئة اختيارياً ويحوّله لـ int، يعود للقيمة الافتراضية عند قيمة غير رقمية."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        import warnings
        warnings.warn(
            f"[config] قيمة '{name}' ({raw!r}) غير رقمية، سيُستخدم الافتراضي {default}.",
            stacklevel=2,
        )
        return default


# جلسة Pyrogram لـ Userbot يُستخدم للانضمام للمكالمات الصوتية.
# اختياري — إن كان فارغاً تُعطَّل أوامر التشغيل برسالة واضحة بدون إيقاف البوت.
ASSISTANT_SESSION: str = _optional("ASSISTANT_SESSION")

# تفعيل تشغيل الفيديو (افتراضي: False = صوت فقط)
VC_VIDEO_ENABLED: bool = _optional("VC_VIDEO_ENABLED", "false").lower() == "true"

# الحد الأقصى لمدة أي مقطع بالدقائق (افتراضي: 60 دقيقة)
VC_DURATION_LIMIT_MINUTES: int = _optional_int("VC_DURATION_LIMIT_MINUTES", 60)

# ArtistBots API — رابط التنزيل للصوت
# مثال: https://api.artistbots.net  (راجع توثيق ArtistBots للمضيف الصحيح)
API_URL: str = _optional("API_URL", "").strip()

# ArtistBots API — رابط التنزيل للفيديو (قد يكون نفس API_URL أو مضيفاً مختلفاً)
VIDEO_API_URL: str = _optional("VIDEO_API_URL", "").strip()

# مفاتيح ArtistBots — فالباك تلقائي لـ API_KEY المفرد إن لم تُضبط API_KEYS
API_KEYS: list[str] = _parse_vc_api_keys()
