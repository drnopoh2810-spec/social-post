import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///social_post.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

    # Session & Cookie settings — مهم لـ HuggingFace Spaces (HTTPS proxy)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    WTF_CSRF_SSL_STRICT = False          # يسمح بـ CSRF عبر الـ proxy
    WTF_CSRF_TIME_LIMIT = 3600           # ساعة كاملة قبل انتهاء الـ token

    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

    # AI
    COHERE_API_KEY = os.environ.get('COHERE_API_KEY', '')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

    # Cloudinary
    CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME', '')
    CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY', '')
    CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET', '')

    # Social
    FB_PAGE_ID = os.environ.get('FB_PAGE_ID', '')
    FB_ACCESS_TOKEN = os.environ.get('FB_ACCESS_TOKEN', '')
    IG_USER_ID = os.environ.get('IG_USER_ID', '')
    IG_ACCESS_TOKEN = os.environ.get('IG_ACCESS_TOKEN', '')
    TWITTER_API_KEY = os.environ.get('TWITTER_API_KEY', '')
    TWITTER_API_SECRET = os.environ.get('TWITTER_API_SECRET', '')
    TWITTER_ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN', '')
    TWITTER_ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET', '')
    THREADS_USER_ID = os.environ.get('THREADS_USER_ID', '')
    THREADS_ACCESS_TOKEN = os.environ.get('THREADS_ACCESS_TOKEN', '')
    LI_PERSON_ID = os.environ.get('LI_PERSON_ID', '')
    LI_ACCESS_TOKEN = os.environ.get('LI_ACCESS_TOKEN', '')

    # Image
    WORKER_URL = os.environ.get('WORKER_URL', '')
    POLLINATIONS_KEY = os.environ.get('POLLINATIONS_KEY', '')
    IMAGE_WIDTH = 1080
    IMAGE_HEIGHT = 1350

    # Telegram Bot
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_ADMIN_CHAT_ID = os.environ.get('TELEGRAM_ADMIN_CHAT_ID', '')

    # Scheduler
    IDEA_FACTORY_TIME = os.environ.get('IDEA_FACTORY_TIME', '08:00')
    POST_TIMES = os.environ.get('POST_TIMES', '09:00,13:00,17:00,21:00')


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
