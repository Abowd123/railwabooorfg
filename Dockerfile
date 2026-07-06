FROM python:3.11-slim

# ffmpeg مطلوب فعلياً على مستوى النظام (لتحميل/تحويل الصوت والفيديو في core/worker.py)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# مسار افتراضي لملفات kvsqlite + التحميلات المؤقتة (اربطهما بـ Volume في Railway
# إن أردت أن تبقى البيانات بعد كل إعادة نشر)
RUN mkdir -p /app/downloads /app/logs

# لا نضع CMD ثابت هنا: كل من خدمة البوت وخدمة الـ worker على Railway
# تحدد أمر التشغيل الخاص بها بنفسها (Custom Start Command):
#   خدمة البوت:    python main.py
#   خدمة الـ worker: arq core.worker.WorkerSettings
CMD ["python", "main.py"]
