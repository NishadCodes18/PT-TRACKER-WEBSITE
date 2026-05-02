"""Email sending utilities with HTML templates."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import render_template_string, current_app
import os


def render_email_template(template_name, **context):
    """Render an email template from backend/templates/emails/"""
    template_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'templates', 'emails'
    )
    
    template_path = os.path.join(template_dir, f'{template_name}.html')
    
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Email template not found: {template_path}")
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    return render_template_string(template_content, **context)


def create_html_email(recipient, subject, template_name, **context):
    """Create a MIME email with HTML content."""
    gym_name = current_app.config.get('GYM_NAME', 'Gym Tracker')
    
    # Add context defaults
    context.setdefault('gym_name', gym_name)
    context.setdefault('logo_url', '/static/images/gym-logo.png')
    context.setdefault('support_email', current_app.config.get('SMTP_USER', 'support@gym.com'))
    
    html_content = render_email_template(template_name, **context)
    
    # Create message with both plain text and HTML
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = current_app.config.get('SMTP_USER')
    msg['To'] = recipient
    
    # Plain text version (fallback)
    plain_text = f"Subject: {subject}\n\nPlease view this email in HTML format."
    msg.attach(MIMEText(plain_text, 'plain'))
    
    # HTML version
    msg.attach(MIMEText(html_content, 'html'))
    
    return msg


def send_html_email(recipient, subject, template_name, **context):
    """Send an HTML email using a template.
    
    Args:
        recipient: Email address to send to
        subject: Email subject line
        template_name: Name of template file (without .html extension)
        **context: Variables to pass to the template
        
    Example:
        send_html_email(
            'client@email.com',
            'Your Payment Reminder',
            'payment_reminder',
            client_name='John',
            due_amount=100
        )
    """
    if not recipient:
        return False
    
    try:
        msg = create_html_email(recipient, subject, template_name, **context)
        
        host = current_app.config.get('SMTP_SERVER', 'smtp.gmail.com')
        port = current_app.config.get('SMTP_PORT', 587)
        user = current_app.config.get('SMTP_USER')
        password = current_app.config.get('SMTP_PASSWORD')
        
        if not user or not password:
            print("SMTP credentials not configured")
            return False
        
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(user, password)
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"Failed to send email to {recipient}: {e}")
        return False


def send_html_email_async(app, recipient, subject, template_name, **context):
    """Send HTML email asynchronously in a thread."""
    import threading
    
    def _send():
        with app.app_context():
            send_html_email(recipient, subject, template_name, **context)
    
    thread = threading.Thread(target=_send)
    thread.daemon = True
    thread.start()
