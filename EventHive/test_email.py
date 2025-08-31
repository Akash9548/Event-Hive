# test_email.py
import smtplib
from email.mime.text import MIMEText

def test_email():
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login("ishanverma2611@gmail.com", "jglq xxqn hfro qldx")
        print("✅ Email connection successful!")
        server.quit()
        return True
    except Exception as e:
        print(f"❌ Email test failed: {e}")
        return False

if __name__ == "__main__":
    test_email()