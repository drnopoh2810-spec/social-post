import os
from app import create_app

os.environ.setdefault('FLASK_ENV', 'production')
application = create_app('production')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    application.run(host='0.0.0.0', port=port)
