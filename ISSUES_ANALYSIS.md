# تحليل المشاكل وحلولها 🔍

## المشاكل المكتشفة من الـ Logs

### 1. ❌ Cloudinary Upload Error (400 Bad Request)
**المشكلة:**
```
400 Client Error: Bad Request for url: https://api.cloudinary.com/v1_1/dmxcipnbf/image/upload
```

**السبب المحتمل:**
- الصورة المُرسلة إلى Cloudinary قد تكون فارغة أو تالفة
- المشكلة تحدث بعد فشل جميع مزودي الصور الآخرين
- عندما تصل صورة غير صالحة (bytes فارغة أو تالفة) إلى Cloudinary

**الحل:**
```python
# في image_service.py - دالة upload_to_cloudinary
def upload_to_cloudinary(image_bytes, cloud_name, api_key, api_secret,
                          folder="social_posts"):
    """Upload image bytes to Cloudinary. Returns (secure_url, public_id)."""
    # ✅ إضافة فحص للصورة قبل الرفع
    if not image_bytes or len(image_bytes) < 100:
        raise ValueError("Image bytes are empty or too small")
    
    # ✅ التحقق من صحة الصورة
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
    except Exception as e:
        raise ValueError(f"Invalid image data: {e}")
    
    # ... باقي الكود
```

---

### 2. ❌ Google Imagen API Errors

#### 2.1 Imagen Models (400 Bad Request)
**المشكلة:**
```
400 Bad Request for url: https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict
400 Bad Request for url: https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-fast-generate-001:predict
```

**السبب:**
- Google Imagen API تغيّر endpoint أو format
- الـ API قد لا يدعم `:predict` endpoint بعد الآن
- المفتاح قد لا يملك صلاحيات Imagen

**الحل:**
```python
# في image_service.py - دالة generate_image_gemini
def generate_image_gemini(api_key: str, prompt: str,
                           width=1080, height=1350,
                           model: str = "imagen-4.0-generate-001") -> bytes:
    """Google Imagen 4 / Gemini Image — free with Gemini API key."""
    import base64
    aspect = _get_aspect_ratio(width, height)

    # ✅ استخدام Imagen 3 بدلاً من 4 (أكثر استقراراً)
    if "imagen" in model and "4.0" in model:
        model = model.replace("4.0", "3.0")
    
    if "gemini" in model:
        # ... كود Gemini
    else:
        # ✅ تحديث endpoint للـ Imagen
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model}:generateImages?key={api_key}")  # ✅ تغيير من :predict
        payload = {
            "prompt": prompt,
            "numberOfImages": 1,
            "aspectRatio": aspect,
        }
        # ... باقي الكود
```

#### 2.2 Gemini Model Not Found (404)
**المشكلة:**
```
404 Not Found for url: https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent
```

**السبب:**
- النموذج `gemini-2.0-flash-exp` تجريبي وقد يكون غير متاح
- الـ endpoint قد تغيّر

**الحل:**
```python
# في image_service.py - تحديث قائمة النماذج
GEMINI_IMAGE_MODELS = [
    "gemini-1.5-flash",           # ✅ مستقر ومتاح
    "gemini-1.5-pro",             # ✅ مستقر
    # "gemini-2.0-flash-exp",     # ❌ إزالة النماذج التجريبية غير المستقرة
    "imagen-3.0-generate-001",    # ✅ تغيير من 4.0 إلى 3.0
    "imagen-3.0-fast-generate-001",
]
```

---

### 3. ❌ api.airforce Proxy Error (403 Forbidden)
**المشكلة:**
```
HTTPSConnectionPool(host='anondrop.net', port=443): Max retries exceeded
Caused by ProxyError('Unable to connect to proxy', OSError('Tunnel connection failed: 403 Forbidden'))
```

**السبب:**
- PythonAnywhere يحظر الاتصال بـ `anondrop.net` (موقع استضافة الصور)
- api.airforce يُرجع روابط صور على `anondrop.net` والتي لا يمكن الوصول إليها من PythonAnywhere
- PythonAnywhere Free Plan يحظر معظم المواقع الخارجية

**الحل:**
```python
# في image_service.py - دالة generate_image_airforce
def generate_image_airforce(prompt: str, width=1024, height=1024,
                             model: str = "flux-2-klein-4b",
                             api_key: str = "") -> bytes:
    """api.airforce image generation via SSE streaming."""
    import json as _json

    if api_key and model != "flux":
        # ... كود SSE
        with requests.post(...) as resp:
            for line in resp.iter_lines():
                # ... معالجة الـ chunks
                if img_url:
                    # ✅ إضافة timeout أقصر وتجاهل أخطاء anondrop.net
                    try:
                        # ✅ فحص الـ domain قبل التحميل
                        if "anondrop.net" in img_url:
                            logger.warning(f"Skipping anondrop.net URL (blocked by PA): {img_url}")
                            continue
                        
                        img_r = requests.get(img_url, timeout=30)  # ✅ timeout أقصر
                        img_r.raise_for_status()
                        return img_r.content
                    except Exception as e:
                        logger.warning(f"Failed to download from {img_url}: {e}")
                        continue
                
                # ✅ تفضيل base64 على URLs
                b64 = (chunk.get("b64_json") or ...)
                if b64:
                    return base64.b64decode(b64)
```

**حل بديل:** تعطيل api.airforce على PythonAnywhere:
```python
# في config.py أو .env
DISABLE_AIRFORCE_ON_PA = True

# في image_service.py
def _try_airforce(prompt: str, width: int, height: int) -> bytes | None:
    # ✅ تخطي api.airforce على PythonAnywhere
    import os
    if os.environ.get("PYTHONANYWHERE_DOMAIN"):
        logger.info("Skipping api.airforce (running on PythonAnywhere)")
        return None
    # ... باقي الكود
```

---

### 4. ⚠️ Overlay Service Error (cannot identify image file)
**المشكلة:**
```
WARNING services.overlay_service: Overlay failed (returning original): cannot identify image file <_io.BytesIO object>
```

**السبب:**
- الصورة الواردة إلى `process_overlay` تالفة أو فارغة
- PIL لا يستطيع قراءة البيانات من BytesIO
- المشكلة تحدث بعد فشل توليد الصورة

**الحل:**
```python
# في overlay_service.py - دالة apply_text_overlay
def apply_text_overlay(image_bytes: bytes, text: str, cfg: dict = None) -> bytes:
    """Apply Arabic text overlay on image using Pillow."""
    from PIL import Image, ImageDraw, ImageFont

    if not text or not text.strip():
        return image_bytes
    
    # ✅ إضافة فحص للصورة
    if not image_bytes or len(image_bytes) < 100:
        logger.warning("Image bytes too small for overlay")
        return image_bytes

    try:
        # ✅ التحقق من صحة الصورة قبل المعالجة
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()  # ✅ التحقق من سلامة الصورة
        
        # ✅ إعادة فتح الصورة بعد verify (لأن verify يُغلق الملف)
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    except Exception as e:
        logger.warning(f"Cannot open image for overlay: {e}")
        return image_bytes
    
    # ... باقي الكود
```

---

## الحلول الموصى بها 🛠️

### الحل الشامل: تحسين Pipeline توليد الصور

```python
# في image_service.py - دالة process_image
def process_image(post_data, cfg):
    """Main image generation pipeline with robust error handling."""
    from services.overlay_service import process_overlay
    
    prompt = post_data.get('image_prompt', '')
    if not prompt:
        return None, None
    
    width  = int(cfg.get('image_width', 1080))
    height = int(cfg.get('image_height', 1350))
    
    # ✅ محاولة كل المزودين بالترتيب
    providers = [
        ("Cloudflare Worker", lambda: _try_cloudflare(prompt, width, height)),
        ("Google Imagen", lambda: _try_gemini_image(prompt, width, height)),
        ("Ideogram", lambda: _try_ideogram(prompt, width, height)),
        ("OpenAI", lambda: _try_openai_image(prompt, width, height)),
        ("Stability AI", lambda: _try_stability(prompt, width, height)),
        ("HuggingFace", lambda: _try_huggingface(prompt, width, height)),
        ("Together AI", lambda: _try_together(prompt, width, height)),
        ("Fal.ai", lambda: _try_fal(prompt, width, height)),
        # ("api.airforce", lambda: _try_airforce(prompt, width, height)),  # ❌ معطل على PA
        ("Pollinations", lambda: _try_pollinations(prompt, width, height)),
    ]
    
    image_bytes = None
    used_provider = None
    
    for provider_name, provider_func in providers:
        try:
            logger.info(f"Trying {provider_name}...")
            image_bytes = provider_func()
            if image_bytes and len(image_bytes) > 100:
                # ✅ التحقق من صحة الصورة
                from PIL import Image
                try:
                    img = Image.open(io.BytesIO(image_bytes))
                    img.verify()
                    used_provider = provider_name
                    logger.info(f"✅ Image generated via {provider_name}")
                    break
                except Exception as e:
                    logger.warning(f"{provider_name} returned invalid image: {e}")
                    image_bytes = None
        except Exception as e:
            logger.warning(f"{provider_name} failed: {e}")
    
    if not image_bytes:
        logger.error("❌ All image providers failed")
        return None, None
    
    # ✅ Apply overlay (مع معالجة الأخطاء)
    try:
        image_bytes = process_overlay(
            image_bytes,
            post_data.get('post_content', ''),
            post_data.get('idea', ''),
            used_provider
        )
    except Exception as e:
        logger.warning(f"Overlay failed: {e}")
    
    # ✅ Upload to Cloudinary (مع معالجة الأخطاء)
    try:
        cloud_name = cfg.get('cloudinary_cloud_name', '')
        api_key    = cfg.get('cloudinary_api_key', '')
        api_secret = cfg.get('cloudinary_api_secret', '')
        
        if not all([cloud_name, api_key, api_secret]):
            logger.error("Cloudinary credentials missing")
            return None, None
        
        url, public_id = upload_to_cloudinary(
            image_bytes, cloud_name, api_key, api_secret
        )
        return url, public_id
    except Exception as e:
        logger.error(f"Cloudinary upload failed: {e}")
        return None, None
```

---

## خطوات التطبيق 📋

### 1. تحديث image_service.py
- ✅ إضافة فحص صحة الصور قبل الرفع
- ✅ تحديث Imagen models (استخدام 3.0 بدلاً من 4.0)
- ✅ تعطيل api.airforce على PythonAnywhere
- ✅ تحسين معالجة الأخطاء

### 2. تحديث overlay_service.py
- ✅ إضافة فحص صحة الصور قبل المعالجة
- ✅ استخدام img.verify() للتحقق من سلامة الصورة

### 3. تحديث قائمة المزودين
- ✅ إزالة النماذج التجريبية غير المستقرة
- ✅ ترتيب المزودين حسب الموثوقية

### 4. إضافة Logging محسّن
- ✅ تسجيل حجم الصورة المُولّدة
- ✅ تسجيل المزود الناجح
- ✅ تسجيل أسباب الفشل بوضوح

---

## الاختبار 🧪

```bash
# اختبار توليد الصور
curl -X POST https://nopoh55678.pythonanywhere.com/api/image/test \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A beautiful sunset over mountains"}'

# اختبار الـ overlay
curl -X POST https://nopoh55678.pythonanywhere.com/api/image/test-overlay \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Educational scene",
    "post_content": "اكتشف أسرارًا تعليمية ستغير طريقة تفكيرك!",
    "idea": "نصائح تعليمية"
  }'
```

---

## الخلاصة 📝

المشاكل الرئيسية:
1. ❌ Cloudinary يرفض صور تالفة/فارغة
2. ❌ Google Imagen 4.0 غير مستقر (استخدم 3.0)
3. ❌ api.airforce محظور على PythonAnywhere
4. ⚠️ Overlay يفشل مع صور تالفة

الحلول:
1. ✅ فحص صحة الصور قبل كل خطوة
2. ✅ استخدام نماذج مستقرة فقط
3. ✅ تعطيل المزودين المحظورين
4. ✅ معالجة أخطاء قوية في كل مرحلة
