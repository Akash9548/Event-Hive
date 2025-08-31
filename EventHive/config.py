# config.py
import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "supersecretkey")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URI", "sqlite:///eventhive.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "ishanverma2611@gmail.com")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "jglq xxqn hfro qldx")
    MAIL_DEFAULT_SENDER = ("EventHive", "ishanverma2611@gmail.com")
    
    RAZORPAY_KEY_ID = "test_mode"
    RAZORPAY_KEY_SECRET = "test_mode"
    TEST_MODE = True