"""
Core workflow orchestration — mirrors the n8n workflow logic.
"""
import random
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


def get_cfg():
    """Load all config values into a dict."""
    from database.models import Config
    keys = [
        # Content
        "niche", "image_ratio_percent",
        # Image
        "image_width", "image_height", "image_model",
        "worker_url", "pollinations_key", "frame_url", "frame_opacity",
        "cloudinary_cloud_name", "cloudinary_api_key", "cloudinary_api_secret",
        # Social platforms
        "fb_page_id", "fb_access_token",
        "ig_user_id", "ig_access_token",
        "threads_user_id", "threads_access_token",
        "li_person_id", "li_access_token",
        "twitter_api_key", "twitter_api_secret",
        "twitter_access_token", "twitter_access_token_secret",
        # Timing
        "delay_min_seconds", "delay_max_seconds",
    ]
    return {k: Config.get(k, "") for k in keys}


def get_ai_config(stage):
    """Get AI model + provider for a stage."""
    from database.models import AIModel, Prompt, db
    model_row = db.session.get(AIModel, stage)
    prompt_row = db.session.get(Prompt, stage)
    provider = model_row.provider if model_row else "gemini"
    return provider, prompt_row


def _is_valid_image_url(url: str) -> bool:
    """Check if URL is a real public URL (not data: or truncated)."""
    if not url:
        return False
    if url.startswith("data:"):
        return False
    if not url.startswith("http"):
        return False
    return True


def run_idea_factory(app):
    """Generate new ideas and save to DB / Google Sheets."""
    with app.app_context():
        from database.models import db, Post, WorkflowLog
        from services.ai_service import generate_ideas
        from services.key_rotator import KeysExhaustedError

        try:
            cfg = get_cfg()
            niche = cfg.get("niche", "Special Education")
            provider, prompt_row = get_ai_config("idea_factory")

            if not prompt_row:
                logger.warning("No prompt configured for idea_factory")
                _log(db, "idea_factory", "لا يوجد برومبت لمصنع الأفكار — أضف من /prompts", "error")
                return

            # ── Build context from existing posts ─────────────────────────
            all_posts   = Post.query.order_by(Post.created_at.desc()).all()
            all_ideas   = "\n- ".join([p.idea for p in all_posts if p.idea][-50:])
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            recent_posts  = [p for p in all_posts if p.created_at and p.created_at >= today_start]
            recent_ideas  = "\n- ".join([p.idea for p in recent_posts if p.idea])

            from collections import Counter
            kw_list = []
            for p in all_posts:
                if p.keywords:
                    kw_list.extend([k.strip() for k in p.keywords.split(",")])
            saturated = ", ".join([f"{k}({v})" for k, v in Counter(kw_list).most_common(10)])

            posted   = [p for p in all_posts if p.status == "POSTED"]
            pending  = [p for p in all_posts if p.status == "NEW"]
            top5     = sorted(posted, key=lambda x: x.engagement_score or 0, reverse=True)[:5]
            bottom5  = sorted(posted, key=lambda x: x.engagement_score or 0)[:5]
            avg_score = int(sum(p.engagement_score or 0 for p in posted) / len(posted)) if posted else 0

            stats = {
                "total":    len(all_posts),
                "posted":   len(posted),
                "pending":  len(pending),
                "avg_score": avg_score,
                "top5":     "\n".join([f'- "{p.idea[:60]}" | {p.tone} | score:{p.engagement_score}' for p in top5]) or "لا توجد بيانات",
                "bottom5":  "\n".join([f'- "{p.idea[:60]}" | score:{p.engagement_score}' for p in bottom5]) or "لا توجد بيانات",
                "perf_summary": f"تم تحليل {len(posted)} منشور. متوسط: {avg_score}" if posted else "أول دورة",
                "recent_styles":   " | ".join(list(set([p.writing_style for p in posted[-5:] if p.writing_style]))),
                "recent_openings": " | ".join(list(set([p.opening_type  for p in posted[-5:] if p.opening_type]))),
                "last_snippet":    (posted[-1].post_content or "")[:200] if posted else "",
            }

            # ── Generate ideas via AI ──────────────────────────────────────
            ideas = generate_ideas(niche, all_ideas, recent_ideas, saturated, stats, prompt_row, provider)
            valid_ideas = [i for i in ideas if i.get("idea")]

            if not valid_ideas:
                logger.warning("AI returned no valid ideas")
                _log(db, "idea_factory", "AI لم يُرجع أفكاراً صالحة", "warning")
                return

            count = 0

            # ── Write to Sheets first, then sync to DB ─────────────────────
            try:
                from services.sheets_sync import write_ideas_to_sheets, sync_from_sheets_to_db, is_configured
                if is_configured():
                    written = write_ideas_to_sheets(valid_ideas)
                    logger.info(f"Wrote {written} ideas to Google Sheets")
                    ins, _ = sync_from_sheets_to_db()
                    count = ins
                    logger.info(f"Synced {ins} new ideas from Sheets → DB")
                else:
                    raise ValueError("Sheets not configured")
            except Exception as sheets_err:
                logger.warning(f"Sheets write failed ({sheets_err}) — saving directly to DB")
                for idea in valid_ideas:
                    kw = idea.get("keywords", [])
                    if isinstance(kw, list):
                        kw = ", ".join(kw)
                    db.session.add(Post(
                        idea=idea["idea"], keywords=kw,
                        tone=idea.get("tone", ""),
                        writing_style=idea.get("writing_style", "مراقب ميداني"),
                        opening_type=idea.get("opening_type", "مشهد ميداني"),
                        status="NEW",
                    ))
                    count += 1
                db.session.commit()

            _log(db, "idea_factory", f"تم توليد {count} فكرة جديدة", "info")
            logger.info(f"Idea factory: {count} ideas generated")

            try:
                from services.telegram_bot import notify
                notify(f"🧠 <b>مصنع الأفكار:</b> تم توليد <b>{count}</b> فكرة جديدة ✅")
            except Exception:
                pass

        except KeysExhaustedError as e:
            logger.error(f"All AI keys exhausted: {e}")
            _log(db, "idea_factory", f"🔑 جميع مفاتيح AI انتهت: {str(e)[:300]}", "error")
            try:
                from services.telegram_bot import notify
                notify(f"🔑 <b>تحذير:</b> جميع مفاتيح AI انتهت!\n<code>{str(e)[:200]}</code>")
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Idea factory error: {e}", exc_info=True)
            _log(db, "idea_factory", f"خطأ: {str(e)[:400]}", "error")


def run_post_engine(app):
    """Pick one NEW post, write content, generate image, publish to all platforms."""
    with app.app_context():
        from database.models import db, Post, Platform, WorkflowLog
        from services.ai_service import write_post, generate_image_prompt
        from services.image_service import process_image
        from services.key_rotator import KeysExhaustedError
        from services import social_service as ss

        try:
            cfg   = get_cfg()
            niche = cfg.get("niche", "Special Education")

            # ── Pick next NEW post ─────────────────────────────────────────
            post = Post.query.filter_by(status="NEW").order_by(Post.created_at.asc()).first()
            if not post:
                logger.info("No NEW posts to publish")
                return

            # Mark as IN_PROGRESS to prevent double-publishing
            post.status = "IN_PROGRESS"
            db.session.commit()

            try:
                _run_single_post(post, cfg, niche, db, ss, process_image,
                                 write_post, generate_image_prompt)
            except Exception as inner_e:
                # Revert status so it can be retried
                post.status = "NEW"
                db.session.commit()
                raise inner_e

        except KeysExhaustedError as e:
            logger.error(f"All AI keys exhausted: {e}")
            _log(db, "post_engine", f"🔑 جميع مفاتيح AI انتهت: {str(e)[:300]}", "error")
            try:
                from services.telegram_bot import notify
                notify(f"🔑 <b>تحذير:</b> جميع مفاتيح AI انتهت!\n<code>{str(e)[:200]}</code>")
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Post engine error: {e}", exc_info=True)
            _log(db, "post_engine", f"خطأ: {str(e)[:400]}", "error")
            try:
                from services.telegram_bot import notify
                notify(f"❌ <b>خطأ في محرك النشر:</b>\n<code>{str(e)[:300]}</code>")
            except Exception:
                pass


def _run_single_post(post, cfg, niche, db, ss, process_image,
                     write_post, generate_image_prompt):
    """Core logic for publishing one post — separated for clean error handling."""

    # ── 1. Write post content ──────────────────────────────────────────────
    provider, prompt_row = get_ai_config("post_writer")
    if not prompt_row:
        raise RuntimeError("No prompt configured for post_writer — add from /prompts")

    idea_data = {
        "idea":         post.idea or "",
        "keywords":     post.keywords or "",
        "tone":         post.tone or "",
        "writing_style": post.writing_style or "",
        "opening_type": post.opening_type or "",
        "last_snippet": "",
    }
    post_content = write_post(idea_data, niche, prompt_row, provider)
    if not post_content or len(post_content.strip()) < 50:
        raise RuntimeError(f"AI returned empty/short post content: '{post_content[:100]}'")
    post.post_content = post_content

    # ── 2. Decide image or text ────────────────────────────────────────────
    ratio     = int(cfg.get("image_ratio_percent", "90") or 90)
    post_type = "image" if random.randint(1, 100) <= ratio else "text"
    post.post_type = post_type

    # ── 3. Generate image ──────────────────────────────────────────────────
    image_url = None
    image_pid = None   # Cloudinary public_id for deletion after publishing
    if post_type == "image":
        ip_provider, ip_prompt = get_ai_config("image_prompt")
        if ip_prompt:
            try:
                img_prompt = generate_image_prompt(
                    idea_data, niche,
                    int(cfg.get("image_width", "1080") or 1080),
                    int(cfg.get("image_height", "1350") or 1350),
                    ip_prompt, ip_provider,
                )
                result = process_image(
                    {**cfg, "image_prompt": img_prompt,
                     "post_content": post_content,
                     "idea": post.idea or ""},
                    cfg
                )
                # process_image now returns (url, public_id)
                if isinstance(result, tuple):
                    image_url, image_pid = result
                else:
                    image_url = result  # backward compat
                if _is_valid_image_url(image_url):
                    post.image_url = image_url
                else:
                    logger.warning("Image generation returned invalid URL — falling back to text post")
                    post_type = "text"
                    post.post_type = "text"
            except Exception as img_err:
                logger.warning(f"Image generation failed: {img_err} — falling back to text post")
                post_type = "text"
                post.post_type = "text"
        else:
            logger.warning("No image_prompt configured — posting as text")
            post_type = "text"
            post.post_type = "text"

    # ── 4. Publish to platforms ────────────────────────────────────────────
    platforms = {p.name: p for p in
                 __import__('database.models', fromlist=['Platform']).Platform
                 .query.filter_by(enabled=True).all()}

    published_to = []
    failed_on    = []

    # ── Facebook ──────────────────────────────────────────────────────────
    if "facebook" in platforms:
        fb_id = cfg.get("fb_page_id", "")
        fb_token = cfg.get("fb_access_token", "")
        if fb_id and fb_token:
            try:
                if post_type == "image" and image_url:
                    post.fb_post_id = ss.post_facebook_image(fb_id, fb_token, image_url, post_content)
                else:
                    post.fb_post_id = ss.post_facebook_text(fb_id, fb_token, post_content)
                published_to.append("Facebook")
                logger.info(f"✅ Facebook: {post.fb_post_id}")
            except Exception as e:
                failed_on.append(f"Facebook: {str(e)[:100]}")
                logger.error(f"Facebook publish failed: {e}")
        else:
            logger.warning("Facebook: missing fb_page_id or fb_access_token — skipped")

    # ── Instagram ─────────────────────────────────────────────────────────
    if "instagram" in platforms:
        ig_id    = cfg.get("ig_user_id", "")
        ig_token = cfg.get("ig_access_token", "")
        if ig_id and ig_token:
            if post_type == "image" and image_url:
                try:
                    cap = _platform_caption("ig_caption", post_content, niche)
                    post.ig_post_id = ss.post_instagram_image(ig_id, ig_token, image_url, cap)
                    if post.ig_post_id:
                        published_to.append("Instagram")
                        logger.info(f"✅ Instagram: {post.ig_post_id}")
                except Exception as e:
                    failed_on.append(f"Instagram: {str(e)[:100]}")
                    logger.error(f"Instagram publish failed: {e}")
            else:
                logger.info("Instagram: text-only post skipped (API limitation)")
        else:
            logger.warning("Instagram: missing ig_user_id or ig_access_token — skipped")

    # ── Threads ───────────────────────────────────────────────────────────
    if "threads" in platforms:
        th_id    = cfg.get("threads_user_id", "")
        th_token = cfg.get("threads_access_token", "")
        if th_id and th_token:
            try:
                cap = _platform_caption("threads_caption", post_content, niche)
                if post_type == "image" and image_url:
                    post.threads_post_id = ss.post_threads_image(th_id, th_token, image_url, cap)
                else:
                    post.threads_post_id = ss.post_threads_text(th_id, th_token, cap)
                published_to.append("Threads")
                logger.info(f"✅ Threads: {post.threads_post_id}")
            except Exception as e:
                failed_on.append(f"Threads: {str(e)[:100]}")
                logger.error(f"Threads publish failed: {e}")
        else:
            logger.warning("Threads: missing threads_user_id or threads_access_token — skipped")

    # ── LinkedIn ──────────────────────────────────────────────────────────
    if "linkedin" in platforms:
        li_id    = cfg.get("li_person_id", "")
        li_token = cfg.get("li_access_token", "")
        if li_id and li_token:
            try:
                cap = _platform_caption("linkedin_caption", post_content, niche)
                if post_type == "image" and image_url:
                    post.linkedin_post_id = ss.post_linkedin_image(li_id, li_token, image_url, cap, post.idea or "")
                else:
                    post.linkedin_post_id = ss.post_linkedin_text(li_id, li_token, cap)
                published_to.append("LinkedIn")
                logger.info(f"✅ LinkedIn: {post.linkedin_post_id}")
            except Exception as e:
                failed_on.append(f"LinkedIn: {str(e)[:100]}")
                logger.error(f"LinkedIn publish failed: {e}")
        else:
            logger.warning("LinkedIn: missing li_person_id or li_access_token — skipped")

    # ── Twitter / X ───────────────────────────────────────────────────────
    if "twitter" in platforms:
        tw_key    = cfg.get("twitter_api_key", "")
        tw_secret = cfg.get("twitter_api_secret", "")
        tw_token  = cfg.get("twitter_access_token", "")
        tw_tsecret = cfg.get("twitter_access_token_secret", "")
        if tw_key and tw_secret and tw_token and tw_tsecret:
            try:
                cap = _platform_caption("x_caption", post_content, niche)
                img_bytes = None
                if post_type == "image" and image_url:
                    import requests as req
                    img_bytes = req.get(image_url, timeout=30).content
                post.x_post_id = ss.post_twitter(tw_key, tw_secret, tw_token, tw_tsecret, cap, img_bytes)
                published_to.append("Twitter/X")
                logger.info(f"✅ Twitter: {post.x_post_id}")
            except Exception as e:
                failed_on.append(f"Twitter: {str(e)[:100]}")
                logger.error(f"Twitter publish failed: {e}")
        else:
            logger.warning("Twitter: missing credentials — skipped")

    # ── 5. Mark as POSTED ─────────────────────────────────────────────────
    post.status    = "POSTED"
    post.posted_at = datetime.utcnow()
    db.session.commit()

    ptype_ar = "🖼️ صورة" if post_type == "image" else "📝 نص"
    pub_str  = ", ".join(published_to) if published_to else "لا شيء"
    fail_str = " | ".join(failed_on) if failed_on else ""

    _log(db, "post_engine",
         f"نُشر #{post.id} ({ptype_ar}) على: {pub_str}"
         + (f" | فشل: {fail_str}" if fail_str else ""),
         "info" if published_to else "warning")

    logger.info(f"Post #{post.id} published to: {pub_str}")

    # ── 6. Delete image from Cloudinary after publishing ──────────────────
    # الصورة تم نشرها على المنصات — لا حاجة لها على Cloudinary
    if image_pid and published_to:
        try:
            from services.image_service import delete_from_cloudinary
            cloud_name = cfg.get("cloudinary_cloud_name", "")
            api_key    = cfg.get("cloudinary_api_key", "")
            api_secret = cfg.get("cloudinary_api_secret", "")
            if cloud_name and api_key and api_secret:
                deleted = delete_from_cloudinary(image_pid, cloud_name, api_key, api_secret)
                if deleted:
                    logger.info(f"Cloudinary: deleted image {image_pid} after publishing")
        except Exception as e:
            logger.warning(f"Cloudinary cleanup failed: {e}")  # non-critical

    # ── 6. Sync to Google Sheets ──────────────────────────────────────────
    try:
        from services.sheets_sync import push_post, is_configured
        if is_configured():
            push_post(post)
    except Exception as e:
        logger.warning(f"Sheets push failed: {e}")

    # ── 7. Telegram notification ──────────────────────────────────────────
    try:
        from services.telegram_bot import notify
        msg = (
            f"✅ <b>تم النشر!</b>\n"
            f"📌 <code>#{post.id}</code> {(post.idea or '')[:80]}\n"
            f"📋 النوع: {ptype_ar}\n"
            f"📢 المنصات: {pub_str}"
        )
        if fail_str:
            msg += f"\n⚠️ فشل: {fail_str}"
        notify(msg)
    except Exception:
        pass


def _platform_caption(stage: str, post_content: str, niche: str) -> str:
    """Adapt caption for a platform using AI. Falls back to original on error."""
    try:
        from services.ai_service import adapt_caption
        provider, prompt_row = get_ai_config(stage)
        if prompt_row:
            result = adapt_caption(stage, post_content, prompt_row, provider)
            if result and len(result.strip()) > 10:
                return result
    except Exception as e:
        logger.warning(f"Caption adaptation failed for {stage}: {e}")
    return post_content


def _log(db, event: str, message: str, level: str = "info"):
    """Helper to add a WorkflowLog entry."""
    try:
        from database.models import WorkflowLog
        db.session.add(WorkflowLog(event=event, message=message[:500], level=level))
        db.session.commit()
    except Exception as e:
        logger.warning(f"Failed to write WorkflowLog: {e}")
