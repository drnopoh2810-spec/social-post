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


def _parse_credentials(raw: str) -> dict:
    """
    Parse credentials from multiple formats:
    1. JSON string (single or multi-line)
    2. File path pointing to a .json file
    3. Base64-encoded JSON (for env vars that can't hold special chars)
    """
    raw = raw.strip()

    # Format 1: file path
    if raw.startswith("/") or raw.startswith("~") or raw.endswith(".json"):
        path = os.path.expanduser(raw)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

    # Format 2: JSON string (may be multi-line or single-line)
    if raw.startswith("{"):
        # Normalize: replace literal \n inside private_key with actual newlines
        # (some env systems escape the backslash)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Try fixing escaped newlines: \\n → \n
            fixed = raw.replace("\\\\n", "\\n")
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

    # Format 3: Base64-encoded JSON
    try:
        import base64
        decoded = base64.b64decode(raw).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        pass

    raise ValueError(
        "GOOGLE_SHEETS_CREDENTIALS format not recognized.\n"
        "Accepted formats:\n"
        "  1. JSON string (single line or multi-line)\n"
        "  2. Path to .json file: /home/user/credentials.json\n"
        "  3. Base64-encoded JSON string"
    )


def _get_client():
    """Get or create authenticated gspread client."""
    global _gc
    if _gc is not None:
        return _gc

    raw = os.environ.get("GOOGLE_SHEETS_CREDENTIALS", "").strip()
    if not raw:
        try:
            from database.models import Config
            raw = Config.get("google_sheets_credentials", "").strip()
        except Exception:
            pass

    if not raw:
        raise ValueError("GOOGLE_SHEETS_CREDENTIALS not configured")

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        creds_dict = _parse_credentials(raw)
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


def sync_from_sheets_to_db():
    """
    Full bidirectional sync: Sheets → DB.
    - New rows in Sheets → insert in DB
    - Updated status/engagement in Sheets → update DB
    - Returns (inserted, updated) counts
    """
    try:
        from database.models import db, Post
        ws = _get_sheet()
        all_values = ws.get_all_values()

        if len(all_values) < 2:
            return 0, 0

        header = all_values[0]
        rows   = all_values[1:]

        def col(row, name, default=""):
            try:
                idx = header.index(name)
                return row[idx] if idx < len(row) else default
            except ValueError:
                return default

        def parse_dt(s):
            if not s: return None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try: return datetime.strptime(s, fmt)
                except ValueError: pass
            return None

        inserted = updated = 0

        for row in rows:
            if not row or not row[0]:
                continue
            try:
                post_id = int(row[0])
            except (ValueError, IndexError):
                continue

            existing = Post.query.get(post_id)

            if existing:
                # Sync status change from Sheets → DB
                sheet_status = col(row, "status") or existing.status
                changed = False
                if sheet_status != existing.status:
                    existing.status = sheet_status
                    changed = True
                # Sync engagement
                try:
                    score = int(col(row, "engagement_score") or 0)
                    if score != (existing.engagement_score or 0):
                        existing.engagement_score = score
                        existing.impressions = int(col(row, "impressions") or 0)
                        existing.likes       = int(col(row, "engaged_users") or 0)
                        existing.comments    = int(col(row, "reactions") or 0)
                        changed = True
                except Exception:
                    pass
                # Sync post_content if empty in DB but filled in Sheets
                if not existing.post_content and col(row, "post_content"):
                    existing.post_content = col(row, "post_content")
                    changed = True
                if changed:
                    updated += 1
            else:
                # New row in Sheets → insert in DB
                try:
                    p = Post(
                        id              = post_id,
                        idea            = col(row, "idea"),
                        keywords        = col(row, "keywords"),
                        tone            = col(row, "tone"),
                        status          = col(row, "status") or "NEW",
                        created_at      = parse_dt(col(row, "created_at")) or datetime.utcnow(),
                        posted_at       = parse_dt(col(row, "posted_at")),
                        post_content    = col(row, "post_content"),
                        fb_post_id      = col(row, "fb_post_id"),
                        ig_post_id      = col(row, "ig_post_id"),
                        x_post_id       = col(row, "x_post_id"),
                        threads_post_id = col(row, "threads_post_id"),
                        linkedin_post_id= col(row, "linkedin_post_id"),
                        writing_style   = col(row, "writing_style"),
                        opening_type    = col(row, "opening_type"),
                        engagement_score= int(col(row, "engagement_score") or 0),
                        impressions     = int(col(row, "impressions") or 0),
                        likes           = int(col(row, "engaged_users") or 0),
                        comments        = int(col(row, "reactions") or 0),
                    )
                    db.session.add(p)
                    inserted += 1
                except Exception as ex:
                    logger.warning(f"Sheets sync insert error row {post_id}: {ex}")

        if inserted or updated:
            db.session.commit()
            logger.info(f"Sheets→DB sync: {inserted} inserted, {updated} updated")

        return inserted, updated

    except Exception as e:
        logger.warning(f"sync_from_sheets_to_db failed: {e}")
        return 0, 0


def write_ideas_to_sheets(ideas: list) -> int:
    """
    Write a list of new idea dicts directly to Google Sheets.
    Each idea: {idea, keywords, tone, writing_style, opening_type}
    Returns number of rows written.
    Auto-assigns IDs based on last row in sheet.
    """
    try:
        ws = _get_sheet()
        all_values = ws.get_all_values()

        # Ensure header
        if not all_values or all_values[0] != SHEET_COLUMNS:
            ws.clear()
            ws.insert_row(SHEET_COLUMNS, index=1)
            all_values = [SHEET_COLUMNS]

        # Find next available ID
        existing_ids = []
        for row in all_values[1:]:
            if row and row[0]:
                try: existing_ids.append(int(row[0]))
                except ValueError: pass
        next_id = max(existing_ids, default=0) + 1

        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        rows_to_add = []

        for idea in ideas:
            kw = idea.get("keywords", [])
            if isinstance(kw, list):
                kw = ", ".join(kw)
            row = [
                str(next_id),           # id
                idea.get("idea", ""),   # idea
                kw,                     # keywords
                idea.get("tone", ""),   # tone
                "NEW",                  # status
                now,                    # created_at
                "",                     # posted_at
                "",                     # post_content
                "", "", "", "", "",     # platform post IDs
                idea.get("writing_style", ""),
                idea.get("opening_type", ""),
                "0", "0", "0", "0", "0",  # engagement fields
            ]
            rows_to_add.append(row)
            next_id += 1

        if rows_to_add:
            ws.append_rows(rows_to_add, value_input_option="USER_ENTERED")
            logger.info(f"Sheets: wrote {len(rows_to_add)} new ideas")

        return len(rows_to_add)

    except Exception as e:
        logger.warning(f"write_ideas_to_sheets failed: {e}")
        return 0


def update_post_in_sheets(post_id: int, fields: dict):
    """
    Update specific fields for a post in Sheets by ID.
    fields: dict of column_name → value
    """
    try:
        ws = _get_sheet()
        all_values = ws.get_all_values()
        if len(all_values) < 2:
            return False

        header = all_values[0]
        post_id_str = str(post_id)

        for i, row in enumerate(all_values[1:], start=2):
            if row and row[0] == post_id_str:
                for col_name, value in fields.items():
                    if col_name in header:
                        col_idx = header.index(col_name) + 1  # 1-based
                        ws.update_cell(i, col_idx, str(value) if value is not None else "")
                logger.debug(f"Sheets: updated post #{post_id} fields {list(fields.keys())}")
                return True

        return False
    except Exception as e:
        logger.warning(f"update_post_in_sheets failed: {e}")
        return False
