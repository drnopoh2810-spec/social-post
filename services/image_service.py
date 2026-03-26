"""
Image Service — Multi-Provider Pipeline
=========================================
Flow (first success wins):
  1.  ☁️  Cloudflare Worker      (primary — مجاني)
  2.  🔵  Google Imagen 4        (مجاني بمفتاح Gemini)
  3.  🎨  Ideogram v3            (مدفوع — أفضل نص عربي)
  4.  🟢  OpenAI gpt-image-1     (مدفوع — جودة عالية)
  5.  🔷  Stability AI SD 3.5    (مدفوع — مرن)
  6.  🤗  HuggingFace Flux       (مجاني بمفتاح)
  7.  🔗  Together AI Flux Free  (مجاني بمفتاح)
  8.  ⚡  Fal.ai Flux Schnell    (مجاني محدود)
  9.  🛩️  api.airforce           (مجاني بدون مفتاح)
  10. 🌸  Pollinations auth      (مجاني بـ token)
  11. 🌸  Pollinations anon      (last fallback — دايماً يشتغل)
  ↓
  Upload to Cloudinary → Overlay Frame
"""

import requests
import time
import logging
import io
from urllib.parse import quote

logger = logging.getLogger(__name__)

# ── Prompt quality enhancer ───────────────────────────────────────────────────

_QUALITY_SUFFIX = (
    ", professional editorial photography, Kodak Portra 400, "
    "sharp focus, high detail, 8k resolution, clean composition"
)
_NEGATIVE_PROMPT = (
    "blurry, low quality, pixelated, watermark, text overlay, logo, "
    "distorted, ugly, bad anatomy, extra limbs, duplicate"
)


def _enhance_prompt(prompt: str) -> str:
    if not prompt:
        return prompt
    p = prompt.strip()
    if "kodak" in p.lower() or "8k" in p.lower():
        return p
    return p + _QUALITY_SUFFIX


# ── Key helper ────────────────────────────────────────────────────────────────

def _get_image_key(provider: str) -> str:
    try:
        from database.models import AIProviderKey, Config
        key = AIProviderKey.query.filter_by(
            provider=provider, is_active=True, is_exhausted=False
        ).order_by(AIProviderKey.priority.asc()).first()
        if key:
            return key.key_value
        return Config.get(f"{provider}_api_key", "")
    except Exception:
        return ""


# ── Provider 1: Cloudflare Worker ────────────────────────────────────────────

def generate_image_cloudflare(worker_url, prompt, width=1080, height=1350):
    """Generate via Cloudflare Worker (Flux 2). ORIGINAL — unchanged."""
    from urllib.parse import urlencode
    params = urlencode({"prompt": prompt, "model": "flux2", "w": width, "h": height})
    r = requests.get(f"{worker_url}/?{params}", timeout=120)
    r.raise_for_status()
    return r.content


# ── Provider 2: Google Imagen 4 / Gemini Image ────────────────────────────────
# مجاني بنفس مفتاح Gemini — يدعم النص العربي

GEMINI_IMAGE_MODELS = [
    "imagen-4.0-generate-001",
    "imagen-4.0-fast-generate-001",
    "gemini-2.0-flash-exp",
]

_ASPECT_MAP = {
    (1, 1): "1:1", (3, 4): "3:4", (4, 3): "4:3",
    (9, 16): "9:16", (16, 9): "16:9",
}


def _get_aspect_ratio(width: int, height: int) -> str:
    ratio = width / height
    return _ASPECT_MAP[min(_ASPECT_MAP, key=lambda r: abs(r[0] / r[1] - ratio))]


def generate_image_gemini(api_key: str, prompt: str,
                           width=1080, height=1350,
                           model: str = "imagen-4.0-generate-001") -> bytes:
    """Google Imagen 4 / Gemini Image — free with Gemini API key."""
    import base64
    aspect = _get_aspect_ratio(width, height)

    if "gemini" in model:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model}:generateContent?key={api_key}")
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
        }
        r = requests.post(url, json=payload, timeout=120)
        r.raise_for_status()
        for part in r.json().get("candidates", [{}])[0].get("content", {}).get("parts", []):
            if "inlineData" in part:
                return base64.b64decode(part["inlineData"]["data"])
        raise ValueError("Gemini image: no image in response")
    else:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model}:predict?key={api_key}")
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": 1, "aspectRatio": aspect},
        }
        r = requests.post(url, json=payload, timeout=120)
        r.raise_for_status()
        preds = r.json().get("predictions", [])
        if not preds:
            raise ValueError(f"Imagen: no predictions: {r.text[:200]}")
        b64 = preds[0].get("bytesBase64Encoded", "")
        if not b64:
            raise ValueError("Imagen: no image bytes")
        return base64.b64decode(b64)


def _try_gemini_image(prompt: str, width: int, height: int) -> bytes | None:
    api_key = _get_image_key("gemini_image")
    if not api_key:
        try:
            from database.models import Config
            api_key = Config.get("gemini_api_key", "")
        except Exception:
            pass
    if not api_key:
        return None
    for model in GEMINI_IMAGE_MODELS:
        try:
            result = generate_image_gemini(api_key, prompt, width, height, model)
            logger.info(f"✅ Image via Google {model}")
            return result
        except Exception as e:
            logger.warning(f"Google {model} failed: {e}")
    return None


# ── Provider 3: Ideogram v3 — أفضل نص عربي ───────────────────────────────────

_IDEOGRAM_ASPECT = {
    (1, 1): "ASPECT_1_1", (4, 5): "ASPECT_4_5", (9, 16): "ASPECT_9_16",
    (16, 9): "ASPECT_16_9", (3, 4): "ASPECT_3_4", (4, 3): "ASPECT_4_3",
}


def _ideogram_aspect(width: int, height: int) -> str:
    ratio = width / height
    return _IDEOGRAM_ASPECT[min(_IDEOGRAM_ASPECT, key=lambda r: abs(r[0] / r[1] - ratio))]


def generate_image_ideogram(api_key: str, prompt: str,
                             width=1080, height=1350) -> bytes:
    """Ideogram v3 — best for Arabic text in images. ~$0.08/image."""
    r = requests.post(
        "https://api.ideogram.ai/v1/ideogram-v3/generate",
        headers={"Api-Key": api_key, "Content-Type": "application/json"},
        json={
            "prompt": prompt,
            "aspect_ratio": _ideogram_aspect(width, height),
            "style_type": "REALISTIC",
            "magic_prompt": "OFF",
            "num_images": 1,
        },
        timeout=120,
    )
    r.raise_for_status()
    img_url = r.json()["data"][0].get("url", "")
    if not img_url:
        raise ValueError(f"Ideogram: no URL: {r.text[:200]}")
    return requests.get(img_url, timeout=60).content


def _try_ideogram(prompt: str, width: int, height: int) -> bytes | None:
    api_key = _get_image_key("ideogram")
    if not api_key:
        return None
    try:
        result = generate_image_ideogram(api_key, prompt, width, height)
        logger.info("✅ Image via Ideogram v3")
        return result
    except Exception as e:
        logger.warning(f"Ideogram failed: {e}")
        return None


# ── Provider 4: OpenAI gpt-image-1 / DALL-E 3 ────────────────────────────────

def generate_image_openai(api_key: str, prompt: str,
                           width=1080, height=1350,
                           model: str = "gpt-image-1") -> bytes:
    """OpenAI Images API. ~$0.04-0.08/image."""
    import base64
    if model == "dall-e-3":
        size = "1024x1792" if height > width else ("1792x1024" if width > height else "1024x1024")
    else:
        size = "1024x1536" if height > width else ("1536x1024" if width > height else "1024x1024")

    payload = {"model": model, "prompt": prompt, "n": 1,
               "size": size, "response_format": "b64_json"}
    if model == "dall-e-3":
        payload.update({"quality": "hd", "style": "natural"})

    r = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload, timeout=120,
    )
    r.raise_for_status()
    data = r.json()["data"][0]
    if data.get("b64_json"):
        return base64.b64decode(data["b64_json"])
    return requests.get(data.get("url", ""), timeout=60).content


def _try_openai_image(prompt: str, width: int, height: int) -> bytes | None:
    api_key = _get_image_key("openai_image")
    if not api_key:
        try:
            from database.models import Config
            api_key = Config.get("openai_api_key", "")
        except Exception:
            pass
    if not api_key:
        return None
    for model in ["gpt-image-1", "dall-e-3"]:
        try:
            result = generate_image_openai(api_key, prompt, width, height, model)
            logger.info(f"✅ Image via OpenAI {model}")
            return result
        except Exception as e:
            logger.warning(f"OpenAI {model} failed: {e}")
    return None


# ── Provider 5: Stability AI SD 3.5 ──────────────────────────────────────────

def generate_image_stability(api_key: str, prompt: str,
                              width=1024, height=1344,
                              model: str = "sd3.5-large") -> bytes:
    """Stability AI. ~$0.065/image."""
    w = max(min(int(width / 64) * 64, 1536), 512)
    h = max(min(int(height / 64) * 64, 1536), 512)
    r = requests.post(
        "https://api.stability.ai/v2beta/stable-image/generate/sd3",
        headers={"Authorization": f"Bearer {api_key}", "Accept": "image/*"},
        files={"none": ""},
        data={"prompt": prompt, "model": model,
              "width": str(w), "height": str(h),
              "output_format": "jpeg", "negative_prompt": _NEGATIVE_PROMPT},
        timeout=120,
    )
    if not r.ok:
        raise ValueError(f"Stability {r.status_code}: {r.text[:200]}")
    return r.content


def _try_stability(prompt: str, width: int, height: int) -> bytes | None:
    api_key = _get_image_key("stability")
    if not api_key:
        return None
    for model in ["sd3.5-large", "sd3.5-medium"]:
        try:
            result = generate_image_stability(api_key, prompt, width, height, model)
            logger.info(f"✅ Image via Stability AI {model}")
            return result
        except Exception as e:
            logger.warning(f"Stability {model} failed: {e}")
    return None


# ── Provider 6: HuggingFace Inference API ────────────────────────────────────

HF_MODELS = [
    "black-forest-labs/FLUX.1-schnell",
    "black-forest-labs/FLUX.1-dev",
    "stabilityai/stable-diffusion-xl-base-1.0",
]


def generate_image_huggingface(api_key: str, prompt: str,
                                width=1080, height=1350,
                                model: str = HF_MODELS[0]) -> bytes:
    """HuggingFace Inference API — free tier."""
    r = requests.post(
        f"https://api-inference.huggingface.co/models/{model}",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"inputs": prompt, "parameters": {
            "width": min(width, 1024), "height": min(height, 1024),
            "num_inference_steps": 4, "guidance_scale": 0.0,
        }},
        timeout=120,
    )
    if r.status_code == 503:
        logger.info("HF: model loading, retrying in 20s...")
        time.sleep(20)
        r = requests.post(
            f"https://api-inference.huggingface.co/models/{model}",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"inputs": prompt, "parameters": {
                "width": min(width, 1024), "height": min(height, 1024),
                "num_inference_steps": 4, "guidance_scale": 0.0,
            }},
            timeout=120,
        )
    r.raise_for_status()
    if r.headers.get("content-type", "").startswith("application/json"):
        raise ValueError(f"HF returned JSON: {r.text[:200]}")
    return r.content


def _try_huggingface(prompt: str, width: int, height: int) -> bytes | None:
    api_key = _get_image_key("huggingface")
    if not api_key:
        return None
    for model in HF_MODELS[:2]:
        try:
            result = generate_image_huggingface(api_key, prompt, width, height, model)
            logger.info(f"✅ Image via HuggingFace {model}")
            return result
        except Exception as e:
            logger.warning(f"HF {model} failed: {e}")
    return None


# ── Provider 7: Together AI ───────────────────────────────────────────────────

def generate_image_together(api_key: str, prompt: str,
                             width=1024, height=1024) -> bytes:
    """Together AI — Flux.1 Schnell Free."""
    import base64
    r = requests.post(
        "https://api.together.xyz/v1/images/generations",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "black-forest-labs/FLUX.1-schnell-Free",
            "prompt": prompt,
            "width": min(width, 1440), "height": min(height, 1440),
            "steps": 4, "n": 1, "response_format": "b64_json",
        },
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()["data"][0]
    if data.get("b64_json"):
        return base64.b64decode(data["b64_json"])
    img_url = data.get("url", "")
    if img_url:
        return requests.get(img_url, timeout=60).content
    raise ValueError("Together AI: no image in response")


def _try_together(prompt: str, width: int, height: int) -> bytes | None:
    api_key = _get_image_key("together")
    if not api_key:
        return None
    try:
        result = generate_image_together(api_key, prompt, width, height)
        logger.info("✅ Image via Together AI")
        return result
    except Exception as e:
        logger.warning(f"Together AI failed: {e}")
        return None


# ── Provider 8: Fal.ai ────────────────────────────────────────────────────────

def generate_image_fal(api_key: str, prompt: str,
                        width=1024, height=1360) -> bytes:
    """Fal.ai — Flux Schnell. Free tier available."""
    r = requests.post(
        "https://fal.run/fal-ai/flux/schnell",
        headers={"Authorization": f"Key {api_key}", "Content-Type": "application/json"},
        json={
            "prompt": prompt,
            "image_size": {"width": min(width, 1440), "height": min(height, 1440)},
            "num_inference_steps": 4, "num_images": 1,
            "enable_safety_checker": False,
        },
        timeout=120,
    )
    r.raise_for_status()
    img_url = r.json().get("images", [{}])[0].get("url", "")
    if not img_url:
        raise ValueError(f"Fal.ai: no URL: {r.text[:200]}")
    return requests.get(img_url, timeout=60).content


def _try_fal(prompt: str, width: int, height: int) -> bytes | None:
    api_key = _get_image_key("fal")
    if not api_key:
        return None
    try:
        result = generate_image_fal(api_key, prompt, width, height)
        logger.info("✅ Image via Fal.ai")
        return result
    except Exception as e:
        logger.warning(f"Fal.ai failed: {e}")
        return None


# ── Provider 9: api.airforce ─────────────────────────────────────────────────
# OpenAI-compatible API — يدعم chat + image generation
# مجاني بمفتاح (بعض النماذج مجانية price=0)
# الـ endpoint: https://api.airforce/v1/

# نماذج الصور المتاحة (supports_images=true)
AIRFORCE_IMAGE_MODELS = [
    "flux",           # الأصلي عبر /imagine2
    "dirtberry",      # degraded لكن مجاني
    "special-berry",  # degraded لكن مجاني
    "z-image",        # degraded
]

# نماذج الـ chat المجانية (pricepermilliontokens=0, operational)
AIRFORCE_FREE_CHAT_MODELS = [
    "gemma3-270m:free",    # Google — سريع جداً
    "moirai-agent",        # Salesforce — مجاني
    "translategemma-27b",  # Google — مجاني
    "teuken-7b",           # OpenGPT-X — مجاني
]

# نماذج الـ chat الـ operational (مدفوعة لكن بأسعار منخفضة)
AIRFORCE_CHAT_MODELS = [
    "deepseek-v3-0324",    # DeepSeek — operational
    "deepseek-r1",         # DeepSeek — operational
    "gemini-2.5-flash",    # Google — operational
    "claude-sonnet-4.6",   # Anthropic — operational
    "gpt-5-nano",          # OpenAI — operational
    "gemma3-270m:free",    # مجاني
]


def generate_image_airforce(prompt: str, width=1024, height=1024,
                             model: str = "flux",
                             api_key: str = "") -> bytes:
    """
    api.airforce image generation.
    - /imagine2 endpoint: بدون مفتاح (Flux)
    - /v1/images/generations: بـ Bearer token (OpenAI-compatible)
    """
    if api_key and model not in ("flux",):
        # OpenAI-compatible images endpoint
        r = requests.post(
            "https://api.airforce/v1/images/generations",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={
                "model": model,
                "prompt": prompt,
                "n": 1,
                "size": f"{min(width, 1024)}x{min(height, 1024)}",
            },
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        img_url = data.get("data", [{}])[0].get("url", "")
        if img_url:
            return requests.get(img_url, timeout=60).content
        import base64
        b64 = data.get("data", [{}])[0].get("b64_json", "")
        if b64:
            return base64.b64decode(b64)
        raise ValueError(f"airforce image: no image in response: {str(data)[:200]}")
    else:
        # Legacy /imagine2 endpoint — no key needed
        url = (
            f"https://api.airforce/imagine2"
            f"?prompt={quote(prompt)}"
            f"&model=flux"
            f"&width={min(width, 1024)}&height={min(height, 1024)}"
            f"&seed=0"
        )
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        if r.headers.get("content-type", "").startswith("application/json"):
            raise ValueError(f"airforce JSON: {r.text[:200]}")
        return r.content


def _try_airforce(prompt: str, width: int, height: int) -> bytes | None:
    """Try api.airforce — tries authenticated first, then anonymous."""
    api_key = _get_image_key("airforce")

    # Try with key first (better models)
    if api_key:
        for model in ["dirtberry", "special-berry", "z-image"]:
            try:
                result = generate_image_airforce(prompt, width, height, model, api_key)
                logger.info(f"✅ Image via api.airforce ({model}, authenticated)")
                return result
            except Exception as e:
                logger.warning(f"api.airforce {model} failed: {e}")

    # Fallback: anonymous /imagine2
    try:
        result = generate_image_airforce(prompt, width, height, "flux", "")
        logger.info("✅ Image via api.airforce (anonymous flux)")
        return result
    except Exception as e:
        logger.warning(f"api.airforce anonymous failed: {e}")
        return None


# ── Provider 10+11: Pollinations ─────────────────────────────────────────────

POLLINATIONS_MODELS = ["flux", "turbo", "gptimage", "kontext"]


def generate_image_pollinations(prompt, model="flux", width=1080, height=1350,
                                 api_key="") -> bytes:
    """
    Pollinations — new endpoint image.pollinations.ai (2025+).
    Bearer token removes watermark and raises rate limit.
    Works without token as last fallback.
    """
    encoded = quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?model={model}&width={width}&height={height}"
        f"&seed=0&nologo=true&private=true&enhance=false"
    )
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    r = requests.get(url, headers=headers, timeout=120)
    r.raise_for_status()
    return r.content


# ── Cloudinary helpers ────────────────────────────────────────────────────────

def upload_to_cloudinary(image_bytes, cloud_name, api_key, api_secret,
                          folder="social_posts"):
    """Upload image bytes to Cloudinary. Returns (secure_url, public_id)."""
    import hashlib
    ts = int(time.time())
    sig = hashlib.sha1(
        (f"folder={folder}&timestamp={ts}" + api_secret).encode()
    ).hexdigest()
    r = requests.post(
        f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload",
        files={"file": ("image.jpg", image_bytes, "image/jpeg")},
        data={"api_key": api_key, "timestamp": ts,
              "folder": folder, "signature": sig},
        timeout=60,
    )
    r.raise_for_status()
    resp = r.json()
    if "error" in resp:
        raise ValueError(f"Cloudinary: {resp['error']['message']}")
    url       = resp.get("secure_url") or resp.get("url")
    public_id = resp.get("public_id", "")
    return url, public_id


def delete_from_cloudinary(public_id: str, cloud_name: str,
                            api_key: str, api_secret: str) -> bool:
    """
    Delete an image from Cloudinary by public_id.
    Called after successful publishing to free up storage.
    Returns True on success.
    """
    if not public_id or not cloud_name:
        return False
    try:
        import hashlib
        ts  = int(time.time())
        sig = hashlib.sha1(
            (f"public_id={public_id}&timestamp={ts}" + api_secret).encode()
        ).hexdigest()
        r = requests.post(
            f"https://api.cloudinary.com/v1_1/{cloud_name}/image/destroy",
            data={"public_id": public_id, "api_key": api_key,
                  "timestamp": ts, "signature": sig},
            timeout=30,
        )
        result = r.json().get("result", "")
        if result == "ok":
            logger.info(f"Cloudinary: deleted {public_id}")
            return True
        logger.warning(f"Cloudinary delete returned: {result} for {public_id}")
        return False
    except Exception as e:
        logger.warning(f"Cloudinary delete failed for {public_id}: {e}")
        return False


def overlay_frame_cloudinary(base_url, frame_url, cloud_name, api_key, api_secret,
                              width=1080, height=1350, folder="social_posts"):
    """Overlay frame on image and re-upload. Returns (url, public_id)."""
    from PIL import Image
    base_bytes  = requests.get(base_url, timeout=60).content
    frame_bytes = requests.get(frame_url, timeout=60).content
    base_img    = Image.open(io.BytesIO(base_bytes)).convert("RGBA").resize((width, height))
    frame_img   = Image.open(io.BytesIO(frame_bytes)).convert("RGBA").resize((width, height))
    base_img.paste(frame_img, (0, 0), frame_img)
    out = io.BytesIO()
    base_img.convert("RGB").save(out, format="JPEG", quality=92)
    return upload_to_cloudinary(out.getvalue(), cloud_name, api_key, api_secret, folder)


# ── Main pipeline ─────────────────────────────────────────────────────────────

def process_image(post_data, cfg):
    """
    Full image pipeline.
    Generation order (first success wins):
      1.  ☁️  Cloudflare Worker
      2.  🔵  Google Imagen 4 / Gemini Image  (مجاني بمفتاح Gemini)
      3.  🎨  Ideogram v3                     (مدفوع — أفضل نص عربي)
      4.  🟢  OpenAI gpt-image-1              (مدفوع)
      5.  🔷  Stability AI SD 3.5             (مدفوع)
      6.  🤗  HuggingFace Flux               (مجاني بمفتاح)
      7.  🔗  Together AI Flux Free           (مجاني بمفتاح)
      8.  ⚡  Fal.ai Flux Schnell             (مجاني محدود)
      9.  🛩️  api.airforce                   (مجاني بدون مفتاح)
      10. 🌸  Pollinations (authenticated)    (مجاني بـ token)
      11. 🌸  Pollinations (anonymous)        (last fallback)
    Then: Upload to Cloudinary → Overlay Frame
    """
    prompt     = post_data.get("image_prompt", "")
    width      = int(cfg.get("image_width", 1080))
    height     = int(cfg.get("image_height", 1350))
    worker_url = cfg.get("worker_url", "")
    poll_key   = cfg.get("pollinations_key", "")
    cloud_name = cfg.get("cloudinary_cloud_name", "")
    api_key    = cfg.get("cloudinary_api_key", "")
    api_secret = cfg.get("cloudinary_api_secret", "")
    frame_url  = cfg.get("frame_url", "")

    enhanced = _enhance_prompt(prompt)
    image_bytes   = None
    used_provider = ""

    # 1. Cloudflare Worker
    if worker_url:
        try:
            image_bytes   = generate_image_cloudflare(worker_url, enhanced, width, height)
            used_provider = "cloudflare"
            logger.info("✅ Image via Cloudflare Worker")
        except Exception as e:
            logger.warning(f"Cloudflare failed: {e}")

    # 2. Google Imagen 4 / Gemini Image
    if image_bytes is None:
        image_bytes = _try_gemini_image(enhanced, width, height)
        if image_bytes: used_provider = "google_imagen"

    # 3. Ideogram v3
    if image_bytes is None:
        image_bytes = _try_ideogram(enhanced, width, height)
        if image_bytes: used_provider = "ideogram"

    # 4. OpenAI gpt-image-1
    if image_bytes is None:
        image_bytes = _try_openai_image(enhanced, width, height)
        if image_bytes: used_provider = "openai_image"

    # 5. Stability AI
    if image_bytes is None:
        image_bytes = _try_stability(enhanced, width, height)
        if image_bytes: used_provider = "stability"

    # 6. HuggingFace
    if image_bytes is None:
        image_bytes = _try_huggingface(enhanced, width, height)
        if image_bytes: used_provider = "huggingface"

    # 7. Together AI
    if image_bytes is None:
        image_bytes = _try_together(enhanced, width, height)
        if image_bytes: used_provider = "together"

    # 8. Fal.ai
    if image_bytes is None:
        image_bytes = _try_fal(enhanced, width, height)
        if image_bytes: used_provider = "fal"

    # 9. api.airforce (no key needed)
    if image_bytes is None:
        image_bytes = _try_airforce(enhanced, width, height)
        if image_bytes: used_provider = "airforce"

    # 10. Pollinations authenticated
    if image_bytes is None and poll_key:
        try:
            image_bytes   = generate_image_pollinations(enhanced, width=width,
                                                         height=height, api_key=poll_key)
            used_provider = "pollinations_auth"
            logger.info("✅ Image via Pollinations (authenticated)")
        except Exception as e:
            logger.warning(f"Pollinations auth failed: {e}")

    # 11. Pollinations anonymous — last fallback
    if image_bytes is None:
        try:
            image_bytes   = generate_image_pollinations(enhanced, width=width, height=height)
            used_provider = "pollinations_anon"
            logger.info("✅ Image via Pollinations (anonymous)")
        except Exception as e:
            logger.error(f"All providers failed: {e}")
            raise RuntimeError(
                "All image providers failed. "
                "Tried: cloudflare→imagen→ideogram→openai→stability→"
                "huggingface→together→fal→airforce→pollinations. "
                f"Last error: {e}"
            )

    logger.info(f"Image provider used: {used_provider}")

    # Upload to Cloudinary
    if not cloud_name or not api_key or not api_secret:
        raise RuntimeError(
            "Cloudinary not configured — add cloudinary_cloud_name, "
            "cloudinary_api_key, cloudinary_api_secret in /config"
        )

    base_url, base_pid = upload_to_cloudinary(image_bytes, cloud_name, api_key, api_secret)
    logger.info(f"Uploaded: {base_url}")

    # Track all intermediate public_ids for cleanup
    intermediate_pids = []

    # Overlay frame
    if frame_url and frame_url not in ("", "YOUR_FRAME_IMAGE_URL"):
        try:
            framed_url, framed_pid = overlay_frame_cloudinary(
                base_url, frame_url, cloud_name, api_key, api_secret, width, height
            )
            logger.info(f"Frame overlaid: {framed_url}")
            # Delete the base (pre-frame) image — no longer needed
            if base_pid:
                intermediate_pids.append(base_pid)
            base_url = framed_url
            base_pid = framed_pid
        except Exception as e:
            logger.warning(f"Frame overlay failed: {e}")

    # Text overlay — Arabic title/teaser on image
    try:
        from services.overlay_service import process_overlay
        post_content = post_data.get("post_content", "")
        idea         = post_data.get("idea", "")
        if post_content or idea:
            img_bytes = requests.get(base_url, timeout=30).content
            overlaid  = process_overlay(img_bytes, post_content, idea)
            if overlaid != img_bytes:
                overlay_url, overlay_pid = upload_to_cloudinary(
                    overlaid, cloud_name, api_key, api_secret,
                    folder="social_posts_overlay"
                )
                logger.info(f"Text overlay applied: {overlay_url}")
                # Delete the pre-text-overlay image
                if base_pid:
                    intermediate_pids.append(base_pid)
                base_url = overlay_url
                base_pid = overlay_pid
    except Exception as e:
        logger.warning(f"Text overlay failed (using base image): {e}")

    # Clean up intermediate images (frame-only, pre-overlay versions)
    for pid in intermediate_pids:
        delete_from_cloudinary(pid, cloud_name, api_key, api_secret)

    # Return final URL and public_id so workflow can delete after publishing
    return base_url, base_pid


# ── Provider info (for UI) ────────────────────────────────────────────────────

IMAGE_PROVIDERS_INFO = {
    "cloudflare": {
        "label": "Cloudflare Worker (Flux 2)", "icon": "☁️", "free": True,
        "key_required": False, "config_key": "worker_url",
        "note": "مجاني — يحتاج WORKER_URL فقط",
    },
    "gemini_image": {
        "label": "Google Imagen 4 / Gemini Image ⭐", "icon": "🔵", "free": True,
        "key_required": True, "models": GEMINI_IMAGE_MODELS,
        "note": "مجاني بنفس مفتاح Gemini — يدعم النص العربي — ai.google.dev",
    },
    "ideogram": {
        "label": "Ideogram v3 (أفضل نص عربي)", "icon": "🎨", "free": False,
        "key_required": True, "pricing": "$0.08/صورة",
        "note": "مدفوع — الأفضل في النص العربي والتصاميم — developer.ideogram.ai",
    },
    "openai_image": {
        "label": "OpenAI gpt-image-1 / DALL-E 3", "icon": "🟢", "free": False,
        "key_required": True, "pricing": "$0.04-0.08/صورة",
        "note": "مدفوع — جودة عالية — platform.openai.com/api-keys",
    },
    "stability": {
        "label": "Stability AI (SD 3.5 Large)", "icon": "🔷", "free": False,
        "key_required": True, "pricing": "$0.065/صورة",
        "note": "مدفوع — مرن وبأسعار معقولة — platform.stability.ai",
    },
    "huggingface": {
        "label": "HuggingFace Inference API", "icon": "🤗", "free": True,
        "key_required": True, "models": HF_MODELS,
        "note": "مجاني — hf.co/settings/tokens",
    },
    "together": {
        "label": "Together AI (Flux.1 Schnell Free)", "icon": "🔗", "free": True,
        "key_required": True,
        "note": "مجاني — api.together.xyz",
    },
    "fal": {
        "label": "Fal.ai (Flux Schnell)", "icon": "⚡", "free": True,
        "key_required": True,
        "note": "مجاني محدود — fal.ai/dashboard",
    },
    "airforce": {
        "label": "api.airforce (بدون مفتاح)", "icon": "🛩️", "free": True,
        "key_required": False,
        "note": "مجاني تماماً بدون مفتاح — proxy لـ Flux",
    },
    "pollinations": {
        "label": "Pollinations (image.pollinations.ai)", "icon": "🌸", "free": True,
        "key_required": False, "config_key": "pollinations_key",
        "models": POLLINATIONS_MODELS,
        "note": "مجاني — سجّل على auth.pollinations.ai للـ token (بدون watermark)",
    },
}
