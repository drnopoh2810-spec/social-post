"""
Telegram Bot — لوحة تحكم كاملة عبر تيليجرام
=============================================
الأوامر:
  /start /help /status /ideas /post /pending /posted
  /logs /keys /platforms /pause /resume /skip <id>
  /delete <id> /config
"""

import logging
import threading
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

_flask_app = None
_bot_loop: asyncio.AbstractEventLoop = None   # the bot's dedicated event loop
_bot_instance = None                           # telegram.Bot instance (set after init)
_scheduler_paused = False


# ── Public notify API ─────────────────────────────────────────────────────────

def notify(message: str, parse_mode: str = "HTML"):
    """
    Push a message to the admin Telegram chat.
    Safe to call from any thread — uses the bot's own event loop.
    """
    if not _bot_loop or not _bot_instance or not _flask_app:
        return
    try:
        with _flask_app.app_context():
            from database.models import Config
            chat_id = (Config.get("telegram_admin_chat_id", "")
                       or _flask_app.config.get("TELEGRAM_ADMIN_CHAT_ID", ""))
        if not chat_id:
            return
        future = asyncio.run_coroutine_threadsafe(
            _bot_instance.send_message(chat_id=chat_id, text=message, parse_mode=parse_mode),
            _bot_loop,
        )
        future.result(timeout=10)
    except Exception as e:
        logger.warning(f"Telegram notify failed: {e}")


# ── Auth guard ────────────────────────────────────────────────────────────────

def _admin_chat_id() -> str:
    if not _flask_app:
        return ""
    with _flask_app.app_context():
        from database.models import Config
        return str(Config.get("telegram_admin_chat_id", "")
                   or _flask_app.config.get("TELEGRAM_ADMIN_CHAT_ID", ""))


async def _auth(update, context) -> bool:
    if str(update.effective_chat.id) != _admin_chat_id():
        await update.message.reply_text("⛔ غير مصرح.")
        return False
    return True


# ── Sync helpers (called from async handlers) ─────────────────────────────────

def _stats():
    with _flask_app.app_context():
        from database.models import Post
        total   = Post.query.count()
        posted  = Post.query.filter_by(status="POSTED").count()
        pending = Post.query.filter_by(status="NEW").count()
        today   = Post.query.filter(
            Post.posted_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        return total, posted, pending, today


def _platform_lines():
    with _flask_app.app_context():
        from database.models import Platform
        icons = {"facebook":"📘","instagram":"📷","twitter":"𝕏","threads":"🔗","linkedin":"💼"}
        return "\n".join(
            f"{icons.get(p.name,'📱')} {p.name.capitalize()}: {'✅' if p.enabled else '❌'}"
            for p in Platform.query.all()
        )


def _ai_keys_lines():
    with _flask_app.app_context():
        from services.key_rotator import get_provider_status
        lines = []
        for p in ["cohere","gemini","groq","openrouter","openai"]:
            s = get_provider_status(p)
            if s["total"] == 0:
                continue
            icon = "🟢" if s["healthy"] else "🔴"
            lines.append(f"{icon} <b>{p}</b>: {s['available']}/{s['total']} متاح"
                         + (f" | {s['exhausted']} منتهي" if s["exhausted"] else ""))
        return "\n".join(lines) or "لا توجد مفاتيح مضافة"


# ── Command handlers ──────────────────────────────────────────────────────────

async def cmd_start(update, context):
    if not await _auth(update, context): return
    await update.message.reply_text(
        "🧠 <b>بوست سوشال — لوحة التحكم</b>\n\n"
        "/status — حالة النظام\n/ideas — توليد أفكار\n/post — نشر الآن\n"
        "/pending — أفكار منتظرة\n/posted — آخر المنشورات\n/logs — السجل\n"
        "/keys — مفاتيح AI\n/platforms — المنصات\n/pause — إيقاف الجدولة\n"
        "/resume — استئناف الجدولة\n/skip &lt;id&gt; — تخطي فكرة\n"
        "/delete &lt;id&gt; — حذف فكرة\n/config — الإعدادات",
        parse_mode="HTML"
    )

async def cmd_help(update, context):
    await cmd_start(update, context)

async def cmd_status(update, context):
    if not await _auth(update, context): return
    total, posted, pending, today = _stats()
    await update.message.reply_text(
        f"📊 <b>حالة النظام</b>\n\n"
        f"💡 إجمالي: <b>{total}</b> | ✅ منشور: <b>{posted}</b>\n"
        f"⏳ انتظار: <b>{pending}</b> | 📅 اليوم: <b>{today}</b>\n\n"
        f"<b>المنصات:</b>\n{_platform_lines()}\n\n"
        f"{'⏸️ <b>الجدولة متوقفة</b>' if _scheduler_paused else '▶️ الجدولة تعمل'}",
        parse_mode="HTML"
    )

async def cmd_ideas(update, context):
    if not await _auth(update, context): return
    await update.message.reply_text("🧠 جاري توليد الأفكار في الخلفية...")
    threading.Thread(target=_run_ideas, daemon=True).start()

async def cmd_post(update, context):
    if not await _auth(update, context): return
    await update.message.reply_text("📢 جاري تشغيل محرك النشر في الخلفية...")
    threading.Thread(target=_run_post, daemon=True).start()

async def cmd_pending(update, context):
    if not await _auth(update, context): return
    with _flask_app.app_context():
        from database.models import Post
        posts = Post.query.filter_by(status="NEW").order_by(Post.created_at.asc()).limit(10).all()
    if not posts:
        await update.message.reply_text("📭 لا توجد أفكار منتظرة.")
        return
    lines = [f"⏳ <b>الأفكار المنتظرة ({len(posts)}):</b>\n"]
    for p in posts:
        lines.append(f"• <code>#{p.id}</code> {(p.idea or '')[:80]}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def cmd_posted(update, context):
    if not await _auth(update, context): return
    with _flask_app.app_context():
        from database.models import Post
        posts = Post.query.filter_by(status="POSTED").order_by(Post.posted_at.desc()).limit(5).all()
    if not posts:
        await update.message.reply_text("📭 لا توجد منشورات بعد.")
        return
    lines = ["✅ <b>آخر المنشورات:</b>\n"]
    for p in posts:
        date = p.posted_at.strftime("%Y-%m-%d %H:%M") if p.posted_at else "—"
        lines.append(
            f"{'🖼️' if p.post_type=='image' else '📝'} <code>#{p.id}</code> {(p.idea or '')[:60]}\n"
            f"   📅 {date} | score: {p.engagement_score or 0}"
        )
    await update.message.reply_text("\n\n".join(lines), parse_mode="HTML")

async def cmd_logs(update, context):
    if not await _auth(update, context): return
    with _flask_app.app_context():
        from database.models import WorkflowLog
        logs = WorkflowLog.query.order_by(WorkflowLog.created_at.desc()).limit(10).all()
    if not logs:
        await update.message.reply_text("📋 لا توجد أحداث.")
        return
    icons = {"info":"ℹ️","warning":"⚠️","error":"❌"}
    lines = ["📋 <b>آخر الأحداث:</b>\n"]
    for log in logs:
        t = log.created_at.strftime("%H:%M:%S") if log.created_at else ""
        lines.append(f"{icons.get(log.level,'•')} <code>[{t}]</code> <b>{log.event}</b>\n   {(log.message or '')[:120]}")
    await update.message.reply_text("\n\n".join(lines), parse_mode="HTML")

async def cmd_keys(update, context):
    if not await _auth(update, context): return
    await update.message.reply_text(f"🗝️ <b>حالة مفاتيح AI:</b>\n\n{_ai_keys_lines()}", parse_mode="HTML")

async def cmd_platforms(update, context):
    if not await _auth(update, context): return
    await update.message.reply_text(f"📱 <b>حالة المنصات:</b>\n\n{_platform_lines()}", parse_mode="HTML")

async def cmd_pause(update, context):
    if not await _auth(update, context): return
    global _scheduler_paused
    _scheduler_paused = True
    _pause_resume_scheduler(pause=True)
    await update.message.reply_text("⏸️ تم إيقاف الجدولة مؤقتاً.")

async def cmd_resume(update, context):
    if not await _auth(update, context): return
    global _scheduler_paused
    _scheduler_paused = False
    _pause_resume_scheduler(pause=False)
    await update.message.reply_text("▶️ تم استئناف الجدولة.")

async def cmd_skip(update, context):
    if not await _auth(update, context): return
    if not context.args:
        await update.message.reply_text("الاستخدام: /skip <id>"); return
    try:
        pid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID غير صحيح."); return
    with _flask_app.app_context():
        from database.models import db, Post
        p = db.session.get(Post, pid)
        if not p:
            await update.message.reply_text(f"❌ لا توجد فكرة #{pid}"); return
        p.status = "SKIP"
        db.session.commit()
    await update.message.reply_text(f"⏭️ تم تخطي الفكرة #{pid}")

async def cmd_delete(update, context):
    if not await _auth(update, context): return
    if not context.args:
        await update.message.reply_text("الاستخدام: /delete <id>"); return
    try:
        pid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID غير صحيح."); return
    with _flask_app.app_context():
        from database.models import db, Post
        p = db.session.get(Post, pid)
        if not p:
            await update.message.reply_text(f"❌ لا توجد فكرة #{pid}"); return
        db.session.delete(p)
        db.session.commit()
    await update.message.reply_text(f"🗑️ تم حذف الفكرة #{pid}")

async def cmd_config(update, context):
    if not await _auth(update, context): return
    with _flask_app.app_context():
        from database.models import Config
        niche   = (Config.get("niche","") or "")[:80]
        ratio   = Config.get("image_ratio_percent","90")
        t_idea  = Config.get("idea_factory_time","08:00")
        times   = " | ".join(Config.get(f"sched_{i}","—") for i in range(1,5))
        fb_page = Config.get("fb_page_id","—")
        ig_uid  = Config.get("ig_user_id","—")
    await update.message.reply_text(
        f"⚙️ <b>الإعدادات:</b>\n\n"
        f"🎯 النيش: <code>{niche}</code>\n"
        f"🖼️ نسبة الصور: <b>{ratio}%</b>\n"
        f"🕗 مصنع الأفكار: <b>{t_idea}</b>\n"
        f"📅 مواعيد النشر: <b>{times}</b>\n"
        f"📘 FB Page: <code>{fb_page}</code>\n"
        f"📷 IG User: <code>{ig_uid}</code>",
        parse_mode="HTML"
    )


# ── Background task runners ───────────────────────────────────────────────────

def _run_ideas():
    from services.workflow_service import run_idea_factory
    run_idea_factory(_flask_app)

def _run_post():
    from services.workflow_service import run_post_engine
    run_post_engine(_flask_app)

def _pause_resume_scheduler(pause: bool):
    """Pause or resume APScheduler without circular import."""
    try:
        import app as _app_module
        sched = getattr(_app_module, 'scheduler', None)
        if sched:
            sched.pause() if pause else sched.resume()
    except Exception as e:
        logger.warning(f"Scheduler pause/resume failed: {e}")


# ── Bot lifecycle ─────────────────────────────────────────────────────────────

def start_bot(flask_app):
    """Start the Telegram bot in a background daemon thread."""
    global _flask_app
    _flask_app = flask_app

    token = flask_app.config.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        with flask_app.app_context():
            from database.models import Config
            token = Config.get("telegram_bot_token", "")
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram bot disabled")
        return

    t = threading.Thread(target=_run_bot, args=(token,), daemon=True, name="telegram-bot")
    t.start()
    logger.info("Telegram bot thread started")


def _run_bot(token: str):
    """Dedicated event loop for the Telegram bot."""
    global _bot_loop, _bot_instance

    from telegram.ext import Application, CommandHandler

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _bot_loop = loop

    async def _main():
        global _bot_instance
        tg_app = Application.builder().token(token).build()
        _bot_instance = tg_app.bot

        for cmd, handler in [
            ("start",     cmd_start),
            ("help",      cmd_help),
            ("status",    cmd_status),
            ("ideas",     cmd_ideas),
            ("post",      cmd_post),
            ("pending",   cmd_pending),
            ("posted",    cmd_posted),
            ("logs",      cmd_logs),
            ("keys",      cmd_keys),
            ("platforms", cmd_platforms),
            ("pause",     cmd_pause),
            ("resume",    cmd_resume),
            ("skip",      cmd_skip),
            ("delete",    cmd_delete),
            ("config",    cmd_config),
        ]:
            tg_app.add_handler(CommandHandler(cmd, handler))

        logger.info("Telegram bot polling started")
        # run_polling handles initialize/start/idle/stop cleanly
        await tg_app.run_polling(drop_pending_updates=True, close_loop=False)

    try:
        loop.run_until_complete(_main())
    except Exception as e:
        logger.error(f"Telegram bot crashed: {e}")
    finally:
        loop.close()
