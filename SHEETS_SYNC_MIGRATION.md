# تحويل النظام من Redis إلى Google Sheets ✅

## التاريخ: 2026-03-26

---

## التغييرات المطبقة 🔄

### 1. ✅ إلغاء التكامل مع Redis

#### الملفات المعدلة:
- `templates/pages/backup.html` - إزالة قسم Redis بالكامل
- `routes/api.py` - حذف endpoints Redis:
  - ❌ `/api/backup/push-redis`
  - ❌ `/api/redis/status`
  - ❌ `/api/redis/sync`
- `database/models.py` - تحديث `Config.set()` لإزالة Redis sync

---

### 2. ✅ إضافة نظام Google Sheets الشامل

#### الملفات الجديدة:
- `services/config_sheets_sync.py` - خدمة مزامنة الإعدادات مع Sheets

#### الوظائف الجديدة:
```python
# Sync to Sheets
sync_config_to_sheets()      # حفظ جميع الإعدادات
sync_ai_keys_to_sheets()     # حفظ مفاتيح AI
sync_api_keys_to_sheets()    # حفظ مفاتيح API
sync_prompts_to_sheets()     # حفظ البرومبتات
sync_platforms_to_sheets()   # حفظ إعدادات المنصات
sync_all_to_sheets()         # حفظ كل شيء

# Restore from Sheets
restore_config_from_sheets() # استعادة الإعدادات
restore_all_from_sheets()    # استعادة كل شيء
```

#### API Endpoints الجديدة:
- ✅ `POST /api/config/sync-to-sheets` - حفظ جميع الإعدادات
- ✅ `POST /api/config/restore-from-sheets` - استعادة جميع الإعدادات

---

### 3. ✅ Auto-Sync عند التغيير

تم تحديث `Config.set()` لحفظ التغييرات تلقائياً في Google Sheets:

```python
@staticmethod
def set(key, value):
    """Save to DB and auto-sync to Google Sheets."""
    # Save to DB
    row = db.session.get(Config, key)
    if row:
        row.value = value
    else:
        row = Config(key=key, value=value)
        db.session.add(row)
    db.session.commit()
    
    # Auto-sync to Google Sheets (async, non-blocking)
    try:
        from services.config_sheets_sync import sync_config_to_sheets, is_configured
        if is_configured():
            import threading
            threading.Thread(target=sync_config_to_sheets, daemon=True).start()
    except Exception:
        pass
```

**النتيجة:** أي تغيير في الإعدادات يُحفظ تلقائياً في Google Sheets في الخلفية!

---

## هيكل Google Sheet 📊

### Sheet ID:
```
1b7FSivlYSy8rbMhW5AyruU4TZ4OdzeBKirCHk6bUKRQ
```

### الـ Tabs (Worksheets):

#### 1. Config
```
key | value | updated_at
```
جميع إعدادات النظام (niche, image_width, api keys, إلخ)

#### 2. AI_Keys
```
id | provider | label | key_value | priority | is_active | is_exhausted | updated_at
```
مفاتيح AI (Cohere, Gemini, Groq, OpenRouter, إلخ)

#### 3. API_Keys
```
id | platform | label | key_value | is_active | updated_at
```
مفاتيح المنصات الاجتماعية (Facebook, Twitter, إلخ)

#### 4. Prompts
```
stage | model | temperature | max_tokens | system_prompt | user_prompt | updated_at
```
البرومبتات المخصصة لكل مرحلة

#### 5. Platforms
```
name | enabled | settings | updated_at
```
إعدادات المنصات (Facebook, Instagram, إلخ)

#### 6. Posts (موجود مسبقاً)
```
id | idea | keywords | tone | status | created_at | posted_at | post_content | ...
```
جميع المنشورات

---

## الاستخدام 🚀

### من الواجهة (Dashboard):

1. افتح `/backup`
2. اضغط "⬆️ حفظ جميع الإعدادات الآن" لحفظ كل شيء
3. اضغط "⬇️ استعادة جميع الإعدادات" لاستعادة من الـ Sheet
4. اضغط "📝 رفع المنشورات" لحفظ المنشورات

### من الكود:

```python
from services.config_sheets_sync import sync_all_to_sheets, restore_all_from_sheets

# حفظ كل شيء
counts = sync_all_to_sheets()
# {'config': 50, 'ai_keys': 5, 'api_keys': 3, 'prompts': 6, 'platforms': 5}

# استعادة كل شيء
counts = restore_all_from_sheets()
```

### Auto-Sync:

```python
from database.models import Config

# أي تغيير يُحفظ تلقائياً في Sheets
Config.set('niche', 'تعليم')  # ✅ يُحفظ في DB + Sheets تلقائياً
Config.set('image_width', '1080')  # ✅ يُحفظ في DB + Sheets تلقائياً
```

---

## المزايا الجديدة ✨

### 1. ✅ مزامنة تلقائية
- أي تغيير في الإعدادات يُحفظ فوراً في Google Sheets
- لا حاجة لضغط أي زر

### 2. ✅ نسخ احتياطي دائم
- جميع الإعدادات محفوظة في السحابة
- يمكن الوصول إليها من أي مكان
- يمكن تعديلها مباشرة من Google Sheets

### 3. ✅ استعادة سهلة
- استعادة كاملة بضغطة زر واحدة
- لا حاجة لملفات JSON

### 4. ✅ شفافية كاملة
- يمكن رؤية جميع الإعدادات في الـ Sheet
- يمكن مراجعة التغييرات
- يمكن التعديل اليدوي إذا لزم الأمر

### 5. ✅ لا تكاليف إضافية
- Google Sheets مجاني
- لا حاجة لـ Redis/Upstash المدفوع

---

## الإعداد المطلوب ⚙️

### 1. Google Sheets Credentials

أضف في الإعدادات أو Environment Variables:

```bash
GOOGLE_SHEETS_CREDENTIALS='{"type":"service_account","project_id":"...","private_key":"...","client_email":"..."}'
GOOGLE_SHEET_ID='1b7FSivlYSy8rbMhW5AyruU4TZ4OdzeBKirCHk6bUKRQ'
```

### 2. منح الصلاحيات

شارك الـ Sheet مع Service Account Email:
```
your-service-account@project-id.iam.gserviceaccount.com
```
بصلاحية "Editor"

---

## الاختبار 🧪

### 1. اختبار الحفظ:
```bash
curl -X POST https://nopoh55678.pythonanywhere.com/api/config/sync-to-sheets \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION"
```

### 2. اختبار الاستعادة:
```bash
curl -X POST https://nopoh55678.pythonanywhere.com/api/config/restore-from-sheets \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION"
```

### 3. اختبار Auto-Sync:
```python
from database.models import Config

# غيّر إعداد
Config.set('test_key', 'test_value')

# تحقق من الـ Sheet — يجب أن تجد test_key في tab "Config"
```

---

## الملفات المحذوفة/المعطلة ❌

لم يتم حذف أي ملفات، لكن تم تعطيل:
- ❌ `services/redis_config.py` - لم يعد مستخدماً
- ❌ Redis endpoints في `routes/api.py`
- ❌ Redis sync في `Config.set()`

يمكن حذف `services/redis_config.py` إذا أردت، لكن تركه لن يسبب مشاكل.

---

## الخلاصة 🎯

### قبل التحديث:
- ❌ Redis مدفوع (Upstash)
- ❌ مزامنة يدوية
- ❌ صعوبة الوصول للإعدادات
- ❌ تكاليف إضافية

### بعد التحديث:
- ✅ Google Sheets مجاني
- ✅ مزامنة تلقائية
- ✅ وصول سهل من أي مكان
- ✅ شفافية كاملة
- ✅ نسخ احتياطي دائم
- ✅ لا تكاليف إضافية

---

## الخطوات التالية 📝

1. ✅ تأكد من إعداد Google Sheets Credentials
2. ✅ اضغط "حفظ جميع الإعدادات الآن" من `/backup`
3. ✅ تحقق من الـ Sheet أن كل شيء محفوظ
4. ✅ جرّب تغيير إعداد وتحقق من Auto-Sync
5. ✅ (اختياري) احذف `services/redis_config.py`

---

## الدعم 💬

إذا واجهت أي مشاكل:
1. تحقق من Google Sheets Credentials
2. تحقق من صلاحيات الـ Sheet
3. راجع الـ logs في `/var/log/`
4. تحقق من الـ Sheet ID صحيح

النظام الآن جاهز للعمل بشكل كامل مع Google Sheets! 🚀
