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
  8.  ⚡  Fal.ai FLUX.1 Schnell  (رخيص $0.003/صورة)
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
# Updated: Using stable 3.0 models instead of experimental 4.0

GEMINI_IMAGE_MODELS = [
    "gemini-1.5-flash",           # Stable and available
    "gemini-1.5-pro",             # Stable
    "imagen-3.0-generate-001",    # Stable (changed from 4.0)
    "imagen-3.0-fast-generate-001",
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
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": prompt,
        "parameters": {
            "num_inference_steps": 40,
            "guidance_scale": 7.5
        }
    }
    
    r = requests.post(
        f"https://api-inference.huggingface.co/models/{model}",
        headers=headers,
        json=payload,
        timeout=120,
    )
    if r.status_code == 503:
        logger.info("HF: model loading, retrying in 20s...")
        time.sleep(20)
        r = requests.post(
            f"https://api-inference.huggingface.co/models/{model}",
            headers=headers,
            json=payload,
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
    """
    Together AI image generation.
    Endpoint: POST https://api.together.xyz/v1/images/generations
    Free models: FLUX.1-schnell-Free, FLUX.1-schnell
    """
    import base64

    # Try free models in order
    models = [
        "black-forest-labs/FLUX.1-schnell-Free",
        "black-forest-labs/FLUX.1-schnell",
        "black-forest-labs/FLUX.1-dev",
    ]

    last_err = None
    for model in models:
        try:
            r = requests.post(
                "https://api.together.xyz/v1/images/generations",
                headers={"Authorization": f"Bearer {api_key}",
                         "Content-Type": "application/json"},
                json={
                    "model": model,
                    "prompt": prompt,
                    "width": min(width, 1440),
                    "height": min(height, 1440),
                    "steps": 4,
                    "n": 1,
                    "response_format": "b64_json",
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
        except Exception as e:
            last_err = e
            logger.warning(f"Together AI {model} failed: {e}")
            continue

    raise ValueError(f"Together AI: all models failed. Last: {last_err}")


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
    """Fal.ai — FLUX.1 Schnell (fastest, cheapest at $0.003/image)."""
    # Calculate image_size preset or custom dimensions
    ratio = width / height
    if 0.9 <= ratio <= 1.1:
        image_size = "square_hd"  # 1:1
    elif ratio > 1.7:
        image_size = "landscape_16_9"
    elif ratio > 1.2:
        image_size = "landscape_4_3"
    elif ratio < 0.6:
        image_size = "portrait_16_9"
    elif ratio < 0.85:
        image_size = "portrait_4_3"
    else:
        # Custom size
        image_size = {"width": min(width, 1440), "height": min(height, 1440)}
    
    r = requests.post(
        "https://fal.run/fal-ai/flux/schnell",
        headers={"Authorization": f"Key {api_key}", "Content-Type": "application/json"},
        json={
            "prompt": prompt,
            "image_size": image_size,
            "num_inference_steps": 4,
            "num_images": 1,
            "guidance_scale": 3.5,
            "enable_safety_checker": False,
            "output_format": "png",
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
# Image models المتاحة (من /v1/models — supports_images=true):

# نماذج الصور الأكثر استقراراً (بالترتيب)
AIRFORCE_IMAGE_MODELS_ORDERED = [
    "flux-2-klein-4b",   # partial_outage — أرخص وأسرع ($0.03/img)
    "flux-2-klein-9b",   # degraded — جودة أعلى ($0.05/img)
    "flux-2-dev",        # degraded — جودة عالية ($0.10/img)
    "special-berry",     # degraded — مجاني ($0)
    "dirtberry",         # degraded — مجاني ($0)
    "z-image",           # degraded ($0.10/img)
    "flux",              # /imagine2 legacy — بدون مفتاح
]


def generate_image_airforce(prompt: str, width=1024, height=1024,
                             model: str = "flux-2-klein-4b",
                             api_key: str = "") -> bytes:
    """
    api.airforce image generation via SSE streaming.
    Endpoint: POST /v1/images/generations  (SSE only — sse=true required)
    Legacy:   GET  /imagine2               (no key needed)
    """
    import json as _json

    if api_key and model != "flux":
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": f"{min(width, 1024)}x{min(height, 1024)}",
            "response_format": "url",
            "sse": True,   # required — API only supports SSE
        }
        with requests.post(
            "https://api.airforce/v1/images/generations",
            headers=headers, json=payload, stream=True, timeout=90,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                line_str = line.decode("utf-8") if isinstance(line, bytes) else line
                if line_str in ("data: [DONE]", "data: : keepalive", "data: "):
                    continue
                if line_str.startswith("data: "):
                    try:
                        chunk = _json.loads(line_str[6:])
                        img_url = (
                            chunk.get("url") or
                            (chunk.get("data") or [{}])[0].get("url", "")
                        )
                        if img_url:
                            # Skip anondrop.net URLs (blocked on PythonAnywhere)
                            if "anondrop.net" in img_url:
                                logger.warning(f"Skipping anondrop.net URL (blocked): {img_url}")
                                continue
                            
                            try:
                                img_r = requests.get(img_url, timeout=30)
                                img_r.raise_for_status()
                                return img_r.content
                            except Exception as e:
                                logger.warning(f"Failed to download from {img_url}: {e}")
                                continue
                        import base64
                        b64 = (
                            chunk.get("b64_json") or
                            (chunk.get("data") or [{}])[0].get("b64_json", "")
                        )
                        if b64:
                            return base64.b64decode(b64)
                    except (_json.JSONDecodeError, Exception):
                        continue
        raise ValueError(f"airforce {model}: no image found in SSE stream")

    else:
        # Legacy /imagine2 — no key needed
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
            raise ValueError(f"airforce /imagine2 returned JSON: {r.text[:200]}")
        return r.content

def _try_airforce(prompt: str, width: int, height: int) -> bytes | None:
    """Try api.airforce — tries best available model first."""
    # Skip on PythonAnywhere (anondrop.net is blocked)
    import os
    if os.environ.get("PYTHONANYWHERE_DOMAIN") or os.environ.get("PYTHONANYWHERE_SITE"):
        logger.info("Skipping api.airforce (running on PythonAnywhere - anondrop.net blocked)")
        return None
    
    api_key = _get_image_key("airforce")

    if api_key:
        # Get preferred model from Config, fallback to ordered list
        preferred = ""
        try:
            from database.models import Config
            preferred = Config.get("airforce_image_model", "")
        except Exception:
            pass

        # Build model list: preferred first, then rest
        models_to_try = list(AIRFORCE_IMAGE_MODELS_ORDERED[:-1])  # exclude "flux"
        if preferred and preferred in models_to_try:
            models_to_try.remove(preferred)
            models_to_try.insert(0, preferred)
        elif preferred and preferred not in models_to_try:
            models_to_try.insert(0, preferred)

        for model in models_to_try:
            try:
                result = generate_image_airforce(prompt, width, height, model, api_key)
                logger.info(f"✅ Image via api.airforce ({model})")
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
    Pollinations — gen.pollinations.ai endpoint with Bearer authentication.
    API key (sk_ or pk_) removes watermark and raises rate limit.
    Works without token as fallback.
    """
    encoded = quote(prompt)
    url = (
        f"https://gen.pollinations.ai/image/{encoded}"
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
    
    # Validate image bytes before upload
    if not image_bytes or len(image_bytes) < 100:
        raise ValueError("Image bytes are empty or too small")
    
    # Verify image integrity
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
        logger.info(f"Uploading valid image ({len(image_bytes)} bytes) to Cloudinary")
    except Exception as e:
        raise ValueError(f"Invalid image data: {e}")
    
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
      8.  ⚡  Fal.ai FLUX.1 Schnell           (رخيص $0.003/صورة)
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

    # Load image provider chain from Config (user-defined order)
    from services.key_rotator import get_image_chain
    img_chain = get_image_chain()

    # Map provider name → try function
    _providers = {
        "cloudflare":   lambda: generate_image_cloudflare(worker_url, enhanced, width, height) if worker_url else (_ for _ in ()).throw(ValueError("no worker_url")),
        "google_imagen": lambda: _try_gemini_image(enhanced, width, height),
        "ideogram":     lambda: _try_ideogram(enhanced, width, height),
        "openai_image": lambda: _try_openai_image(enhanced, width, height),
        "stability":    lambda: _try_stability(enhanced, width, height),
        "huggingface":  lambda: _try_huggingface(enhanced, width, height),
        "together":     lambda: _try_together(enhanced, width, height),
        "fal":          lambda: _try_fal(enhanced, width, height),
        "airforce":     lambda: _try_airforce(enhanced, width, height),
        "pollinations": lambda: generate_image_pollinations(enhanced, width=width, height=height, api_key=poll_key) if poll_key else None,
    }

    for provider_name in img_chain:
        if image_bytes:
            break
        fn = _providers.get(provider_name)
        if not fn:
            continue
        try:
            result = fn()
            if result:
                # Validate image before accepting it
                if len(result) < 100:
                    logger.warning(f"{provider_name} returned image too small ({len(result)} bytes)")
                    continue
                
                # Verify image integrity
                try:
                    from PIL import Image
                    img_test = Image.open(io.BytesIO(result))
                    img_test.verify()
                    image_bytes   = result
                    used_provider = provider_name
                    logger.info(f"✅ Image via {provider_name} ({len(result)} bytes)")
                except Exception as e:
                    logger.warning(f"{provider_name} returned invalid image: {e}")
                    continue
        except Exception as e:
            logger.warning(f"{provider_name} failed: {e}")

    # Always-on fallback: Pollinations anonymous (not in chain, guaranteed)
    if image_bytes is None:
        try:
            result = generate_image_pollinations(enhanced, width=width, height=height)
            if result and len(result) > 100:
                # Verify fallback image too
                try:
                    from PIL import Image
                    img_test = Image.open(io.BytesIO(result))
                    img_test.verify()
                    image_bytes   = result
                    used_provider = "pollinations_anon"
                    logger.info(f"✅ Image via Pollinations (anonymous fallback, {len(result)} bytes)")
                except Exception as e:
                    logger.error(f"Pollinations fallback returned invalid image: {e}")
                    raise RuntimeError("All image providers failed — even Pollinations fallback")
            else:
                raise RuntimeError("Pollinations fallback returned empty/small image")
        except Exception as e:
            logger.error(f"All image providers failed: {e}")
            raise RuntimeError(
                f"All image providers failed (chain: {img_chain}). Last error: {e}"
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
        "label": "Fal.ai (FLUX.1 Schnell)", "icon": "⚡", "free": False,
        "key_required": True, "pricing": "$0.003/صورة",
        "note": "رخيص جداً — أسرع نموذج FLUX — fal.ai/dashboard",
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
