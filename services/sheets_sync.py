"""
Google Sheets Sync Service
===========================
يعمل كـ backup ثنائي الاتجاه بين SQLite وGoogle Sheets.

الاتجاهات:
  DB → Sheets : بعد كل نشر أو تحديث (push)
  Sheets → DB : عند بدء التشغيل لو DB فارغة أو ناقصة (restore)

الأعمدة في الـ Sheet:
  id, idea, keywords, tone, status, created_at, posted_at,
  post_content, fb_post_id, ig_post_id, x_post_id,
  threads_post_id, linkedin_post_id, writing_style,
  opening_type, engagement_score, impressions,
  engaged_users, reactions, engagement_rate
"""

import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# Column order in the Sheet (must match exactly)
SHEET_COLUMNS = [
    "id", "idea", "keywords", "tone", "status",
    "created_at", "posted_at", "post_content",
    "fb_post_id", "ig_post_id", "x_post_id",
    "threads_post_id", "linkedin_post_id",
    "writing_style", "opening_type",
    "engagement_score", "impressions",
    "engaged_users", "reactions", "engagement_rate",
]

_gc = None   # gspread client (cached)


def _get_client():
    """Get or create authenticated gspread client."""
    global _gc
    if _gc is not None:
        return _gc

    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS", "")
    if not creds_json:
        # Try DB
        try:
            from database.models import Config
            creds_json = Config.get("google_sheets_credentials", "")
        except Exception:
            pass

    if not creds_json:
        raise ValueError("GOOGLE_SHEETS_CREDENTIALS not configured")

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        creds_dict = json.loads(creds_json)
        scopes = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        _gc = gspread.authorize(creds)
        logger.info("Google Sheets client initialized")
        return _gc
    except Exception as e:
        logger.error(f"Google Sheets auth failed: {e}")
        raise


def _get_sheet():
    """Get the worksheet object."""
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")
    if not sheet_id:
        try:
            from database.models import Config
            sheet_id = Config.get("google_sheet_id", "")
        except Exception:
            pass
    if not sheet_id:
        raise ValueError("GOOGLE_SHEET_ID not configured")

    gc = _get_client()
    spreadsheet = gc.open_by_key(sheet_id)
    return spreadsheet.sheet1


def _post_to_row(post) -> list:
    """Convert a Post DB object to a Sheet row."""
    def safe(val):
        if val is None:
            return ""
        if isinstance(val, datetime):
            return val.strftime("%Y-%m-%d %H:%M:%S")
        return str(val)

    return [
        safe(post.id),
        safe(post.idea),
        safe(post.keywords),
        safe(post.tone),
        safe(post.status),
        safe(post.created_at),
        safe(post.posted_at),
        safe(post.post_content),
        safe(post.fb_post_id),
        safe(post.ig_post_id),
        safe(post.x_post_id),
        safe(post.threads_post_id),
        safe(post.linkedin_post_id),
        safe(post.writing_style),
        safe(post.opening_type),
        safe(post.engagement_score or 0),
        safe(post.impressions or 0),
        safe(post.likes or 0),       # engaged_users
        safe(post.comments or 0),    # reactions
        safe(0),                     # engagement_rate
    ]


def push_post(post):
    """
    Push a single post to Google Sheets.
    - If row with same id exists → update it
    - Otherwise → append new row
    """
    try:
        ws = _get_sheet()
        all_values = ws.get_all_values()

        # Ensure header row exists
        if not all_values or all_values[0] != SHEET_COLUMNS:
            ws.insert_row(SHEET_COLUMNS, index=1)
            all_values = ws.get_all_values()

        # Find existing row by id
        post_id_str = str(post.id)
        row_index = None
        for i, row in enumerate(all_values[1:], start=2):  # skip header
            if row and row[0] == post_id_str:
                row_index = i
                break

        new_row = _post_to_row(post)

        if row_index:
            # Update existing row
            ws.update(f"A{row_index}", [new_row])
            logger.debug(f"Sheets: updated post #{post.id} at row {row_index}")
        else:
            # Append new row
            ws.append_row(new_row, value_input_option="USER_ENTERED")
            logger.debug(f"Sheets: appended post #{post.id}")

    except Exception as e:
        logger.warning(f"Sheets push_post failed: {e}")


def push_all_posts():
    """Push all posts from DB to Sheets (full sync)."""
    try:
        from database.models import Post
        posts = Post.query.order_by(Post.id.asc()).all()
        if not posts:
            logger.info("Sheets: no posts to push")
            return 0

        ws = _get_sheet()
        # Clear and rewrite
        ws.clear()
        rows = [SHEET_COLUMNS]
        for p in posts:
            rows.append(_post_to_row(p))
        ws.update("A1", rows, value_input_option="USER_ENTERED")
        logger.info(f"Sheets: pushed {len(posts)} posts")
        return len(posts)

    except Exception as e:
        logger.warning(f"Sheets push_all failed: {e}")
        return 0


def restore_from_sheets():
    """
    Restore posts from Google Sheets → SQLite.
    Called on startup if DB is empty or has fewer rows than Sheet.
    Returns number of posts restored.
    """
    try:
        from database.models import db, Post
        ws = _get_sheet()
        all_values = ws.get_all_values()

        if len(all_values) < 2:
            logger.info("Sheets: no data to restore")
            return 0

        header = all_values[0]
        rows   = all_values[1:]

        def col(row, name):
            try:
                idx = header.index(name)
                return row[idx] if idx < len(row) else ""
            except ValueError:
                return ""

        restored = 0
        for row in rows:
            if not row or not row[0]:
                continue
            try:
                post_id = int(row[0])
            except (ValueError, IndexError):
                continue

            existing = Post.query.get(post_id)
            if existing:
                # Update engagement data if Sheet has newer values
                try:
                    score = int(col(row, "engagement_score") or 0)
                    if score > (existing.engagement_score or 0):
                        existing.engagement_score = score
                        existing.impressions = int(col(row, "impressions") or 0)
                        existing.likes       = int(col(row, "engaged_users") or 0)
                        existing.comments    = int(col(row, "reactions") or 0)
                        restored += 1
                except Exception:
                    pass
                continue

            # Create new post from Sheet row
            try:
                def parse_dt(s):
                    if not s: return None
                    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                        try: return datetime.strptime(s, fmt)
                        except ValueError: pass
                    return None

                p = Post(
                    id             = post_id,
                    idea           = col(row, "idea"),
                    keywords       = col(row, "keywords"),
                    tone           = col(row, "tone"),
                    status         = col(row, "status") or "NEW",
                    created_at     = parse_dt(col(row, "created_at")) or datetime.utcnow(),
                    posted_at      = parse_dt(col(row, "posted_at")),
                    post_content   = col(row, "post_content"),
                    fb_post_id     = col(row, "fb_post_id"),
                    ig_post_id     = col(row, "ig_post_id"),
                    x_post_id      = col(row, "x_post_id"),
                    threads_post_id= col(row, "threads_post_id"),
                    linkedin_post_id=col(row, "linkedin_post_id"),
                    writing_style  = col(row, "writing_style"),
                    opening_type   = col(row, "opening_type"),
                    engagement_score=int(col(row, "engagement_score") or 0),
                    impressions    = int(col(row, "impressions") or 0),
                    likes          = int(col(row, "engaged_users") or 0),
                    comments       = int(col(row, "reactions") or 0),
                )
                db.session.add(p)
                restored += 1
            except Exception as ex:
                logger.warning(f"Sheets restore row error: {ex}")
                continue

        if restored:
            db.session.commit()
            logger.info(f"Sheets: restored {restored} posts → DB")
        return restored

    except Exception as e:
        logger.warning(f"Sheets restore_from_sheets failed: {e}")
        return 0


def is_configured() -> bool:
    """Check if Google Sheets is configured."""
    creds = os.environ.get("GOOGLE_SHEETS_CREDENTIALS", "")
    sheet = os.environ.get("GOOGLE_SHEET_ID", "")
    if creds and sheet:
        return True
    try:
        from database.models import Config
        return bool(Config.get("google_sheets_credentials") and
                    Config.get("google_sheet_id"))
    except Exception:
        return False
