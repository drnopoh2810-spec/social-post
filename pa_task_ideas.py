#!/usr/bin/env python3
"""
PA Scheduled Task — توليد الأفكار
===================================
يُشغَّل كـ PythonAnywhere Scheduled Task مستقل.
لا يحتاج Flask يكون شغّال — يشتغل لوحده.

إعداد على PythonAnywhere:
  Command: /home/USERNAME/social-post/venv/bin/python /home/USERNAME/social-post/pa_task_ideas.py
  Schedule: Daily at 08:00
"""

import os
import sys

# ── Setup path ────────────────────────────────────────────────────────────────
APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(APP_DIR, ".env"))
except ImportError:
    # Parse .env manually if dotenv not installed
    env_path = os.path.join(APP_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

os.environ.setdefault("FLASK_ENV", "production")

print(f"[pa_task_ideas] Starting idea factory — {__import__('datetime').datetime.now()}")

# ── Run inside Flask app context ──────────────────────────────────────────────
try:
    from app import create_app
    app = create_app("production")

    with app.app_context():
        from services.workflow_service import run_idea_factory
        run_idea_factory(app)

    print("[pa_task_ideas] ✅ Done")

except Exception as e:
    print(f"[pa_task_ideas] ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
