"""Vercel serverless function entry point."""
import os
import sys
import traceback
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the parent directory to the path so we can import from backend
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

logger.info(f"Python path: {sys.path}")
logger.info(f"Parent directory: {parent_dir}")

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = os.path.join(parent_dir, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        logger.info(".env file loaded")
except Exception as e:
    logger.warning(f"Could not load .env file: {e}")

# Set Vercel flag if not already set
os.environ.setdefault('VERCEL', 'true')

# Validate critical environment variables
missing_vars = []
if not os.environ.get('DATABASE_URL'):
    missing_vars.append('DATABASE_URL')
    logger.error("DATABASE_URL is missing")
if not os.environ.get('SECRET_KEY') or os.environ.get('SECRET_KEY') == 'your-secret-key-here':
    missing_vars.append('SECRET_KEY')
    logger.error("SECRET_KEY is missing or using default")

if missing_vars:
    logger.critical(f"Missing environment variables: {', '.join(missing_vars)}")
    logger.info("Please configure these in Vercel Dashboard -> Settings -> Environment Variables")

# Initialize app
app = None
init_error = None
try:
    logger.info("Importing create_app from backend...")
    from backend import create_app
    logger.info("Creating Flask app...")
    app = create_app()
    logger.info("Flask app created successfully")
except Exception as e:
    init_error = str(e)
    init_traceback = traceback.format_exc()
    error_msg = f"CRITICAL ERROR: Failed to create Flask app: {e}"
    logger.error(error_msg)
    logger.error(init_traceback)

    # Create a minimal error app
    from flask import Flask, jsonify
    app = Flask(__name__)

    @app.route('/')
    @app.route('/<path:path>')
    def error_handler(path=''):
        return jsonify({
            "error": "Application failed to initialize",
            "message": init_error,
            "traceback": init_traceback
        }), 500

# Export app for Vercel
# Vercel's Python runtime looks for 'app' or 'application' variable
if app is None:
    logger.critical("App is None, creating minimal error handler")
    from flask import Flask, jsonify
    app = Flask(__name__)

    @app.route('/')
    @app.route('/<path:path>')
    def critical_error(path=''):
        return jsonify({
            "error": "Application initialization failed",
            "message": "Check Vercel logs for details"
        }), 500

logger.info("Exporting app as handler for Vercel")
# This is required for Vercel
handler = app
