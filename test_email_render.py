#!/usr/bin/env python3
"""
Quick email diagnostic script for Render platform.
Run this on Render to test SMTP configuration.
"""
import os
import sys

def check_env_vars():
    """Check if all required SMTP environment variables are set."""
    print("=" * 60)
    print("CHECKING ENVIRONMENT VARIABLES")
    print("=" * 60)

    required_vars = {
        'SMTP_SERVER': os.environ.get('SMTP_SERVER'),
        'SMTP_PORT': os.environ.get('SMTP_PORT'),
        'SMTP_USE_TLS': os.environ.get('SMTP_USE_TLS'),
        'SMTP_USE_SSL': os.environ.get('SMTP_USE_SSL'),
        'SMTP_USER': os.environ.get('SMTP_USER'),
        'SMTP_PASSWORD': os.environ.get('SMTP_PASSWORD'),
    }

    all_set = True
    for key, value in required_vars.items():
        if value:
            if 'PASSWORD' in key:
                print(f"✓ {key}: ***SET*** (length: {len(value)})")
            else:
                print(f"✓ {key}: {value}")
        else:
            print(f"✗ {key}: NOT SET")
            all_set = False

    print()
    if all_set:
        print("✓ All required environment variables are set!")
    else:
        print("✗ MISSING environment variables! Add them in Render dashboard.")
        print("   Then click 'Manual Deploy' → 'Clear build cache & deploy'")
        return False

    return True


def test_smtp_connection():
    """Test SMTP connection without sending email."""
    print("=" * 60)
    print("TESTING SMTP CONNECTION")
    print("=" * 60)

    import smtplib
    import ssl

    host = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    port = int(os.environ.get('SMTP_PORT', 587))
    use_tls = os.environ.get('SMTP_USE_TLS', 'true').lower() in ('true', '1', 'yes')
    use_ssl = os.environ.get('SMTP_USE_SSL', 'false').lower() in ('true', '1', 'yes')
    user = os.environ.get('SMTP_USER')
    password = os.environ.get('SMTP_PASSWORD')

    try:
        print(f"Connecting to {host}:{port}...")
        print(f"Mode: {'SSL' if use_ssl and port == 465 else 'STARTTLS' if use_tls else 'Plain'}")

        if use_ssl and port == 465:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, port, timeout=30, context=context)
        else:
            server = smtplib.SMTP(host, port, timeout=30)
            if use_tls:
                print("Starting TLS...")
                context = ssl.create_default_context()
                server.starttls(context=context)

        print("Logging in...")
        server.login(user, password)
        print("✓ LOGIN SUCCESSFUL!")

        server.quit()
        print("✓ Connection test passed!")
        return True

    except Exception as e:
        print(f"✗ CONNECTION FAILED: {e}")
        return False


if __name__ == '__main__':
    print("\n🔍 Email Diagnostic Tool for Render\n")

    if not check_env_vars():
        sys.exit(1)

    if not test_smtp_connection():
        print("\n❌ SMTP connection failed. Check:")
        print("   1. Are you using Gmail App Password (not regular password)?")
        print("   2. Did you remove spaces from the App Password?")
        print("   3. Is 2FA enabled on your Gmail account?")
        print("   4. Did you redeploy after setting env vars?")
        sys.exit(1)

    print("\n✅ All tests passed! Email should work.")
    print("\nNext steps:")
    print("   1. Try sending a test email from your admin panel")
    print("   2. Check Email Logs section for delivery status")
