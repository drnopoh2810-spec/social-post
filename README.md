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

نظام نشر محتوى علمي ومعرفي ذكي ومتكامل على منصات السوشال ميديا.
مبني بـ **Flask + APScheduler + Telegram Bot** — يعمل على PythonAnywhere و HuggingFace Spaces.

[![CI](https://github.com/drnopoh2810-spec/social-post/actions/workflows/ci.yml/badge.svg)](https://github.com/drnopoh2810-spec/social-post/actions/workflows/ci.yml)

---

## 🌟 المميزات الرئيسية

### 🤖 الذكاء الاصطناعي
- **توليد أفكار علمية** تلقائياً — منشورات معرفية عميقة باللهجة المصرية
- **كتابة المنشورات** بـ 5 طبقات: افتتاحية → عمق علمي → تصحيح مفهوم → تطبيق عملي → ختام مفتوح
- **تكييف المحتوى** لكل منصة تلقائياً (Instagram / Twitter / Threads / LinkedIn)
- **6 مزودي AI** مع Failover تلقائي: Gemini → Groq → Cohere → OpenRouter → api.airforce → OpenAI
- **Rotation مفاتيح** — عدة مفاتيح لكل مزود، تبديل تلقائي عند انتهاء الحصة
- **Failover بين المزودين** — لو كل مفاتيح مزود انتهت ينتقل للتالي تلقائياً

### 🎨 توليد الصور
**11 مزود بالترتيب (أول نجاح يُستخدم):**
1. ☁️ Cloudflare Worker (Flux 2) — primary
2. 🔵 Google Imagen 4 / Gemini Image — مجاني بمفتاح Gemini
3. 🎨 Ideogram v3 — الأفضل للنص العربي
4. 🟢 OpenAI gpt-image-1 / DALL-E 3
5. 🔷 Stability AI SD 3.5
6. 🤗 HuggingFace Flux Schnell
7. 🔗 Together AI Flux Free
8. ⚡ Fal.ai Flux Schnell
9. 🛩️ api.airforce — مجاني بدون مفتاح
10. 🌸 Pollinations (authenticated)
11. 🌸 Pollinations (anonymous) — last fallback دايماً

**معالجة الصور:**
- Overlay إطار شفاف (PNG) على الصورة
- **Text Overlay** — نص عربي على الصورة بـ 5 خطوط عربية (Cairo / Noto Naskh / Noto Kufi / Amiri / Tajawal)
- تحكم كامل: موضع + إزاحة دقيقة + حجم + لون + خلفية + ظل
- AI يولد العنوان/الجملة التشويقية تلقائياً
- رفع على Cloudinary + حذف تلقائي بعد النشر لتوفير المساحة

### 📢 النشر على المنصات
| المنصة | صورة | نص | ملاحظة |
|--------|------|-----|--------|
| Facebook | ✅ | ✅ | Graph API v20 |
| Instagram | ✅ | — | Business/Creator فقط |
| Twitter/X | ✅ | ✅ | Tweepy OAuth1 |
| Threads | ✅ | ✅ | Threads API v1 |
| LinkedIn | ✅ | ✅ | UGC Posts + Image Upload |

- كل منصة مستقلة — فشل منصة لا يوقف الباقي
- التحقق من credentials قبل المحاولة
- حماية من double-publishing (status = IN_PROGRESS)

### 📊 التحليلات
- جلب engagement metrics حقيقية من كل منصة تلقائياً
- حساب engagement score (likes×1 + comments×3 + shares×5)
- تحديث تلقائي كل 6 ساعات
- تحليل أفضل أسلوب كتابة ونبرة بناءً على البيانات الفعلية
- رسوم بيانية: bar charts + daily trend + top posts

### 🗄️ التخزين والاستمرارية
- **SQLite** — قاعدة البيانات الرئيسية
- **Redis (Upstash)** — حفظ الإعدادات بشكل دائم بين الـ restarts
- **Google Sheets** — backup ثنائي الاتجاه، مصدر الحقيقة للأفكار
- **Cloudinary** — رفع الصور مع حذف تلقائي بعد النشر

**أولوية قراءة الإعدادات:** env vars → Redis → DB

### 🤖 بوت تيليجرام
- لوحة تحكم كاملة بـ Inline Keyboards
- توليد أفكار / نشر منشور / عرض الإحصائيات
- تعديل البرومبتات مباشرةً من التيليجرام
- تفعيل/تعطيل المنصات
- إشعارات فورية عند كل نشر أو خطأ

### ⚙️ الجدولة والأتمتة
- **APScheduler** — جدولة داخلية (HuggingFace)
- **PA Scheduled Tasks** — مهام مستقلة على PythonAnywhere (تعمل حتى لو التطبيق نايم)
- **Auto-updater** — يتحقق من GitHub كل 30 دقيقة ويحدّث تلقائياً
- **Analytics refresh** — تحديث metrics كل 6 ساعات

---

## 🚀 التثبيت

### على PythonAnywhere (موصى به)

```bash
# في Bash Console
git clone https://github.com/drnopoh2810-spec/social-post.git
cd social-post
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env   # أضف مفاتيحك
```

**إعداد WSGI:**
```python
import sys, os
sys.path.insert(0, '/home/USERNAME/social-post')
from dotenv import load_dotenv
load_dotenv('/home/USERNAME/social-post/.env')
os.environ.setdefault('FLASK_ENV', 'production')
from app import create_app
application = create_app('production')
```

**Scheduled Tasks (من لوحة التحكم → /scheduler):**
```
Task 1: /home/USERNAME/social-post/venv/bin/python /home/USERNAME/social-post/pa_task_ideas.py
        Daily at 08:00

Task 2: /home/USERNAME/social-post/venv/bin/python /home/USERNAME/social-post/pa_task_post.py
        Daily at 09:00
```

### على HuggingFace Spaces

**Secrets الإلزامية:**
```
SECRET_KEY          → مفتاح عشوائي (openssl rand -hex 32)
ADMIN_USERNAME      → اسم المستخدم
ADMIN_PASSWORD      → كلمة مرور قوية
FLASK_ENV           → production
REDIS_URL           → rediss://default:TOKEN@host:port (Upstash)
```

**Secrets الاختيارية (أو من لوحة التحكم):**
```
GEMINI_API_KEY / COHERE_API_KEY / GROQ_API_KEY / OPENROUTER_API_KEY
CLOUDINARY_CLOUD_NAME / CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET
FB_PAGE_ID / FB_ACCESS_TOKEN
IG_USER_ID / IG_ACCESS_TOKEN
TWITTER_API_KEY / TWITTER_API_SECRET / TWITTER_ACCESS_TOKEN / TWITTER_ACCESS_TOKEN_SECRET
THREADS_USER_ID / THREADS_ACCESS_TOKEN
LI_PERSON_ID / LI_ACCESS_TOKEN
TELEGRAM_BOT_TOKEN / TELEGRAM_ADMIN_CHAT_ID
WORKER_URL / POLLINATIONS_KEY
GOOGLE_SHEET_ID / GOOGLE_SHEETS_CREDENTIALS
```

### محلياً

```bash
git clone https://github.com/drnopoh2810-spec/social-post.git
cd social-post
pip install -r requirements.txt
cp .env.example .env
python run.py
```

افتح: `http://localhost:5000`

---

## 🔑 بيانات الدخول الافتراضية

```
Username: admin
Password: admin123
```

**غيّرهم فوراً من `.env` أو من لوحة التحكم.**

---

## 📁 هيكل المشروع

```
social_post/
├── app.py                    # Flask factory + scheduler
├── config.py                 # إعدادات البيئات
├── prompts_config.py         # كل البرومبتات في مكان واحد
├── wsgi.py / run.py          # نقاط الدخول
├── pa_task_ideas.py          # PA Scheduled Task — توليد الأفكار
├── pa_task_post.py           # PA Scheduled Task — النشر
├── database/
│   └── models.py             # SQLAlchemy models (User/Post/Config/Prompt/...)
├── routes/
│   ├── auth.py               # تسجيل الدخول
│   ├── dashboard.py          # صفحات لوحة التحكم
│   ├── api.py                # REST API + Analytics + Image test
│   └── workflow.py           # تشغيل يدوي
├── services/
│   ├── ai_service.py         # استدعاء نماذج AI (6 مزودين)
│   ├── key_rotator.py        # Rotation + Failover بين المزودين
│   ├── image_service.py      # 11 مزود صور + Cloudinary
│   ├── overlay_service.py    # Text overlay بـ 5 خطوط عربية
│   ├── analytics_service.py  # جلب metrics من المنصات
│   ├── social_service.py     # النشر على 5 منصات
│   ├── workflow_service.py   # منطق الـ workflow الكامل
│   ├── telegram_bot.py       # بوت تيليجرام
│   ├── sheets_sync.py        # Google Sheets sync
│   ├── redis_config.py       # Redis persistence
│   └── auto_updater.py       # تحديث تلقائي من GitHub
├── templates/pages/
│   ├── dashboard.html        # لوحة التحكم الرئيسية
│   ├── posts.html            # إدارة الأفكار والمنشورات
│   ├── analytics.html        # التحليلات والأداء
│   ├── models.html           # اختيار نماذج AI (live fetch)
│   ├── ai_keys.html          # مفاتيح AI + Image providers
│   ├── image_config.html     # إعدادات الصور + Text Overlay
│   ├── prompts.html          # تعديل البرومبتات
│   ├── scheduler.html        # الجدولة + PA Tasks
│   ├── platforms.html        # إعدادات المنصات
│   └── backup.html           # نسخ احتياطية
├── static/fonts/             # خطوط عربية (Cairo/Noto/Amiri/Tajawal)
├── deploy/                   # ملفات النشر (nginx/systemd)
└── .github/workflows/
    ├── ci.yml                # CI checks
    ├── deploy-hf.yml         # Auto-deploy to HuggingFace
    └── keep-alive.yml        # Ping كل 20 دقيقة
```

---

## 📱 بوت تيليجرام

1. افتح [@BotFather](https://t.me/BotFather) → `/newbot` → انسخ الـ Token
2. افتح البوت → `/myid` → انسخ الـ Chat ID
3. أضفهم في `.env` أو لوحة التحكم → `/telegram`

**القوائم المتاحة:**
- 📊 الإحصائيات — ملخص شامل
- 📝 الأفكار — عرض / تخطي / حذف / نشر
- 📢 نشر الآن — تشغيل محرك النشر
- 🧠 توليد أفكار — تشغيل مصنع الأفكار
- 📈 التحليلات — أفضل المنشورات
- 📋 السجل — آخر الأحداث
- 📱 المنصات — تفعيل/تعطيل
- 🗝️ مفاتيح AI — حالة المفاتيح
- ✍️ البرومبتات — عرض وتعديل
- ⚙️ الإعدادات — عرض الإعدادات الحالية
- ⏸️ إيقاف/تشغيل الجدولة

---

## 🔧 إعداد الخطوط العربية

لتفعيل Text Overlay بخطوط عربية على PythonAnywhere:

```bash
cd /home/USERNAME/social-post/static/fonts
# حمّل الخطوط من Google Fonts
wget "https://fonts.gstatic.com/s/cairo/v28/SLXgc1nY6HkvalIhTp2mxdt0UX8.woff2" -O Cairo-Regular.ttf
```

أو ارفع الملفات يدوياً:
- `Cairo-Regular.ttf` — من [fonts.google.com/specimen/Cairo](https://fonts.google.com/specimen/Cairo)
- `NotoNaskhArabic-Regular.ttf` — من [fonts.google.com/noto](https://fonts.google.com/noto)
- `Amiri-Regular.ttf` — من [fonts.google.com/specimen/Amiri](https://fonts.google.com/specimen/Amiri)
- `Tajawal-Regular.ttf` — من [fonts.google.com/specimen/Tajawal](https://fonts.google.com/specimen/Tajawal)
- `NotoKufiArabic-Regular.ttf` — من [fonts.google.com/noto](https://fonts.google.com/noto)

---

## 📋 المتغيرات البيئية الكاملة

راجع ملف [`.env.example`](.env.example) للقائمة الكاملة.

---

## License

MIT — [drnopoh2810-spec](https://github.com/drnopoh2810-spec)
