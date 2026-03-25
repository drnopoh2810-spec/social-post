"""
Core workflow orchestration — mirrors the n8n workflow logic.
"""
import random
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def get_cfg():
    """Load all config values into a dict."""
    from database.models import Config
    keys = [
        "niche", "image_ratio_percent", "image_width", "image_height",
        "image_model", "worker_url", "pollinations_key", "frame_url",
        "cloudinary_cloud_name", "cloudinary_api_key", "cloudinary_api_secret",
        "fb_page_id", "fb_access_token", "ig_user_id", "ig_access_token",
        "threads_user_id", "threads_access_token", "li_person_id", "li_access_token",
        "delay_min_seconds", "delay_max_seconds",
    ]
    return {k: Config.get(k, "") for k in keys}


def get_ai_config(stage):
    """Get AI model + provider for a stage. No api_key needed — rotator handles it."""
    from database.models import AIModel, Prompt, db
    model_row = db.session.get(AIModel, stage)
    prompt_row = db.session.get(Prompt, stage)
    provider = model_row.provider if model_row else "cohere"
    return provider, prompt_row


def run_idea_factory(app):
    """Generate 10 new ideas and save to DB."""
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
                return

            # Build context from existing posts
            all_posts = Post.query.order_by(Post.created_at.desc()).all()
            all_ideas = "\n- ".join([p.idea for p in all_posts if p.idea][-50:])
            recent_posts = Post.query.filter(
                Post.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            ).all()
            recent_ideas = "\n- ".join([p.idea for p in recent_posts if p.idea])

            from collections import Counter
            kw_list = []
            for p in all_posts:
                if p.keywords:
                    kw_list.extend([k.strip() for k in p.keywords.split(",")])
            saturated = ", ".join([f"{k}({v})" for k, v in Counter(kw_list).most_common(10)])

            posted = [p for p in all_posts if p.status == "POSTED"]
            pending = [p for p in all_posts if p.status == "NEW"]
            top5 = sorted(posted, key=lambda x: x.engagement_score or 0, reverse=True)[:5]
            bottom5 = sorted(posted, key=lambda x: x.engagement_score or 0)[:5]
            avg_score = int(sum(p.engagement_score or 0 for p in posted) / len(posted)) if posted else 0

            stats = {
                "total": len(all_posts),
                "posted": len(posted),
                "pending": len(pending),
                "avg_score": avg_score,
                "top5": "\n".join([f'- "{p.idea[:60]}" | {p.tone} | score:{p.engagement_score}' for p in top5]) or "لا توجد بيانات",
                "bottom5": "\n".join([f'- "{p.idea[:60]}" | score:{p.engagement_score}' for p in bottom5]) or "لا توجد بيانات",
                "perf_summary": f"تم تحليل {len(posted)} منشور. متوسط: {avg_score}" if posted else "أول دورة",
                "recent_styles": " | ".join(list(set([p.writing_style for p in posted[-5:] if p.writing_style]))),
                "recent_openings": " | ".join(list(set([p.opening_type for p in posted[-5:] if p.opening_type]))),
                "last_snippet": (posted[-1].post_content or "")[:200] if posted else "",
            }

            # ── call_ai now handles key rotation internally ──────────────────
            ideas = generate_ideas(niche, all_ideas, recent_ideas, saturated, stats, prompt_row, provider)

            count = 0
            for idea in ideas:
                if not idea.get("idea"):
                    continue
                kw = idea.get("keywords", [])
                if isinstance(kw, list):
                    kw = ", ".join(kw)
                post = Post(
                    idea=idea["idea"], keywords=kw,
                    tone=idea.get("tone", ""),
                    writing_style=idea.get("writing_style", "مراقب ميداني"),
                    opening_type=idea.get("opening_type", "مشهد ميداني"),
                    status="NEW",
                )
                db.session.add(post)
                count += 1

            db.session.commit()
            log = WorkflowLog(event="idea_factory", message=f"Generated {count} ideas", level="info")
            db.session.add(log)
            db.session.commit()
            logger.info(f"Idea factory: {count} ideas generated")
            try:
                from services.telegram_bot import notify
                notify(f"🧠 <b>مصنع الأفكار:</b> تم توليد <b>{count}</b> فكرة جديدة ✅")
            except Exception:
                pass

        except KeysExhaustedError as e:
            logger.error(f"All AI keys exhausted: {e}")
            from database.models import db, WorkflowLog
            db.session.add(WorkflowLog(event="idea_factory", message=f"🔑 جميع مفاتيح AI انتهت: {e}", level="error"))
            db.session.commit()
            try:
                from services.telegram_bot import notify
                notify(f"🔑 <b>تحذير:</b> جميع مفاتيح AI انتهت!\n<code>{str(e)[:200]}</code>")
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Idea factory error: {e}")
            from database.models import db, WorkflowLog
            db.session.add(WorkflowLog(event="idea_factory", message=str(e), level="error"))
            db.session.commit()


def run_post_engine(app):
    """Pick one NEW post, write content, generate image, publish to all platforms."""
    with app.app_context():
        from database.models import db, Post, Platform, WorkflowLog
        from services.ai_service import write_post, generate_image_prompt, adapt_caption
        from services.image_service import process_image
        from services.key_rotator import KeysExhaustedError
        from services import social_service as ss

        try:
            cfg = get_cfg()
            niche = cfg.get("niche", "Special Education")

            post = Post.query.filter_by(status="NEW").order_by(Post.created_at.asc()).first()
            if not post:
                logger.info("No NEW posts to publish")
                return

            # ── Write post content ──────────────────────────────────────────
            provider, prompt_row = get_ai_config("post_writer")
            if not prompt_row:
                logger.warning("No prompt for post_writer")
                return

            idea_data = {
                "idea": post.idea, "keywords": post.keywords,
                "tone": post.tone, "writing_style": post.writing_style,
                "opening_type": post.opening_type, "last_snippet": "",
            }
            post_content = write_post(idea_data, niche, prompt_row, provider)
            post.post_content = post_content

            # ── Decide image or text ────────────────────────────────────────
            ratio = int(cfg.get("image_ratio_percent", 90))
            post_type = "image" if random.randint(1, 100) <= ratio else "text"
            post.post_type = post_type

            image_url = None
            if post_type == "image":
                ip_provider, ip_prompt = get_ai_config("image_prompt")
                if ip_prompt:
                    img_prompt = generate_image_prompt(
                        idea_data, niche,
                        int(cfg.get("image_width", 1080)),
                        int(cfg.get("image_height", 1350)),
                        ip_prompt, ip_provider
                    )
                    image_url = process_image({**cfg, "image_prompt": img_prompt}, cfg)
                    post.image_url = image_url

            # ── Publish to platforms ────────────────────────────────────────
            platforms = {p.name: p for p in Platform.query.filter_by(enabled=True).all()}

            if "facebook" in platforms:
                try:
                    if post_type == "image" and image_url:
                        post.fb_post_id = ss.post_facebook_image(cfg["fb_page_id"], cfg["fb_access_token"], image_url, post_content)
                    else:
                        post.fb_post_id = ss.post_facebook_text(cfg["fb_page_id"], cfg["fb_access_token"], post_content)
                except Exception as e:
                    logger.error(f"Facebook: {e}")

            if "instagram" in platforms:
                try:
                    cap = _platform_caption("ig_caption", post_content, niche)
                    if post_type == "image" and image_url:
                        post.ig_post_id = ss.post_instagram_image(cfg["ig_user_id"], cfg["ig_access_token"], image_url, cap)
                    else:
                        post.ig_post_id = ss.post_instagram_text(cfg["ig_user_id"], cfg["ig_access_token"], cap)
                except Exception as e:
                    logger.error(f"Instagram: {e}")

            if "threads" in platforms:
                try:
                    cap = _platform_caption("threads_caption", post_content, niche)
                    if post_type == "image" and image_url:
                        post.threads_post_id = ss.post_threads_image(cfg["threads_user_id"], cfg["threads_access_token"], image_url, cap)
                    else:
                        post.threads_post_id = ss.post_threads_text(cfg["threads_user_id"], cfg["threads_access_token"], cap)
                except Exception as e:
                    logger.error(f"Threads: {e}")

            if "linkedin" in platforms:
                try:
                    cap = _platform_caption("linkedin_caption", post_content, niche)
                    if post_type == "image" and image_url:
                        post.linkedin_post_id = ss.post_linkedin_image(cfg["li_person_id"], cfg["li_access_token"], image_url, cap, post.idea or "")
                    else:
                        post.linkedin_post_id = ss.post_linkedin_text(cfg["li_person_id"], cfg["li_access_token"], cap)
                except Exception as e:
                    logger.error(f"LinkedIn: {e}")

            if "twitter" in platforms:
                try:
                    from database.models import Config as Cfg
                    cap = _platform_caption("x_caption", post_content, niche)
                    img_bytes = None
                    if post_type == "image" and image_url:
                        import requests as req
                        img_bytes = req.get(image_url, timeout=30).content
                    post.x_post_id = ss.post_twitter(
                        Cfg.get("twitter_api_key"), Cfg.get("twitter_api_secret"),
                        Cfg.get("twitter_access_token"), Cfg.get("twitter_access_token_secret"),
                        cap, img_bytes
                    )
                except Exception as e:
                    logger.error(f"Twitter: {e}")

            post.status = "POSTED"
            post.posted_at = datetime.utcnow()
            db.session.commit()

            db.session.add(WorkflowLog(event="post_engine", message=f"Published post #{post.id} ({post_type})", level="info"))
            db.session.commit()
            logger.info(f"Post #{post.id} published")
            try:
                from services.telegram_bot import notify
                ptype_ar = "🖼️ صورة" if post_type == "image" else "📝 نص"
                notify(
                    f"✅ <b>تم النشر بنجاح!</b>\n"
                    f"📌 <code>#{post.id}</code> {(post.idea or '')[:80]}...\n"
                    f"📋 النوع: {ptype_ar}"
                )
            except Exception:
                pass

        except KeysExhaustedError as e:
            logger.error(f"All AI keys exhausted: {e}")
            from database.models import db, WorkflowLog
            db.session.add(WorkflowLog(event="post_engine", message=f"🔑 جميع مفاتيح AI انتهت: {e}", level="error"))
            db.session.commit()
            try:
                from services.telegram_bot import notify
                notify(f"🔑 <b>تحذير:</b> جميع مفاتيح AI انتهت!\n<code>{str(e)[:200]}</code>")
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Post engine error: {e}")
            from database.models import db, WorkflowLog
            db.session.add(WorkflowLog(event="post_engine", message=str(e), level="error"))
            db.session.commit()
            try:
                from services.telegram_bot import notify
                notify(f"❌ <b>خطأ في محرك النشر:</b>\n<code>{str(e)[:300]}</code>")
            except Exception:
                pass


def _platform_caption(stage, post_content, niche):
    """Adapt caption for a platform using AI, fallback to original."""
    try:
        from services.ai_service import adapt_caption
        provider, prompt_row = get_ai_config(stage)
        if prompt_row:
            return adapt_caption(stage, post_content, prompt_row, provider)
    except Exception as e:
        logger.warning(f"Caption adaptation failed for {stage}: {e}")
    return post_content
