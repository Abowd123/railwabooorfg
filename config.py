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
