# سيناريوهات المزامنة التلقائية 🔄

## عند بدء التشغيل (Startup)

النظام يتعامل مع 3 سيناريوهات تلقائياً:

---

## السيناريو 1️⃣: Sheet فاضي + DB فيها إعدادات

**الحالة:**
- 📊 Google Sheet فاضي (أول مرة)
- 💾 Database فيها إعدادات (من التشغيل السابق أو defaults)

**ما يحدث:**
```
1. النظام يكتشف أن الـ Sheet فاضي
2. يأخذ كل الإعدادات من DB
3. ينشئ الـ Tabs تلقائياً:
   - Config
   - AI_Keys
   - API_Keys
   - Prompts
   - Platforms
   - Posts
4. يكتب الأعمدة (Headers) في كل Tab
5. يملأ البيانات من DB
```

**النتيجة:**
```
✅ Initialized Sheets with 67 items: 
   {'config': 45, 'ai_keys': 5, 'api_keys': 3, 'prompts': 7, 'platforms': 5}
```

**مثال Log:**
```
📤 Sheets is empty — pushing current DB config to Sheets...
✅ Initialized Sheets with 67 items
✓ Synced posts to Google Sheets
```

---

## السيناريو 2️⃣: Sheet فيها بيانات + DB فاضية

**الحالة:**
- 📊 Google Sheet فيها بيانات (من تشغيل سابق)
- 💾 Database فاضية (حساب جديد / DB جديدة)

**ما يحدث:**
```
1. النظام يكتشف أن الـ Sheet فيها بيانات
2. يقرأ كل الـ Tabs
3. يستورد البيانات إلى DB:
   - Config → جدول config
   - AI_Keys → جدول ai_provider_keys
   - API_Keys → جدول api_keys
   - Prompts → جدول prompts
   - Platforms → جدول platforms
   - Posts → جدول posts
```

**النتيجة:**
```
✅ Restored 67 items from Sheets: 
   {'config': 45, 'ai_keys': 5, 'api_keys': 3, 'prompts': 7, 'platforms': 5}
✅ Restored 150 posts from Google Sheets
```

**مثال Log:**
```
🔄 Checking Google Sheets for existing config...
✅ Restored 67 items from Sheets
✅ Restored 150 posts from Google Sheets
```

---

## السيناريو 3️⃣: كلاهما فاضي (أول تشغيل تماماً)

**الحالة:**
- 📊 Google Sheet فاضي
- 💾 Database فاضية

**ما يحدث:**
```
1. النظام يستخدم الـ Defaults المبرمجة
2. يملأ DB بالـ defaults
3. ينشئ الـ Tabs في Sheet
4. يكتب الـ defaults في Sheet
```

**النتيجة:**
```
📊 Both DB and Sheets empty — using defaults and syncing to Sheets...
✅ Initialized Sheets with defaults: 
   {'config': 15, 'ai_keys': 0, 'api_keys': 0, 'prompts': 7, 'platforms': 5}
```

**الـ Defaults المبرمجة:**
- ⚙️ Config: niche, image_width, image_height, schedules, إلخ
- ✍️ Prompts: 7 برومبتات للمراحل المختلفة
- 📱 Platforms: Facebook, Instagram, Twitter, Threads, LinkedIn

---

## السيناريو 4️⃣: كلاهما فيهم بيانات (تشغيل عادي)

**الحالة:**
- 📊 Google Sheet فيها بيانات
- 💾 Database فيها بيانات

**ما يحدث:**
```
1. النظام يقارن البيانات
2. يستورد أي تحديثات من Sheet (engagement scores, إلخ)
3. يدفع أي بيانات جديدة من DB إلى Sheet
```

**النتيجة:**
```
✓ Config already exists (45 items) — skipping restore
✓ Updated 5 posts from Google Sheets
✓ Synced posts to Google Sheets
```

---

## المزامنة التلقائية أثناء التشغيل ⚡

### عند تغيير الإعدادات:
```python
Config.set('niche', 'تعليم خاص')
# ✅ يُحفظ في DB فوراً
# ✅ يُحفظ في Sheet تلقائياً (في الخلفية)
```

### عند إضافة/تعديل مفتاح AI:
```python
# من /ai-keys
# ✅ يُحفظ في DB
# ✅ يُحفظ في Sheet تلقائياً
```

### عند نشر منشور:
```python
# بعد النشر الناجح
# ✅ يُحدث status في DB
# ✅ يُحدث في Sheet تلقائياً
```

---

## هيكل الـ Sheet المُنشأ تلقائياً 📋

### Tab: Config
```
| key                  | value              | updated_at          |
|----------------------|--------------------|---------------------|
| niche                | تربية خاصة         | 2026-03-26 10:00:00 |
| image_width          | 1080               | 2026-03-26 10:00:00 |
| image_height         | 1350               | 2026-03-26 10:00:00 |
| cohere_api_key       | sk-xxx...          | 2026-03-26 10:00:00 |
| ...                  | ...                | ...                 |
```

### Tab: AI_Keys
```
| id | provider | label      | key_value  | priority | is_active | is_exhausted | updated_at          |
|----|----------|------------|------------|----------|-----------|--------------|---------------------|
| 1  | cohere   | حساب رئيسي | sk-xxx...  | 0        | TRUE      | FALSE        | 2026-03-26 10:00:00 |
| 2  | gemini   | مفتاح 1    | AIza...    | 0        | TRUE      | FALSE        | 2026-03-26 10:00:00 |
```

### Tab: API_Keys
```
| id | platform  | label      | key_value      | is_active | updated_at          |
|----|-----------|------------|----------------|-----------|---------------------|
| 1  | facebook  | صفحة رئيسية | EAABwz...      | TRUE      | 2026-03-26 10:00:00 |
| 2  | twitter   | حساب 1     | oauth1:xxx...  | TRUE      | 2026-03-26 10:00:00 |
```

### Tab: Prompts
```
| stage        | model                      | temperature | max_tokens | system_prompt | user_prompt | updated_at          |
|--------------|----------------------------|-------------|------------|---------------|-------------|---------------------|
| idea_factory | command-r7b-arabic-02-2025 | 0.8         | 1500       | أنت خبير...   | اقترح 5...  | 2026-03-26 10:00:00 |
| post_writer  | command-r7b-arabic-02-2025 | 0.7         | 2000       | أنت كاتب...   | اكتب منشور..| 2026-03-26 10:00:00 |
```

### Tab: Platforms
```
| name      | enabled | settings | updated_at          |
|-----------|---------|----------|---------------------|
| facebook  | TRUE    | {}       | 2026-03-26 10:00:00 |
| instagram | TRUE    | {}       | 2026-03-26 10:00:00 |
| twitter   | TRUE    | {}       | 2026-03-26 10:00:00 |
```

### Tab: Posts
```
| id | idea           | keywords | tone    | status | created_at          | posted_at           | post_content | ... |
|----|----------------|----------|---------|--------|---------------------|---------------------|--------------|-----|
| 1  | نصائح تعليمية | تعليم    | ودود    | POSTED | 2026-03-26 09:00:00 | 2026-03-26 09:30:00 | اكتشف...    | ... |
```

---

## الخلاصة 🎯

### ✅ ما يحدث تلقائياً:

1. **عند أول تشغيل:**
   - إذا Sheet فاضي → يملأه من DB
   - إذا DB فاضية → يملأها من Sheet
   - إذا كلاهما فاضي → يستخدم defaults ويملأ الاثنين

2. **أثناء التشغيل:**
   - أي تغيير في الإعدادات → يُحفظ في Sheet تلقائياً
   - أي إضافة/تعديل مفتاح → يُحفظ في Sheet تلقائياً
   - أي نشر منشور → يُحفظ في Sheet تلقائياً

3. **عند كل restart:**
   - يتحقق من Sheet ويستورد أي تحديثات
   - يدفع أي بيانات جديدة من DB

### ✅ لا تحتاج أن تفعل شيء:

- ❌ لا تحتاج تضغط "حفظ"
- ❌ لا تحتاج تضغط "استعادة"
- ❌ لا تحتاج تنشئ الـ Tabs يدوياً
- ❌ لا تحتاج تكتب الأعمدة يدوياً

### ✅ كل شيء أوتوماتيكي! 🚀

فقط:
1. أضف `GOOGLE_SHEETS_CREDENTIALS` و `GOOGLE_SHEET_ID`
2. شغّل المشروع
3. النظام يتولى الباقي تلقائياً!

---

## مثال عملي 💡

### السيناريو: نقل المشروع لحساب جديد

```bash
# 1. على الحساب القديم (قبل النقل)
# النظام حفظ كل شيء في Sheet تلقائياً ✅

# 2. على الحساب الجديد
git clone https://github.com/your-repo/social-post.git
cd social-post

# 3. أضف نفس الـ credentials
export GOOGLE_SHEETS_CREDENTIALS='{"type":"service_account",...}'
export GOOGLE_SHEET_ID='1b7FSivlYSy8rbMhW5AyruU4TZ4OdzeBKirCHk6bUKRQ'

# 4. شغّل المشروع
python run.py

# 5. النظام يستورد كل شيء تلقائياً! ✅
# 🔄 Checking Google Sheets for existing config...
# ✅ Restored 67 items from Sheets
# ✅ Restored 150 posts from Google Sheets
# ✓ All settings and data restored!
```

**النتيجة:** المشروع يعمل بنفس الإعدادات تماماً! 🎉
