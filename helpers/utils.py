"""
helpers/utils.py — bmqa-v2

مُنقول من bmqa/helpers/utils.py مع تصحيح: في النسخة الأصلية كانت دالة
cssworker_url تعتمد على uuid و http (httpx.AsyncClient) و HTTPError، وهذه
الأسماء لم تكن مُعرَّفة داخل utils.py نفسه، بل كانت مستوردة/مُنشأة فقط في
Plugins/private&sudos.py (الذي كان يعيد تعريف الدالة نفسها محلياً). أي
استيراد مباشر لهذا الملف كان سيفشل بـ NameError. هنا تم جعل الملف مستقلاً
تماماً بإضافة الاستيرادات الناقصة، دون تغيير أي منطق.

كل الدوال هنا async بالفعل ولا تعتمد على مكتبات sync (لا "requests")،
تماشياً مع قاعدة المشروع (راجع requirements.txt).
"""

import asyncio
import uuid

import httpx

_timeout = httpx.Timeout(40, pool=None)
http = httpx.AsyncClient(http2=True, timeout=_timeout)


async def shell_exec(code: str):
    """ينفّذ أمر shell بشكل async ويرجع (stdout, process)."""
    process = await asyncio.create_subprocess_shell(
        code, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )

    stdout = (await process.communicate())[0].decode().strip()
    return stdout, process


async def cssworker_url(target_url: str):
    """يطلب سكرين‌شوت لصفحة ويب عبر htmlcsstoimage.com ويرجع JSON الرد."""
    url = "https://htmlcsstoimage.com/demo_run"
    my_headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:95.0) Gecko/20100101 Firefox/95.0",
    }

    data = {
        "url": target_url,
        # Sending a random CSS to make the API to generate a new screenshot.
        "css": f"random-tag: {uuid.uuid4()}",
        "render_when_ready": False,
        "viewport_width": 1280,
        "viewport_height": 720,
        "device_scale": 1,
    }

    try:
        resp = await http.post(url, headers=my_headers, json=data)
        return resp.json()
    except httpx.HTTPError:
        return None
