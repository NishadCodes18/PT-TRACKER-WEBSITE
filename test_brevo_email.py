"""
Test script to verify Brevo email configuration
Run this after setting up your BREVO_API_KEY in .env
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_brevo_config():
    """Test if Brevo is properly configured"""
    print("=" * 60)
    print("BREVO EMAIL CONFIGURATION TEST")
    print("=" * 60)

    api_key = os.getenv('BREVO_API_KEY')
    sender_email = os.getenv('BREVO_SENDER_EMAIL')
    sender_name = os.getenv('BREVO_SENDER_NAME', 'PT Tracker')
    email_provider = os.getenv('EMAIL_PROVIDER')

    print(f"\n✓ Email Provider: {email_provider}")
    print(f"✓ Sender Email: {sender_email}")
    print(f"✓ Sender Name: {sender_name}")
    print(f"✓ API Key: {'✓ Set' if api_key else '✗ NOT SET'}")

    if not api_key:
        print("\n❌ ERROR: BREVO_API_KEY is not set in .env file")
        print("   Please add your Brevo API key to the .env file")
        return False

    if not sender_email:
        print("\n❌ ERROR: BREVO_SENDER_EMAIL is not set in .env file")
        return False

    if email_provider != 'brevo_api':
        print(f"\n⚠ WARNING: EMAIL_PROVIDER is set to '{email_provider}'")
        print("   Change to 'brevo_api' to use Brevo")

    print("\n" + "=" * 60)
    print("Configuration looks good! Testing email send...")
    print("=" * 60)

    return True

def test_send_email():
    """Test sending an actual email"""
    from backend import create_app
    from backend.utils.mail import send_html_email

    app = create_app()

    with app.app_context():
        # Get test recipient email
        test_email = input("\nEnter your email address to receive test email: ").strip()

        if not test_email or '@' not in test_email:
            print("❌ Invalid email address")
            return False

        print(f"\nSending test email to {test_email}...")

        # Try sending a simple test email
        result = send_html_email(
            recipient=test_email,
            subject="Test Email from PT Tracker - Brevo Setup",
            template_name="welcome",
            trainer_id=None,
            email_type='test',
            client_name="Test User",
            gym_name="NITRRO ZONE 360",
            app_developer="NISHAD PATIL"
        )

        if result:
            print("\n✅ SUCCESS! Email sent successfully via Brevo!")
            print(f"   Check {test_email} for the test email")
            print("\n📧 If you don't see it:")
            print("   1. Check your spam/junk folder")
            print("   2. Verify sender email in Brevo dashboard")
            print("   3. Check Brevo logs at https://app.brevo.com/")
            return True
        else:
            print("\n❌ FAILED: Could not send email")
            print("\n🔍 Troubleshooting:")
            print("   1. Check your BREVO_API_KEY is correct")
            print("   2. Verify sender email in Brevo dashboard")
            print("   3. Check Brevo account status and limits")
            print("   4. Review logs above for specific error")
            return False

def main():
    """Main test function"""
    try:
        # Test configuration
        if not test_brevo_config():
            return

        # Ask if user wants to send test email
        print("\n" + "=" * 60)
        send_test = input("Do you want to send a test email? (y/n): ").strip().lower()

        if send_test == 'y':
            test_send_email()
        else:
            print("\n✓ Configuration test complete!")
            print("  Run this script again when ready to test email sending")

    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
