"""Database migration: Add license_keys table

Run this script to create the license_keys table in your database.
Works with both SQLite (local) and PostgreSQL (production).

Usage:
    python scripts/create_license_table.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import db
from backend import create_app
from backend.models_license import LicenseKey

def create_license_table():
    """Create the license_keys table."""
    app = create_app()
    with app.app_context():
        print("Creating license_keys table...")

        # Check database type
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        is_postgres = 'postgresql' in db_uri

        if is_postgres:
            print("✓ Detected PostgreSQL database")
        else:
            print("✓ Detected SQLite database")

        # Create table
        try:
            db.create_all()
            print("✓ License keys table created successfully!")
        except Exception as e:
            print(f"✗ Error creating table: {e}")
            return False

        # Verify table exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        if 'license_keys' in tables:
            print("✓ Verified: license_keys table exists in database")

            # Show table columns
            columns = inspector.get_columns('license_keys')
            print(f"\n✓ Table structure ({len(columns)} columns):")
            for col in columns:
                print(f"  - {col['name']}: {col['type']}")

            # Count existing keys
            count = LicenseKey.query.count()
            print(f"\n✓ Current license keys in database: {count}")

            if count == 0:
                print("\n⚡ Next step: Generate license keys with:")
                print("   python scripts/generate_licenses.py 20")
        else:
            print("✗ Error: license_keys table was not created")
            return False

        return True

if __name__ == '__main__':
    success = create_license_table()
    sys.exit(0 if success else 1)
