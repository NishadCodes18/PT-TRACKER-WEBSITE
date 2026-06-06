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
    debug = os.environ.get('FLASK_DEBUG', '1') == '1'
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=debug, host='0.0.0.0', port=port)