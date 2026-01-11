"""
SMTP Email Configuration Test Script

This script tests the SMTP email configuration to ensure that the email agent
can successfully send emails. It validates the SMTP server connection, authentication,
and email delivery.

Usage:
    python test_email.py

The script will:
1. Display current SMTP configuration from .env
2. Prompt for a recipient email address
3. Attempt to send a test email
4. Report success or failure with detailed error messages

Environment Variables Required:
- SMTP_SERVER (default: smtp.gmail.com)
- SMTP_PORT (default: 587)
- SMTP_USERNAME: Sender email address
- SMTP_PASSWORD: Sender email password/app password

Dependencies:
- smtplib (built-in)
- python-dotenv
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

def test_smtp_connection():
    """
    Test SMTP connection and send a test email.
    
    Prompts user for recipient email and attempts to send a test message
    using the configured SMTP settings. Provides detailed feedback on
    success or failure.
    """
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    sender_email = os.getenv("SMTP_USERNAME")
    sender_password = os.getenv("SMTP_PASSWORD")
    
    print(f"--- SMTP Test Configuration ---")
    print(f"SMTP Server: {smtp_server}")
    print(f"SMTP Port: {smtp_port}")
    print(f"Sender Email: {sender_email}")
    print(f"Sender Password: {'[SET]' if sender_password else '[NOT SET]'}")
    
    if not sender_email or not sender_password:
        print("\n❌ Error: SMTP_USERNAME or SMTP_PASSWORD missing in .env")
        return

    recipient = input("\nEnter recipient email to receive test message: ")
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient
    msg['Subject'] = "🚀 SMTP Configuration Test"
    msg.attach(MIMEText("This is a test email to verify your SMTP settings. If you received this, your credentials are correct!", 'plain'))

    try:
        print(f"\nConnecting to {smtp_server}...")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            print("Logging in...")
            server.login(sender_email, sender_password)
            print("Sending test email...")
            server.send_message(msg)
        print(f"\n✅ SUCCESS: Email sent to {recipient}")
        print("Now you can be sure your .env credentials work!")
    except Exception as e:
        print(f"\n❌ FAILED to send email: {str(e)}")


if __name__ == "__main__":
    test_smtp_connection()
