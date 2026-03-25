#!/bin/bash
# ============================================================
# سكريبت التثبيت على VPS (Ubuntu 22.04+)
# الاستخدام: sudo bash deploy/install.sh
# ============================================================
set -e

APP_DIR="/opt/social_post"
SERVICE_NAME="social_post"
PYTHON="python3.11"

echo "🚀 تثبيت بوست سوشال..."

# 1. System packages
apt-get update -qq
apt-get install -y python3.11 python3.11-venv python3-pip nginx curl git \
    libjpeg-dev libpng-dev libwebp-dev

# 2. App directory
mkdir -p $APP_DIR
cp -r . $APP_DIR/
cd $APP_DIR

# 3. Virtual environment
$PYTHON -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Environment file
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  عدّل ملف .env بمفاتيحك الحقيقية: nano $APP_DIR/.env"
fi

# 5. Systemd service
cp deploy/social_post.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME

# 6. Nginx
cp deploy/nginx.conf /etc/nginx/sites-available/social_post
ln -sf /etc/nginx/sites-available/social_post /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

echo ""
echo "✅ التثبيت اكتمل!"
echo "📋 الأوامر المفيدة:"
echo "   systemctl status $SERVICE_NAME    — حالة الخدمة"
echo "   journalctl -u $SERVICE_NAME -f    — السجلات المباشرة"
echo "   systemctl restart $SERVICE_NAME   — إعادة التشغيل"
echo ""
echo "⚠️  لا تنسَ تعديل: $APP_DIR/.env"
