"""WSGI entrypoint for Gunicorn / Render."""
import os
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from backend import create_app

app = create_app()
