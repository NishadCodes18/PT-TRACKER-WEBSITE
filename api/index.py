"""Vercel serverless function entry point."""
import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Add the parent directory to the path so we can import from backend
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

# Set Vercel flag if not already set
os.environ.setdefault('VERCEL', 'true')

# Load environment variables only if .env exists
try:
    from dotenv import load_dotenv
    env_path = os.path.join(parent_dir, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
except Exception:
    pass

# Initialize app
app = None
try:
    from backend import create_app
    app = create_app()
    logger.info("Flask app created successfully")
except Exception as e:
    logger.error(f"Failed to create Flask app: {e}", exc_info=True)
    from flask import Flask, jsonify
    app = Flask(__name__)

    @app.route('/')
    @app.route('/<path:path>')
    def error_handler(path=''):
        return jsonify({
            "error": "Application failed to initialize",
            "message": str(e),
            "hint": "Check DATABASE_URL is set correctly and email provider is configured"
        }), 500

# Export app for Vercel
handler = app
