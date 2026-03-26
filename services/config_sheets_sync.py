"""
Config Sync with Google Sheets
================================
يحفظ جميع الإعدادات في Google Sheets تلقائياً عند أي تغيير.

Sheet Structure:
  Tab 1 (Config): key | value | updated_at
  Tab 2 (AI Keys): id | provider | label | key_value | priority | is_active | is_exhausted | updated_at
  Tab 3 (API Keys): id | platform | label | key_value | is_active | updated_at
  Tab 4 (Prompts): stage | model | temperature | max_tokens | system_prompt | user_prompt | updated_at
  Tab 5 (Platforms): name | enabled | settings | updated_at
"""

import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

_gc = None  # gspread client (cached)


def _parse_credentials(raw: str) -> dict:
    """Parse credentials from multiple formats."""
    raw = raw.strip()

    # Format 1: file path
    if raw.startswith("/") or raw.startswith("~") or raw.endswith(".json"):
        path = os.path.expanduser(raw)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

    # Format 2: JSON string
    if raw.startswith("{"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
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

    raise ValueError("GOOGLE_SHEETS_CREDENTIALS format not recognized")


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
        logger.info("Google Sheets client initialized for config sync")
        return _gc
    except Exception as e:
        logger.error(f"Google Sheets auth failed: {e}")
        raise


def _get_spreadsheet():
    """Get the spreadsheet object."""
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
    return gc.open_by_key(sheet_id)


def _ensure_worksheet(spreadsheet, title: str, headers: list):
    """Ensure a worksheet exists with the given title and headers."""
    try:
        ws = spreadsheet.worksheet(title)
    except Exception:
        # Create new worksheet
        ws = spreadsheet.add_worksheet(title=title, rows=1000, cols=len(headers))
    
    # Ensure headers
    existing = ws.row_values(1)
    if existing != headers:
        ws.update("A1", [headers])
    
    return ws


def sync_config_to_sheets():
    """Sync all Config table to Google Sheets."""
    try:
        from database.models import Config
        
        spreadsheet = _get_spreadsheet()
        ws = _ensure_worksheet(spreadsheet, "Config", ["key", "value", "updated_at"])
        
        # Get all config
        configs = Config.query.all()
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        rows = [["key", "value", "updated_at"]]
        for cfg in configs:
            rows.append([cfg.key, cfg.value or "", now])
        
        # Clear and write
        ws.clear()
        ws.update("A1", rows, value_input_option="USER_ENTERED")
        
        logger.info(f"✅ Synced {len(configs)} config items to Sheets")
        return len(configs)
        
    except Exception as e:
        logger.error(f"sync_config_to_sheets failed: {e}")
        return 0


def sync_ai_keys_to_sheets():
    """Sync all AI Provider Keys to Google Sheets."""
    try:
        from database.models import AIProviderKey
        
        spreadsheet = _get_spreadsheet()
        ws = _ensure_worksheet(spreadsheet, "AI_Keys", [
            "id", "provider", "label", "key_value", "priority", 
            "is_active", "is_exhausted", "updated_at"
        ])
        
        keys = AIProviderKey.query.all()
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        rows = [["id", "provider", "label", "key_value", "priority", "is_active", "is_exhausted", "updated_at"]]
        for key in keys:
            rows.append([
                str(key.id),
                key.provider,
                key.label or "",
                key.key_value or "",
                str(key.priority),
                "TRUE" if key.is_active else "FALSE",
                "TRUE" if key.is_exhausted else "FALSE",
                now
            ])
        
        ws.clear()
        ws.update("A1", rows, value_input_option="USER_ENTERED")
        
        logger.info(f"✅ Synced {len(keys)} AI keys to Sheets")
        return len(keys)
        
    except Exception as e:
        logger.error(f"sync_ai_keys_to_sheets failed: {e}")
        return 0


def sync_api_keys_to_sheets():
    """Sync all API Keys (social platforms) to Google Sheets."""
    try:
        from database.models import ApiKey
        
        spreadsheet = _get_spreadsheet()
        ws = _ensure_worksheet(spreadsheet, "API_Keys", [
            "id", "platform", "label", "key_value", "is_active", "updated_at"
        ])
        
        keys = ApiKey.query.all()
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        rows = [["id", "platform", "label", "key_value", "is_active", "updated_at"]]
        for key in keys:
            rows.append([
                str(key.id),
                key.platform,
                key.label or "",
                key.key_value or "",
                "TRUE" if key.is_active else "FALSE",
                now
            ])
        
        ws.clear()
        ws.update("A1", rows, value_input_option="USER_ENTERED")
        
        logger.info(f"✅ Synced {len(keys)} API keys to Sheets")
        return len(keys)
        
    except Exception as e:
        logger.error(f"sync_api_keys_to_sheets failed: {e}")
        return 0


def sync_prompts_to_sheets():
    """Sync all Prompts to Google Sheets."""
    try:
        from database.models import Prompt
        
        spreadsheet = _get_spreadsheet()
        ws = _ensure_worksheet(spreadsheet, "Prompts", [
            "stage", "model", "temperature", "max_tokens", 
            "system_prompt", "user_prompt", "updated_at"
        ])
        
        prompts = Prompt.query.all()
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        rows = [["stage", "model", "temperature", "max_tokens", "system_prompt", "user_prompt", "updated_at"]]
        for p in prompts:
            rows.append([
                p.stage,
                p.model or "",
                str(p.temperature),
                str(p.max_tokens),
                p.system_prompt or "",
                p.user_prompt or "",
                now
            ])
        
        ws.clear()
        ws.update("A1", rows, value_input_option="USER_ENTERED")
        
        logger.info(f"✅ Synced {len(prompts)} prompts to Sheets")
        return len(prompts)
        
    except Exception as e:
        logger.error(f"sync_prompts_to_sheets failed: {e}")
        return 0


def sync_platforms_to_sheets():
    """Sync all Platforms to Google Sheets."""
    try:
        from database.models import Platform
        
        spreadsheet = _get_spreadsheet()
        ws = _ensure_worksheet(spreadsheet, "Platforms", [
            "name", "enabled", "settings", "updated_at"
        ])
        
        platforms = Platform.query.all()
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        rows = [["name", "enabled", "settings", "updated_at"]]
        for p in platforms:
            rows.append([
                p.name,
                "TRUE" if p.enabled else "FALSE",
                p.settings or "{}",
                now
            ])
        
        ws.clear()
        ws.update("A1", rows, value_input_option="USER_ENTERED")
        
        logger.info(f"✅ Synced {len(platforms)} platforms to Sheets")
        return len(platforms)
        
    except Exception as e:
        logger.error(f"sync_platforms_to_sheets failed: {e}")
        return 0


def sync_all_to_sheets():
    """Sync all configuration data to Google Sheets."""
    try:
        counts = {
            "config": sync_config_to_sheets(),
            "ai_keys": sync_ai_keys_to_sheets(),
            "api_keys": sync_api_keys_to_sheets(),
            "prompts": sync_prompts_to_sheets(),
            "platforms": sync_platforms_to_sheets(),
        }
        
        total = sum(counts.values())
        logger.info(f"✅ Full sync to Sheets complete: {counts}")
        return counts
        
    except Exception as e:
        logger.error(f"sync_all_to_sheets failed: {e}")
        return {}


def restore_config_from_sheets():
    """Restore Config from Google Sheets to DB."""
    try:
        from database.models import db, Config
        
        spreadsheet = _get_spreadsheet()
        ws = spreadsheet.worksheet("Config")
        rows = ws.get_all_values()
        
        if len(rows) < 2:
            return 0
        
        count = 0
        for row in rows[1:]:  # Skip header
            if len(row) >= 2 and row[0]:
                Config.set(row[0], row[1])
                count += 1
        
        db.session.commit()
        logger.info(f"✅ Restored {count} config items from Sheets")
        return count
        
    except Exception as e:
        logger.error(f"restore_config_from_sheets failed: {e}")
        return 0


def restore_all_from_sheets():
    """Restore all configuration from Google Sheets to DB."""
    try:
        from database.models import db, Config, AIProviderKey, ApiKey, Prompt, Platform
        
        spreadsheet = _get_spreadsheet()
        counts = {"config": 0, "ai_keys": 0, "api_keys": 0, "prompts": 0, "platforms": 0}
        
        # Restore Config
        try:
            ws = spreadsheet.worksheet("Config")
            rows = ws.get_all_values()[1:]  # Skip header
            for row in rows:
                if len(row) >= 2 and row[0]:
                    Config.set(row[0], row[1])
                    counts["config"] += 1
        except Exception as e:
            logger.warning(f"Config restore failed: {e}")
        
        # Restore AI Keys
        try:
            ws = spreadsheet.worksheet("AI_Keys")
            rows = ws.get_all_values()[1:]
            for row in rows:
                if len(row) >= 4 and row[1]:  # provider required
                    existing = AIProviderKey.query.filter_by(
                        provider=row[1], key_value=row[3]
                    ).first()
                    if not existing:
                        key = AIProviderKey(
                            provider=row[1],
                            label=row[2] if len(row) > 2 else "",
                            key_value=row[3],
                            priority=int(row[4]) if len(row) > 4 and row[4] else 0,
                            is_active=row[5].upper() == "TRUE" if len(row) > 5 else True,
                            is_exhausted=row[6].upper() == "TRUE" if len(row) > 6 else False,
                        )
                        db.session.add(key)
                        counts["ai_keys"] += 1
        except Exception as e:
            logger.warning(f"AI Keys restore failed: {e}")
        
        # Restore API Keys
        try:
            ws = spreadsheet.worksheet("API_Keys")
            rows = ws.get_all_values()[1:]
            for row in rows:
                if len(row) >= 4 and row[1]:  # platform required
                    existing = ApiKey.query.filter_by(
                        platform=row[1], label=row[2] if len(row) > 2 else ""
                    ).first()
                    if not existing:
                        key = ApiKey(
                            platform=row[1],
                            label=row[2] if len(row) > 2 else "",
                            key_value=row[3],
                            is_active=row[4].upper() == "TRUE" if len(row) > 4 else False,
                        )
                        db.session.add(key)
                        counts["api_keys"] += 1
        except Exception as e:
            logger.warning(f"API Keys restore failed: {e}")
        
        # Restore Prompts
        try:
            ws = spreadsheet.worksheet("Prompts")
            rows = ws.get_all_values()[1:]
            for row in rows:
                if len(row) >= 6 and row[0]:  # stage required
                    prompt = Prompt.query.get(row[0])
                    if prompt:
                        prompt.model = row[1] if len(row) > 1 else prompt.model
                        prompt.temperature = float(row[2]) if len(row) > 2 and row[2] else prompt.temperature
                        prompt.max_tokens = int(row[3]) if len(row) > 3 and row[3] else prompt.max_tokens
                        prompt.system_prompt = row[4] if len(row) > 4 else prompt.system_prompt
                        prompt.user_prompt = row[5] if len(row) > 5 else prompt.user_prompt
                        counts["prompts"] += 1
        except Exception as e:
            logger.warning(f"Prompts restore failed: {e}")
        
        # Restore Platforms
        try:
            ws = spreadsheet.worksheet("Platforms")
            rows = ws.get_all_values()[1:]
            for row in rows:
                if len(row) >= 2 and row[0]:  # name required
                    platform = Platform.query.get(row[0])
                    if platform:
                        platform.enabled = row[1].upper() == "TRUE" if len(row) > 1 else platform.enabled
                        platform.settings = row[2] if len(row) > 2 else platform.settings
                        counts["platforms"] += 1
        except Exception as e:
            logger.warning(f"Platforms restore failed: {e}")
        
        db.session.commit()
        logger.info(f"✅ Restored from Sheets: {counts}")
        return counts
        
    except Exception as e:
        logger.error(f"restore_all_from_sheets failed: {e}")
        return {}


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
