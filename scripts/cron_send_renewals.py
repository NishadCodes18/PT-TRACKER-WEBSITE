"""Trigger automated renewal emails (used by Render cron)."""
import os
import sys

import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, '.env'))

APP_URL = os.environ.get('APP_URL', 'http://localhost:5000').rstrip('/')
CRON_SECRET = os.environ.get('CRON_SECRET', '')


def main():
    if not CRON_SECRET:
        print('CRON_SECRET is not set')
        sys.exit(1)

    url = f"{APP_URL}/api/cron/send-renewals"
    response = requests.post(
        url,
        headers={'Authorization': f'Bearer {CRON_SECRET}'},
        timeout=120,
    )
    print(response.status_code, response.text)
    response.raise_for_status()


if __name__ == '__main__':
    main()
