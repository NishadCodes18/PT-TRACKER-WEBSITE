"""Vercel serverless function entry point."""
import os
import sys
import traceback

# Add the parent directory to the path so we can import from backend
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = os.path.join(parent_dir, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")

# Set Vercel flag if not already set
os.environ.setdefault('VERCEL', 'true')

# Validate critical environment variables
missing_vars = []
if not os.environ.get('DATABASE_URL'):
    missing_vars.append('DATABASE_URL')
if not os.environ.get('SECRET_KEY') or os.environ.get('SECRET_KEY') == 'your-secret-key-here':
    missing_vars.append('SECRET_KEY')

if missing_vars:
    print(f"❌ CRITICAL: Missing environment variables: {', '.join(missing_vars)}")
    print("Please configure these in Vercel Dashboard → Settings → Environment Variables")

# Initialize app
app = None
try:
    from backend import create_app
    print("Creating Flask app...")
    app = create_app()
    print("Flask app created successfully")
except Exception as e:
    error_msg = f"CRITICAL ERROR: Failed to create Flask app: {e}\n{traceback.format_exc()}"
    print(error_msg)

    # Create a minimal error app
    from flask import Flask, jsonify
    app = Flask(__name__)

    @app.route('/')
    @app.route('/<path:path>')
    def error_handler(path=''):
        return jsonify({
            "error": "Application failed to initialize",
            "message": str(e),
            "traceback": traceback.format_exc()
        }), 500

# Export app for Vercel
# Vercel's Python runtime looks for 'app' or 'application' variable
if app is None:
    print("CRITICAL: App is None, creating minimal error handler")
    from flask import Flask, jsonify
    app = Flask(__name__)

    @app.route('/')
    @app.route('/<path:path>')
    def critical_error(path=''):
        return jsonify({
            "error": "Application initialization failed",
            "message": "Check Vercel logs for details"
        }), 500

# This is required for Vercel
handler = app
