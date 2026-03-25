from flask import Blueprint, jsonify, request
from flask_login import login_required
from flask_wtf.csrf import csrf_exempt
from database.models import WorkflowLog
import threading

workflow_bp = Blueprint('workflow', __name__, url_prefix='/workflow')


@workflow_bp.route('/run-ideas', methods=['POST'])
@login_required
def run_ideas():
    from flask import current_app
    app = current_app._get_current_object()
    t = threading.Thread(target=_run_ideas_bg, args=(app,))
    t.daemon = True
    t.start()
    return jsonify({'ok': True, 'message': 'مصنع الأفكار يعمل في الخلفية'})


@workflow_bp.route('/run-post', methods=['POST'])
@login_required
def run_post():
    from flask import current_app
    app = current_app._get_current_object()
    t = threading.Thread(target=_run_post_bg, args=(app,))
    t.daemon = True
    t.start()
    return jsonify({'ok': True, 'message': 'محرك النشر يعمل في الخلفية'})


@workflow_bp.route('/logs', methods=['GET'])
@login_required
def get_logs():
    logs = WorkflowLog.query.order_by(WorkflowLog.created_at.desc()).limit(50).all()
    return jsonify([{
        'id': l.id,
        'event': l.event,
        'message': l.message,
        'level': l.level,
        'created_at': l.created_at.strftime('%Y-%m-%d %H:%M:%S') if l.created_at else '',
    } for l in logs])


def _run_ideas_bg(app):
    from services.workflow_service import run_idea_factory
    run_idea_factory(app)


def _run_post_bg(app):
    from services.workflow_service import run_post_engine
    run_post_engine(app)
