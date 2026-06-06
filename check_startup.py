#!/usr/bin/env python3
"""
Pre-startup health check for Render.
Run this before starting the main app to catch configuration errors early.
"""
import os
import sys

def check_critical_env_vars():
    """Check if critical environment variables are set."""
    print("=" * 60)
    print("CHECKING CRITICAL ENVIRONMENT VARIABLES")
    print("=" * 60)

    critical_vars = {
        'SECRET_KEY': os.environ.get('SECRET_KEY'),
        'DATABASE_URL': os.environ.get('DATABASE_URL'),
    }

    optional_vars = {
        'SMTP_SERVER': os.environ.get('SMTP_SERVER'),
        'SMTP_PORT': os.environ.get('SMTP_PORT'),
        'SMTP_USER': os.environ.get('SMTP_USER'),
        'SMTP_PASSWORD': os.environ.get('SMTP_PASSWORD'),
    }

    all_critical_set = True

    print("\n✓ Critical (required):")
    for key, value in critical_vars.items():
        if value:
            if 'KEY' in key or 'SECRET' in key:
                print(f"  ✓ {key}: ***SET*** (length: {len(value)})")
            else:
                print(f"  ✓ {key}: {value[:30]}...")
        else:
            print(f"  ✗ {key}: NOT SET")
            all_critical_set = False

    print("\n⚠ Optional (email features):")
    smtp_count = 0
    for key, value in optional_vars.items():
        if value:
            if 'PASSWORD' in key:
                print(f"  ✓ {key}: ***SET***")
            else:
                print(f"  ✓ {key}: {value}")
            smtp_count += 1
        else:
            print(f"  ✗ {key}: NOT SET")

    if not all_critical_set:
        print("\n❌ CRITICAL: Missing required environment variables!")
        print("   App will fail to start.")
        return False

    if smtp_count < 4:
        print(f"\n⚠ WARNING: Email not configured ({smtp_count}/4 SMTP vars set)")
        print("   App will start but emails won't work.")

    return True


def check_database_connection():
    """Check if database is accessible."""
    print("\n" + "=" * 60)
    print("CHECKING DATABASE CONNECTION")
    print("=" * 60)

    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("⚠ No DATABASE_URL set - will use SQLite")
        return True

    try:
        if database_url.startswith('postgres'):
            print(f"Database: PostgreSQL")
            print("Attempting connection...")

            # Quick connection test
            import psycopg2
            from urllib.parse import urlparse

            result = urlparse(database_url)
            conn = psycopg2.connect(
                database=result.path[1:],
                user=result.username,
                password=result.password,
                host=result.hostname,
                port=result.port or 5432,
                connect_timeout=10
            )
            conn.close()
            print("✓ Database connection successful!")
            return True
        else:
            print(f"Database: SQLite")
            return True

    except Exception as e:
        print(f"✗ Database connection FAILED: {e}")
        return False


def check_port_available():
    """Check if PORT is set for Render."""
    print("\n" + "=" * 60)
    print("CHECKING PORT CONFIGURATION")
    print("=" * 60)

    port = os.environ.get('PORT')
    if port:
        print(f"✓ PORT: {port}")
        return True
    else:
        print("⚠ PORT not set - using default 5000")
        print("  (This is normal for local dev, but may fail on Render)")
        return True


if __name__ == '__main__':
    print("\n🔍 Render Startup Health Check\n")

    checks_passed = True

    if not check_critical_env_vars():
        checks_passed = False

    if not check_port_available():
        checks_passed = False

    if not check_database_connection():
        checks_passed = False

    print("\n" + "=" * 60)
    if checks_passed:
        print("✅ ALL CHECKS PASSED - App should start successfully")
        print("=" * 60)
        sys.exit(0)
    else:
        print("❌ SOME CHECKS FAILED - App may fail to start")
        print("=" * 60)
        print("\nCheck Render environment variables and database configuration.")
        sys.exit(1)
