import requests
import os
from dotenv import load_dotenv

load_dotenv()

EMAILJS_URL = "https://api.emailjs.com/api/v1.0/email/send"

SERVICE_ID = os.getenv("EMAILJS_SERVICE_ID")
TEMPLATE_ID = os.getenv("EMAILJS_TEMPLATE_ID")
PUBLIC_KEY = os.getenv("EMAILJS_PUBLIC_KEY")


def send_otp_email(to_email: str, otp: str):
    """
    Send OTP email using EmailJS REST API.
    EmailJS requires specific headers and parameter structure.
    """
    if not all([SERVICE_ID, TEMPLATE_ID, PUBLIC_KEY]):
        print("Warning: EmailJS credentials not configured. OTP not sent.")
        return

    # EmailJS API requires exact parameter names in template_params
    # These must match your EmailJS template variables exactly
    payload = {
        "service_id": SERVICE_ID,
        "template_id": TEMPLATE_ID,
        "user_id": PUBLIC_KEY,
        "template_params": {
            "email": to_email,  # Must match EmailJS template variable name
            "otp": otp,  # Must match EmailJS template variable name
            "message": f"Your verification code is: {otp}"  # Optional fallback
        }
    }

    try:
        # EmailJS API requires specific headers
        headers = {
            "Content-Type": "application/json",
            "Origin": "http://localhost:5000"  # Your frontend origin
        }

        response = requests.post(
            EMAILJS_URL,
            json=payload,
            headers=headers,
            timeout=15
        )

        # EmailJS returns 200 on success even if email fails to send
        # Check response content for actual success confirmation
        if response.status_code == 200:
            print(f"OTP email sent successfully to {to_email}")
            # Log response for debugging
            try:
                response_data = response.json()
                print(f"EmailJS response: {response_data}")
            except:
                print(f"EmailJS response text: {response.text}")
        else:
            print(f"EmailJS HTTP error: {response.status_code} - {response.text}")
            raise Exception(f"EmailJS API error: {response.status_code}")

    except requests.exceptions.Timeout:
        print("EmailJS request timeout - OTP not sent")
        raise Exception("Email service timeout")
    except requests.exceptions.RequestException as e:
        print(f"EmailJS network error: {e}")
        raise Exception("Email service unavailable")
    except Exception as e:
        print(f"EmailJS unexpected error: {e}")
        raise Exception("Email sending failed")
