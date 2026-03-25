"""
Auto-Updater Service
====================
يتحقق من GitHub كل فترة — لو فيه commits جديدة:
  1. git pull
  2. pip install -r requirements.txt (لو requirements.txt اتغير)
  3. يسجل التحديث في WorkflowLog
  4. يرسل إشعار تيليجرام
  5. يعيد تشغيل التطبيق (على PythonAnywhere فقط)

يعمل كـ APScheduler job في الخلفية.
"""

import os
import subprocess
import logging
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)

GITHUB_REPO   = "https://github.com/drnopoh2810-spec/social-post"
GITHUB_API    = "https://api.github.com/repos/drnopoh2810-spec/social-post/commits/main"
APP_DIR       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_last_commit  = None   # آخر commit شفناه


def _get_latest_commit() -> str | None:
    """اجلب آخر commit SHA من GitHub API."""
    try:
        import requests
        r = requests.get(GITHUB_API, timeout=10,
                         headers={"Accept": "application/vnd.github.v3+json"})
        if r.ok:
            return r.json().get("sha", "")[:12]
    except Exception as e:
        logger.debug(f"Auto-updater: GitHub check failed: {e}")
    return None


def _get_local_commit() -> str:
    """اجلب الـ commit الحالي من git."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=APP_DIR, capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _requirements_hash() -> str:
    """Hash ملف requirements.txt لمعرفة لو اتغير."""
    req_path = os.path.join(APP_DIR, "requirements.txt")
    try:
        with open(req_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return ""


def _run(cmd: list, cwd=None) -> tuple[bool, str]:
    """تشغيل أمر shell وإرجاع (success, output)."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd or APP_DIR,
            capture_output=True, text=True, timeout=300
        )
        output = (result.stdout + result.stderr).strip()
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def _find_pip() -> str:
    """
    يحدد مسار pip الصحيح تلقائياً:
    1. venv داخل APP_DIR  (أي مشروع على أي سيرفر)
    2. venv في /home/USERNAME/project/venv  (PythonAnywhere)
    3. pip في الـ PATH العادي
    """
    candidates = [
        # venv داخل المشروع مباشرة
        os.path.join(APP_DIR, "venv", "bin", "pip"),
        os.path.join(APP_DIR, "venv", "bin", "pip3"),
        # PythonAnywhere — يستخرج اسم اليوزر من APP_DIR تلقائياً
        # مثال: /home/nopoh55678/social-post → /home/nopoh55678/social-post/venv/bin/pip
        os.path.join(APP_DIR, ".venv", "bin", "pip"),
        # Windows venv
        os.path.join(APP_DIR, "venv", "Scripts", "pip.exe"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            logger.debug(f"Auto-updater: using pip at {path}")
            return path

    # Fallback: pip في الـ PATH
    return "pip"


def _find_python() -> str:
    """يحدد مسار python الصحيح في الـ venv."""
    candidates = [
        os.path.join(APP_DIR, "venv", "bin", "python"),
        os.path.join(APP_DIR, "venv", "bin", "python3"),
        os.path.join(APP_DIR, ".venv", "bin", "python"),
        os.path.join(APP_DIR, "venv", "Scripts", "python.exe"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return "python3"


def check_and_update(app=None):
    """
    الدالة الرئيسية — تُستدعى من APScheduler.
    تتحقق من GitHub وتحدّث لو فيه جديد.
    """
    global _last_commit

    # تحقق من GitHub
    latest = _get_latest_commit()
    if not latest:
        return  # مش قادر يتصل بـ GitHub

    local = _get_local_commit()

    # أول مرة — سجّل الـ commit الحالي
    if _last_commit is None:
        _last_commit = local
        logger.debug(f"Auto-updater: initialized at commit {local}")
        return

    # مفيش تحديث
    if latest == local or latest == _last_commit:
        logger.debug(f"Auto-updater: up to date ({local})")
        return

    # فيه تحديث جديد!
    logger.info(f"Auto-updater: new commit detected {local} → {latest}")

    req_hash_before = _requirements_hash()

    # git pull
    success, output = _run(["git", "pull", "origin", "main"])
    if not success:
        logger.error(f"Auto-updater: git pull failed: {output[:300]}")
        _log_update(app, "error", f"git pull failed: {output[:200]}")
        return

    logger.info(f"Auto-updater: git pull OK\n{output[:200]}")

    # pip install لو requirements.txt اتغير
    req_hash_after = _requirements_hash()
    pip_output = ""
    if req_hash_before != req_hash_after:
        logger.info("Auto-updater: requirements.txt changed — running pip install...")
        pip_cmd = _find_pip()
        logger.info(f"Auto-updater: using pip: {pip_cmd}")
        pip_ok, pip_output = _run([
            pip_cmd, "install", "-r",
            os.path.join(APP_DIR, "requirements.txt"), "--quiet"
        ])
        if pip_ok:
            logger.info("Auto-updater: pip install OK")
        else:
            logger.warning(f"Auto-updater: pip install warning: {pip_output[:200]}")

    _last_commit = latest

    # سجّل في DB
    msg = (f"Updated {local} → {latest}\n"
           f"git: {output[:150]}\n"
           + (f"pip: {pip_output[:100]}" if pip_output else ""))
    _log_update(app, "info", msg)

    # إشعار تيليجرام
    try:
        from services.telegram_bot import notify
        notify(
            f"🔄 <b>تحديث تلقائي!</b>\n\n"
            f"📦 Commit: <code>{local}</code> → <code>{latest}</code>\n"
            f"{'📦 تم تحديث المكتبات' if req_hash_before != req_hash_after else ''}\n"
            f"✅ التطبيق محدّث"
        )
    except Exception:
        pass

    # إعادة تشغيل على PythonAnywhere
    _try_reload_webapp(app)


def _log_update(app, level, message):
    """سجّل التحديث في WorkflowLog."""
    if not app:
        return
    try:
        with app.app_context():
            from database.models import db, WorkflowLog
            db.session.add(WorkflowLog(
                event="auto_update",
                message=message[:500],
                level=level
            ))
            db.session.commit()
    except Exception as e:
        logger.warning(f"Auto-updater: log failed: {e}")


def _try_reload_webapp(app):
    """
    على PythonAnywhere — يعيد تشغيل الـ webapp.
    يستخرج اسم اليوزر تلقائياً من APP_DIR لو مش محدد.
    """
    if not app:
        return

    try:
        with app.app_context():
            from database.models import Config
            pa_token    = Config.get("pythonanywhere_token", "")
            pa_username = Config.get("pythonanywhere_username", "")

        # استخرج اسم اليوزر من APP_DIR تلقائياً
        # مثال: /home/nopoh55678/social-post → nopoh55678
        if not pa_username:
            parts = APP_DIR.split(os.sep)
            if len(parts) >= 3 and parts[1] == "home":
                pa_username = parts[2]
                logger.debug(f"Auto-updater: detected username from path: {pa_username}")

        if pa_token and pa_username:
            import requests
            domain = f"{pa_username}.pythonanywhere.com"
            r = requests.post(
                f"https://www.pythonanywhere.com/api/v0/user/{pa_username}/webapps/{domain}/reload/",
                headers={"Authorization": f"Token {pa_token}"},
                timeout=15
            )
            if r.ok:
                logger.info(f"Auto-updater: reloaded {domain}")
            else:
                logger.warning(f"Auto-updater: reload failed: {r.text[:100]}")
            return

        # Fallback: touch WSGI file
        if pa_username:
            wsgi_path = f"/var/www/{pa_username}_pythonanywhere_com_wsgi.py"
            if os.path.exists(wsgi_path):
                import pathlib
                pathlib.Path(wsgi_path).touch()
                logger.info(f"Auto-updater: touched WSGI file: {wsgi_path}")

    except Exception as e:
        logger.warning(f"Auto-updater: reload error: {e}")
