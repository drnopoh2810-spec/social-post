# نقل المشروع في 3 خطوات ⚡

## نعم! الآن يمكنك نقل المشروع لحساب جديد في 3 خطوات فقط 🎉

---

## الخطوات:

### 1️⃣ Clone المشروع
```bash
git clone https://github.com/your-repo/social-post.git
cd social-post
```

### 2️⃣ أضف Google Sheets Credentials
```bash
export GOOGLE_SHEETS_CREDENTIALS='{"type":"service_account",...}'
export GOOGLE_SHEET_ID='1b7FSivlYSy8rbMhW5AyruU4TZ4OdzeBKirCHk6bUKRQ'
```

### 3️⃣ شغّل المشروع
```bash
python run.py
```

---

## ماذا يحدث تلقائياً؟

```
🔄 Checking Google Sheets for existing config...
✅ Restored 67 items from Sheets
✅ Restored 150 posts from Google Sheets
🚀 App is ready with all your settings!
```

---

## ما يتم استيراده تلقائياً:

- ✅ جميع الإعدادات (niche, image settings, schedules)
- ✅ مفاتيح AI (Cohere, Gemini, Groq, إلخ)
- ✅ مفاتيح المنصات (Facebook, Twitter, إلخ)
- ✅ البرومبتات المخصصة
- ✅ إعدادات المنصات
- ✅ جميع المنشورات مع engagement scores

---

## المزامنة التلقائية:

```python
# أي تغيير يُحفظ تلقائياً في Google Sheets
Config.set('niche', 'تعليم')  # ✅ حُفظ في Sheet
# إضافة مفتاح AI  # ✅ حُفظ في Sheet
# نشر منشور  # ✅ حُفظ في Sheet
```

---

## السيناريوهات:

### Sheet فيه بيانات + DB فاضية (الحالة المعتادة)
```
✅ يستورد كل شيء من Sheet تلقائياً
```

### Sheet فاضي + DB فيها بيانات
```
✅ يملأ Sheet من DB تلقائياً
✅ ينشئ Tabs والأعمدة تلقائياً
```

### كلاهما فاضي
```
✅ يستخدم Defaults ويملأ الاثنين
```

---

## الخلاصة:

### قبل:
```
❌ نسخ ملفات + تصدير DB + استيراد يدوي
```

### الآن:
```
✅ 3 خطوات فقط → كل شيء يعمل!
```

---

## للمزيد من التفاصيل:

- `FINAL_SETUP_GUIDE.md` - دليل كامل
- `AUTO_SYNC_SCENARIOS.md` - شرح السيناريوهات
- `SHEETS_SYNC_MIGRATION.md` - توثيق تقني

**النظام جاهز! 🚀**
