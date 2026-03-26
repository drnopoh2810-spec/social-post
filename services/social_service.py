"""
Social media publishing service — Production-ready integrations.

Facebook  : Graph API v20.0 — صورة + نص كامل
Instagram : Graph API v20.0 — صورة + كابشن (2200 حرف) | text-only = skip
Twitter/X : Tweepy OAuth1   — صورة + نص (270 حرف)
Threads   : Threads API v1.0 — صورة + نص | نص فقط
LinkedIn  : UGC Posts API   — صورة (article) + نص | نص فقط

ملاحظة Instagram:
  - يدعم فقط: IMAGE مع caption
  - لا يدعم: text-only على الـ feed عبر API
  - الـ caption يُقطع على 2200 حرف (حد Instagram)
  - الصورة يجب أن تكون على URL عام (Cloudinary)
  - يتطلب حساب Business أو Creator
"""
import requests
import time
import logging
import io

logger = logging.getLogger(__name__)

GRAPH_VER = "v20.0"
IG_CAPTION_LIMIT = 2200   # حد Instagram الرسمي للكابشن


# ─── Facebook ─────────────────────────────────────────────────────────────────

def post_facebook_image(page_id: str, access_token: str, image_url: str, caption: str) -> str:
    """نشر صورة مع كابشن على صفحة Facebook."""
    r = requests.post(
        f"https://graph.facebook.com/{GRAPH_VER}/{page_id}/photos",
        data={"url": image_url, "caption": caption, "access_token": access_token},
        timeout=30,
    )
    _raise_with_detail(r, "Facebook image post")
    return r.json().get("post_id") or r.json().get("id", "")


def post_facebook_text(page_id: str, access_token: str, message: str) -> str:
    """نشر منشور نصي على صفحة Facebook."""
    r = requests.post(
        f"https://graph.facebook.com/{GRAPH_VER}/{page_id}/feed",
        data={"message": message, "access_token": access_token},
        timeout=30,
    )
    _raise_with_detail(r, "Facebook text post")
    return r.json().get("id", "")


# ─── Instagram ────────────────────────────────────────────────────────────────

def post_instagram_image(ig_user_id: str, access_token: str, image_url: str, caption: str) -> str:
    """
    نشر صورة + كابشن على Instagram Business/Creator.

    المتطلبات:
    - حساب Instagram Business أو Creator (مش Personal)
    - الصورة على URL عام يمكن لـ Facebook servers الوصول إليه (Cloudinary ✅)
    - الـ caption بحد أقصى 2200 حرف
    - نسبة الصورة: 4:5 (1080×1350) أو 1:1 (1080×1080) أو 1.91:1

    Flow:
    1. إنشاء media container مع image_url + caption
    2. انتظار processing (polling حتى FINISHED)
    3. نشر الـ container
    """
    # قطع الكابشن على الحد الرسمي
    caption_trimmed = caption[:IG_CAPTION_LIMIT] if caption else ""

    # Step 1: Create media container
    r = requests.post(
        f"https://graph.facebook.com/{GRAPH_VER}/{ig_user_id}/media",
        json={
            "image_url": image_url,
            "caption": caption_trimmed,
            "access_token": access_token,
        },
        timeout=30,
    )
    _raise_with_detail(r, "Instagram create container")
    container_id = r.json().get("id")
    if not container_id:
        raise ValueError(f"Instagram: no container ID. Response: {r.text[:200]}")

    # Step 2: Wait for processing
    _wait_for_ig_container(ig_user_id, access_token, container_id)

    # Step 3: Publish
    r2 = requests.post(
        f"https://graph.facebook.com/{GRAPH_VER}/{ig_user_id}/media_publish",
        params={"creation_id": container_id, "access_token": access_token},
        timeout=30,
    )
    _raise_with_detail(r2, "Instagram publish")
    post_id = r2.json().get("id", "")
    logger.info(f"Instagram published: {post_id} | caption: {len(caption_trimmed)} chars")
    return post_id


def _wait_for_ig_container(ig_user_id: str, access_token: str, container_id: str,
                            max_wait: int = 60):
    """
    Poll container status_code حتى FINISHED أو timeout.
    status_code values: IN_PROGRESS | FINISHED | ERROR | EXPIRED | PUBLISHED
    """
    for attempt in range(max_wait // 5):
        time.sleep(5)
        r = requests.get(
            f"https://graph.facebook.com/{GRAPH_VER}/{container_id}",
            params={"fields": "status_code,status", "access_token": access_token},
            timeout=15,
        )
        if r.ok:
            data = r.json()
            status = data.get("status_code", "")
            logger.debug(f"IG container {container_id} status: {status} (attempt {attempt+1})")
            if status == "FINISHED":
                return
            if status in ("ERROR", "EXPIRED"):
                raise ValueError(
                    f"Instagram container failed with status '{status}': {data.get('status', '')}"
                )
        # IN_PROGRESS → keep waiting
    # Timeout fallback — try to publish anyway
    logger.warning(f"IG container {container_id} polling timed out — attempting publish anyway")


def post_instagram_text(ig_user_id: str, access_token: str, text: str) -> str:
    """
    Instagram لا يدعم text-only posts على الـ feed عبر Content Publishing API.

    البدائل المتاحة:
    - استخدم Threads بدلاً منه للنص الطويل
    - أو أنشئ صورة نصية (text-on-image) وانشرها كـ image post

    الحل المطبق هنا: skip بدون error — المنشور يُنشر على باقي المنصات.
    """
    logger.info("Instagram: text-only posts not supported via API — skipped (use image post instead)")
    return ""


# ─── Twitter / X ─────────────────────────────────────────────────────────────

def post_twitter(api_key: str, api_secret: str, access_token: str,
                 access_token_secret: str, text: str, image_bytes: bytes = None) -> str:
    """نشر تغريدة مع أو بدون صورة."""
    import tweepy

    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
    api_v1 = tweepy.API(auth)
    client = tweepy.Client(
        consumer_key=api_key, consumer_secret=api_secret,
        access_token=access_token, access_token_secret=access_token_secret,
    )

    media_ids = []
    if image_bytes:
        media = api_v1.media_upload(filename="image.jpg", file=io.BytesIO(image_bytes))
        media_ids = [media.media_id_string]

    tweet = client.create_tweet(
        text=text[:270],
        media_ids=media_ids if media_ids else None,
    )
    return str(tweet.data.get("id", ""))


# ─── Threads ─────────────────────────────────────────────────────────────────

def post_threads_image(user_id: str, access_token: str, image_url: str, text: str) -> str:
    """نشر صورة على Threads."""
    headers = {"Authorization": f"Bearer {access_token}"}

    # Step 1: Create container
    r = requests.post(
        f"https://graph.threads.net/v1.0/{user_id}/threads",
        headers=headers,
        json={"media_type": "IMAGE", "image_url": image_url, "text": text[:500]},
        timeout=30,
    )
    _raise_with_detail(r, "Threads create image container")
    container_id = r.json().get("id")

    time.sleep(8)

    # Step 2: Publish
    r2 = requests.post(
        f"https://graph.threads.net/v1.0/{user_id}/threads_publish",
        headers=headers,
        json={"creation_id": container_id},
        timeout=30,
    )
    _raise_with_detail(r2, "Threads publish image")
    return r2.json().get("id", "")


def post_threads_text(user_id: str, access_token: str, text: str) -> str:
    """نشر منشور نصي على Threads."""
    headers = {"Authorization": f"Bearer {access_token}"}

    r = requests.post(
        f"https://graph.threads.net/v1.0/{user_id}/threads",
        headers=headers,
        json={"media_type": "TEXT", "text": text[:500]},
        timeout=30,
    )
    _raise_with_detail(r, "Threads create text container")
    container_id = r.json().get("id")

    time.sleep(8)

    r2 = requests.post(
        f"https://graph.threads.net/v1.0/{user_id}/threads_publish",
        headers=headers,
        json={"creation_id": container_id},
        timeout=30,
    )
    _raise_with_detail(r2, "Threads publish text")
    return r2.json().get("id", "")


# ─── LinkedIn ─────────────────────────────────────────────────────────────────

def post_linkedin_image(person_id: str, access_token: str, image_url: str,
                        text: str, idea_title: str = "") -> str:
    """
    نشر صورة على LinkedIn عبر رفع الصورة أولاً ثم نشرها.
    Flow:
    1. Register upload → get uploadUrl + asset URN
    2. PUT image bytes to uploadUrl
    3. Create UGC post with IMAGE media
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    # Step 1: Register image upload
    reg_body = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": f"urn:li:person:{person_id}",
            "serviceRelationships": [{
                "relationshipType": "OWNER",
                "identifier": "urn:li:userGeneratedContent",
            }],
        }
    }
    r = requests.post(
        "https://api.linkedin.com/v2/assets?action=registerUpload",
        headers=headers, json=reg_body, timeout=30,
    )
    _raise_with_detail(r, "LinkedIn register upload")
    reg_data   = r.json()
    upload_url = reg_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    asset_urn  = reg_data["value"]["asset"]

    # Step 2: Upload image bytes
    img_r = requests.get(image_url, timeout=60)
    img_r.raise_for_status()
    put_r = requests.put(
        upload_url,
        data=img_r.content,
        headers={"Authorization": f"Bearer {access_token}",
                 "Content-Type": "image/jpeg"},
        timeout=60,
    )
    if not put_r.ok and put_r.status_code != 201:
        raise requests.HTTPError(
            f"LinkedIn image upload failed [{put_r.status_code}]: {put_r.text[:200]}"
        )

    # Step 3: Create UGC post with uploaded image
    body = {
        "author": f"urn:li:person:{person_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text[:3000]},
                "shareMediaCategory": "IMAGE",
                "media": [{
                    "status": "READY",
                    "media": asset_urn,
                    "title": {"text": (idea_title or "")[:200]},
                }],
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    r2 = requests.post("https://api.linkedin.com/v2/ugcPosts", headers=headers, json=body, timeout=30)
    _raise_with_detail(r2, "LinkedIn image post")
    return r2.json().get("id", "")


def post_linkedin_text(person_id: str, access_token: str, text: str) -> str:
    """نشر منشور نصي على LinkedIn."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    body = {
        "author": f"urn:li:person:{person_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text[:3000]},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    r = requests.post("https://api.linkedin.com/v2/ugcPosts", headers=headers, json=body, timeout=30)
    _raise_with_detail(r, "LinkedIn text post")
    return r.json().get("id", "")


# ─── Connection test helpers ──────────────────────────────────────────────────

def test_facebook(page_id: str, access_token: str) -> dict:
    """اختبار الاتصال بـ Facebook — يرجع معلومات الصفحة."""
    r = requests.get(
        f"https://graph.facebook.com/{GRAPH_VER}/{page_id}",
        params={"fields": "id,name,fan_count", "access_token": access_token},
        timeout=15,
    )
    if r.ok:
        d = r.json()
        return {"ok": True, "name": d.get("name"), "fans": d.get("fan_count", 0)}
    return {"ok": False, "error": r.json().get("error", {}).get("message", r.text[:200])}


def test_instagram(ig_user_id: str, access_token: str) -> dict:
    """اختبار الاتصال بـ Instagram."""
    r = requests.get(
        f"https://graph.facebook.com/{GRAPH_VER}/{ig_user_id}",
        params={"fields": "id,username,followers_count", "access_token": access_token},
        timeout=15,
    )
    if r.ok:
        d = r.json()
        return {"ok": True, "username": d.get("username"), "followers": d.get("followers_count", 0)}
    return {"ok": False, "error": r.json().get("error", {}).get("message", r.text[:200])}


def test_threads(user_id: str, access_token: str) -> dict:
    """اختبار الاتصال بـ Threads."""
    r = requests.get(
        f"https://graph.threads.net/v1.0/{user_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"fields": "id,username"},
        timeout=15,
    )
    if r.ok:
        d = r.json()
        return {"ok": True, "username": d.get("username"), "id": d.get("id")}
    return {"ok": False, "error": r.text[:200]}


def test_linkedin(access_token: str) -> dict:
    """اختبار الاتصال بـ LinkedIn."""
    r = requests.get(
        "https://api.linkedin.com/v2/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    if r.ok:
        d = r.json()
        name = f"{d.get('localizedFirstName','')} {d.get('localizedLastName','')}".strip()
        return {"ok": True, "name": name, "id": d.get("id")}
    return {"ok": False, "error": r.text[:200]}


def test_twitter(api_key: str, api_secret: str, access_token: str, access_token_secret: str) -> dict:
    """اختبار الاتصال بـ Twitter/X."""
    try:
        import tweepy
        client = tweepy.Client(
            consumer_key=api_key, consumer_secret=api_secret,
            access_token=access_token, access_token_secret=access_token_secret,
        )
        me = client.get_me()
        return {"ok": True, "username": me.data.username if me.data else "unknown"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _raise_with_detail(response: requests.Response, context: str):
    """Raise with a clear error message including the API response."""
    if not response.ok:
        try:
            err = response.json().get("error", {})
            msg = err.get("message") or err.get("error_description") or response.text[:300]
        except Exception:
            msg = response.text[:300]
        raise requests.HTTPError(
            f"{context} failed [{response.status_code}]: {msg}",
            response=response,
        )
