import requests
import hashlib
import hmac
import time
import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


def generate_image_cloudflare(worker_url, prompt, width=1080, height=1350):
    """Generate image via Cloudflare Worker (Flux 2)."""
    params = urlencode({"prompt": prompt, "model": "flux2", "w": width, "h": height})
    url = f"{worker_url}/?{params}"
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    return r.content  # raw bytes


def generate_image_pollinations(prompt, model="flux", width=1080, height=1350, api_key=""):
    """Fallback: Pollinations image generation."""
    from urllib.parse import quote
    url = f"https://gen.pollinations.ai/image/{quote(prompt)}?model={model}&width={width}&height={height}&seed=0&enhance=false"
    if api_key:
        url += f"&key={api_key}"
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    return r.content


def upload_to_cloudinary(image_bytes, cloud_name, api_key, api_secret, folder="social_posts"):
    """Upload image bytes to Cloudinary and return secure_url."""
    import hashlib
    ts = int(time.time())
    params_to_sign = f"folder={folder}&timestamp={ts}"
    signature = hashlib.sha1((params_to_sign + api_secret).encode()).hexdigest()

    url = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"
    files = {"file": ("image.jpg", image_bytes, "image/jpeg")}
    data = {
        "api_key": api_key,
        "timestamp": ts,
        "folder": folder,
        "signature": signature,
    }
    r = requests.post(url, files=files, data=data, timeout=60)
    r.raise_for_status()
    resp = r.json()
    if "error" in resp:
        raise ValueError(f"Cloudinary error: {resp['error']['message']}")
    return resp.get("secure_url") or resp.get("url")


def overlay_frame_cloudinary(base_url, frame_url, cloud_name, api_key, api_secret,
                              width=1080, height=1350, folder="social_posts"):
    """
    Download base image, overlay frame, re-upload to Cloudinary.
    Returns final secure_url.
    """
    # Download base image
    r = requests.get(base_url, timeout=60)
    r.raise_for_status()
    base_bytes = r.content

    # Download frame
    rf = requests.get(frame_url, timeout=60)
    rf.raise_for_status()
    frame_bytes = rf.content

    # Composite with Pillow
    from PIL import Image
    import io
    base_img = Image.open(io.BytesIO(base_bytes)).convert("RGBA").resize((width, height))
    frame_img = Image.open(io.BytesIO(frame_bytes)).convert("RGBA").resize((width, height))
    base_img.paste(frame_img, (0, 0), frame_img)

    output = io.BytesIO()
    base_img.convert("RGB").save(output, format="JPEG", quality=92)
    final_bytes = output.getvalue()

    return upload_to_cloudinary(final_bytes, cloud_name, api_key, api_secret, folder)


def process_image(post_data, cfg):
    """
    Full image pipeline:
    1. Generate via Cloudflare Worker (fallback: Pollinations)
    2. Overlay frame
    3. Return final Cloudinary URL
    """
    prompt = post_data.get("image_prompt", "")
    width = int(cfg.get("image_width", 1080))
    height = int(cfg.get("image_height", 1350))
    worker_url = cfg.get("worker_url", "")
    poll_key = cfg.get("pollinations_key", "")
    cloud_name = cfg.get("cloudinary_cloud_name", "")
    api_key = cfg.get("cloudinary_api_key", "")
    api_secret = cfg.get("cloudinary_api_secret", "")
    frame_url = cfg.get("frame_url", "")

    # Step 1: Generate
    image_bytes = None
    if worker_url:
        try:
            image_bytes = generate_image_cloudflare(worker_url, prompt, width, height)
            logger.info("Image generated via Cloudflare Worker")
        except Exception as e:
            logger.warning(f"Cloudflare Worker failed: {e}, trying Pollinations")

    if image_bytes is None:
        image_bytes = generate_image_pollinations(prompt, width=width, height=height, api_key=poll_key)
        logger.info("Image generated via Pollinations")

    # Step 2: Upload base image
    base_url = upload_to_cloudinary(image_bytes, cloud_name, api_key, api_secret)
    logger.info(f"Base image uploaded: {base_url}")

    # Step 3: Overlay frame if configured
    if frame_url and frame_url != "YOUR_FRAME_IMAGE_URL":
        try:
            final_url = overlay_frame_cloudinary(base_url, frame_url, cloud_name, api_key, api_secret, width, height)
            logger.info(f"Frame overlaid: {final_url}")
            return final_url
        except Exception as e:
            logger.warning(f"Frame overlay failed: {e}, using base image")

    return base_url
