"""WSGI entrypoint for Gunicorn / Render."""
import os
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

try:
    from backend import create_app  # noqa: E402
    app = create_app()
    print("✓ Flask app created successfully")
except Exception as e:
    print(f"❌ FATAL: Failed to create Flask app: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
