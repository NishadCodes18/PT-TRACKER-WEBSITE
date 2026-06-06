"""
Personal Trainer CRM & Expense Tracker
Main application entry point
"""
import os
from dotenv import load_dotenv

# Load environment variables first
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend import create_app

app = create_app()

if __name__ == '__main__':
    # Get the port assigned by Render, default to 5000 if running locally
    port = int(os.environ.get("PORT", 5000))
    # host='0.0.0.0' tells Flask to listen to external traffic
    app.run(host='0.0.0.0', port=port)

