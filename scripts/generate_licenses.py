"""Generate license keys for gym tracker registration

This script generates unique license keys that can be distributed to users
who want to register for the gym tracker system.

Usage:
    python scripts/generate_licenses.py <number_of_keys>

Example:
    python scripts/generate_licenses.py 10
"""
import sys
import os
import secrets
import string

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import db
from backend import create_app
from backend.models_license import LicenseKey


def generate_license_key():
    """Generate a random license key in format: XXXX-XXXX-XXXX-XXXX"""
    chars = string.ascii_uppercase + string.digits
    parts = []
    for _ in range(4):
        part = ''.join(secrets.choice(chars) for _ in range(4))
        parts.append(part)
    return '-'.join(parts)


def generate_licenses(count=10, notes=None):
    """Generate multiple license keys and save to database."""
    app = create_app()
    with app.app_context():
        generated = []
        for i in range(count):
            # Generate unique key
            while True:
                key = generate_license_key()
                existing = LicenseKey.query.filter_by(license_key=key).first()
                if not existing:
                    break

            # Create license record
            license_record = LicenseKey(
                license_key=key,
                notes=notes or f'Generated batch on 2026-06-12'
            )
            db.session.add(license_record)
            generated.append(key)

        db.session.commit()
        print(f"\n✓ Generated {count} license keys:\n")
        for idx, key in enumerate(generated, 1):
            print(f"{idx:2d}. {key}")

        print(f"\n✓ Keys saved to database successfully!")
        print(f"Total unused keys: {LicenseKey.query.filter_by(is_used=False).count()}")

        return generated


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scripts/generate_licenses.py <number_of_keys>")
        print("Example: python scripts/generate_licenses.py 10")
        sys.exit(1)

    try:
        count = int(sys.argv[1])
        if count < 1 or count > 100:
            print("Error: Please specify between 1 and 100 keys")
            sys.exit(1)

        notes = sys.argv[2] if len(sys.argv) > 2 else None
        generate_licenses(count, notes)
    except ValueError:
        print("Error: Invalid number")
        sys.exit(1)
