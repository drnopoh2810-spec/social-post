"""Development runner."""
import os
from app import create_app

os.environ.setdefault('FLASK_ENV', 'development')
app = create_app('development')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
