from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    idea = db.Column(db.Text)
    keywords = db.Column(db.Text)
    tone = db.Column(db.String(100))
    writing_style = db.Column(db.String(100))
    opening_type = db.Column(db.String(100))
    post_type = db.Column(db.String(20), default='image')
    status = db.Column(db.String(20), default='NEW')
    post_content = db.Column(db.Text)
    image_url = db.Column(db.Text)
    engagement_score = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    comments = db.Column(db.Integer, default=0)
    shares = db.Column(db.Integer, default=0)
    impressions = db.Column(db.Integer, default=0)
    fb_post_id = db.Column(db.String(100))
    ig_post_id = db.Column(db.String(100))
    x_post_id = db.Column(db.String(100))
    threads_post_id = db.Column(db.String(100))
    linkedin_post_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    posted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'idea': self.idea,
            'keywords': self.keywords,
            'tone': self.tone,
            'writing_style': self.writing_style,
            'opening_type': self.opening_type,
            'post_type': self.post_type,
            'status': self.status,
            'post_content': self.post_content,
            'image_url': self.image_url,
            'engagement_score': self.engagement_score,
            'likes': self.likes,
            'comments': self.comments,
            'shares': self.shares,
            'fb_post_id': self.fb_post_id,
            'ig_post_id': self.ig_post_id,
            'x_post_id': self.x_post_id,
            'threads_post_id': self.threads_post_id,
            'linkedin_post_id': self.linkedin_post_id,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'posted_at': self.posted_at.strftime('%Y-%m-%d %H:%M') if self.posted_at else None,
        }


class Config(db.Model):
    __tablename__ = 'config'
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text)

    # Mapping: DB key → environment variable name
    _ENV_MAP = {
        'niche':                    'NICHE',
        'cohere_api_key':           'COHERE_API_KEY',
        'gemini_api_key':           'GEMINI_API_KEY',
        'cloudinary_cloud_name':    'CLOUDINARY_CLOUD_NAME',
        'cloudinary_api_key':       'CLOUDINARY_API_KEY',
        'cloudinary_api_secret':    'CLOUDINARY_API_SECRET',
        'fb_page_id':               'FB_PAGE_ID',
        'fb_access_token':          'FB_ACCESS_TOKEN',
        'ig_user_id':               'IG_USER_ID',
        'ig_access_token':          'IG_ACCESS_TOKEN',
        'twitter_api_key':          'TWITTER_API_KEY',
        'twitter_api_secret':       'TWITTER_API_SECRET',
        'twitter_access_token':     'TWITTER_ACCESS_TOKEN',
        'twitter_access_token_secret': 'TWITTER_ACCESS_TOKEN_SECRET',
        'threads_user_id':          'THREADS_USER_ID',
        'threads_access_token':     'THREADS_ACCESS_TOKEN',
        'li_person_id':             'LI_PERSON_ID',
        'li_access_token':          'LI_ACCESS_TOKEN',
        'worker_url':               'WORKER_URL',
        'pollinations_key':         'POLLINATIONS_KEY',
        'telegram_bot_token':       'TELEGRAM_BOT_TOKEN',
        'telegram_admin_chat_id':   'TELEGRAM_ADMIN_CHAT_ID',
    }

    @staticmethod
    def get(key, default=''):
        """
        Priority:
        1. Environment variable (HuggingFace Secrets / .env)
        2. Database value (set via dashboard)
        3. default
        """
        import os
        from database.models import db
        # Check env first
        env_name = Config._ENV_MAP.get(key)
        if env_name:
            env_val = os.environ.get(env_name, '')
            if env_val:
                return env_val
        # Fallback to DB
        row = db.session.get(Config, key)
        return row.value if row else default

    @staticmethod
    def set(key, value):
        from database.models import db
        row = db.session.get(Config, key)
        if row:
            row.value = value
        else:
            row = Config(key=key, value=value)
            db.session.add(row)
        db.session.commit()


class ApiKey(db.Model):
    __tablename__ = 'api_keys'
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    label = db.Column(db.String(100))
    key_value = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'platform': self.platform,
            'label': self.label,
            'key_value': self.key_value,
            'is_active': self.is_active,
        }


class Prompt(db.Model):
    __tablename__ = 'prompts'
    stage = db.Column(db.String(50), primary_key=True)
    system_prompt = db.Column(db.Text)
    user_prompt = db.Column(db.Text)
    model = db.Column(db.String(100))
    temperature = db.Column(db.Float, default=0.8)
    max_tokens = db.Column(db.Integer, default=2048)

    def to_dict(self):
        return {
            'stage': self.stage,
            'system_prompt': self.system_prompt,
            'user_prompt': self.user_prompt,
            'model': self.model,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
        }


class Platform(db.Model):
    __tablename__ = 'platforms'
    name = db.Column(db.String(50), primary_key=True)
    enabled = db.Column(db.Boolean, default=True)
    settings = db.Column(db.Text, default='{}')

    def to_dict(self):
        import json
        return {
            'name': self.name,
            'enabled': self.enabled,
            'settings': json.loads(self.settings or '{}'),
        }


class AIModel(db.Model):
    __tablename__ = 'ai_models'
    stage = db.Column(db.String(50), primary_key=True)
    provider = db.Column(db.String(50))
    model_id = db.Column(db.String(100))
    api_key_ref = db.Column(db.String(100))

    def to_dict(self):
        return {
            'stage': self.stage,
            'provider': self.provider,
            'model_id': self.model_id,
        }


class AIProviderKey(db.Model):
    """
    Multiple API keys per AI provider with automatic rotation.
    When a key hits rate-limit or quota, the rotator moves to the next active key.
    """
    __tablename__ = 'ai_provider_keys'
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)   # cohere | gemini | groq | openrouter | openai
    label = db.Column(db.String(100))                      # e.g. "حساب شخصي", "حساب شركة"
    key_value = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)        # False = disabled by admin
    is_exhausted = db.Column(db.Boolean, default=False)    # True = quota/rate-limit hit
    priority = db.Column(db.Integer, default=0)            # lower = tried first
    fail_count = db.Column(db.Integer, default=0)          # consecutive failures
    last_used_at = db.Column(db.DateTime)
    last_error = db.Column(db.Text)
    exhausted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'provider': self.provider,
            'label': self.label,
            'key_value': self.key_value,
            'is_active': self.is_active,
            'is_exhausted': self.is_exhausted,
            'priority': self.priority,
            'fail_count': self.fail_count,
            'last_used_at': self.last_used_at.strftime('%Y-%m-%d %H:%M') if self.last_used_at else None,
            'last_error': self.last_error,
            'exhausted_at': self.exhausted_at.strftime('%Y-%m-%d %H:%M') if self.exhausted_at else None,
        }


class WorkflowLog(db.Model):
    __tablename__ = 'workflow_logs'
    id = db.Column(db.Integer, primary_key=True)
    event = db.Column(db.String(100))
    message = db.Column(db.Text)
    level = db.Column(db.String(20), default='info')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
