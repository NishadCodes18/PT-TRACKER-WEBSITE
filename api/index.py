"""Vercel serverless function entry point."""
import os
import sys

# Add the parent directory to the path so we can import from backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from backend import create_app

app = create_app()
