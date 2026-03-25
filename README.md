---
title: بوست سوشال — Social Post Manager
emoji: 🧠
colorFrom: purple
colorTo: pink
sdk: docker
pinned: false
license: mit
app_port: 7860
---

# 🧠 بوست سوشال — Social Post Manager

نظام نشر ذكي ومتكامل على منصات السوشال ميديا — مبني بـ Flask + APScheduler + Telegram Bot.

[![CI](https://github.com/YOUR_USER/social-post/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USER/social-post/actions/workflows/ci.yml)

---

## المنصات المدعومة

| المنصة | النشر | الاختبار |
|--------|-------|---------|
| Facebook | صورة + نص | ✅ |
| Instagram | صورة | ✅ |
| Twitter/X | صورة + نص | ✅ |
| Threads | صورة + نص | ✅ |
| LinkedIn | صورة + نص (إنجليزي) | ✅ |

---

## المميزات

- توليد أفكار تلقائي بالذكاء الاصطناعي (Cohere / Gemini / Groq / OpenRouter)
- نشر مجدول تلقائياً (4 مرات يومياً)
- توليد صور بـ Flux 2 عبر Cloudflare Worker + Pollinations كـ fallback
- بوت تيليجرام للتحكم الكامل من موبايلك
- Rotation تلقائي لمفاتيح AI عند انتهاء الحصة
- Keep-alive لمنع النوم على free tier
- لوحة تحكم عربية RTL كاملة
- SQLite مع APScheduler persistent jobs

---

## التثبيت المحلي

```bash
git clone https://github.com/YOUR_USER/social-post.git
cd social-post
pip install -r requirements.txt
cp .env.example .env
# عدّل .env بمفاتيحك
python run.py
```

افتح: `http://localhost:5000`

---

## بيانات الدخول الافتراضية

```
Username: admin
Password: admin123
```

**غيّرهم فوراً من `.env` قبل أي نشر.**

---

## النشر على HuggingFace Spaces

### 1. أضف Secrets في إعدادات الـ Space:

```
SECRET_KEY          → مفتاح عشوائي طويل
ADMIN_USERNAME      → اسم المستخدم
ADMIN_PASSWORD      → كلمة مرور قوية
COHERE_API_KEY      → مفتاح Cohere
CLOUDINARY_CLOUD_NAME
CLOUDINARY_API_KEY
CLOUDINARY_API_SECRET
FB_PAGE_ID
FB_ACCESS_TOKEN
IG_USER_ID
IG_ACCESS_TOKEN
TELEGRAM_BOT_TOKEN
TELEGRAM_ADMIN_CHAT_ID
```

### 2. ارفع الكود:

```bash
git remote add hf https://huggingface.co/spaces/YOUR_USER/YOUR_SPACE
git push hf main
```

---

## النشر على GitHub + Auto-Deploy

### GitHub Secrets المطلوبة:

| Secret | القيمة |
|--------|--------|
| `APP_URL` | رابط التطبيق (للـ keep-alive) مثال: `https://user-space.hf.space` |
| `HF_TOKEN` | HuggingFace Access Token من [hf.co/settings/tokens](https://huggingface.co/settings/tokens) |
| `HF_SPACE` | اسم الـ Space بالصيغة `username/space-name` |

### إضافة Secrets:

```
GitHub Repo → Settings → Secrets and variables → Actions → New repository secret
```

### الـ Workflows:

| الملف | الوظيفة | متى يعمل |
|-------|---------|----------|
| `ci.yml` | Syntax check + Docker build test | كل push/PR |
| `deploy-hf.yml` | Auto-deploy لـ HuggingFace | عند push لـ main |
| `keep-alive.yml` | Ping كل 20 دقيقة | كل 20 دقيقة 24/7 |

---

## النشر على VPS (Ubuntu)

```bash
git clone https://github.com/YOUR_USER/social-post.git /opt/social_post
cd /opt/social_post
cp .env.example .env
nano .env   # أضف مفاتيحك
sudo bash deploy/install.sh
```

### أوامر مفيدة:

```bash
systemctl status social_post       # حالة الخدمة
journalctl -u social_post -f       # السجلات المباشرة
systemctl restart social_post      # إعادة التشغيل
systemctl stop social_post         # إيقاف
```

---

## بوت تيليجرام

1. افتح [@BotFather](https://t.me/BotFather) → `/newbot`
2. انسخ الـ Token → ضعه في `TELEGRAM_BOT_TOKEN`
3. افتح [@userinfobot](https://t.me/userinfobot) → انسخ الـ ID → ضعه في `TELEGRAM_ADMIN_CHAT_ID`

### الأوامر:

```
/status   — حالة النظام
/ideas    — توليد أفكار الآن
/post     — نشر منشور الآن
/pending  — الأفكار المنتظرة
/posted   — آخر المنشورات
/logs     — سجل الأحداث
/keys     — حالة مفاتيح AI
/pause    — إيقاف الجدولة
/resume   — استئناف الجدولة
/skip 5   — تخطي فكرة رقم 5
/delete 5 — حذف فكرة رقم 5
```

---

## هيكل المشروع

```
social_post/
├── app.py                  # Flask app factory + scheduler + health
├── config.py               # إعدادات البيئات
├── wsgi.py                 # نقطة دخول gunicorn
├── gunicorn.conf.py        # إعدادات gunicorn للإنتاج
├── Dockerfile              # Docker image
├── Procfile                # Heroku/Railway
├── database/
│   └── models.py           # SQLAlchemy models
├── routes/
│   ├── auth.py             # تسجيل الدخول
│   ├── dashboard.py        # صفحات لوحة التحكم
│   ├── api.py              # REST API endpoints
│   └── workflow.py         # تشغيل يدوي للـ workflow
├── services/
│   ├── ai_service.py       # استدعاء نماذج AI
│   ├── image_service.py    # توليد الصور + Cloudinary
│   ├── social_service.py   # النشر على المنصات
│   ├── workflow_service.py # منطق الـ workflow الكامل
│   ├── key_rotator.py      # rotation مفاتيح AI
│   └── telegram_bot.py     # بوت تيليجرام
├── templates/              # Jinja2 templates (RTL عربي)
├── deploy/
│   ├── install.sh          # سكريبت تثبيت VPS
│   ├── nginx.conf          # إعدادات Nginx
│   └── social_post.service # systemd service
└── .github/workflows/
    ├── ci.yml              # CI: syntax + docker test
    ├── deploy-hf.yml       # Auto-deploy to HuggingFace
    └── keep-alive.yml      # Ping كل 20 دقيقة
```

---

## License

MIT
