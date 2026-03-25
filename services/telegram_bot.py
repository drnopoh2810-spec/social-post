"""
Telegram Bot — لوحة تحكم تفاعلية كاملة
========================================
يستخدم Inline Keyboards للتنقل بين القوائم بدون أوامر نصية.

القوائم:
  🏠 الرئيسية  →  إحصائيات + أزرار سريعة
  📝 الأفكار   →  عرض / تخطي / حذف
  📢 النشر     →  نشر الآن / توليد أفكار
  📊 التحليلات →  أفضل المنشورات
  ⚙️ الإعدادات →  عرض الإعدادات + مفاتيح AI
  📋 السجل     →  آخر الأحداث
  ✍️ البرومبتات →  عرض وتعديل كل مرحلة
"""

import logging
import threading
import asyncio
from datetime import datetime

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand, ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters, ConversationHandler
)

logger = logging.getLogger(__name__)

# Conversation states for prompt editing
PROMPT_WAITING_FIELD  = 1
PROMPT_WAITING_VALUE  = 2

_flask_app   = None
_bot_loop    = None
_bot_instance = None
_scheduler_paused = False

# ── Auth ──────────────────────────────────────────────────────────────────────

def _admin_id() -> str:
    if not _flask_app:
        return ""
    with _flask_app.app_context():
        from database.models import Config
        return str(Config.get("telegram_admin_chat_id", "")
                   or _flask_app.config.get("TELEGRAM_ADMIN_CHAT_ID", ""))


async def _check_auth(update: Update) -> bool:
    uid = str(update.effective_chat.id)
    aid = _admin_id()
    if not aid:
        msg = (f"⚠️ <b>TELEGRAM_ADMIN_CHAT_ID غير محدد!</b>\n\n"
               f"Chat ID بتاعك: <code>{uid}</code>\n"
               f"أضفه في HF Secrets أو .env:\n"
               f"<code>TELEGRAM_ADMIN_CHAT_ID={uid}</code>")
        if update.callback_query:
            await update.callback_query.answer("غير مصرح", show_alert=True)
            await update.callback_query.edit_message_text(msg, parse_mode="HTML")
        else:
            await update.message.reply_text(msg, parse_mode="HTML")
        return False
    if uid != aid:
        if update.callback_query:
            await update.callback_query.answer("⛔ غير مصرح", show_alert=True)
        else:
            await update.message.reply_text(
                f"⛔ غير مصرح\nID بتاعك: <code>{uid}</code>", parse_mode="HTML")
        return False
    return True


# ── Notify (public API) ───────────────────────────────────────────────────────

def notify(message: str, parse_mode: str = "HTML"):
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


# ── Data helpers ──────────────────────────────────────────────────────────────

def _get_stats():
    with _flask_app.app_context():
        from database.models import Post
        total   = Post.query.count()
        posted  = Post.query.filter_by(status="POSTED").count()
        pending = Post.query.filter_by(status="NEW").count()
        today   = Post.query.filter(
            Post.posted_at >= datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0)
        ).count()
        return total, posted, pending, today


def _get_platforms():
    with _flask_app.app_context():
        from database.models import Platform
        icons = {"facebook":"📘","instagram":"📷","twitter":"𝕏",
                 "threads":"🔗","linkedin":"💼"}
        return [(p.name, icons.get(p.name,"📱"), p.enabled)
                for p in Platform.query.all()]


def _get_ai_status():
    with _flask_app.app_context():
        from services.key_rotator import get_provider_status
        result = []
        for p in ["cohere","gemini","groq","openrouter","openai"]:
            s = get_provider_status(p)
            if s["total"] > 0:
                result.append((p, s["available"], s["total"], s["healthy"]))
        return result


def _get_pending_posts(limit=8):
    with _flask_app.app_context():
        from database.models import Post
        return Post.query.filter_by(status="NEW").order_by(
            Post.created_at.asc()).limit(limit).all()


def _get_recent_logs(limit=8):
    with _flask_app.app_context():
        from database.models import WorkflowLog
        return WorkflowLog.query.order_by(
            WorkflowLog.created_at.desc()).limit(limit).all()


def _get_top_posts(limit=5):
    with _flask_app.app_context():
        from database.models import Post
        return Post.query.filter_by(status="POSTED").order_by(
            Post.engagement_score.desc()).limit(limit).all()


# ── Keyboards ─────────────────────────────────────────────────────────────────

def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 الإحصائيات",    callback_data="stats"),
         InlineKeyboardButton("📝 الأفكار",        callback_data="ideas_menu")],
        [InlineKeyboardButton("📢 نشر الآن",       callback_data="post_now"),
         InlineKeyboardButton("🧠 توليد أفكار",    callback_data="gen_ideas")],
        [InlineKeyboardButton("📈 التحليلات",      callback_data="analytics"),
         InlineKeyboardButton("📋 السجل",          callback_data="logs")],
        [InlineKeyboardButton("📱 المنصات",        callback_data="platforms"),
         InlineKeyboardButton("🗝️ مفاتيح AI",      callback_data="ai_keys")],
        [InlineKeyboardButton("✍️ البرومبتات",     callback_data="prompts_menu"),
         InlineKeyboardButton("⚙️ الإعدادات",      callback_data="config")],
        [InlineKeyboardButton("⏸️ إيقاف/تشغيل الجدولة", callback_data="toggle_sched")],
    ])


def kb_back(to="main"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 رجوع", callback_data=f"back_{to}")]
    ])


def kb_ideas(posts):
    rows = []
    for p in posts:
        idea_short = (p.idea or "")[:35]
        rows.append([
            InlineKeyboardButton(f"#{p.id} {idea_short}", callback_data=f"idea_view_{p.id}")
        ])
    rows.append([
        InlineKeyboardButton("🔙 رجوع", callback_data="back_main"),
        InlineKeyboardButton("🔄 تحديث", callback_data="ideas_menu"),
    ])
    return InlineKeyboardMarkup(rows)


def kb_idea_actions(post_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭️ تخطي",  callback_data=f"skip_{post_id}"),
         InlineKeyboardButton("🗑️ حذف",   callback_data=f"delete_{post_id}"),
         InlineKeyboardButton("📢 نشر",   callback_data=f"publish_{post_id}")],
        [InlineKeyboardButton("🔙 رجوع للأفكار", callback_data="ideas_menu")],
    ])


def kb_confirm(action, post_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأكيد",  callback_data=f"confirm_{action}_{post_id}"),
         InlineKeyboardButton("❌ إلغاء",  callback_data=f"idea_view_{post_id}")],
    ])


def kb_platforms(platforms):
    rows = []
    for name, icon, enabled in platforms:
        status = "✅" if enabled else "❌"
        rows.append([
            InlineKeyboardButton(
                f"{icon} {name.capitalize()} {status}",
                callback_data=f"toggle_platform_{name}"
            )
        ])
    rows.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
    return InlineKeyboardMarkup(rows)


# Stage labels
STAGE_LABELS = {
    "idea_factory":    "🧠 مصنع الأفكار",
    "post_writer":     "✍️ كاتب المنشورات",
    "image_prompt":    "🎨 برومبت الصور",
    "ig_caption":      "📷 كابشن Instagram",
    "x_caption":       "𝕏 كابشن Twitter/X",
    "threads_caption": "🔗 كابشن Threads",
    "linkedin_caption":"💼 كابشن LinkedIn",
}


def kb_prompts_list():
    """قائمة بكل المراحل."""
    rows = []
    for stage, label in STAGE_LABELS.items():
        rows.append([InlineKeyboardButton(label, callback_data=f"prompt_view_{stage}")])
    rows.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
    return InlineKeyboardMarkup(rows)


def kb_prompt_actions(stage):
    """أزرار تعديل مرحلة معينة."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ تعديل System Prompt",
                              callback_data=f"prompt_edit_{stage}_system")],
        [InlineKeyboardButton("✏️ تعديل User Prompt",
                              callback_data=f"prompt_edit_{stage}_user")],
        [InlineKeyboardButton("🌡️ تعديل Temperature",
                              callback_data=f"prompt_edit_{stage}_temperature"),
         InlineKeyboardButton("🔢 تعديل Max Tokens",
                              callback_data=f"prompt_edit_{stage}_max_tokens")],
        [InlineKeyboardButton("🤖 تغيير النموذج",
                              callback_data=f"prompt_edit_{stage}_model")],
        [InlineKeyboardButton("🔙 رجوع للبرومبتات", callback_data="prompts_menu")],
    ])


# ── Message builders ──────────────────────────────────────────────────────────

def msg_main():
    total, posted, pending, today = _get_stats()
    sched = "⏸️ متوقفة" if _scheduler_paused else "▶️ تعمل"
    return (
        f"🧠 <b>بوست سوشال — لوحة التحكم</b>\n\n"
        f"💡 الأفكار: <b>{total}</b>  |  ✅ منشور: <b>{posted}</b>\n"
        f"⏳ انتظار: <b>{pending}</b>  |  📅 اليوم: <b>{today}</b>\n"
        f"🕐 الجدولة: {sched}\n\n"
        f"<i>اختر من القائمة:</i>"
    )


def msg_stats():
    total, posted, pending, today = _get_stats()
    platforms = _get_platforms()
    plat_lines = "\n".join(
        f"  {'✅' if en else '❌'} {icon} {name.capitalize()}"
        for name, icon, en in platforms
    )
    return (
        f"📊 <b>الإحصائيات التفصيلية</b>\n\n"
        f"💡 إجمالي الأفكار: <b>{total}</b>\n"
        f"✅ تم نشره: <b>{posted}</b>\n"
        f"⏳ في الانتظار: <b>{pending}</b>\n"
        f"📅 نُشر اليوم: <b>{today}</b>\n\n"
        f"<b>المنصات:</b>\n{plat_lines}"
    )


def msg_analytics():
    top = _get_top_posts()
    if not top:
        return "📈 <b>التحليلات</b>\n\nلا توجد بيانات بعد — انشر وأضف engagement scores."
    lines = ["📈 <b>أفضل المنشورات:</b>\n"]
    for i, p in enumerate(top, 1):
        lines.append(
            f"{i}. <code>#{p.id}</code> {(p.idea or '')[:50]}\n"
            f"   📊 Score: <b>{p.engagement_score}</b> | "
            f"👍 {p.likes} 💬 {p.comments} 🔁 {p.shares}"
        )
    return "\n\n".join(lines)


def msg_logs():
    logs = _get_recent_logs()
    if not logs:
        return "📋 <b>السجل</b>\n\nلا توجد أحداث بعد."
    icons = {"info": "ℹ️", "warning": "⚠️", "error": "❌"}
    lines = ["📋 <b>آخر الأحداث:</b>\n"]
    for log in logs:
        t    = log.created_at.strftime("%H:%M") if log.created_at else ""
        icon = icons.get(log.level, "•")
        lines.append(f"{icon} <code>[{t}]</code> <b>{log.event}</b>\n   {(log.message or '')[:100]}")
    return "\n\n".join(lines)


def msg_ai_keys():
    keys = _get_ai_status()
    if not keys:
        return "🗝️ <b>مفاتيح AI</b>\n\nلا توجد مفاتيح مضافة."
    lines = ["🗝️ <b>حالة مفاتيح AI:</b>\n"]
    for provider, avail, total, healthy in keys:
        icon = "🟢" if healthy else "🔴"
        lines.append(f"{icon} <b>{provider}</b>: {avail}/{total} متاح")
    return "\n".join(lines)


def msg_config():
    with _flask_app.app_context():
        from database.models import Config
        niche  = (Config.get("niche","") or "")[:60]
        ratio  = Config.get("image_ratio_percent","90")
        t_idea = Config.get("idea_factory_time","08:00")
        times  = " | ".join(Config.get(f"sched_{i}","—") for i in range(1,5))
        fb     = Config.get("fb_page_id","—")
        ig     = Config.get("ig_user_id","—")
    return (
        f"⚙️ <b>الإعدادات الحالية:</b>\n\n"
        f"🎯 النيش: <code>{niche}</code>\n"
        f"🖼️ نسبة الصور: <b>{ratio}%</b>\n"
        f"🕗 مصنع الأفكار: <b>{t_idea}</b>\n"
        f"📅 مواعيد النشر: <b>{times}</b>\n"
        f"📘 FB Page: <code>{fb}</code>\n"
        f"📷 IG User: <code>{ig}</code>"
    )


def msg_prompt_detail(stage):
    """عرض تفاصيل برومبت مرحلة معينة."""
    with _flask_app.app_context():
        from database.models import Prompt
        p = Prompt.query.get(stage)
    if not p:
        return f"❌ لا يوجد برومبت للمرحلة: {stage}"
    label = STAGE_LABELS.get(stage, stage)
    sys_preview  = (p.system_prompt or "")[:200]
    user_preview = (p.user_prompt or "")[:300]
    return (
        f"✍️ <b>{label}</b>\n\n"
        f"🤖 النموذج: <code>{p.model}</code>\n"
        f"🌡️ Temperature: <code>{p.temperature}</code>\n"
        f"🔢 Max Tokens: <code>{p.max_tokens}</code>\n\n"
        f"<b>System Prompt:</b>\n"
        f"<code>{sys_preview}{'...' if len(p.system_prompt or '') > 200 else ''}</code>\n\n"
        f"<b>User Prompt:</b>\n"
        f"<code>{user_preview}{'...' if len(p.user_prompt or '') > 300 else ''}</code>"
    )


# ── Command handlers ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_auth(update): return
    await update.message.reply_text(
        msg_main(), parse_mode="HTML", reply_markup=kb_main()
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)


async def cmd_myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_chat.id
    aid = _admin_id()
    is_admin = str(uid) == aid if aid else False
    await update.message.reply_text(
        f"🆔 <b>Chat ID بتاعك:</b> <code>{uid}</code>\n"
        f"Admin: {'✅ نعم' if is_admin else '❌ لا'}\n\n"
        + ("" if is_admin else
           f"لتسجيلك كـ Admin:\n<code>TELEGRAM_ADMIN_CHAT_ID={uid}</code>"),
        parse_mode="HTML"
    )


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء أي عملية تعديل جارية."""
    uid = update.effective_user.id
    key = f"edit_{uid}"
    if key in context.bot_data:
        del context.bot_data[key]
    await update.message.reply_text(
        "❌ تم الإلغاء.", reply_markup=None
    )
    await update.message.reply_text(
        msg_main(), parse_mode="HTML", reply_markup=kb_main()
    )


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    يستقبل النص الجديد لتعديل برومبت.
    يُفعَّل فقط لو فيه edit context مخزن.
    """
    if not await _check_auth(update): return

    uid = update.effective_user.id
    key = f"edit_{uid}"
    edit_ctx = context.bot_data.get(key)

    if not edit_ctx:
        # مش في وضع تعديل — تجاهل
        return

    stage = edit_ctx["stage"]
    field = edit_ctx["field"]
    new_value = update.message.text.strip()

    # Map field name to DB column
    field_map = {
        "system":      "system_prompt",
        "user":        "user_prompt",
        "temperature": "temperature",
        "max_tokens":  "max_tokens",
        "model":       "model",
    }
    db_field = field_map.get(field, field)

    # Validate
    try:
        if field == "temperature":
            new_value = float(new_value)
            if not (0.0 <= new_value <= 2.0):
                raise ValueError("يجب أن يكون بين 0.0 و 2.0")
        elif field == "max_tokens":
            new_value = int(new_value)
            if not (256 <= new_value <= 8192):
                raise ValueError("يجب أن يكون بين 256 و 8192")
    except ValueError as e:
        await update.message.reply_text(f"❌ قيمة غير صالحة: {e}\nحاول مجدداً:")
        return

    # Save to DB
    with _flask_app.app_context():
        from database.models import db, Prompt
        p = Prompt.query.get(stage)
        if not p:
            await update.message.reply_text("❌ المرحلة غير موجودة")
            del context.bot_data[key]
            return
        setattr(p, db_field, new_value)
        db.session.commit()

    # Clear edit context
    del context.bot_data[key]

    field_labels = {
        "system":      "System Prompt",
        "user":        "User Prompt",
        "temperature": "Temperature",
        "max_tokens":  "Max Tokens",
        "model":       "النموذج",
    }
    await update.message.reply_text(
        f"✅ <b>تم الحفظ!</b>\n"
        f"المرحلة: {STAGE_LABELS.get(stage, stage)}\n"
        f"الحقل: {field_labels.get(field, field)}\n"
        f"القيمة الجديدة: <code>{str(new_value)[:200]}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👁️ عرض البرومبت", callback_data=f"prompt_view_{stage}"),
             InlineKeyboardButton("🔙 القائمة",       callback_data="back_main")]
        ])
    )


# ── Callback query handler (الأزرار) ─────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await _check_auth(update): return

    data = query.data

    # ── Main menu ─────────────────────────────────────────────────────────────
    if data in ("back_main", "main"):
        await query.edit_message_text(
            msg_main(), parse_mode="HTML", reply_markup=kb_main())

    # ── Stats ─────────────────────────────────────────────────────────────────
    elif data == "stats":
        await query.edit_message_text(
            msg_stats(), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تحديث", callback_data="stats"),
                 InlineKeyboardButton("🔙 رجوع",  callback_data="back_main")]
            ])
        )

    # ── Ideas menu ────────────────────────────────────────────────────────────
    elif data == "ideas_menu":
        posts = _get_pending_posts()
        if not posts:
            await query.edit_message_text(
                "📝 <b>الأفكار المنتظرة</b>\n\nلا توجد أفكار حالياً.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🧠 توليد أفكار", callback_data="gen_ideas"),
                     InlineKeyboardButton("🔙 رجوع",        callback_data="back_main")]
                ])
            )
        else:
            await query.edit_message_text(
                f"📝 <b>الأفكار المنتظرة ({len(posts)}):</b>\n\nاختر فكرة:",
                parse_mode="HTML",
                reply_markup=kb_ideas(posts)
            )

    # ── View single idea ──────────────────────────────────────────────────────
    elif data.startswith("idea_view_"):
        post_id = int(data.split("_")[-1])
        with _flask_app.app_context():
            from database.models import Post
            p = Post.query.get(post_id)
        if not p:
            await query.edit_message_text("❌ الفكرة غير موجودة",
                                          reply_markup=kb_back("ideas_menu"))
            return
        text = (
            f"💡 <b>الفكرة #{p.id}</b>\n\n"
            f"{p.idea or '—'}\n\n"
            f"🎭 النبرة: {p.tone or '—'}\n"
            f"✍️ الأسلوب: {p.writing_style or '—'}\n"
            f"🚪 الافتتاحية: {p.opening_type or '—'}\n"
            f"📅 {p.created_at.strftime('%Y-%m-%d') if p.created_at else '—'}"
        )
        await query.edit_message_text(
            text, parse_mode="HTML",
            reply_markup=kb_idea_actions(post_id)
        )

    # ── Skip idea ─────────────────────────────────────────────────────────────
    elif data.startswith("skip_"):
        post_id = int(data.split("_")[-1])
        await query.edit_message_text(
            f"⏭️ تأكيد تخطي الفكرة #{post_id}؟",
            reply_markup=kb_confirm("skip", post_id)
        )

    # ── Delete idea ───────────────────────────────────────────────────────────
    elif data.startswith("delete_"):
        post_id = int(data.split("_")[-1])
        await query.edit_message_text(
            f"🗑️ تأكيد حذف الفكرة #{post_id}؟",
            reply_markup=kb_confirm("delete", post_id)
        )

    # ── Publish single idea ───────────────────────────────────────────────────
    elif data.startswith("publish_"):
        post_id = int(data.split("_")[-1])
        await query.edit_message_text(
            f"📢 تأكيد نشر الفكرة #{post_id} الآن؟",
            reply_markup=kb_confirm("publish", post_id)
        )

    # ── Confirm actions ───────────────────────────────────────────────────────
    elif data.startswith("confirm_"):
        parts   = data.split("_")
        action  = parts[1]
        post_id = int(parts[2])

        with _flask_app.app_context():
            from database.models import db, Post
            p = Post.query.get(post_id)
            if not p:
                await query.edit_message_text("❌ الفكرة غير موجودة",
                                              reply_markup=kb_back("ideas_menu"))
                return
            if action == "skip":
                p.status = "SKIP"
                db.session.commit()
                await query.edit_message_text(
                    f"⏭️ تم تخطي الفكرة #{post_id}",
                    reply_markup=kb_back("ideas_menu"))
            elif action == "delete":
                db.session.delete(p)
                db.session.commit()
                await query.edit_message_text(
                    f"🗑️ تم حذف الفكرة #{post_id}",
                    reply_markup=kb_back("ideas_menu"))
            elif action == "publish":
                await query.edit_message_text(
                    f"📢 جاري نشر الفكرة #{post_id} في الخلفية...",
                    reply_markup=kb_back("main"))
                threading.Thread(target=_run_post, daemon=True).start()

    # ── Generate ideas ────────────────────────────────────────────────────────
    elif data == "gen_ideas":
        await query.edit_message_text(
            "🧠 جاري توليد الأفكار في الخلفية...\nستصلك إشعار عند الانتهاء.",
            reply_markup=kb_back("main")
        )
        threading.Thread(target=_run_ideas, daemon=True).start()

    # ── Post now ──────────────────────────────────────────────────────────────
    elif data == "post_now":
        await query.edit_message_text(
            "📢 جاري تشغيل محرك النشر في الخلفية...\nستصلك إشعار عند الانتهاء.",
            reply_markup=kb_back("main")
        )
        threading.Thread(target=_run_post, daemon=True).start()

    # ── Analytics ─────────────────────────────────────────────────────────────
    elif data == "analytics":
        await query.edit_message_text(
            msg_analytics(), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تحديث", callback_data="analytics"),
                 InlineKeyboardButton("🔙 رجوع",  callback_data="back_main")]
            ])
        )

    # ── Logs ──────────────────────────────────────────────────────────────────
    elif data == "logs":
        await query.edit_message_text(
            msg_logs(), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تحديث", callback_data="logs"),
                 InlineKeyboardButton("🔙 رجوع",  callback_data="back_main")]
            ])
        )

    # ── Platforms ─────────────────────────────────────────────────────────────
    elif data == "platforms":
        platforms = _get_platforms()
        await query.edit_message_text(
            "📱 <b>المنصات — اضغط لتفعيل/تعطيل:</b>",
            parse_mode="HTML",
            reply_markup=kb_platforms(platforms)
        )

    elif data.startswith("toggle_platform_"):
        name = data.replace("toggle_platform_", "")
        with _flask_app.app_context():
            from database.models import db, Platform
            p = Platform.query.get(name)
            if p:
                p.enabled = not p.enabled
                db.session.commit()
        platforms = _get_platforms()
        await query.edit_message_text(
            "📱 <b>المنصات — اضغط لتفعيل/تعطيل:</b>",
            parse_mode="HTML",
            reply_markup=kb_platforms(platforms)
        )

    # ── AI Keys ───────────────────────────────────────────────────────────────
    elif data == "ai_keys":
        await query.edit_message_text(
            msg_ai_keys(), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تحديث", callback_data="ai_keys"),
                 InlineKeyboardButton("🔙 رجوع",  callback_data="back_main")]
            ])
        )

    # ── Config ────────────────────────────────────────────────────────────────
    elif data == "config":
        await query.edit_message_text(
            msg_config(), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
            ])
        )

    # ── Toggle scheduler ──────────────────────────────────────────────────────
    elif data == "toggle_sched":
        global _scheduler_paused
        _scheduler_paused = not _scheduler_paused
        _pause_resume_scheduler(_scheduler_paused)
        status = "⏸️ تم إيقاف الجدولة" if _scheduler_paused else "▶️ تم استئناف الجدولة"
        await query.edit_message_text(
            f"{status}\n\n{msg_main()}", parse_mode="HTML",
            reply_markup=kb_main()
        )

    # ── Prompts menu ──────────────────────────────────────────────────────────
    elif data == "prompts_menu":
        await query.edit_message_text(
            "✍️ <b>البرومبتات — اختر مرحلة للعرض أو التعديل:</b>",
            parse_mode="HTML",
            reply_markup=kb_prompts_list()
        )

    elif data.startswith("prompt_view_"):
        stage = data.replace("prompt_view_", "")
        await query.edit_message_text(
            msg_prompt_detail(stage), parse_mode="HTML",
            reply_markup=kb_prompt_actions(stage)
        )

    elif data.startswith("prompt_edit_"):
        # format: prompt_edit_{stage}_{field}
        parts = data.split("_", 3)  # ['prompt', 'edit', stage, field]
        if len(parts) < 4:
            await query.answer("خطأ في البيانات", show_alert=True)
            return
        stage = parts[2]
        field = parts[3]

        field_labels = {
            "system":      "System Prompt",
            "user":        "User Prompt",
            "temperature": "Temperature (0.0 - 2.0)",
            "max_tokens":  "Max Tokens (256 - 8192)",
            "model":       "اسم النموذج",
        }
        field_label = field_labels.get(field, field)

        # Get current value
        with _flask_app.app_context():
            from database.models import Prompt
            p = Prompt.query.get(stage)
        current = ""
        if p:
            current = str(getattr(p, field if field not in ("system","user")
                                  else f"{field}_prompt", ""))

        # Store edit context in bot_data
        context.bot_data[f"edit_{query.from_user.id}"] = {
            "stage": stage, "field": field, "msg_id": query.message.message_id
        }

        await query.edit_message_text(
            f"✏️ <b>تعديل {field_label}</b>\n"
            f"المرحلة: {STAGE_LABELS.get(stage, stage)}\n\n"
            f"<b>القيمة الحالية:</b>\n"
            f"<code>{current[:500] if current else '(فارغ)'}</code>\n\n"
            f"أرسل القيمة الجديدة الآن، أو /cancel للإلغاء:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ إلغاء", callback_data=f"prompt_view_{stage}")]
            ])
        )


# ── Background runners ────────────────────────────────────────────────────────

def _run_ideas():
    from services.workflow_service import run_idea_factory
    run_idea_factory(_flask_app)

def _run_post():
    from services.workflow_service import run_post_engine
    run_post_engine(_flask_app)

def _pause_resume_scheduler(pause: bool):
    try:
        import app as _app_module
        sched = getattr(_app_module, 'scheduler', None)
        if sched:
            sched.pause() if pause else sched.resume()
    except Exception as e:
        logger.warning(f"Scheduler pause/resume: {e}")


# ── Bot lifecycle ─────────────────────────────────────────────────────────────

def start_bot(flask_app):
    global _flask_app
    _flask_app = flask_app

    token = flask_app.config.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        with flask_app.app_context():
            from database.models import Config
            token = Config.get("telegram_bot_token", "")
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set — bot disabled")
        return

    t = threading.Thread(target=_run_bot, args=(token,), daemon=True, name="telegram-bot")
    t.start()
    logger.info("Telegram bot thread started")


def _run_bot(token: str):
    global _bot_loop, _bot_instance

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _bot_loop = loop

    async def _main():
        global _bot_instance
        tg_app = Application.builder().token(token).build()
        _bot_instance = tg_app.bot

        # Commands
        tg_app.add_handler(CommandHandler("start",  cmd_start))
        tg_app.add_handler(CommandHandler("help",   cmd_help))
        tg_app.add_handler(CommandHandler("myid",   cmd_myid))
        tg_app.add_handler(CommandHandler("cancel", cmd_cancel))

        # Callback queries (buttons)
        tg_app.add_handler(CallbackQueryHandler(handle_callback))

        # Text input for prompt editing (must be after callback handler)
        tg_app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text_input
        ))

        # Set bot commands menu
        await tg_app.bot.set_my_commands([
            BotCommand("start",  "🏠 القائمة الرئيسية"),
            BotCommand("myid",   "🆔 Chat ID بتاعك"),
            BotCommand("cancel", "❌ إلغاء التعديل"),
            BotCommand("help",   "❓ مساعدة"),
        ])

        logger.info("Telegram bot polling started")
        await tg_app.initialize()
        await tg_app.start()
        await tg_app.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"],
        )
        await asyncio.Event().wait()

    try:
        loop.run_until_complete(_main())
    except Exception as e:
        logger.error(f"Telegram bot crashed: {e}")
    finally:
        try:
            loop.close()
        except Exception:
            pass
