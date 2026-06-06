"""Send a test welcome email using SMTP settings from .env.

Usage (from project root):
  python scripts/test_welcome_email.py you@example.com
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'backend'))

from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, '.env'))

from backend import create_app  # noqa: E402
from backend.utils.client_emails import send_client_welcome_email


class _FakeTrainer:
    username = 'Test Trainer'


class _FakeClient:
    id = 0
    trainer_id = 1
    name = 'Test Member'
    email = None
    gym_name = os.environ.get('GYM_NAME', 'NITRRO ZONE 360')
    pt_tier = '5000'
    time_slot = 'Mon, Wed, Fri'
    renewal_date = None
    trainer = _FakeTrainer()


def main():
    if len(sys.argv) < 2:
        print('Usage: python scripts/test_welcome_email.py recipient@email.com')
        sys.exit(1)

    recipient = sys.argv[1].strip()
    app = create_app()
    client = _FakeClient()
    client.email = recipient

    with app.app_context():
        ok = send_client_welcome_email(client)
        if ok:
            print(f'Welcome email sent to {recipient}')
        else:
            print('Failed to send. Check SMTP_USER, SMTP_PASSWORD, and SMTP_SERVER in .env')
            sys.exit(1)


if __name__ == '__main__':
    main()
