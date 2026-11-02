"""
WSGI entry point for QuizVerse Online Examination System.
Enables execution via Gunicorn, uWSGI, Waitress, or standard WSGI servers.
"""

import os
from app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    app.run(host=host, port=port)

