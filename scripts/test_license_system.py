"""Quick test script to verify license key system setup

Run this after creating the license table to verify everything works.

Usage:
    python scripts/test_license_system.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import db
from backend import create_app
from backend.models_license import LicenseKey
from backend.models import Trainer


def test_license_system():
    """Test the license key system."""
    app = create_app()
    with app.app_context():
        print("\n=== License Key System Test ===\n")

        # Check if table exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        if 'license_keys' not in tables:
            print("✗ Error: license_keys table does not exist!")
            print("  Run: python scripts/create_license_table.py")
            return False

        print("✓ License keys table exists")

        # Check for existing keys
        total_keys = LicenseKey.query.count()
        unused_keys = LicenseKey.query.filter_by(is_used=False).count()
        used_keys = LicenseKey.query.filter_by(is_used=True).count()

        print(f"✓ Total license keys: {total_keys}")
        print(f"  - Unused: {unused_keys}")
        print(f"  - Used: {used_keys}")

        if total_keys == 0:
            print("\n⚠ Warning: No license keys found!")
            print("  Generate keys with: python scripts/generate_licenses.py 10")
        else:
            print("\n✓ License key system is ready!")

            if unused_keys > 0:
                print(f"\nFirst 5 unused keys:")
                keys = LicenseKey.query.filter_by(is_used=False).limit(5).all()
                for idx, key in enumerate(keys, 1):
                    print(f"  {idx}. {key.license_key}")

        # Check trainer relationship
        if used_keys > 0:
            print("\nUsed keys:")
            keys = LicenseKey.query.filter_by(is_used=True).limit(5).all()
            for key in keys:
                trainer = Trainer.query.get(key.used_by_trainer_id) if key.used_by_trainer_id else None
                trainer_name = trainer.username if trainer else "Unknown"
                print(f"  {key.license_key} - Used by: {trainer_name} (ID: {key.used_by_trainer_id})")

        print("\n=== Test Complete ===\n")
        return True


if __name__ == '__main__':
    success = test_license_system()
    sys.exit(0 if success else 1)
